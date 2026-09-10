"""
SIH26117 — XLSX Spreadsheet Parser Module
Extracts sheets, columns, and rows from Excel workbooks safely using openpyxl.
Runs in read-only data mode without evaluating formulas, macros, or external references.
"""

import io
from typing import Any, Dict, List, Tuple
import openpyxl

try:
    from app.services.ingestion.exceptions import InvalidDocumentError
    from app.services.ingestion.models import (
        DocumentProvenance,
        ParsedTable,
        SheetData,
    )
    from app.services.ingestion.table_extractor import clean_cell_value
except ImportError:
    from backend.app.services.ingestion.exceptions import InvalidDocumentError
    from backend.app.services.ingestion.models import (
        DocumentProvenance,
        ParsedTable,
        SheetData,
    )
    from backend.app.services.ingestion.table_extractor import clean_cell_value


class XLSXParser:
    """Parses XLSX workbooks into structured sheets and tables with cell coordinates."""

    def parse(
        self,
        content: bytes,
        sha256: str,
        filename: str,
    ) -> Tuple[List[SheetData], List[ParsedTable], Dict[str, Any]]:
        """
        Parse raw XLSX bytes.

        Returns:
            Tuple: (sheets, tables, metadata)
        """
        try:
            workbook = openpyxl.load_workbook(
                io.BytesIO(content),
                read_only=True,
                data_only=True,  # Never evaluate macros or live formulas
            )
        except Exception as e:
            raise InvalidDocumentError(
                f"Failed to parse XLSX workbook: {str(e)}",
                details={"filename": filename},
            )

        sheets: List[SheetData] = []
        all_tables: List[ParsedTable] = []
        metadata: Dict[str, Any] = {
            "sheet_names": workbook.sheetnames,
            "sheet_count": len(workbook.sheetnames),
        }

        try:
            for s_idx, sheet_name in enumerate(workbook.sheetnames):
                sheet = workbook[sheet_name]
                raw_rows: List[List[Any]] = []

                for row in sheet.iter_rows(values_only=True):
                    cleaned_row = [clean_cell_value(cell) for cell in row]
                    # Retain row if any cell is not empty
                    if any(c != "" for c in cleaned_row):
                        raw_rows.append(cleaned_row)

                if not raw_rows:
                    # Empty sheet
                    empty_sheet = SheetData(
                        sheet_name=sheet_name,
                        sheet_index=s_idx,
                        row_count=0,
                        col_count=0,
                        headers=[],
                        tables=[],
                        provenance=DocumentProvenance(
                            source_filename=filename,
                            source_sha256=sha256,
                            sheet_name=sheet_name,
                        ),
                    )
                    sheets.append(empty_sheet)
                    continue

                # Header is first populated row
                headers = [
                    str(h).strip() if str(h).strip() else f"Col_{c_idx + 1}"
                    for c_idx, h in enumerate(raw_rows[0])
                ]
                data_rows = raw_rows[1:] if len(raw_rows) > 1 else []

                # Normalize row width
                col_count = len(headers)
                normalized_rows = []
                for r in data_rows:
                    if len(r) < col_count:
                        r = r + [""] * (col_count - len(r))
                    elif len(r) > col_count:
                        r = r[:col_count]
                    normalized_rows.append(r)

                table_id = f"table_{sha256[:8]}_sheet_{s_idx + 1}"
                provenance = DocumentProvenance(
                    source_filename=filename,
                    source_sha256=sha256,
                    sheet_name=sheet_name,
                )

                parsed_table = ParsedTable(
                    table_id=table_id,
                    sheet_name=sheet_name,
                    headers=headers,
                    rows=normalized_rows,
                    row_count=len(normalized_rows),
                    col_count=col_count,
                    extraction_method="openpyxl",
                    confidence=1.0,
                    provenance=provenance,
                )
                all_tables.append(parsed_table)

                sheet_data = SheetData(
                    sheet_name=sheet_name,
                    sheet_index=s_idx,
                    row_count=len(normalized_rows) + 1,
                    col_count=col_count,
                    headers=headers,
                    tables=[parsed_table],
                    provenance=provenance,
                )
                sheets.append(sheet_data)

        finally:
            workbook.close()

        metadata["total_tables"] = len(all_tables)
        return sheets, all_tables, metadata
