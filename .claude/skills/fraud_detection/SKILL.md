---
name: fraud_detection
description: Identify suspicious transactions, generate risk features, detect abnormal transaction behaviour, calculate an explainable risk score, and state why each transaction was flagged. Use when asked about fraud, suspicious transactions, or transaction risk scoring.
---

# Fraud Detection Skill

Responsible for: `Transactions -> Risk Features -> Risk Score -> Fraud Flags`.

## Responsibilities

- Identify suspicious transactions using `src/risk_engine.score_transactions(transactions, accounts, customers)`.
- Generate risk features by combining data-quality flags (`src/data_cleaner.py`), customer/account risk attributes, and behavioural signals (`src/anomaly_detector.flag_amount_outliers`).
- Calculate a 0-100 `risk_score` and a `risk_level` (LOW/MEDIUM/HIGH) per transaction — weights and bands are documented in `governance/risk_policy.md`.
- Explain why a transaction was flagged: every row carries `risk_reasons` (a list of the specific rules that fired). Never present a risk score without its reasons.

## Rules

- Add new risk signals by appending a `(key, weight, reason, predicate)` tuple to `RULES` in `src/risk_engine.py` — do not edit existing rule predicates to add a new pattern (Open/Closed).
- Never hard-code a risk score or fraud flag; always compute from the current data.
- A HIGH risk score is a flag for human review, never an automatic fraud determination or account action.
