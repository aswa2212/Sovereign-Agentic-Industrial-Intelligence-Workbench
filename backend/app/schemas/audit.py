"""Pydantic schemas for the Audit & Sovereignty API endpoints."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.services.audit.models import (
    AuditEvent,
    AuditEventType,
    AuditVerificationResult,
    NetworkObservationReport,
    SovereigntyStatus,
)


class AuditEventResponse(BaseModel):
    """Schema for returning a single audit event."""
    event: AuditEvent


class AuditEventListResponse(BaseModel):
    """Schema for returning paginated audit events."""
    items: List[AuditEvent]
    total: int
    limit: int
    offset: int


class AuditIntegrityResponse(BaseModel):
    """Schema for audit ledger integrity check results."""
    verification: AuditVerificationResult


class NetworkObservationResponse(BaseModel):
    """Schema for network observation endpoint."""
    report: NetworkObservationReport


class SovereigntyResponse(BaseModel):
    """Schema for sovereignty and air-gap enforcement status."""
    sovereignty: SovereigntyStatus


class PhysicalIsolationAttestationRequest(BaseModel):
    """Auditable checklist payload asserted by the operator."""
    ethernet_disconnected: bool = Field(True, description="Physical Ethernet cable confirmed detached")
    wifi_disabled: bool = Field(True, description="Wi-Fi radio disabled in OS settings")
    adapter_disabled: bool = Field(True, description="External/cellular network adapters disabled")
    external_route_checked: bool = Field(True, description="Confirmed no active default gateway route to WAN")
    radios_checked: bool = Field(True, description="Unnecessary wireless/Bluetooth interfaces audited")
    operator_confirmed: bool = Field(True, description="Explicit operator affirmation")
    operator_notes: Optional[str] = Field(None, description="Optional observation or test session ID")


class PhysicalIsolationAttestationResponse(BaseModel):
    """Tamper-evident attestation certificate recorded in audit ledger."""
    status: str
    event_id: str
    timestamp: str
    event_hash: str
    hostname: str
    operator_confirmed: bool
    evidence: Dict[str, Any]
    network_observation: Dict[str, Any]
    sovereignty_status: str

