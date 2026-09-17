"""
SIH26117 — Document Ingestion Strongly Typed Models & Contracts
Defines normalized internal representations, provenance models, and extraction contracts.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExtractionStatus(str, Enum):
    """Execution status of document extraction."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    NEEDS_OCR = "needs_ocr"
    UNSUPPORTED = "unsupported"


class MediaType(str, Enum):
    """Canonical supported MIME types for industrial ingestion."""

    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    CSV = "text/csv"
    PNG = "image/png"
    JPEG = "image/jpeg"


class DocumentProvenance(BaseModel):
    """Source provenance tracking back to original artifact and coordinate."""

    model_config = ConfigDict(protected_namespaces=())

    source_filename: str = Field(..., description="Original filename")
    source_sha256: str = Field(..., description="SHA-256 hash of original raw artifact")
    page_number: Optional[int] = Field(default=None, description="1-based page number for paginated docs")
    section_index: Optional[int] = Field(default=None, description="Section or paragraph index")
    sheet_name: Optional[str] = Field(default=None, description="Spreadsheet sheet name")
    row_index: Optional[int] = Field(default=None, description="Spreadsheet or CSV row index")
    col_index: Optional[int] = Field(default=None, description="Spreadsheet or CSV column index")
    coordinates: Optional[Dict[str, Any]] = Field(default=None, description="Bounding box or spatial coords")


class ParsedTable(BaseModel):
    """Normalized tabular structure extracted from document."""

    model_config = ConfigDict(protected_namespaces=())

    table_id: str = Field(..., description="Unique table identifier")
    source_page: Optional[int] = Field(default=None, description="Page number where table was found")
    sheet_name: Optional[str] = Field(default=None, description="Sheet name if spreadsheet")
    headers: List[str] = Field(default_factory=list, description="Extracted column header names")
    rows: List[List[Any]] = Field(default_factory=list, description="Table rows containing cell values")
    row_count: int = Field(default=0, description="Total number of data rows")
    col_count: int = Field(default=0, description="Total number of columns")
    extraction_method: str = Field(..., description="Parser or tool used (e.g. pdfplumber, docx, openpyxl)")
    confidence: float = Field(default=1.0, description="Extraction confidence score (0.0 to 1.0)")
    provenance: DocumentProvenance = Field(..., description="Traceable provenance anchor")
    warnings: List[str] = Field(default_factory=list, description="Extraction warnings or anomalies")


class DocumentPage(BaseModel):
    """Per-page extracted text, metadata, and tables for paginated documents."""

    model_config = ConfigDict(protected_namespaces=())

    page_number: int = Field(..., description="1-based page number")
    text: str = Field(default="", description="Extracted raw text content")
    char_count: int = Field(default=0, description="Number of extracted characters")
    word_count: int = Field(default=0, description="Number of extracted words")
    tables: List[ParsedTable] = Field(default_factory=list, description="Tables identified on this page")
    has_images: bool = Field(default=False, description="Whether the page contains embedded images")
    is_scanned: bool = Field(default=False, description="Whether the page appears to be a scan with no text layer")
    is_likely_drawing: bool = Field(default=False, description="Heuristic indicator for engineering schematic/drawing")
    status: ExtractionStatus = Field(default=ExtractionStatus.SUCCESS, description="Page extraction status")
    provenance: DocumentProvenance = Field(..., description="Page-level provenance anchor")


class DocumentSection(BaseModel):
    """Section or paragraph extracted from flowing text documents (e.g. DOCX)."""

    model_config = ConfigDict(protected_namespaces=())

    section_index: int = Field(..., description="Zero-based sequence index")
    heading_level: Optional[int] = Field(default=None, description="Heading level if applicable (1, 2, 3)")
    heading: Optional[str] = Field(default=None, description="Heading text if a header")
    text: str = Field(default="", description="Paragraph text content")
    tables: List[ParsedTable] = Field(default_factory=list, description="Tables in this section")
    provenance: DocumentProvenance = Field(..., description="Section-level provenance anchor")


class SheetData(BaseModel):
    """Extracted sheet contents from spreadsheets (XLSX, CSV)."""

    model_config = ConfigDict(protected_namespaces=())

    sheet_name: str = Field(..., description="Name of the sheet")
    sheet_index: int = Field(default=0, description="Zero-based sheet index")
    row_count: int = Field(default=0, description="Number of populated rows")
    col_count: int = Field(default=0, description="Number of populated columns")
    headers: List[str] = Field(default_factory=list, description="Detected or default column headers")
    tables: List[ParsedTable] = Field(default_factory=list, description="Extracted structured tables")
    provenance: DocumentProvenance = Field(..., description="Sheet-level provenance anchor")


class ImageInfo(BaseModel):
    """Validated image properties for standalone image uploads."""

    model_config = ConfigDict(protected_namespaces=())

    format: str = Field(..., description="Image format (PNG, JPEG)")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    mode: str = Field(..., description="Color mode (RGB, RGBA, L, CMYK)")
    color_channels: int = Field(default=3, description="Number of color channels")
    has_alpha: bool = Field(default=False, description="Presence of alpha channel")
    size_bytes: int = Field(..., description="Original image size in bytes")
    provenance: DocumentProvenance = Field(..., description="Image-level provenance anchor")


class NormalizedDocument(BaseModel):
    """Normalized master internal representation of an ingested document."""

    model_config = ConfigDict(protected_namespaces=())

    document_id: str = Field(..., description="Unique document UUID")
    sha256: str = Field(..., description="SHA-256 hash of the original raw file")
    original_filename: str = Field(..., description="Original uploaded filename")
    sanitized_filename: str = Field(..., description="Sanitized safe filename")
    file_extension: str = Field(..., description="Detected file extension without dot")
    media_type: str = Field(..., description="Detected MIME media type")
    size_bytes: int = Field(..., description="Size of original raw file in bytes")
    raw_path: str = Field(..., description="Relative or resolved path to preserved raw file")
    processed_path: Optional[str] = Field(default=None, description="Path to processed JSON representation")
    created_at: str = Field(..., description="ISO 8601 timestamp of ingestion")
    status: ExtractionStatus = Field(default=ExtractionStatus.SUCCESS, description="Overall document status")
    extraction_method: str = Field(..., description="Primary parser applied")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extracted document metadata properties")
    pages: List[DocumentPage] = Field(default_factory=list, description="Paginated pages (PDF)")
    sections: List[DocumentSection] = Field(default_factory=list, description="Linear sections (DOCX)")
    sheets: List[SheetData] = Field(default_factory=list, description="Spreadsheet sheets (XLSX, CSV)")
    tables: List[ParsedTable] = Field(default_factory=list, description="All extracted tables aggregated")
    image_info: Optional[ImageInfo] = Field(default=None, description="Image properties if image file")
    is_scanned: bool = Field(default=False, description="Flag indicating scanned / image-only content")
    needs_ocr: bool = Field(default=False, description="Flag indicating document requires Phase 5 OCR/Vision")
    is_drawing: bool = Field(default=False, description="Flag indicating likely engineering drawing or P&ID")
    warnings: List[str] = Field(default_factory=list, description="Warnings encountered during ingestion")
    errors: List[str] = Field(default_factory=list, description="Errors encountered during ingestion")


class DocumentIngestionResult(BaseModel):
    """Standardized response schema returned by the ingestion service and API."""

    model_config = ConfigDict(protected_namespaces=())

    document_id: str = Field(..., description="Unique document UUID")
    filename: str = Field(..., description="Sanitized filename of the artifact")
    sha256: str = Field(..., description="SHA-256 hash identity of the raw artifact")
    media_type: str = Field(..., description="MIME type of the ingested document")
    size_bytes: int = Field(..., description="File size in bytes")
    status: ExtractionStatus = Field(..., description="Extraction completion status")
    is_scanned: bool = Field(default=False, description="Whether document is scanned/no-text")
    needs_ocr: bool = Field(default=False, description="Handoff flag for Phase 5 OCR processing")
    is_drawing: bool = Field(default=False, description="Heuristic flag for P&ID / engineering schematic")
    page_count: int = Field(default=0, description="Total pages or sections parsed")
    table_count: int = Field(default=0, description="Total structured tables extracted")
    is_duplicate: bool = Field(default=False, description="True if an identical artifact was already ingested")
    raw_path: str = Field(..., description="Location of preserved raw artifact")
    processed_path: Optional[str] = Field(default=None, description="Location of processed artifact")
    extraction_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary statistics of extraction")
    warnings: List[str] = Field(default_factory=list, description="Ingestion warnings")
    errors: List[str] = Field(default_factory=list, description="Ingestion errors")
    normalized_document: Optional[NormalizedDocument] = Field(
        default=None, description="Full normalized representation if requested"
    )
    evidence: Optional[Dict[str, Any]] = Field(
        default=None, description="Structured engineering evidence extracted from document"
    )
