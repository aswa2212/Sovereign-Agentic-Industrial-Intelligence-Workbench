"""
SIH26117 — Sandbox Validator Compatibility Layer
Thin compatibility re-export module satisfying docs/implementation_plan.md naming.
Re-exports PythonASTPreScreener and payload validation utilities.
"""

try:
    from app.services.sandbox.validators import (
        FORBIDDEN_CALLS,
        FORBIDDEN_MODULES,
        PythonASTPreScreener,
        validate_tool_payload,
    )
except ImportError:
    from backend.app.services.sandbox.validators import (
        FORBIDDEN_CALLS,
        FORBIDDEN_MODULES,
        PythonASTPreScreener,
        validate_tool_payload,
    )

__all__ = [
    "PythonASTPreScreener",
    "validate_tool_payload",
    "FORBIDDEN_MODULES",
    "FORBIDDEN_CALLS",
]
