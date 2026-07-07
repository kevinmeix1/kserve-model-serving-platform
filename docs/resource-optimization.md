# Resource Optimization

This layer adds right-sizing and autoscaling guardrails for online inference. The recommendations are generated locally, while the Kubernetes manifest models the production controls: VPA recommendation mode, HPA behavior policy, Prometheus alerts, and Airflow pool sizing.

Run:

```bash
make optimize-resources
```

The report is written to `.local/reports/resource_optimization.json`.

## Decisions

- Keep VPA in `Off` mode during rollout windows so request changes are reviewed.
- Use fast HPA scale-up and slow scale-down to protect latency while reducing replica flapping.
- Separate canary analysis, smoke tests, and rollback checks into different Airflow pools.
- Treat CPU throttling as a canary gate input, not just an infrastructure metric.

## References

Kubernetes resource requests drive scheduling, VPA provides recommendation bounds through its CRD status, HPA behavior policies reduce flapping through stabilization windows, and Airflow pools protect scarce systems from too much concurrent work.
