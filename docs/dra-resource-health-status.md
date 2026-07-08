# DRA Resource Health Status For KServe

`make resource-health-status` writes `.local/reports/resource_health_status_plan.json` and pairs it with `kubernetes/dra-resource-health-status.yaml`.

## What It Shows

- Kubernetes v1.36 `ResourceHealthStatus` for DRA device health in Pod status.
- `ResourceClaim` `status.devices` as companion evidence for challenger and shadow-analysis accelerator claims.
- Kubelet `PodResourcesLister` and `DynamicResource` telemetry as the runtime cross-check.
- `DeviceTaintRule` quarantine for unhealthy shared L4 devices.
- KServe traffic behavior when a challenger GPU is `Unhealthy` or a shadow-analysis device becomes `Unknown`.

## Production Notes

Serving incidents often blur together application failures, model load problems, and accelerator faults. This report makes the device layer explicit before the platform changes traffic. The canary-analysis runner inspects `status.containerStatuses[*].allocatedResourcesStatus`, checks `ResourceClaim.status.devices`, correlates the claim with kubelet PodResourcesLister telemetry, and then decides whether to hold, roll back, or continue CPU-only shadow scoring.

The rollback smoke probe intentionally stays CPU-runnable. A bad shared GPU should never prevent the platform from proving that the champion route can still serve traffic.

## References

- Kubernetes Dynamic Resource Allocation: <https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/>
- Kubernetes v1.36 DRA update: <https://kubernetes.io/blog/2026/05/07/kubernetes-v1-36-dra-136-updates/>
- Kubernetes v1.36 release highlights: <https://github.com/kubernetes/sig-release/discussions/2958>
