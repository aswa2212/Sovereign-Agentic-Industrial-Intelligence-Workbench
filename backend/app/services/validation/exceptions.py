"""
SIH26117 — Phase 9: Structured Output Validation Exceptions
Defines the exception hierarchy for parsing, schema, and engineering validation failures.
"""


class ValidationError(Exception):
    """Base class for all Phase 9 validation errors."""


class ParsingError(ValidationError):
    """Raised when model output cannot be parsed into a structured form."""


class SchemaValidationError(ValidationError):
    """Raised when a parsed payload fails Pydantic schema validation."""


class EngineeringValidationError(ValidationError):
    """Raised when business/engineering consistency checks fail."""


class ProvenanceError(ValidationError):
    """Raised when citation or source provenance is missing or invalid."""


class CalculationMismatchError(EngineeringValidationError):
    """
    Raised when an independently computed value does not match the
    model-supplied calculation result within the accepted tolerance.
    """
