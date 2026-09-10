"""
SIH26117 — Vision & OCR Services Package
Public interface for local OCR, image preprocessing, and P&ID visual understanding.
"""

from app.services.vision.base import (
    BoundingBox,
    InvalidImageError,
    OCRBlock,
    OCREngineUnavailableError,
    OCRExtractionResult,
    OCRProvider,
    OCRToken,
    SchematicAnalysisResult,
    VisionError,
    VisionModelUnavailableError,
    VisionProvider,
    VisualFinding,
    VisualFindingType,
)
from app.services.vision.ocr_engine import (
    LocalOCREngine,
    MockOCRProvider,
    TesseractOCRProvider,
)
from app.services.vision.preprocessor import (
    ImagePreprocessor,
    PreprocessingConfig,
)
from app.services.vision.schematic_parser import SchematicParser
from app.services.vision.vlm_client import (
    MockVisionProvider,
    ModelManagerVisionProvider,
    VisionEngine,
)

__all__ = [
    "VisionError",
    "OCREngineUnavailableError",
    "VisionModelUnavailableError",
    "InvalidImageError",
    "VisualFindingType",
    "BoundingBox",
    "OCRToken",
    "OCRBlock",
    "OCRExtractionResult",
    "VisualFinding",
    "SchematicAnalysisResult",
    "OCRProvider",
    "VisionProvider",
    "TesseractOCRProvider",
    "MockOCRProvider",
    "LocalOCREngine",
    "PreprocessingConfig",
    "ImagePreprocessor",
    "ModelManagerVisionProvider",
    "MockVisionProvider",
    "VisionEngine",
    "SchematicParser",
]
