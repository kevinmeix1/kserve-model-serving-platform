# Topology-Aware Scheduling

`make topology-plan` writes `.local/reports/topology_placement_plan.json` and pairs it with `kubernetes/topology-aware-scheduling.yaml`.

## What It Shows

- Kueue `Topology` and topology-backed `ResourceFlavor` resources for serving analysis capacity.
- Kubernetes `topologySpreadConstraints` for live router availability across zones.
- LeaderWorkerSet annotations for rack-level co-location of leader and worker pods.
- Admission check scaffolding for topology-aware provisioning.
- Rollback-first fallback when compact large-model placement is not available.

## Production Notes

Serving systems need two opposite placement behaviors. Live routers and predictors should spread across failure domains. Large multi-pod inference profiles should compact within a rack when communication latency matters. The project models both so topology-aware scheduling does not accidentally trade away availability for locality.

References: Kueue Topology Aware Scheduling, Kueue LeaderWorkerSet integration, Kubernetes topology spread constraints, and Kueue AdmissionChecks.
