---
name: evaluation
description: Compare predicted/detected results against ground truth, calculate evaluation metrics (accuracy, precision, recall, F1, etc.), generate the evaluation report, and flag regressions. Use when asked to evaluate detection quality, run the test set, or check for regressions.
---

# Evaluation Skill

## Responsibilities

- Compare predicted results with ground truth: `evaluation/evaluation_metrics.py` diffs each `src/` detector's live output against the frozen files in `expected_outputs/`.
- Calculate evaluation metrics: Accuracy, Precision, Recall, F1, False Positive Rate, False Negative Rate, Test Pass Rate, Rule Detection Accuracy, Ground-Truth Match Rate — via `evaluation.evaluation_metrics.evaluate()`.
- Generate the evaluation report: `evaluate()` writes `evaluation/evaluation_report.csv`.
- Flag regressions: a metric that drops below its previous recorded value (or below the pass thresholds in `governance/risk_policy.md`) should be surfaced, not silently overwritten.

## Rules

- `expected_outputs/*.csv` is the ground truth — never regenerate it from the same code path being evaluated, or the evaluation becomes circular. It was generated once from the literal rule definitions in the requirements doc and should only change if the source data or the documented rule definitions change.
- Metrics are always calculated from actual comparisons; no metric value is ever hard-coded into the dashboard or report.
- This skill is also invoked by `.claude/hooks/evaluation_check.py` whenever analytical logic under `src/` changes.
