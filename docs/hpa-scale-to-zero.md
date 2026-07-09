# HPA Scale To Zero

`make hpa-scale-zero` writes `.local/reports/hpa_scale_to_zero_plan.json`.

## What It Shows

- Kubernetes v1.36 `HPAScaleToZero` as an alpha, disabled-by-default feature gate.
- `autoscaling/v2` HorizontalPodAutoscaler objects with `minReplicas: 0`.
- Object and External metric wakeups for shadow replay, async explainers, and route-conformance probes.
- Protected router, champion predictor, and rollback controller replica floors.
- Cold-start alerts that separate cost optimization from user-facing serving SLOs.

## Production Notes

KServe already has its own autoscaling story for inference revisions. This project uses HPA scale to zero only for helper workloads around the serving path: replay, explainability, and rollout smoke checks. The customer-facing router and champion model stay warm.

The operational dependency is the metrics adapter. If queue-depth metrics are missing while replicas are zero, the HPA cannot wake the workload. The included Prometheus rules make missing metrics and failed wakeups visible before the rollout controller misdiagnoses the serving stack.

## Senior Review Angle

This shows restraint. The project treats scale-to-zero as a narrow cost-control pattern for asynchronous serving workers, not as a universal reliability feature. It demonstrates HPA API constraints, feature-gate awareness, KServe cold-start risk, metric adapter dependency, and rollback-safe serving design.

References:

- https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/
- https://kubernetes.io/docs/reference/kubernetes-api/autoscaling/horizontal-pod-autoscaler-v2/
- https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/
