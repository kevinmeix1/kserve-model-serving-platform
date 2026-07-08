# Dynamic Resource Allocation

This serving project models Kubernetes Dynamic Resource Allocation (DRA) for accelerator-aware KServe rollouts.

The demo writes `reports/device_allocation_plan.json` and the Kubernetes example lives in `kubernetes/dynamic-resource-allocation.yaml`.

## What It Shows

- DRA `DeviceClass` and `ResourceClaimTemplate` resources for KServe challenger pods.
- Kueue admission coupling for canary and shadow-analysis work.
- time-sliced L4 claims for low-risk challenger traffic.
- MIG claims for memory-sensitive profiling.
- Rollback-first fallback when accelerator claims are pending or unhealthy.

## Production Notes

DRA is useful for serving when the deployment needs a device capability, not just a GPU count. Keep champion rollback CPU-runnable, use shared L4 claims only for low-risk canary/shadow traffic, and reserve MIG or exclusive claims for isolation-sensitive model families.

References: Kubernetes DRA docs, Kueue workload admission docs, NVIDIA GPU Operator sharing docs, and KServe canary rollout docs.
