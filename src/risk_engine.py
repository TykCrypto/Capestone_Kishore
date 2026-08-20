"""Transaction risk scoring.

    Transaction -> Data Quality Rules -> Customer Risk -> Account Risk ->
    Transaction Behaviour -> Anomaly Detection -> Risk Score -> Risk Level

Every rule is a ``(key, weight, reason, predicate)`` tuple in ``RULES``.
Adding a new risk signal means appending to that list (Open/Closed) —
nothing else in this module needs to change. Weights/bands are documented
in ``governance/risk_policy.md`` so the code and the policy can't diverge
silently.
"""

from __future__ import annotations

import pandas as pd

from src import data_cleaner
from src.anomaly_detector import flag_amount_outliers

LOW_MEDIUM_BOUNDARY = 40
MEDIUM_HIGH_BOUNDARY = 70

Predicate = "callable(pd.DataFrame) -> pd.Series[bool]"


def _build_context(
    transactions: pd.DataFrame, accounts: pd.DataFrame, customers: pd.DataFrame
) -> pd.DataFrame:
    ctx = data_cleaner.enrich_with_account_info(transactions, accounts)
    ctx = ctx.merge(
        customers[["customer_id", "risk_category", "kyc_status"]],
        on="customer_id",
        how="left",
    )
    outliers = flag_amount_outliers(transactions)
    ctx = ctx.join(outliers)

    dup_idx = transactions.index.isin(data_cleaner.find_duplicate_transactions(transactions).index)
    neg_idx = transactions.index.isin(data_cleaner.find_negative_amounts(transactions).index)
    future_idx = transactions.index.isin(data_cleaner.find_future_dated(transactions).index)
    currency_idx = transactions.index.isin(data_cleaner.find_invalid_currency(transactions).index)
    closed_idx = transactions.index.isin(
        data_cleaner.find_closed_account_transactions(transactions, accounts).index
    )
    mismatch_idx = transactions.index.isin(
        data_cleaner.find_invalid_customer_relationship(transactions, accounts, customers).index
    )
    kyc_hv_idx = transactions.index.isin(
        data_cleaner.find_kyc_high_value(transactions, customers).index
    )

    ctx["_dup"] = dup_idx
    ctx["_negative"] = neg_idx
    ctx["_future"] = future_idx
    ctx["_bad_currency"] = currency_idx
    ctx["_closed_account"] = closed_idx
    ctx["_customer_mismatch"] = mismatch_idx
    ctx["_kyc_high_value"] = kyc_hv_idx
    return ctx


RULES: list[tuple[str, int, str, "Predicate"]] = [
    ("duplicate_transaction_id", 25, "Duplicate transaction ID detected", lambda c: c["_dup"]),
    ("negative_amount", 30, "Negative transaction amount", lambda c: c["_negative"]),
    ("future_dated", 20, "Transaction dated in the future", lambda c: c["_future"]),
    ("invalid_currency", 10, "Unrecognized or invalid currency code", lambda c: c["_bad_currency"]),
    ("closed_account", 30, "Transaction executed against a closed account", lambda c: c["_closed_account"]),
    (
        "invalid_customer_relationship",
        25,
        "Transaction customer does not match the account owner on record",
        lambda c: c["_customer_mismatch"],
    ),
    (
        "account_dormant_or_blocked",
        20,
        "Account status is DORMANT or BLOCKED",
        lambda c: c["account_status"].isin(["DORMANT", "BLOCKED"]),
    ),
    ("account_frozen", 15, "Account is currently frozen", lambda c: c["freeze_status"] == "Y"),
    (
        "customer_high_risk_category",
        15,
        "Customer flagged as HIGH risk category",
        lambda c: c["risk_category"] == "HIGH",
    ),
    (
        "customer_medium_risk_category",
        5,
        "Customer flagged as MEDIUM risk category",
        lambda c: c["risk_category"] == "MEDIUM",
    ),
    (
        "kyc_not_verified",
        10,
        "Customer KYC status is not verified",
        lambda c: c["kyc_status"].isin(list(data_cleaner.NON_VERIFIED_KYC)),
    ),
    (
        "kyc_high_value_combo",
        15,
        "High-value transaction combined with incomplete KYC verification",
        lambda c: c["_kyc_high_value"],
    ),
    (
        "amount_outlier",
        15,
        "Transaction amount is a statistical outlier for its transaction type",
        lambda c: c["is_amount_outlier"],
    ),
    (
        "currency_mismatch",
        10,
        "Transaction currency differs from the account's registered currency",
        lambda c: c["account_currency"].notna() & (c["currency"] != c["account_currency"]),
    ),
]


def _risk_level(score: int) -> str:
    if score >= MEDIUM_HIGH_BOUNDARY:
        return "HIGH"
    if score >= LOW_MEDIUM_BOUNDARY:
        return "MEDIUM"
    return "LOW"


def score_transactions(
    transactions: pd.DataFrame, accounts: pd.DataFrame, customers: pd.DataFrame
) -> pd.DataFrame:
    """Return ``transactions`` enriched with ``risk_score`` (0-100, capped),
    ``risk_level`` (LOW/MEDIUM/HIGH) and ``risk_reasons`` (list[str] — the
    triggered rules, in evaluation order, so every flag is explainable)."""
    ctx = _build_context(transactions, accounts, customers)

    total = pd.Series(0, index=ctx.index, dtype=int)
    reasons = pd.Series([[] for _ in range(len(ctx))], index=ctx.index)

    for _key, weight, reason, predicate in RULES:
        mask = predicate(ctx).fillna(False)
        total = total.add(mask.astype(int) * weight, fill_value=0)
        for idx in ctx.index[mask]:
            reasons.at[idx].append(reason)

    result = transactions.copy()
    result["risk_score"] = total.clip(upper=100).astype(int)
    result["risk_level"] = result["risk_score"].map(_risk_level)
    result["risk_reasons"] = reasons
    return result


def high_risk_transactions(scored_transactions: pd.DataFrame) -> pd.DataFrame:
    return scored_transactions[scored_transactions["risk_level"] == "HIGH"]
