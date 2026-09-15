"""Pydantic models and enums for Phase 11 Audit & Sovereignty Evidence."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Controlled taxonomy of audit event types."""
    TASK_CREATED = "TASK_CREATED"
    TASK_STARTED = "TASK_STARTED"
    STATE_CHANGED = "STATE_CHANGED"
    PLAN_CREATED = "PLAN_CREATED"
    MODEL_ROUTED = "MODEL_ROUTED"
    MODEL_INVOKED = "MODEL_INVOKED"
    KNOWLEDGE_RETRIEVED = "KNOWLEDGE_RETRIEVED"
    VISION_ANALYSIS = "VISION_ANALYSIS"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    VALIDATION_STARTED = "VALIDATION_STARTED"
    VALIDATION_COMPLETED = "VALIDATION_COMPLETED"
    DELIVERABLE_CREATED = "DELIVERABLE_CREATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    NETWORK_CHECK = "NETWORK_CHECK"
    SOVEREIGNTY_CHECK = "SOVEREIGNTY_CHECK"
    PHYSICAL_ISOLATION_ATTESTED = "PHYSICAL_ISOLATION_ATTESTED"


class AuditEvent(BaseModel):
    """Tamper-evident audit event model with hash-chain linkage."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    task_id: Optional[str] = None
    event_type: AuditEventType
    action: str
    agent_state: Optional[str] = None
    model_role: Optional[str] = None
    capability: Optional[str] = None
    tool_name: Optional[str] = None
    source: Optional[str] = None
    status: str = "SUCCESS"
    duration_ms: Optional[float] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    previous_hash: str = ""
    event_hash: str = ""

    model_config = {
        "frozen": False,
        "populate_by_name": True,
        "protected_namespaces": ()
    }


class AuditVerificationResult(BaseModel):
    """Structured result of audit hash-chain integrity verification."""
    valid: bool
    events_checked: int
    first_invalid_event: Optional[str] = None
    first_invalid_index: Optional[int] = None
    error_detail: Optional[str] = None


class NetworkConnectionRecord(BaseModel):
    """Safe representation of an observed network connection."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    pid: Optional[int] = None
    process_name: Optional[str] = None
    local_address: str
    remote_address: Optional[str] = None
    status: str = "ESTABLISHED"
    is_loopback: bool = True


class NetworkObservationReport(BaseModel):
    """Summary report of runtime network observation."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    observation_method: str
    total_connections: int
    loopback_connections: int
    non_loopback_connections: int
    connections: List[NetworkConnectionRecord] = Field(default_factory=list)
    warning: Optional[str] = None


class ProviderSovereigntyCheck(BaseModel):
    """Result of verifying an individual provider's network locality."""
    provider_name: str
    configured_url: Optional[str] = None
    is_local: bool
    host: Optional[str] = None
    port: Optional[int] = None
    error: Optional[str] = None


class SovereigntyStatus(BaseModel):
    """Structured report of software-level local-provider sovereignty enforcement."""
    status: str  # "PASS" | "FAIL"
    local_mode_enabled: bool
    provider_checks: List[ProviderSovereigntyCheck] = Field(default_factory=list)
    network_observation: Optional[NetworkObservationReport] = None
    external_connections_observed: bool = False
    violations: List[str] = Field(default_factory=list)
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    note: str = (
        "Software-level local-provider enforcement and runtime network evidence. "
        "Physical air-gap isolation remains a deployment/environment control."
    )
