import pandas as pd
import pytest

from src import data_loader, observability_engine, risk_engine


@pytest.fixture(scope="module")
def datasets():
    return data_loader.load_all()


@pytest.fixture(scope="module")
def context(datasets):
    scored = risk_engine.score_transactions(
        datasets["transactions"], datasets["accounts"], datasets["customers"]
    )
    return {
        "datasets": datasets,
        "scored_transactions": scored,
        "high_risk_transactions": risk_engine.high_risk_transactions(scored),
    }


def _sample_audit_log() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": ["2026-08-18T09:00:00", "2026-08-18T10:00:00", "2026-08-19T09:00:00"],
            "action": ["post_tool_use:Edit", "governance_check", "post_tool_use:Edit"],
            "detail": ["status=ok target=src/x.py", "results={'Security': 'FAIL'}", "status=error target=src/y.py"],
        }
    )


def test_load_audit_log_returns_empty_frame_with_columns_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(observability_engine, "AUDIT_LOG_PATH", tmp_path / "does_not_exist.csv")
    log = observability_engine.load_audit_log()
    assert log.empty
    assert list(log.columns) == observability_engine.AUDIT_LOG_COLUMNS


def test_audit_action_summary_counts_by_action():
    log = _sample_audit_log()
    summary = observability_engine.audit_action_summary(log)
    counts = dict(zip(summary["action"], summary["occurrences"]))
    assert counts["post_tool_use:Edit"] == 2
    assert counts["governance_check"] == 1


def test_audit_events_over_time_groups_by_day():
    log = _sample_audit_log()
    log["timestamp"] = pd.to_datetime(log["timestamp"])
    timeline = observability_engine.audit_events_over_time(log)
    assert timeline["events"].sum() == 3
    assert len(timeline) == 2


def test_audit_error_events_matches_error_and_fail_case_insensitively():
    log = _sample_audit_log()
    errors = observability_engine.audit_error_events(log)
    assert len(errors) == 2
    assert "status=error target=src/y.py" in errors["detail"].values
    assert "results={'Security': 'FAIL'}" in errors["detail"].values


def test_audit_helpers_handle_empty_log():
    empty = pd.DataFrame(columns=observability_engine.AUDIT_LOG_COLUMNS)
    assert observability_engine.audit_action_summary(empty).empty
    assert observability_engine.audit_events_over_time(empty).empty
    assert observability_engine.audit_error_events(empty).empty


def test_pipeline_run_summary_derives_from_context(context):
    log = _sample_audit_log()
    log["timestamp"] = pd.to_datetime(log["timestamp"])
    summary = observability_engine.pipeline_run_summary(context, log)
    assert summary["datasets_loaded"] == len(context["datasets"])
    assert summary["total_source_rows"] == sum(len(df) for df in context["datasets"].values())
    assert summary["high_risk_flags"] == len(context["high_risk_transactions"])
    assert summary["audit_events_logged"] == 3
    assert summary["audit_error_events"] == 2


def test_trace_transaction_links_customer_and_account(context):
    known_id = context["datasets"]["transactions"]["transaction_id"].iloc[0]
    trace = observability_engine.trace_transaction(known_id, context)

    assert trace["found"] is True
    assert trace["transaction"]["transaction_id"] == known_id
    if trace["customer"] is not None:
        assert trace["customer"]["customer_id"] == trace["transaction"]["customer_id"]
    if trace["account"] is not None:
        assert trace["account"]["account_id"] == trace["transaction"]["account_id"]
    assert isinstance(trace["risk_reasons"], list)


def test_trace_transaction_unknown_id_reports_not_found(context):
    trace = observability_engine.trace_transaction("TX_DOES_NOT_EXIST", context)
    assert trace == {"transaction_id": "TX_DOES_NOT_EXIST", "found": False}


def test_trace_incident_nests_transaction_trace_when_linked(context):
    incidents = context["datasets"]["incidents"]
    linked = incidents[incidents["related_transaction_id"].notna()].iloc[0]

    trace = observability_engine.trace_incident(linked["incident_id"], context)

    assert trace["found"] is True
    assert trace["related_transaction_trace"] is not None
    assert trace["related_transaction_trace"]["found"] is True
    assert trace["related_transaction_trace"]["transaction_id"] == linked["related_transaction_id"]


def test_trace_incident_unknown_id_reports_not_found(context):
    trace = observability_engine.trace_incident("INC_DOES_NOT_EXIST", context)
    assert trace == {"incident_id": "INC_DOES_NOT_EXIST", "found": False}
