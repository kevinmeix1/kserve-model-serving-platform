# Airflow Deadline Alerts

`make deadline-alerts-plan` writes `.local/reports/deadline_alert_plan.json`.

## What It Shows

- Airflow 3-style Deadline Alert policies for rollout queue time, shadow warmup, gateway route convergence, and emergency rollback.
- A migration stance away from legacy Airflow 2 SLA callbacks.
- `AIRFLOW__CALLBACKS__CALLBACK_EXECUTION_TIMEOUT=300` so notifier callbacks cannot hang rollout recovery.
- Route-convergence remediation for HTTPRoute accepted conditions, endpoint picker health, and traffic weights.
- Rollback remediation that forces champion traffic and attaches canary evidence.

## Production Notes

Serving rollouts need time-bound alerting for the points where user impact can grow quickly: a queued rollout that never starts, a shadow endpoint that will not warm, a route that does not converge, or a rollback that misses its window. Deadline Alerts turn those time thresholds into explicit operational actions instead of generic task failure noise.
