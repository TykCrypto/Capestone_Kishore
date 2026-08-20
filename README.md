# BFSI AI Risk & Incident Intelligence Platform

An AI-powered banking risk and operational intelligence application built for the Capstone Project: *AI-Powered BFSI Risk & Incident Intelligence Platform*. It analyzes banking transactions, customer/account data, production incidents, API logs, application logs, and test results to surface fraud/risk patterns, data-quality issues, production failures, SLA breaches, and operational anomalies — then presents AI-generated insights and recommendations through an interactive, Cognizant-themed Streamlit dashboard.

## Problem Statement

Banks generate large volumes of transactional and operational data across systems that are rarely analyzed together: transactions, accounts, customers, production incidents, API logs, application logs, and test results. Left siloed, this data hides fraud patterns, data-quality defects, SLA breaches, and reliability regressions until they cause customer or financial impact. This platform unifies all seven data sources into one explainable pipeline that flags risk, explains every flag, and routes findings to human reviewers rather than automating banking decisions.

## Dataset Description

Synthetic banking environment in `data/` (read-only source of truth):

| File | Rows (approx.) | Contents |
|---|---|---|
| `customers.csv` | 10,000 | Demographics, risk category, KYC status |
| `accounts.csv` | 15,000 | Account type/status, balances, freeze status |
| `transactions.csv` | 25,000 | Amount, currency, channel, seed `fraud_flag`/`risk_score` |
| `incidents.csv` | 10,000 | Severity, SLA breach flag, root cause, related transaction |
| `api_logs.csv` | 15,000 | Response time/code, endpoint, environment |
| `application_logs.csv` | 20,000 | Log level, error code, module |
| `test_cases.csv` | 5,000 | Execution status, automation status, module |
| `reference_data.csv` | — | Branch/error-code/SLA-hour reference values |

The data intentionally contains real-world quality problems: duplicate transactions, negative amounts, future-dated transactions, invalid customer relationships, transactions on closed accounts, KYC risk, SLA breaches, slow APIs, HTTP 5xx failures, and failed test cases.

## Architecture

```
Dataset → Data Validation → Risk Detection → Incident Detection →
Anomaly Analysis → AI Insights → Recommendations → Dashboard
```

Every AI-surfaced finding is a **recommendation**, never a decision:

```
AI Recommendation → Human Review → Final Decision
```

`app.py` is a thin Streamlit composition layer. It never recomputes a rule — every number and chart is produced once by a `src/` engine and passed through a single `context` dict to render functions, the insights engine, and the governance engine.

## Project Structure

```
├── CLAUDE.md, README.md, requirements.txt, app.py
├── data/                  # raw source CSVs — never modified in place
├── docs/                  # data dictionary & ground-truth rule definitions
├── expected_outputs/      # frozen ground-truth CSVs used for testing/evaluation
├── src/                   # data_loader, data_cleaner, risk_engine, anomaly_detector,
│                          # incident_analyzer, api_analyzer, test_analyzer,
│                          # insights_engine, governance_engine, observability_engine, theme
├── .streamlit/config.toml # Cognizant-themed native Streamlit theme
├── .claude/
│   ├── skills/            # data_analysis, fraud_detection, incident_analysis, evaluation
│   ├── agents/            # data_agent, risk_agent, incident_agent, testing_agent, governance_agent
│   ├── hooks/             # pre_tool_use, post_tool_use, governance_check, evaluation_check
│   └── settings.json      # wires the hooks above into PreToolUse/PostToolUse
├── governance/            # governance_rules.md, risk_policy.md, audit_log.csv
├── tests/                 # pytest suite per module
├── evaluation/            # test_set.csv, evaluation_metrics.py, evaluation_report.csv
└── conftest.py            # empty — puts the project root on sys.path for pytest
```

## Installation

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
streamlit run app.py
```

Open **http://localhost:8501**. The sidebar lets you navigate all 14 sections: Executive Dashboard, Transaction Analytics, Fraud & Risk Detection, Customer & Account Risk, Data Quality, Production Incidents, API Monitoring, Application Logs, Test Quality, AI Insights, Recommendations, Governance, Observability & Traceability, and Evaluation Results.

This deployment is **local-only** — no code is pushed to a remote repository and no public tunnel/cloud deployment is created.

## Risk Detection Logic

```
Transaction → Data Quality Rules → Customer Risk → Account Risk →
Transaction Behaviour → Anomaly Detection → Risk Score → Low/Medium/High
```

`src/risk_engine.py` scores every transaction with a registry of 14 weighted rules (`RULES`, an Open/Closed list — new signals are added by appending, never by editing existing predicates). Scores are summed and capped at 100:

| Score | Level |
|---|---|
| 0–39 | LOW |
| 40–69 | MEDIUM |
| ≥ 70 | HIGH |

Every flagged transaction carries a `risk_reasons` list explaining exactly which rules fired, e.g.:

```
Transaction ID: TX12345
Risk Score: 87/100
Risk Level: HIGH
Reasons:
- Closed account activity
- Customer flagged as HIGH risk category
- Transaction amount is a statistical outlier for its transaction type
```

Full rule weights and thresholds are documented in [`governance/risk_policy.md`](governance/risk_policy.md) and must never diverge from `src/risk_engine.py`.

Anomaly detection (`src/anomaly_detector.py`) uses the IQR method per `transaction_type` (global fallback for small groups) rather than a black-box ML model — a deliberate KISS choice, since a simple statistical rule already expresses "unusual amount for this transaction type" without added opacity.

## Claude Code Skills (`.claude/skills/`)

- **data_analysis** — load datasets, check schemas, detect duplicates/missing values, validate dates/relationships, produce the data-quality summary.
- **fraud_detection** — identify suspicious transactions, generate risk features, calculate risk score, explain every flag.
- **incident_analysis** — detect SLA breaches, find recurring error patterns, correlate with API/application logs, identify operational hotspots.
- **evaluation** — compare predictions with ground truth, calculate evaluation metrics, generate the evaluation report, flag regressions.

## Subagents (`.claude/agents/`)

- **data_agent** — Data Loading → Validation → Cleaning → Quality Report.
- **risk_agent** — Transactions → Risk Features → Risk Score → Fraud Flags.
- **incident_agent** — Incidents + Logs → Root Patterns → SLA Analysis → Recommendations.
- **testing_agent** — Unit Tests → Business Rule Tests → Regression Tests.
- **governance_agent** — Privacy → Explainability → Audit → Compliance Checks.

## Hooks (`.claude/hooks/`)

- **pre_tool_use** — blocks Write/Edit/MultiEdit/NotebookEdit/Bash operations that would modify `data/`, edit `governance/audit_log.csv` directly, touch secret-looking paths, or run destructive Bash against the raw datasets.
- **post_tool_use** — appends an audit-log row for every Write/Edit/MultiEdit.
- **governance_check** — runs `governance_engine.run_governance_checks` and fails the hook (exit 2) if any of the 9 governance areas fail, when the edited path touches `src/`.
- **evaluation_check** — runs `evaluation.evaluation_metrics.evaluate()` (tests + ground-truth comparison + metrics) and fails the hook if `test_pass_rate_pct < 90`.

Wired via `.claude/settings.json` under `PreToolUse`/`PostToolUse`.

## Governance

The Governance dashboard evaluates 9 areas, each from a real computed condition (never hard-coded):

| Area | Check |
|---|---|
| Data Privacy | Customer PII (name, IP) is masked before display |
| Data Integrity | No null primary keys across core tables |
| Explainability | Every HIGH-risk transaction has ≥1 `risk_reasons` entry |
| Bias | Mean risk score doesn't vary >40 points across customer segments |
| Security | The path/Bash guard hook (`pre_tool_use.py`) is present |
| Auditability | `governance/audit_log.csv` exists and is being written to |
| Human Oversight | No automated `final_decision`/`approved`/`declined` column exists — findings stay recommendations |
| Reliability | Latest `evaluation/evaluation_report.csv` shows `test_pass_rate_pct` ≥ 90% |
| Traceability | Every scored transaction retains its source `transaction_id` |

Full definitions: [`governance/governance_rules.md`](governance/governance_rules.md). Weights/thresholds: [`governance/risk_policy.md`](governance/risk_policy.md).

**AI Recommendation → Human Review → Final Decision** — no insight, score, or recommendation in this application is ever presented as, or automatically converted into, a final banking action.

## Observability & Traceability

The Governance page's `Auditability` and `Traceability` rows report a single PASS/FAIL. The **Observability & Traceability** dashboard page shows the underlying evidence those two checks are based on, computed by `src/observability_engine.py` (reads/analyzes only — `governance_engine` remains the sole audit-log writer and policy checker):

- **Pipeline observability** — KPIs (datasets loaded, total source rows, high-risk flags, audit events logged, audit error/fail events, last audit event) plus an audit-actions-by-type chart and an audit-events-over-time chart, all read live from `governance/audit_log.csv` (the same file the `pre_tool_use`/`post_tool_use`/`governance_check`/`evaluation_check` hooks write to).
- **Traceability lookup** — enter any `transaction_id` or `incident_id` and trace it end-to-end: the source transaction/customer/account rows (PII-masked via `governance_engine.mask_pii`), its `risk_score`/`risk_level`/`risk_reasons` from the risk engine, any incident linked via `related_transaction_id`, and matching `api_logs`/`application_logs` row counts. Every lookup itself is appended to the audit log (`traceability_lookup`), so using the tool is itself auditable.

## Testing

```bash
pytest -q
```

`tests/` covers every data-quality rule, the risk engine's scoring bands and ground-truth match, incident SLA logic, and API log analysis — asserting against the frozen ground truth in `expected_outputs/` plus hand-built edge cases (e.g. a synthetic clean transaction, a synthetic negative-amount transaction).

## Evaluation

```bash
python -m evaluation.evaluation_metrics
```

Computes and writes `evaluation/evaluation_report.csv`:

- **Accuracy / Precision / Recall / F1 / False Positive Rate / False Negative Rate** — the risk engine's `risk_level` (MEDIUM/HIGH vs LOW) evaluated against the dataset's independent seed `fraud_flag` column. This is deliberately *not* compared against `expected_outputs/expected_high_risk_transactions.csv`, since that file was generated by the same rule logic being evaluated — comparing against it would be circular. Low precision/recall here is expected and acceptable: the risk engine is designed to surface a *broader* set of compliance/data-quality/behavioural concerns than the narrow synthetic fraud label captures, by design.
- **Rule Detection Accuracy / Ground-Truth Match Rate** — deterministic detectors (duplicates, SLA breaches, slow APIs, etc.) compared exactly against the frozen `expected_outputs/` ground truth. These are the metrics that should sit at 100%.
- **Test Pass Rate** — parsed from a live `pytest` run.
- **Governance Checks Status** — PASS only if all 9 governance areas pass.

`evaluation/test_set.csv` lists concrete `test_id,input_condition,expected_result` cases sampled from `expected_outputs/`.

### Ground truth

No ground-truth pack was supplied with the dataset. `expected_outputs/*.csv` was generated once by applying each rule's literal definition (see [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md)) directly against `data/`, then frozen — the same role a supplied ground-truth pack would play. It is never regenerated by the code path it's used to test.

## Local Deployment

```bash
pip install -r requirements.txt
streamlit run app.py
```

Verified: the app starts cleanly and all 14 dashboard sections render without runtime errors at **http://localhost:8501**.
