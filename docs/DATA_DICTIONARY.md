# Data Dictionary & Ground Truth

(Markdown in place of `01_Data_Dictionary_and_Ground_Truth.xlsx` — same
content, easier to keep in sync with the code that implements it.)

## customers.csv (10,000 rows)
`customer_id, customer_name, customer_segment (RETAIL/PREMIUM/SME/CORPORATE), age_group, city, state, occupation, annual_income_inr, risk_category (LOW/MEDIUM/HIGH), kyc_status (VERIFIED/PENDING/REJECTED/EXPIRED), customer_since, customer_status (ACTIVE/DORMANT/BLOCKED/CLOSED)`

## accounts.csv (15,000 rows)
`account_id, customer_id, account_type (SAVINGS/CURRENT/SALARY/FIXED_DEPOSIT), branch_code, opening_date, current_balance, available_balance, currency (INR/USD/EUR/GBP), account_status (ACTIVE/DORMANT/CLOSED/BLOCKED), freeze_status (Y/N), last_transaction_date`

## transactions.csv (25,000 rows)
`transaction_id, account_id, customer_id, transaction_datetime, transaction_type, transaction_channel, transaction_amount, currency, beneficiary_id, source_location, destination_location, device_id, ip_address, transaction_status, failure_reason, settlement_status, fraud_flag (seed label, Y/N), risk_score (seed value — loaded as `seed_risk_score`, kept only as an evaluation reference; the app always computes its own via `risk_engine`)`

## incidents.csv (10,000 rows)
`incident_id, incident_title, application_module, severity (SEV1-4), priority (P1-4), reported_datetime, environment, incident_status, assigned_team, assigned_engineer, root_cause, resolution_summary, resolved_datetime, sla_hours, sla_breached (Y/N), related_transaction_id, related_release_id`

## api_logs.csv (15,000 rows)
`log_id, timestamp, api_name, endpoint, request_method, response_code, response_time_ms, request_size_bytes, response_size_bytes, server_name, environment, error_code, timeout_flag, transaction_id`

## application_logs.csv (20,000 rows)
`log_id, timestamp, log_level (INFO/WARN/ERROR/DEBUG/FATAL), application_module, service_name, server_name, error_code, error_message, stack_trace, user_id, transaction_id, correlation_id`

## test_cases.csv (5,000 rows)
`test_case_id, test_module, test_scenario, test_type, priority, expected_result, automation_status (AUTOMATED/MANUAL/CANDIDATE), last_execution_date, execution_status (PASS/FAIL/NOT_RUN/BLOCKED), failure_reason, execution_time_seconds, defect_id`

## reference_data.csv
`reference_type, code, description, attribute_1, attribute_2` — covers `BRANCH`, `TRANSACTION_TYPE`, `CHANNEL`, `ERROR_CODE`, `SLA_RULE` (severity → resolution-hour SLA), `APPLICATION_MODULE`.

## Ground-truth rule definitions (`expected_outputs/*.csv`)

These were generated once by applying the literal rule below to the data
in `data/` — no supplied ground-truth pack shipped with this project, so
this *is* the ground truth (regenerate only if the rule definition or the
source data changes; never regenerate from the same detector being
evaluated against it).

| File | Rule |
|---|---|
| `negative_amount_transactions.csv` | `transaction_amount < 0` |
| `future_dated_transactions.csv` | `transaction_datetime > now()` |
| `duplicate_transaction_ids.csv` | `transaction_id` appears more than once |
| `closed_account_transactions.csv` | transaction's account has `account_status == CLOSED` |
| `invalid_customer_relationship_transactions.csv` | transaction's `customer_id` doesn't exist in `customers.csv`, or belongs to a different customer than the account's owner |
| `kyc_high_value_transactions.csv` | customer `kyc_status` in `{PENDING, REJECTED, EXPIRED}` **and** `transaction_amount >= 100,000` |
| `expected_high_risk_transactions.csv` | `risk_engine.score_transactions(...)` result with `risk_level == HIGH` |
| `sla_breached_incidents.csv` | `incidents.sla_breached == 'Y'` |
| `slow_api_logs_over_2000ms.csv` | `api_logs.response_time_ms > 2000` |
| `failed_api_logs_5xx.csv` | `api_logs.response_code` in `500-599` |
| `failed_test_cases.csv` | `test_cases.execution_status == 'FAIL'` |
