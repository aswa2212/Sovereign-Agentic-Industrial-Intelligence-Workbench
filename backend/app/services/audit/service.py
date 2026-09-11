"""Unified AuditService managing the local audit ledger, integrity, and sovereignty."""

from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.services.audit.event_store import LocalAuditEventStore
from app.services.audit.hash_chain import GENESIS_HASH, calculate_event_hash
from app.services.audit.integrity import AuditIntegrityVerifier
from app.services.audit.models import (
    AuditEvent,
    AuditEventType,
    AuditVerificationResult,
    NetworkObservationReport,
    SovereigntyStatus,
)
from app.services.audit.network_monitor import RuntimeNetworkMonitor
from app.services.audit.sovereignty import SovereigntyChecker

SENSITIVE_KEY_SUBSTRINGS = {
    "api_key",
    "secret",
    "password",
    "token",
    "authorization",
    "credential",
    "private_key",
    "access_token"
}


def sanitize_metadata(data: Any) -> Any:
    """
    Recursively scrub sensitive keys and credential-like strings from metadata.
    Replaces sensitive values with '[REDACTED]'.
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(sub in k_lower for sub in SENSITIVE_KEY_SUBSTRINGS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_metadata(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_metadata(item) for item in data]
    return data


class AuditService:
    """
    Core service for recording tamper-evident audit events, verifying ledger integrity,
    monitoring runtime network activity, and enforcing sovereignty constraints.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            settings = get_settings()
            data_dir = getattr(settings, "data_dir", None) or getattr(settings, "DATA_DIR", None) or (settings.project_root / "data")
            storage_path = Path(data_dir) / "audit" / "events.jsonl"
        self.storage_path = Path(storage_path)
        self.store = LocalAuditEventStore(self.storage_path)
        self.verifier = AuditIntegrityVerifier()
        self.network_monitor = RuntimeNetworkMonitor()
        self.sovereignty_checker = SovereigntyChecker(self.network_monitor)
        self._write_lock = threading.Lock()

    def record_event(
        self,
        event_type: AuditEventType,
        action: str,
        task_id: Optional[str] = None,
        agent_state: Optional[str] = None,
        model_role: Optional[str] = None,
        capability: Optional[str] = None,
        tool_name: Optional[str] = None,
        source: Optional[str] = None,
        status: str = "SUCCESS",
        duration_ms: Optional[float] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        Create, sanitize, hash-chain, and durably store an AuditEvent.
        Guarantees thread-safe sequential linkage.
        """
        clean_metadata = sanitize_metadata(metadata or {})

        with self._write_lock:
            last_event = self.store.get_last_event()
            previous_hash = last_event.event_hash if last_event else GENESIS_HASH

            event = AuditEvent(
                task_id=task_id,
                event_type=event_type,
                action=action,
                agent_state=agent_state,
                model_role=model_role,
                capability=capability,
                tool_name=tool_name,
                source=source,
                status=status,
                duration_ms=duration_ms,
                message=message,
                metadata=clean_metadata,
                previous_hash=previous_hash,
                event_hash=""
            )

            # Compute SHA-256 hash bound to canonical representation and previous_hash
            event.event_hash = calculate_event_hash(event, previous_hash)

            # Append to storage
            stored_event = self.store.append(event)
            return stored_event

    def verify_ledger(self) -> AuditVerificationResult:
        """Verify the integrity of all events in the audit ledger."""
        all_events = self.store.get_all_events()
        return self.verifier.verify_chain(all_events)

    def observe_network(self) -> NetworkObservationReport:
        """Observe runtime network activity safely without transmitting telemetry."""
        return self.network_monitor.observe_connections()

    def check_sovereignty(self, air_gapped_mode: Optional[bool] = None) -> SovereigntyStatus:
        """Check provider configuration and network behavior against sovereignty rules."""
        return self.sovereignty_checker.evaluate_sovereignty(air_gapped_mode=air_gapped_mode)

    def get_events(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEvent]:
        """Query stored events."""
        return self.store.query(task_id=task_id, event_type=event_type, limit=limit, offset=offset)

    def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """Retrieve a specific event by ID."""
        return self.store.get_event_by_id(event_id)

    def count_events(self) -> int:
        """Total count of recorded audit events."""
        return self.store.count()


_global_audit_service: Optional[AuditService] = None
_global_lock = threading.Lock()


def get_audit_service() -> AuditService:
    """Retrieve or initialize the global singleton AuditService."""
    global _global_audit_service
    with _global_lock:
        if _global_audit_service is None:
            _global_audit_service = AuditService()
        return _global_audit_service
