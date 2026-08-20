"""Loads the raw BFSI datasets. This is the only module that touches
`data/` directly — every other module receives DataFrames as arguments.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_DATE_COLUMNS = {
    "customers": ["customer_since"],
    "accounts": ["opening_date", "last_transaction_date"],
    "transactions": ["transaction_datetime"],
    "incidents": ["reported_datetime", "resolved_datetime"],
    "api_logs": ["timestamp"],
    "application_logs": ["timestamp"],
    "test_cases": ["last_execution_date"],
    "reference_data": [],
}

DATASET_NAMES = tuple(_DATE_COLUMNS.keys())


def _load_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / f"{name}.csv"
    df = pd.read_csv(path)
    for col in _DATE_COLUMNS.get(name, []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if name == "transactions" and "risk_score" in df.columns:
        # The source dataset ships a seed risk_score — keep it only as a
        # reference signal for evaluation; the app always computes its own
        # via risk_engine.score_transactions (never copies dataset outputs).
        df = df.rename(columns={"risk_score": "seed_risk_score"})
    return df


def load_all() -> dict[str, pd.DataFrame]:
    """Load every dataset once. Callers should cache this (e.g. via
    ``st.cache_data``) rather than calling it repeatedly."""
    return {name: _load_csv(name) for name in DATASET_NAMES}
