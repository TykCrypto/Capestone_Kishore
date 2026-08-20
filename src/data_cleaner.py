"""Data-quality rule detectors.

Each ``find_*`` function takes raw DataFrame(s) and returns the subset of
transaction rows that violate one specific, named rule. Keeping one rule
per function (instead of one big "clean everything" pass) is what lets
``risk_engine`` register/compose them independently (see RULES there) and
lets tests assert on each rule in isolation.
"""

from __future__ import annotations

import pandas as pd

VALID_CURRENCIES = {"INR", "USD", "EUR", "GBP"}
KYC_HIGH_VALUE_THRESHOLD = 100_000  # INR-equivalent; see governance/risk_policy.md
NON_VERIFIED_KYC = {"PENDING", "REJECTED", "EXPIRED"}


def enrich_with_account_info(transactions: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Left-join account status/owner/currency onto each transaction.

    Shared by data-quality checks and the risk engine so the join logic
    (and its column names) exists in exactly one place.
    """
    acct_cols = accounts[["account_id", "customer_id", "account_status", "freeze_status", "currency"]].rename(
        columns={
            "customer_id": "account_customer_id",
            "account_status": "account_status",
            "currency": "account_currency",
        }
    )
    return transactions.merge(acct_cols, on="account_id", how="left", suffixes=("", "_acct"))


def find_duplicate_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    mask = transactions["transaction_id"].duplicated(keep=False)
    return transactions[mask]


def find_negative_amounts(transactions: pd.DataFrame) -> pd.DataFrame:
    return transactions[transactions["transaction_amount"] < 0]


def find_future_dated(transactions: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.DataFrame:
    as_of = as_of or pd.Timestamp.now()
    return transactions[transactions["transaction_datetime"] > as_of]


def find_invalid_currency(transactions: pd.DataFrame) -> pd.DataFrame:
    return transactions[~transactions["currency"].isin(VALID_CURRENCIES)]


def find_closed_account_transactions(transactions: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    enriched = enrich_with_account_info(transactions, accounts)
    return transactions[(enriched["account_status"] == "CLOSED").values]


def find_invalid_customer_relationship(
    transactions: pd.DataFrame, accounts: pd.DataFrame, customers: pd.DataFrame
) -> pd.DataFrame:
    """A transaction's customer relationship is invalid when either:
    - its ``customer_id`` doesn't exist in ``customers`` at all (orphan
      reference — the actual condition present in this dataset), or
    - the account it ran against belongs to a *different* customer than
      the one recorded on the transaction (ownership mismatch).
    """
    enriched = enrich_with_account_info(transactions, accounts)
    orphan_customer = ~transactions["customer_id"].isin(customers["customer_id"])
    ownership_mismatch = enriched["account_customer_id"].notna() & (
        enriched["customer_id"] != enriched["account_customer_id"]
    )
    invalid = orphan_customer.values | ownership_mismatch.values
    return transactions[invalid]


def find_kyc_high_value(transactions: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    cust_cols = customers[["customer_id", "kyc_status"]]
    enriched = transactions.merge(cust_cols, on="customer_id", how="left")
    mask = (
        enriched["kyc_status"].isin(NON_VERIFIED_KYC)
        & (enriched["transaction_amount"] >= KYC_HIGH_VALUE_THRESHOLD)
    ).values
    return transactions[mask]


def data_quality_summary(datasets: dict[str, pd.DataFrame]) -> dict[str, int]:
    """One-shot count summary for the Data Quality KPI row."""
    tx, accounts, customers = datasets["transactions"], datasets["accounts"], datasets["customers"]
    return {
        "duplicate_transactions": len(find_duplicate_transactions(tx)),
        "negative_amount_transactions": len(find_negative_amounts(tx)),
        "future_dated_transactions": len(find_future_dated(tx)),
        "invalid_currency_transactions": len(find_invalid_currency(tx)),
        "closed_account_transactions": len(find_closed_account_transactions(tx, accounts)),
        "invalid_customer_relationship_transactions": len(
            find_invalid_customer_relationship(tx, accounts, customers)
        ),
        "kyc_high_value_transactions": len(find_kyc_high_value(tx, customers)),
    }
