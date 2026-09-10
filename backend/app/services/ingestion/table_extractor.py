"""
SIH26117 — Structured Table Extractor
Extracts tabular matrices from digital PDF pages using pdfplumber.
Cleans whitespace, detects column headers, and attaches complete provenance.
"""

from typing import Any, List, Optional
import uuid

try:
    from app.services.ingestion.models import DocumentProvenance, ParsedTable
except ImportError:
    from backend.app.services.ingestion.models import DocumentProvenance, ParsedTable


def clean_cell_value(val: Any) -> Any:
    """Normalize whitespace and strip none values from table cells."""
    if val is None:
        return ""
    if isinstance(val, str):
        # Replace multiple spaces and newlines with single space
        cleaned = " ".join(val.split()).strip()
        return cleaned
    return val


def extract_tables_from_pdf_page(
    plumber_page: Any,
    page_num: int,
    source_sha256: str,
    source_filename: str,
) -> List[ParsedTable]:
    """
    Extract structured tables from a single pdfplumber PDF page.
    Identifies header row, normalizes matrix dimensions, and constructs ParsedTable models.
    """
    extracted_tables: List[ParsedTable] = []
    
    try:
        raw_tables = plumber_page.extract_tables()
    except Exception as e:
        # Gracefully handle internal pdfplumber parsing quirks on complex pages
        return extracted_tables

    if not raw_tables:
        return extracted_tables

    for idx, raw_table in enumerate(raw_tables):
        if not raw_table or len(raw_table) == 0:
            continue

        # Filter out empty rows
        filtered_rows = []
        for row in raw_table:
            cleaned_row = [clean_cell_value(cell) for cell in row]
            # Keep row if at least one cell has content
            if any(cell != "" for cell in cleaned_row):
                filtered_rows.append(cleaned_row)

        if not filtered_rows:
            continue

        # Determine headers: take the first row as headers
        raw_headers = filtered_rows[0]
        headers: List[str] = []
        for col_idx, h in enumerate(raw_headers):
            h_str = str(h).strip() if h is not None else ""
            if not h_str:
                h_str = f"Column_{col_idx + 1}"
            headers.append(h_str)

        # Data rows follow header
        data_rows = filtered_rows[1:] if len(filtered_rows) > 1 else []

        # Standardize row lengths to match header count
        target_cols = len(headers)
        normalized_data_rows = []
        for row in data_rows:
            if len(row) < target_cols:
                row = row + [""] * (target_cols - len(row))
            elif len(row) > target_cols:
                row = row[:target_cols]
            normalized_data_rows.append(row)

        table_id = f"table_{source_sha256[:8]}_p{page_num}_{idx + 1}"

        provenance = DocumentProvenance(
            source_filename=source_filename,
            source_sha256=source_sha256,
            page_number=page_num,
            section_index=idx,
        )

        parsed = ParsedTable(
            table_id=table_id,
            source_page=page_num,
            headers=headers,
            rows=normalized_data_rows,
            row_count=len(normalized_data_rows),
            col_count=target_cols,
            extraction_method="pdfplumber",
            confidence=0.95 if normalized_data_rows else 0.70,
            provenance=provenance,
            warnings=[] if normalized_data_rows else ["Table extracted with headers only"],
        )
        extracted_tables.append(parsed)

    return extracted_tables
