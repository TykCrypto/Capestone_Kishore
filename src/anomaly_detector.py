"""Statistical anomaly detection.

Kept generic (input/output are plain Series/DataFrames) so any future
detector can reuse ``flag_amount_outliers`` without touching risk_engine.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

IQR_MULTIPLIER = 1.5


def _iqr_bounds(values: pd.Series) -> tuple[float, float]:
    q1, q3 = values.quantile(0.25), values.quantile(0.75)
    iqr = q3 - q1
    return q1 - IQR_MULTIPLIER * iqr, q3 + IQR_MULTIPLIER * iqr


def flag_amount_outliers(transactions: pd.DataFrame) -> pd.DataFrame:
    """Flag transactions whose amount is an IQR outlier within its own
    ``transaction_type`` group (falls back to the global distribution for
    groups too small to have a meaningful IQR).

    Returns a DataFrame indexed like ``transactions`` with columns
    ``is_amount_outlier`` (bool) and ``amount_deviation`` (float, multiples
    of the group's IQR beyond the nearer bound).
    """
    amounts = transactions["transaction_amount"]
    global_low, global_high = _iqr_bounds(amounts)

    is_outlier = pd.Series(False, index=transactions.index)
    deviation = pd.Series(0.0, index=transactions.index)

    for _, group in transactions.groupby("transaction_type"):
        idx = group.index
        values = group["transaction_amount"]
        if len(values) >= 20:
            low, high = _iqr_bounds(values)
        else:
            low, high = global_low, global_high
        span = max(high - low, 1e-9)
        below = values < low
        above = values > high
        is_outlier.loc[idx] = (below | above)
        deviation.loc[idx] = np.where(
            below, (low - values) / span, np.where(above, (values - high) / span, 0.0)
        )

    return pd.DataFrame({"is_amount_outlier": is_outlier, "amount_deviation": deviation})
