"""Turns computed analysis results into plain-language insights and
recommendations.

Every statement is built from a number pulled out of ``context`` at call
time — nothing here is a canned string, so results move when the data
does. ``context`` is the single dict assembled once in ``app.py`` (see
its module docstring for the exact keys); passing one dict instead of a
dozen positional DataFrames keeps this module's interface narrow and
stable as more analyzers are added.

Insights = observed evidence. Recommendations = suggested action. The two
are kept in separate functions/sections on purpose so the UI never blurs
"what happened" with "what to do about it" (CLAUDE.md governance rule:
AI Recommendation -> Human Review -> Final Decision).
"""

from __future__ import annotations

import pandas as pd


def generate_insights(context: dict) -> list[str]:
    insights: list[str] = []

    high_risk = context["high_risk_transactions"]
    customers = context["customers"]
    if len(high_risk):
        merged = high_risk.merge(
            customers[["customer_id", "customer_segment"]], on="customer_id", how="left"
        )
        top_segment = merged["customer_segment"].value_counts().idxmax()
        top_count = merged["customer_segment"].value_counts().max()
        pct = round(top_count / len(high_risk) * 100, 1)
        insights.append(
            f"{pct}% of HIGH-risk transactions ({top_count} of {len(high_risk)}) are concentrated "
            f"in the {top_segment} customer segment."
        )

    closed_count = context["dq_summary"]["closed_account_transactions"]
    if closed_count:
        insights.append(
            f"{closed_count} transactions occurred against CLOSED accounts, indicating a control "
            f"gap in account-status enforcement at the point of transaction."
        )

    api_latency = context["api_latency"]
    slow_row = api_latency[api_latency["slow_count"] > 0].sort_values("slow_count", ascending=False)
    if len(slow_row):
        row = slow_row.iloc[0]
        pct = round(row["slow_count"] / row["total_calls"] * 100, 1)
        insights.append(
            f"The {row['api_name']} API exceeded the 2000ms response-time threshold in "
            f"{int(row['slow_count'])} of {int(row['total_calls'])} calls ({pct}%), the worst of any API."
        )

    patterns = context["recurring_patterns"]
    if len(patterns):
        row = patterns.iloc[0]
        insights.append(
            f"Root cause '{row['root_cause']}' in the {row['application_module']} module accounts for "
            f"{int(row['occurrences'])} incidents, the most frequent recurring pattern in production."
        )

    sla_by_module = context["sla_by_module"]
    if len(sla_by_module):
        row = sla_by_module.sort_values("breach_rate_pct", ascending=False).iloc[0]
        insights.append(
            f"The {row['application_module']} module has the highest SLA breach rate at "
            f"{row['breach_rate_pct']}% ({int(row['breached'])} of {int(row['total_incidents'])} incidents)."
        )

    fail_by_module = context["test_fail_rate_by_module"]
    if len(fail_by_module):
        row = fail_by_module.sort_values("fail_rate_pct", ascending=False).iloc[0]
        insights.append(
            f"The {row['test_module']} test module has the highest failure rate at "
            f"{row['fail_rate_pct']}% ({int(row['failed'])} of {int(row['total'])} test cases)."
        )

    return insights


def generate_recommendations(context: dict) -> list[str]:
    recommendations: list[str] = []

    high_risk = context["high_risk_transactions"]
    if len(high_risk):
        recommendations.append(
            f"Prioritize investigation of the {len(high_risk)} HIGH-risk transactions flagged by "
            f"the risk engine before further processing."
        )

    closed_count = context["dq_summary"]["closed_account_transactions"]
    if closed_count:
        recommendations.append(
            f"Introduce real-time controls to block transaction attempts on closed accounts "
            f"({closed_count} observed in this dataset)."
        )

    api_latency = context["api_latency"]
    slow_row = api_latency[api_latency["slow_count"] > 0].sort_values("slow_count", ascending=False)
    if len(slow_row):
        row = slow_row.iloc[0]
        recommendations.append(
            f"Investigate the {row['api_name']} API with the owning engineering team — it repeatedly "
            f"exceeds the latency threshold ({int(row['slow_count'])} calls over 2000ms)."
        )

    failed_5xx = context["failed_5xx"]
    if len(failed_5xx):
        recommendations.append(
            f"Prioritize root-cause remediation of recurring HTTP 5xx failures "
            f"({len(failed_5xx)} occurrences across the API log)."
        )

    sla_by_module = context["sla_by_module"]
    if len(sla_by_module):
        row = sla_by_module.sort_values("breach_rate_pct", ascending=False).iloc[0]
        recommendations.append(
            f"Escalate the {row['application_module']} incident category to leadership given its "
            f"{row['breach_rate_pct']}% SLA breach rate."
        )

    fail_by_module = context["test_fail_rate_by_module"]
    if len(fail_by_module):
        row = fail_by_module.sort_values("fail_rate_pct", ascending=False).iloc[0]
        recommendations.append(
            f"Strengthen regression testing coverage for the {row['test_module']} module, which has "
            f"the highest test failure rate ({row['fail_rate_pct']}%)."
        )

    return recommendations
