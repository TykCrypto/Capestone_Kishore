"""Production incident analysis: SLA breaches, recurring patterns,
cross-correlation with API/application logs, and operational hotspots.
"""

from __future__ import annotations

import pandas as pd


def _sla_hours_by_severity(reference_data: pd.DataFrame) -> dict[str, float]:
    sla_rows = reference_data[reference_data["reference_type"] == "SLA_RULE"]
    return dict(zip(sla_rows["code"], sla_rows["attribute_1"].astype(float)))


def recompute_sla_breach(incidents: pd.DataFrame, reference_data: pd.DataFrame) -> pd.Series:
    """Independently recompute SLA breach from elapsed time vs. the SLA
    hours table, as a cross-check against the dataset's own
    ``sla_breached`` flag (used to report a Reliability governance check)."""
    hours_map = _sla_hours_by_severity(reference_data)
    sla_hours = incidents["severity"].map(hours_map)
    resolved = incidents["resolved_datetime"]
    reported = incidents["reported_datetime"]
    elapsed_hours = (resolved.fillna(pd.Timestamp.now()) - reported).dt.total_seconds() / 3600
    return elapsed_hours > sla_hours


def sla_breached_incidents(incidents: pd.DataFrame) -> pd.DataFrame:
    return incidents[incidents["sla_breached"] == "Y"]


def sla_breach_rate_by(incidents: pd.DataFrame, by: str) -> pd.DataFrame:
    grouped = incidents.groupby(by).agg(
        total_incidents=("incident_id", "count"),
        breached=("sla_breached", lambda s: (s == "Y").sum()),
    )
    grouped["breach_rate_pct"] = (grouped["breached"] / grouped["total_incidents"] * 100).round(1)
    return grouped.sort_values("breached", ascending=False).reset_index()


def recurring_error_patterns(incidents: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    return (
        incidents.groupby(["application_module", "root_cause"])
        .size()
        .reset_index(name="occurrences")
        .sort_values("occurrences", ascending=False)
        .head(top_n)
    )


def correlate_with_logs(
    incidents: pd.DataFrame, api_logs: pd.DataFrame, application_logs: pd.DataFrame
) -> pd.DataFrame:
    """For each incident with a related transaction, count how many API/
    application log entries reference that same transaction — a simple,
    explainable evidence trail rather than a black-box correlation score."""
    linked = incidents[incidents["related_transaction_id"].notna()].copy()
    api_counts = api_logs.groupby("transaction_id").size()
    app_counts = application_logs.groupby("transaction_id").size()
    linked["related_api_log_count"] = linked["related_transaction_id"].map(api_counts).fillna(0).astype(int)
    linked["related_app_log_count"] = linked["related_transaction_id"].map(app_counts).fillna(0).astype(int)
    return linked[
        [
            "incident_id",
            "application_module",
            "related_transaction_id",
            "related_api_log_count",
            "related_app_log_count",
            "sla_breached",
        ]
    ]


def operational_hotspots(incidents: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    return sla_breach_rate_by(incidents, "assigned_team").head(top_n)
