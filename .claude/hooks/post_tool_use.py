#!/usr/bin/env python3
"""PostToolUse hook: record execution status, capture errors and files
modified, and update the audit log. Thin wrapper around
src.governance_engine.append_audit_log — no logging logic is duplicated
here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.governance_engine import append_audit_log  # noqa: E402


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = payload.get("tool_name", "unknown_tool")
    tool_input = payload.get("tool_input", {}) or {}
    tool_response = payload.get("tool_response", {}) or {}

    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("command", "")
    status = "error" if tool_response.get("error") else "ok"

    append_audit_log(action=f"post_tool_use:{tool_name}", detail=f"status={status} target={file_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
