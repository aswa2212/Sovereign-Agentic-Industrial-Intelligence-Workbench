"""
SIH26117 — Phase 13: End-to-End System Integration Exceptions

Defines domain exceptions for the full-system integration pipeline.
Ensures that failures at any stage (ingestion, routing, vision, agent,
validation, deliverables, audit) are captured with structured context.
"""


class IntegrationError(Exception):
    """Base exception for all Phase 13 integration failures."""

    def __init__(self, message: str, stage: str = "general", details: dict = None) -> None:
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.details = details or {}


class DocumentIngestionStageError(IntegrationError):
    """Raised when document ingestion or parsing fails during the workflow."""

    def __init__(self, message: str, details: dict = None) -> None:
        super().__init__(message, stage="ingestion", details=details)


class ModelRoutingStageError(IntegrationError):
    """Raised when task routing or model allocation fails."""

    def __init__(self, message: str, details: dict = None) -> None:
        super().__init__(message, stage="routing", details=details)


class AgentExecutionStageError(IntegrationError):
    """Raised when agent state machine or tool execution fails."""

    def __init__(self, message: str, details: dict = None) -> None:
        super().__init__(message, stage="agent", details=details)


class ValidationGateError(IntegrationError):
    """
    Raised when engineering validation fails.
    Enforces the fail-closed gate that prevents unvalidated deliverable generation.
    """

    def __init__(self, message: str, validation_errors: list = None, details: dict = None) -> None:
        d = details or {}
        if validation_errors:
            d["validation_errors"] = validation_errors
        super().__init__(message, stage="validation", details=d)
        self.validation_errors = validation_errors or []


class DeliverableStageError(IntegrationError):
    """Raised when office deliverable generation fails."""

    def __init__(self, message: str, details: dict = None) -> None:
        super().__init__(message, stage="deliverables", details=details)


class WorkflowTimeoutError(IntegrationError):
    """Raised when the workflow execution exceeds its configured global timeout."""

    def __init__(self, message: str, details: dict = None) -> None:
        super().__init__(message, stage="timeout", details=details)
