"""
SIH26117 — Agent REST API Endpoints
Provides endpoints for executing agent tasks and retrieving observable state traces.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status

try:
    from app.schemas.agent import (
        AgentRunRequest,
        AgentRunResponse,
        AgentTaskStatusResponse,
    )
    from app.services.agent.base import AgentState
    from app.services.agent.orchestrator import AgentStateMachineOrchestrator
except ImportError:
    from backend.app.schemas.agent import (
        AgentRunRequest,
        AgentRunResponse,
        AgentTaskStatusResponse,
    )
    from backend.app.services.agent.base import AgentState
    from backend.app.services.agent.orchestrator import AgentStateMachineOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

_orchestrator_instance: Optional[AgentStateMachineOrchestrator] = None


def get_orchestrator() -> AgentStateMachineOrchestrator:
    """Return singleton AgentStateMachineOrchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentStateMachineOrchestrator()
    return _orchestrator_instance


def set_orchestrator(orchestrator: AgentStateMachineOrchestrator) -> None:
    """Override singleton orchestrator (useful for test isolation)."""
    global _orchestrator_instance
    _orchestrator_instance = orchestrator


@router.post(
    "/run",
    response_model=AgentRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute an autonomous task through the agent state machine",
)
async def run_agent_task(req: AgentRunRequest) -> AgentRunResponse:
    """
    Submits a task to the sovereign agent orchestrator.
    Transitions through RECEIVE -> UNDERSTAND -> PLAN -> EXECUTE -> OBSERVE -> REFLECT -> VALIDATE -> DELIVER.
    """
    clean_task = req.task.strip()
    if not clean_task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_TASK", "message": "Task instruction cannot be empty or whitespace."},
        )

    orchestrator = get_orchestrator()
    context = await orchestrator.execute_task(task=clean_task, max_steps=req.max_steps)

    status_str = "completed" if context.current_state == AgentState.DELIVER else "failed"

    return AgentRunResponse(
        task_id=context.task_id,
        status=status_str,
        final_state=context.current_state,
        result=context.final_result,
        execution_trace=context.execution_trace,
        citations=context.get_citations(),
        errors=context.errors,
    )


@router.get(
    "/{task_id}",
    response_model=AgentTaskStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get execution trace and state of a task",
)
async def get_task_status(task_id: str) -> AgentTaskStatusResponse:
    """Inspect intermediate or final execution trace for a given task ID."""
    orchestrator = get_orchestrator()
    context = orchestrator.get_task_context(task_id)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": f"Task '{task_id}' not found in runtime registry."},
        )

    return AgentTaskStatusResponse(
        task_id=context.task_id,
        current_state=context.current_state,
        step_count=context.step_count,
        started_at=context.started_at,
        updated_at=context.updated_at,
        execution_trace=context.execution_trace,
        errors=context.errors,
    )
