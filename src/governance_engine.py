"""Privacy masking, governance checks, and audit logging.

Every check in ``run_governance_checks`` is computed from a real
condition in the data or repo — none is a hard-coded "PASS" — so the
Governance dashboard can never silently drift from reality. See
``governance/governance_rules.md`` for what each area means in policy
terms.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIT_LOG_PATH = PROJECT_ROOT / "governance" / "audit_log.csv"
EVALUATION_REPORT_PATH = PROJECT_ROOT / "evaluation" / "evaluation_report.csv"
AUDIT_LOG_HEADER = ["timestamp", "action", "detail"]

PII_COLUMNS = ("customer_name", "ip_address")


def mask_pii(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with known PII columns redacted for display.
    Never mutates the original — callers keep the raw frame for
    computation and only mask what reaches the UI."""
    masked = df.copy()
    if "customer_name" in masked.columns:
        masked["customer_name"] = masked["customer_name"].apply(
            lambda name: f"{str(name)[0]}{'*' * max(len(str(name)) - 1, 3)}" if pd.notna(name) else name
        )
    if "ip_address" in masked.columns:
        masked["ip_address"] = masked["ip_address"].apply(
            lambda ip: ".".join(str(ip).split(".")[:2] + ["xxx", "xxx"]) if pd.notna(ip) else ip
        )
    return masked


def append_audit_log(action: str, detail: str) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_new = not AUDIT_LOG_PATH.exists()
    with AUDIT_LOG_PATH.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(AUDIT_LOG_HEADER)
        writer.writerow([datetime.now().isoformat(timespec="seconds"), action, detail])


def _check_data_privacy(customers: pd.DataFrame) -> str:
    sample = customers[customers["customer_name"].notna()].head(50)
    if sample.empty:
        return "PASS"
    masked = mask_pii(sample)
    fully_redacted = (masked["customer_name"] != sample["customer_name"]).all()
    return "PASS" if fully_redacted else "FAIL"


def _check_data_integrity(datasets: dict[str, pd.DataFrame]) -> str:
    key_columns = {
        "customers": "customer_id",
        "accounts": "account_id",
        "transactions": "transaction_id",
        "incidents": "incident_id",
    }
    for name, key in key_columns.items():
        if datasets[name][key].isna().any():
            return "FAIL"
    return "PASS"


def _check_explainability(scored_transactions: pd.DataFrame) -> str:
    high_risk = scored_transactions[scored_transactions["risk_level"] == "HIGH"]
    if high_risk.empty:
        return "PASS"
    has_reasons = high_risk["risk_reasons"].apply(lambda r: len(r) > 0)
    return "PASS" if has_reasons.all() else "FAIL"


def _check_bias(scored_transactions: pd.DataFrame, customers: pd.DataFrame, threshold: float = 40.0) -> str:
    merged = scored_transactions.merge(
        customers[["customer_id", "customer_segment"]], on="customer_id", how="left"
    )
    by_segment = merged.groupby("customer_segment")["risk_score"].mean()
    if len(by_segment) < 2:
        return "PASS"
    spread = by_segment.max() - by_segment.min()
    return "PASS" if spread <= threshold else "FAIL"


def _check_security() -> str:
    return "PASS" if (PROJECT_ROOT / ".claude" / "hooks" / "pre_tool_use.py").exists() else "FAIL"


def _check_auditability() -> str:
    return "PASS" if AUDIT_LOG_PATH.exists() else "FAIL"


def _check_human_oversight(scored_transactions: pd.DataFrame) -> str:
    decision_columns = {"final_decision", "approved", "declined"}
    return "PASS" if not decision_columns & set(scored_transactions.columns) else "FAIL"


def _check_reliability(min_pass_rate_pct: float = 90.0) -> str:
    if not EVALUATION_REPORT_PATH.exists():
        return "NOT_RUN"
    report = pd.read_csv(EVALUATION_REPORT_PATH)
    row = report[report["metric"] == "test_pass_rate_pct"]
    if row.empty:
        return "NOT_RUN"
    return "PASS" if float(row.iloc[0]["value"]) >= min_pass_rate_pct else "FAIL"


def _check_traceability(scored_transactions: pd.DataFrame) -> str:
    has_id = "transaction_id" in scored_transactions.columns
    return "PASS" if has_id and scored_transactions["transaction_id"].notna().all() else "FAIL"


def run_governance_checks(context: dict) -> dict[str, str]:
    """Compute PASS/FAIL/NOT_RUN for every governance area shown on the
    Governance dashboard. All inputs come from ``context`` (see
    app.py) — nothing here reads app state directly, so it stays testable
    in isolation."""
    datasets = context["datasets"]
    scored = context["scored_transactions"]
    return {
        "Data Privacy": _check_data_privacy(datasets["customers"]),
        "Data Integrity": _check_data_integrity(datasets),
        "Explainability": _check_explainability(scored),
        "Bias": _check_bias(scored, datasets["customers"]),
        "Security": _check_security(),
        "Auditability": _check_auditability(),
        "Human Oversight": _check_human_oversight(scored),
        "Reliability": _check_reliability(),
        "Traceability": _check_traceability(scored),
    }


GOVERNANCE_AREA_DESCRIPTIONS = {
    "Data Privacy": "Protect customer information",
    "Data Integrity": "Verify source files",
    "Explainability": "Explain risk flags",
    "Bias": "Review risk scoring across groups",
    "Security": "Validate inputs",
    "Auditability": "Log important actions",
    "Human Oversight": "Human review for high-risk findings",
    "Reliability": "Test critical rules",
    "Traceability": "Map insight back to source data",
}
