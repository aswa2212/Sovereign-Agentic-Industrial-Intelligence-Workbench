"""
SIH26117 — Phase 9: Safe Model Output Parser

Parses structured model/agent output into a CorrosionAuditResult.

SECURITY INVARIANTS:
- Never uses eval(), exec(), or compile().
- Never treats model output as trusted Python code.
- Safely handles optional Markdown code fences (deterministic stripping only).
- Rejects malformed JSON with structured ParsingError.
- Rejects unexpected structure (delegated to schema validator).
"""

import json
import logging
import re
from typing import Any, Dict, Union

try:
    from app.services.validation.exceptions import ParsingError
except ImportError:
    from backend.app.services.validation.exceptions import ParsingError

logger = logging.getLogger(__name__)

# Matches a single ```json ... ``` or ``` ... ``` Markdown code fence.
# Only the first fence block is extracted; everything else is rejected.
_CODE_FENCE_RE = re.compile(
    r"^```(?:json)?\s*\n(.*?)\n```\s*$",
    re.DOTALL | re.IGNORECASE,
)


def _strip_code_fence(text: str) -> str:
    """
    Deterministically extract JSON from a Markdown code fence if present.

    Only a single fence surrounding the entire content is supported.
    Mixed fences or fences embedded in prose are rejected.
    This never interprets the fenced content as anything other than text.
    """
    stripped = text.strip()
    match = _CODE_FENCE_RE.match(stripped)
    if match:
        return match.group(1).strip()
    return stripped


def parse_model_output(
    raw: Union[str, bytes, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Parse raw model/agent output into a plain Python dict for schema validation.

    Accepted input types:
    - dict / Pydantic-compatible mapping: returned directly after key-type check.
    - str / bytes: parsed as JSON (with optional Markdown code-fence stripping).

    Raises ParsingError on all failure paths.
    Never raises bare exceptions that expose internal stack traces.
    Never executes content.
    """
    # Already a dict — accept directly after basic sanity check
    if isinstance(raw, dict):
        if not all(isinstance(k, str) for k in raw.keys()):
            raise ParsingError("Payload dict contains non-string keys; rejecting as malformed.")
        return raw

    # Bytes -> str
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ParsingError(f"Cannot decode byte payload as UTF-8: {e}") from e

    if not isinstance(raw, str):
        raise ParsingError(
            f"Unsupported payload type '{type(raw).__name__}'. "
            "Expected str, bytes, or dict."
        )

    if not raw.strip():
        raise ParsingError("Model output is empty; cannot parse structured result.")

    # Optionally strip a single Markdown code fence
    candidate = _strip_code_fence(raw)

    # Parse JSON — no eval, no exec
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ParsingError(
            f"Model output is not valid JSON (position {e.pos}): {e.msg}"
        ) from e

    if not isinstance(parsed, dict):
        raise ParsingError(
            f"Expected a JSON object at the top level, got {type(parsed).__name__}."
        )

    if not all(isinstance(k, str) for k in parsed.keys()):
        raise ParsingError("Parsed JSON object contains non-string keys; rejecting as malformed.")

    logger.debug("parse_model_output: successfully parsed %d top-level keys", len(parsed))
    return parsed
