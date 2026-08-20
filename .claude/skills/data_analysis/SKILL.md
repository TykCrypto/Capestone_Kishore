---
name: data_analysis
description: Load and validate the BFSI datasets, check schemas, handle missing values, detect duplicates, validate dates/relationships, and produce a data-quality summary. Use when asked to load, validate, or clean the banking datasets, or to investigate a data-quality question.
---

# Data Analysis Skill

Responsible for the first stage of the pipeline: `Dataset -> Data Validation`.

## Responsibilities

- Load all datasets via `src/data_loader.load_all()` — this is the only function that should read from `data/` directly.
- Check schemas: confirm expected columns/dtypes exist before any downstream engine runs.
- Handle missing values: report null counts per key column; never silently drop rows without logging why.
- Detect duplicates: `src/data_cleaner.find_duplicate_transactions`.
- Validate dates: `src/data_cleaner.find_future_dated`.
- Validate relationships: `src/data_cleaner.find_closed_account_transactions`, `find_invalid_customer_relationship`.
- Validate currency codes: `src/data_cleaner.find_invalid_currency`.
- Produce a data-quality summary: `src/data_cleaner.data_quality_summary(datasets)`.

## Rules

- Never modify files under `data/` — it is the immutable source of truth (enforced by `.claude/hooks/pre_tool_use.py`).
- Every quality check must return the offending rows (not just a count) so findings are traceable back to source records.
- Reuse `src/data_cleaner.py` functions rather than re-implementing a rule inline — this is the single source of truth other skills (fraud_detection, evaluation) build on.
