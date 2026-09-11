"""
SIH26117 — Sandbox Input Validation & Python AST Pre-Screener
Enforces static code analysis, prevents prohibited module imports, and validates tool payloads.
"""

import ast
import logging
from typing import Any, Dict, Set, Type
from pydantic import BaseModel, ValidationError

try:
    from app.services.sandbox.base import PolicyViolationError, ToolValidationError
except ImportError:
    from backend.app.services.sandbox.base import PolicyViolationError, ToolValidationError

logger = logging.getLogger(__name__)

# Modules strictly forbidden in sandboxed execution
FORBIDDEN_MODULES: Set[str] = {
    "os",
    "subprocess",
    "socket",
    "urllib",
    "urllib3",
    "requests",
    "httpx",
    "http",
    "ftplib",
    "smtplib",
    "poplib",
    "imaplib",
    "telnetlib",
    "pty",
    "shutil",
    "sys",
    "posix",
    "nt",
    "signal",
    "multiprocessing",
    "threading",
    "ctypes",
    "winreg",
}

# Dangerous builtin function calls
FORBIDDEN_CALLS: Set[str] = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "breakpoint",
    "memoryview",
}


class PythonASTPreScreener:
    """
    Static AST analyzer verifying that generated Python snippets contain zero forbidden imports,
    zero shell executions, and zero dynamic code evaluation.
    """

    @classmethod
    def screen_code(cls, source_code: str) -> None:
        """
        Parse and inspect Python AST.
        Raises PolicyViolationError if code attempts prohibited operations.
        """
        if not source_code or not source_code.strip():
            return

        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise PolicyViolationError(f"Syntax error in submitted code: {str(e)}") from e

        for node in ast.walk(tree):
            # 1. Inspect import statements: `import os`, `import socket`
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    if root_pkg in FORBIDDEN_MODULES:
                        raise PolicyViolationError(
                            f"Security violation: Prohibited module '{alias.name}' is forbidden in sandbox."
                        )

            # 2. Inspect from-imports: `from subprocess import Popen`
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_pkg = node.module.split(".")[0]
                    if root_pkg in FORBIDDEN_MODULES:
                        raise PolicyViolationError(
                            f"Security violation: Prohibited module '{node.module}' is forbidden in sandbox."
                        )

            # 3. Inspect dangerous builtin calls: `eval(...)`, `exec(...)`
            elif isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in FORBIDDEN_CALLS:
                    raise PolicyViolationError(
                        f"Security violation: Dynamic evaluation call '{func_name}' is forbidden in sandbox."
                    )


def validate_tool_payload(
    tool_name: str,
    payload: Dict[str, Any],
    schema: Type[BaseModel],
) -> BaseModel:
    """
    Validates input payload against a Pydantic model contract.
    Raises ToolValidationError if data is invalid or malformed.
    """
    try:
        return schema.model_validate(payload)
    except ValidationError as e:
        logger.warning("Tool '%s' input validation failed: %s", tool_name, str(e))
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        raise ToolValidationError(
            f"Input validation error for tool '{tool_name}': {'; '.join(errors)}"
        ) from e
