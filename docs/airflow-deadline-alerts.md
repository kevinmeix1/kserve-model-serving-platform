# Airflow Deadline Alerts

`make deadline-alerts-plan` writes `.local/reports/deadline_alert_plan.json`.

## What It Shows

- Airflow 3-style Deadline Alert policies for rollout queue time, shadow warmup, gateway route convergence, and emergency rollback.
- A migration stance away from legacy Airflow 2 SLA callbacks.
- `AIRFLOW__CALLBACKS__CALLBACK_EXECUTION_TIMEOUT=300` so notifier callbacks cannot hang rollout recovery.
- Explicit callback contracts with dedupe keys, bounded payload fields, owners, and allowed side effects.
- Route-convergence remediation for HTTPRoute accepted conditions, endpoint picker health, and traffic weights.
- Rollback remediation that forces champion traffic and attaches canary evidence.

## Callback Contract

Each Deadline Alert callback is intentionally narrow. The generated plan records the receiver, owner, retry policy, dedupe key, payload fields, and allowed side effect. A callback may notify, page, open an incident, or request a guarded rollout task, but it must not directly patch KServe resources, Gateway routes, or traffic state.

## Production Notes

Serving rollouts need time-bound alerting for the points where user impact can grow quickly: a queued rollout that never starts, a shadow endpoint that will not warm, a route that does not converge, or a rollback that misses its window. Deadline Alerts turn those time thresholds into explicit operational actions instead of generic task failure noise.
