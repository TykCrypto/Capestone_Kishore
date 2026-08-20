import pandas as pd
import pytest

from src import api_analyzer, data_loader


@pytest.fixture(scope="module")
def api_logs():
    return data_loader.load_all()["api_logs"]


def test_slow_api_logs_match_ground_truth(api_logs):
    found = api_analyzer.slow_api_logs(api_logs)
    expected = set(pd.read_csv("expected_outputs/slow_api_logs_over_2000ms.csv")["log_id"])
    assert set(found["log_id"]) == expected
    assert (found["response_time_ms"] > 2000).all()


def test_failed_5xx_logs_match_ground_truth(api_logs):
    found = api_analyzer.failed_5xx_logs(api_logs)
    expected = set(pd.read_csv("expected_outputs/failed_api_logs_5xx.csv")["log_id"])
    assert set(found["log_id"]) == expected
    codes = pd.to_numeric(found["response_code"])
    assert codes.between(500, 599).all()


def test_api_latency_by_name_has_expected_columns(api_logs):
    result = api_analyzer.api_latency_by_name(api_logs)
    assert {"api_name", "avg_response_ms", "p95_response_ms", "slow_count", "total_calls"} <= set(
        result.columns
    )
    assert (result["slow_count"] <= result["total_calls"]).all()


def test_failure_rate_by_api_is_a_valid_percentage(api_logs):
    result = api_analyzer.failure_rate_by_api(api_logs)
    assert result["failure_rate_pct"].between(0, 100).all()


def test_slow_threshold_boundary_is_exclusive():
    logs = pd.DataFrame({"response_time_ms": [2000, 2001], "log_id": ["A", "B"]})
    found = api_analyzer.slow_api_logs(logs)
    assert list(found["log_id"]) == ["B"]
