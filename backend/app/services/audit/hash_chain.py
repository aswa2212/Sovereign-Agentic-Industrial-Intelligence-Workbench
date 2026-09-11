"""Deterministic canonical serialization and SHA-256 hash-chaining."""

import hashlib
import json
from typing import Any, Dict
from app.services.audit.models import AuditEvent

GENESIS_HASH = "GENESIS_" + "0" * 56  # 64 characters total


def _canonicalize_value(val: Any) -> Any:
    """Recursively convert values to JSON-serializable deterministic types."""
    if isinstance(val, dict):
        return {str(k): _canonicalize_value(v) for k, v in sorted(val.items())}
    elif isinstance(val, (list, tuple)):
        return [_canonicalize_value(item) for item in val]
    elif hasattr(val, "value"):  # Enum support
        return val.value
    elif val is None or isinstance(val, (bool, int, float, str)):
        return val
    else:
        return str(val)


def canonicalize_event(event: AuditEvent) -> bytes:
    """
    Deterministically serialize an AuditEvent to canonical JSON bytes.
    Excludes event_hash to enable cryptographic signing/hashing.
    Ensures sorted keys, compact separators, and UTF-8 encoding.
    """
    event_dict = event.model_dump(exclude={"event_hash"})
    cleaned_dict = _canonicalize_value(event_dict)
    json_str = json.dumps(
        cleaned_dict,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )
    return json_str.encode("utf-8")


def calculate_event_hash(event: AuditEvent, previous_hash: str) -> str:
    """
    Calculate the SHA-256 hash of the canonical event combined with previous_hash.
    SHA256(canonical_event_bytes + previous_hash.encode('utf-8'))
    """
    event.previous_hash = previous_hash
    canonical_bytes = canonicalize_event(event)
    combined = canonical_bytes + previous_hash.encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def verify_event_hash(event: AuditEvent, expected_previous_hash: str) -> bool:
    """Verify that an event's previous_hash and event_hash match recalculation."""
    if event.previous_hash != expected_previous_hash:
        return False
    calculated = calculate_event_hash(event, expected_previous_hash)
    return event.event_hash == calculated
