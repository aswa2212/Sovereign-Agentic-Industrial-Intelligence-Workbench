"""
SIH26117 — Local OCR Engine & Providers
Implements OCR abstraction supporting local Tesseract execution and deterministic test mocks.
Preserves token-level confidence scores, bounding boxes, and document provenance.
"""

import io
import logging
from typing import Any, Dict, List, Optional
from PIL import Image

try:
    from app.services.ingestion.models import DocumentProvenance
    from app.services.vision.base import (
        BoundingBox,
        OCRBlock,
        OCRExtractionResult,
        OCREngineUnavailableError,
        OCRProvider,
        OCRToken,
    )
    from app.services.vision.preprocessor import ImagePreprocessor, PreprocessingConfig
except ImportError:
    from backend.app.services.ingestion.models import DocumentProvenance
    from backend.app.services.vision.base import (
        BoundingBox,
        OCRBlock,
        OCRExtractionResult,
        OCREngineUnavailableError,
        OCRProvider,
        OCRToken,
    )
    from backend.app.services.vision.preprocessor import ImagePreprocessor, PreprocessingConfig

logger = logging.getLogger(__name__)

# Check pytesseract availability
try:
    import pytesseract
    PYTESSERACT_INSTALLED = True
except ImportError:
    PYTESSERACT_INSTALLED = False


class TesseractOCRProvider(OCRProvider):
    """
    Local OCR provider utilizing Tesseract OCR via pytesseract.
    Actively checks host binary presence and raises OCREngineUnavailableError if missing.
    """

    def __init__(self, tesseract_cmd: Optional[str] = None) -> None:
        self.tesseract_cmd = tesseract_cmd
        if tesseract_cmd and PYTESSERACT_INSTALLED:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def is_available(self) -> bool:
        """Probe if tesseract executable is available on the local system."""
        if not PYTESSERACT_INSTALLED:
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    async def extract_text(
        self,
        image_bytes: bytes,
        provenance: Optional[DocumentProvenance] = None,
    ) -> OCRExtractionResult:
        """Run Tesseract OCR on image bytes and structure token/block results."""
        if not self.is_available():
            raise OCREngineUnavailableError(
                "Tesseract OCR executable is not available on this host. "
                "Ensure tesseract is installed in the system PATH."
            )

        prov = provenance or DocumentProvenance(
            source_filename="unknown_image",
            source_sha256="unknown_hash",
        )

        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            img_w, img_h = pil_img.size
            data: Dict[str, List[Any]] = pytesseract.image_to_data(
                pil_img, output_type=pytesseract.Output.DICT
            )

        tokens: List[OCRToken] = []
        blocks_dict: Dict[int, List[OCRToken]] = {}
        n_boxes = len(data.get("text", []))

        for i in range(n_boxes):
            raw_text = str(data["text"][i]).strip()
            conf_val = float(data.get("conf", [0])[i])

            # Tesseract reports -1 for structure blocks without recognized text
            if not raw_text or conf_val < 0:
                continue

            norm_conf = max(0.0, min(1.0, conf_val / 100.0))
            x = int(data["left"][i])
            y = int(data["top"][i])
            w = int(data["width"][i])
            h = int(data["height"][i])

            bbox = BoundingBox(
                x_min=round(x / img_w, 4) if img_w > 0 else 0.0,
                y_min=round(y / img_h, 4) if img_h > 0 else 0.0,
                x_max=round((x + w) / img_w, 4) if img_w > 0 else 0.0,
                y_max=round((y + h) / img_h, 4) if img_h > 0 else 0.0,
                pixel_x=x,
                pixel_y=y,
                pixel_width=w,
                pixel_height=h,
            )

            token = OCRToken(text=raw_text, confidence=norm_conf, bbox=bbox)
            tokens.append(token)

            line_num = int(data.get("line_num", [1])[i])
            blocks_dict.setdefault(line_num, []).append(token)

        # Build line blocks
        blocks: List[OCRBlock] = []
        for line_num, line_tokens in sorted(blocks_dict.items()):
            line_text = " ".join(t.text for t in line_tokens)
            line_mean_conf = sum(t.confidence for t in line_tokens) / len(line_tokens)
            # Combine bounding boxes for line
            min_x = min(t.bbox.pixel_x for t in line_tokens if t.bbox)
            min_y = min(t.bbox.pixel_y for t in line_tokens if t.bbox)
            max_r = max(t.bbox.pixel_x + t.bbox.pixel_width for t in line_tokens if t.bbox)
            max_b = max(t.bbox.pixel_y + t.bbox.pixel_height for t in line_tokens if t.bbox)

            line_bbox = BoundingBox(
                x_min=round(min_x / img_w, 4) if img_w > 0 else 0.0,
                y_min=round(min_y / img_h, 4) if img_h > 0 else 0.0,
                x_max=round(max_r / img_w, 4) if img_w > 0 else 0.0,
                y_max=round(max_b / img_h, 4) if img_w > 0 else 0.0,
                pixel_x=min_x,
                pixel_y=min_y,
                pixel_width=max_r - min_x,
                pixel_height=max_b - min_y,
            )

            blocks.append(
                OCRBlock(
                    line_number=line_num,
                    text=line_text,
                    tokens=line_tokens,
                    mean_confidence=round(line_mean_conf, 4),
                    bbox=line_bbox,
                )
            )

        full_text = "\n".join(b.text for b in blocks)
        overall_mean_conf = sum(t.confidence for t in tokens) / len(tokens) if tokens else 0.0

        return OCRExtractionResult(
            text=full_text,
            tokens=tokens,
            blocks=blocks,
            mean_confidence=round(overall_mean_conf, 4),
            provenance=prov,
            status="success" if tokens else "empty",
            engine_name="tesseract",
        )


class MockOCRProvider(OCRProvider):
    """
    Deterministic mock OCR provider for tests, CI pipelines, and hardware-free verification.
    Simulates high-precision OCR extraction with token geometries and confidences.
    """

    def __init__(self, predefined_text: Optional[str] = None) -> None:
        self.predefined_text = predefined_text

    def is_available(self) -> bool:
        return True

    async def extract_text(
        self,
        image_bytes: bytes,
        provenance: Optional[DocumentProvenance] = None,
    ) -> OCRExtractionResult:
        prov = provenance or DocumentProvenance(
            source_filename="mock_scan.png",
            source_sha256="mock_sha256_00000000000000000000000000000000",
            page_number=1,
        )

        sample_text = self.predefined_text or (
            "MRPL NDT ULTRASONIC INSPECTION REPORT\n"
            "Equipment: C-101 Atmospheric Column\n"
            "Date: 2026-03-15 | Nominal: 12.0 mm\n"
            "P-01 Shell Top: 11.2 mm\n"
            "P-02 Shell Mid: 10.9 mm\n"
            "PT-101 Pressure Transmitter Normal"
        )

        tokens: List[OCRToken] = []
        blocks: List[OCRBlock] = []

        lines = sample_text.strip().split("\n")
        for line_idx, line in enumerate(lines):
            line_tokens: List[OCRToken] = []
            words = line.split()
            y_base = 0.15 + (line_idx * 0.12)

            for w_idx, w in enumerate(words):
                x_base = 0.05 + (w_idx * 0.15)
                # Assign high confidence for clean words, slightly lower for punctuation/numbers
                conf = 0.98 if w.isalpha() else 0.94
                bbox = BoundingBox(
                    x_min=round(x_base, 4),
                    y_min=round(y_base, 4),
                    x_max=round(x_base + 0.12, 4),
                    y_max=round(y_base + 0.08, 4),
                    pixel_x=int(x_base * 1000),
                    pixel_y=int(y_base * 1000),
                    pixel_width=120,
                    pixel_height=80,
                )
                tok = OCRToken(text=w, confidence=conf, bbox=bbox)
                tokens.append(tok)
                line_tokens.append(tok)

            line_conf = sum(t.confidence for t in line_tokens) / len(line_tokens) if line_tokens else 0.95
            blocks.append(
                OCRBlock(
                    line_number=line_idx + 1,
                    text=line,
                    tokens=line_tokens,
                    mean_confidence=round(line_conf, 4),
                    bbox=BoundingBox(
                        x_min=0.05,
                        y_min=round(y_base, 4),
                        x_max=0.90,
                        y_max=round(y_base + 0.08, 4),
                    ),
                )
            )

        mean_conf = sum(t.confidence for t in tokens) / len(tokens) if tokens else 0.95

        return OCRExtractionResult(
            text=sample_text,
            tokens=tokens,
            blocks=blocks,
            mean_confidence=round(mean_conf, 4),
            provenance=prov,
            status="success",
            engine_name="mock_ocr",
        )


class LocalOCREngine:
    """
    Orchestrates deterministic image preprocessing and localized OCR extraction.
    Allows seamless switching between Tesseract and test mock providers.
    """

    def __init__(
        self,
        provider: Optional[OCRProvider] = None,
        preprocessor: Optional[ImagePreprocessor] = None,
        prefer_mock_if_unavailable: bool = False,
    ) -> None:
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.prefer_mock = prefer_mock_if_unavailable

        if provider is not None:
            self.provider = provider
        else:
            tesseract_provider = TesseractOCRProvider()
            if tesseract_provider.is_available():
                self.provider = tesseract_provider
            elif prefer_mock_if_unavailable:
                self.provider = MockOCRProvider()
            else:
                self.provider = tesseract_provider

    def is_engine_ready(self) -> bool:
        """Check if active OCR provider can execute."""
        return self.provider.is_available()

    async def extract_from_image(
        self,
        image_bytes: bytes,
        provenance: Optional[DocumentProvenance] = None,
        preprocess: bool = True,
        config: Optional[PreprocessingConfig] = None,
    ) -> OCRExtractionResult:
        """
        Preprocess image and execute OCR extraction.
        """
        if preprocess:
            processed_bytes, _ = self.preprocessor.preprocess(image_bytes, config=config)
        else:
            processed_bytes = image_bytes

        return await self.provider.extract_text(
            processed_bytes,
            provenance=provenance,
        )
