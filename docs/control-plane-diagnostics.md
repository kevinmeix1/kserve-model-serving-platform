# Control Plane Diagnostics

`make control-plane-diagnostics` writes `.local/reports/control_plane_diagnostics_plan.json`.

## What It Shows

- Kubernetes v1.36 controller staleness mitigation for KServe and Gateway route automation.
- Component `/statusz` and `/flagz` readiness for API server, controller manager, scheduler, and kubelet.
- PSI metrics for CPU, memory, and IO stall detection on serving nodes.
- native histogram readiness for high-resolution control-plane and inference latency metrics.
- Fail-closed traffic behavior when route, shadow-analysis, or rollback controllers read stale cache state.

## Production Notes

Canary automation can move traffic to the wrong model if the controller cache is stale. This plan gives route, shadow, and rollback controllers strict freshness budgets and requires direct API reads before a high-impact traffic decision.

`/statusz` shows the component build and health. `/flagz` shows the live feature-gate state after upgrades. Together they make Kubernetes upgrade drift visible before KServe automation trusts new routing, scheduling, security, or metrics behavior.

## Senior Review Angle

This is the operator layer for online inference: it shows how the platform detects stale watches, feature-gate drift, node pressure, and metrics-cardinality risk before those issues corrupt route promotion or rollback decisions.

References:

- https://kubernetes.io/blog/2026/04/28/kubernetes-v1-36-staleness-mitigation-for-controllers/
- https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/
- https://kubernetes.io/blog/2026/04/25/kubernetes-v1-36-psi-metrics/
