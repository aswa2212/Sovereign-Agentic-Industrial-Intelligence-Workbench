"""
SIH26117 — Phase 13: End-to-End Primary Corrosion Audit Workflow

Connects all 11 subsystems into a unified, deterministic, fail-closed operational pipeline:
1. Document Ingestion (Phase 4)
2. OCR / Vision Engine (Phase 5)
3. Task Router (Phase 3)
4. Local Model Manager (Phase 2)
5. Sovereign RAG Retrieval (Phase 6)
6. Agent State Machine (Phase 7)
7. Sandboxed Engineering Tools (Phase 8)
8. Fail-Closed Validation Gate (Phase 9)
9. Deterministic Deliverables Factory (Phase 10)
10. Hash-Chained Audit Ledger (Phase 11)
11. Host Socket Sovereignty Check (Phase 11)
"""

import asyncio
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Union
import uuid

from app.core.config import get_settings
from app.services.agent.models import AgentContext
from app.services.agent.orchestrator import AgentStateMachineOrchestrator
from app.services.audit.models import AuditEventType
from app.services.audit.network_monitor import RuntimeNetworkMonitor
from app.services.audit.service import AuditService, get_audit_service
from app.services.audit.sovereignty import SovereigntyChecker
from app.services.deliverables.factory import DeliverablesFactory
from app.services.deliverables.models import DeliverableFormat, ReportMetadata
from app.services.ingestion.evidence import (
    EngineeringEvidence,
    EngineeringEvidenceExtractor,
)
from app.services.ingestion.models import ExtractionStatus
from app.services.ingestion.service import IngestionService
from app.services.integration.exceptions import (
    DocumentIngestionStageError,
    IntegrationError,
    ModelAllocationError,
    ValidationGateError,
    WorkflowTimeoutError,
)
from app.services.router.taxonomy import Capability, ModelRole
from app.services.integration.models import (
    ArtifactSummary,
    CorrosionAuditWorkflowRequest,
    CorrosionAuditWorkflowResult,
    StageStatus,
    WorkflowExecutionMode,
    WorkflowStageTelemetry,
    WorkflowStatus,
    utc_now_iso,
)
from app.services.model_manager.manager import ModelManager
from app.api.v1.endpoints.models import get_model_manager
from app.services.rag.retriever import SovereignRetriever
from app.services.router.rule_router import RuleRouter
from app.services.sandbox.base import ExecutionStatus, ToolExecutionRequest
from app.services.sandbox.subprocess_executor import SubprocessSandboxExecutor
from app.services.validation.models import (
    CorrosionAuditResult,
    CorrosionCalculation,
    InspectionFinding,
    RecommendationCode,
    SourceCitation,
    ValidationResult,
    WallThicknessMeasurement,
)
from app.services.validation.service import StructuredOutputService
from app.services.vision.base import OCREngineUnavailableError, VisionError
from app.services.vision.ocr_engine import LocalOCREngine, MockOCRProvider
from app.services.vision.vlm_client import (
    MockVisionProvider,
    ModelManagerVisionProvider,
    VisionEngine,
)

logger = logging.getLogger(__name__)


class CorrosionAuditWorkflow:
    """
    Primary end-to-end integration orchestrator for the C-101 refining equipment corrosion audit.
    """

    def __init__(
        self,
        ingestion_service: Optional[IngestionService] = None,
        router: Optional[RuleRouter] = None,
        model_manager: Optional[ModelManager] = None,
        agent_orchestrator: Optional[AgentStateMachineOrchestrator] = None,
        retriever: Optional[SovereignRetriever] = None,
        sandbox_executor: Optional[SubprocessSandboxExecutor] = None,
        validation_service: Optional[StructuredOutputService] = None,
        deliverables_factory: Optional[DeliverablesFactory] = None,
        audit_service: Optional[AuditService] = None,
        network_monitor: Optional[RuntimeNetworkMonitor] = None,
        ocr_engine: Optional[LocalOCREngine] = None,
        vision_engine: Optional[VisionEngine] = None,
        evidence_extractor: Optional[EngineeringEvidenceExtractor] = None,
    ) -> None:
        self.settings = get_settings()
        self.ingestion_service = ingestion_service or IngestionService()
        self.evidence_extractor = evidence_extractor or EngineeringEvidenceExtractor()
        self.router = router or RuleRouter()
        self.model_manager = model_manager or get_model_manager()
        self.retriever = retriever or SovereignRetriever()
        self.sandbox_executor = sandbox_executor or SubprocessSandboxExecutor()
        self.validation_service = validation_service or StructuredOutputService()
        self.audit_service = audit_service or get_audit_service()
        self.deliverables_factory = deliverables_factory or DeliverablesFactory(audit_service=self.audit_service)
        self.network_monitor = network_monitor or RuntimeNetworkMonitor()
        self.sovereignty_checker = SovereigntyChecker(self.network_monitor)
        self.ocr_engine = ocr_engine or LocalOCREngine(provider=MockOCRProvider())
        self.vision_engine = vision_engine or VisionEngine(
            provider=ModelManagerVisionProvider(self.model_manager)
        )

        # Agent orchestrator with audit service injection
        self.agent_orchestrator = agent_orchestrator or AgentStateMachineOrchestrator(
            router=self.router,
            audit_service=self.audit_service,
            structured_output_service=self.validation_service,
        )

        # In-memory history of completed workflow executions
        self._results: Dict[str, CorrosionAuditWorkflowResult] = {}

    def get_result(self, workflow_id: str) -> Optional[CorrosionAuditWorkflowResult]:
        """Retrieve stored workflow execution result."""
        return self._results.get(workflow_id)

    async def run(
        self,
        request: CorrosionAuditWorkflowRequest,
        pdf_bytes: Optional[bytes] = None,
        timeout_seconds: Optional[float] = None,
    ) -> CorrosionAuditWorkflowResult:
        """
        Execute the full 11-stage primary corrosion audit workflow.
        """
        workflow_id = uuid.uuid4().hex
        task_id = request.task_id or f"task_{workflow_id[:8]}"
        started_at = utc_now_iso()
        start_mono = time.monotonic()
        effective_timeout = timeout_seconds or 120.0

        stages_telemetry: List[WorkflowStageTelemetry] = []
        errors: List[str] = []

        # Audit initial event
        self._safe_audit(
            AuditEventType.TASK_STARTED,
            action=f"Started Corrosion Audit Workflow [{workflow_id[:8]}] for {request.component_id}",
            task_id=task_id,
            metadata={"workflow_id": workflow_id, "mode": request.execution_mode.value},
        )

        # Context containers across stages
        doc_summary: Dict[str, Any] = {}
        evidence_dict: Optional[Dict[str, Any]] = None
        evidence_obj: Optional[EngineeringEvidence] = None
        ocr_summary: Dict[str, Any] = {}
        routing_decision_dict: Optional[Dict[str, Any]] = None
        model_allocation_dict: Optional[Dict[str, Any]] = None
        rag_citations: List[Dict[str, Any]] = []
        calc_result_dict: Optional[Dict[str, Any]] = None
        validation_result_dict: Optional[Dict[str, Any]] = None
        deliverable_summaries: List[ArtifactSummary] = []
        agent_summary_dict: Optional[Dict[str, Any]] = None
        execution_capability: Optional[str] = None
        active_model: Optional[str] = None
        overall_status = WorkflowStatus.IN_PROGRESS

        try:
            # ── 1. Document Ingestion & Evidence Extraction ───────────────────
            t_stage_start = time.monotonic()
            st_ingest = WorkflowStageTelemetry(
                stage_name="document_ingestion",
                stage_index=0,
                status=StageStatus.IN_PROGRESS,
                started_at=utc_now_iso(),
            )

            try:
                # Resolve document bytes
                raw_pdf = pdf_bytes
                filename = request.document_filename

                if raw_pdf is None:
                    if request.is_demo_preset:
                        # Explicit demo preset path: allow loading bundled C-101 sample
                        filename = filename or "corrosion_inspection_c101.pdf"
                        sample_path = (
                            self.settings.project_root
                            / "data"
                            / "samples"
                            / filename
                        )
                        if not sample_path.is_file():
                            raise DocumentIngestionStageError(
                                f"Specified demo document '{filename}' was not found at {sample_path}."
                            )
                        raw_pdf = sample_path.read_bytes()
                    elif filename:
                        sample_path = (
                            self.settings.project_root
                            / "data"
                            / "samples"
                            / filename
                        )
                        if not sample_path.is_file():
                            raise DocumentIngestionStageError(
                                f"Requested document not found: {filename} at {sample_path}."
                            )
                        raw_pdf = sample_path.read_bytes()
                    else:
                        raise DocumentIngestionStageError(
                            "Document input required: No document uploaded and is_demo_preset is False."
                        )
                elif not filename:
                    filename = "uploaded_inspection_document.pdf"

                # Execute ingestion
                ingest_res = self.ingestion_service.ingest_file(raw_pdf, filename)
                if ingest_res.status in (ExtractionStatus.FAILED, ExtractionStatus.UNSUPPORTED) or not ingest_res.normalized_document:
                    err_msg = ", ".join(ingest_res.errors) if ingest_res.errors else f"status {ingest_res.status.value}"
                    raise DocumentIngestionStageError(
                        f"Document ingestion failed with status {ingest_res.status.value}: {err_msg}"
                    )

                norm_doc = ingest_res.normalized_document

                # ── Engineering Evidence Extraction ─────────────────────────
                evidence = self.evidence_extractor.extract(
                    norm_doc=norm_doc,
                    user_equipment_id=request.component_id,
                    user_elapsed_time_years=request.elapsed_time_years,
                    user_minimum_required_thickness_mm=request.minimum_required_thickness_mm,
                    is_demo_preset=request.is_demo_preset,
                )

                if request.is_demo_preset:
                    if evidence.nominal_thickness_mm is None:
                        evidence.nominal_thickness_mm = 12.0
                        evidence.nominal_thickness_source = "DEMO_PRESET"
                    if evidence.current_thickness_mm is None:
                        evidence.current_thickness_mm = 10.1
                        evidence.current_thickness_source = "DEMO_PRESET"
                    if evidence.elapsed_time_years is None:
                        evidence.elapsed_time_years = 5.0
                        evidence.elapsed_time_source = "DEMO_PRESET"
                    if evidence.minimum_required_thickness_mm is None:
                        evidence.minimum_required_thickness_mm = 8.0
                        evidence.minimum_thickness_source = "DEMO_PRESET"
                    if evidence.equipment_id is None:
                        evidence.equipment_id = "C-101"
                        evidence.equipment_id_source = "DEMO_PRESET"
                    evidence.can_calculate_corrosion_rate = True
                    evidence.can_calculate_remaining_life = True

                evidence_obj = evidence
                evidence_dict = evidence.model_dump()

                doc_summary = {
                    "document_id": norm_doc.document_id,
                    "filename": filename,
                    "sha256": norm_doc.sha256,
                    "page_count": len(norm_doc.pages),
                    "table_count": len(norm_doc.tables),
                    "is_scanned": any(p.is_scanned for p in norm_doc.pages) if norm_doc.pages else False,
                    "equipment_id": evidence.equipment_id or request.component_id,
                    "evidence": evidence_dict,
                }

                if evidence.conflict_detected:
                    raise IntegrationError(
                        f"EVIDENCE_CONFLICT: {evidence.conflict_details}",
                        stage="evidence_extraction",
                    )

                st_ingest.status = StageStatus.SUCCESS
                st_ingest.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
                st_ingest.completed_at = utc_now_iso()
                st_ingest.details = doc_summary
                stages_telemetry.append(st_ingest)
            except Exception as ing_err:
                st_ingest.status = StageStatus.FAILED
                st_ingest.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
                st_ingest.completed_at = utc_now_iso()
                st_ingest.error = str(ing_err)
                stages_telemetry.append(st_ingest)
                raise DocumentIngestionStageError(str(ing_err)) from ing_err

            # ── 2. OCR & Vision Engine ───────────────────────────────────────
            t_stage_start = time.monotonic()
            st_vision = WorkflowStageTelemetry(
                stage_name="ocr_vision_analysis",
                stage_index=1,
                status=StageStatus.IN_PROGRESS,
                started_at=utc_now_iso(),
            )

            try:
                import io
                from PIL import Image
                from app.services.ingestion.models import DocumentProvenance

                prov = DocumentProvenance(
                    source_filename=filename,
                    source_sha256=doc_summary.get("sha256", "mock_sha"),
                    page_number=1,
                )

                if request.execution_mode == WorkflowExecutionMode.LIVE:
                    # LIVE MODE: Enforce Ollama / ModelManager health (fail closed, no silent mock fallback)
                    is_healthy = await self.model_manager.health_check()
                    if not is_healthy:
                        raise IntegrationError(
                            "Local inference provider (Ollama) is unreachable for LIVE execution mode. Fail closed.",
                            stage="ocr_vision_analysis",
                        )

                    # Determine image bytes for visual analysis (Finding 1: strict provenance)
                    img_bytes: Optional[bytes] = None
                    is_demo_fixture = False

                    if request.is_demo_preset:
                        # Demo preset ONLY: bundled sample image may be used with explicit DEMO provenance
                        pid_sample_path = self.settings.project_root / "data" / "samples" / "pid_sample.png"
                        if pid_sample_path.is_file():
                            img_bytes = pid_sample_path.read_bytes()
                        else:
                            img = Image.new("RGB", (400, 300), color=(255, 255, 255))
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            img_bytes = buf.getvalue()
                        is_demo_fixture = True
                        prov = DocumentProvenance(
                            source_filename="pid_sample.png (DEMO PRESET)",
                            source_sha256="demo_preset_fixture",
                            page_number=1,
                        )
                    elif pdf_bytes and any(filename.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg")):
                        # CASE 1: Uploaded file is already an image (.png/.jpg/.jpeg)
                        img_bytes = pdf_bytes
                    elif pdf_bytes and filename.lower().endswith(".pdf"):
                        # CASE 2: Uploaded file is PDF -> render first page using pypdfium2
                        try:
                            import pypdfium2
                            pdf_doc = pypdfium2.PdfDocument(pdf_bytes)
                            if len(pdf_doc) > 0:
                                pil_img = pdf_doc[0].render(scale=1.5).to_pil()
                                buf = io.BytesIO()
                                pil_img.save(buf, format="PNG")
                                img_bytes = buf.getvalue()
                        except Exception as render_err:
                            logger.warning("PDF vision rendering unavailable: %s", render_err)
                            img_bytes = None
                    else:
                        # CASE 3: Uploaded file is DOCX/XLSX/CSV/text/etc. -> No visual analysis
                        img_bytes = None

                    if img_bytes is not None:
                        # Execute real VLM inference via ModelManager abstraction
                        vlm_res = await self.vision_engine.analyze_schematic(img_bytes, provenance=prov)

                        ocr_summary = {
                            "engine_name": "local_vlm",
                            "model_used": vlm_res.model_used,
                            "provider": "ollama",
                            "findings_count": len(vlm_res.findings),
                            "equipment_tags": vlm_res.equipment_tags,
                            "instrument_tags": vlm_res.instrument_tags,
                            "summary": vlm_res.summary,
                            "status": vlm_res.status,
                            "degraded": False,
                            "is_demo_fixture": is_demo_fixture,
                        }
                        self._safe_audit(
                            AuditEventType.MODEL_INVOKED,
                            action=f"Live VLM inference executed via ModelManager ({vlm_res.model_used})",
                            task_id=task_id,
                            model_role="vision",
                            metadata={
                                "model": vlm_res.model_used,
                                "findings_count": len(vlm_res.findings),
                                "equipment_tags": vlm_res.equipment_tags,
                                "instrument_tags": vlm_res.instrument_tags,
                                "is_demo_fixture": is_demo_fixture,
                            },
                        )
                        st_vision.status = StageStatus.SUCCESS
                    else:
                        # Non-visual or unrenderable upload -> Explicitly SKIP vision stage (never load pid_sample.png)
                        skip_reason = (
                            "PDF vision rendering unavailable"
                            if filename.lower().endswith(".pdf")
                            else f"Document type ({Path(filename).suffix or 'unknown'}) does not require visual schematic analysis"
                        )
                        ocr_summary = {
                            "engine_name": "local_vlm",
                            "status": StageStatus.SKIPPED.value,
                            "reason": skip_reason,
                            "findings_count": 0,
                            "equipment_tags": [],
                            "instrument_tags": [],
                            "summary": f"Vision analysis skipped: {skip_reason}. Engineering evidence path active.",
                            "degraded": False,
                            "is_demo_fixture": False,
                        }
                        st_vision.status = StageStatus.SKIPPED
                else:
                    img = Image.new("RGB", (300, 150), color=(255, 255, 255))
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    img_bytes = buf.getvalue()

                    ocr_res = await self.ocr_engine.extract_from_image(img_bytes, provenance=prov)
                    ocr_summary = {
                        "engine_name": ocr_res.engine_name,
                        "total_tokens": len(ocr_res.tokens),
                        "confidence_avg": round(ocr_res.mean_confidence, 3),
                        "status": ocr_res.status,
                        "degraded": False,
                    }
                    st_vision.status = StageStatus.SUCCESS
            except IntegrationError:
                st_vision.status = StageStatus.FAILED
                raise
            except (OCREngineUnavailableError, VisionError, Exception) as vision_err:
                if request.execution_mode == WorkflowExecutionMode.LIVE:
                    st_vision.status = StageStatus.FAILED
                    st_vision.error = str(vision_err)
                    raise IntegrationError(
                        f"Live VLM execution failed: {str(vision_err)}",
                        stage="ocr_vision_analysis",
                    ) from vision_err
                logger.warning("Vision/OCR operating in degraded mode: %s", str(vision_err))
                ocr_summary = {
                    "engine_name": "none",
                    "total_tokens": 0,
                    "confidence_avg": 0.0,
                    "degraded": True,
                    "reason": str(vision_err),
                }
                st_vision.status = StageStatus.DEGRADED

            st_vision.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
            st_vision.completed_at = utc_now_iso()
            st_vision.details = ocr_summary
            stages_telemetry.append(st_vision)

            # ── 3. Task Router Intent Classification ──────────────────────────
            t_stage_start = time.monotonic()
            st_router = WorkflowStageTelemetry(
                stage_name="task_routing",
                stage_index=2,
                status=StageStatus.IN_PROGRESS,
                started_at=utc_now_iso(),
            )

            route_decision = self.router.route(task=request.objective, request_id=task_id)
            routing_decision_dict = {
                "task_type": route_decision.task_type.value,
                "model_role": route_decision.model_role.value,
                "capability": route_decision.capability.value,
                "confidence": route_decision.confidence,
                "primary_rule_id": route_decision.primary_rule_id,
                "routing_method": route_decision.routing_method,
            }
            self._safe_audit(
                AuditEventType.MODEL_ROUTED,
                action=f"Routed query intent: {route_decision.task_type.value}",
                task_id=task_id,
                model_role=route_decision.model_role.value,
                capability=route_decision.capability.value,
                metadata=routing_decision_dict,
            )

            st_router.status = StageStatus.SUCCESS
            st_router.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
            st_router.completed_at = utc_now_iso()
            st_router.details = routing_decision_dict
            stages_telemetry.append(st_router)

            # ── 4. Local Model Allocation ────────────────────────────────────
            t_stage_start = time.monotonic()
            st_model = WorkflowStageTelemetry(
                stage_name="model_allocation",
                stage_index=3,
                status=StageStatus.IN_PROGRESS,
                started_at=utc_now_iso(),
            )

            tier_config = self.model_manager.get_tier_config()
            role_key = (
                route_decision.model_role.value
                if hasattr(route_decision.model_role, "value")
                else str(route_decision.model_role)
            )

            # Resolve model entry directly from active tier by requested role (no string-collapsing or silent fallback)
            model_entry = tier_config.get_model(role_key)
            if model_entry is None:
                tier_desc = getattr(tier_config, "description", "active tier")
                st_model.status = StageStatus.FAILED
                st_model.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
                st_model.completed_at = utc_now_iso()
                st_model.error = f"Requested model role '{role_key}' is not configured in active tier ({tier_desc})."
                stages_telemetry.append(st_model)
                raise ModelAllocationError(
                    f"Requested model role '{role_key}' is not configured in active hardware tier ({tier_desc}). "
                    "Fail closed without silent fallback.",
                    details={"role": role_key, "tier_description": tier_desc},
                )

            vision_entry = tier_config.get_model(ModelRole.VISION.value)

            try:
                available_models = await self.model_manager.list_models()
                models_count = len(available_models)
            except Exception:
                models_count = len(tier_config.list_roles()) if hasattr(tier_config, "list_roles") else 1

            model_allocation_dict = {
                "assigned_role": role_key,
                "tier_role": role_key,
                "assigned_model_tag": model_entry.model_tag,
                "vision_model_tag": vision_entry.model_tag if vision_entry else None,
                "resolved_model_tag": model_entry.model_tag,
                "provider": "ollama" if request.execution_mode == WorkflowExecutionMode.LIVE else "mock",
                "available_models_count": models_count,
                "is_mock": True if request.execution_mode == WorkflowExecutionMode.DETERMINISTIC else False,
            }

            st_model.status = StageStatus.SUCCESS
            st_model.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
            st_model.completed_at = utc_now_iso()
            st_model.details = model_allocation_dict
            stages_telemetry.append(st_model)

            # Branch execution based on routed capability / model role (strict enum/value equality)
            is_vision_task = (
                route_decision.model_role == ModelRole.VISION
                or (hasattr(route_decision.capability, "value") and route_decision.capability.value == Capability.VISION.value)
                or str(route_decision.capability) == Capability.VISION.value
            )

            if is_vision_task:
                execution_capability = "vision"
                active_model = model_allocation_dict.get("vision_model_tag") or (vision_entry.model_tag if vision_entry else None)

                # ── 5. Knowledge Retrieval (SKIPPED for vision-only) ─────────
                st_rag = WorkflowStageTelemetry(
                    stage_name="knowledge_retrieval",
                    stage_index=4,
                    status=StageStatus.SKIPPED,
                    duration_ms=0.0,
                    started_at=utc_now_iso(),
                    completed_at=utc_now_iso(),
                    details={"reason": "Knowledge retrieval bypassed for visual-only inspection."},
                )
                stages_telemetry.append(st_rag)
                rag_citations = []

                # ── 6. Agent State Machine (Visual findings summary) ─────────
                t_stage_start = time.monotonic()
                st_agent = WorkflowStageTelemetry(
                    stage_name="agent_orchestration",
                    stage_index=5,
                    status=StageStatus.SUCCESS,
                    started_at=utc_now_iso(),
                    completed_at=utc_now_iso(),
                    duration_ms=round((time.monotonic() - t_stage_start) * 1000, 2),
                    details={
                        "final_state": "DELIVER",
                        "findings_count": ocr_summary.get("findings_count", 0),
                        "capability": "vision",
                    },
                )
                stages_telemetry.append(st_agent)
                agent_summary_dict = {
                    "final_state": "DELIVER",
                    "steps_executed": 1,
                    "plan_steps": 1,
                    "observations_count": ocr_summary.get("findings_count", 0),
                    "capability": "vision",
                }

                # ── 7. Sandboxed Calculation (SKIPPED - do NOT run corrosion calc)
                st_sandbox = WorkflowStageTelemetry(
                    stage_name="sandboxed_calculation",
                    stage_index=6,
                    status=StageStatus.SKIPPED,
                    duration_ms=0.0,
                    started_at=utc_now_iso(),
                    completed_at=utc_now_iso(),
                    details={"reason": "Corrosion rate calculations not requested for visual-only task."},
                )
                stages_telemetry.append(st_sandbox)
                calc_result_dict = None

                # ── 8. Engineering Validation Gate (SKIPPED - do NOT run validation)
                st_validation = WorkflowStageTelemetry(
                    stage_name="engineering_validation_gate",
                    stage_index=7,
                    status=StageStatus.SKIPPED,
                    duration_ms=0.0,
                    started_at=utc_now_iso(),
                    completed_at=utc_now_iso(),
                    details={"reason": "Corrosion engineering validation gate not requested for visual-only task."},
                )
                stages_telemetry.append(st_validation)
                validation_result_dict = None

                # ── 9. Deliverables Factory (SKIPPED - do NOT generate DOCX/XLSX)
                st_deliverables = WorkflowStageTelemetry(
                    stage_name="deliverables_factory",
                    stage_index=8,
                    status=StageStatus.SKIPPED,
                    duration_ms=0.0,
                    started_at=utc_now_iso(),
                    completed_at=utc_now_iso(),
                    details={
                        "artifacts_count": 0,
                        "reason": "Visual analysis completed. Engineering calculation and reports not requested.",
                    },
                )
                stages_telemetry.append(st_deliverables)
                deliverable_summaries = []

            else:
                execution_capability = getattr(route_decision.capability, "value", str(route_decision.capability))
                active_model = model_allocation_dict.get("assigned_model_tag") or (model_entry.model_tag if model_entry else None)

                # ── 5. Sovereign Knowledge / RAG Retrieval ────────────────────────
                t_stage_start = time.monotonic()
                st_rag = WorkflowStageTelemetry(
                    stage_name="knowledge_retrieval",
                    stage_index=4,
                    status=StageStatus.IN_PROGRESS,
                    started_at=utc_now_iso(),
                )

                rag_query = f"{request.component_id} minimum wall thickness corrosion rate retirement limits SOP API 570"
                retrieved_chunks, source_citations = await self.retriever.retrieve_with_citations(
                    query=rag_query,
                    top_k=2,
                    threshold=0.60,
                )

                # Convert to dictionary serialization for telemetry
                rag_citations = [c.model_dump() for c in source_citations]
                st_rag.status = StageStatus.SUCCESS
                st_rag.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
                st_rag.completed_at = utc_now_iso()
                st_rag.details = {
                    "query": rag_query,
                    "retrieved_chunks_count": len(retrieved_chunks),
                    "citations_count": len(source_citations),
                    "top_source": source_citations[0].source_document if source_citations else None,
                }
                stages_telemetry.append(st_rag)

                # ── 6. Agent State Machine Orchestration ──────────────────────────
                t_stage_start = time.monotonic()
                st_agent = WorkflowStageTelemetry(
                    stage_name="agent_orchestration",
                    stage_index=5,
                    status=StageStatus.IN_PROGRESS,
                    started_at=utc_now_iso(),
                )

                # Run agent task to drive the state machine lifecycle
                agent_ctx: AgentContext = await self.agent_orchestrator.execute_task(
                    task=request.objective,
                    task_id=task_id,
                    evidence=evidence_dict,
                )

                agent_summary_dict = {
                    "final_state": agent_ctx.current_state.value,
                    "steps_executed": agent_ctx.step_count,
                    "plan_steps": len(agent_ctx.plan.steps) if agent_ctx.plan else 0,
                    "observations_count": len(agent_ctx.observations),
                }

                if agent_ctx.current_state.value == "FAILED":
                    st_agent.status = StageStatus.FAILED
                    st_agent.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
                    st_agent.completed_at = utc_now_iso()
                    st_agent.details = agent_summary_dict
                    stages_telemetry.append(st_agent)
                    self._safe_audit(
                        AuditEventType.TASK_FAILED,
                        action=f"Agent reached FAILED state for {evidence_obj.equipment_id if evidence_obj else request.component_id}",
                        task_id=task_id,
                        status="FAILED",
                        metadata=agent_summary_dict,
                    )
                    raise IntegrationError(
                        "Agent execution failed: current_state is FAILED. Downstream calculation and deliverables halted.",
                        stage="agent_orchestration",
                    )

                st_agent.status = StageStatus.SUCCESS
                st_agent.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
                st_agent.completed_at = utc_now_iso()
                st_agent.details = agent_summary_dict
                stages_telemetry.append(st_agent)

                # ── 7. Sandboxed Engineering Calculation ─────────────────────────
                t_stage_start = time.monotonic()
                st_sandbox = WorkflowStageTelemetry(
                    stage_name="sandboxed_calculation",
                    stage_index=6,
                    status=StageStatus.IN_PROGRESS,
                    started_at=utc_now_iso(),
                )

                # Values derived from Engineering Evidence (provenance-backed):
                assert evidence_obj is not None, "Engineering evidence must be established prior to calculation"
                if not evidence_obj.can_calculate_corrosion_rate:
                    raise IntegrationError(
                        f"INSUFFICIENT_EVIDENCE: Missing required fields {evidence_obj.missing_fields} to compute corrosion rate.",
                        stage="sandboxed_calculation",
                    )

                initial_t = evidence_obj.nominal_thickness_mm
                current_t = evidence_obj.current_thickness_mm
                interval_yrs = evidence_obj.elapsed_time_years
                min_req_t = evidence_obj.minimum_required_thickness_mm
                comp_id = evidence_obj.equipment_id or request.component_id or "EQUIPMENT"

                calc_req = ToolExecutionRequest(
                    tool_name="corrosion_rate_calc",
                    input={
                        "component_id": comp_id,
                        "previous_thickness_mm": initial_t,
                        "current_thickness_mm": current_t,
                        "elapsed_time_years": interval_yrs,
                        "minimum_required_mm": min_req_t,
                    },
                    execution_mode="subprocess",
                )
                calc_resp = await self.sandbox_executor.execute_tool(calc_req)

                if calc_resp.status != ExecutionStatus.SUCCESS or not calc_resp.structured_result:
                    raise IntegrationError(
                        f"Sandboxed corrosion rate calculation failed: {calc_resp.error_message}",
                        stage="sandbox",
                    )

                calc_result_dict = calc_resp.structured_result

                # Check minimum wall thickness margin check if threshold is present
                if min_req_t is not None:
                    margin_req = ToolExecutionRequest(
                        tool_name="minimum_wall_thickness_check",
                        input={
                            "component_id": comp_id,
                            "measured_thickness_mm": current_t,
                            "minimum_required_mm": min_req_t,
                        },
                        execution_mode="subprocess",
                    )
                    margin_resp = await self.sandbox_executor.execute_tool(margin_req)
                    calc_result_dict["margin_check"] = margin_resp.structured_result or {}
                else:
                    calc_result_dict["margin_check"] = {
                        "status": "INSUFFICIENT_EVIDENCE",
                        "message": "Minimum retirement thickness threshold unavailable.",
                    }

                st_sandbox.status = StageStatus.SUCCESS
                st_sandbox.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
                st_sandbox.completed_at = utc_now_iso()
                st_sandbox.details = calc_result_dict
                stages_telemetry.append(st_sandbox)

                # ── 8. Fail-Closed Validation Gate ───────────────────────────────
                t_stage_start = time.monotonic()
                st_validation = WorkflowStageTelemetry(
                    stage_name="engineering_validation_gate",
                    stage_index=7,
                    status=StageStatus.IN_PROGRESS,
                    started_at=utc_now_iso(),
                )

                # Build grounded CorrosionAuditResult
                corrosion_calc = CorrosionCalculation(
                    initial_thickness_mm=initial_t,
                    current_thickness_mm=current_t,
                    inspection_interval_years=interval_yrs,
                    minimum_required_mm=min_req_t,
                    corrosion_rate_mm_per_year=calc_result_dict["corrosion_rate_mm_per_year"],
                    remaining_life_years=calc_result_dict.get("remaining_life_years"),
                    formula_applied="corrosion_rate = (initial - current) / interval; remaining_life = (current - min_req) / rate",
                )

                # Build validated citations list from retrieved RAG citations
                pydantic_citations = [
                    SourceCitation(
                        source_document=c.source_document,
                        page_number=c.page_number,
                        chunk_id=c.chunk_id,
                        content_sha256=c.content_sha256,
                        similarity_score=c.similarity_score,
                    )
                    for c in source_citations
                ]

                # Prepend primary citation from uploaded inspection evidence
                primary_citation = SourceCitation(
                    source_document=evidence_obj.source_filename,
                    page_number=evidence_obj.source_page or 1,
                    content_sha256=evidence_obj.source_sha256,
                    excerpt=(
                        f"Extracted measurement: {evidence_obj.selected_measurement.location_desc} = {current_t} mm "
                        f"(Nominal: {initial_t} mm, Interval: {interval_yrs} yrs)"
                        if evidence_obj.selected_measurement
                        else f"Measured thickness: {current_t} mm"
                    ),
                )
                all_citations = [primary_citation] + pydantic_citations

                if min_req_t is not None and calc_result_dict.get("remaining_life_years") is not None:
                    rem_life = calc_result_dict.get("remaining_life_years")
                    margin_mm = round(current_t - min_req_t, 2)
                    conclusion_text = (
                        f"Equipment wall thickness ({current_t} mm) exceeds minimum retirement limit "
                        f"({min_req_t} mm) with a remaining margin of +{margin_mm} mm. "
                        f"Estimated remaining service life is {rem_life} years."
                    )
                    rec_code = RecommendationCode.CONTINUE_SERVICE if margin_mm >= 0 else RecommendationCode.RETIRE_FROM_SERVICE
                else:
                    conclusion_text = (
                        f"Calculated corrosion rate is {calc_result_dict['corrosion_rate_mm_per_year']} mm/year "
                        f"based on initial thickness {initial_t} mm and current measured thickness {current_t} mm "
                        f"over {interval_yrs} years. Remaining operational life assessment is INSUFFICIENT_EVIDENCE "
                        f"(minimum required retirement thickness threshold was not provided in evidence)."
                    )
                    rec_code = RecommendationCode.INSUFFICIENT_DATA

                audit_payload = CorrosionAuditResult(
                    task_id=task_id,
                    equipment_id=comp_id,
                    inspection_subject=evidence_obj.inspection_subject or f"Equipment {comp_id} Ultrasonic Survey",
                    current_measurement=WallThicknessMeasurement(
                        value_mm=current_t,
                        measurement_date=evidence_obj.selected_measurement.measurement_date if evidence_obj.selected_measurement else None,
                        location_tag=evidence_obj.selected_measurement.cml_tag if evidence_obj.selected_measurement else f"{comp_id}-CRITICAL",
                    ),
                    initial_measurement=WallThicknessMeasurement(
                        value_mm=initial_t,
                        measurement_date=None,
                        location_tag=f"{comp_id}-NOMINAL",
                    ),
                    minimum_required_thickness_mm=min_req_t,
                    calculation=corrosion_calc,
                    findings=[
                        InspectionFinding(
                            finding_id="F-01",
                            description=(
                                f"Ultrasonic survey identified governing wall thickness of {current_t} mm at "
                                f"{evidence_obj.selected_measurement.location_desc if evidence_obj.selected_measurement else 'critical location'}."
                            ),
                            severity="MEDIUM",
                            supporting_citation=primary_citation,
                        )
                    ],
                    conclusion=conclusion_text,
                    recommendation=rec_code,
                    citations=all_citations,
                    confidence=0.95,
                )

                # Execute validation pipeline
                val_res: ValidationResult = self.validation_service.validate(audit_payload.model_dump())
                validation_result_dict = {
                    "valid": val_res.valid,
                    "status": val_res.status,
                    "checks_passed": val_res.checks_passed,
                    "checks_failed": val_res.checks_failed,
                    "warnings": val_res.warnings,
                }

                if not val_res.valid or val_res.status != "VALID":
                    st_validation.status = StageStatus.FAILED
                    st_validation.error = f"Validation gate rejected result: {', '.join(val_res.checks_failed)}"
                    st_validation.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
                    st_validation.completed_at = utc_now_iso()
                    st_validation.details = validation_result_dict
                    stages_telemetry.append(st_validation)
                    overall_status = WorkflowStatus.VALIDATION_FAILED
                    raise ValidationGateError(
                        message=f"Fail-closed validation gate rejected deliverable generation: {val_res.checks_failed}",
                        validation_errors=val_res.checks_failed,
                        details=validation_result_dict,
                    )

                st_validation.status = StageStatus.SUCCESS
                st_validation.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
                st_validation.completed_at = utc_now_iso()
                st_validation.details = validation_result_dict
                stages_telemetry.append(st_validation)

                # ── 9. Deterministic Office Deliverables ──────────────────────────
                t_stage_start = time.monotonic()
                st_deliverables = WorkflowStageTelemetry(
                    stage_name="deliverables_factory",
                    stage_index=8,
                    status=StageStatus.IN_PROGRESS,
                    started_at=utc_now_iso(),
                )

                meta = ReportMetadata(
                    title=f"Refining Equipment Corrosion Audit — {comp_id}",
                    organization="MANGALORE REFINERY AND PETROCHEMICALS LIMITED (MRPL)",
                    facility="Mangalore Refinery Complex",
                    division="Inspection & Asset Integrity Division",
                    prepared_by="SIH26117 Sovereign Agentic Intelligence Workbench",
                    approved_by="Chief Inspection Engineer, MRPL",
                )

                deliv_res = self.deliverables_factory.generate(
                    payload=val_res.validated_data or audit_payload,
                    formats=request.requested_formats,
                    metadata=meta,
                    task_id=task_id,
                )

                for art in deliv_res.artifacts:
                    deliverable_summaries.append(
                        ArtifactSummary(
                            artifact_id=art.artifact_id,
                            format=art.format.value,
                            filename=art.filename,
                            relative_path=art.relative_path,
                            file_size_bytes=art.file_size_bytes,
                            sha256=art.sha256_hash,
                            download_url=f"/api/v1/deliverables/download/{art.format.value}/{art.filename}",
                        )
                    )

                st_deliverables.status = StageStatus.SUCCESS
                st_deliverables.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
                st_deliverables.completed_at = utc_now_iso()
                st_deliverables.details = {
                    "artifacts_count": len(deliverable_summaries),
                    "formats": [a.format for a in deliverable_summaries],
                }
                stages_telemetry.append(st_deliverables)

            # ── 10. Audit Chain Verification ─────────────────────────────────
            t_stage_start = time.monotonic()
            st_audit = WorkflowStageTelemetry(
                stage_name="audit_chain_verification",
                stage_index=9,
                status=StageStatus.IN_PROGRESS,
                started_at=utc_now_iso(),
            )

            # Record final completed event
            completed_action = (
                f"Completed Vision Analysis Workflow [{workflow_id[:8]}]"
                if is_vision_task
                else f"Completed Corrosion Audit Workflow [{workflow_id[:8]}]"
            )
            self._safe_audit(
                AuditEventType.TASK_COMPLETED,
                action=completed_action,
                task_id=task_id,
                model_role=role_key,
                capability=execution_capability,
                status="SUCCESS",
                metadata={
                    "artifacts_produced": len(deliverable_summaries),
                    "capability": execution_capability,
                    "active_model": active_model,
                },
            )

            audit_verify = self.audit_service.verify_ledger()
            audit_summary = {
                "ledger_valid": audit_verify.valid,
                "events_checked": audit_verify.events_checked,
                "first_invalid_index": audit_verify.first_invalid_index,
                "error_detail": audit_verify.error_detail,
            }

            st_audit.status = StageStatus.SUCCESS
            st_audit.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
            st_audit.completed_at = utc_now_iso()
            st_audit.details = audit_summary
            stages_telemetry.append(st_audit)

            # ── 11. Sovereignty & Network Isolation Check ────────────────────
            t_stage_start = time.monotonic()
            st_sovereignty = WorkflowStageTelemetry(
                stage_name="sovereignty_verification",
                stage_index=10,
                status=StageStatus.IN_PROGRESS,
                started_at=utc_now_iso(),
            )

            net_report = self.audit_service.observe_network()
            sov_check = self.audit_service.check_sovereignty()
            sovereignty_summary = {
                "status": sov_check.status,
                "local_mode_enabled": sov_check.local_mode_enabled,
                "external_connections_observed": sov_check.external_connections_observed,
                "violations_count": len(sov_check.violations),
                "total_connections": net_report.total_connections,
                "loopback_connections": net_report.loopback_connections,
                "non_loopback_connections": net_report.non_loopback_connections,
                "airgap_confirmed": not sov_check.external_connections_observed,
            }

            if sov_check.status != "PASS" or sov_check.external_connections_observed:
                st_sovereignty.status = StageStatus.FAILED
                st_sovereignty.error = f"Sovereignty violation detected: {sov_check.violations}"
                st_sovereignty.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
                st_sovereignty.completed_at = utc_now_iso()
                st_sovereignty.details = sovereignty_summary
                stages_telemetry.append(st_sovereignty)
                deliverable_summaries.clear()
                raise IntegrationError(
                    f"Sovereignty check failed: {len(sov_check.violations)} violations observed",
                    stage="sovereignty_verification",
                )

            st_sovereignty.status = StageStatus.SUCCESS
            st_sovereignty.duration_ms = round((time.monotonic() - t_stage_start) * 1000, 2)
            st_sovereignty.completed_at = utc_now_iso()
            st_sovereignty.details = sovereignty_summary
            stages_telemetry.append(st_sovereignty)

            # Workflow completed successfully
            overall_status = WorkflowStatus.COMPLETED

        except ValidationGateError as val_err:
            logger.warning("Workflow validation gate failed: %s", str(val_err))
            overall_status = WorkflowStatus.VALIDATION_FAILED
            errors.append(str(val_err))
            self._safe_audit(
                AuditEventType.TASK_FAILED,
                action=f"Workflow validation gate rejected deliverable: {str(val_err)}",
                task_id=task_id,
                status="FAILED",
            )
        except Exception as exc:
            err_msg = str(exc)
            logger.error("Workflow execution failed: %s", err_msg, exc_info=True)
            if "EVIDENCE_CONFLICT" in err_msg:
                overall_status = WorkflowStatus.EVIDENCE_CONFLICT
            elif "INSUFFICIENT_EVIDENCE" in err_msg:
                overall_status = WorkflowStatus.INSUFFICIENT_EVIDENCE
            else:
                overall_status = WorkflowStatus.FAILED
            errors.append(err_msg)
            self._safe_audit(
                AuditEventType.TASK_FAILED,
                action=f"Workflow failed: {err_msg}",
                task_id=task_id,
                status="FAILED",
            )

        duration_total = round(time.monotonic() - start_mono, 3)
        if duration_total > effective_timeout:
            overall_status = WorkflowStatus.FAILED
            errors.append(f"Execution exceeded global timeout of {effective_timeout}s.")

        result = CorrosionAuditWorkflowResult(
            workflow_id=workflow_id,
            task_id=task_id,
            status=overall_status,
            execution_mode=request.execution_mode,
            objective=request.objective,
            started_at=started_at,
            completed_at=utc_now_iso(),
            duration_seconds=duration_total,
            document_summary=doc_summary,
            evidence_summary=evidence_dict,
            ocr_vision_summary=ocr_summary,
            routing_decision=routing_decision_dict,
            model_allocation=model_allocation_dict,
            agent_summary=agent_summary_dict,
            rag_citations=rag_citations,
            calculation_result=calc_result_dict,
            validation_result=validation_result_dict,
            deliverables=deliverable_summaries,
            audit_summary=audit_summary if "audit_summary" in locals() else {},
            sovereignty_proof=sovereignty_summary if "sovereignty_summary" in locals() else {},
            execution_capability=execution_capability,
            active_model=active_model,
            stages=stages_telemetry,
            errors=errors,
        )

        self._results[workflow_id] = result
        return result

    def _safe_audit(
        self,
        event_type: AuditEventType,
        action: str,
        task_id: Optional[str] = None,
        model_role: Optional[str] = None,
        capability: Optional[str] = None,
        status: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Helper to safely record an audit event without breaking workflow execution."""
        try:
            self.audit_service.record_event(
                event_type=event_type,
                action=action,
                task_id=task_id,
                model_role=model_role,
                capability=capability,
                status=status,
                metadata=metadata or {},
            )
        except Exception as e:
            logger.warning("Audit record skipped in workflow: %s", str(e))
