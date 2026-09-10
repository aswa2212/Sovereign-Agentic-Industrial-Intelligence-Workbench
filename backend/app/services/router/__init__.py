"""
SIH26117 — Task Router Package

Public exports for the rest of the application:
- RuleRouter          → Level 0 deterministic implementation (use this for Phase 3)
- TaskRouter          → Abstract base class for all router implementations
- SemanticRouter      → Level 1 extension point (NOT YET IMPLEMENTED)
- ClassifierRouter    → Level 2 extension point (NOT YET IMPLEMENTED)
- HybridRouter        → Future cascade scaffold
- RoutingDecision     → Strongly-typed routing output contract
- RuleMatchEvidence   → Audit evidence for one fired rule
- TaskType            → Task category enum
- Capability          → Processing modality enum
- ModelRole           → Model slot enum (must match model_tiers.yaml keys)
"""

from .base import ClassifierRouter, HybridRouter, SemanticRouter, TaskRouter
from .decision import RoutingDecision, RuleMatchEvidence
from .rule_router import RuleRouter
from .taxonomy import (
    CAPABILITY_ROLE_MAP,
    TASK_CAPABILITY_MAP,
    Capability,
    ModelRole,
    TaskType,
    capability_for_task,
    role_for_capability,
    role_for_task,
)

__all__ = [
    # Routers
    "TaskRouter",
    "RuleRouter",
    "SemanticRouter",
    "ClassifierRouter",
    "HybridRouter",
    # Decision contracts
    "RoutingDecision",
    "RuleMatchEvidence",
    # Taxonomy
    "TaskType",
    "Capability",
    "ModelRole",
    # Mapping helpers
    "CAPABILITY_ROLE_MAP",
    "TASK_CAPABILITY_MAP",
    "capability_for_task",
    "role_for_capability",
    "role_for_task",
]
