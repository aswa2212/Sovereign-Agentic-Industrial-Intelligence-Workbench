"""
SIH26117 — Standalone Subprocess Runner Entry Point
Invoked by SubprocessSandboxExecutor in an isolated process with scrubbed environment.
Reads input payload from stdin and outputs structured JSON to stdout.
"""

import json
import sys

try:
    from app.services.sandbox.tools import ToolWhitelistRegistry
except ImportError:
    from backend.app.services.sandbox.tools import ToolWhitelistRegistry


def main() -> None:
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python -m app.services.sandbox.runner <tool_name>\n")
        sys.exit(1)

    tool_name = sys.argv[1]
    registry = ToolWhitelistRegistry()

    # Read payload from stdin
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input) if raw_input.strip() else {}
    except Exception as e:
        sys.stderr.write(f"Malformed JSON input: {str(e)}\n")
        sys.exit(2)

    try:
        tool = registry.get_tool(tool_name)
        result = tool.execute(payload)
        sys.stdout.write(json.dumps(result))
        sys.stdout.flush()
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"Execution failure: {str(e)}\n")
        sys.exit(3)


if __name__ == "__main__":
    main()
