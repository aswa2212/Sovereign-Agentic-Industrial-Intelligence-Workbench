"""
SIH26117 — Task Router Taxonomy
Defines the closed vocabulary of task types, capabilities, and model roles used
throughout the routing pipeline. Using enums ensures compile-time validation and
prevents string-drift across module boundaries.

TAXONOMY DESIGN NOTES:
- TaskType  — What the user is asking for (intent category).
- Capability — What kind of processing is needed to fulfil the task.
- ModelRole  — Which named model slot in model_tiers.yaml handles the capability.

The mapping TaskType → Capability → ModelRole is declared in CAPABILITY_MAP and
ROLE_MAP below. The router consults these tables; it never hardcodes model IDs.

KNOWN LIMITATIONS:
- The taxonomy is manually curated for MRPL's industrial workflow.
- Rule routing accuracy has not yet been formally benchmarked.
- Ambiguous tasks (e.g. a P&ID described in text) may be mis-classified at Level 0.
"""

from enum import Enum
from typing import Dict


# ---------------------------------------------------------------------------
# Task Type — what kind of task the user submitted
# ---------------------------------------------------------------------------

class TaskType(str, Enum):
    """Closed vocabulary of task categories recognised by the routing system."""

    # Code generation / debugging / scripting
    CODING = "coding"

    # Visual understanding: P&ID inspection, diagram reading, image-based QA
    VISION = "vision"

    # Deep analysis of technical / regulatory documents
    DOCUMENT_ANALYSIS = "document_analysis"

    # Text compression and synthesis of existing content
    SUMMARIZATION = "summarization"

    # Numerical / formula-based computation
    CALCULATION = "calculation"

    # Structured data pull from unstructured text or images
    EXTRACTION = "extraction"

    # Multi-step comparative reasoning, decision support, trade-off analysis
    REASONING = "reasoning"

    # No specific signal detected — default safe category
    GENERAL = "general"


# ---------------------------------------------------------------------------
# Capability — what processing modality is required
# ---------------------------------------------------------------------------

class Capability(str, Enum):
    """
    Processing capability required to fulfil a task.
    Decoupled from TaskType so multiple task types can share a capability.
    """

    REASONING = "reasoning"
    CODING = "coding"
    VISION = "vision"
    EXTRACTION = "extraction"
    CALCULATION = "calculation"
    GENERAL = "general"


# ---------------------------------------------------------------------------
# ModelRole — the named slot in model_tiers.yaml
# ---------------------------------------------------------------------------

class ModelRole(str, Enum):
    """
    Named model slot in the active hardware tier configuration.
    Must match the role keys defined in models/configs/model_tiers.yaml.
    The router selects a role; the ModelManager resolves it to a model tag.
    """

    ROUTER = "router"
    REASONING = "reasoning"
    CODER = "coder"
    VISION = "vision"
    EMBEDDING = "embedding"


# ---------------------------------------------------------------------------
# Capability → ModelRole mapping table
# ---------------------------------------------------------------------------
# This is the ONLY place where capability is mapped to a model role.
# The router reads this table; it never hardcodes model IDs or model filenames.

CAPABILITY_ROLE_MAP: Dict[Capability, ModelRole] = {
    Capability.REASONING: ModelRole.REASONING,
    Capability.CODING: ModelRole.CODER,
    Capability.VISION: ModelRole.VISION,
    Capability.EXTRACTION: ModelRole.REASONING,   # extraction via reasoning model
    Capability.CALCULATION: ModelRole.REASONING,  # calculation scaffolded via reasoning
    Capability.GENERAL: ModelRole.REASONING,      # safe universal fallback
}


# ---------------------------------------------------------------------------
# TaskType → Capability mapping table
# ---------------------------------------------------------------------------

TASK_CAPABILITY_MAP: Dict[TaskType, Capability] = {
    TaskType.CODING: Capability.CODING,
    TaskType.VISION: Capability.VISION,
    TaskType.DOCUMENT_ANALYSIS: Capability.REASONING,
    TaskType.SUMMARIZATION: Capability.REASONING,
    TaskType.CALCULATION: Capability.CALCULATION,
    TaskType.EXTRACTION: Capability.EXTRACTION,
    TaskType.REASONING: Capability.REASONING,
    TaskType.GENERAL: Capability.GENERAL,
}


def capability_for_task(task_type: TaskType) -> Capability:
    """Return the processing capability required for a given task type."""
    return TASK_CAPABILITY_MAP[task_type]


def role_for_capability(capability: Capability) -> ModelRole:
    """Return the model role that handles a given processing capability."""
    return CAPABILITY_ROLE_MAP[capability]


def role_for_task(task_type: TaskType) -> ModelRole:
    """
    Convenience shortcut: resolve task_type → capability → model_role in one call.
    This is the function the RuleRouter calls after classification.
    """
    cap = capability_for_task(task_type)
    return role_for_capability(cap)
