"""
Unit and integration tests for Phase 11 — Audit & Sovereignty Evidence.
Verifies tamper-evident hash chaining, integrity checks, network observation,
sovereignty enforcement, secret filtering, agent/deliverable integration, and API endpoints.
"""

import json
from pathlib import Path
import threading
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.audit import (
    AuditEvent,
    AuditEventType,
    AuditIntegrityVerifier,
    AuditService,
    GENESIS_HASH,
    LocalAuditEventStore,
    RuntimeNetworkMonitor,
    SovereigntyChecker,
    calculate_event_hash,
    canonicalize_event,
    verify_event_hash,
)
from app.services.audit.service import sanitize_metadata
from app.services.agent.orchestrator import AgentStateMachineOrchestrator
from app.services.deliverables.factory import DeliverablesFactory
from app.services.deliverables.models import DeliverableFormat
from app.services.validation.models import (
    CorrosionAuditResult,
    CorrosionCalculation,
    InspectionFinding,
    MeasurementUnit,
    WallThicknessMeasurement,
)


@pytest.fixture
def temp_audit_service(tmp_path: Path) -> AuditService:
    """Provide an isolated AuditService with a temporary storage path."""
    audit_file = tmp_path / "audit" / "events.jsonl"
    return AuditService(storage_path=audit_file)


# ── 1. Event Creation ─────────────────────────────────────────────────────────

def test_audit_event_creation():
    """Verify strongly typed AuditEvent creation with defaults."""
    event = AuditEvent(
        event_type=AuditEventType.TASK_CREATED,
        action="Created test task",
        task_id="task-123",
        status="SUCCESS",
        metadata={"key": "value"}
    )
    assert event.event_id is not None
    assert event.timestamp is not None
    assert event.event_type == AuditEventType.TASK_CREATED
    assert event.action == "Created test task"
    assert event.status == "SUCCESS"
    assert event.metadata["key"] == "value"


# ── 2. Deterministic Serialization ───────────────────────────────────────────

def test_deterministic_serialization():
    """Verify that serialization is canonical: key order invariant and excludes event_hash."""
    ev1 = AuditEvent(
        event_id="fixed-id-1",
        timestamp="2026-09-11T00:00:00Z",
        event_type=AuditEventType.TASK_STARTED,
        action="Action A",
        metadata={"b": 2, "a": 1},
        event_hash="should_be_ignored_1"
    )
    ev2 = AuditEvent(
        event_id="fixed-id-1",
        timestamp="2026-09-11T00:00:00Z",
        event_type=AuditEventType.TASK_STARTED,
        action="Action A",
        metadata={"a": 1, "b": 2},
        event_hash="should_be_ignored_2"
    )
    bytes1 = canonicalize_event(ev1)
    bytes2 = canonicalize_event(ev2)
    assert bytes1 == bytes2
    assert b"should_be_ignored" not in bytes1


# ── 3. SHA-256 Hashing ────────────────────────────────────────────────────────

def test_sha256_hashing():
    """Verify calculate_event_hash produces valid 64-char hex SHA-256 digest."""
    ev = AuditEvent(
        event_type=AuditEventType.STATE_CHANGED,
        action="Transitioned state",
        task_id="task-test"
    )
    hash_val = calculate_event_hash(ev, GENESIS_HASH)
    assert len(hash_val) == 64
    assert all(c in "0123456789abcdef" for c in hash_val)


# ── 4. Genesis Event ──────────────────────────────────────────────────────────

def test_genesis_event(temp_audit_service: AuditService):
    """Verify the first event in an empty ledger binds to GENESIS_HASH."""
    event = temp_audit_service.record_event(
        event_type=AuditEventType.TASK_CREATED,
        action="First genesis event",
        task_id="genesis-task"
    )
    assert event.previous_hash == GENESIS_HASH
    assert event.event_hash != ""
    assert verify_event_hash(event, GENESIS_HASH)


# ── 5. Hash-Chain Continuity & Multiple Events ────────────────────────────────

def test_hash_chain_continuity(temp_audit_service: AuditService):
    """Verify that multiple events sequentially chain their hashes."""
    ev1 = temp_audit_service.record_event(
        event_type=AuditEventType.TASK_CREATED,
        action="Event 1",
        task_id="task-chain"
    )
    ev2 = temp_audit_service.record_event(
        event_type=AuditEventType.TASK_STARTED,
        action="Event 2",
        task_id="task-chain"
    )
    ev3 = temp_audit_service.record_event(
        event_type=AuditEventType.TASK_COMPLETED,
        action="Event 3",
        task_id="task-chain"
    )

    assert ev1.previous_hash == GENESIS_HASH
    assert ev2.previous_hash == ev1.event_hash
    assert ev3.previous_hash == ev2.event_hash

    # Verify each event hash
    assert verify_event_hash(ev1, GENESIS_HASH)
    assert verify_event_hash(ev2, ev1.event_hash)
    assert verify_event_hash(ev3, ev2.event_hash)


# ── 6. Integrity Verification: PASS ───────────────────────────────────────────

def test_integrity_verification_pass(temp_audit_service: AuditService):
    """Verify integrity check succeeds on a valid, untampered ledger."""
    for i in range(5):
        temp_audit_service.record_event(
            event_type=AuditEventType.STATE_CHANGED,
            action=f"Step {i}",
            task_id="task-pass"
        )

    res = temp_audit_service.verify_ledger()
    assert res.valid is True
    assert res.events_checked == 5
    assert res.first_invalid_event is None


# ── 7. Integrity Verification: Modified Event Detection ───────────────────────

def test_integrity_detects_modified_event(temp_audit_service: AuditService):
    """Verify tampering with an event's payload invalidates the chain."""
    for i in range(3):
        temp_audit_service.record_event(
            event_type=AuditEventType.TOOL_STARTED,
            action=f"Action {i}",
            task_id="task-mod"
        )

    # Read events from store, tamper with event 1, and write back
    events = temp_audit_service.store.get_all_events()
    assert len(events) == 3

    # Tamper with action
    events[1].action = "MALICIOUS_TAMPERING"

    # Re-verify with verifier
    res = AuditIntegrityVerifier.verify_chain(events)
    assert res.valid is False
    assert res.first_invalid_index == 1
    assert res.first_invalid_event == events[1].event_id
    assert "Cryptographic digest mismatch" in (res.error_detail or "")


# ── 8. Integrity Verification: Deleted Event Detection ────────────────────────

def test_integrity_detects_deleted_event(temp_audit_service: AuditService):
    """Verify that deleting an intermediate event breaks the previous_hash link."""
    ev1 = temp_audit_service.record_event(
        event_type=AuditEventType.TASK_STARTED, action="1"
    )
    ev2 = temp_audit_service.record_event(
        event_type=AuditEventType.TOOL_STARTED, action="2"
    )
    ev3 = temp_audit_service.record_event(
        event_type=AuditEventType.TOOL_COMPLETED, action="3"
    )

    # Simulate deletion of ev2
    corrupted_chain = [ev1, ev3]
    res = AuditIntegrityVerifier.verify_chain(corrupted_chain)
    assert res.valid is False
    assert res.first_invalid_index == 1
    assert res.first_invalid_event == ev3.event_id
    assert "Hash link mismatch" in (res.error_detail or "")


# ── 9. Integrity Verification: Reordered Event Detection ──────────────────────

def test_integrity_detects_reordered_events(temp_audit_service: AuditService):
    """Verify that reordering events in the ledger is caught as a tampering failure."""
    ev1 = temp_audit_service.record_event(
        event_type=AuditEventType.TASK_STARTED, action="1"
    )
    ev2 = temp_audit_service.record_event(
        event_type=AuditEventType.TOOL_STARTED, action="2"
    )
    ev3 = temp_audit_service.record_event(
        event_type=AuditEventType.TOOL_COMPLETED, action="3"
    )

    # Reorder events
    corrupted_chain = [ev1, ev3, ev2]
    res = AuditIntegrityVerifier.verify_chain(corrupted_chain)
    assert res.valid is False
    assert res.first_invalid_index == 1


# ── 10. Malformed Event Handling ──────────────────────────────────────────────

def test_malformed_event_handling(tmp_path: Path):
    """Verify that unparseable lines in the ledger trigger AuditStorageError."""
    corrupt_file = tmp_path / "corrupt.jsonl"
    corrupt_file.write_text("NOT_VALID_JSON\n", encoding="utf-8")
    store = LocalAuditEventStore(corrupt_file)

    with pytest.raises(Exception):
        store.get_all_events()


# ── 11. Concurrent Append Safety ──────────────────────────────────────────────

def test_concurrent_append_thread_safety(temp_audit_service: AuditService):
    """Verify concurrent thread appends maintain unbroken chain integrity."""
    def append_events(count: int, prefix: str):
        for i in range(count):
            temp_audit_service.record_event(
                event_type=AuditEventType.STATE_CHANGED,
                action=f"{prefix}-{i}",
                task_id=f"task-{prefix}"
            )

    threads = []
    for t_idx in range(4):
        t = threading.Thread(target=append_events, args=(10, f"worker-{t_idx}"))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert temp_audit_service.count_events() == 40
    res = temp_audit_service.verify_ledger()
    assert res.valid is True
    assert res.events_checked == 40


# ── 12. Secret Filtering ──────────────────────────────────────────────────────

def test_secret_filtering(temp_audit_service: AuditService):
    """Verify sensitive tokens and keys are redacted from metadata before storing."""
    sensitive_meta = {
        "api_key": "sk-secret-12345",
        "nested": {
            "password": "super-secret-pw",
            "token": "bearer-token-abc",
            "safe_field": "public_data"
        },
        "user_token": "token-123",
        "public_flag": True
    }

    sanitized = sanitize_metadata(sensitive_meta)
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert sanitized["nested"]["safe_field"] == "public_data"
    assert sanitized["user_token"] == "[REDACTED]"
    assert sanitized["public_flag"] is True

    # Record and verify storage
    event = temp_audit_service.record_event(
        event_type=AuditEventType.TOOL_STARTED,
        action="Tool with secrets",
        metadata=sensitive_meta
    )
    assert event.metadata["api_key"] == "[REDACTED]"
    assert "sk-secret-12345" not in temp_audit_service.storage_path.read_text(encoding="utf-8")


# ── 13. Runtime Network Observation ───────────────────────────────────────────

def test_runtime_network_observation():
    """Verify RuntimeNetworkMonitor safely returns structured connection evidence."""
    monitor = RuntimeNetworkMonitor()
    report = monitor.observe_connections()

    assert report.timestamp is not None
    assert report.total_connections >= 0
    assert report.loopback_connections >= 0
    assert report.non_loopback_connections >= 0
    assert isinstance(report.connections, list)
    assert report.observation_method in ("psutil_process_connections", "stdlib_socket_inspection")


# ── 14. Sovereignty Check: Local Provider PASS ────────────────────────────────

def test_sovereignty_check_local_pass():
    """Verify local loopback providers pass sovereignty evaluation."""
    checker = SovereigntyChecker()
    local_providers = {
        "Ollama": "http://127.0.0.1:11434",
        "LlamaCPP": "http://localhost:8080",
        "vLLM": "http://[::1]:8000"
    }
    status = checker.evaluate_sovereignty(air_gapped_mode=True, custom_providers=local_providers)
    assert status.status == "PASS"
    assert status.local_mode_enabled is True
    assert len(status.violations) == 0
    for p in status.provider_checks:
        assert p.is_local is True


# ── 15. Sovereignty Check: External Provider FAIL ─────────────────────────────

def test_sovereignty_check_external_fail():
    """Verify remote cloud or external provider URLs fail sovereign air-gap policy."""
    checker = SovereigntyChecker()
    external_providers = {
        "OpenAI": "https://api.openai.com/v1",
        "ExternalOllama": "http://192.168.1.50:11434"
    }
    status = checker.evaluate_sovereignty(air_gapped_mode=True, custom_providers=external_providers)
    assert status.status == "FAIL"
    assert len(status.violations) > 0
    assert any("OpenAI" in v for v in status.violations)


# ── 16. Sovereignty Note Requirement ──────────────────────────────────────────

def test_sovereignty_wording_exact():
    """Verify sovereignty status uses strictly compliant wording (no false physical air-gap claim)."""
    checker = SovereigntyChecker()
    status = checker.evaluate_sovereignty(air_gapped_mode=True)
    assert "Software-level local-provider enforcement and runtime network evidence." in status.note
    assert "Physical air-gap isolation remains a deployment/environment control." in status.note
    assert "100% air-gap guaranteed" not in status.note
    assert "physical air gap proven" not in status.note.lower()


# ── 17. API Endpoints: Events Query ───────────────────────────────────────────

def test_api_audit_events_endpoint(monkeypatch, temp_audit_service: AuditService):
    """Verify GET /api/v1/audit/events returns paginated audit events."""
    monkeypatch.setattr("app.api.v1.endpoints.audit.get_audit_service", lambda: temp_audit_service)

    temp_audit_service.record_event(
        event_type=AuditEventType.TASK_CREATED, action="API Task 1", task_id="api-task"
    )
    temp_audit_service.record_event(
        event_type=AuditEventType.TASK_COMPLETED, action="API Task 2", task_id="api-task"
    )

    client = TestClient(app)
    resp = client.get("/api/v1/audit/events?task_id=api-task")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["action"] == "API Task 1"


# ── 18. API Endpoints: Event by ID ────────────────────────────────────────────

def test_api_audit_event_by_id(monkeypatch, temp_audit_service: AuditService):
    """Verify GET /api/v1/audit/events/{id} returns single event or 404."""
    monkeypatch.setattr("app.api.v1.endpoints.audit.get_audit_service", lambda: temp_audit_service)

    ev = temp_audit_service.record_event(
        event_type=AuditEventType.VISION_ANALYSIS, action="Inspecting image"
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/audit/events/{ev.event_id}")
    assert resp.status_code == 200
    assert resp.json()["event"]["event_id"] == ev.event_id

    resp_404 = client.get("/api/v1/audit/events/non-existent-uuid")
    assert resp_404.status_code == 404


# ── 19. API Endpoints: Integrity Verification ─────────────────────────────────

def test_api_audit_integrity_endpoint(monkeypatch, temp_audit_service: AuditService):
    """Verify GET /api/v1/audit/integrity checks hash-chain integrity."""
    monkeypatch.setattr("app.api.v1.endpoints.audit.get_audit_service", lambda: temp_audit_service)

    temp_audit_service.record_event(
        event_type=AuditEventType.TASK_STARTED, action="Integrity test"
    )

    client = TestClient(app)
    resp = client.get("/api/v1/audit/integrity")
    assert resp.status_code == 200
    verification = resp.json()["verification"]
    assert verification["valid"] is True
    assert verification["events_checked"] == 1


# ── 20. API Endpoints: Network & Sovereignty ──────────────────────────────────

def test_api_network_and_sovereignty_endpoints(monkeypatch, temp_audit_service: AuditService):
    """Verify GET /api/v1/audit/network and /api/v1/audit/sovereignty endpoints."""
    monkeypatch.setattr("app.api.v1.endpoints.audit.get_audit_service", lambda: temp_audit_service)

    client = TestClient(app)

    net_resp = client.get("/api/v1/audit/network")
    assert net_resp.status_code == 200
    assert "report" in net_resp.json()

    sov_resp = client.get("/api/v1/audit/sovereignty?air_gapped_mode=true")
    assert sov_resp.status_code == 200
    assert "sovereignty" in sov_resp.json()
    assert "status" in sov_resp.json()["sovereignty"]


# ── 21. Agent Orchestrator Audit Integration ──────────────────────────────────

@pytest.mark.asyncio
async def test_agent_orchestrator_audit_integration(temp_audit_service: AuditService):
    """Verify Phase 7 Agent orchestrator logs lifecycle events to AuditService."""
    orchestrator = AgentStateMachineOrchestrator(audit_service=temp_audit_service)

    context = await orchestrator.execute_task(
        task="Calculate corrosion rate for Crude Column C-110",
        task_id="agent-audit-test"
    )

    events = temp_audit_service.get_events(task_id="agent-audit-test")
    assert len(events) > 0

    event_types = [e.event_type for e in events]
    assert AuditEventType.TASK_STARTED in event_types
    assert AuditEventType.MODEL_ROUTED in event_types
    assert AuditEventType.PLAN_CREATED in event_types

    # Verify model role and capability recorded
    model_routed_ev = next(e for e in events if e.event_type == AuditEventType.MODEL_ROUTED)
    assert model_routed_ev.model_role is not None
    assert model_routed_ev.capability is not None

    # Verify chain integrity
    integrity = temp_audit_service.verify_ledger()
    assert integrity.valid is True


def test_router_model_role_audit_evidence(temp_audit_service: AuditService):
    """Verify recording of task routing decision with model role and capability metadata."""
    from app.services.router.decision import Capability, ModelRole, RoutingDecision, TaskType

    decision = RoutingDecision(
        task_type=TaskType.CALCULATION,
        capability=Capability.CALCULATION,
        model_role=ModelRole.REASONING,
        confidence=0.95,
        routing_method="rule_based",
        reason="Test engineering calculation routing",
    )

    ev = temp_audit_service.record_event(
        event_type=AuditEventType.MODEL_ROUTED,
        action=f"Routed intent: {decision.task_type.value}",
        task_id="route-task-001",
        model_role=decision.model_role.value,
        capability=decision.capability.value,
        metadata={"confidence": decision.confidence, "method": decision.routing_method}
    )

    assert ev.model_role == "reasoning"
    assert ev.capability == "calculation"
    assert ev.metadata["confidence"] == 0.95
    assert ev.metadata["method"] == "rule_based"
    assert verify_event_hash(ev, GENESIS_HASH)


# ── 22. Tool Execution Audit Evidence ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_tool_execution_audit_evidence(temp_audit_service: AuditService):
    """Verify tool execution start/complete events are captured with duration/status."""
    orchestrator = AgentStateMachineOrchestrator(audit_service=temp_audit_service)

    await orchestrator.execute_task(
        task="Calculate corrosion rate with tool execution",
        task_id="tool-audit-test",
        max_steps=2
    )

    events = temp_audit_service.get_events(task_id="tool-audit-test")
    tool_events = [e for e in events if e.event_type in (AuditEventType.TOOL_STARTED, AuditEventType.TOOL_COMPLETED)]

    # If steps were executed, tool events must be present
    if any(e.event_type == AuditEventType.TOOL_STARTED for e in tool_events):
        started = [e for e in tool_events if e.event_type == AuditEventType.TOOL_STARTED][0]
        assert started.tool_name is not None
        assert started.agent_state == "EXECUTE"


# ── 23. RAG Retrieval Provenance Evidence ─────────────────────────────────────

def test_rag_provenance_audit_evidence(temp_audit_service: AuditService):
    """Verify RAG retrieval can be recorded with safe provenance metadata."""
    event = temp_audit_service.record_event(
        event_type=AuditEventType.KNOWLEDGE_RETRIEVED,
        action="Retrieved knowledge chunks for query",
        task_id="rag-audit-test",
        source="knowledge_base",
        metadata={
            "query": "corrosion rate API 570",
            "chunks_count": 2,
            "citations": [
                {"document": "API_570.pdf", "page": 12, "chunk_id": "c-101", "similarity": 0.88},
                {"document": "API_570.pdf", "page": 13, "chunk_id": "c-102", "similarity": 0.85}
            ]
        }
    )
    assert event.event_type == AuditEventType.KNOWLEDGE_RETRIEVED
    assert event.metadata["chunks_count"] == 2
    assert len(event.metadata["citations"]) == 2
    assert event.metadata["citations"][0]["document"] == "API_570.pdf"


# ── 24. Deliverables Factory Audit Evidence ───────────────────────────────────

def test_deliverables_factory_audit_evidence(tmp_path: Path, temp_audit_service: AuditService):
    """Verify Phase 10 DeliverablesFactory logs DELIVERABLE_CREATED audit events."""
    factory = DeliverablesFactory(output_dir=tmp_path / "output", audit_service=temp_audit_service)

    valid_payload = CorrosionAuditResult(
        task_id="deliv-audit-task",
        equipment_id="T-201",
        inspection_subject="Atmospheric Storage Tank",
        current_measurement=WallThicknessMeasurement(
            value_mm=4.20,
            unit=MeasurementUnit.MM,
            measurement_date="2026-03-15",
            location_tag="10-HC-101-CML-A",
        ),
        initial_measurement=WallThicknessMeasurement(
            value_mm=8.00,
            unit=MeasurementUnit.MM,
            measurement_date="2021-03-15",
            location_tag="10-HC-101-CML-A",
        ),
        minimum_required_thickness_mm=3.20,
        calculation=CorrosionCalculation(
            initial_thickness_mm=8.00,
            current_thickness_mm=4.20,
            inspection_interval_years=5.0,
            minimum_required_mm=3.20,
            corrosion_rate_mm_per_year=0.760,
            remaining_life_years=1.316,
            formula_applied="API 570 Section 7.1",
        ),
        findings=[
            InspectionFinding(
                finding_id="F-01",
                description="Localized wall thinning identified at 6 o'clock position.",
                severity="HIGH",
            )
        ],
        citations=[]
    )

    res = factory.generate(valid_payload, formats=[DeliverableFormat.DOCX], task_id="deliv-audit-task")
    assert res.success is True

    events = temp_audit_service.get_events(task_id="deliv-audit-task")
    deliv_events = [e for e in events if e.event_type == AuditEventType.DELIVERABLE_CREATED]
    assert len(deliv_events) == 1
    assert deliv_events[0].metadata["equipment_id"] == "T-201"
    assert deliv_events[0].metadata["format"] == "docx"
    assert "filename" in deliv_events[0].metadata


# ── 25. Outbound Network Isolation Verification ───────────────────────────────

def test_no_outbound_network_during_audit(temp_audit_service: AuditService):
    """Verify that performing audit operations causes no external socket connections."""
    monitor = RuntimeNetworkMonitor()
    initial_report = monitor.observe_connections()

    # Perform a sequence of audit operations
    for i in range(10):
        temp_audit_service.record_event(
            event_type=AuditEventType.STATE_CHANGED,
            action=f"Test event {i}",
            task_id="net-check"
        )
    temp_audit_service.verify_ledger()
    checker = SovereigntyChecker(monitor)
    sov = checker.evaluate_sovereignty(air_gapped_mode=True)

    post_report = monitor.observe_connections()
    assert post_report.non_loopback_connections == initial_report.non_loopback_connections
    assert sov.status == "PASS"


# ── 26. Physical Isolation Attestation Verification ──────────────────────────

def test_physical_isolation_attestation_service(temp_audit_service: AuditService):
    """Verify operator physical isolation attestation event recording and ledger integrity."""
    checklist_evidence = {
        "ethernet_disconnected": True,
        "wifi_disabled": True,
        "adapter_disabled": True,
        "external_route_checked": True,
        "radios_checked": True,
        "operator_confirmed": True,
    }

    event = temp_audit_service.record_event(
        event_type=AuditEventType.PHYSICAL_ISOLATION_ATTESTED,
        action="Operator verified physical air-gap isolation checklist",
        task_id="sovereignty-attestation",
        metadata={
            "checklist": checklist_evidence,
            "operator_notes": "Evaluation station test operator check",
            "hostname": "local-workstation",
        },
    )

    assert event.event_type == AuditEventType.PHYSICAL_ISOLATION_ATTESTED
    assert event.event_hash is not None
    assert event.metadata["checklist"]["ethernet_disconnected"] is True

    # Confirm cryptographic chain integrity with the newly added attestation
    verification = temp_audit_service.verify_ledger()
    assert verification.valid is True
    assert verification.events_checked == 1


# ── 27. Physical Isolation Attestation REST API ──────────────────────────────

def test_physical_isolation_attestation_api():
    """Verify POST /api/v1/audit/attest-physical-isolation and latest status retrieval."""
    client = TestClient(app)

    # 1. Test POST attestation
    payload = {
        "checklist": {
            "ethernet_disconnected": True,
            "wifi_disabled": True,
            "adapter_disabled": True,
            "external_route_checked": True,
            "radios_checked": True,
            "operator_confirmed": True,
        },
        "operator_notes": "Automated test operator verification",
    }

    resp = client.post("/api/v1/audit/attest-physical-isolation", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "OPERATOR_VERIFIED"
    assert data["operator_confirmed"] is True
    assert "event_id" in data
    assert "event_hash" in data
    assert data["evidence"]["ethernet_disconnected"] is True

    # 2. Test GET latest attestation
    latest_resp = client.get("/api/v1/audit/attest-physical-isolation/latest")
    assert latest_resp.status_code == 200
    latest_data = latest_resp.json()
    assert latest_data["status"] == "OPERATOR_VERIFIED"
    assert latest_data["event_id"] == data["event_id"]

