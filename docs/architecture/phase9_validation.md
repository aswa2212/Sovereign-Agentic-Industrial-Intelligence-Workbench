# Phase 9: Structured Output & Validation Architecture

**SIH26117 — Sovereign On-Premise Agentic AI Workbench**

---

## Overview

Phase 9 implements the Structured Output & Validation layer — a deterministic,
LLM-independent pipeline that ensures model/agent outputs are never treated as
trusted free-form text.

```
Local Model / Agent
        ↓
Structured Output (CorrosionAuditResult)
        ↓
Pydantic Schema Validation
        ↓
Deterministic Engineering Validation
        ↓
Validated Result (ValidationResult)
        ↓
Phase 10 Deliverable Generation
```

---

## Critical Design Invariants

> **Schema-valid ≠ engineering-valid.**
> A payload that passes Pydantic validation may still fail deterministic engineering checks.

> **Model-generated calculations are independently validated.**
> The engineering validator recomputes corrosion rate and remaining life independently
> and compares against claimed values within an explicit, documented tolerance.

> **Fails closed.**
> Any pipeline stage failure produces a structured `INVALID` result.
> Unknown model output never silently becomes a trusted engineering fact.

> **No fabricated citations.**
> The validator never injects or invents source citations.
> Provenance is preserved verbatim from Phase 6 RAG retrieval.

---

## Pipeline Stages

### Stage 1: Parser (`parser.py`)

Accepts:
- `dict` — returned directly after key-type check
- `str` — parsed as JSON with optional Markdown code-fence stripping
- `bytes` — decoded UTF-8 then parsed as JSON

Security invariants:
- **Never calls `eval()`, `exec()`, or `compile()`**
- Never interprets model output as Python
- Markdown code-fence handling is deterministic regex extraction only
- Non-string keys rejected
- Empty input rejected
- Top-level JSON array or scalar rejected

### Stage 2: Schema Validator (`schema_validator.py`)

Validates a parsed dict against `CorrosionAuditResult` (Pydantic model with `extra="forbid"`).

Distinguishes:
| Code | Meaning |
|------|---------|
| `REQUIRED_FIELD_MISSING` | Required field absent |
| `INVALID_TYPE` | Wrong field type |
| `UNEXPECTED_FIELD` | Extra field not in schema |
| `INVALID_ENUM_VALUE` | Enum field has invalid value |
| `VALUE_TOO_SMALL` / `VALUE_TOO_LARGE` | Numeric bounds violated |

Internal Pydantic stack traces are **never** surfaced to callers.

### Stage 3: Engineering Validator (`engineering_validator.py`)

Deterministic business consistency checks applied to a schema-validated `CorrosionAuditResult`.

Checks performed:

| Check | Error Code | Description |
|-------|-----------|-------------|
| Equipment ID present | `REQUIRED_FIELD_MISSING` | `equipment_id` must be non-empty after strip |
| Current measurement positive | `NON_POSITIVE_THICKNESS` | `value_mm > 0` |
| Initial measurement positive | `NON_POSITIVE_THICKNESS` | `value_mm > 0` |
| Minimum thickness valid | `NON_POSITIVE_THICKNESS` | `minimum_required > 0` |
| Recommendation consistent | `INCONSISTENT_RECOMMENDATION` | `CONTINUE_SERVICE` invalid when below minimum |
| Corrosion rate sign | `NEGATIVE_CORROSION_RATE` | Rate must be ≥ 0 |
| **Corrosion rate independent calculation** | `CALCULATION_MISMATCH` | See formula below |
| **Remaining life independent calculation** | `CALCULATION_MISMATCH` | See formula below |
| Provenance when findings present | `INSUFFICIENT_PROVENANCE` | Citations required when findings exist |
| Citation source document | `EMPTY_CITATION_SOURCE` | `source_document` must be non-empty |

---

## Calculation Verification Formulas

These formulas are implemented deterministically in `engineering_validator.py`.
**No compliance standard is implied** (not API 570, ASME, ASTM, MRPL, or any other).
These are internal consistency checks only.

### Corrosion Rate Verification

```
independently_computed_rate = (initial_thickness_mm - current_thickness_mm) / inspection_interval_years
```

The claimed `corrosion_rate_mm_per_year` must satisfy:

```
|claimed_rate - independently_computed_rate| ≤ tolerance (default: 0.001 mm/yr)
```

### Remaining Life Verification

```
independently_computed_life = (current_thickness_mm - minimum_required_mm) / corrosion_rate_mm_per_year
```

The claimed `remaining_life_years` must satisfy:

```
|claimed_life - independently_computed_life| ≤ max(0.1, |independently_computed_life| × 0.01)
```

---

## Validation Status Codes

| Status | Meaning |
|--------|---------|
| `VALID` | All pipeline stages passed |
| `INVALID` | Engineering or recommendation check failed |
| `INSUFFICIENT_EVIDENCE` | Missing required source provenance |
| `CALCULATION_MISMATCH` | Independently computed value differs beyond tolerance |
| `SCHEMA_ERROR` | Pydantic model validation failed |
| `PARSING_ERROR` | JSON parsing or structural rejection |

---

## Provenance Handling

Citations are preserved verbatim from Phase 6 RAG retrieval:

```python
class SourceCitation(BaseModel):
    source_document: str       # Preserved exactly as received
    page_number: Optional[int]
    chunk_id: Optional[str]
    content_sha256: Optional[str]  # Tamper-evident hash preserved
    similarity_score: Optional[float]
    excerpt: Optional[str]
```

**The validation layer never fabricates, modifies, or removes citations.**

If citations are required (findings present) but absent, the result status is
`INSUFFICIENT_EVIDENCE` — not silently treated as valid.

No source file path (`SOP-MRPL-PIP-001.pdf`, page 3, etc.) is hardcoded in
business logic. The validator operates on dynamically supplied provenance.

---

## Service Boundary

```
StructuredOutputService
    ↓ parse_model_output()       — Stage 1: Parser
    ↓ validate_schema()          — Stage 2: Pydantic
    ↓ EngineeringValidator()     — Stage 3: Business rules + calculation verification
    → ValidationResult
```

Dependency direction:
```
Agent (Phase 7) → StructuredOutputService
                        ↑
              (never the reverse)
```

The `StructuredOutputService` can be called independently of the Agent.

---

## Agent Integration

The Phase 7 `AgentStateMachineOrchestrator` is extended **additively**:

1. `StructuredOutputService` is injected as an optional constructor parameter.
2. In the `FINALIZE` state, when calculation data is present in `final_result`,
   the service validates the calculation payload and adds a `structured_validation`
   key to the result.
3. Failures in the structured output service do **not** crash the orchestrator —
   they are recorded as a `structured_validation.valid=False` warning.
4. The existing 11-state machine, state transitions, timeouts, and `Validator`
   class are **completely unchanged**.

---

## API Endpoint

```
POST /api/v1/validation/validate
```

### Request Body

```json
{
  "payload": { ... },              // Required: CorrosionAuditResult-compatible dict
  "rate_tolerance": 0.001,         // Optional: mm/yr tolerance override
  "require_citations": true        // Optional: citation enforcement toggle
}
```

### Response Body

Always HTTP 200 (except 422 for malformed request body or 500 for internal errors).

```json
{
  "valid": true,
  "status": "VALID",
  "validated_data": { ... },       // Only populated when valid=true
  "errors": [],
  "warnings": [],
  "validation_checks": [...],
  "checks_passed": [...],
  "checks_failed": [],
  "calculation_tolerance_mm_per_year": 0.001
}
```

No internal stack traces are ever included in the response.

---

## Security

- No external network calls
- No model inference triggered
- No `eval()`, `exec()`, or `compile()` used anywhere in the pipeline
- Internal exceptions caught and classified — never raw tracebacks in API responses
- Unknown fields in structured output are rejected (Pydantic `extra="forbid"`)
- Markdown code-fence content treated as text only — never interpreted as code

---

## Failure Behavior

The validation pipeline **fails closed** at every stage:

| Scenario | Behavior |
|---------|---------|
| Empty input | `PARSING_ERROR` |
| Malformed JSON | `PARSING_ERROR` |
| Unknown extra field | `SCHEMA_ERROR` |
| Missing required field | `SCHEMA_ERROR` |
| Negative corrosion rate | `INVALID` |
| Calculation mismatch | `CALCULATION_MISMATCH` |
| Missing citations with findings | `INSUFFICIENT_EVIDENCE` |
| CONTINUE_SERVICE below minimum | `INVALID` |
| Internal exception | Structured error, no traceback |

---

## Phase 10 Boundary

Phase 9 produces a `ValidationResult` containing:
- `valid_data: CorrosionAuditResult` — the fully validated structured result
- `citations: List[SourceCitation]` — provenance-preserving citation list
- `validation_checks` — audit trail of all checks run

Phase 10 (Deliverable Generation) consumes `ValidationResult.validated_data` to
generate DOCX/XLSX/PPTX deliverables. Phase 9 does **not** generate any documents.

---

## Known Limitations

1. **Corrosion rate formula is linear.** The validator uses a linear uniform-rate
   assumption. Non-uniform or accelerating corrosion is not modelled.

2. **No regulatory compliance.** Checks are deterministic consistency rules only.
   No claim of API 570, ASME B31.3, ASTM, or MRPL policy compliance is made.

3. **Equipment-specific tolerances not supported.** The calculation tolerance
   is a single global parameter; per-equipment tolerance profiles are Phase 10+ scope.

4. **Validation is synchronous.** The `StructuredOutputService.validate()` method
   is synchronous. For async agent integration it is called in a try/except block
   without `await`.

---

## Tests

86 tests in `backend/tests/test_validation.py`:

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestParser` | 16 | JSON, bytes, code-fence, empty, security |
| `TestSchemaValidator` | 13 | Valid, missing, wrong types, enums, ranges |
| `TestEngineeringValidator` | 14 | Thickness, rate, calculation, provenance |
| `TestProvenance` | 4 | Field preservation, no fabrication |
| `TestStructuredOutputService` | 13 | Full pipeline, all status codes |
| `TestValidationAPI` | 8 | HTTP 200/422, no traceback |
| `TestAgentIntegration` | 4 | Import, injection, states unchanged |
| `TestNetworkSovereignty` | 2 | Socket intercept, urllib intercept |
| `TestPhase18Regression` | 10 | Phase 1–8 modules importable |
