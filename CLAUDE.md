# Project

**BFSI AI Risk & Incident Intelligence Platform** — an AI-powered banking risk and operational intelligence application built for the Capstone Project: *AI-Powered BFSI Risk & Incident Intelligence Platform*.

# Objective

Analyze banking transactions, customer/account data, production incidents, API logs, application logs, and test results to automatically surface fraud/risk patterns, data-quality issues, production failures, SLA breaches, and operational anomalies — then present AI-generated insights and recommendations through an interactive Streamlit dashboard.

Flow: `Dataset → Data Validation → Risk Detection → Incident Detection → Anomaly Analysis → AI Insights → Recommendations → Dashboard`

The application must always separate observed evidence from suggested action, and must never present an AI risk prediction as a final banking decision:
`AI Recommendation → Human Review → Final Decision`

# Dataset

Synthetic banking environment in `data/` (already provided — treat as read-only source of truth):

| File | Rows (approx.) |
|---|---|
| `customers.csv` | 10,000 |
| `accounts.csv` | 15,000 |
| `transactions.csv` | 25,000 |
| `incidents.csv` | 10,000 |
| `api_logs.csv` | 15,000 |
| `application_logs.csv` | 20,000 |
| `test_cases.csv` | 5,000 |
| `reference_data.csv` | branch/error-code/SLA reference |

The data intentionally contains real-world quality problems: duplicate transactions, negative amounts, future-dated transactions, invalid customer relationships, transactions on closed accounts, KYC risk, SLA breaches, slow APIs, HTTP 5xx failures, and failed test cases. `expected_outputs/*.csv` (ground truth) and `docs/01_Data_Dictionary_and_Ground_Truth.xlsx` are the reference for correctness — every detector must be checkable against them.

# Required Project Structure

```
├── CLAUDE.md, README.md, requirements.txt, app.py
├── data/                  # raw source CSVs — never modify in place
├── docs/                  # data dictionary & ground truth
├── expected_outputs/      # ground-truth CSVs used for evaluation
├── src/                   # data_loader, data_cleaner, risk_engine, anomaly_detector,
│                          # incident_analyzer, api_analyzer, test_analyzer,
│                          # insights_engine, governance_engine
├── .claude/
│   ├── skills/            # data_analysis, fraud_detection, incident_analysis, evaluation
│   ├── agents/            # data_agent, risk_agent, incident_agent, testing_agent, governance_agent
│   └── hooks/             # pre_tool_use, post_tool_use, governance_check, evaluation_check
├── governance/            # governance_rules.md, risk_policy.md, audit_log.csv
├── tests/                 # pytest suite per module
└── evaluation/            # test_set.csv, evaluation_metrics.py, evaluation_report.csv
```

# Core Tasks

1. Load and validate all datasets.
2. Detect data-quality problems.
3. Detect suspicious banking transactions.
4. Calculate transaction risk scores.
5. Detect SLA breaches.
6. Detect slow APIs and HTTP failures.
7. Analyze failed test cases.
8. Generate insights and recommendations.
9. Display results using Streamlit.
10. Maintain governance and auditability.

# Development Principles

Follow **DRY, KISS, and SOLID** as non-negotiable defaults, not aspirations:

- **DRY** — one canonical implementation per rule/metric. Shared logic (data loading, date/currency parsing, risk-band thresholds, KPI aggregation) lives in `src/` and is imported everywhere, including tests and Streamlit pages. Never recompute or hand-copy a detection rule between a `src/` module and a dashboard page.
- **KISS** — prefer explicit rule-based logic and readable pandas/NumPy over clever one-liners or unnecessary ML complexity. Only introduce a statistical/ML anomaly technique (e.g. z-score, IQR, isolation forest) where a simple threshold rule genuinely cannot express the pattern — and document why.
- **SOLID**, applied to Python modules/classes rather than as ceremony:
  - *Single Responsibility* — each `src/` module owns one concern (`data_loader.py` loads, `data_cleaner.py` cleans, `risk_engine.py` scores — no module reaches across concerns).
  - *Open/Closed* — new risk rules or detectors are added by extending a rule registry/strategy list, not by editing existing rule functions.
  - *Liskov Substitution* — any detector/analyzer implementing a shared interface (e.g. `.run(df) -> DataFrame`) must be swappable without breaking callers.
  - *Interface Segregation* — Streamlit pages depend on narrow, purpose-built functions from `src/` (e.g. `get_high_risk_transactions()`), never on entire engine internals.
  - *Dependency Inversion* — engines and analyzers depend on abstractions (a `DataSource` / config), not on hard-coded file paths or Streamlit session state.

Additional rules:
- Do not hard-code dataset outputs, KPI numbers, or evaluation scores — always calculate them from the actual data at runtime.
- Preserve original source data in `data/`; write intermediate/cleaned data elsewhere if persisted at all.
- Log important processing actions (rows dropped, rules triggered, errors) via the governance/audit logging path.
- Validate data before analysis; never let a detector silently run on malformed input.
- Explain every risk flag with the specific reasons that triggered it (see Risk Engine below).
- Never expose sensitive customer information unnecessarily — mask/redact PII in UI and logs by default.
- Write pytest tests for every critical business rule, and compare results against `expected_outputs/` ground truth.

# UI Theme — Cognizant-Inspired Branding

Style the Streamlit application with a professional, Cognizant-inspired enterprise theme (approximate corporate palette — not official trademarked assets, adjust if exact brand guidelines are provided later):

- **Primary (Cognizant Blue):** `#0033A0` — headers, primary buttons, active nav, KPI card accents.
- **Secondary/Accent (Cognizant Cyan):** `#00A9E0` — links, chart highlight series, hover states, progress indicators.
- **Dark Navy (text/emphasis):** `#001B4D` — headings, sidebar background.
- **Neutral background:** `#F5F7FA` (light) with white (`#FFFFFF`) content cards.
- **Status colors:** Low risk `#2E7D32` (green), Medium risk `#F9A825` (amber), High risk `#C62828` (red) — reserved strictly for risk/severity indicators, not decorative use.
- Use a clean sans-serif font stack (e.g. `"Segoe UI", Roboto, sans-serif`), generous white space, card-based KPI tiles, and a persistent sidebar for navigation across all sections.
- Centralize theme constants (hex codes, font stack) in one config/module — do not repeat hex values inline across pages (DRY).

# Claude Code Skills (`.claude/skills/`)

- **data_analysis** — load datasets, check schemas, handle missing values, detect duplicates, validate dates/relationships, produce a data-quality summary.
- **fraud_detection** — identify suspicious transactions, generate risk features, detect abnormal behavior, calculate risk score, explain every flag.
- **incident_analysis** — analyze incidents, detect SLA breaches, find recurring error patterns, correlate with API/application logs, identify operational hotspots.
- **evaluation** — compare predictions with ground truth, calculate evaluation metrics, generate the evaluation report, flag regressions.

# Subagents (`.claude/agents/`)

- **data_agent** — Data Loading → Validation → Cleaning → Quality Report.
- **risk_agent** — Transactions → Risk Features → Risk Score → Fraud Flags.
- **incident_agent** — Incidents + Logs → Root Patterns → SLA Analysis → Recommendations.
- **testing_agent** — Unit Tests → Business Rule Tests → Regression Tests.
- **governance_agent** — Privacy → Explainability → Audit → Compliance Checks.

# Hooks (`.claude/hooks/`)

- **pre_tool_use** — validate input paths, prevent accidental modification of raw datasets, check for sensitive-data exposure, validate allowed operations.
- **post_tool_use** — record execution status, capture errors and files modified, update audit logs.
- **governance_check** — verify data privacy, PII exposure, risk-score explainability, dataset integrity, audit logging, responsible-AI rules.
- **evaluation_check** — whenever analytical logic changes: run tests, compare with ground truth, calculate evaluation metrics, record pass/fail.

# Risk Engine

```
Transaction → Data Quality Rules → Customer Risk → Account Risk →
Transaction Behaviour → Anomaly Detection → Risk Score → Low/Medium/High
```

Every flagged transaction must return a structured, explainable result, e.g.:

```
Transaction ID: TX12345
Risk Score: 87/100
Risk Level: HIGH
Reasons:
- High transaction amount
- Customer KYC risk
- Unusual transaction behaviour
- Closed account activity
```

# Streamlit Application Sections

Executive Dashboard · Transaction Analytics · Fraud & Risk Detection · Customer & Account Risk · Data Quality · Production Incidents · API Monitoring · Application Logs · Test Quality · AI Insights · Recommendations · Governance · Evaluation Results.

**KPIs:** Total Customers, Total Accounts, Total Transactions, High-Risk Transactions, Duplicate Transactions, Invalid Transactions, Closed Account Transactions, Total Incidents, SLA Breaches, API Failures, Slow APIs, Failed Test Cases — always computed from live data, with supporting charts/filters (Plotly).

# AI Insights & Recommendations

Insights must be data-supported statements (e.g. "High-risk transactions are concentrated in specific customer/account segments"). Recommendations must be clearly separated as suggested actions (e.g. "Prioritize investigation of high-risk transactions"), never phrased as decisions already made.

# Governance

Maintain a Governance dashboard covering: Data Privacy, Data Integrity, Explainability, Bias, Security, Auditability, Human Oversight, Reliability, Traceability. Every insight must be traceable back to source data, and every high-risk finding must route through human review before any action is taken.

# Testing & Evaluation

- `tests/` — pytest coverage for data quality, transactions, risk engine, incidents, API analysis.
- `evaluation/test_set.csv` — cases derived from ground truth (duplicate, negative amount, future-dated, invalid currency, closed account, invalid customer relationship, KYC/high-value, high-risk, SLA breach, slow API, HTTP 5xx, failed test case).
- `evaluation/evaluation_metrics.py` — compute Accuracy, Precision, Recall, F1, False Positive Rate, False Negative Rate, Test Pass Rate, Rule Detection Accuracy, Ground-Truth Match Rate — all calculated, never hard-coded.

# Local Deployment

```
pip install -r requirements.txt
streamlit run app.py
```

Verify the app starts cleanly and every dashboard section loads without runtime errors at `http://localhost:8501` before considering a change complete.
