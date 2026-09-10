"""
SIH26117 — Task Router REST API Endpoint
POST /api/v1/router/route — classify a task and return a routing decision.

CONTRACT:
- This endpoint performs routing ONLY. It does NOT invoke inference.
- It does NOT call Ollama, load models, or make network calls.
- It returns a RoutingDecision that downstream callers (Agent, UI) can act on.
- All classification is deterministic and offline-capable.
"""

from fastapi import APIRouter, Depends, HTTPException, status

try:
    from app.core.config import Settings, get_settings
    from app.schemas.router import RouteRequest, RouteResponse, RuleEvidenceSchema
    from app.services.router import RuleRouter, TaskRouter
except ImportError:
    from backend.app.core.config import Settings, get_settings
    from backend.app.schemas.router import RouteRequest, RouteResponse, RuleEvidenceSchema
    from backend.app.services.router import RuleRouter, TaskRouter

router = APIRouter(prefix="/router", tags=["Task Router"])


# ---------------------------------------------------------------------------
# Application-level TaskRouter dependency (lazy singleton)
# ---------------------------------------------------------------------------

_task_router: TaskRouter | None = None


def get_task_router() -> TaskRouter:
    """
    FastAPI dependency returning the initialized TaskRouter singleton.

    Builds a RuleRouter from settings on first call (lazy initialization).
    Tests override this via set_task_router().
    """
    global _task_router
    if _task_router is None:
        _task_router = RuleRouter.from_settings()
    return _task_router


def set_task_router(r: TaskRouter | None) -> None:
    """Override the global TaskRouter — used by tests to inject custom rules."""
    global _task_router
    _task_router = r


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/route",
    response_model=RouteResponse,
    summary="Route a Task",
    description=(
        "Classify a user task and return a deterministic routing decision "
        "indicating which model role, capability, and confidence level "
        "apply. This endpoint does NOT invoke inference — it is a pure "
        "classification step that the Agent Orchestrator consumes."
    ),
)
async def route_task(
    request: RouteRequest,
    settings: Settings = Depends(get_settings),
    task_router: TaskRouter = Depends(get_task_router),
) -> RouteResponse:
    """
    Classify the submitted task and return a routing decision.

    - Uses Level 0 (RuleRouter) by default.
    - Returns full audit evidence: matched rules, confidence, fallback status.
    - No inference is performed.
    - No network calls are made.
    """
    if not task_router.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task router is not available. Check router configuration.",
        )

    try:
        decision = task_router.route(
            task=request.task,
            context=request.context,
            request_id=request.request_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Router error: {exc}",
        )

    # Map internal domain objects to API schema
    candidates_schema = [
        RuleEvidenceSchema(
            rule_id=c.rule_id,
            matched_patterns=c.matched_patterns,
            task_type=c.task_type.value,
            confidence=c.confidence,
            reason=c.reason,
        )
        for c in decision.candidates
    ]

    return RouteResponse(
        task_type=decision.task_type.value,
        capability=decision.capability.value,
        model_role=decision.model_role.value,
        confidence=decision.confidence,
        routing_method=decision.routing_method,
        fallback_used=decision.fallback_used,
        reason=decision.reason,
        matched_rule_ids=decision.matched_rule_ids,
        primary_rule_id=decision.primary_rule_id,
        candidates=candidates_schema,
        request_id=decision.request_id,
        timestamp=decision.timestamp,
    )
