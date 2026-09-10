"""
SIH26117 — Phase 5 OCR & Vision Engine Unit & API Tests
Comprehensive offline test suite covering:
1. Image preprocessing (deterministic operations, grayscale, contrast, sharpening, thresholding)
2. OCR provider contract and LocalOCREngine orchestration
3. Tesseract availability guard (raises OCREngineUnavailableError when host binary is absent)
4. MockOCRProvider extraction, token confidence scores, and bounding boxes
5. Provenance preservation on OCR tokens and blocks
6. Vision / VLM provider contract and ModelManager integration
7. MockVisionProvider structured P&ID visual findings (C-101, PT-101, line IDs)
8. SchematicParser workflows: ocr_only, vision_only, and hybrid
9. BoundingBox normalization and pixel coordinate preservation
10. Scanned document handoff from Phase 4 (consuming needs_ocr artifacts)
11. Provider and model unavailable error handling
12. Air-gap compliance (zero external network sockets)
13. API endpoints (/api/v1/vision/ocr and /api/v1/vision/analyze-drawing)
"""

import io
import socket
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image

try:
    from app.core.config import get_settings
    from app.main import app
    from app.services.ingestion.models import DocumentProvenance
    from app.services.model_manager.base import InferenceBackend, ModelCapabilities, ModelInfo
    from app.services.model_manager.config_loader import ModelEntry, TierConfig
    from app.services.model_manager.manager import ModelManager
    from app.services.model_manager.mock_adapter import MockInferenceBackend
    from app.services.vision.base import (
        BoundingBox,
        InvalidImageError,
        OCREngineUnavailableError,
        OCRProvider,
        OCRToken,
        SchematicAnalysisResult,
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
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.main import app
    from backend.app.services.ingestion.models import DocumentProvenance
    from backend.app.services.model_manager.base import (
        InferenceBackend,
        ModelCapabilities,
        ModelInfo,
    )
    from backend.app.services.model_manager.config_loader import ModelEntry, TierConfig
    from backend.app.services.model_manager.manager import ModelManager
    from backend.app.services.model_manager.mock_adapter import MockInferenceBackend
    from backend.app.services.vision.base import (
        BoundingBox,
        InvalidImageError,
        OCREngineUnavailableError,
        OCRProvider,
        OCRToken,
        SchematicAnalysisResult,
        VisionModelUnavailableError,
        VisionProvider,
        VisualFinding,
        VisualFindingType,
    )
    from backend.app.services.vision.ocr_engine import (
        LocalOCREngine,
        MockOCRProvider,
        TesseractOCRProvider,
    )
    from backend.app.services.vision.preprocessor import (
        ImagePreprocessor,
        PreprocessingConfig,
    )
    from backend.app.services.vision.schematic_parser import SchematicParser
    from backend.app.services.vision.vlm_client import (
        MockVisionProvider,
        ModelManagerVisionProvider,
        VisionEngine,
    )

client = TestClient(app)


# ── Synthetic In-Memory Image Helpers ─────────────────────────────────────────

def build_test_image(width: int = 200, height: int = 150, color=(50, 100, 200)) -> bytes:
    """Construct an in-memory PNG image."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Image Preprocessor Tests ──────────────────────────────────────────────────

class TestImagePreprocessor:
    """Verifies deterministic image transformations."""

    def test_empty_image_raises_invalid_image(self):
        preprocessor = ImagePreprocessor()
        with pytest.raises(InvalidImageError):
            preprocessor.preprocess(b"")

    def test_corrupted_image_raises_invalid_image(self):
        preprocessor = ImagePreprocessor()
        with pytest.raises(InvalidImageError):
            preprocessor.preprocess(b"NOT_A_VALID_IMAGE_BYTES")

    def test_grayscale_and_contrast_enhancement(self):
        img_bytes = build_test_image(100, 100, color=(100, 150, 220))
        preprocessor = ImagePreprocessor()
        config = PreprocessingConfig(grayscale=True, normalize_contrast=True)

        processed_bytes, (w, h) = preprocessor.preprocess(img_bytes, config=config)
        assert w == 100
        assert h == 100
        assert len(processed_bytes) > 0

        # Verify output is valid image in L mode
        with Image.open(io.BytesIO(processed_bytes)) as pil_img:
            assert pil_img.mode == "L"

    def test_binarization_threshold(self):
        img_bytes = build_test_image(80, 80, color=(180, 180, 180))
        preprocessor = ImagePreprocessor()
        config = PreprocessingConfig(binarize=True, binary_threshold=140)

        processed_bytes, (w, h) = preprocessor.preprocess(img_bytes, config=config)
        with Image.open(io.BytesIO(processed_bytes)) as pil_img:
            assert pil_img.mode == "1"

    def test_max_dimension_downscaling(self):
        img_bytes = build_test_image(3000, 1500)
        preprocessor = ImagePreprocessor()
        config = PreprocessingConfig(max_dimension=1000)

        processed_bytes, (w, h) = preprocessor.preprocess(img_bytes, config=config)
        assert w <= 1000
        assert h <= 1000
        assert w == 1000
        assert h == 500  # Preserved aspect ratio 2:1

    def test_raw_bytes_unaltered(self):
        img_bytes = build_test_image(50, 50)
        original_copy = bytes(img_bytes)
        preprocessor = ImagePreprocessor()
        preprocessor.preprocess(img_bytes)
        assert img_bytes == original_copy


# ── OCR Engine & Provider Tests ───────────────────────────────────────────────

class TestOCREngine:
    """Verifies OCR provider contracts, availability gating, and confidence calculations."""

    def test_tesseract_availability_gating(self):
        """
        Verify that TesseractOCRProvider safely probes availability and raises
        OCREngineUnavailableError when host binary is absent.
        """
        provider = TesseractOCRProvider(tesseract_cmd="nonexistent_tesseract_binary_path")
        assert provider.is_available() is False

    @pytest.mark.anyio
    async def test_tesseract_raises_unavailable_when_called(self):
        provider = TesseractOCRProvider(tesseract_cmd="nonexistent_tesseract_binary_path")
        img_bytes = build_test_image(50, 50)
        with pytest.raises(OCREngineUnavailableError) as exc_info:
            await provider.extract_text(img_bytes)
        assert "not available" in str(exc_info.value)
        assert exc_info.value.code == "OCR_UNAVAILABLE"

    @pytest.mark.anyio
    async def test_mock_ocr_provider_extraction(self):
        provider = MockOCRProvider()
        assert provider.is_available() is True

        img_bytes = build_test_image(200, 100)
        prov = DocumentProvenance(
            source_filename="ndt_scan.png",
            source_sha256="abc123sha256",
            page_number=1,
        )

        res = await provider.extract_text(img_bytes, provenance=prov)
        assert res.status == "success"
        assert res.engine_name == "mock_ocr"
        assert res.provenance.source_filename == "ndt_scan.png"
        assert res.provenance.page_number == 1
        assert "C-101" in res.text
        assert "11.2 mm" in res.text
        assert res.mean_confidence >= 0.90

        # Verify tokens have bounding boxes and confidence scores
        assert len(res.tokens) > 0
        first_tok = res.tokens[0]
        assert first_tok.confidence > 0.0
        assert first_tok.bbox is not None
        assert 0.0 <= first_tok.bbox.x_min <= 1.0
        assert 0.0 <= first_tok.bbox.y_min <= 1.0

        # Verify line blocks
        assert len(res.blocks) >= 3
        first_block = res.blocks[0]
        assert first_block.line_number == 1
        assert len(first_block.tokens) > 0

    @pytest.mark.anyio
    async def test_local_ocr_engine_orchestration(self):
        mock_prov = MockOCRProvider(predefined_text="TAG-01 Reading: 9.8 mm")
        engine = LocalOCREngine(provider=mock_prov)
        assert engine.is_engine_ready() is True

        img_bytes = build_test_image(100, 100)
        res = await engine.extract_from_image(img_bytes, preprocess=True)
        assert "TAG-01" in res.text
        assert "9.8 mm" in res.text


# ── Vision & VLM Provider Tests ───────────────────────────────────────────────

class TestVisionProvider:
    """Verifies Vision/VLM abstraction, P&ID candidate extraction, and ModelManager integration."""

    @pytest.mark.anyio
    async def test_mock_vision_provider_p_and_id_findings(self):
        provider = MockVisionProvider()
        assert provider.is_available() is True

        img_bytes = build_test_image(300, 200)
        prov = DocumentProvenance(
            source_filename="pid_cdu_101.png",
            source_sha256="pid_sha256_mock",
            page_number=1,
        )

        res = await provider.analyze_image(img_bytes, provenance=prov)
        assert res.status == "success"
        assert "C-101" in res.equipment_tags
        assert "PT-101" in res.instrument_tags
        assert "FT-202" in res.instrument_tags
        assert len(res.findings) >= 4

        # Check visual finding properties
        c101_finding = next(f for f in res.findings if f.label == "C-101")
        assert c101_finding.finding_type == VisualFindingType.EQUIPMENT_TAG
        assert c101_finding.confidence >= 0.90
        assert c101_finding.bounding_box is not None
        assert c101_finding.bounding_box.x_min == 0.20
        assert c101_finding.provenance.source_filename == "pid_cdu_101.png"
        assert "distillation vessel" in c101_finding.evidence.lower()

    @pytest.mark.anyio
    async def test_model_manager_vision_provider_integration(self):
        """
        Verify that ModelManagerVisionProvider requests role 'vision' through ModelManager
        without hardcoding model IDs.
        """
        # Build mock tier configuration
        tier_cfg = TierConfig(
            description="Test Tier",
            vram_budget_gb=8.0,
            max_concurrent_models=1,
            vision=ModelEntry(
                provider="mock",
                model_tag="qwen2.5-vl:3b",
                context_window=4096,
            ),
        )
        mock_backend = MockInferenceBackend()
        model_mgr = ModelManager(backend=mock_backend, tier_config=tier_cfg)
        provider = ModelManagerVisionProvider(model_mgr)

        assert provider.is_available() is True

        img_bytes = build_test_image(100, 100)
        res = await provider.analyze_image(img_bytes)
        assert res.status == "success"
        assert res.model_used == "qwen2.5-vl:3b"

    @pytest.mark.anyio
    async def test_model_manager_vision_provider_missing_role_raises_error(self):
        # Build tier without vision role
        tier_cfg = TierConfig(
            description="No Vision Tier",
            vram_budget_gb=8.0,
            max_concurrent_models=1,
            vision=None,
        )
        model_mgr = ModelManager(backend=MockInferenceBackend(), tier_config=tier_cfg)
        provider = ModelManagerVisionProvider(model_mgr)

        assert provider.is_available() is False
        with pytest.raises(VisionModelUnavailableError):
            await provider.analyze_image(build_test_image(50, 50))


# ── Schematic Parser (P&ID Hybrid Workflows) ─────────────────────────────────

class TestSchematicParser:
    """Verifies OCR-only, Vision-only, and Hybrid schematic analysis."""

    @pytest.mark.anyio
    async def test_schematic_parser_ocr_only_mode(self):
        mock_ocr = MockOCRProvider(
            predefined_text="P&ID UNIT CDU\nC-101 Distillation Column\nPT-101 4.5 bar\n10-CDU-0101-CS150"
        )
        ocr_engine = LocalOCREngine(provider=mock_ocr)
        parser = SchematicParser(ocr_engine=ocr_engine, vision_engine=None)

        img_bytes = build_test_image(200, 150)
        res = await parser.parse_drawing(img_bytes, mode="ocr_only")

        assert res.status == "success"
        assert "C-101" in res.equipment_tags
        assert "PT-101" in res.instrument_tags
        assert any(f.finding_type == VisualFindingType.LINE_ID for f in res.findings)

    @pytest.mark.anyio
    async def test_schematic_parser_vision_only_mode(self):
        vision_engine = VisionEngine(provider=MockVisionProvider())
        parser = SchematicParser(ocr_engine=None, vision_engine=vision_engine)

        img_bytes = build_test_image(200, 150)
        res = await parser.parse_drawing(img_bytes, mode="vision_only")

        assert res.status == "success"
        assert "C-101" in res.equipment_tags
        assert "PT-101" in res.instrument_tags

    @pytest.mark.anyio
    async def test_schematic_parser_hybrid_mode(self):
        mock_ocr = MockOCRProvider()
        ocr_engine = LocalOCREngine(provider=mock_ocr)
        vision_engine = VisionEngine(provider=MockVisionProvider())
        parser = SchematicParser(ocr_engine=ocr_engine, vision_engine=vision_engine)

        img_bytes = build_test_image(200, 150)
        res = await parser.parse_drawing(img_bytes, mode="hybrid")

        assert res.status == "success"
        assert len(res.findings) > 0


# ── Phase 4 Ingestion Handoff Integration ─────────────────────────────────────

class TestPhase4Handoff:
    """Verifies that Phase 4 artifacts flagged needs_ocr can be consumed by Phase 5."""

    @pytest.mark.anyio
    async def test_consume_synthetic_ndt_sample_provenance(self):
        sample_path = Path(__file__).resolve().parent.parent.parent / "data" / "samples" / "corrosion_inspection_c101.pdf"
        assert sample_path.is_file()

        # Simulate Phase 4 scanned page handoff
        prov = DocumentProvenance(
            source_filename="corrosion_inspection_c101.pdf",
            source_sha256="sample_c101_hash",
            page_number=1,
        )

        mock_ocr = MockOCRProvider(
            predefined_text="Equipment ID: C-101\nNominal: 12.0 mm\nReadings: 11.2, 10.9, 10.5, 10.1"
        )
        engine = LocalOCREngine(provider=mock_ocr)
        img_bytes = build_test_image(200, 100)

        ocr_result = await engine.extract_from_image(img_bytes, provenance=prov)
        assert ocr_result.provenance.source_filename == "corrosion_inspection_c101.pdf"
        assert ocr_result.provenance.page_number == 1
        assert "C-101" in ocr_result.text
        assert "11.2" in ocr_result.text


# ── API Endpoints Tests ───────────────────────────────────────────────────────

class TestVisionAPI:
    """Verifies /api/v1/vision REST endpoints."""

    def test_api_ocr_with_mock_provider(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "inference_provider", "mock")

        img_bytes = build_test_image(150, 100)
        response = client.post(
            "/api/v1/vision/ocr",
            files={"file": ("test_scan.png", img_bytes, "image/png")},
            data={"page_number": 1, "preprocess": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "tokens" in data
        assert "mean_confidence" in data
        assert data["status"] == "success"
        assert data["engine_name"] == "mock_ocr"

    def test_api_analyze_drawing_with_mock_provider(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "inference_provider", "mock")

        img_bytes = build_test_image(200, 150)
        response = client.post(
            "/api/v1/vision/analyze-drawing",
            files={"file": ("drawing.png", img_bytes, "image/png")},
            data={"mode": "hybrid"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "findings" in data
        assert "candidate_tags" in data
        assert "C-101" in data["equipment_tags"]
        assert "PT-101" in data["instrument_tags"]
        assert data["status"] == "success"

    def test_api_ocr_missing_input_returns_400(self):
        response = client.post("/api/v1/vision/ocr", data={"page_number": 1})
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "MISSING_INPUT"

    def test_api_ocr_nonexistent_sha_returns_404(self):
        response = client.post(
            "/api/v1/vision/ocr",
            data={"document_sha256": "nonexistent_sha256_hash", "page_number": 1},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "DOCUMENT_NOT_FOUND"


# ── Air-Gap & Sovereignty Verification ────────────────────────────────────────

def test_air_gap_no_outbound_network_calls(monkeypatch):
    """
    Verify that Phase 5 OCR and Vision engines make zero outbound network connections.
    """
    def forbidden_connect(*args, **kwargs):
        raise AssertionError("Air-gap violation: Attempted outbound socket connection during Vision/OCR!")

    monkeypatch.setattr(socket, "create_connection", forbidden_connect)

    mock_ocr = MockOCRProvider()
    engine = LocalOCREngine(provider=mock_ocr)
    img_bytes = build_test_image(100, 100)

    import asyncio
    res = asyncio.run(engine.extract_from_image(img_bytes))
    assert res.status == "success"
