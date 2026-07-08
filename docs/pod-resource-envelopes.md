# Pod Resource Envelopes

`make pod-resource-envelopes` writes `.local/reports/pod_resource_envelope_plan.json` and pairs it with `kubernetes/pod-resource-envelopes.yaml`.

## What It Shows

- Kubernetes `PodLevelResources` with pod-level `spec.resources` for canary route probes, shadow analysis, and rollback smoke workloads.
- Stable Pod Scheduling Readiness through `schedulingGates`.
- Release gate removal only after KServe model cache, Gateway `HTTPRoute`, Kueue admission, and champion preload evidence exist.
- Scheduler observability with `scheduler_pending_pods{queue="gated"}`.
- Dynamic Resource Allocation guardrails so explainer and shadow workloads fit inside the pod-level envelope.

## Production Notes

Serving platforms often waste scheduler and autoscaler effort while a modelcar download, Gateway route, or Kueue-admitted analysis job is not actually ready to run. Scheduling gates make those pods intentionally gated instead of repeatedly unschedulable.

Pod-level resources make sidecar-heavy serving checks easier to budget because the pod owns a CPU and memory envelope while the probe, OpenTelemetry collector, metrics exporter, or checkpoint sidecar keeps its local request. Use `PodLevelResourceManagers` when CPUManager, MemoryManager, or TopologyManager alignment matters for latency-sensitive probes.

## References

- Kubernetes pod-level resources: <https://kubernetes.io/docs/tasks/configure-pod-container/assign-pod-level-resources/>
- Kubernetes Pod Scheduling Readiness: <https://kubernetes.io/docs/concepts/scheduling-eviction/pod-scheduling-readiness/>
- Kubernetes Dynamic Resource Allocation: <https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/>
