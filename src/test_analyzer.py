"""Test-quality analysis over ``test_cases.csv``."""

from __future__ import annotations

import pandas as pd


def failed_test_cases(test_cases: pd.DataFrame) -> pd.DataFrame:
    return test_cases[test_cases["execution_status"] == "FAIL"]


def blocked_test_cases(test_cases: pd.DataFrame) -> pd.DataFrame:
    return test_cases[test_cases["execution_status"] == "BLOCKED"]


def failure_rate_by_module(test_cases: pd.DataFrame) -> pd.DataFrame:
    grouped = test_cases.groupby("test_module").agg(
        total=("test_case_id", "count"),
        failed=("execution_status", lambda s: (s == "FAIL").sum()),
        blocked=("execution_status", lambda s: (s == "BLOCKED").sum()),
    )
    grouped["fail_rate_pct"] = (grouped["failed"] / grouped["total"] * 100).round(1)
    return grouped.sort_values("failed", ascending=False).reset_index()


def automation_gap(test_cases: pd.DataFrame) -> pd.DataFrame:
    """Modules with the most MANUAL/CANDIDATE (i.e. not yet automated)
    test cases — a regression-testing coverage gap indicator."""
    grouped = test_cases.groupby("test_module").agg(
        total=("test_case_id", "count"),
        not_automated=("automation_status", lambda s: (s != "AUTOMATED").sum()),
    )
    grouped["not_automated_pct"] = (grouped["not_automated"] / grouped["total"] * 100).round(1)
    return grouped.sort_values("not_automated", ascending=False).reset_index()
