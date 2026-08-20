---
name: incident_analysis
description: Analyze production incidents, detect SLA breaches, find recurring error patterns, correlate incidents with application/API logs, and identify operational hotspots. Use when asked about incidents, SLA breaches, production stability, or operational risk.
---

# Incident Analysis Skill

Responsible for: `Incidents + Logs -> Root Patterns -> SLA Analysis -> Recommendations`.

## Responsibilities

- Detect SLA breaches: `src/incident_analyzer.sla_breached_incidents` and `sla_breach_rate_by`; cross-check against `recompute_sla_breach` (elapsed time vs. the SLA-hours table in `reference_data.csv`).
- Find recurring error patterns: `src/incident_analyzer.recurring_error_patterns` (grouped by `application_module` + `root_cause`).
- Correlate incidents with logs: `src/incident_analyzer.correlate_with_logs`, joining on `related_transaction_id` against `api_logs`/`application_logs`.
- Identify slow APIs and HTTP failures: `src/api_analyzer.slow_api_logs`, `failed_5xx_logs`, `api_latency_by_name`, `failure_rate_by_api`.
- Identify operational hotspots: `src/incident_analyzer.operational_hotspots` (breach rate by assigned team).

## Rules

- Every correlation must cite the specific incident/log IDs involved — no aggregate claim without traceable evidence.
- Recommendations produced from this analysis go through `src/insights_engine.generate_recommendations`, kept separate from the observed insight text.
