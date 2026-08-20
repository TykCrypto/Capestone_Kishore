"""API log analysis: latency and HTTP failure detection."""

from __future__ import annotations

import pandas as pd

SLOW_API_THRESHOLD_MS = 2000


def slow_api_logs(api_logs: pd.DataFrame, threshold_ms: int = SLOW_API_THRESHOLD_MS) -> pd.DataFrame:
    return api_logs[api_logs["response_time_ms"] > threshold_ms]


def failed_5xx_logs(api_logs: pd.DataFrame) -> pd.DataFrame:
    codes = pd.to_numeric(api_logs["response_code"], errors="coerce")
    return api_logs[(codes >= 500) & (codes < 600)]


def api_latency_by_name(api_logs: pd.DataFrame) -> pd.DataFrame:
    return (
        api_logs.groupby("api_name")
        .agg(
            avg_response_ms=("response_time_ms", "mean"),
            p95_response_ms=("response_time_ms", lambda s: s.quantile(0.95)),
            slow_count=("response_time_ms", lambda s: (s > SLOW_API_THRESHOLD_MS).sum()),
            total_calls=("response_time_ms", "count"),
        )
        .round(0)
        .sort_values("slow_count", ascending=False)
        .reset_index()
    )


def failure_rate_by_api(api_logs: pd.DataFrame) -> pd.DataFrame:
    codes = pd.to_numeric(api_logs["response_code"], errors="coerce")
    df = api_logs.assign(is_5xx=(codes >= 500) & (codes < 600))
    grouped = df.groupby("api_name").agg(
        total_calls=("is_5xx", "count"),
        failed_5xx=("is_5xx", "sum"),
    )
    grouped["failure_rate_pct"] = (grouped["failed_5xx"] / grouped["total_calls"] * 100).round(1)
    return grouped.sort_values("failed_5xx", ascending=False).reset_index()
