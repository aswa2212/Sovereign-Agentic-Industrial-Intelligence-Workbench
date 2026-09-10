"""
SIH26117 — CSV Ingestion Parser Module
Safely parses CSV files with dialect and encoding detection.
Protects against CSV formula injection and records row-level provenance.
"""

import csv
import io
from typing import Any, Dict, List, Tuple

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


def sanitize_csv_cell(cell: Any) -> Any:
    """
    Sanitize potential CSV formula injection characters (=, +, -, @).
    Treats all cell contents strictly as passive text data.
    """
    val = clean_cell_value(cell)
    if isinstance(val, str) and val.startswith(("=", "+", "-", "@")):
        # Prepend a single quote or preserve as literal string to neutralize execution
        return f"'{val}"
    return val


class CSVParser:
    """Safely extracts tabular data and row provenance from delimited text files."""

    def parse(
        self,
        content: bytes,
        sha256: str,
        filename: str,
    ) -> Tuple[List[SheetData], List[ParsedTable], Dict[str, Any]]:
        """
        Parse raw CSV bytes.

        Returns:
            Tuple: (sheets, tables, metadata)
        """
        # 1. Detect encoding
        decoded_text: str = ""
        detected_encoding = "utf-8"
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                decoded_text = content.decode(enc)
                detected_encoding = enc
                break
            except UnicodeDecodeError:
                continue

        if not decoded_text:
            raise InvalidDocumentError(
                "Unable to decode CSV text with supported encodings (utf-8, latin-1, cp1252).",
                details={"filename": filename},
            )

        # 2. Sniff delimiter
        sample = decoded_text[:4096]
        delimiter = ","
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=",;\t|")
            delimiter = dialect.delimiter
        except Exception:
            # Fall back to comma
            delimiter = ","

        # 3. Read rows
        reader = csv.reader(io.StringIO(decoded_text), delimiter=delimiter)
        raw_rows: List[List[Any]] = []
        for row in reader:
            cleaned = [sanitize_csv_cell(c) for c in row]
            if any(c != "" for c in cleaned):
                raw_rows.append(cleaned)

        if not raw_rows:
            # Empty CSV
            empty_sheet = SheetData(
                sheet_name="CSV_Data",
                sheet_index=0,
                row_count=0,
                col_count=0,
                headers=[],
                tables=[],
                provenance=DocumentProvenance(
                    source_filename=filename,
                    source_sha256=sha256,
                    sheet_name="CSV_Data",
                ),
            )
            return [empty_sheet], [], {"encoding": detected_encoding, "delimiter": delimiter}

        # First row as header
        raw_headers = raw_rows[0]
        headers = [
            str(h).strip() if str(h).strip() else f"Col_{c_idx + 1}"
            for c_idx, h in enumerate(raw_headers)
        ]
        data_rows = raw_rows[1:] if len(raw_rows) > 1 else []

        col_count = len(headers)
        normalized_rows = []
        for row in data_rows:
            if len(row) < col_count:
                row = row + [""] * (col_count - len(row))
            elif len(row) > col_count:
                row = row[:col_count]
            normalized_rows.append(row)

        table_id = f"table_{sha256[:8]}_csv_1"
        provenance = DocumentProvenance(
            source_filename=filename,
            source_sha256=sha256,
            sheet_name="CSV_Data",
        )

        parsed_table = ParsedTable(
            table_id=table_id,
            sheet_name="CSV_Data",
            headers=headers,
            rows=normalized_rows,
            row_count=len(normalized_rows),
            col_count=col_count,
            extraction_method="csv",
            confidence=1.0,
            provenance=provenance,
        )

        sheet_data = SheetData(
            sheet_name="CSV_Data",
            sheet_index=0,
            row_count=len(normalized_rows) + 1,
            col_count=col_count,
            headers=headers,
            tables=[parsed_table],
            provenance=provenance,
        )

        metadata = {
            "encoding": detected_encoding,
            "delimiter": delimiter,
            "row_count": len(raw_rows),
            "column_count": col_count,
        }

        return [sheet_data], [parsed_table], metadata
