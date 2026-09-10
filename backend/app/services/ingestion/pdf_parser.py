"""
SIH26117 — Digital PDF Parser Module
Parses PDF documents using pypdf and pdfplumber.
Extracts per-page text, metadata, tables, detects scanned pages (NEEDS_OCR),
and applies a safe heuristic for engineering schematics/drawings.
"""

import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pypdf
import pdfplumber

try:
    from app.services.ingestion.exceptions import InvalidDocumentError
    from app.services.ingestion.models import (
        DocumentPage,
        DocumentProvenance,
        ExtractionStatus,
        ParsedTable,
    )
    from app.services.ingestion.table_extractor import extract_tables_from_pdf_page
except ImportError:
    from backend.app.services.ingestion.exceptions import InvalidDocumentError
    from backend.app.services.ingestion.models import (
        DocumentPage,
        DocumentProvenance,
        ExtractionStatus,
        ParsedTable,
    )
    from backend.app.services.ingestion.table_extractor import extract_tables_from_pdf_page

# Minimum character count to consider a page as containing native digital text
SCANNED_PAGE_CHAR_THRESHOLD = 40


def evaluate_drawing_heuristic(
    page_width: float,
    page_height: float,
    char_count: int,
    image_count: int,
    curve_count: int,
) -> bool:
    """
    Safe heuristic to identify candidate engineering schematics or P&IDs:
    1. Large engineering sheet dimensions (width > 800 or aspect ratio > 1.35)
    2. Low text density relative to page area (< 250 characters)
    3. High vector curve / line density (> 30 curves/lines) or embedded schematic image
    """
    aspect_ratio = (page_width / page_height) if page_height > 0 else 1.0
    is_wide = aspect_ratio > 1.35 or page_width > 800 or page_height > 800

    if is_wide and char_count < 250 and (curve_count > 30 or image_count > 0):
        return True
    return False


class PDFParser:
    """
    Extracts text, metadata, and tables from digital PDF documents.
    Operates strictly offline without external OCR or vision calls.
    """

    def parse(
        self,
        content: bytes,
        sha256: str,
        filename: str,
    ) -> Tuple[List[DocumentPage], List[ParsedTable], Dict[str, Any], bool, bool, bool]:
        """
        Parse raw PDF bytes.
        
        Returns:
            Tuple:
            - pages: List[DocumentPage]
            - tables: List[ParsedTable] (all extracted tables)
            - metadata: Dict[str, Any]
            - is_scanned: bool (true if all or majority pages lack text)
            - needs_ocr: bool (true if any page needs OCR)
            - is_drawing: bool (true if any page looks like an engineering drawing)
        """
        # 1. Validate PDF using pypdf reader
        try:
            pypdf_reader = pypdf.PdfReader(io.BytesIO(content))
        except Exception as e:
            raise InvalidDocumentError(
                f"Failed to read PDF structure: {str(e)}",
                details={"filename": filename},
            )

        if pypdf_reader.is_encrypted:
            raise InvalidDocumentError(
                "Encrypted/password-protected PDFs are not supported.",
                details={"filename": filename},
            )

        total_pages = len(pypdf_reader.pages)
        if total_pages == 0:
            raise InvalidDocumentError(
                "Invalid PDF: Document contains 0 pages.",
                details={"filename": filename},
            )

        # 2. Extract Document Metadata
        metadata: Dict[str, Any] = {
            "page_count": total_pages,
            "pdf_version": getattr(pypdf_reader, "pdf_header", "unknown"),
        }
        if pypdf_reader.metadata:
            for k, v in pypdf_reader.metadata.items():
                clean_key = str(k).lstrip("/").lower()
                metadata[clean_key] = str(v)

        # 3. Extract Per-Page Content & Tables using pdfplumber
        pages: List[DocumentPage] = []
        all_tables: List[ParsedTable] = []
        scanned_page_count = 0
        drawing_page_count = 0

        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for idx, page in enumerate(pdf.pages):
                    page_num = idx + 1
                    
                    # Text extraction
                    extracted_text = page.extract_text() or ""
                    cleaned_text = extracted_text.strip()
                    char_count = len(cleaned_text)
                    word_count = len(cleaned_text.split()) if cleaned_text else 0

                    # Inspect graphics/images
                    images_on_page = page.images or []
                    curves_on_page = page.curves or []
                    lines_on_page = page.lines or []
                    has_images = len(images_on_page) > 0
                    total_graphics = len(curves_on_page) + len(lines_on_page)

                    # Extract digital tables
                    page_tables = extract_tables_from_pdf_page(
                        plumber_page=page,
                        page_num=page_num,
                        source_sha256=sha256,
                        source_filename=filename,
                    )
                    all_tables.extend(page_tables)

                    # Determine if page is scanned / lacks native text layer
                    # A page with digital tables or sufficient text is not scanned
                    is_scanned_page = False
                    if char_count == 0:
                        is_scanned_page = True
                    elif char_count < SCANNED_PAGE_CHAR_THRESHOLD and not page_tables and (has_images or total_graphics > 0):
                        is_scanned_page = True

                    if is_scanned_page:
                        scanned_page_count += 1
                        page_status = ExtractionStatus.NEEDS_OCR
                    else:
                        page_status = ExtractionStatus.SUCCESS

                    # Evaluate drawing heuristic
                    page_width = float(page.width or 0)
                    page_height = float(page.height or 0)
                    is_drawing_page = evaluate_drawing_heuristic(
                        page_width=page_width,
                        page_height=page_height,
                        char_count=char_count,
                        image_count=len(images_on_page),
                        curve_count=total_graphics,
                    )
                    if is_drawing_page:
                        drawing_page_count += 1

                    # Page provenance
                    provenance = DocumentProvenance(
                        source_filename=filename,
                        source_sha256=sha256,
                        page_number=page_num,
                    )

                    doc_page = DocumentPage(
                        page_number=page_num,
                        text=cleaned_text,
                        char_count=char_count,
                        word_count=word_count,
                        tables=page_tables,
                        has_images=has_images,
                        is_scanned=is_scanned_page,
                        is_likely_drawing=is_drawing_page,
                        status=page_status,
                        provenance=provenance,
                    )
                    pages.append(doc_page)

        except Exception as e:
            if isinstance(e, InvalidDocumentError):
                raise
            raise InvalidDocumentError(
                f"Error during PDF content extraction: {str(e)}",
                details={"filename": filename},
            )

        is_scanned_doc = scanned_page_count == total_pages or (scanned_page_count > 0 and total_pages <= 2)
        needs_ocr = scanned_page_count > 0
        is_drawing_doc = drawing_page_count > 0

        return pages, all_tables, metadata, is_scanned_doc, needs_ocr, is_drawing_doc
