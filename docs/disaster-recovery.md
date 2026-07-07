# Disaster Recovery

This project includes a DR plan for serving state: KServe objects, gateway routes, registry aliases, idempotency cache, and prediction logs.

Run:

```bash
make dr-plan
```

The report is written to `.local/reports/disaster_recovery_plan.json`.

## Restore Order

1. Namespace and serving CRDs.
2. Network and gateway routes.
3. Registry aliases and model artifacts.
4. Idempotency cache.
5. KServe runtime.

Velero handles Kubernetes resources and snapshots; application consistency still needs registry exports and replay validation.
