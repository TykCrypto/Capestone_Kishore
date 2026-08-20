"""Computes evaluation metrics for both analytical performance and
software quality, and writes ``evaluation/evaluation_report.csv``.

Design choice worth calling out: Accuracy/Precision/Recall/F1/FPR/FNR are
evaluated against the dataset's *seed* ``fraud_flag`` column (an
independent label that ships with the data), not against
``expected_high_risk_transactions.csv`` — comparing the risk engine to a
label it had no part in producing is what makes this a real evaluation
rather than a circular one. Rule Detection Accuracy / Ground-Truth Match
Rate instead compare deterministic detectors (duplicates, SLA breaches,
etc.) against the frozen ``expected_outputs/`` files, which is
appropriate there because those rules are exact, not statistical.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import api_analyzer, data_cleaner, data_loader, incident_analyzer, risk_engine, test_analyzer  # noqa: E402
from src.governance_engine import run_governance_checks  # noqa: E402

EXPECTED_DIR = PROJECT_ROOT / "expected_outputs"
REPORT_PATH = PROJECT_ROOT / "evaluation" / "evaluation_report.csv"

RULE_SPECS = [
    ("duplicate_transaction_ids", "transaction_id", lambda d: data_cleaner.find_duplicate_transactions(d["transactions"])),
    ("negative_amount_transactions", "transaction_id", lambda d: data_cleaner.find_negative_amounts(d["transactions"])),
    ("future_dated_transactions", "transaction_id", lambda d: data_cleaner.find_future_dated(d["transactions"])),
    (
        "closed_account_transactions",
        "transaction_id",
        lambda d: data_cleaner.find_closed_account_transactions(d["transactions"], d["accounts"]),
    ),
    (
        "invalid_customer_relationship_transactions",
        "transaction_id",
        lambda d: data_cleaner.find_invalid_customer_relationship(d["transactions"], d["accounts"], d["customers"]),
    ),
    (
        "kyc_high_value_transactions",
        "transaction_id",
        lambda d: data_cleaner.find_kyc_high_value(d["transactions"], d["customers"]),
    ),
    ("sla_breached_incidents", "incident_id", lambda d: incident_analyzer.sla_breached_incidents(d["incidents"])),
    ("slow_api_logs_over_2000ms", "log_id", lambda d: api_analyzer.slow_api_logs(d["api_logs"])),
    ("failed_api_logs_5xx", "log_id", lambda d: api_analyzer.failed_5xx_logs(d["api_logs"])),
    ("failed_test_cases", "test_case_id", lambda d: test_analyzer.failed_test_cases(d["test_cases"])),
]


def _rule_detection_metrics(datasets: dict[str, pd.DataFrame]) -> tuple[float, float]:
    exact_matches = []
    jaccards = []
    for name, id_col, live_fn in RULE_SPECS:
        live_ids = set(live_fn(datasets)[id_col])
        expected_ids = set(pd.read_csv(EXPECTED_DIR / f"{name}.csv")[id_col])
        union = live_ids | expected_ids
        jaccards.append(len(live_ids & expected_ids) / len(union) if union else 1.0)
        exact_matches.append(live_ids == expected_ids)
    rule_detection_accuracy_pct = sum(exact_matches) / len(exact_matches) * 100
    ground_truth_match_rate_pct = sum(jaccards) / len(jaccards) * 100
    return round(rule_detection_accuracy_pct, 2), round(ground_truth_match_rate_pct, 2)


def _classifier_metrics(scored: pd.DataFrame) -> dict[str, float]:
    y_true = scored["fraud_flag"] == "Y"
    y_pred = scored["risk_level"].isin(["MEDIUM", "HIGH"])

    tp = int((y_true & y_pred).sum())
    fp = int((~y_true & y_pred).sum())
    fn = int((y_true & ~y_pred).sum())
    tn = int((~y_true & ~y_pred).sum())

    accuracy = (tp + tn) / len(scored) * 100
    precision = tp / (tp + fp) * 100 if (tp + fp) else 0.0
    recall = tp / (tp + fn) * 100 if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) * 100 if (fp + tn) else 0.0
    fnr = fn / (fn + tp) * 100 if (fn + tp) else 0.0

    return {
        "accuracy_pct": round(accuracy, 2),
        "precision_pct": round(precision, 2),
        "recall_pct": round(recall, 2),
        "f1_pct": round(f1, 2),
        "false_positive_rate_pct": round(fpr, 2),
        "false_negative_rate_pct": round(fnr, 2),
    }


def _test_pass_rate_pct() -> float:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "--ignore=evaluation"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", result.stdout)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", result.stdout)) else 0
    total = passed + failed
    return round(passed / total * 100, 2) if total else 0.0


def evaluate() -> dict:
    datasets = data_loader.load_all()
    scored = risk_engine.score_transactions(datasets["transactions"], datasets["accounts"], datasets["customers"])

    metrics = _classifier_metrics(scored)
    rule_detection_accuracy_pct, ground_truth_match_rate_pct = _rule_detection_metrics(datasets)
    metrics["rule_detection_accuracy_pct"] = rule_detection_accuracy_pct
    metrics["ground_truth_match_rate_pct"] = ground_truth_match_rate_pct
    metrics["test_pass_rate_pct"] = _test_pass_rate_pct()

    governance_results = run_governance_checks({"datasets": datasets, "scored_transactions": scored})
    metrics["governance_checks_status"] = "PASS" if all(v == "PASS" for v in governance_results.values()) else "FAIL"

    report_rows = [{"metric": k, "value": v} for k, v in metrics.items()]
    pd.DataFrame(report_rows).to_csv(REPORT_PATH, index=False)
    return metrics


if __name__ == "__main__":
    for key, value in evaluate().items():
        print(f"{key}: {value}")
