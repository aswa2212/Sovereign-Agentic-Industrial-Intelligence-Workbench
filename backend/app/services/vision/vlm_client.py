"""
SIH26117 — Local Vision / VLM Provider Abstraction
Decouples visual inference from specific model weights and hardware profiles.
Integrates through ModelManager role 'vision' without embedding model IDs in business logic.
"""

import base64
import logging
from typing import Any, Dict, List, Optional

try:
    from app.services.ingestion.models import DocumentProvenance
    from app.services.model_manager.manager import ModelManager
    from app.services.vision.base import (
        BoundingBox,
        SchematicAnalysisResult,
        VisionModelUnavailableError,
        VisionProvider,
        VisualFinding,
        VisualFindingType,
    )
except ImportError:
    from backend.app.services.ingestion.models import DocumentProvenance
    from backend.app.services.model_manager.manager import ModelManager
    from backend.app.services.vision.base import (
        BoundingBox,
        SchematicAnalysisResult,
        VisionModelUnavailableError,
        VisionProvider,
        VisualFinding,
        VisualFindingType,
    )

logger = logging.getLogger(__name__)

PID_ANALYSIS_SYSTEM_PROMPT = """You are a certified Refinery P&ID and Engineering Drawing Inspection Specialist for Mangalore Refinery and Petrochemicals Limited (MRPL).
Analyze the provided engineering schematic or technical drawing carefully.
Extract all visible equipment identifiers, instrument tags, line numbers, and engineering notes.

Output strictly valid JSON conforming to this schema:
{
  "summary": "High-level description of drawing contents and unit operation",
  "equipment_tags": ["C-101", "P-101A"],
  "instrument_tags": ["PT-101", "FT-202", "TT-301"],
  "line_ids": ["10-CDU-0101-CS150"],
  "findings": [
    {
      "finding_type": "equipment_tag" | "instrument_tag" | "line_id" | "valve_symbol" | "spec_note",
      "label": "standardized tag string",
      "text": "text as appears on drawing",
      "confidence": 0.95,
      "evidence": "justification/location description",
      "bounding_box": {
        "x_min": 0.1, "y_min": 0.2, "x_max": 0.25, "y_max": 0.35
      }
    }
  ],
  "drawing_metadata": {
    "sheet_title": "string or unknown",
    "unit": "string or unknown"
  }
}
Do not fabricate detections. If any tag is ambiguous, assign confidence < 0.70 and note the uncertainty in evidence."""


class ModelManagerVisionProvider(VisionProvider):
    """
    Vision provider that coordinates with ModelManager using the abstract 'vision' role.
    Respects hardware constraints (RTX 4060 8 GB VRAM) by utilizing serial model loading.
    """

    def __init__(self, model_manager: ModelManager) -> None:
        self.model_manager = model_manager

    def is_available(self) -> bool:
        """Verify that the model manager is initialized and has a configured vision role."""
        try:
            tier = self.model_manager.get_tier_config()
            return tier.get_model("vision") is not None
        except Exception:
            return False

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: Optional[str] = None,
        provenance: Optional[DocumentProvenance] = None,
    ) -> SchematicAnalysisResult:
        """
        Execute visual inference on an engineering drawing or scan using the local VLM.
        """
        if not self.is_available():
            raise VisionModelUnavailableError(
                "No local vision model is configured or available in the active hardware tier."
            )

        prov = provenance or DocumentProvenance(
            source_filename="drawing_artifact",
            source_sha256="unknown_hash",
        )

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        user_prompt = prompt or "Identify all equipment, instrument tags, and piping lines in this schematic."

        try:
            # ModelManager handles serial loading/unloading and semaphore control
            structured_data = await self.model_manager.generate_structured(
                role="vision",
                prompt=user_prompt,
                system_prompt=PID_ANALYSIS_SYSTEM_PROMPT,
                temperature=0.1,
                images=[b64_image],
            )
        except Exception as e:
            logger.error("Vision VLM execution failed: %s", str(e))
            raise VisionModelUnavailableError(
                f"Local vision model execution failed: {str(e)}"
            ) from e

        return self._parse_structured_response(structured_data, prov)

    async def identify_tags(
        self,
        image_bytes: bytes,
        provenance: Optional[DocumentProvenance] = None,
    ) -> List[VisualFinding]:
        """Specialized tag identification query."""
        res = await self.analyze_image(
            image_bytes=image_bytes,
            prompt="Extract all P&ID instrument tags, equipment identifiers, and line specifications.",
            provenance=provenance,
        )
        return res.findings

    def _parse_structured_response(
        self,
        data: Dict[str, Any],
        provenance: DocumentProvenance,
    ) -> SchematicAnalysisResult:
        summary = str(data.get("summary", "Schematic visual analysis completed."))

        def _extract_tag_str(item: Any) -> str:
            if isinstance(item, str):
                return item.strip()
            if isinstance(item, dict):
                for k in ("tag", "label", "id", "name", "equipment", "instrument", "text"):
                    val = item.get(k)
                    if val and isinstance(val, (str, int, float)):
                        return str(val).strip()
            return str(item).strip() if item is not None else ""

        cand_eq = [_extract_tag_str(x) for x in data.get("equipment_tags", []) if _extract_tag_str(x)]
        cand_inst = [_extract_tag_str(x) for x in data.get("instrument_tags", []) if _extract_tag_str(x)]
        cand_lines = [_extract_tag_str(x) for x in data.get("line_ids", []) if _extract_tag_str(x)]
        all_tags = list(dict.fromkeys(cand_eq + cand_inst + cand_lines))

        raw_findings = data.get("findings", [])
        findings: List[VisualFinding] = []

        for item in raw_findings:
            if not isinstance(item, dict):
                if isinstance(item, str) and item.strip():
                    findings.append(
                        VisualFinding(
                            finding_type=VisualFindingType.UNKNOWN,
                            label=item.strip(),
                            text=item.strip(),
                            confidence=0.75,
                            provenance=provenance,
                            evidence="Direct text extraction from visual inspection",
                        )
                    )
                continue

            raw_type = str(item.get("finding_type", "")).lower()
            if not raw_type or raw_type == "unknown":
                if "equipment" in item:
                    raw_type = "equipment_tag"
                elif "instrument" in item:
                    raw_type = "instrument_tag"
                elif "line" in item:
                    raw_type = "line_id"

            try:
                finding_type = VisualFindingType(raw_type)
            except ValueError:
                finding_type = VisualFindingType.UNKNOWN

            bbox = None
            b = item.get("bounding_box") or (item if all(k in item for k in ("x_min", "y_min", "x_max", "y_max")) else None)
            if isinstance(b, dict):
                try:
                    x0 = max(0.0, min(1.0, float(b.get("x_min", 0.0))))
                    y0 = max(0.0, min(1.0, float(b.get("y_min", 0.0))))
                    x1 = max(0.0, min(1.0, float(b.get("x_max", 1.0))))
                    y1 = max(0.0, min(1.0, float(b.get("y_max", 1.0))))
                    if x1 >= x0 and y1 >= y0:
                        bbox = BoundingBox(x_min=x0, y_min=y0, x_max=x1, y_max=y1)
                except (ValueError, TypeError):
                    bbox = None

            label_val = _extract_tag_str(item.get("label") or item.get("tag") or item.get("name") or item.get("equipment") or item.get("instrument") or item.get("id") or "UNTAGGED")
            text_val = str(item.get("text", label_val))
            conf_val = float(item.get("confidence", 0.80))
            conf_clamped = max(0.0, min(1.0, conf_val))

            findings.append(
                VisualFinding(
                    finding_type=finding_type,
                    label=label_val,
                    text=text_val,
                    confidence=conf_clamped,
                    bounding_box=bbox,
                    provenance=provenance,
                    evidence=str(item.get("evidence", "Local VLM visual detection")),
                    attributes={k: v for k, v in item.items() if k not in ("finding_type", "label", "text", "confidence", "bounding_box", "evidence")},
                )
            )

        # If findings list was empty but candidate equipment/instruments were found, populate findings
        if not findings and (cand_eq or cand_inst or cand_lines):
            for eq in cand_eq:
                findings.append(VisualFinding(
                    finding_type=VisualFindingType.EQUIPMENT_TAG,
                    label=eq,
                    text=eq,
                    confidence=0.85,
                    provenance=provenance,
                    evidence="Identified from VLM equipment tags",
                ))
            for inst in cand_inst:
                findings.append(VisualFinding(
                    finding_type=VisualFindingType.INSTRUMENT_TAG,
                    label=inst,
                    text=inst,
                    confidence=0.85,
                    provenance=provenance,
                    evidence="Identified from VLM instrument tags",
                ))
            for ln in cand_lines:
                findings.append(VisualFinding(
                    finding_type=VisualFindingType.LINE_ID,
                    label=ln,
                    text=ln,
                    confidence=0.80,
                    provenance=provenance,
                    evidence="Identified from VLM line tags",
                ))

        active_model = self.model_manager.get_tier_config().get_model("vision")
        model_name = active_model.model_tag if active_model else "local_vision_model"

        return SchematicAnalysisResult(
            findings=findings,
            summary=summary,
            candidate_tags=all_tags,
            equipment_tags=cand_eq,
            instrument_tags=cand_inst,
            drawing_metadata=data.get("drawing_metadata", {}),
            provenance=provenance,
            status="success",
            model_used=model_name,
        )


class MockVisionProvider(VisionProvider):
    """
    Deterministic mock vision provider for offline testing and hardware-free CI.
    Simulates high-accuracy visual understanding over MRPL synthetic schematics.
    """

    def __init__(self, predefined_findings: Optional[List[VisualFinding]] = None) -> None:
        self.predefined_findings = predefined_findings

    def is_available(self) -> bool:
        return True

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: Optional[str] = None,
        provenance: Optional[DocumentProvenance] = None,
    ) -> SchematicAnalysisResult:
        prov = provenance or DocumentProvenance(
            source_filename="mock_drawing.png",
            source_sha256="mock_drawing_sha256_00000000000000000000",
            page_number=1,
        )

        if self.predefined_findings:
            findings = self.predefined_findings
        else:
            findings = [
                VisualFinding(
                    finding_type=VisualFindingType.EQUIPMENT_TAG,
                    label="C-101",
                    text="C-101 ATMOSPHERIC COLUMN",
                    confidence=0.96,
                    bounding_box=BoundingBox(x_min=0.20, y_min=0.15, x_max=0.45, y_max=0.75),
                    provenance=prov,
                    evidence="Large vertical distillation vessel symbol in center of sheet",
                ),
                VisualFinding(
                    finding_type=VisualFindingType.INSTRUMENT_TAG,
                    label="PT-101",
                    text="PT-101",
                    confidence=0.94,
                    bounding_box=BoundingBox(x_min=0.48, y_min=0.30, x_max=0.55, y_max=0.38),
                    provenance=prov,
                    evidence="Circular instrument bubble attached to column overhead vapor line",
                ),
                VisualFinding(
                    finding_type=VisualFindingType.INSTRUMENT_TAG,
                    label="FT-202",
                    text="FT-202",
                    confidence=0.91,
                    bounding_box=BoundingBox(x_min=0.10, y_min=0.50, x_max=0.18, y_max=0.58),
                    provenance=prov,
                    evidence="Orifice flow transmitter symbol on feed line",
                ),
                VisualFinding(
                    finding_type=VisualFindingType.LINE_ID,
                    label="10-CDU-0101-CS150",
                    text='10"-CDU-0101-CS150',
                    confidence=0.89,
                    bounding_box=BoundingBox(x_min=0.25, y_min=0.80, x_max=0.60, y_max=0.85),
                    provenance=prov,
                    evidence="Crude distillation unit bottom residue line annotation",
                ),
            ]

        eq_tags = [f.label for f in findings if f.finding_type == VisualFindingType.EQUIPMENT_TAG]
        inst_tags = [f.label for f in findings if f.finding_type == VisualFindingType.INSTRUMENT_TAG]
        all_tags = [f.label for f in findings]

        return SchematicAnalysisResult(
            findings=findings,
            summary="MRPL Crude Distillation Unit P&ID: Column C-101 with instrumentation PT-101 and FT-202.",
            candidate_tags=all_tags,
            equipment_tags=eq_tags,
            instrument_tags=inst_tags,
            drawing_metadata={"sheet_title": "CDU-101 Main Fractionation P&ID", "unit": "CDU"},
            provenance=prov,
            status="success",
            model_used="mock_vision_engine",
        )

    async def identify_tags(
        self,
        image_bytes: bytes,
        provenance: Optional[DocumentProvenance] = None,
    ) -> List[VisualFinding]:
        res = await self.analyze_image(image_bytes, provenance=provenance)
        return res.findings


class VisionEngine:
    """
    High-level orchestrator for visual understanding and VLM inference.
    """

    def __init__(self, provider: VisionProvider) -> None:
        self.provider = provider

    def is_ready(self) -> bool:
        """Check if vision provider is available."""
        return self.provider.is_available()

    async def analyze_schematic(
        self,
        image_bytes: bytes,
        provenance: Optional[DocumentProvenance] = None,
    ) -> SchematicAnalysisResult:
        """Analyze schematic image using configured vision provider."""
        return await self.provider.analyze_image(image_bytes, provenance=provenance)
