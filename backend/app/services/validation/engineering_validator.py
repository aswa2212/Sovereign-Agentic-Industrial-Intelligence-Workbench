"""
SIH26117 — Phase 9: Deterministic Engineering Validator

Applies business/engineering consistency checks to a schema-validated CorrosionAuditResult.

DESIGN PRINCIPLES:
1. Schema-valid ≠ engineering-valid.
2. Model-generated calculations are INDEPENDENTLY recomputed and compared.
3. Provenance is validated structurally; citations are never fabricated.
4. No compliance claims (API 570, ASME, ASTM, MRPL) unless explicitly in source data.
5. These are deterministic consistency checks, not professional engineering certification.
6. Fails closed: any check failure produces a structured error, never a silent pass.
"""

import logging
from typing import List, Optional, Tuple

try:
    from app.services.validation.base import ValidationStage
    from app.services.validation.exceptions import (
        CalculationMismatchError,
        EngineeringValidationError,
        ProvenanceError,
    )
    from app.services.validation.models import (
        CorrosionAuditResult,
        CorrosionCalculation,
        ValidationErrorDetail,
    )
except ImportError:
    from backend.app.services.validation.base import ValidationStage
    from backend.app.services.validation.exceptions import (
        CalculationMismatchError,
        EngineeringValidationError,
        ProvenanceError,
    )
    from backend.app.services.validation.models import (
        CorrosionAuditResult,
        CorrosionCalculation,
        ValidationErrorDetail,
    )

logger = logging.getLogger(__name__)

# Tolerance for floating-point comparison of independently calculated corrosion rates.
# Two corrosion-rate values within this delta are considered equivalent.
DEFAULT_RATE_TOLERANCE_MM_PER_YEAR: float = 0.001


class EngineeringValidator:
    """
    Deterministic engineering consistency validator.

    Validates a CorrosionAuditResult that has already passed schema validation.
    Returns structured error and warning lists without raising exceptions to callers.
    """

    def __init__(
        self,
        rate_tolerance: float = DEFAULT_RATE_TOLERANCE_MM_PER_YEAR,
        require_citations_when_findings: bool = True,
    ) -> None:
        self.rate_tolerance = rate_tolerance
        self.require_citations_when_findings = require_citations_when_findings

    def validate(
        self, result: CorrosionAuditResult
    ) -> Tuple[List[ValidationErrorDetail], List[str], List[str]]:
        """
        Execute all deterministic engineering checks.

        Returns:
            errors   — list of ValidationErrorDetail (any = invalid)
            warnings — list of str (non-fatal)
            passed   — list of check names that passed
        """
        errors: List[ValidationErrorDetail] = []
        warnings: List[str] = []
        passed: List[str] = []

        # ── Check 1: Equipment identifier present ────────────────────────────
        if result.equipment_id and result.equipment_id.strip():
            passed.append("equipment_id_present")
        else:
            errors.append(ValidationErrorDetail(
                field="equipment_id",
                code="REQUIRED_FIELD_MISSING",
                message="Equipment identifier must be a non-empty string.",
                stage=ValidationStage.ENGINEERING.value,
            ))

        # ── Check 2: Current measurement positivity ──────────────────────────
        if result.current_measurement is not None:
            if result.current_measurement.value_mm <= 0:
                errors.append(ValidationErrorDetail(
                    field="current_measurement.value_mm",
                    code="NON_POSITIVE_THICKNESS",
                    message="Current wall thickness must be strictly positive (> 0 mm).",
                    stage=ValidationStage.ENGINEERING.value,
                ))
            else:
                passed.append("current_measurement_positive")

        # ── Check 3: Initial measurement positivity ──────────────────────────
        if result.initial_measurement is not None:
            if result.initial_measurement.value_mm <= 0:
                errors.append(ValidationErrorDetail(
                    field="initial_measurement.value_mm",
                    code="NON_POSITIVE_THICKNESS",
                    message="Initial wall thickness must be strictly positive (> 0 mm).",
                    stage=ValidationStage.ENGINEERING.value,
                ))
            else:
                passed.append("initial_measurement_positive")

        # ── Check 4: Minimum required thickness ─────────────────────────────
        if result.minimum_required_thickness_mm is not None:
            if result.minimum_required_thickness_mm <= 0:
                errors.append(ValidationErrorDetail(
                    field="minimum_required_thickness_mm",
                    code="NON_POSITIVE_THICKNESS",
                    message="Minimum required thickness must be strictly positive (> 0 mm).",
                    stage=ValidationStage.ENGINEERING.value,
                ))
            elif (
                result.current_measurement is not None
                and result.current_measurement.value_mm < result.minimum_required_thickness_mm
            ):
                # Not invalid — this is a critical finding that should be surfaced in recommendation
                warnings.append(
                    f"Current thickness ({result.current_measurement.value_mm} mm) is below "
                    f"minimum required ({result.minimum_required_thickness_mm} mm). "
                    "Verify recommendation is appropriate."
                )
            else:
                passed.append("minimum_thickness_valid")

        # ── Check 5: Recommendation consistency ──────────────────────────────
        if result.recommendation is not None and result.minimum_required_thickness_mm is not None:
            if (
                result.current_measurement is not None
                and result.current_measurement.value_mm < result.minimum_required_thickness_mm
                and result.recommendation.value == "CONTINUE_SERVICE"
            ):
                errors.append(ValidationErrorDetail(
                    field="recommendation",
                    code="INCONSISTENT_RECOMMENDATION",
                    message=(
                        "Recommendation CONTINUE_SERVICE is inconsistent with current thickness "
                        "being below minimum required. A more conservative recommendation is required."
                    ),
                    stage=ValidationStage.ENGINEERING.value,
                ))
            else:
                passed.append("recommendation_consistent")

        # ── Check 6: Calculation verification ────────────────────────────────
        if result.calculation is not None:
            calc_errors, calc_warnings, calc_passed = self._validate_calculation(result.calculation)
            errors.extend(calc_errors)
            warnings.extend(calc_warnings)
            passed.extend(calc_passed)

        # ── Check 7: Provenance when findings are present ────────────────────
        if self.require_citations_when_findings and result.findings:
            has_any_citation = bool(result.citations) or any(
                f.supporting_citation is not None for f in result.findings
            )
            if has_any_citation:
                passed.append("provenance_present_for_findings")
            else:
                errors.append(ValidationErrorDetail(
                    field="citations",
                    code="INSUFFICIENT_PROVENANCE",
                    message=(
                        "Findings are present but no source citations were supplied. "
                        "At least one SourceCitation is required to ground findings in evidence."
                    ),
                    stage=ValidationStage.PROVENANCE.value,
                ))

        # ── Check 8: Citation field integrity ────────────────────────────────
        for idx, cit in enumerate(result.citations):
            if not cit.source_document or not cit.source_document.strip():
                errors.append(ValidationErrorDetail(
                    field=f"citations[{idx}].source_document",
                    code="EMPTY_CITATION_SOURCE",
                    message="Citation source_document must be a non-empty string.",
                    stage=ValidationStage.PROVENANCE.value,
                ))
            else:
                passed.append(f"citation_{idx}_source_document_valid")

        return errors, warnings, passed

    def _validate_calculation(
        self, calc: CorrosionCalculation
    ) -> Tuple[List[ValidationErrorDetail], List[str], List[str]]:
        """
        Independently verify corrosion-rate and remaining-life calculations.

        Formula:
            corrosion_rate = (initial_thickness - current_thickness) / inspection_interval
            remaining_life = (current_thickness - minimum_required) / corrosion_rate

        These are deterministic formulas documented here and in docs/architecture/phase9_validation.md.
        No compliance standard (API 570, ASME, etc.) is implied.
        """
        errors: List[ValidationErrorDetail] = []
        warnings: List[str] = []
        passed: List[str] = []

        # ── 6a: Corrosion rate sign ──────────────────────────────────────────
        if calc.corrosion_rate_mm_per_year < 0:
            errors.append(ValidationErrorDetail(
                field="calculation.corrosion_rate_mm_per_year",
                code="NEGATIVE_CORROSION_RATE",
                message="Corrosion rate cannot be negative.",
                stage=ValidationStage.CALCULATION.value,
            ))
            return errors, warnings, passed  # Cannot verify further

        # ── 6b: Independent rate computation ────────────────────────────────
        if calc.inspection_interval_years > 0:
            metal_loss = calc.initial_thickness_mm - calc.current_thickness_mm
            if metal_loss < 0:
                warnings.append(
                    f"Metal loss is negative ({metal_loss:.4f} mm), indicating thickness increased "
                    "between measurements. Verify measurement accuracy."
                )
            independently_computed_rate = metal_loss / calc.inspection_interval_years
            delta = abs(independently_computed_rate - calc.corrosion_rate_mm_per_year)

            if delta > self.rate_tolerance:
                errors.append(ValidationErrorDetail(
                    field="calculation.corrosion_rate_mm_per_year",
                    code="CALCULATION_MISMATCH",
                    message=(
                        f"Claimed corrosion rate ({calc.corrosion_rate_mm_per_year:.6f} mm/yr) "
                        f"differs from independently computed value "
                        f"({independently_computed_rate:.6f} mm/yr) by {delta:.6f} mm/yr, "
                        f"which exceeds the tolerance of {self.rate_tolerance} mm/yr. "
                        "Formula: (initial_thickness - current_thickness) / inspection_interval."
                    ),
                    stage=ValidationStage.CALCULATION.value,
                ))
            else:
                passed.append("corrosion_rate_calculation_verified")

        # ── 6c: Remaining life verification ──────────────────────────────────
        if (
            calc.remaining_life_years is not None
            and calc.minimum_required_mm is not None
            and calc.corrosion_rate_mm_per_year > 0
        ):
            remaining_thickness = calc.current_thickness_mm - calc.minimum_required_mm
            independently_computed_life = remaining_thickness / calc.corrosion_rate_mm_per_year
            life_delta = abs(independently_computed_life - calc.remaining_life_years)
            # Allow 1% relative tolerance for remaining-life (longer value, more round-off)
            life_tolerance = max(0.1, abs(independently_computed_life) * 0.01)

            if life_delta > life_tolerance:
                errors.append(ValidationErrorDetail(
                    field="calculation.remaining_life_years",
                    code="CALCULATION_MISMATCH",
                    message=(
                        f"Claimed remaining life ({calc.remaining_life_years:.4f} yr) "
                        f"differs from independently computed value "
                        f"({independently_computed_life:.4f} yr) by {life_delta:.4f} yr "
                        f"(tolerance {life_tolerance:.4f} yr). "
                        "Formula: (current_thickness - minimum_required) / corrosion_rate."
                    ),
                    stage=ValidationStage.CALCULATION.value,
                ))
            else:
                passed.append("remaining_life_calculation_verified")
        elif calc.remaining_life_years is not None and calc.corrosion_rate_mm_per_year == 0:
            warnings.append(
                "Remaining life is supplied but corrosion_rate_mm_per_year == 0. "
                "Cannot independently verify remaining life when rate is zero."
            )

        return errors, warnings, passed
