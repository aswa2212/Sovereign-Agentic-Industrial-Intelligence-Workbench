"""
SIH26117 — Phase 9: Validation Service Package Exports
"""

try:
    from app.services.validation.base import (
        AbstractValidator,
        ValidationOutcome,
        ValidationStage,
        ValidationStatus,
    )
    from app.services.validation.exceptions import (
        CalculationMismatchError,
        EngineeringValidationError,
        ParsingError,
        ProvenanceError,
        SchemaValidationError,
        ValidationError,
    )
    from app.services.validation.models import (
        CorrosionAuditResult,
        CorrosionCalculation,
        InspectionFinding,
        MeasurementUnit,
        RecommendationCode,
        SourceCitation,
        ValidationErrorDetail,
        ValidationResult,
        WallThicknessMeasurement,
    )
    from app.services.validation.parser import parse_model_output
    from app.services.validation.service import StructuredOutputService
except ImportError:
    from backend.app.services.validation.base import (
        AbstractValidator,
        ValidationOutcome,
        ValidationStage,
        ValidationStatus,
    )
    from backend.app.services.validation.exceptions import (
        CalculationMismatchError,
        EngineeringValidationError,
        ParsingError,
        ProvenanceError,
        SchemaValidationError,
        ValidationError,
    )
    from backend.app.services.validation.models import (
        CorrosionAuditResult,
        CorrosionCalculation,
        InspectionFinding,
        MeasurementUnit,
        RecommendationCode,
        SourceCitation,
        ValidationErrorDetail,
        ValidationResult,
        WallThicknessMeasurement,
    )
    from backend.app.services.validation.parser import parse_model_output
    from backend.app.services.validation.service import StructuredOutputService

__all__ = [
    # Base
    "AbstractValidator",
    "ValidationOutcome",
    "ValidationStage",
    "ValidationStatus",
    # Exceptions
    "CalculationMismatchError",
    "EngineeringValidationError",
    "ParsingError",
    "ProvenanceError",
    "SchemaValidationError",
    "ValidationError",
    # Models
    "CorrosionAuditResult",
    "CorrosionCalculation",
    "InspectionFinding",
    "MeasurementUnit",
    "RecommendationCode",
    "SourceCitation",
    "ValidationErrorDetail",
    "ValidationResult",
    "WallThicknessMeasurement",
    # Utilities
    "parse_model_output",
    # Service
    "StructuredOutputService",
]
