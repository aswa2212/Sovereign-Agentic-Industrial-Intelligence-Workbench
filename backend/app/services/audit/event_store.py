"""Local append-only JSONL event storage for audit events."""

import json
from pathlib import Path
import threading
from typing import List, Optional
from app.services.audit.exceptions import AuditStorageError
from app.services.audit.models import AuditEvent, AuditEventType


class LocalAuditEventStore:
    """
    Append-only local JSONL store for tamper-evident audit events.
    Thread-safe and flushes writes to disk immediately.
    """

    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self._lock = threading.Lock()
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.storage_path.exists():
                self.storage_path.touch()
        except Exception as e:
            raise AuditStorageError(f"Failed to initialize audit storage at {self.storage_path}: {e}")

    def append(self, event: AuditEvent) -> AuditEvent:
        """Append an AuditEvent to the JSONL ledger in a thread-safe manner."""
        with self._lock:
            try:
                line = event.model_dump_json() + "\n"
                with open(self.storage_path, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
                return event
            except Exception as e:
                raise AuditStorageError(f"Failed to append audit event: {e}")

    def get_last_event(self) -> Optional[AuditEvent]:
        """Read the most recent event from the ledger without loading everything into memory if large."""
        with self._lock:
            if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
                return None
            try:
                last_line = None
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line_str = line.strip()
                        if line_str:
                            last_line = line_str
                if last_line:
                    return AuditEvent.model_validate_json(last_line)
                return None
            except Exception as e:
                raise AuditStorageError(f"Failed to read last audit event: {e}")

    def get_all_events(self) -> List[AuditEvent]:
        """Load all audit events in chronological order."""
        with self._lock:
            events: List[AuditEvent] = []
            if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
                return events
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    for line_no, line in enumerate(f, start=1):
                        line_str = line.strip()
                        if not line_str:
                            continue
                        try:
                            events.append(AuditEvent.model_validate_json(line_str))
                        except Exception as parse_err:
                            raise AuditStorageError(f"Malformed audit event at line {line_no}: {parse_err}")
                return events
            except AuditStorageError:
                raise
            except Exception as e:
                raise AuditStorageError(f"Failed to read audit events: {e}")

    def get_event_by_id(self, event_id: str) -> Optional[AuditEvent]:
        """Search for a specific event by ID."""
        for event in self.get_all_events():
            if event.event_id == event_id:
                return event
        return None

    def query(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEvent]:
        """Query audit events with optional filters."""
        all_events = self.get_all_events()
        filtered = [
            e for e in all_events
            if (task_id is None or e.task_id == task_id) and
               (event_type is None or e.event_type == event_type)
        ]
        return filtered[offset: offset + limit]

    def count(self) -> int:
        """Count total recorded audit events."""
        return len(self.get_all_events())
