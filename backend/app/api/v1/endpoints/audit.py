"""Audit and Sovereignty API endpoints (read/verify oriented)."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.audit import (
    AuditEventListResponse,
    AuditEventResponse,
    AuditIntegrityResponse,
    NetworkObservationResponse,
    PhysicalIsolationAttestationRequest,
    PhysicalIsolationAttestationResponse,
    SovereigntyResponse,
)
from app.services.audit import (
    AuditEventType,
    get_audit_service,
)
import socket

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


@router.post(
    "/attest-physical-isolation",
    response_model=PhysicalIsolationAttestationResponse,
    summary="Record explicit operator physical air-gap attestation",
    description=(
        "Records an auditable operator assertion confirming physical network isolation "
        "(Ethernet unplugged, Wi-Fi/radios disabled). Does NOT falsely claim software proved physical state; "
        "stores an immutable, hash-chained operator attestation in the local audit ledger."
    ),
)
def record_physical_isolation_attestation(req: PhysicalIsolationAttestationRequest):
    if not req.operator_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operator confirmation required to attest physical isolation.",
        )

    service = get_audit_service()
    report = service.observe_network()
    sov = service.check_sovereignty()
    hostname = socket.gethostname()

    evidence_dict = {
        "ethernet_disconnected": req.ethernet_disconnected,
        "wifi_disabled": req.wifi_disabled,
        "adapter_disabled": req.adapter_disabled,
        "external_route_checked": req.external_route_checked,
        "radios_checked": req.radios_checked,
        "operator_confirmed": True,
        "operator_notes": req.operator_notes,
        "hostname": hostname,
        "observed_external_connections": 1 if sov.external_connections_observed else 0,
        "observed_non_loopback": report.non_loopback_connections,
        "observed_loopback": report.loopback_connections,
        "total_observed_connections": report.total_connections,
        "sovereignty_status": sov.status,
    }

    event = service.record_event(
        event_type=AuditEventType.PHYSICAL_ISOLATION_ATTESTED,
        action="Operator Attested Physical Network Isolation",
        source="operator_attestation",
        status="SUCCESS",
        message=(
            f"Physical isolation verified by operator on {hostname}: "
            f"Ethernet={req.ethernet_disconnected}, Wi-Fi={req.wifi_disabled}, "
            f"WAN Route={req.external_route_checked}"
        ),
        metadata=evidence_dict,
    )

    return PhysicalIsolationAttestationResponse(
        status="OPERATOR_VERIFIED",
        event_id=event.event_id,
        timestamp=event.timestamp,
        event_hash=event.event_hash,
        hostname=hostname,
        operator_confirmed=True,
        evidence=evidence_dict,
        network_observation={
            "total_connections": report.total_connections,
            "non_loopback_connections": report.non_loopback_connections,
            "loopback_connections": report.loopback_connections,
            "external_connections": 1 if sov.external_connections_observed else 0,
            "status": sov.status,
            "timestamp": report.timestamp,
        },
        sovereignty_status=sov.status,
    )


@router.get(
    "/attest-physical-isolation/latest",
    summary="Get latest operator physical air-gap attestation",
    description="Returns the most recent physical isolation attestation event if one exists in the local ledger.",
)
def get_latest_physical_isolation_attestation():
    service = get_audit_service()
    events = service.get_events(event_type=AuditEventType.PHYSICAL_ISOLATION_ATTESTED, limit=10000)
    if not events:
        return {
            "status": "NOT_ATTESTED",
            "message": "Physical network isolation has not been attested by an operator for this session.",
            "event_id": "",
            "timestamp": "",
            "event_hash": "",
            "hostname": "",
            "operator_confirmed": False,
            "evidence": {},
            "network_observation": {},
            "sovereignty_status": "",
            "attestation": None,
        }
    latest = events[-1]
    return {
        "status": "OPERATOR_VERIFIED",
        "message": "Physical isolation attested by operator.",
        "event_id": latest.event_id,
        "timestamp": latest.timestamp,
        "event_hash": latest.event_hash,
        "hostname": latest.metadata.get("hostname", "local-workstation"),
        "operator_confirmed": latest.metadata.get("checklist", {}).get("operator_confirmed", True),
        "evidence": latest.metadata.get("checklist", {}),
        "network_observation": latest.metadata.get("network_observation", {}),
        "sovereignty_status": latest.metadata.get("sovereignty_status", "PASS"),
        "attestation": latest.model_dump(),
    }

