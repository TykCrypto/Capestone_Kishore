"""BFSI AI Risk & Incident Intelligence Platform — Streamlit entry point.

Thin composition layer: every number/chart on every page is derived from
``src/`` engine output via the single ``build_context()`` call below. This
file owns navigation and presentation only — no business rule is
recomputed or duplicated here (DRY, Interface Segregation).
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src import (
    anomaly_detector,
    api_analyzer,
    data_cleaner,
    data_loader,
    governance_engine,
    incident_analyzer,
    insights_engine,
    observability_engine,
    risk_engine,
    test_analyzer,
    theme,
)

st.set_page_config(page_title="BFSI AI Risk & Incident Intelligence Platform", layout="wide")
theme.inject_custom_css(st)

SECTIONS = [
    "Executive Dashboard",
    "Transaction Analytics",
    "Fraud & Risk Detection",
    "Customer & Account Risk",
    "Data Quality",
    "Production Incidents",
    "API Monitoring",
    "Application Logs",
    "Test Quality",
    "AI Insights",
    "Recommendations",
    "Governance",
    "Observability & Traceability",
    "Evaluation Results",
]


@st.cache_data(show_spinner="Loading datasets...")
def load_datasets() -> dict[str, pd.DataFrame]:
    return data_loader.load_all()


def _invalid_transaction_ids(datasets: dict[str, pd.DataFrame]) -> set:
    tx, accounts, customers = datasets["transactions"], datasets["accounts"], datasets["customers"]
    ids: set = set()
    ids |= set(data_cleaner.find_negative_amounts(tx)["transaction_id"])
    ids |= set(data_cleaner.find_future_dated(tx)["transaction_id"])
    ids |= set(data_cleaner.find_invalid_currency(tx)["transaction_id"])
    ids |= set(data_cleaner.find_invalid_customer_relationship(tx, accounts, customers)["transaction_id"])
    return ids


@st.cache_data(show_spinner="Running risk, incident, API and test engines...")
def build_context(_datasets_token: int) -> dict:
    """Runs every analytical engine exactly once per data load and returns
    a single context dict — the same dict handed to insights_engine and
    governance_engine, and read by every render_* function below."""
    datasets = load_datasets()
    tx, accounts, customers = datasets["transactions"], datasets["accounts"], datasets["customers"]
    incidents, api_logs = datasets["incidents"], datasets["api_logs"]
    test_cases = datasets["test_cases"]

    scored = risk_engine.score_transactions(tx, accounts, customers)
    high_risk = risk_engine.high_risk_transactions(scored)
    dq_summary = data_cleaner.data_quality_summary(datasets)
    outliers = anomaly_detector.flag_amount_outliers(tx)

    api_latency = api_analyzer.api_latency_by_name(api_logs)
    failure_rate_api = api_analyzer.failure_rate_by_api(api_logs)
    slow_logs = api_analyzer.slow_api_logs(api_logs)
    failed_5xx = api_analyzer.failed_5xx_logs(api_logs)

    sla_breached = incident_analyzer.sla_breached_incidents(incidents)
    sla_by_module = incident_analyzer.sla_breach_rate_by(incidents, "application_module")
    recurring_patterns = incident_analyzer.recurring_error_patterns(incidents)
    hotspots = incident_analyzer.operational_hotspots(incidents)
    correlated = incident_analyzer.correlate_with_logs(incidents, api_logs, datasets["application_logs"])

    failed_tests = test_analyzer.failed_test_cases(test_cases)
    blocked_tests = test_analyzer.blocked_test_cases(test_cases)
    test_fail_rate_by_module = test_analyzer.failure_rate_by_module(test_cases)
    automation_gap = test_analyzer.automation_gap(test_cases)

    context = {
        "datasets": datasets,
        "scored_transactions": scored,
        "high_risk_transactions": high_risk,
        "customers": customers,
        "dq_summary": dq_summary,
        "invalid_transaction_ids": _invalid_transaction_ids(datasets),
        "outliers": outliers,
        "api_latency": api_latency,
        "failure_rate_api": failure_rate_api,
        "slow_logs": slow_logs,
        "failed_5xx": failed_5xx,
        "sla_breached": sla_breached,
        "sla_by_module": sla_by_module,
        "recurring_patterns": recurring_patterns,
        "hotspots": hotspots,
        "correlated": correlated,
        "failed_tests": failed_tests,
        "blocked_tests": blocked_tests,
        "test_fail_rate_by_module": test_fail_rate_by_module,
        "automation_gap": automation_gap,
    }
    context["insights"] = insights_engine.generate_insights(context)
    context["recommendations"] = insights_engine.generate_recommendations(context)
    context["governance"] = governance_engine.run_governance_checks(context)
    return context


def render_executive_dashboard(ctx: dict) -> None:
    st.title("Executive Dashboard")
    d = ctx["datasets"]
    theme.kpi_row(
        st,
        [
            ("Total Customers", f"{len(d['customers']):,}"),
            ("Total Accounts", f"{len(d['accounts']):,}"),
            ("Total Transactions", f"{len(d['transactions']):,}"),
            ("High-Risk Transactions", f"{len(ctx['high_risk_transactions']):,}"),
        ],
        accent=theme.PRIMARY,
    )
    theme.kpi_row(
        st,
        [
            ("Duplicate Transactions", f"{ctx['dq_summary']['duplicate_transactions']:,}"),
            ("Invalid Transactions", f"{len(ctx['invalid_transaction_ids']):,}"),
            ("Closed Account Transactions", f"{ctx['dq_summary']['closed_account_transactions']:,}"),
            ("Total Incidents", f"{len(d['incidents']):,}"),
        ],
        accent=theme.ACCENT,
    )
    theme.kpi_row(
        st,
        [
            ("SLA Breaches", f"{len(ctx['sla_breached']):,}"),
            ("API Failures (5xx)", f"{len(ctx['failed_5xx']):,}"),
            ("Slow APIs (>2000ms)", f"{len(ctx['slow_logs']):,}"),
            ("Failed Test Cases", f"{len(ctx['failed_tests']):,}"),
        ],
        accent=theme.RISK_HIGH,
    )

    st.markdown("### Risk Level Distribution")
    col1, col2 = st.columns(2)
    with col1:
        counts = ctx["scored_transactions"]["risk_level"].value_counts().reindex(["LOW", "MEDIUM", "HIGH"]).fillna(0)
        fig = px.pie(
            names=counts.index,
            values=counts.values,
            color=counts.index,
            color_discrete_map=theme.RISK_COLOR_MAP,
            hole=0.45,
        )
        st.plotly_chart(fig, width="stretch")
    with col2:
        sev = ctx["datasets"]["incidents"]["severity"].value_counts().sort_index()
        fig = px.bar(x=sev.index, y=sev.values, labels={"x": "Severity", "y": "Incident Count"},
                     color=sev.index, color_discrete_sequence=theme.CATEGORICAL_SEQUENCE)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")

    if ctx["insights"]:
        st.markdown("### Top Insight")
        st.info(ctx["insights"][0])


def render_transaction_analytics(ctx: dict) -> None:
    st.title("Transaction Analytics")
    tx = ctx["datasets"]["transactions"]

    theme.kpi_row(
        st,
        [
            ("Total Volume", f"{tx['transaction_amount'].sum():,.0f}"),
            ("Average Amount", f"{tx['transaction_amount'].mean():,.2f}"),
            ("Median Amount", f"{tx['transaction_amount'].median():,.2f}"),
            ("Distinct Types", f"{tx['transaction_type'].nunique()}"),
        ],
    )

    col1, col2 = st.columns(2)
    with col1:
        by_type = tx.groupby("transaction_type")["transaction_amount"].sum().sort_values(ascending=False)
        fig = px.bar(x=by_type.index, y=by_type.values, labels={"x": "Transaction Type", "y": "Total Amount"},
                     color_discrete_sequence=[theme.PRIMARY])
        st.plotly_chart(fig, width="stretch")
    with col2:
        by_channel = tx["transaction_channel"].value_counts()
        fig = px.pie(names=by_channel.index, values=by_channel.values, hole=0.45,
                     color_discrete_sequence=theme.CATEGORICAL_SEQUENCE)
        st.plotly_chart(fig, width="stretch")

    st.markdown("### Transaction Volume Over Time")
    daily = tx.set_index("transaction_datetime").resample("D").size()
    fig = px.line(x=daily.index, y=daily.values, labels={"x": "Date", "y": "Transactions"})
    fig.update_traces(line_color=theme.ACCENT)
    st.plotly_chart(fig, width="stretch")

    st.markdown("### Amount Outliers (IQR method, per transaction type)")
    outliers = ctx["outliers"]
    flagged = tx.join(outliers)
    flagged = flagged[flagged["is_amount_outlier"]]
    st.caption(f"{len(flagged):,} transactions statistically deviate from their type's typical amount range.")
    st.dataframe(
        flagged[["transaction_id", "transaction_type", "transaction_amount", "amount_deviation"]].head(200),
        width="stretch",
    )


def render_fraud_risk_detection(ctx: dict) -> None:
    st.title("Fraud & Risk Detection")
    scored = ctx["scored_transactions"]

    theme.kpi_row(
        st,
        [
            ("HIGH Risk", f"{(scored['risk_level'] == 'HIGH').sum():,}"),
            ("MEDIUM Risk", f"{(scored['risk_level'] == 'MEDIUM').sum():,}"),
            ("LOW Risk", f"{(scored['risk_level'] == 'LOW').sum():,}"),
            ("Average Risk Score", f"{scored['risk_score'].mean():.1f}"),
        ],
    )

    st.markdown("### Most Frequent Risk Reasons")
    reason_counts = pd.Series([r for reasons in scored["risk_reasons"] for r in reasons]).value_counts()
    if len(reason_counts):
        fig = px.bar(x=reason_counts.values, y=reason_counts.index, orientation="h",
                     labels={"x": "Occurrences", "y": ""}, color_discrete_sequence=[theme.RISK_HIGH])
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width="stretch")

    st.markdown("### Flagged Transactions")
    level_filter = st.multiselect("Filter by risk level", ["HIGH", "MEDIUM", "LOW"], default=["HIGH"])
    filtered = scored[scored["risk_level"].isin(level_filter)] if level_filter else scored
    display_cols = ["transaction_id", "customer_id", "transaction_amount", "currency", "risk_score", "risk_level", "risk_reasons"]
    st.dataframe(filtered[display_cols].sort_values("risk_score", ascending=False).head(300), width="stretch")

    st.caption(
        "Every flag above is explainable via `risk_reasons` and is an AI Recommendation only — "
        "see the Governance section for the Human Review boundary before any action is taken."
    )


def render_customer_account_risk(ctx: dict) -> None:
    st.title("Customer & Account Risk")
    customers = ctx["datasets"]["customers"]
    accounts = ctx["datasets"]["accounts"]
    scored = ctx["scored_transactions"]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Customer Risk Category")
        counts = customers["risk_category"].value_counts()
        fig = px.pie(names=counts.index, values=counts.values, hole=0.45,
                     color=counts.index, color_discrete_map={"LOW": theme.RISK_LOW, "MEDIUM": theme.RISK_MEDIUM, "HIGH": theme.RISK_HIGH})
        st.plotly_chart(fig, width="stretch")
    with col2:
        st.markdown("#### KYC Status")
        counts = customers["kyc_status"].value_counts()
        fig = px.bar(x=counts.index, y=counts.values, color_discrete_sequence=[theme.PRIMARY])
        st.plotly_chart(fig, width="stretch")

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### Account Status")
        counts = accounts["account_status"].value_counts()
        fig = px.bar(x=counts.index, y=counts.values, color_discrete_sequence=[theme.ACCENT])
        st.plotly_chart(fig, width="stretch")
    with col4:
        st.markdown("#### Average Risk Score by Customer Segment")
        merged = scored.merge(customers[["customer_id", "customer_segment"]], on="customer_id", how="left")
        by_segment = merged.groupby("customer_segment")["risk_score"].mean().sort_values(ascending=False)
        fig = px.bar(x=by_segment.index, y=by_segment.values, color_discrete_sequence=[theme.DARK_NAVY])
        st.plotly_chart(fig, width="stretch")

    st.markdown("### Customer Sample (PII masked)")
    st.dataframe(governance_engine.mask_pii(customers).head(50), width="stretch")


def render_data_quality(ctx: dict) -> None:
    st.title("Data Quality")
    dq = ctx["dq_summary"]

    theme.kpi_row(
        st,
        [
            ("Duplicate Transactions", f"{dq['duplicate_transactions']:,}"),
            ("Negative Amounts", f"{dq['negative_amount_transactions']:,}"),
            ("Future-Dated", f"{dq['future_dated_transactions']:,}"),
            ("Invalid Currency", f"{dq['invalid_currency_transactions']:,}"),
        ],
    )
    theme.kpi_row(
        st,
        [
            ("Closed Account Tx", f"{dq['closed_account_transactions']:,}"),
            ("Invalid Customer Relationship", f"{dq['invalid_customer_relationship_transactions']:,}"),
            ("KYC High-Value Combo", f"{dq['kyc_high_value_transactions']:,}"),
            ("Total Flagged (union)", f"{len(ctx['invalid_transaction_ids']):,}"),
        ],
        accent=theme.RISK_MEDIUM,
    )

    fig = px.bar(x=list(dq.keys()), y=list(dq.values()), color_discrete_sequence=[theme.PRIMARY])
    fig.update_layout(xaxis_title="Rule", yaxis_title="Flagged Transactions")
    st.plotly_chart(fig, width="stretch")

    tx, accounts, customers = ctx["datasets"]["transactions"], ctx["datasets"]["accounts"], ctx["datasets"]["customers"]
    rules = {
        "Duplicate Transactions": data_cleaner.find_duplicate_transactions(tx),
        "Negative Amounts": data_cleaner.find_negative_amounts(tx),
        "Future-Dated": data_cleaner.find_future_dated(tx),
        "Invalid Currency": data_cleaner.find_invalid_currency(tx),
        "Closed Account": data_cleaner.find_closed_account_transactions(tx, accounts),
        "Invalid Customer Relationship": data_cleaner.find_invalid_customer_relationship(tx, accounts, customers),
        "KYC High-Value": data_cleaner.find_kyc_high_value(tx, customers),
    }
    choice = st.selectbox("Inspect rule violations", list(rules.keys()))
    st.dataframe(rules[choice].head(200), width="stretch")


def render_production_incidents(ctx: dict) -> None:
    st.title("Production Incidents")
    incidents = ctx["datasets"]["incidents"]

    theme.kpi_row(
        st,
        [
            ("Total Incidents", f"{len(incidents):,}"),
            ("SLA Breached", f"{len(ctx['sla_breached']):,}"),
            ("Breach Rate", f"{len(ctx['sla_breached']) / len(incidents) * 100:.1f}%"),
            ("Open Incidents", f"{(incidents['incident_status'] != 'CLOSED').sum():,}"),
        ],
        accent=theme.RISK_HIGH,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### SLA Breach Rate by Application Module")
        sla = ctx["sla_by_module"].head(10)
        fig = px.bar(sla, x="application_module", y="breach_rate_pct", color_discrete_sequence=[theme.RISK_HIGH])
        st.plotly_chart(fig, width="stretch")
    with col2:
        st.markdown("#### Operational Hotspots (by team)")
        hotspots = ctx["hotspots"]
        fig = px.bar(hotspots, x="assigned_team", y="breach_rate_pct", color_discrete_sequence=[theme.DARK_NAVY])
        st.plotly_chart(fig, width="stretch")

    st.markdown("### Recurring Error Patterns")
    st.dataframe(ctx["recurring_patterns"], width="stretch")

    st.markdown("### Incidents Correlated with API/Application Logs")
    st.dataframe(ctx["correlated"].head(100), width="stretch")


def render_api_monitoring(ctx: dict) -> None:
    st.title("API Monitoring")
    api_logs = ctx["datasets"]["api_logs"]

    theme.kpi_row(
        st,
        [
            ("Total API Calls", f"{len(api_logs):,}"),
            ("Slow Calls (>2000ms)", f"{len(ctx['slow_logs']):,}"),
            ("HTTP 5xx Failures", f"{len(ctx['failed_5xx']):,}"),
            ("Avg Response (ms)", f"{api_logs['response_time_ms'].mean():.0f}"),
        ],
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Latency by API")
        st.dataframe(ctx["api_latency"], width="stretch")
    with col2:
        st.markdown("#### Failure Rate by API")
        fig = px.bar(ctx["failure_rate_api"], x="api_name", y="failure_rate_pct", color_discrete_sequence=[theme.RISK_HIGH])
        st.plotly_chart(fig, width="stretch")

    st.markdown("### Slow API Calls")
    st.dataframe(ctx["slow_logs"].head(100), width="stretch")


def render_application_logs(ctx: dict) -> None:
    st.title("Application Logs")
    logs = ctx["datasets"]["application_logs"]

    theme.kpi_row(
        st,
        [
            ("Total Log Entries", f"{len(logs):,}"),
            ("ERROR", f"{(logs['log_level'] == 'ERROR').sum():,}"),
            ("FATAL", f"{(logs['log_level'] == 'FATAL').sum():,}"),
            ("Distinct Modules", f"{logs['application_module'].nunique()}"),
        ],
    )

    col1, col2 = st.columns(2)
    with col1:
        counts = logs["log_level"].value_counts()
        fig = px.pie(names=counts.index, values=counts.values, hole=0.45,
                     color_discrete_sequence=theme.CATEGORICAL_SEQUENCE)
        st.plotly_chart(fig, width="stretch")
    with col2:
        by_module = logs[logs["log_level"].isin(["ERROR", "FATAL"])]["application_module"].value_counts().head(10)
        fig = px.bar(x=by_module.index, y=by_module.values, color_discrete_sequence=[theme.RISK_HIGH])
        st.plotly_chart(fig, width="stretch")

    st.markdown("### Most Frequent Error Codes")
    error_codes = logs[logs["error_code"].notna()]["error_code"].value_counts().head(15)
    st.dataframe(error_codes.rename("occurrences"), width="stretch")


def render_test_quality(ctx: dict) -> None:
    st.title("Test Quality")
    test_cases = ctx["datasets"]["test_cases"]

    theme.kpi_row(
        st,
        [
            ("Total Test Cases", f"{len(test_cases):,}"),
            ("Failed", f"{len(ctx['failed_tests']):,}"),
            ("Blocked", f"{len(ctx['blocked_tests']):,}"),
            ("Overall Fail Rate", f"{len(ctx['failed_tests']) / len(test_cases) * 100:.1f}%"),
        ],
        accent=theme.RISK_MEDIUM,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Failure Rate by Module")
        fig = px.bar(ctx["test_fail_rate_by_module"], x="test_module", y="fail_rate_pct",
                     color_discrete_sequence=[theme.RISK_HIGH])
        st.plotly_chart(fig, width="stretch")
    with col2:
        st.markdown("#### Automation Gap by Module")
        fig = px.bar(ctx["automation_gap"], x="test_module", y="not_automated_pct",
                     color_discrete_sequence=[theme.ACCENT])
        st.plotly_chart(fig, width="stretch")

    st.markdown("### Failed Test Cases")
    st.dataframe(ctx["failed_tests"].head(200), width="stretch")


def render_ai_insights(ctx: dict) -> None:
    st.title("AI Insights")
    st.caption("Data-supported observations only — evidence, not action. See Recommendations for suggested next steps.")
    if not ctx["insights"]:
        st.info("No notable insights surfaced from the current data.")
    for insight in ctx["insights"]:
        st.markdown(f"- {insight}")


def render_recommendations(ctx: dict) -> None:
    st.title("Recommendations")
    st.warning(
        "**AI Recommendation → Human Review → Final Decision.** "
        "These are suggested actions only. No item below has been approved, actioned, or represents a final banking decision."
    )
    if not ctx["recommendations"]:
        st.info("No recommendations generated from the current data.")
    for rec in ctx["recommendations"]:
        st.markdown(f"- {rec}")


def render_governance(ctx: dict) -> None:
    st.title("Governance")
    results = ctx["governance"]

    cols = st.columns(3)
    for i, (area, status) in enumerate(results.items()):
        color = {"PASS": theme.RISK_LOW, "FAIL": theme.RISK_HIGH, "NOT_RUN": theme.RISK_MEDIUM}.get(status, theme.RISK_MEDIUM)
        with cols[i % 3]:
            st.markdown(
                f"""<div class="kpi-card" style="border-left-color:{color};">
                    <div class="kpi-label">{area}</div>
                    <div class="kpi-value" style="color:{color}; font-size:1.3rem;">{status}</div>
                    <div style="font-size:0.8rem; color:#5A6B87;">{governance_engine.GOVERNANCE_AREA_DESCRIPTIONS.get(area, '')}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("### AI Recommendation → Human Review → Final Decision")
    st.info(
        "Every HIGH-risk finding produced by this platform is a recommendation for human review. "
        "No score, insight, or recommendation on this dashboard constitutes an automated final decision."
    )

    st.markdown("### Recent Audit Log")
    if governance_engine.AUDIT_LOG_PATH.exists():
        audit_log = pd.read_csv(governance_engine.AUDIT_LOG_PATH)
        st.dataframe(audit_log.tail(50), width="stretch")
    else:
        st.caption("No audit log entries yet.")


def _display_record(label: str, record: dict | None) -> None:
    st.markdown(f"**{label}**")
    if record is None:
        st.caption("No matching record found.")
        return
    masked = governance_engine.mask_pii(pd.DataFrame([record])).iloc[0].to_dict()
    st.json(masked, expanded=False)


def _render_transaction_trace(trace: dict) -> None:
    if not trace["found"]:
        st.warning(f"No transaction found with id `{trace['transaction_id']}`.")
        return

    st.success(f"Traced transaction `{trace['transaction_id']}` across every dataset and engine it touches.")
    col1, col2 = st.columns(2)
    with col1:
        _display_record("Transaction", trace["transaction"])
        _display_record("Customer", trace["customer"])
    with col2:
        _display_record("Account", trace["account"])
        st.markdown("**Risk Assessment**")
        st.json(
            {
                "risk_score": trace["risk_score"],
                "risk_level": trace["risk_level"],
                "risk_reasons": trace["risk_reasons"],
            },
            expanded=True,
        )

    theme.kpi_row(
        st,
        [
            ("Related Incidents", f"{len(trace['related_incidents']):,}"),
            ("Related API Log Entries", f"{trace['related_api_log_count']:,}"),
            ("Related Application Log Entries", f"{trace['related_app_log_count']:,}"),
        ],
        accent=theme.ACCENT,
    )
    if trace["related_incidents"]:
        st.markdown("**Related Incidents**")
        st.dataframe(pd.DataFrame(trace["related_incidents"]), width="stretch")


def _render_incident_trace(trace: dict) -> None:
    if not trace["found"]:
        st.warning(f"No incident found with id `{trace['incident_id']}`.")
        return

    st.success(f"Traced incident `{trace['incident_id']}` across every dataset and engine it touches.")
    _display_record("Incident", trace["incident"])
    st.markdown(f"**SLA Breached:** {'Yes' if trace['sla_breached'] else 'No'}")

    if trace["related_transaction_trace"] is not None:
        st.markdown("### Related Transaction Trace")
        _render_transaction_trace(trace["related_transaction_trace"])
    else:
        st.caption("This incident has no related transaction to trace further.")


def render_observability_traceability(ctx: dict) -> None:
    st.title("Observability & Traceability")
    st.caption(
        "Operational visibility into the pipeline's own execution (audit-log activity) plus an "
        "end-to-end lineage trace from any transaction or incident back to every source row and "
        "engine output that touches it. See the Governance section for the PASS/FAIL policy checks "
        "this evidence supports."
    )

    audit_log = observability_engine.load_audit_log()
    summary = observability_engine.pipeline_run_summary(ctx, audit_log)

    theme.kpi_row(
        st,
        [
            ("Datasets Loaded", f"{summary['datasets_loaded']}"),
            ("Total Source Rows", f"{summary['total_source_rows']:,}"),
            ("Audit Events Logged", f"{summary['audit_events_logged']:,}"),
            ("High-Risk Flags", f"{summary['high_risk_flags']:,}"),
        ],
    )
    theme.kpi_row(
        st,
        [
            ("Audit Error/Fail Events", f"{summary['audit_error_events']:,}"),
            ("Last Audit Event", f"{summary['last_audit_event']}" if summary["last_audit_event"] is not None else "—"),
        ],
        accent=theme.RISK_MEDIUM,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Audit Actions by Type")
        action_summary = observability_engine.audit_action_summary(audit_log)
        if action_summary.empty:
            st.caption("No audit events recorded yet.")
        else:
            fig = px.bar(action_summary, x="action", y="occurrences", color_discrete_sequence=[theme.PRIMARY])
            st.plotly_chart(fig, width="stretch")
    with col2:
        st.markdown("#### Audit Events Over Time")
        timeline = observability_engine.audit_events_over_time(audit_log)
        if timeline.empty:
            st.caption("No audit events recorded yet.")
        else:
            fig = px.line(timeline, x="date", y="events")
            fig.update_traces(line_color=theme.ACCENT)
            fig.update_xaxes(tickformat="%Y-%m-%d")
            st.plotly_chart(fig, width="stretch")

    st.markdown("### Audit Error / Failure Events")
    errors = observability_engine.audit_error_events(audit_log)
    if errors.empty:
        st.caption("No error/failure events logged.")
    else:
        st.dataframe(errors.tail(50), width="stretch")

    st.markdown("---")
    st.markdown("### Traceability Lookup")
    st.caption("Trace a single transaction or incident end-to-end across every dataset and engine output it appears in.")

    lookup_type = st.radio("Trace by", ["Transaction ID", "Incident ID"], horizontal=True)
    if lookup_type == "Transaction ID":
        high_risk = ctx["high_risk_transactions"]
        sample_id = str(high_risk["transaction_id"].iloc[0]) if len(high_risk) else ""
        tx_id = st.text_input("Transaction ID", value=sample_id)
        if st.button("Trace Transaction") and tx_id:
            trace = observability_engine.trace_transaction(tx_id, ctx)
            governance_engine.append_audit_log("traceability_lookup", f"transaction_id={tx_id} found={trace['found']}")
            _render_transaction_trace(trace)
    else:
        sla_breached = ctx["sla_breached"]
        sample_id = str(sla_breached["incident_id"].iloc[0]) if len(sla_breached) else ""
        inc_id = st.text_input("Incident ID", value=sample_id)
        if st.button("Trace Incident") and inc_id:
            trace = observability_engine.trace_incident(inc_id, ctx)
            governance_engine.append_audit_log("traceability_lookup", f"incident_id={inc_id} found={trace['found']}")
            _render_incident_trace(trace)


def render_evaluation_results(ctx: dict) -> None:
    st.title("Evaluation Results")
    st.caption("Metrics are computed by evaluation/evaluation_metrics.py against expected_outputs/ ground truth and the dataset's independent fraud_flag label — never hard-coded.")

    if st.button("Run Evaluation Now"):
        with st.spinner("Running pytest and recomputing metrics..."):
            from evaluation.evaluation_metrics import evaluate

            evaluate()
        st.success("Evaluation complete.")

    report_path = governance_engine.EVALUATION_REPORT_PATH
    if report_path.exists():
        report = pd.read_csv(report_path)
        st.dataframe(report, width="stretch")
    else:
        st.info("No evaluation report yet — click 'Run Evaluation Now' to generate one.")

    st.markdown("### Evaluation Test Set")
    test_set_path = report_path.parent / "test_set.csv"
    if test_set_path.exists():
        st.dataframe(pd.read_csv(test_set_path), width="stretch")


RENDERERS = {
    "Executive Dashboard": render_executive_dashboard,
    "Transaction Analytics": render_transaction_analytics,
    "Fraud & Risk Detection": render_fraud_risk_detection,
    "Customer & Account Risk": render_customer_account_risk,
    "Data Quality": render_data_quality,
    "Production Incidents": render_production_incidents,
    "API Monitoring": render_api_monitoring,
    "Application Logs": render_application_logs,
    "Test Quality": render_test_quality,
    "AI Insights": render_ai_insights,
    "Recommendations": render_recommendations,
    "Governance": render_governance,
    "Observability & Traceability": render_observability_traceability,
    "Evaluation Results": render_evaluation_results,
}


def main() -> None:
    st.sidebar.markdown("## BFSI AI Risk &\nIncident Intelligence")
    section = st.sidebar.radio("Navigate", SECTIONS, label_visibility="collapsed")
    context = build_context(0)
    RENDERERS[section](context)


if __name__ == "__main__":
    main()
