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
