#!/usr/bin/env python3
"""Evaluation hook: whenever analytical logic under src/ changes, run the
test suite, compare detectors against ground truth, calculate evaluation
metrics, and record pass/fail. Thin wrapper around
evaluation.evaluation_metrics.evaluate() and pytest — no metric logic is
duplicated here. Runs standalone or as a PostToolUse hook.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.governance_engine import append_audit_log  # noqa: E402


def _relevant_hook_payload() -> bool:
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

    from evaluation.evaluation_metrics import evaluate  # imported after sys.path setup

    metrics = evaluate()  # runs pytest internally and records the pass rate
    test_pass_rate = metrics.get("test_pass_rate_pct", 0.0)

    for key, value in metrics.items():
        print(f"{key}: {value}")

    append_audit_log(
        action="evaluation_check",
        detail=f"test_pass_rate_pct={test_pass_rate} accuracy={metrics.get('accuracy_pct')} f1={metrics.get('f1_pct')}",
    )

    if test_pass_rate < 90:
        print(f"Evaluation check FAIL: test_pass_rate_pct={test_pass_rate} < 90", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
