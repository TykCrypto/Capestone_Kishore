"""Pipeline observability (audit-log analytics, run metrics) and
end-to-end traceability (tracing one transaction or incident back
through every source dataset and engine output it touches).

Complements ``governance_engine``'s PASS/FAIL checks with the underlying
evidence those checks are based on. This module only reads/analyzes the
audit log and traces records — ``governance_engine`` remains the sole
writer of audit entries and policy checker (DRY, Single Responsibility).
"""

from __future__ import annotations

import pandas as pd

from src.governance_engine import AUDIT_LOG_PATH

AUDIT_LOG_COLUMNS = ["timestamp", "action", "detail"]


def load_audit_log() -> pd.DataFrame:
    if not AUDIT_LOG_PATH.exists():
        return pd.DataFrame(columns=AUDIT_LOG_COLUMNS)
    log = pd.read_csv(AUDIT_LOG_PATH)
    log["timestamp"] = pd.to_datetime(log["timestamp"], errors="coerce")
    return log


def audit_action_summary(audit_log: pd.DataFrame) -> pd.DataFrame:
    if audit_log.empty:
        return pd.DataFrame(columns=["action", "occurrences"])
    return audit_log["action"].value_counts().rename_axis("action").reset_index(name="occurrences")


def audit_events_over_time(audit_log: pd.DataFrame) -> pd.DataFrame:
    if audit_log.empty:
        return pd.DataFrame(columns=["date", "events"])
    daily = audit_log.set_index("timestamp").resample("D").size()
    return daily.rename_axis("date").reset_index(name="events")


def audit_error_events(audit_log: pd.DataFrame) -> pd.DataFrame:
    if audit_log.empty:
        return audit_log
    is_error = audit_log["detail"].str.contains("error|FAIL", case=False, na=False)
    return audit_log[is_error]


def pipeline_run_summary(context: dict, audit_log: pd.DataFrame) -> dict:
    """KPIs for the Observability & Traceability page — every value is
    derived from ``context``/the audit log, never hard-coded."""
    datasets = context["datasets"]
    errors = audit_error_events(audit_log)
    return {
        "datasets_loaded": len(datasets),
        "total_source_rows": int(sum(len(df) for df in datasets.values())),
        "high_risk_flags": int(len(context["high_risk_transactions"])),
        "audit_events_logged": int(len(audit_log)),
        "audit_error_events": int(len(errors)),
        "last_audit_event": audit_log["timestamp"].max() if not audit_log.empty else None,
    }


def _row_or_none(df: pd.DataFrame, key_col: str, value) -> dict | None:
    match = df[df[key_col] == value]
    return match.iloc[0].to_dict() if not match.empty else None


def trace_transaction(transaction_id: str, context: dict) -> dict:
    """Follow one transaction end-to-end: its own row, the customer and
    account it belongs to, the risk score/reasons the risk engine
    assigned it, any incident that references it, and how many API/
    application log entries mention it."""
    datasets = context["datasets"]
    transactions = datasets["transactions"]

    match = transactions[transactions["transaction_id"] == transaction_id]
    if match.empty:
        return {"transaction_id": transaction_id, "found": False}

    row = match.iloc[0]
    scored = context["scored_transactions"]
    score_match = scored[scored["transaction_id"] == transaction_id]

    incidents = datasets["incidents"]
    related_incidents = incidents[incidents["related_transaction_id"] == transaction_id]

    return {
        "transaction_id": transaction_id,
        "found": True,
        "transaction": row.to_dict(),
        "customer": _row_or_none(datasets["customers"], "customer_id", row.get("customer_id")),
        "account": _row_or_none(datasets["accounts"], "account_id", row.get("account_id")),
        "risk_score": int(score_match.iloc[0]["risk_score"]) if not score_match.empty else None,
        "risk_level": score_match.iloc[0]["risk_level"] if not score_match.empty else None,
        "risk_reasons": score_match.iloc[0]["risk_reasons"] if not score_match.empty else [],
        "related_incidents": related_incidents.to_dict("records"),
        "related_api_log_count": int((datasets["api_logs"]["transaction_id"] == transaction_id).sum()),
        "related_app_log_count": int((datasets["application_logs"]["transaction_id"] == transaction_id).sum()),
    }


def trace_incident(incident_id: str, context: dict) -> dict:
    """Follow one incident end-to-end: its own row, its SLA status, and
    (when it references a transaction) the full transaction trace plus
    matching API/application log rows."""
    datasets = context["datasets"]
    incidents = datasets["incidents"]

    match = incidents[incidents["incident_id"] == incident_id]
    if match.empty:
        return {"incident_id": incident_id, "found": False}

    row = match.iloc[0]
    related_transaction_id = row.get("related_transaction_id")
    transaction_trace = (
        trace_transaction(related_transaction_id, context) if pd.notna(related_transaction_id) else None
    )

    return {
        "incident_id": incident_id,
        "found": True,
        "incident": row.to_dict(),
        "sla_breached": row.get("sla_breached") == "Y",
        "related_transaction_trace": transaction_trace,
    }
