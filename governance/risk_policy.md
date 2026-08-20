# Risk Scoring Policy

This is the documented policy behind `src/risk_engine.py`. If the two ever
disagree, the code is the bug — update the code and this file together.

## Pipeline

```
Transaction -> Data Quality Rules -> Customer Risk -> Account Risk ->
Transaction Behaviour -> Anomaly Detection -> Risk Score -> Risk Level
```

## Rule weights

| Rule | Weight | Category |
|---|---|---|
| Duplicate transaction ID | 25 | Data quality |
| Negative transaction amount | 30 | Data quality |
| Future-dated transaction | 20 | Data quality |
| Invalid/unrecognized currency code | 10 | Data quality |
| Closed-account transaction | 30 | Data quality |
| Invalid customer relationship | 25 | Data quality |
| Account DORMANT or BLOCKED | 20 | Account risk |
| Account frozen | 15 | Account risk |
| Customer risk category = HIGH | 15 | Customer risk |
| Customer risk category = MEDIUM | 5 | Customer risk |
| Customer KYC not verified | 10 | Customer risk |
| High-value transaction + incomplete KYC | 15 | Customer risk (combo) |
| Transaction amount is an IQR outlier for its type | 15 | Behaviour / anomaly |
| Transaction currency ≠ account's registered currency | 10 | Behaviour |

Scores from triggered rules are summed and capped at 100. "High-value" for
the KYC combo rule is defined as **≥ ₹100,000** (`KYC_HIGH_VALUE_THRESHOLD`
in `src/data_cleaner.py`) — a round, policy-explainable threshold rather
than a purely statistical percentile.

## Risk bands

| Score | Level |
|---|---|
| 0–39 | LOW |
| 40–69 | MEDIUM |
| ≥ 70 | HIGH |

## Governance boundary

A HIGH risk_level is a signal for human review — it is never displayed,
stored, or treated as an approval/decline decision. See
`governance/governance_rules.md` for the full Human Oversight rule.

## Evaluation pass thresholds

`governance_engine._check_reliability` treats the Reliability governance
area as PASS only when the most recent `evaluation/evaluation_report.csv`
records a `test_pass_rate_pct` of at least **90%**.
