"""
SIH26117 — Master Document Ingestion Service
Orchestrates validation, hashing, raw storage, format parsing, normalized document assembly,
and processed JSON persistence.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

try:
    from app.core.config import Settings, get_settings
    from app.services.ingestion.csv_parser import CSVParser
    from app.services.ingestion.docx_parser import DOCXParser
    from app.services.ingestion.exceptions import (
        FileTooLargeError,
        IngestionError,
        InvalidDocumentError,
        UnsupportedFileTypeError,
    )
    from app.services.ingestion.file_detector import detect_file_type
    from app.services.ingestion.hasher import compute_sha256_bytes
    from app.services.ingestion.image_parser import ImageParser
    from app.services.ingestion.models import (
        DocumentIngestionResult,
        DocumentPage,
        DocumentSection,
        ExtractionStatus,
        ImageInfo,
        MediaType,
        NormalizedDocument,
        ParsedTable,
        SheetData,
    )
    from app.services.ingestion.pdf_parser import PDFParser
    from app.services.ingestion.storage import StorageManager, sanitize_filename
    from app.services.ingestion.xlsx_parser import XLSXParser
except ImportError:
    from backend.app.core.config import Settings, get_settings
    from backend.app.services.ingestion.csv_parser import CSVParser
    from backend.app.services.ingestion.docx_parser import DOCXParser
    from backend.app.services.ingestion.exceptions import (
        FileTooLargeError,
        IngestionError,
        InvalidDocumentError,
        UnsupportedFileTypeError,
    )
    from backend.app.services.ingestion.file_detector import detect_file_type
    from backend.app.services.ingestion.hasher import compute_sha256_bytes
    from backend.app.services.ingestion.image_parser import ImageParser
    from backend.app.services.ingestion.models import (
        DocumentIngestionResult,
        DocumentPage,
        DocumentSection,
        ExtractionStatus,
        ImageInfo,
        MediaType,
        NormalizedDocument,
        ParsedTable,
        SheetData,
    )
    from backend.app.services.ingestion.pdf_parser import PDFParser
    from backend.app.services.ingestion.storage import StorageManager, sanitize_filename
    from backend.app.services.ingestion.xlsx_parser import XLSXParser


class IngestionService:
    """
    Central pipeline orchestrator for sovereign document ingestion.
    Coordinates cryptographic identity, storage, and format-specific extraction.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.storage = StorageManager(self.settings)
        self.pdf_parser = PDFParser()
        self.docx_parser = DOCXParser()
        self.xlsx_parser = XLSXParser()
        self.csv_parser = CSVParser()
        self.image_parser = ImageParser()

    def ingest_file(
        self,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> DocumentIngestionResult:
        """
        Execute full ingestion pipeline for an uploaded file:
        1. Validate file size against configured ceiling.
        2. Sanitize filename.
        3. Compute deterministic SHA-256 over raw bytes.
        4. Detect content type using magic bytes.
        5. Persist raw artifact with duplicate detection.
        6. Parse format-specific content into normalized models.
        7. Save normalized representation as JSON in processed directory.
        8. Return typed DocumentIngestionResult.
        """
        file_size = len(content)

        # 1. Size Validation
        if file_size > self.settings.max_upload_size_bytes:
            raise FileTooLargeError(
                f"File size ({file_size} bytes) exceeds configured limit of {self.settings.max_upload_size_bytes} bytes.",
                details={
                    "file_size_bytes": file_size,
                    "max_allowed_bytes": self.settings.max_upload_size_bytes,
                    "filename": filename,
                },
            )

        if file_size == 0:
            raise InvalidDocumentError(
                "Uploaded file is completely empty (0 bytes).",
                details={"filename": filename},
            )

        # 2. Filename Sanitization
        safe_name = sanitize_filename(filename)

        # 3. Deterministic SHA-256 computation over original bytes
        sha256 = compute_sha256_bytes(content)

        # 4. Content-aware file type detection
        media_type, ext = detect_file_type(content, safe_name)

        # 5. Persist raw file
        raw_file_path, is_duplicate = self.storage.store_raw_file(
            sha256=sha256,
            filename=safe_name,
            content=content,
        )

        # Compute relative raw path for portability
        try:
            rel_raw_path = str(raw_file_path.relative_to(self.settings.project_root)).replace("\\", "/")
        except ValueError:
            rel_raw_path = str(raw_file_path).replace("\\", "/")

        document_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        # Placeholders for extracted data
        pages: List[DocumentPage] = []
        sections: List[DocumentSection] = []
        sheets: List[SheetData] = []
        tables: List[ParsedTable] = []
        image_info: Optional[ImageInfo] = None
        doc_metadata: Dict[str, Any] = {}
        is_scanned = False
        needs_ocr = False
        is_drawing = False
        doc_status = ExtractionStatus.SUCCESS
        warnings: List[str] = []
        errors: List[str] = []
        extraction_method = "unknown"

        # 6. Dispatch to specific format parser
        try:
            if ext == "pdf":
                extraction_method = "pdfplumber+pypdf"
                pages, tables, doc_metadata, is_scanned, needs_ocr, is_drawing = (
                    self.pdf_parser.parse(content, sha256, safe_name)
                )
                if needs_ocr:
                    doc_status = ExtractionStatus.NEEDS_OCR
                    warnings.append("Document or pages contain scanned images without text; flagged for Phase 5 OCR.")
                if is_drawing:
                    warnings.append("Document matches engineering schematic/drawing heuristic.")

            elif ext == "docx":
                extraction_method = "python-docx"
                sections, tables, doc_metadata = self.docx_parser.parse(
                    content, sha256, safe_name
                )

            elif ext == "xlsx":
                extraction_method = "openpyxl"
                sheets, tables, doc_metadata = self.xlsx_parser.parse(
                    content, sha256, safe_name
                )

            elif ext == "csv":
                extraction_method = "csv-sniffer"
                sheets, tables, doc_metadata = self.csv_parser.parse(
                    content, sha256, safe_name
                )

            elif ext in ("png", "jpg", "jpeg"):
                extraction_method = "pillow"
                image_info, doc_metadata = self.image_parser.parse(
                    content, sha256, safe_name
                )
                needs_ocr = True  # Image files are handed off to Phase 5 for OCR/VLM
                warnings.append("Image artifact ingested; requires Phase 5 Vision/OCR for text extraction.")

        except IngestionError:
            raise
        except Exception as e:
            raise InvalidDocumentError(
                f"Unexpected failure during parsing: {str(e)}",
                details={"filename": safe_name, "format": ext},
            )

        # 7. Construct Normalized Document
        normalized_doc = NormalizedDocument(
            document_id=document_id,
            sha256=sha256,
            original_filename=filename,
            sanitized_filename=safe_name,
            file_extension=ext,
            media_type=media_type,
            size_bytes=file_size,
            raw_path=rel_raw_path,
            created_at=created_at,
            status=doc_status,
            extraction_method=extraction_method,
            metadata=doc_metadata,
            pages=pages,
            sections=sections,
            sheets=sheets,
            tables=tables,
            image_info=image_info,
            is_scanned=is_scanned,
            needs_ocr=needs_ocr,
            is_drawing=is_drawing,
            warnings=warnings,
            errors=errors,
        )

        # 8. Persist Normalized Document JSON
        processed_file_path = self.storage.store_processed_document(
            sha256=sha256,
            document_dict=normalized_doc.model_dump(),
        )

        try:
            rel_processed_path = str(
                processed_file_path.relative_to(self.settings.project_root)
            ).replace("\\", "/")
        except ValueError:
            rel_processed_path = str(processed_file_path).replace("\\", "/")

        normalized_doc.processed_path = rel_processed_path

        # 9. Formulate DocumentIngestionResult
        page_count = len(pages) if pages else (len(sections) if sections else len(sheets))

        summary = {
            "media_type": media_type,
            "format": ext,
            "page_count": page_count,
            "table_count": len(tables),
            "char_count": sum(p.char_count for p in pages) if pages else sum(len(s.text) for s in sections),
            "extraction_method": extraction_method,
        }

        # 9a. Extract structured engineering evidence
        evidence_dict = None
        try:
            from app.services.ingestion.evidence import EngineeringEvidenceExtractor
            ev = EngineeringEvidenceExtractor().extract(normalized_doc)
            evidence_dict = ev.model_dump()
        except Exception:
            evidence_dict = None

        return DocumentIngestionResult(
            document_id=document_id,
            filename=safe_name,
            sha256=sha256,
            media_type=media_type,
            size_bytes=file_size,
            status=doc_status,
            is_scanned=is_scanned,
            needs_ocr=needs_ocr,
            is_drawing=is_drawing,
            page_count=page_count,
            table_count=len(tables),
            is_duplicate=is_duplicate,
            raw_path=rel_raw_path,
            processed_path=rel_processed_path,
            extraction_summary=summary,
            warnings=warnings,
            errors=errors,
            normalized_document=normalized_doc,
            evidence=evidence_dict,
        )

    def get_document_by_sha256(self, sha256: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored normalized document representation by its SHA-256 digest."""
        return self.storage.get_processed_document(sha256)

    def get_raw_file_path(self, sha256: str, filename: str = "") -> Optional[Path]:
        """Retrieve local raw file path by SHA-256."""
        return self.storage.get_raw_file_path(sha256, filename)

    def list_documents(self) -> List[DocumentIngestionResult]:
        """List all successfully ingested documents stored on disk."""
        docs = self.storage.list_processed_documents()
        results = []
        for d in docs:
            try:
                pages = d.get("pages", [])
                tables = d.get("tables", [])
                res = DocumentIngestionResult(
                    document_id=d.get("document_id", d.get("sha256", "")[:12]),
                    filename=d.get("original_filename", d.get("sanitized_filename", "unnamed_document")),
                    sha256=d.get("sha256", ""),
                    media_type=d.get("media_type", "application/pdf"),
                    size_bytes=d.get("size_bytes", 0),
                    status=d.get("status", "success"),
                    is_scanned=d.get("is_scanned", False),
                    needs_ocr=d.get("needs_ocr", False),
                    is_drawing=d.get("is_drawing", False),
                    page_count=len(pages),
                    table_count=len(tables),
                    is_duplicate=False,
                    raw_path=d.get("raw_path", ""),
                    processed_path=d.get("processed_path"),
                    extraction_summary=d.get("metadata", {}),
                    warnings=d.get("warnings", []),
                    errors=d.get("errors", []),
                )
                results.append(res)
            except Exception:
                continue
        return results
