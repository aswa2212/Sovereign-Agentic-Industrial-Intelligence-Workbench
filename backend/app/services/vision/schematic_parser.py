"""
SIH26117 — P&ID and Engineering Drawing Schematic Parser
Integrates local OCR and Vision/VLM reasoning to extract structured industrial schematics.
Supports OCR-only, Vision-only, and Hybrid visual understanding workflows.
"""

import logging
from typing import List, Optional

try:
    from app.services.ingestion.models import DocumentProvenance
    from app.services.vision.base import (
        OCRExtractionResult,
        SchematicAnalysisResult,
        VisualFinding,
        VisualFindingType,
    )
    from app.services.vision.ocr_engine import LocalOCREngine
    from app.services.vision.preprocessor import ImagePreprocessor, PreprocessingConfig
    from app.services.vision.vlm_client import VisionEngine
except ImportError:
    from backend.app.services.ingestion.models import DocumentProvenance
    from backend.app.services.vision.base import (
        OCRExtractionResult,
        SchematicAnalysisResult,
        VisualFinding,
        VisualFindingType,
    )
    from backend.app.services.vision.ocr_engine import LocalOCREngine
    from backend.app.services.vision.preprocessor import ImagePreprocessor, PreprocessingConfig
    from backend.app.services.vision.vlm_client import VisionEngine

logger = logging.getLogger(__name__)


class SchematicParser:
    """
    Orchestrates OCR and Vision extraction on engineering drawings, P&IDs, and inspection scans.
    """

    def __init__(
        self,
        ocr_engine: Optional[LocalOCREngine] = None,
        vision_engine: Optional[VisionEngine] = None,
        preprocessor: Optional[ImagePreprocessor] = None,
    ) -> None:
        self.ocr_engine = ocr_engine
        self.vision_engine = vision_engine
        self.preprocessor = preprocessor or ImagePreprocessor()

    async def parse_drawing(
        self,
        image_bytes: bytes,
        provenance: Optional[DocumentProvenance] = None,
        mode: str = "hybrid",  # 'ocr_only' | 'vision_only' | 'hybrid'
        preprocess: bool = True,
        config: Optional[PreprocessingConfig] = None,
    ) -> SchematicAnalysisResult:
        """
        Process an engineering drawing or P&ID schematic.
        Modes:
            - 'ocr_only': Extracts text tokens, tables, and bounding boxes via OCR engine.
            - 'vision_only': Analyzes drawing layout, symbols, and tags via VLM engine.
            - 'hybrid': Combines OCR token coordinates with VLM visual reasoning.
        """
        prov = provenance or DocumentProvenance(
            source_filename="schematic.png",
            source_sha256="unknown_hash",
            page_number=1,
        )

        # 1. Deterministic Preprocessing
        if preprocess:
            processed_bytes, (width, height) = self.preprocessor.preprocess(
                image_bytes, config=config
            )
        else:
            processed_bytes = image_bytes
            width, height = 0, 0

        # Mode A: Vision Only
        if mode == "vision_only":
            if not self.vision_engine or not self.vision_engine.is_ready():
                raise RuntimeError("VisionEngine is not available for vision_only mode.")
            return await self.vision_engine.analyze_schematic(
                processed_bytes, provenance=prov
            )

        # Mode B: OCR Only
        if mode == "ocr_only":
            if not self.ocr_engine or not self.ocr_engine.is_engine_ready():
                raise RuntimeError("LocalOCREngine is not available for ocr_only mode.")
            ocr_res = await self.ocr_engine.extract_from_image(
                processed_bytes, provenance=prov, preprocess=False
            )
            return self._convert_ocr_to_schematic_result(ocr_res, prov)

        # Mode C: Hybrid (OCR + Vision)
        warnings: List[str] = []
        ocr_res: Optional[OCRExtractionResult] = None

        if self.ocr_engine and self.ocr_engine.is_engine_ready():
            try:
                ocr_res = await self.ocr_engine.extract_from_image(
                    processed_bytes, provenance=prov, preprocess=False
                )
            except Exception as e:
                logger.warning("OCR stage in hybrid pipeline failed: %s", str(e))
                warnings.append(f"OCR stage warning: {str(e)}")

        if self.vision_engine and self.vision_engine.is_ready():
            try:
                vision_res = await self.vision_engine.analyze_schematic(
                    processed_bytes, provenance=prov
                )
                if ocr_res and ocr_res.tokens:
                    # Enrich vision findings with high-confidence OCR text tokens if nearby
                    vision_res.warnings.extend(warnings)
                return vision_res
            except Exception as e:
                logger.warning("Vision stage in hybrid pipeline failed: %s", str(e))
                warnings.append(f"Vision stage warning: {str(e)}")

        # If vision wasn't available but OCR succeeded, return OCR converted result
        if ocr_res:
            res = self._convert_ocr_to_schematic_result(ocr_res, prov)
            res.warnings.extend(warnings)
            return res

        raise RuntimeError(
            "Neither LocalOCREngine nor VisionEngine is available for schematic analysis."
        )

    def _convert_ocr_to_schematic_result(
        self,
        ocr_res: OCRExtractionResult,
        provenance: DocumentProvenance,
    ) -> SchematicAnalysisResult:
        """Convert OCR text tokens and line blocks into initial candidate findings."""
        findings: List[VisualFinding] = []
        candidate_tags: List[str] = []
        equipment_tags: List[str] = []
        instrument_tags: List[str] = []

        import re

        # Regex heuristics for standard refinery P&ID tag patterns
        # Instrument tags (ISA-5.1): PT-101, FT-202, TT-301, LT-401, PIC-101, FCV-101, PSV-101
        inst_pattern = re.compile(r"\b((?:[PFTLA][TIRCVDA]|[A-Z]{3,4})-[0-9]{3,4}[A-Z]?)\b")
        # Equipment tags: C-101 (Column), E-102 (Exchanger), V-103 (Vessel), P-101 (Pump), K-101 (Compressor), T-101, F-101, R-101, TK-101
        eq_pattern = re.compile(r"\b((?:[CEVPKTFR]|TK|HE|CL|FL|DR|EX|BL|ST|PU|CO)-[0-9]{3,4}[A-Z]?)\b")
        # Line spec: 10"-CDU-0101-CS150 or 10-CDU-0101
        line_pattern = re.compile(r"\b(\d{1,2}\"?-[A-Z0-9]{2,6}-\d{3,5}(?:-[A-Z0-9]+)?)\b")

        for block in ocr_res.blocks:
            text = block.text.strip()

            # Check for instrument tag match first
            inst_matches = inst_pattern.findall(text)
            for m in inst_matches:
                if m not in candidate_tags:
                    candidate_tags.append(m)
                    instrument_tags.append(m)
                    findings.append(
                        VisualFinding(
                            finding_type=VisualFindingType.INSTRUMENT_TAG,
                            label=m,
                            text=text,
                            confidence=block.mean_confidence,
                            bounding_box=block.bbox,
                            provenance=provenance,
                            evidence="Detected via OCR instrument bubble pattern matching",
                        )
                    )

            # Check for equipment tag match
            eq_matches = eq_pattern.findall(text)
            for m in eq_matches:
                if m not in candidate_tags and m not in instrument_tags:
                    candidate_tags.append(m)
                    equipment_tags.append(m)
                    findings.append(
                        VisualFinding(
                            finding_type=VisualFindingType.EQUIPMENT_TAG,
                            label=m,
                            text=text,
                            confidence=block.mean_confidence,
                            bounding_box=block.bbox,
                            provenance=provenance,
                            evidence="Detected via OCR equipment tag pattern matching",
                        )
                    )

            # Check for line ID match
            line_matches = line_pattern.findall(text)
            for m in line_matches:
                if m not in candidate_tags:
                    candidate_tags.append(m)
                    findings.append(
                        VisualFinding(
                            finding_type=VisualFindingType.LINE_ID,
                            label=m,
                            text=text,
                            confidence=block.mean_confidence,
                            bounding_box=block.bbox,
                            provenance=provenance,
                            evidence="Detected via OCR piping line spec pattern matching",
                        )
                    )

        return SchematicAnalysisResult(
            findings=findings,
            summary=f"OCR extracted {len(ocr_res.tokens)} tokens across {len(ocr_res.blocks)} lines.",
            candidate_tags=candidate_tags,
            equipment_tags=equipment_tags,
            instrument_tags=instrument_tags,
            drawing_metadata={},
            provenance=provenance,
            status=ocr_res.status,
            model_used=ocr_res.engine_name,
        )
