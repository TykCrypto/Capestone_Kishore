import pandas as pd
import pytest

from src import anomaly_detector, data_loader


@pytest.fixture(scope="module")
def transactions():
    return data_loader.load_all()["transactions"]


def test_transactions_schema_has_required_columns(transactions):
    required = {
        "transaction_id",
        "account_id",
        "customer_id",
        "transaction_datetime",
        "transaction_amount",
        "currency",
        "transaction_type",
    }
    assert required <= set(transactions.columns)


def test_seed_risk_score_renamed_not_dropped(transactions):
    # data_loader must preserve the dataset's own seed risk_score under a
    # different name so it stays available as an evaluation reference,
    # while freeing up `risk_score` for the engine's own output.
    assert "seed_risk_score" in transactions.columns
    assert "risk_score" not in transactions.columns


def test_no_duplicate_column_names(transactions):
    assert len(transactions.columns) == len(set(transactions.columns))


def test_flag_amount_outliers_returns_aligned_boolean_column(transactions):
    result = anomaly_detector.flag_amount_outliers(transactions)
    assert list(result.index) == list(transactions.index)
    assert result["is_amount_outlier"].dtype == bool
    assert result["is_amount_outlier"].any()  # dataset has genuine outliers


def test_flag_amount_outliers_flags_an_extreme_synthetic_value():
    tx = pd.DataFrame(
        {
            "transaction_type": ["UPI"] * 25 + ["UPI"],
            "transaction_amount": [100.0] * 25 + [10_000_000.0],
        }
    )
    result = anomaly_detector.flag_amount_outliers(tx)
    assert result["is_amount_outlier"].iloc[-1]
    assert not result["is_amount_outlier"].iloc[:25].any()
