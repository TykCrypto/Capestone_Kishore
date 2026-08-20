# Governance Rules

Nine governance areas are checked by `src/governance_engine.run_governance_checks`
and shown on the Streamlit Governance page. Every status is computed from
a real condition — none is hard-coded.

| Area | Required Check | How it's computed |
|---|---|---|
| Data Privacy | Protect customer information | Sample `customer_name` values are passed through `mask_pii` and verified to actually differ from the original — PASS only if every sampled name was redacted. |
| Data Integrity | Verify source files | Key ID columns (`customer_id`, `account_id`, `transaction_id`, `incident_id`) must contain no nulls across the loaded datasets. |
| Explainability | Explain risk flags | Every transaction with `risk_level == HIGH` must have a non-empty `risk_reasons` list. |
| Bias | Review risk scoring across groups | Average `risk_score` per `customer_segment` must not spread by more than 40 points — a large spread requires human review before it's treated as PASS. |
| Security | Validate inputs | `.claude/hooks/pre_tool_use.py` must exist and be wired into `.claude/settings.json` (PreToolUse validation is active). |
| Auditability | Log important actions | `governance/audit_log.csv` must exist (created/appended by `append_audit_log`). |
| Human Oversight | Human review for high-risk findings | No `final_decision`/`approved`/`declined` column may exist on the scored transactions — the app never auto-decides. |
| Reliability | Test critical rules | The latest `evaluation/evaluation_report.csv` must show `test_pass_rate_pct >= 90`. |
| Traceability | Map insight back to source data | Scored transactions must retain a non-null `transaction_id` linking every finding back to its source row. |

## Human oversight boundary

`AI Recommendation -> Human Review -> Final Decision`

This application never presents an AI risk prediction as a final banking
decision. Every HIGH-risk finding and every recommendation is framed as
a suggested action for a human reviewer, never as an action already taken.
