# SLO And Error Budget Automation

The serving project writes `reports/slo_error_budget.json` from canary observability and promotion gates.

It tracks:

- serving availability
- p95 serving latency
- shadow score parity
- challenger traffic coverage
- multi-window burn-rate policy
- rollback or canary-freeze recommendation

Run it locally:

```bash
make demo
make slo-report
```

`kubernetes/slo-alerts.yaml` contains PrometheusRule examples for availability burn and shadow-parity breach, plus a scheduled freeze-sync job.
