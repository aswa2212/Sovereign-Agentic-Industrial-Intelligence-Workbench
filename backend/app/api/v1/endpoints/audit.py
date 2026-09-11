"""Audit and Sovereignty API endpoints (read/verify oriented)."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.audit import (
    AuditEventListResponse,
    AuditEventResponse,
    AuditIntegrityResponse,
    NetworkObservationResponse,
    SovereigntyResponse,
)
from app.services.audit import (
    AuditEventType,
    get_audit_service,
)

router = APIRouter(prefix="/audit", tags=["Audit & Sovereignty"])


@router.get(
    "/events",
    response_model=AuditEventListResponse,
    summary="Query audit ledger events",
    description="Retrieve paginated audit events with optional task_id and event_type filters."
)
def get_audit_events(
    task_id: Optional[str] = Query(None, description="Filter events by task ID"),
    event_type: Optional[AuditEventType] = Query(None, description="Filter events by event type"),
    limit: int = Query(100, ge=1, le=1000, description="Max events to return"),
    offset: int = Query(0, ge=0, description="Offset into events ledger")
):
    service = get_audit_service()
    events = service.get_events(task_id=task_id, event_type=event_type, limit=limit, offset=offset)
    total = service.count_events()
    return AuditEventListResponse(
        items=events,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/events/{event_id}",
    response_model=AuditEventResponse,
    summary="Get single audit event by ID",
    description="Retrieve an audit event by its unique UUID."
)
def get_audit_event_by_id(event_id: str):
    service = get_audit_service()
    event = service.get_event(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit event with ID '{event_id}' not found."
        )
    return AuditEventResponse(event=event)


@router.get(
    "/integrity",
    response_model=AuditIntegrityResponse,
    summary="Verify audit chain cryptographic integrity",
    description="Validates full chronological hash-chain continuity and detects any tampering, modification, or deletion."
)
def verify_audit_integrity():
    service = get_audit_service()
    result = service.verify_ledger()
    return AuditIntegrityResponse(verification=result)


@router.get(
    "/network",
    response_model=NetworkObservationResponse,
    summary="Observe runtime network activity",
    description="Provides safe, local-only runtime network socket observation without external telemetry."
)
def observe_runtime_network():
    service = get_audit_service()
    report = service.observe_network()
    return NetworkObservationResponse(report=report)


@router.get(
    "/sovereignty",
    response_model=SovereigntyResponse,
    summary="Check local provider sovereignty",
    description="Verifies that all configured model providers and active connections comply with sovereign local-only policy."
)
def check_sovereignty_status(
    air_gapped_mode: Optional[bool] = Query(None, description="Override air-gapped mode flag for simulation")
):
    service = get_audit_service()
    status_report = service.check_sovereignty(air_gapped_mode=air_gapped_mode)
    return SovereigntyResponse(sovereignty=status_report)
