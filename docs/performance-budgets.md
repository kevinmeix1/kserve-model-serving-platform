# Performance Budgets

This project gates canary progression with a local performance budget report at `.local/reports/performance_budget.json`. The budget joins serving telemetry, traffic split state, and shadow-score parity into a promotion decision.

## What Is Gated

- p95 and p99 online inference latency.
- API error rate.
- Champion/challenger shadow-score delta.
- Challenger traffic share so the canary has real exposure.
- Minimum request volume before promotion.

## Production Mapping

- KServe handles predictor routing, canary rollout, and standardized inference protocol.
- Gateway API weights make promotion and rollback explicit.
- KEDA Prometheus triggers provide event-driven scaling from custom serving signals.
- Prometheus histograms are used for tail latency because averages hide user-visible regressions.
- The CI gate keeps the champion alias unchanged whenever any budget fails.

## Current References

- KServe introduction: <https://kserve.github.io/website/docs/intro>
- KEDA Prometheus scaler: <https://keda.sh/docs/2.20/scalers/prometheus/>
- Kubernetes HorizontalPodAutoscaler: <https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/>
- Prometheus histogram practices: <https://prometheus.io/docs/practices/histograms/>

Run `make performance-budget` after `make demo` to regenerate only this evidence.
