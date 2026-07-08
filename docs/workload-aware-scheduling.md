# Kubernetes Workload-Aware Scheduling

`make workload-aware-scheduling` writes `.local/reports/workload_aware_scheduling_plan.json`.

## What It Shows

- Kubernetes v1.36 `scheduling.k8s.io/v1alpha2` Workload and PodGroup readiness.
- `WorkloadWithJob` fixed-shape Indexed Job integration for shadow replay and rollback smoke jobs.
- PodGroup atomic gang scheduling with `schedulingPolicy.gang.minCount`.
- Topology constraints for zone, rack, or host placement.
- Workload-aware preemption using PodGroup `priority` and `disruptionMode: PodGroup`.
- DRA ResourceClaim sharing at PodGroup scope for high-cardinality serving analysis.
- An explicit boundary that keeps live KServe InferenceService predictors off alpha scheduling APIs.

## Production Notes

Workload-Aware Scheduling is alpha in Kubernetes v1.36 and should be treated as readiness evidence. This repo uses it for shadow replay, route conformance, and rollback smoke workloads where all-or-nothing scheduling makes the canary evidence more meaningful. Live predictors continue to use stable KServe, Gateway API, HPA, Kueue-adjacent admission, and model-cache controls.

The safest first production candidate is a fixed-shape Indexed Job where `.spec.parallelism == .spec.completions`, `.spec.completionMode` is `Indexed`, and the pod template does not set `schedulingGroup` manually. More elastic or request-serving shapes should stay on stable KServe scheduling until the upstream API graduates.

## Senior Review Angle

This demonstrates that serving evidence jobs are scheduled as coherent workloads instead of random pods competing one at a time. The report ties KServe rollout gates, Kueue admission, PodGroup scheduling, DRA ResourceClaims, rollback fallback, and release-admission evidence into one operable readiness story.

References:

- https://kubernetes.io/blog/2026/05/13/kubernetes-v1-36-advancing-workload-aware-scheduling/
- https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/
- https://kubernetes.io/blog/2026/05/07/kubernetes-v1-36-dra-136-updates/
