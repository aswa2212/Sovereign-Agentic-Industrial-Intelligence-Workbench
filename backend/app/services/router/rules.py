"""
SIH26117 — Task Router Rules Engine
Defines RoutingRule dataclasses and the MRPL-domain rule registry.

RULE ARCHITECTURE:
- A RoutingRule is a declarative, named pattern specification.
- Rules are evaluated by scanning lowercase task text for keyword matches.
- Priority controls which rule wins when multiple rules match the same task.
  Lower priority number = evaluated first = wins on tie-break.
- Each rule carries a base_confidence value stating how certain the rule author
  is that its patterns imply its task_type.

PRIORITY ORDER (ascending = evaluated first, wins ties):
  1  — VISION          (strongest domain signal; P&ID/image always unambiguous)
  2  — CODING          (explicit code/programming signals)
  3  — CALCULATION     (explicit formula/numerical computation signals)
  4  — EXTRACTION      (structured data pull from documents)
  5  — SUMMARIZATION   (explicit user intent to compress/distil text)
  6  — DOCUMENT_ANALYSIS (engineering report/regulatory document)
  7  — REASONING       (compare/evaluate/analyse/decide — broad reasoning)
  8  — GENERAL         (catch-all; lowest priority, lowest confidence)

CONFIDENCE POLICY:
- base_confidence is set by the rule author based on signal strength.
- Vision signals (P&ID, diagram, image) → 0.92 (very high specificity)
- Coding signals (python, code, script) → 0.90
- Domain-specific calculation signals   → 0.88
- Extraction signals                    → 0.82
- Document analysis signals             → 0.85
- Summarization signals                 → 0.80
- General reasoning signals             → 0.75
- Catch-all / default                   → 0.50 (below fallback threshold)

Rule routing accuracy has NOT been formally benchmarked.
The confidence values represent the rule author's signal-strength estimate only.

EXTENSIBILITY:
- Add new RoutingRule instances to ROUTING_RULES to extend coverage.
- Rules can be disabled at runtime via RouterConfig (Phase 3+).
- Level 1 SemanticRouter and Level 2 ClassifierRouter will consult the same
  taxonomy but replace this rules list with embedding / classifier inference.
"""

import re
from dataclasses import dataclass, field
from typing import FrozenSet, List, Optional, Tuple

try:
    from app.services.router.taxonomy import Capability, ModelRole, TaskType, role_for_task
except ImportError:
    from backend.app.services.router.taxonomy import (
        Capability,
        ModelRole,
        TaskType,
        role_for_task,
    )


# ---------------------------------------------------------------------------
# RoutingRule dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoutingRule:
    """
    Declarative specification of a single routing rule.

    Attributes:
        rule_id:         Unique machine-readable identifier (snake_case).
        task_type:       TaskType this rule maps to when fired.
        patterns:        Set of lowercase keyword/phrase patterns. A rule fires
                         when ANY pattern is found (case-insensitive substring).
        priority:        Evaluation order. Lower = higher precedence. Range: 1–99.
        base_confidence: Certainty score [0.0, 1.0] when rule fires.
        reason_template: Human-readable reason string; use {matched} placeholder
                         for the first matching pattern.
        enabled:         Set to False to disable a rule without deleting it.
    """

    rule_id: str
    task_type: TaskType
    patterns: FrozenSet[str]
    priority: int
    base_confidence: float
    reason_template: str
    enabled: bool = True

    def match(self, text: str) -> Tuple[bool, List[str]]:
        """
        Test whether this rule fires on the given lowercase text.

        Returns:
            (matched: bool, matched_patterns: List[str])
        """
        if not self.enabled:
            return False, []
        text_lower = text.lower()
        hits = [p for p in self.patterns if p in text_lower]
        return bool(hits), hits


# ---------------------------------------------------------------------------
# MRPL-domain routing rule registry
# ---------------------------------------------------------------------------
# Patterns are intentionally concise — substring matching, not regex —
# to remain readable and auditable. Extend by adding to this list.

ROUTING_RULES: List[RoutingRule] = [

    # ── Priority 1: VISION ─────────────────────────────────────────────────
    # Strong domain signal: tasks referencing images, diagrams, or P&IDs
    # require vision model regardless of any other text.
    RoutingRule(
        rule_id="vision_pid_signal",
        task_type=TaskType.VISION,
        patterns=frozenset({
            "p&id", "p and id", "piping diagram", "piping and instrumentation",
            "instrument diagram", "process diagram", "process flow diagram",
            "flow sheet", "flowsheet", "schematic", "diagram", "image",
            "photo", "photograph", "scan", "scanned", "handwritten",
            "instrument tag", "tag number", "identify the tag",
            "visual", "picture", "figure", "plate", "drawing",
            "read the gauge", "gauge reading", "nameplate",
        }),
        priority=1,
        base_confidence=0.92,
        reason_template=(
            "Task contains visual/P&ID signal '{matched}' — "
            "routing to vision model for image understanding."
        ),
    ),

    # ── Priority 2: CODING ─────────────────────────────────────────────────
    RoutingRule(
        rule_id="coding_signal",
        task_type=TaskType.CODING,
        patterns=frozenset({
            "python", "code", "script", "function", "program", "class",
            "module", "implement", "write a", "debugging", "debug",
            "error in code", "fix the code", "unit test", "pytest",
            "csv parser", "parse csv", "parse json", "parse xml",
            "algorithm", "data structure", "api call", "generate code",
            "sql query", "sql", "bash", "shell script", "automation script",
        }),
        priority=2,
        base_confidence=0.90,
        reason_template=(
            "Task contains coding signal '{matched}' — "
            "routing to coder model for code generation."
        ),
    ),

    # ── Priority 3: CALCULATION ────────────────────────────────────────────
    RoutingRule(
        rule_id="calculation_signal",
        task_type=TaskType.CALCULATION,
        patterns=frozenset({
            "calculate", "calculation", "compute", "formula",
            "corrosion rate", "thickness measurement", "wall thickness",
            "remaining life", "service life", "fitness for service",
            "api 570", "api 579", "tmin", "t-min", "allowable stress",
            "pressure rating", "flow rate", "pressure drop",
            "heat transfer", "efficiency", "yield", "mass balance",
            "numerical", "equation", "solve for", "arithmetic",
            "percentage", "per year", "mm/year", "mpy", "mils per year",
        }),
        priority=3,
        base_confidence=0.88,
        reason_template=(
            "Task contains calculation signal '{matched}' — "
            "routing to reasoning model for numerical analysis."
        ),
    ),

    # ── Priority 4: EXTRACTION ─────────────────────────────────────────────
    RoutingRule(
        rule_id="extraction_signal",
        task_type=TaskType.EXTRACTION,
        patterns=frozenset({
            "extract", "extraction", "pull out", "list all", "list the",
            "identify all", "what are the", "find the values",
            "tabulate", "table of", "enumerate", "data from",
            "equipment tag", "tag list", "line list", "instrument list",
            "from the report", "from the document", "from the pdf",
            "from the image", "from the drawing",
        }),
        priority=4,
        base_confidence=0.82,
        reason_template=(
            "Task contains extraction signal '{matched}' — "
            "routing to reasoning model for structured data extraction."
        ),
    ),

    # ── Priority 5: SUMMARIZATION ──────────────────────────────────────────
    # Priority 5: "summarize" is an explicit user intent verb that overrides
    # generic document analysis when both appear in the same task.
    RoutingRule(
        rule_id="summarization_signal",
        task_type=TaskType.SUMMARIZATION,
        patterns=frozenset({
            "summarize", "summarise", "summarization", "summary",
            "brief", "key points", "highlight", "tldr", "tl;dr",
            "condense", "shorten", "recap", "overview",
            "main findings", "executive summary", "abstract",
        }),
        priority=5,
        base_confidence=0.80,
        reason_template=(
            "Task contains summarization signal '{matched}' — "
            "routing to reasoning model for text summarization."
        ),
    ),

    # ── Priority 6: DOCUMENT ANALYSIS ─────────────────────────────────────
    RoutingRule(
        rule_id="document_analysis_signal",
        task_type=TaskType.DOCUMENT_ANALYSIS,
        patterns=frozenset({
            "report", "inspection report", "ndt report", "audit report",
            "technical report", "engineering report", "maintenance report",
            "regulatory", "compliance", "standard", "specification",
            "sop", "procedure", "policy", "manual", "datasheet",
            "analyze this", "analyse this", "review this",
            "what does the", "interpret", "according to", "based on the",
            "pdf", "document", "corrosion inspection", "ndt",
            "ultrasonic", "wall thinning", "pit depth",
            "turnaround", "shutdown", "outage", "overhaul",
            "vendor bid", "procurement", "bid evaluation",
            "crude assay", "blend", "refinery",
        }),
        priority=6,
        base_confidence=0.85,
        reason_template=(
            "Task contains document analysis signal '{matched}' — "
            "routing to reasoning model for engineering document analysis."
        ),
    ),

    # ── Priority 7: REASONING ──────────────────────────────────────────────
    RoutingRule(
        rule_id="reasoning_signal",
        task_type=TaskType.REASONING,
        patterns=frozenset({
            "compare", "comparison", "evaluate", "evaluate the",
            "assess", "assessment", "recommend", "recommendation",
            "decision", "decide", "tradeoff", "trade-off",
            "pros and cons", "advantages", "disadvantages",
            "explain", "why", "justify", "justification",
            "analyze", "analyse", "think through", "step by step",
            "reasoning", "implications", "consequence", "impact",
            "select the best", "which is better", "optimal",
        }),
        priority=7,
        base_confidence=0.75,
        reason_template=(
            "Task contains reasoning signal '{matched}' — "
            "routing to reasoning model for multi-step analysis."
        ),
    ),

    # ── Priority 8: GENERAL (catch-all) ───────────────────────────────────
    # Intentionally kept below the default fallback threshold (0.70) so that
    # truly unknown tasks trigger the fallback path and are explicitly logged.
    RoutingRule(
        rule_id="general_catchall",
        task_type=TaskType.GENERAL,
        patterns=frozenset({
            "hello", "hi", "help", "what can you", "what do you",
            "who are you", "tell me about", "what is",
        }),
        priority=8,
        base_confidence=0.50,
        reason_template=(
            "Task matched general greeting/meta pattern '{matched}' — "
            "routing to general reasoning fallback."
        ),
    ),
]

# Sorted by priority for deterministic evaluation order
ROUTING_RULES_SORTED: List[RoutingRule] = sorted(ROUTING_RULES, key=lambda r: r.priority)
