"""
SIH26117 — Vision & OCR API Schemas
Defines request and response schemas for local OCR and schematic visual analysis endpoints.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

try:
    from app.services.vision.base import (
        BoundingBox,
        OCRBlock,
        OCRExtractionResult,
        OCRToken,
        SchematicAnalysisResult,
        VisualFinding,
        VisualFindingType,
    )
except ImportError:
    from backend.app.services.vision.base import (
        BoundingBox,
        OCRBlock,
        OCRExtractionResult,
        OCRToken,
        SchematicAnalysisResult,
        VisualFinding,
        VisualFindingType,
    )


class OCRRequest(BaseModel):
    """Request schema for initiating OCR on a previously ingested document artifact."""

    model_config = ConfigDict(protected_namespaces=())

    document_sha256: Optional[str] = Field(
        default=None, description="SHA-256 hash of raw document preserved in data/raw/"
    )
    page_number: Optional[int] = Field(
        default=1, description="1-based page number if paginated document"
    )
    preprocess: bool = Field(
        default=True, description="Whether to apply contrast normalization and sharpening"
    )


class SchematicAnalysisRequest(BaseModel):
    """Request schema for visual P&ID and schematic analysis."""

    model_config = ConfigDict(protected_namespaces=())

    document_sha256: Optional[str] = Field(
        default=None, description="SHA-256 hash of drawing artifact in data/raw/"
    )
    page_number: Optional[int] = Field(
        default=1, description="1-based page number if multi-page document"
    )
    mode: str = Field(
        default="hybrid", description="Execution mode: 'hybrid' | 'ocr_only' | 'vision_only'"
    )
    custom_prompt: Optional[str] = Field(
        default=None, description="Optional operator prompt guiding tag or symbol inspection"
    )


__all__ = [
    "OCRRequest",
    "SchematicAnalysisRequest",
    "OCRExtractionResult",
    "SchematicAnalysisResult",
    "VisualFinding",
    "VisualFindingType",
    "BoundingBox",
    "OCRToken",
    "OCRBlock",
]
