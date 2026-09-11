"""
SIH26117 — Agent Task Planner
Decomposes user tasks into structured, bounded execution plans (maximum 8 steps).
Provides deterministic local planning for offline CI and SOP workflows without hardcoded model IDs.
"""

import logging
import uuid
from typing import Optional

try:
    from app.core.config import get_settings
    from app.services.router.decision import RoutingDecision
    from app.services.agent.base import PlanningError
    from app.services.agent.models import Plan, PlanStep
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.services.router.decision import RoutingDecision
    from backend.app.services.agent.base import PlanningError
    from backend.app.services.agent.models import Plan, PlanStep

logger = logging.getLogger(__name__)


class Planner:
    """
    Decomposes user requests into structured, executable multi-step plans.
    Enforces maximum step ceiling (default 8).
    """

    def __init__(self, max_steps: Optional[int] = None) -> None:
        settings = get_settings()
        self.max_steps = max_steps or settings.agent_max_steps

    async def create_plan(
        self,
        task: str,
        task_id: str,
        routing_decision: Optional[RoutingDecision] = None,
    ) -> Plan:
        """
        Generate a structured Plan with PlanStep items.
        Raises PlanningError if plan exceeds max_steps limit.
        """
        if not task or not task.strip():
            raise PlanningError("Cannot create plan for empty task.")

        clean_task = task.strip().lower()
        steps = []

        # Heuristic 1: Calculation requests (e.g. remaining life, corrosion rate)
        needs_calculation = any(k in clean_task for k in ["calculate", "corrosion rate", "remaining life", "formula"])

        # Heuristic 2: RAG / Knowledge retrieval (SOP, standard, thickness, spec, clause, code)
        needs_rag = any(
            k in clean_task for k in [
                "sop", "standard", "thickness", "requirement", "code", "rule",
                "carbon steel", "class 150", "find", "what is", "minimum"
            ]
        ) or not needs_calculation

        step_counter = 1

        if needs_rag:
            steps.append(
                PlanStep(
                    id=f"step_{step_counter}",
                    description="Retrieve relevant MRPL SOPs and industrial inspection clauses",
                    capability="rag_retrieval",
                    tool_name="rag_retrieval",
                    input_payload={"query": task.strip(), "top_k": 3},
                )
            )
            step_counter += 1

        if needs_calculation:
            steps.append(
                PlanStep(
                    id=f"step_{step_counter}",
                    description="Execute deterministic engineering calculation for equipment life",
                    capability="calculation",
                    tool_name="calculation",
                    input_payload={"calc_type": "remaining_life"},
                )
            )
            step_counter += 1

        # Enforce maximum steps limit
        if len(steps) > self.max_steps:
            raise PlanningError(
                f"Generated plan has {len(steps)} steps, exceeding safety limit of {self.max_steps} steps."
            )

        plan = Plan(
            plan_id=uuid.uuid4().hex[:12],
            task_id=task_id,
            goal=task.strip(),
            steps=steps,
        )

        logger.info(
            "Planner created plan '%s' with %d steps for task [%s]",
            plan.plan_id,
            len(plan.steps),
            task_id[:8],
        )
        return plan
