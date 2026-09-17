"""
SIH26117 — Engineering Evidence Extraction Layer
Extracts typed engineering measurements and provenance from NormalizedDocument structures.
Enforces deterministic measurement selection and strict fail-closed evidence validation.
"""

from datetime import datetime
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

try:
    from app.services.ingestion.models import (
        DocumentProvenance,
        NormalizedDocument,
        ParsedTable,
    )
except ImportError:
    from backend.app.services.ingestion.models import (
        DocumentProvenance,
        NormalizedDocument,
        ParsedTable,
    )

logger = logging.getLogger(__name__)

# Approved demonstrator sample fixture SHA-256 (corrosion_inspection_c101.pdf)
DEMO_C101_PDF_SHA256 = "30dfb6cc4472edd29002b273018f57c506153f4cdb0ecdaba18e2f43f3613cf8"


# ── Alias Dictionaries for Flexible Header Matching ─────────────────────────

NOMINAL_ALIASES = [
    "nominal",
    "nominal_mm",
    "nominal thickness",
    "nominal (mm)",
    "nominal_thickness",
    "design thickness",
    "design_thickness",
    "baseline",
    "baseline (mm)",
    "t_initial",
    "initial thickness",
    "initial_thickness",
    "t_nom",
]

CURRENT_ALIASES = [
    "actual",
    "actual_mm",
    "actual (mm)",
    "measured",
    "measured_mm",
    "measured (mm)",
    "current thickness",
    "current_thickness",
    "ut thickness",
    "ut_thickness",
    "wall thickness",
    "wall_thickness",
    "current_mm",
    "t_actual",
    "reading",
    "utg reading",
    "utg_reading",
]

LOCATION_ALIASES = [
    "cml",
    "cml_tag",
    "cml tag",
    "location",
    "inspection location",
    "inspection_location",
    "nozzle",
    "point",
    "measurement location",
    "tag",
]

DATE_ALIASES = [
    "date",
    "inspection_date",
    "measurement_date",
    "date_measured",
    "reading_date",
    "year",
]


class ExtractedMeasurement(BaseModel):
    """Discrete wall thickness gauging measurement with complete source provenance."""

    model_config = ConfigDict(protected_namespaces=())

    cml_tag: str = Field(default="CML-UNKNOWN", description="Corrosion monitoring location tag")
    location_desc: str = Field(default="", description="Detailed location description or nozzle tag")
    nominal_thickness_mm: Optional[float] = Field(default=None, description="Nominal/baseline thickness in mm")
    measured_thickness_mm: float = Field(..., description="Actual measured thickness in mm")
    loss_mm: Optional[float] = Field(default=None, description="Calculated metal loss in mm")
    measurement_date: Optional[str] = Field(default=None, description="Date of measurement")
    source_page: Optional[int] = Field(default=None, description="Page number where found")
    provenance: DocumentProvenance = Field(..., description="Traceable provenance anchor")


class EngineeringEvidence(BaseModel):
    """Structured engineering evidence extracted from raw document artifacts."""

    model_config = ConfigDict(protected_namespaces=())

    equipment_id: Optional[str] = Field(default=None, description="Primary equipment identifier")
    equipment_id_source: str = Field(default="UNKNOWN", description="Source of equipment ID (USER, DOCUMENT, VISION)")
    inspection_subject: Optional[str] = Field(default=None, description="Inspection subject or component description")
    
    measurements: List[ExtractedMeasurement] = Field(default_factory=list, description="All valid extracted measurements")
    selected_measurement: Optional[ExtractedMeasurement] = Field(default=None, description="Critical minimum measurement selected")

    nominal_thickness_mm: Optional[float] = Field(default=None, description="Baseline nominal thickness in mm")
    nominal_thickness_source: str = Field(default="NONE", description="Source of nominal thickness (DOCUMENT_TABLE, DOCUMENT_TEXT, DEMO_PRESET, NONE)")
    current_thickness_mm: Optional[float] = Field(default=None, description="Critical measured thickness in mm")
    current_thickness_source: str = Field(default="NONE", description="Source of current thickness (DOCUMENT_TABLE, DOCUMENT_TEXT, DEMO_PRESET, NONE)")
    elapsed_time_years: Optional[float] = Field(default=None, description="Elapsed operating time in years")
    elapsed_time_source: str = Field(default="NONE", description="Source of elapsed time (USER, DOCUMENT, APPROVED_CONFIG, DEMO_PRESET, NONE)")
    minimum_required_thickness_mm: Optional[float] = Field(default=None, description="Retirement limit in mm")
    minimum_thickness_source: str = Field(default="NONE", description="Source of minimum required thickness (USER, DOCUMENT, APPROVED_CONFIG, DEMO_PRESET, NONE)")

    source_filename: str = Field(..., description="Original filename of the ingested document")
    source_sha256: str = Field(..., description="Cryptographic SHA-256 hash of original document")
    source_page: Optional[int] = Field(default=None, description="Primary evidence page")
    extraction_method: str = Field(default="table_parser", description="Extractor method applied")

    missing_fields: List[str] = Field(default_factory=list, description="Required fields not found in evidence")
    conflict_detected: bool = Field(default=False, description="True if conflict between user and document exists")
    conflict_details: Optional[str] = Field(default=None, description="Details of the conflict")

    can_calculate_corrosion_rate: bool = Field(default=False, description="True if nominal, current, and elapsed time exist")
    can_calculate_remaining_life: bool = Field(default=False, description="True if corrosion rate and retirement limit exist")


def _clean_header(header: Any) -> str:
    """Normalize column header string for robust matching."""
    if header is None:
        return ""
    text = str(header).strip().lower()
    text = re.sub(r"[\s\-_]+", " ", text)
    return text


def _parse_float(val: Any) -> Optional[float]:
    """Safely extract float from numeric strings or numbers."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    text = str(val).strip().lower()
    # Remove common units and formatting
    text = re.sub(r"[^\d.\-]", "", text)
    if not text or text == "-" or text == ".":
        return None
    try:
        f = float(text)
        return f if f > 0 else None
    except ValueError:
        return None


def _find_column_index(headers: List[str], aliases: List[str]) -> Optional[int]:
    """Find index of column header matching any alias."""
    norm_headers = [_clean_header(h) for h in headers]
    for idx, h in enumerate(norm_headers):
        for alias in aliases:
            # Match exact or clean substring
            if alias == h or (alias in h and len(h) <= len(alias) + 8):
                return idx
    # Fallback to loose containment
    for idx, h in enumerate(norm_headers):
        for alias in aliases:
            if alias in h:
                return idx
    return None


class EngineeringEvidenceExtractor:
    """
    Extracts deterministic engineering evidence from NormalizedDocument instances.
    Connects ingestion tables and text to downstream calculation contracts.
    """

    def extract(
        self,
        norm_doc: NormalizedDocument,
        user_component_id: Optional[str] = None,
        user_elapsed_years: Optional[float] = None,
        user_min_thickness: Optional[float] = None,
        vision_tags: Optional[List[str]] = None,
        is_demo_preset: bool = False,
        user_equipment_id: Optional[str] = None,
        user_elapsed_time_years: Optional[float] = None,
        user_minimum_required_thickness_mm: Optional[float] = None,
    ) -> EngineeringEvidence:
        """
        Extract structured evidence from normalized document tables and text.
        """
        user_component_id = user_component_id or user_equipment_id
        user_elapsed_years = user_elapsed_years if user_elapsed_years is not None else user_elapsed_time_years
        user_min_thickness = user_min_thickness if user_min_thickness is not None else user_minimum_required_thickness_mm

        evidence = EngineeringEvidence(
            source_filename=norm_doc.original_filename,
            source_sha256=norm_doc.sha256,
            extraction_method=norm_doc.extraction_method,
        )

        # ── 1. Equipment Tag Resolution & Precedence (Finding 3) ─────────────
        table_id = self._extract_equipment_tag_from_table(norm_doc)
        body_id = self._extract_equipment_tag_from_body(norm_doc)
        meta_id = self._extract_equipment_tag_from_metadata(norm_doc)
        file_id = self._extract_equipment_tag_from_filename(norm_doc)

        # Check for internal document conflict between strong explicit evidence sources
        # (Table/Header evidence vs Document Body text)
        internal_conflict = False
        if table_id and body_id and table_id != body_id:
            internal_conflict = True
            evidence.conflict_detected = True
            evidence.conflict_details = (
                f"Conflicting equipment identity in document evidence: "
                f"table/header specifies '{table_id}' but document body specifies '{body_id}'."
            )
            evidence.equipment_id = table_id
            evidence.equipment_id_source = "DOCUMENT_CONFLICT"

        # Determine document-level equipment ID by strict precedence:
        # 1. Structured table/header
        # 2. Body text
        # 3. Metadata
        # 4. Filename inference (weak final fallback)
        doc_equipment_id: Optional[str] = None
        doc_id_source = "UNKNOWN"
        if table_id:
            doc_equipment_id = table_id
            doc_id_source = "DOCUMENT_TABLE"
        elif body_id:
            doc_equipment_id = body_id
            doc_id_source = "DOCUMENT_BODY"
        elif meta_id:
            doc_equipment_id = meta_id
            doc_id_source = "DOCUMENT_METADATA"
        elif file_id:
            doc_equipment_id = file_id
            doc_id_source = "FILENAME_INFERENCE"

        # Now resolve overall equipment ID against User-Supplied Target (Precedence #1)
        if user_component_id:
            clean_user = user_component_id.strip().upper()
            if internal_conflict:
                evidence.equipment_id = clean_user
                evidence.equipment_id_source = "USER"
            elif doc_equipment_id:
                clean_doc = doc_equipment_id.strip().upper()
                if clean_user != clean_doc and not (is_demo_preset and clean_user == "C-101"):
                    evidence.conflict_detected = True
                    evidence.conflict_details = (
                        f"User specified equipment tag '{clean_user}' but uploaded document specifies '{clean_doc}' "
                        f"(source: {doc_id_source})."
                    )
                    evidence.equipment_id = clean_user
                    evidence.equipment_id_source = "USER"
                else:
                    evidence.equipment_id = clean_user
                    evidence.equipment_id_source = "USER"
            else:
                evidence.equipment_id = clean_user
                evidence.equipment_id_source = "USER"
        else:
            # No user target supplied: use document-derived ID by precedence
            if not internal_conflict:
                if doc_equipment_id:
                    evidence.equipment_id = doc_equipment_id
                    evidence.equipment_id_source = doc_id_source
                elif vision_tags:
                    evidence.equipment_id = vision_tags[0].strip().upper()
                    evidence.equipment_id_source = "VISION"

        # ── 2. Table Gauging Measurement Extraction ─────────────────────────
        all_measurements: List[ExtractedMeasurement] = []

        for table in norm_doc.tables:
            measurements_from_table = self._extract_from_table(table, norm_doc)
            all_measurements.extend(measurements_from_table)

        evidence.measurements = all_measurements

        # ── 3. Deterministic Measurement Selection Rule ──────────────────────
        # Select the critical minimum measured thickness across all gauging points
        valid_measurements = [m for m in all_measurements if m.measured_thickness_mm > 0]
        if valid_measurements:
            # Sort by measured_thickness_mm ascending; first is the critical minimum
            selected = min(valid_measurements, key=lambda m: m.measured_thickness_mm)
            evidence.selected_measurement = selected
            evidence.current_thickness_mm = selected.measured_thickness_mm
            evidence.current_thickness_source = "DOCUMENT_TABLE"
            evidence.source_page = selected.source_page or (table.source_page if norm_doc.tables else 1)

            # Assign nominal thickness from selected measurement or across table
            if selected.nominal_thickness_mm:
                evidence.nominal_thickness_mm = selected.nominal_thickness_mm
                evidence.nominal_thickness_source = "DOCUMENT_TABLE"
            else:
                for m in valid_measurements:
                    if m.nominal_thickness_mm:
                        evidence.nominal_thickness_mm = m.nominal_thickness_mm
                        evidence.nominal_thickness_source = "DOCUMENT_TABLE"
                        break

        # Fallback: scan document text if table didn't yield nominal or current
        if evidence.current_thickness_mm is None or evidence.nominal_thickness_mm is None:
            text_nom, text_act = self._scan_text_for_thickness(norm_doc)
            if evidence.nominal_thickness_mm is None and text_nom:
                evidence.nominal_thickness_mm = text_nom
                evidence.nominal_thickness_source = "DOCUMENT_TEXT"
            if evidence.current_thickness_mm is None and text_act:
                evidence.current_thickness_mm = text_act
                evidence.current_thickness_source = "DOCUMENT_TEXT"
                if not evidence.selected_measurement:
                    evidence.selected_measurement = ExtractedMeasurement(
                        cml_tag=f"{evidence.equipment_id or 'EQUIP'}-T1",
                        location_desc="Extracted from document text body",
                        nominal_thickness_mm=evidence.nominal_thickness_mm,
                        measured_thickness_mm=text_act,
                        provenance=norm_doc.tables[0].provenance if norm_doc.tables else DocumentProvenance(
                            source_filename=norm_doc.original_filename,
                            source_sha256=norm_doc.sha256,
                            page_number=1,
                        ),
                    )

        # ── 4. Elapsed Time Determination (Documented Precedence) ────────────
        # 1. User-supplied value
        if user_elapsed_years is not None and user_elapsed_years > 0:
            evidence.elapsed_time_years = float(user_elapsed_years)
            evidence.elapsed_time_source = "USER"
        else:
            # 2. Document-derived interval from dates or table headers
            doc_elapsed = self._extract_elapsed_years_from_doc(norm_doc, all_measurements)
            if doc_elapsed is not None and doc_elapsed > 0:
                evidence.elapsed_time_years = doc_elapsed
                evidence.elapsed_time_source = "DOCUMENT"
            # 3. Approved demo preset or verified demo fixture ONLY (equipment_id alone must NEVER activate demo defaults)
            elif is_demo_preset or norm_doc.sha256 == DEMO_C101_PDF_SHA256:
                evidence.elapsed_time_years = 5.0
                evidence.elapsed_time_source = "DEMO_PRESET" if is_demo_preset else "APPROVED_CONFIG"
            else:
                evidence.elapsed_time_years = None
                evidence.elapsed_time_source = "NONE"

        # ── 5. Minimum Required Thickness Determination (Precedence) ────────
        # 1. User-supplied value
        if user_min_thickness is not None and user_min_thickness > 0:
            evidence.minimum_required_thickness_mm = float(user_min_thickness)
            evidence.minimum_thickness_source = "USER"
        else:
            # 2. Document-derived retirement threshold
            doc_min_t = self._extract_minimum_required_thickness_from_doc(norm_doc)
            if doc_min_t is not None and doc_min_t > 0:
                evidence.minimum_required_thickness_mm = doc_min_t
                evidence.minimum_thickness_source = "DOCUMENT"
            # 3. Approved demo preset or verified demo fixture ONLY (equipment_id alone must NEVER activate demo defaults)
            elif is_demo_preset or norm_doc.sha256 == DEMO_C101_PDF_SHA256:
                evidence.minimum_required_thickness_mm = 8.0
                evidence.minimum_thickness_source = "DEMO_PRESET" if is_demo_preset else "APPROVED_CONFIG"
            else:
                evidence.minimum_required_thickness_mm = None
                evidence.minimum_thickness_source = "NONE"

        # ── 6. Inspection Subject Description ────────────────────────────────
        if evidence.selected_measurement and evidence.selected_measurement.location_desc:
            evidence.inspection_subject = (
                f"{evidence.equipment_id or 'Equipment'} {evidence.selected_measurement.location_desc}"
            )
        else:
            evidence.inspection_subject = f"Equipment {evidence.equipment_id or 'Inspection'} Wall Survey"

        # ── 7. Evidence Sufficiency Evaluation ───────────────────────────────
        missing = []
        if evidence.nominal_thickness_mm is None:
            missing.append("nominal_thickness_mm")
        if evidence.current_thickness_mm is None:
            missing.append("current_thickness_mm")
        if evidence.elapsed_time_years is None:
            missing.append("elapsed_time_years")

        evidence.missing_fields = missing
        evidence.can_calculate_corrosion_rate = len(missing) == 0

        # Remaining life requires minimum required thickness
        evidence.can_calculate_remaining_life = (
            evidence.can_calculate_corrosion_rate
            and evidence.minimum_required_thickness_mm is not None
        )

        return evidence

    def _extract_from_table(
        self, table: ParsedTable, norm_doc: NormalizedDocument
    ) -> List[ExtractedMeasurement]:
        """Extract wall thickness gauging rows from a ParsedTable."""
        measurements: List[ExtractedMeasurement] = []
        if not table.headers or not table.rows:
            return measurements

        headers = table.headers
        nom_col = _find_column_index(headers, NOMINAL_ALIASES)
        act_col = _find_column_index(headers, CURRENT_ALIASES)
        loc_col = _find_column_index(headers, LOCATION_ALIASES)
        date_col = _find_column_index(headers, DATE_ALIASES)

        if act_col is None:
            # If no explicit actual/current column, table is not a thickness survey
            return measurements

        # Check if headers themselves indicate years (e.g. "Baseline (2021)", "Current (2026)")
        header_dates = self._inspect_headers_for_dates(headers)

        for r_idx, row in enumerate(table.rows):
            if not row or len(row) <= act_col:
                continue

            act_val = _parse_float(row[act_col])
            if act_val is None or act_val <= 0:
                continue

            nom_val = _parse_float(row[nom_col]) if nom_col is not None and len(row) > nom_col else None
            loc_val = str(row[loc_col]).strip() if loc_col is not None and len(row) > loc_col and row[loc_col] else f"PT-{r_idx+1}"
            date_val = str(row[date_col]).strip() if date_col is not None and len(row) > date_col and row[date_col] else header_dates.get("current_date")

            cml_tag = loc_val
            loc_desc = loc_val
            if " - " in loc_val:
                parts = loc_val.split(" - ", 1)
                cml_tag = parts[0].strip()
                loc_desc = parts[1].strip()
            elif ":" in loc_val:
                parts = loc_val.split(":", 1)
                cml_tag = parts[0].strip()
                loc_desc = parts[1].strip()

            prov = DocumentProvenance(
                source_filename=norm_doc.original_filename,
                source_sha256=norm_doc.sha256,
                page_number=table.source_page or 1,
                sheet_name=table.sheet_name,
                row_index=r_idx,
                col_index=act_col,
            )

            loss = round(nom_val - act_val, 4) if nom_val is not None else None

            measurements.append(
                ExtractedMeasurement(
                    cml_tag=cml_tag,
                    location_desc=loc_desc,
                    nominal_thickness_mm=nom_val,
                    measured_thickness_mm=act_val,
                    loss_mm=loss,
                    measurement_date=date_val,
                    source_page=table.source_page,
                    provenance=prov,
                )
            )

        return measurements

    def _inspect_headers_for_dates(self, headers: List[str]) -> Dict[str, Optional[str]]:
        """Inspect column headers for year references like 'Baseline (2021)'."""
        dates: Dict[str, Optional[str]] = {"baseline_year": None, "current_year": None}
        for h in headers:
            text = _clean_header(h)
            m_year = re.search(r"\b(20\d\d)\b", text)
            if m_year:
                year = m_year.group(1)
                if any(k in text for k in ["base", "init", "nom", "start"]):
                    dates["baseline_year"] = year
                elif any(k in text for k in ["curr", "act", "meas", "survey"]):
                    dates["current_year"] = year
        return dates

    def _extract_equipment_tag_from_table(self, norm_doc: NormalizedDocument) -> Optional[str]:
        """Extract equipment ID from structured table headers or columns."""
        for table in norm_doc.tables:
            # 1. Check if table has an explicit equipment / tag column
            eq_col = _find_column_index(table.headers, ["equipment", "equipment_id", "equipment_tag", "tag_no", "tag", "component", "component_id"])
            if eq_col is not None and table.rows:
                for row in table.rows:
                    if len(row) > eq_col and row[eq_col]:
                        val = str(row[eq_col]).strip().upper()
                        m = re.search(r"([A-Z]{1,3})[-_]?(\d{2,4}[A-Z]?)", val)
                        if m and m.group(1) not in ("SOP", "API", "MRPL"):
                            return f"{m.group(1)}-{m.group(2)}"

            # 2. Check if table headers themselves contain an explicit equipment tag
            for h in (table.headers or []):
                h_str = str(h).strip().upper()
                m_hdr = re.search(r"(?:EQUIPMENT|TAG|COMPONENT|VESSEL|COLUMN|PUMP)?\s*[:=\-]?\s*([A-Z]{1,3})[-_](\d{2,4}[A-Z]?)", h_str)
                if m_hdr and m_hdr.group(1) not in ("SOP", "API", "MRPL", "CML", "PT"):
                    return f"{m_hdr.group(1)}-{m_hdr.group(2)}"

            # 3. Check point/cml column for component prefix (e.g. 'P-204-01' -> 'P-204')
            loc_col = _find_column_index(table.headers, LOCATION_ALIASES)
            if loc_col is not None and table.rows:
                for row in table.rows:
                    if len(row) > loc_col and row[loc_col]:
                        val = str(row[loc_col]).strip().upper()
                        m_pt = re.search(r"([A-Z]{1,3})[-_](\d{2,4})[-_]\w+", val)
                        if m_pt and m_pt.group(1) not in ("SOP", "API", "MRPL", "CML"):
                            return f"{m_pt.group(1)}-{m_pt.group(2)}"
        return None

    def _extract_equipment_tag_from_body(self, norm_doc: NormalizedDocument) -> Optional[str]:
        """Extract explicit equipment ID from document body text."""
        corpus_sample = ""
        for page in norm_doc.pages[:3]:
            corpus_sample += " " + page.text
        for section in norm_doc.sections[:5]:
            corpus_sample += " " + section.text
        for table in norm_doc.tables:
            for row in table.rows:
                row_text = " ".join(str(c) for c in row if c)
                if any(k in row_text.upper() for k in ["EQUIPMENT", "COMPONENT", "CIRCUIT", "VESSEL", "COLUMN", "PUMP", "TAG"]):
                    corpus_sample += " " + row_text

        match = re.search(
            r"\b(?:EQUIPMENT|COMPONENT|CIRCUIT|VESSEL|COLUMN|PUMP|TAG)(?:\s+ID|\s+TAG|\s+NO|\s+NUMBER)?\s*[:=\-]?\s*([A-Z]{1,3})[-_]?(\d{2,4}[A-Z]?)\b",
            corpus_sample,
            re.IGNORECASE,
        )
        if match and match.group(1).upper() not in ("SOP", "API", "MRPL"):
            return f"{match.group(1).upper()}-{match.group(2).upper()}"
        return None

    def _extract_equipment_tag_from_metadata(self, norm_doc: NormalizedDocument) -> Optional[str]:
        """Extract equipment ID from document metadata."""
        if "equipment_id" in norm_doc.metadata and norm_doc.metadata["equipment_id"]:
            return str(norm_doc.metadata["equipment_id"]).strip().upper()
        return None

    def _extract_equipment_tag_from_filename(self, norm_doc: NormalizedDocument) -> Optional[str]:
        """Extract equipment tag inference from filename (weak fallback)."""
        fn_match = re.search(r"(?:^|[\W_])([A-Z]{1,3})[-_]?(\d{2,4}[A-Z]?)(?:[\W_]|$)", norm_doc.original_filename.upper())
        if fn_match:
            prefix, num = fn_match.group(1), fn_match.group(2)
            tag = f"{prefix}-{num}"
            if tag not in ("SOP-001", "MRPL-001", "API-570", "API-510"):
                return tag
        return None

    def _extract_equipment_tag_from_doc(self, norm_doc: NormalizedDocument) -> Optional[str]:
        """
        Extract equipment tag following strict evidence precedence:
        1. Structured table/header
        2. Document body text
        3. Metadata
        4. Filename inference (weak final fallback)
        """
        table_id = self._extract_equipment_tag_from_table(norm_doc)
        if table_id:
            return table_id
        body_id = self._extract_equipment_tag_from_body(norm_doc)
        if body_id:
            return body_id
        meta_id = self._extract_equipment_tag_from_metadata(norm_doc)
        if meta_id:
            return meta_id
        file_id = self._extract_equipment_tag_from_filename(norm_doc)
        if file_id:
            return file_id
        return None

    def _scan_text_for_thickness(self, norm_doc: NormalizedDocument) -> Tuple[Optional[float], Optional[float]]:
        """Fallback: regex scan of text paragraphs for nominal and measured thickness."""
        full_text = ""
        for p in norm_doc.pages:
            full_text += " " + p.text
        for s in norm_doc.sections:
            full_text += " " + s.text

        nom = None
        act = None

        m_nom = re.search(r"(?:nominal|baseline|t_initial)\s*(?:thickness)?\s*[:=]?\s*(\d+(?:\.\d+)?)\s*mm", full_text, re.IGNORECASE)
        if m_nom:
            nom = _parse_float(m_nom.group(1))

        m_act = re.search(r"(?:actual|current|measured|lowest|minimum\s+measured)\s*(?:thickness)?\s*[:=]?\s*(\d+(?:\.\d+)?)\s*mm", full_text, re.IGNORECASE)
        if m_act:
            act = _parse_float(m_act.group(1))

        return nom, act

    def _extract_elapsed_years_from_doc(
        self, norm_doc: NormalizedDocument, measurements: List[ExtractedMeasurement]
    ) -> Optional[float]:
        """Extract elapsed operating interval in years from dates or text."""
        # 1. Check header year differences
        for table in norm_doc.tables:
            dates = self._inspect_headers_for_dates(table.headers)
            if dates["baseline_year"] and dates["current_year"]:
                try:
                    diff = float(dates["current_year"]) - float(dates["baseline_year"])
                    if diff > 0:
                        return diff
                except ValueError:
                    pass

        # 2. Check explicit regex in text: "elapsed time = X years", "interval of X years", "over X years"
        full_text = ""
        for p in norm_doc.pages[:2]:
            full_text += " " + p.text
        for s in norm_doc.sections[:3]:
            full_text += " " + s.text

        m_int = re.search(r"(?:elapsed\s+time|operating\s+interval|service\s+interval|over\s+a\s+period\s+of)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:years|year|yrs|yr)", full_text, re.IGNORECASE)
        if m_int:
            val = _parse_float(m_int.group(1))
            if val and val > 0:
                return val

        # 3. Check date differences in measurements
        dates = [m.measurement_date for m in measurements if m.measurement_date]
        years = []
        for d in dates:
            m_yr = re.search(r"\b(20\d\d)\b", d)
            if m_yr:
                years.append(int(m_yr.group(1)))
        if years and max(years) != min(years):
            diff = float(max(years) - min(years))
            if diff > 0:
                return diff

        return None

    def _extract_minimum_required_thickness_from_doc(self, norm_doc: NormalizedDocument) -> Optional[float]:
        """Extract minimum required retirement thickness limit from document tables/text."""
        # 1. Check table columns
        for table in norm_doc.tables:
            min_col = _find_column_index(
                table.headers,
                ["minimum", "minimum_mm", "min_req", "min_req_mm", "t_min", "tmin", "retirement", "retirement_mm"]
            )
            if min_col is not None and table.rows:
                for row in table.rows:
                    if len(row) > min_col:
                        val = _parse_float(row[min_col])
                        if val and val > 0:
                            return val

        # 2. Check text regex
        full_text = ""
        for p in norm_doc.pages:
            full_text += " " + p.text
        for s in norm_doc.sections:
            full_text += " " + s.text

        m_min = re.search(r"(?:retirement|minimum\s+allowable|minimum\s+required|t_min|tmin)\s*(?:wall\s+thickness|thickness)?\s*[:=]?\s*(\d+(?:\.\d+)?)(?:\s*mm)?", full_text, re.IGNORECASE)
        if m_min:
            return _parse_float(m_min.group(1))

        return None
