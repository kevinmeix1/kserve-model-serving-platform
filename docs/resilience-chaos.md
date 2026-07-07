# Resilience and Chaos Drills

The serving platform now includes bounded Chaos Mesh experiments for progressive delivery. Each drill is mapped to a serving control: rollback, traffic hold, Kueue admission, or canary analysis.

## Drills

- `challenger_runtime_kill`: kills one challenger predictor and expects champion traffic to stay healthy.
- `gateway_latency`: injects gateway latency and expects the rollout planner to hold traffic based on p95 latency and error confidence bounds.
- `canary_analysis_cpu_pressure`: adds CPU pressure to analysis jobs and expects Kueue to protect online serving capacity.

Run the local evidence generator:

```bash
make chaos-drill
```

Apply the cluster experiments after installing Chaos Mesh:

```bash
kubectl apply -f kubernetes/chaos-experiments.yaml
```

## Production Notes

- Drill only a challenger or a narrow route during business hours; keep champion-serving blast radius out of routine tests.
- Tie every experiment to a rollback, hold, or promote decision.
- Use scheduled experiments with `concurrencyPolicy: Forbid` and keep history for post-incident review.
- Store latency, route weights, model version, and rollback evidence in the same run artifact.

References: Chaos Mesh provides pod, network, stress, and scheduled experiments; Kubernetes disruption controls and KServe readiness gates keep experiments reviewable.
