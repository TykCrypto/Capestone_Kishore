#!/usr/bin/env python3
"""PreToolUse hook: validate input paths, prevent accidental modification of
raw datasets, block obvious secret-file writes, and validate that the
requested operation is allowed before it runs.

Reads the standard Claude Code PreToolUse JSON payload from stdin. To
block, prints the reason to stderr and to stdout (as a structured
decision, for harness versions that read it) and exits 2. To allow,
exits 0 with no output.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROTECTED_DIR_NAMES = {"data"}
PROTECTED_FILES = {PROJECT_ROOT / "governance" / "audit_log.csv"}
SECRET_PATH_PATTERN = re.compile(r"\.env(\.|$)|\.pem$|credentials|secret", re.IGNORECASE)
DESTRUCTIVE_BASH_PATTERN = re.compile(r"\b(rm|mv|truncate|>>?|sed\s+-i)\b")


def _deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(2)


def _resolve(file_path: str) -> Path:
    path = Path(file_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _check_path_write(file_path: str) -> None:
    resolved = _resolve(file_path)
    try:
        relative = resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        return
    if relative.parts and relative.parts[0] in PROTECTED_DIR_NAMES:
        _deny(f"Refusing to modify raw source dataset '{relative}' under data/ — it must stay read-only.")
    if resolved in PROTECTED_FILES:
        _deny(f"Refusing to directly edit '{relative}' — audit log entries must be appended via governance_engine.append_audit_log.")
    if SECRET_PATH_PATTERN.search(str(relative)):
        _deny(f"Refusing to write '{relative}' — path looks like a secret/credential file.")


def _check_bash(command: str) -> None:
    if "data/" in command and DESTRUCTIVE_BASH_PATTERN.search(command):
        _deny(f"Refusing potentially destructive Bash command against data/: {command!r}")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # nothing to validate — allow

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}

    if tool_name in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
        file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if file_path:
            _check_path_write(file_path)
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if command:
            _check_bash(command)

    sys.exit(0)


if __name__ == "__main__":
    main()
