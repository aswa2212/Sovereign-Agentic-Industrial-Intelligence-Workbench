"""Phase 11 Audit & Sovereignty Evidence module."""

from app.services.audit.event_store import LocalAuditEventStore
from app.services.audit.exceptions import (
    AuditError,
    AuditIntegrityError,
    AuditStorageError,
    SovereigntyViolationError,
)
from app.services.audit.hash_chain import (
    GENESIS_HASH,
    calculate_event_hash,
    canonicalize_event,
    verify_event_hash,
)
from app.services.audit.integrity import AuditIntegrityVerifier
from app.services.audit.models import (
    AuditEvent,
    AuditEventType,
    AuditVerificationResult,
    NetworkConnectionRecord,
    NetworkObservationReport,
    ProviderSovereigntyCheck,
    SovereigntyStatus,
)
from app.services.audit.network_monitor import RuntimeNetworkMonitor
from app.services.audit.service import AuditService, get_audit_service
from app.services.audit.sovereignty import SovereigntyChecker

__all__ = [
    "AuditEvent",
    "AuditEventType",
    "AuditVerificationResult",
    "NetworkConnectionRecord",
    "NetworkObservationReport",
    "ProviderSovereigntyCheck",
    "SovereigntyStatus",
    "AuditError",
    "AuditStorageError",
    "AuditIntegrityError",
    "SovereigntyViolationError",
    "GENESIS_HASH",
    "canonicalize_event",
    "calculate_event_hash",
    "verify_event_hash",
    "LocalAuditEventStore",
    "AuditIntegrityVerifier",
    "RuntimeNetworkMonitor",
    "SovereigntyChecker",
    "AuditService",
    "get_audit_service",
]
