"""
SIH26117 — Phase 9: Structured Output Validation Base Contracts
Defines the abstract base for validators and the validation status enum.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationStatus(str, Enum):
    """
    Lifecycle states for a validation result.

    Hierarchy (severity descending):
      PARSING_ERROR > SCHEMA_ERROR > CALCULATION_MISMATCH > INSUFFICIENT_EVIDENCE > INVALID > VALID
    """
    VALID = "VALID"
    INVALID = "INVALID"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CALCULATION_MISMATCH = "CALCULATION_MISMATCH"
    SCHEMA_ERROR = "SCHEMA_ERROR"
    PARSING_ERROR = "PARSING_ERROR"


class ValidationStage(str, Enum):
    """Identifies which pipeline stage raised an error."""
    PARSING = "parsing"
    SCHEMA = "schema"
    ENGINEERING = "engineering"
    PROVENANCE = "provenance"
    CALCULATION = "calculation"


class AbstractValidator(ABC):
    """
    Abstract interface for all validation layers.
    Dependency direction: caller -> AbstractValidator implementation.
    The validator must never import from Agent or Orchestrator modules.
    """

    @abstractmethod
    def validate(self, payload: Any) -> "ValidationOutcome":
        """Validate payload and return structured ValidationOutcome."""
        ...


class ValidationOutcome:
    """
    Lightweight dataclass-like container returned by AbstractValidator.
    Use models.ValidationResult for the public Pydantic-serialisable surface.
    """

    __slots__ = ("valid", "status", "stage", "errors", "warnings", "data")

    def __init__(
        self,
        *,
        valid: bool,
        status: ValidationStatus,
        stage: Optional[ValidationStage] = None,
        errors: Optional[List[Dict[str, str]]] = None,
        warnings: Optional[List[str]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.valid = valid
        self.status = status
        self.stage = stage
        self.errors = errors or []
        self.warnings = warnings or []
        self.data = data or {}
