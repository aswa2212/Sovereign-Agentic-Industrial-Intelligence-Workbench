"""
SIH26117 — Task Router Abstract Interface
Defines the TaskRouter ABC and extension-point stubs for Level 1 (Semantic)
and Level 2 (Classifier) routers.

ROUTER HIERARCHY:
  TaskRouter (ABC)
    ├── RuleRouter       — Level 0: deterministic keyword rules (IMPLEMENTED)
    ├── SemanticRouter   — Level 1: embedding cosine similarity (EXTENSION POINT)
    ├── ClassifierRouter — Level 2: local ML classifier (EXTENSION POINT)
    └── HybridRouter     — Cascade: rules → semantic → classifier → fallback (FUTURE)

The application depends only on the TaskRouter ABC. Swapping implementations
requires no changes to API endpoints or the Agent Orchestrator.

LEVEL 1 (SemanticRouter) — NOT IMPLEMENTED IN PHASE 3:
- Embeds the task prompt against pre-computed category centroids.
- Requires nomic-embed-text or bge-base-en-v1.5 (configured in model_tiers.yaml).
- Returns NOT_IMPLEMENTED_METHOD_ERROR until Phase 7+ embedding infrastructure exists.

LEVEL 2 (ClassifierRouter) — NOT IMPLEMENTED IN PHASE 3:
- Uses a locally-loaded DeBERTa or 1.5B classifier fine-tuned on MRPL prompts.
- Training/evaluation in Google Colab; the application loads the serialised model.
- Returns NOT_IMPLEMENTED_METHOD_ERROR until a trained model is available.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional

try:
    from app.services.router.decision import RoutingDecision
except ImportError:
    from backend.app.services.router.decision import RoutingDecision


# ---------------------------------------------------------------------------
# Abstract Base
# ---------------------------------------------------------------------------

class TaskRouter(ABC):
    """
    Abstract interface for all task routing implementations.

    Concrete implementations must implement only `route()`. All other
    method signatures define the expected extension points.

    Contract:
    - route() MUST NOT make network calls.
    - route() MUST NOT call Ollama or any inference backend directly.
    - route() MUST NOT load or unload models.
    - route() MUST return a fully populated RoutingDecision.
    - route() MUST be synchronous (no async) to keep routing latency near-zero.
      If a subclass (e.g. SemanticRouter) needs I/O, it should resolve it
      at initialization time, not inside route().
    """

    @abstractmethod
    def route(
        self,
        task: str,
        context: Optional[Dict] = None,
        request_id: Optional[str] = None,
    ) -> RoutingDecision:
        """
        Classify a task and return a routing decision.

        Args:
            task:       Raw user task text.
            context:    Optional additional context (e.g. file_ids, mime_type).
            request_id: Caller-supplied correlation ID for audit logging.

        Returns:
            A fully populated, immutable RoutingDecision.
        """
        pass

    def is_available(self) -> bool:
        """
        Returns True if this router implementation is ready to classify tasks.
        Subclasses that require external resources should override this.
        """
        return True


# ---------------------------------------------------------------------------
# Level 1 — Semantic Router (Extension Point — NOT IMPLEMENTED)
# ---------------------------------------------------------------------------

class SemanticRouter(TaskRouter):
    """
    Level 1 routing via embedding cosine similarity.

    IMPLEMENTATION STATUS: NOT IMPLEMENTED IN PHASE 3.

    When implemented:
    - Embeds the task prompt with nomic-embed-text (CPU) or bge-base-en-v1.5.
    - Computes cosine similarity against pre-computed MRPL domain centroids.
    - Returns RoutingDecision with routing_method='semantic'.

    To activate:
    1. Generate category centroid embeddings (offline, store as .npy files).
    2. Implement _embed() using the embedding model from ModelManager.
    3. Implement _cosine_match() against loaded centroid library.
    4. Return routing_method='semantic' in the RoutingDecision.
    """

    def route(
        self,
        task: str,
        context: Optional[Dict] = None,
        request_id: Optional[str] = None,
    ) -> RoutingDecision:
        raise NotImplementedError(
            "SemanticRouter is not yet implemented. "
            "Use RuleRouter (Level 0) for Phase 3 routing. "
            "Level 1 semantic routing will be implemented in Phase 7+ "
            "once the RAG and embedding infrastructure is established."
        )

    def is_available(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Level 2 — Classifier Router (Extension Point — NOT IMPLEMENTED)
# ---------------------------------------------------------------------------

class ClassifierRouter(TaskRouter):
    """
    Level 2 routing via a locally-loaded fine-tuned text classifier.

    IMPLEMENTATION STATUS: NOT IMPLEMENTED IN PHASE 3.

    When implemented:
    - Loads a serialised DeBERTa-v3-small or 1.5B classifier from disk.
    - The classifier was trained on synthetic MRPL prompt data (Google Colab).
    - Returns RoutingDecision with routing_method='classifier'.
    - The model path is resolved from Settings (no hardcoded paths).

    To activate:
    1. Complete classifier training in Google Colab.
    2. Export model to ONNX or TorchScript.
    3. Implement model loading in __init__ from settings.model_classifier_path.
    4. Implement _classify() wrapping the forward pass.
    """

    def route(
        self,
        task: str,
        context: Optional[Dict] = None,
        request_id: Optional[str] = None,
    ) -> RoutingDecision:
        raise NotImplementedError(
            "ClassifierRouter is not yet implemented. "
            "Training the classifier is a separate offline experiment (Google Colab). "
            "Use RuleRouter (Level 0) for Phase 3 routing."
        )

    def is_available(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Hybrid Router Scaffold (Extension Point — FUTURE)
# ---------------------------------------------------------------------------

class HybridRouter(TaskRouter):
    """
    Cascade router: attempts Level 0 → Level 1 → Level 2 → fallback.

    IMPLEMENTATION STATUS: SCAFFOLD ONLY. Instantiation requires at minimum
    a RuleRouter. Semantic and classifier routers are optional.

    When the hierarchy is complete:
    1. Rule router runs first (zero latency, deterministic).
    2. If confidence < threshold, SemanticRouter refines the decision.
    3. If SemanticRouter unavailable, ClassifierRouter is tried.
    4. If all fail, RuleRouter's fallback decision is used.
    """

    def __init__(
        self,
        rule_router: TaskRouter,
        semantic_router: Optional[TaskRouter] = None,
        classifier_router: Optional[TaskRouter] = None,
    ) -> None:
        self._rule = rule_router
        self._semantic = semantic_router
        self._classifier = classifier_router

    def route(
        self,
        task: str,
        context: Optional[Dict] = None,
        request_id: Optional[str] = None,
    ) -> RoutingDecision:
        """
        Cascade routing:
        1. Try RuleRouter.
        2. If low confidence and SemanticRouter available, try semantic.
        3. If still low confidence and ClassifierRouter available, try classifier.
        4. Return best available decision.
        """
        decision = self._rule.route(task, context, request_id)

        # Attempt semantic refinement if confidence is low
        if (
            decision.fallback_used
            and self._semantic is not None
            and self._semantic.is_available()
        ):
            try:
                decision = self._semantic.route(task, context, request_id)
            except NotImplementedError:
                pass  # Semantic not yet implemented; keep rule decision

        # Attempt classifier refinement
        if (
            decision.fallback_used
            and self._classifier is not None
            and self._classifier.is_available()
        ):
            try:
                decision = self._classifier.route(task, context, request_id)
            except NotImplementedError:
                pass  # Classifier not yet implemented; keep best available

        return decision
