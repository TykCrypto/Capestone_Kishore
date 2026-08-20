#!/usr/bin/env python3
"""Governance hook: verify data privacy, PII exposure, risk-score
explainability, dataset integrity, audit logging, and responsible-AI
rules. Thin wrapper around src.governance_engine.run_governance_checks —
runs standalone (``python .claude/hooks/governance_check.py``) or as a
PostToolUse hook triggered when files under src/ change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import data_loader, risk_engine  # noqa: E402
from src.governance_engine import append_audit_log, run_governance_checks  # noqa: E402


def _relevant_hook_payload() -> bool:
    """When invoked as a hook, only act if the change touched src/. When
    invoked standalone (no piped hook JSON), always run."""
    if sys.stdin.isatty():
        return True
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return True
    tool_input = payload.get("tool_input", {}) or {}
    target = tool_input.get("file_path", "") or tool_input.get("command", "")
    return "src/" in target or "src\\" in target


def main() -> None:
    if not _relevant_hook_payload():
        sys.exit(0)

    datasets = data_loader.load_all()
    scored = risk_engine.score_transactions(
        datasets["transactions"], datasets["accounts"], datasets["customers"]
    )
    context = {"datasets": datasets, "scored_transactions": scored}
    results = run_governance_checks(context)

    failed = [area for area, status in results.items() if status == "FAIL"]
    for area, status in results.items():
        print(f"{area}: {status}")

    append_audit_log(
        action="governance_check",
        detail=f"results={results}",
    )

    if failed:
        print(f"Governance FAIL in: {', '.join(failed)}", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
