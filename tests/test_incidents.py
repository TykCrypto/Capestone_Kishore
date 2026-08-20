import pandas as pd
import pytest

from src import data_loader, incident_analyzer


@pytest.fixture(scope="module")
def datasets():
    return data_loader.load_all()


def test_sla_breached_incidents_match_ground_truth(datasets):
    found = incident_analyzer.sla_breached_incidents(datasets["incidents"])
    expected = set(pd.read_csv("expected_outputs/sla_breached_incidents.csv")["incident_id"])
    assert set(found["incident_id"]) == expected
    assert (found["sla_breached"] == "Y").all()


def test_recompute_sla_breach_broadly_agrees_with_dataset_flag(datasets):
    incidents = datasets["incidents"]
    recomputed = incident_analyzer.recompute_sla_breach(incidents, datasets["reference_data"])
    agreement = (recomputed == (incidents["sla_breached"] == "Y")).mean()
    # Open incidents use "now" as a resolution stand-in, so some disagreement
    # near the SLA boundary is expected — but the two signals must broadly agree.
    assert agreement > 0.7


def test_recurring_error_patterns_are_sorted_descending(datasets):
    patterns = incident_analyzer.recurring_error_patterns(datasets["incidents"], top_n=10)
    assert list(patterns["occurrences"]) == sorted(patterns["occurrences"], reverse=True)
    assert len(patterns) <= 10


def test_correlate_with_logs_only_covers_linked_incidents(datasets):
    correlated = incident_analyzer.correlate_with_logs(
        datasets["incidents"], datasets["api_logs"], datasets["application_logs"]
    )
    assert correlated["related_transaction_id"].notna().all()
    assert (correlated["related_api_log_count"] >= 0).all()


def test_operational_hotspots_have_breach_rate_between_0_and_100(datasets):
    hotspots = incident_analyzer.operational_hotspots(datasets["incidents"])
    assert hotspots["breach_rate_pct"].between(0, 100).all()
