"""
SIH26117 — Vision & OCR Base Contracts & Data Models
Defines typed schemas for bounding boxes, OCR tokens, visual findings, and provider abstractions.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

try:
    from app.services.ingestion.models import DocumentProvenance
except ImportError:
    from backend.app.services.ingestion.models import DocumentProvenance


# ── Exceptions ────────────────────────────────────────────────────────────────

class VisionError(Exception):
    """Base exception for all vision and OCR pipeline errors."""

    def __init__(
        self,
        message: str,
        code: str = "VISION_ERROR",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details


class OCREngineUnavailableError(VisionError):
    """Raised when the local OCR engine (e.g. Tesseract) is not installed or unreachable."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, code="OCR_UNAVAILABLE", details=details)


class VisionModelUnavailableError(VisionError):
    """Raised when the local vision/VLM model is not available or cannot be loaded."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, code="VISION_MODEL_UNAVAILABLE", details=details)


class InvalidImageError(VisionError):
    """Raised when image bytes are corrupted, unreadable, or unsupported."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, code="INVALID_IMAGE", details=details)


# ── Enums & Data Contracts ────────────────────────────────────────────────────

class VisualFindingType(str, Enum):
    """Classification of visual engineering findings in industrial documents and schematics."""

    EQUIPMENT_TAG = "equipment_tag"      # e.g., C-101, E-102, V-103
    INSTRUMENT_TAG = "instrument_tag"    # e.g., PT-101, FT-202, TT-301
    LINE_ID = "line_id"                  # e.g., 10"-CDU-0101-CS150
    VALVE_SYMBOL = "valve_symbol"        # e.g., Gate Valve, Control Valve
    SPEC_NOTE = "spec_note"              # e.g., Material specs, design pressure
    TABLE_CELL = "table_cell"            # Degraded tabular reading
    CORROSION_REGION = "corrosion_region"# Visual indication of wall thinning
    UNKNOWN = "unknown"


class BoundingBox(BaseModel):
    """
    Spatial geometry bounding box in both normalized and pixel coordinates.
    Normalized coordinates (0.0 to 1.0) allow resolution-independent rendering.
    """

    model_config = ConfigDict(protected_namespaces=())

    # Normalized coordinates [0.0 - 1.0]
    x_min: float = Field(..., description="Normalized left coordinate (0.0 - 1.0)")
    y_min: float = Field(..., description="Normalized top coordinate (0.0 - 1.0)")
    x_max: float = Field(..., description="Normalized right coordinate (0.0 - 1.0)")
    y_max: float = Field(..., description="Normalized bottom coordinate (0.0 - 1.0)")

    # Absolute pixel dimensions if available
    pixel_x: Optional[int] = Field(default=None, description="Absolute pixel left")
    pixel_y: Optional[int] = Field(default=None, description="Absolute pixel top")
    pixel_width: Optional[int] = Field(default=None, description="Absolute pixel width")
    pixel_height: Optional[int] = Field(default=None, description="Absolute pixel height")


class OCRToken(BaseModel):
    """Individual character, word, or alphanumeric token extracted by OCR."""

    model_config = ConfigDict(protected_namespaces=())

    text: str = Field(..., description="Recognized token string")
    confidence: float = Field(..., description="Recognition confidence (0.0 to 1.0)")
    bbox: Optional[BoundingBox] = Field(default=None, description="Token spatial bounding box")


class OCRBlock(BaseModel):
    """Line or logical block of OCR tokens."""

    model_config = ConfigDict(protected_namespaces=())

    line_number: int = Field(default=1, description="Sequential line index")
    text: str = Field(..., description="Concatenated line text")
    tokens: List[OCRToken] = Field(default_factory=list, description="Constituent tokens")
    mean_confidence: float = Field(..., description="Average line confidence (0.0 to 1.0)")
    bbox: Optional[BoundingBox] = Field(default=None, description="Line bounding box")


class OCRExtractionResult(BaseModel):
    """Normalized structured result from an OCR extraction run."""

    model_config = ConfigDict(protected_namespaces=())

    text: str = Field(default="", description="Full reconstructed text from page/image")
    tokens: List[OCRToken] = Field(default_factory=list, description="Individual word tokens")
    blocks: List[OCRBlock] = Field(default_factory=list, description="Line and paragraph blocks")
    mean_confidence: float = Field(default=0.0, description="Overall extraction confidence (0.0 to 1.0)")
    provenance: DocumentProvenance = Field(..., description="Traceable provenance anchor")
    status: str = Field(default="success", description="Extraction status (success, partial, failed)")
    engine_name: str = Field(..., description="Name of OCR engine utilized")
    warnings: List[str] = Field(default_factory=list, description="Warnings during OCR")
    errors: List[str] = Field(default_factory=list, description="Non-fatal extraction anomalies")


class VisualFinding(BaseModel):
    """A verified or candidate visual entity detected in an engineering drawing or scan."""

    model_config = ConfigDict(protected_namespaces=())

    finding_type: VisualFindingType = Field(..., description="Entity category")
    label: str = Field(..., description="Standardized label or tag identifier (e.g. C-101, PT-101)")
    text: str = Field(default="", description="Literal text detected at or near symbol")
    confidence: float = Field(..., description="Detection confidence (0.0 to 1.0)")
    bounding_box: Optional[BoundingBox] = Field(default=None, description="Spatial coordinates")
    provenance: DocumentProvenance = Field(..., description="Anchor back to source document/page")
    evidence: str = Field(default="", description="Descriptive visual evidence justifying detection")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional domain metadata")


class SchematicAnalysisResult(BaseModel):
    """Complete structured output from P&ID / drawing visual understanding."""

    model_config = ConfigDict(protected_namespaces=())

    findings: List[VisualFinding] = Field(default_factory=list, description="All detected visual entities")
    summary: str = Field(default="", description="Executive visual summary of the drawing")
    candidate_tags: List[str] = Field(default_factory=list, description="All identified tag codes")
    equipment_tags: List[str] = Field(default_factory=list, description="Identified equipment tags (columns, pumps)")
    instrument_tags: List[str] = Field(default_factory=list, description="Identified instrument tags (PT, FT, TT)")
    drawing_metadata: Dict[str, Any] = Field(default_factory=dict, description="Extracted title block/sheet metadata")
    provenance: DocumentProvenance = Field(..., description="Source document provenance anchor")
    status: str = Field(default="success", description="Overall analysis status")
    model_used: str = Field(default="unknown", description="Vision model / engine used")
    warnings: List[str] = Field(default_factory=list, description="Analysis warnings")
    errors: List[str] = Field(default_factory=list, description="Non-fatal errors")


# ── Provider Abstract Interfaces ──────────────────────────────────────────────

class OCRProvider(ABC):
    """Abstract interface for local OCR engines (Tesseract, mock, etc.)."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if local OCR engine dependencies are installed and executable."""
        pass

    @abstractmethod
    async def extract_text(
        self,
        image_bytes: bytes,
        provenance: Optional[DocumentProvenance] = None,
    ) -> OCRExtractionResult:
        """Execute local OCR on an image buffer and return structured tokens and lines."""
        pass


class VisionProvider(ABC):
    """Abstract interface for local vision / VLM inference (Qwen2.5-VL via ModelManager)."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the vision backend/model is available."""
        pass

    @abstractmethod
    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: Optional[str] = None,
        provenance: Optional[DocumentProvenance] = None,
    ) -> SchematicAnalysisResult:
        """Analyze drawing or technical sheet image and return structured visual findings."""
        pass

    @abstractmethod
    async def identify_tags(
        self,
        image_bytes: bytes,
        provenance: Optional[DocumentProvenance] = None,
    ) -> List[VisualFinding]:
        """Specialized extraction focusing strictly on P&ID tags and equipment labels."""
        pass
