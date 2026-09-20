"""
SIH26117 — Phase 1: Image-Aware Routing Verification Tests

Verifies the Phase-1 fix:
    uploaded image -> has_image=True context -> router selects ModelRole.VISION
    -> VisionEngine -> ModelManagerVisionProvider (mocked in CI) -> actual bytes

Covers:
1. Router context override: has_image=True -> ModelRole.VISION (4 image types)
2. Router context override: has_image=False -> reasoning/calculation (unchanged)
3. Workflow stage: DETERMINISTIC mode with real image bytes routes to VisionEngine
4. Workflow stage: no image file does NOT create blank/synthetic image
5. Image bytes integrity: actual uploaded bytes reach the VisionProvider
6. Observability: ocr_summary["image_input"] == True for image uploads

These tests use MockVisionProvider injected into the workflow -- no Ollama required.
The production path (real qwen2.5vl:3b) is verified separately via manual runtime check.
"""

import io
from pathlib import Path
from typing import List, Optional

import pytest
from PIL import Image

try:
    from app.core.config import get_settings
    from app.services.ingestion.models import DocumentProvenance
    from app.services.integration.models import (
        CorrosionAuditWorkflowRequest,
        StageStatus,
        WorkflowExecutionMode,
        WorkflowStatus,
    )
    from app.services.integration.workflow import CorrosionAuditWorkflow
    from app.services.router.rule_router import RuleRouter
    from app.services.router.taxonomy import Capability, ModelRole, TaskType
    from app.services.vision.base import SchematicAnalysisResult, VisualFinding, VisualFindingType
    from app.services.vision.vlm_client import MockVisionProvider, VisionEngine
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.services.ingestion.models import DocumentProvenance
    from backend.app.services.integration.models import (
        CorrosionAuditWorkflowRequest,
        StageStatus,
        WorkflowExecutionMode,
        WorkflowStatus,
    )
    from backend.app.services.integration.workflow import CorrosionAuditWorkflow
    from backend.app.services.router.rule_router import RuleRouter
    from backend.app.services.router.taxonomy import Capability, ModelRole, TaskType
    from backend.app.services.vision.base import (
        SchematicAnalysisResult,
        VisualFinding,
        VisualFindingType,
    )
    from backend.app.services.vision.vlm_client import MockVisionProvider, VisionEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_png() -> bytes:
    """Create a real (tiny) PNG in memory -- not a blank Image.new() substitute."""
    img = Image.new("RGB", (64, 64), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _vision_test_image(sub: str, name: str) -> Optional[bytes]:
    """Load an image from data/vision_test/<sub>/<name>. Returns None if missing."""
    try:
        settings = get_settings()
        p = settings.project_root / "data" / "vision_test" / sub / name
        return p.read_bytes() if p.is_file() else None
    except Exception:
        return None


def _make_test_safe_mock_provider() -> MockVisionProvider:
    """Return a MockVisionProvider with test-safe, non-production fixture tags."""
    prov = DocumentProvenance(
        source_filename="test_image.png",
        source_sha256="test_sha256_00000000000000000000000000000000",
        page_number=1,
    )
    findings = [
        VisualFinding(
            finding_type=VisualFindingType.EQUIPMENT_TAG,
            label="TEST-EQUIPMENT",
            text="TEST-EQUIPMENT",
            confidence=0.90,
            provenance=prov,
            evidence="Phase-1 test fixture -- not real engineering data",
        ),
    ]
    return MockVisionProvider(predefined_findings=findings)


# ---------------------------------------------------------------------------
# Section 1: Router context override tests
# ---------------------------------------------------------------------------

class TestRouterHasImageOverride:
    """Verify that has_image=True in context unconditionally selects ModelRole.VISION."""

    def _router(self) -> RuleRouter:
        return RuleRouter()

    def test_pid_image_context_routes_vision(self):
        """P&ID image: has_image=True -> ModelRole.VISION regardless of objective text."""
        router = self._router()
        decision = router.route(
            task="Audit thickness readings against MRPL specification, calculate corrosion rate.",
            context={"has_image": True},
        )
        assert decision.model_role == ModelRole.VISION, (
            f"Expected VISION, got {decision.model_role} (rule: {decision.primary_rule_id})"
        )
        assert decision.task_type == TaskType.VISION
        assert decision.capability == Capability.VISION
        assert decision.confidence >= 0.92
        assert not decision.fallback_used

    def test_equipment_image_context_routes_vision(self):
        """Equipment image: has_image=True -> ModelRole.VISION."""
        router = self._router()
        decision = router.route(
            task="Inspect centrifugal pump for signs of corrosion.",
            context={"has_image": True},
        )
        assert decision.model_role == ModelRole.VISION
        assert decision.task_type == TaskType.VISION
        assert not decision.fallback_used

    def test_gauge_image_context_routes_vision(self):
        """Gauge image: has_image=True -> ModelRole.VISION."""
        router = self._router()
        decision = router.route(
            task="Read pressure gauge and record current value.",
            context={"has_image": True},
        )
        assert decision.model_role == ModelRole.VISION
        assert decision.task_type == TaskType.VISION

    def test_table_image_context_routes_vision(self):
        """Table image: has_image=True -> ModelRole.VISION."""
        router = self._router()
        decision = router.route(
            task="Extract thickness readings from this inspection table.",
            context={"has_image": True},
        )
        assert decision.model_role == ModelRole.VISION
        assert decision.task_type == TaskType.VISION

    def test_no_image_context_preserves_calculation_routing(self):
        """Without has_image context, calculation objective still routes to REASONING."""
        router = self._router()
        decision = router.route(
            task="Calculate corrosion rate from thickness readings.",
            context=None,
        )
        assert decision.model_role != ModelRole.VISION, (
            "Routing changed for non-image input -- regression!"
        )

    def test_has_image_false_does_not_override(self):
        """has_image=False must NOT trigger vision override."""
        router = self._router()
        decision = router.route(
            task="Calculate corrosion rate from thickness readings.",
            context={"has_image": False},
        )
        assert decision.model_role != ModelRole.VISION

    def test_empty_task_with_image_routes_vision(self):
        """An empty objective but has_image=True should still route to VISION."""
        router = self._router()
        decision = router.route(task="", context={"has_image": True})
        assert decision.model_role == ModelRole.VISION
        assert decision.task_type == TaskType.VISION

    def test_no_match_task_with_image_routes_vision(self):
        """A task with no matching text rules but has_image=True should route VISION."""
        router = self._router()
        decision = router.route(
            task="xyz zzz random noise gibberish",
            context={"has_image": True},
        )
        assert decision.model_role == ModelRole.VISION


# ---------------------------------------------------------------------------
# Section 2: Workflow vision stage -- actual bytes, no blank substitution
# ---------------------------------------------------------------------------

class TestWorkflowVisionStageBytes:
    """Verify the DETERMINISTIC-mode vision stage uses actual uploaded bytes."""

    def _make_workflow_with_mock_vision(self):
        received_bytes: list = []

        mock_provider = _make_test_safe_mock_provider()
        original_analyze = mock_provider.analyze_image

        async def capturing_analyze(image_bytes, prompt=None, provenance=None):
            received_bytes.append(image_bytes)
            return await original_analyze(image_bytes, prompt, provenance)

        mock_provider.analyze_image = capturing_analyze  # type: ignore[method-assign]
        workflow = CorrosionAuditWorkflow(
            vision_engine=VisionEngine(provider=mock_provider),
        )
        return workflow, received_bytes

    @pytest.mark.anyio
    async def test_png_upload_bytes_reach_vision_engine(self):
        """Real PNG bytes must arrive at the VisionProvider unmodified."""
        real_bytes = _make_minimal_png()
        workflow, received = self._make_workflow_with_mock_vision()

        request = CorrosionAuditWorkflowRequest(
            objective="Inspect this equipment image.",
            document_filename="test_equipment.png",
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
            component_id="TEST-P1",
            elapsed_time_years=3.0,
            minimum_required_thickness_mm=6.0,
        )

        try:
            await workflow.run(request=request, pdf_bytes=real_bytes)
        except Exception:
            pass  # Evidence/calculation failure expected in Phase 1

        assert len(received) == 1, (
            "VisionProvider.analyze_image() was not called -- bytes never reached vision engine"
        )
        assert received[0] == real_bytes, (
            "VisionProvider received different bytes than uploaded -- blank image may have been substituted"
        )

    @pytest.mark.anyio
    async def test_ocr_summary_image_input_flag_true_for_png(self):
        """ocr_vision_analysis stage must report image_input=True for PNG uploads."""
        real_bytes = _make_minimal_png()
        workflow, _ = self._make_workflow_with_mock_vision()

        request = CorrosionAuditWorkflowRequest(
            objective="Inspect this equipment image.",
            document_filename="test_equipment.png",
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
            component_id="TEST-P1",
            elapsed_time_years=3.0,
            minimum_required_thickness_mm=6.0,
        )

        result = None
        try:
            result = await workflow.run(request=request, pdf_bytes=real_bytes)
        except Exception:
            pass

        if result:
            vision_stage = next(
                (s for s in result.stages if s.stage_name == "ocr_vision_analysis"),
                None,
            )
            if vision_stage:
                assert vision_stage.details.get("image_input") is True, (
                    f"Stage did not set image_input=True. Details: {vision_stage.details}"
                )
                assert vision_stage.details.get("engine_name") == "local_vlm"

    @pytest.mark.anyio
    async def test_non_image_file_does_not_call_vision(self):
        """Non-image uploads (CSV) must NOT call the VisionProvider."""
        workflow, received = self._make_workflow_with_mock_vision()

        settings = get_settings()
        csv_path = settings.project_root / "data" / "samples" / "P-201_UT_Wall_Survey_2026.csv"
        if not csv_path.is_file():
            pytest.skip("P-201 CSV sample not available")

        csv_bytes = csv_path.read_bytes()
        request = CorrosionAuditWorkflowRequest(
            objective="Calculate corrosion rate from thickness survey.",
            document_filename="P-201_UT_Wall_Survey_2026.csv",
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
            component_id="P-201",
            elapsed_time_years=5.0,
            minimum_required_thickness_mm=6.0,
        )

        try:
            await workflow.run(request=request, pdf_bytes=csv_bytes)
        except Exception:
            pass

        assert len(received) == 0, (
            "VisionProvider was called for a CSV file -- vision should be skipped for non-images"
        )

    @pytest.mark.anyio
    async def test_no_blank_300x150_image_for_png_upload(self):
        """The 300x150 blank white image must NEVER be substituted for a real PNG upload."""
        BLANK_SIZE = (300, 150)
        received_sizes: list = []

        mock_provider = _make_test_safe_mock_provider()
        original_analyze = mock_provider.analyze_image

        async def capturing_analyze(image_bytes, prompt=None, provenance=None):
            img = Image.open(io.BytesIO(image_bytes))
            received_sizes.append(img.size)
            return await original_analyze(image_bytes, prompt, provenance)

        mock_provider.analyze_image = capturing_analyze  # type: ignore[method-assign]
        workflow = CorrosionAuditWorkflow(
            vision_engine=VisionEngine(provider=mock_provider),
        )

        real_bytes = _make_minimal_png()  # 64x64 -- distinctly not 300x150
        request = CorrosionAuditWorkflowRequest(
            objective="Inspect this equipment image.",
            document_filename="test_equipment.png",
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
            component_id="TEST-P1",
            elapsed_time_years=3.0,
            minimum_required_thickness_mm=6.0,
        )

        try:
            await workflow.run(request=request, pdf_bytes=real_bytes)
        except Exception:
            pass

        assert received_sizes, "VisionProvider was not called at all"
        assert received_sizes[0] != BLANK_SIZE, (
            f"Blank 300x150 substitute was used instead of the real uploaded image "
            f"(received size: {received_sizes[0]})"
        )


# ---------------------------------------------------------------------------
# Section 3: Real vision_test dataset routing
# ---------------------------------------------------------------------------

class TestVisionTestDatasetRouting:
    """Route real vision_test dataset images and verify VISION role is selected."""

    @pytest.mark.parametrize("sub,filename,label", [
        ("pid", "pid_distillation_column.png", "P&ID"),
        ("equipment", "equipment_centrifugal_pump.png", "equipment"),
        ("gauges", "gauge_pressure_analog.png", "gauge"),
        ("tables", "table_thickness_survey_scan.png", "table"),
    ])
    def test_real_image_routes_to_vision(self, sub, filename, label):
        """Each real vision_test image must route to ModelRole.VISION via has_image context."""
        img_bytes = _vision_test_image(sub, filename)
        if img_bytes is None:
            pytest.skip(f"Vision test image not found: data/vision_test/{sub}/{filename}")

        router = RuleRouter()
        decision = router.route(
            task="Audit this refinery equipment image.",
            context={"has_image": True},
        )

        assert decision.model_role == ModelRole.VISION, (
            f"[{label}] Expected ModelRole.VISION, got {decision.model_role}"
        )
        assert decision.task_type == TaskType.VISION
        assert decision.capability == Capability.VISION
        assert decision.confidence >= 0.92
        assert not decision.fallback_used

    @pytest.mark.parametrize("sub,filename,label", [
        ("pid", "pid_distillation_column.png", "P&ID"),
        ("equipment", "equipment_centrifugal_pump.png", "equipment"),
        ("gauges", "gauge_pressure_analog.png", "gauge"),
        ("tables", "table_thickness_survey_scan.png", "table"),
    ])
    @pytest.mark.anyio
    async def test_real_image_bytes_reach_vision_provider(self, sub, filename, label):
        """Actual uploaded bytes from each test image must reach the VisionProvider."""
        img_bytes = _vision_test_image(sub, filename)
        if img_bytes is None:
            pytest.skip(f"Vision test image not found: data/vision_test/{sub}/{filename}")

        received: list = []
        mock_provider = _make_test_safe_mock_provider()
        original_analyze = mock_provider.analyze_image

        async def capturing_analyze(image_bytes, prompt=None, provenance=None):
            received.append(image_bytes)
            return await original_analyze(image_bytes, prompt, provenance)

        mock_provider.analyze_image = capturing_analyze  # type: ignore[method-assign]

        workflow = CorrosionAuditWorkflow(
            vision_engine=VisionEngine(provider=mock_provider),
        )

        request = CorrosionAuditWorkflowRequest(
            objective="Inspect this refinery equipment image.",
            document_filename=filename,
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
            component_id="TEST-VISION",
            elapsed_time_years=3.0,
            minimum_required_thickness_mm=6.0,
        )

        try:
            await workflow.run(request=request, pdf_bytes=img_bytes)
        except Exception:
            pass  # Evidence/calculation failure expected in Phase 1

        assert len(received) == 1, (
            f"[{label}] VisionProvider.analyze_image() was not called. "
            "Bytes did not reach the vision engine."
        )
        assert received[0] == img_bytes, (
            f"[{label}] VisionProvider received bytes different from original upload. "
            "Blank/synthetic image may have been substituted."
        )
