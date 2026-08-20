import pandas as pd
import pytest

from src import data_loader, risk_engine


@pytest.fixture(scope="module")
def datasets():
    return data_loader.load_all()


@pytest.fixture(scope="module")
def scored(datasets):
    return risk_engine.score_transactions(
        datasets["transactions"], datasets["accounts"], datasets["customers"]
    )


def test_risk_score_is_within_bounds(scored):
    assert scored["risk_score"].between(0, 100).all()


def test_risk_level_bands_match_score(scored):
    assert (scored.loc[scored["risk_score"] >= 70, "risk_level"] == "HIGH").all()
    medium = scored[(scored["risk_score"] >= 40) & (scored["risk_score"] < 70)]
    assert (medium["risk_level"] == "MEDIUM").all()
    low = scored[scored["risk_score"] < 40]
    assert (low["risk_level"] == "LOW").all()


def test_every_high_risk_row_has_reasons(scored):
    high_risk = risk_engine.high_risk_transactions(scored)
    assert len(high_risk) > 0
    assert high_risk["risk_reasons"].apply(len).gt(0).all()


def test_high_risk_transactions_match_ground_truth(scored):
    high_risk_ids = set(risk_engine.high_risk_transactions(scored)["transaction_id"])
    expected = set(pd.read_csv("expected_outputs/expected_high_risk_transactions.csv")["transaction_id"])
    assert high_risk_ids == expected


def test_negative_amount_alone_scores_at_least_its_rule_weight(datasets):
    tx = datasets["transactions"].iloc[[0]].copy()
    tx["transaction_amount"] = -500.0
    scored_one = risk_engine.score_transactions(tx, datasets["accounts"], datasets["customers"])
    assert scored_one.iloc[0]["risk_score"] >= 30
    assert "Negative transaction amount" in scored_one.iloc[0]["risk_reasons"]


def test_clean_row_with_low_risk_customer_scores_low():
    tx = pd.DataFrame(
        {
            "transaction_id": ["TX_TEST_1"],
            "account_id": ["ACC_TEST_1"],
            "customer_id": ["CUST_TEST_1"],
            "transaction_amount": [500.0],
            "currency": ["INR"],
            "transaction_type": ["UPI"],
            "transaction_datetime": [pd.Timestamp("2026-01-01")],
        }
    )
    accounts = pd.DataFrame(
        {
            "account_id": ["ACC_TEST_1"],
            "customer_id": ["CUST_TEST_1"],
            "account_status": ["ACTIVE"],
            "freeze_status": ["N"],
            "currency": ["INR"],
        }
    )
    customers = pd.DataFrame(
        {"customer_id": ["CUST_TEST_1"], "risk_category": ["LOW"], "kyc_status": ["VERIFIED"]}
    )
    scored_one = risk_engine.score_transactions(tx, accounts, customers)
    assert scored_one.iloc[0]["risk_level"] == "LOW"
    assert scored_one.iloc[0]["risk_reasons"] == []
