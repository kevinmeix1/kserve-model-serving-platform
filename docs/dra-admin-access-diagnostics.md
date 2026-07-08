# KServe DRA AdminAccess Diagnostics

`make admin-access-diagnostics` writes `.local/reports/admin_access_diagnostics_plan.json` and pairs it with `kubernetes/dra-admin-access-diagnostics.yaml`.

## What It Shows

- Kubernetes v1.36 DRA `AdminAccess` ResourceClaims in a namespace labeled `resource.kubernetes.io/admin-access: "true"`.
- Serving-specific break-glass diagnostics for challenger predictors, GPU explainers, and rollback smoke probes.
- Least-privilege RBAC that separates privileged claim creation from read-only KServe `InferenceService` status inspection.
- Evidence capture for `ResourceClaim.status.devices`, Pod `allocatedResourcesStatus`, KServe revisions, and model-cache state.
- Cleanup deadlines and Prometheus alerts when privileged claims outlive their incident window.

## Production Notes

AdminAccess is only used after serving health points to a device-level problem. The rollout controller should pin traffic to KServe's last good rolled-out revision while the diagnostic claim is active, collect read-only driver and cache evidence, then delete the claim. This keeps the feature useful for production troubleshooting without turning privileged ResourceClaims into a normal serving deployment path.

The runbook complements KServe canary rollback semantics: use `ResourceHealthStatus` for first detection, AdminAccess for deeper in-use device diagnostics, and the canary decision record for audit evidence.

## References

- Kubernetes Dynamic Resource Allocation: <https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/>
- Kubernetes v1.36 release highlights: <https://github.com/kubernetes/sig-release/discussions/2958>
- KEP-5018 DRA Admin Access: <https://www.kubernetes.dev/resources/keps/5018/>
- KServe canary rollout strategy: <https://kserve.github.io/website/docs/model-serving/predictive-inference/rollout-strategies/canary>
