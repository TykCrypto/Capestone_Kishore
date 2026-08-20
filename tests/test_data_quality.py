import pandas as pd
import pytest

from src import data_cleaner, data_loader

EXPECTED_DIR = "expected_outputs"


@pytest.fixture(scope="module")
def datasets():
    return data_loader.load_all()


def _expected_ids(name: str, id_col: str = "transaction_id") -> set:
    df = pd.read_csv(f"{EXPECTED_DIR}/{name}.csv")
    return set(df[id_col])


def _expected_row_count(name: str) -> int:
    return len(pd.read_csv(f"{EXPECTED_DIR}/{name}.csv"))


def test_duplicate_transactions_match_ground_truth(datasets):
    found = data_cleaner.find_duplicate_transactions(datasets["transactions"])
    assert set(found["transaction_id"]) == _expected_ids("duplicate_transaction_ids")


def test_negative_amount_transactions_match_ground_truth(datasets):
    found = data_cleaner.find_negative_amounts(datasets["transactions"])
    assert set(found["transaction_id"]) == _expected_ids("negative_amount_transactions")
    assert (found["transaction_amount"] < 0).all()


def test_future_dated_transactions_match_ground_truth(datasets):
    found = data_cleaner.find_future_dated(datasets["transactions"])
    assert set(found["transaction_id"]) == _expected_ids("future_dated_transactions")


def test_invalid_currency_transactions_are_not_in_valid_set(datasets):
    found = data_cleaner.find_invalid_currency(datasets["transactions"])
    assert not set(found["currency"]) & data_cleaner.VALID_CURRENCIES
    assert len(found) > 0


def test_closed_account_transactions_match_ground_truth(datasets):
    found = data_cleaner.find_closed_account_transactions(datasets["transactions"], datasets["accounts"])
    assert set(found["transaction_id"]) == _expected_ids("closed_account_transactions")


def test_invalid_customer_relationship_matches_ground_truth(datasets):
    found = data_cleaner.find_invalid_customer_relationship(
        datasets["transactions"], datasets["accounts"], datasets["customers"]
    )
    assert set(found["transaction_id"]) == _expected_ids("invalid_customer_relationship_transactions")


def test_kyc_high_value_matches_ground_truth(datasets):
    found = data_cleaner.find_kyc_high_value(datasets["transactions"], datasets["customers"])
    assert set(found["transaction_id"]) == _expected_ids("kyc_high_value_transactions")
    assert (found["transaction_amount"] >= data_cleaner.KYC_HIGH_VALUE_THRESHOLD).all()


def test_data_quality_summary_counts_are_consistent(datasets):
    summary = data_cleaner.data_quality_summary(datasets)
    assert summary["duplicate_transactions"] == _expected_row_count("duplicate_transaction_ids")
    assert summary["closed_account_transactions"] == _expected_row_count("closed_account_transactions")
    assert all(count >= 0 for count in summary.values())


def test_negative_amount_edge_case_is_caught():
    tx = pd.DataFrame({"transaction_id": ["T1", "T2"], "transaction_amount": [-1.0, 5.0]})
    found = data_cleaner.find_negative_amounts(tx)
    assert list(found["transaction_id"]) == ["T1"]


def test_clean_transaction_triggers_no_quality_rule():
    tx = pd.DataFrame(
        {
            "transaction_id": ["T1"],
            "transaction_amount": [100.0],
            "currency": ["INR"],
        }
    )
    assert data_cleaner.find_negative_amounts(tx).empty
    assert data_cleaner.find_invalid_currency(tx).empty
