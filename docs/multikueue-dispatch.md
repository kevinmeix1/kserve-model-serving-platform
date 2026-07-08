# MultiKueue Dispatch

`make multikueue-dispatch` writes `.local/reports/multikueue_dispatch_plan.json` and pairs it with `kubernetes/multikueue-dispatch.yaml`.

This project uses MultiKueue only for serving-adjacent analysis work. Online `InferenceService` predictor and router replicas stay on the normal KServe, HPA, and Gateway API path. The queued work is finite evidence generation: shadow replay, route conformance, rollback smoke tests, and GPU explainers.

## Operating Model

- Airflow submits serving-analysis Jobs to the manager cluster.
- The manager reserves Kueue quota and delegates the Workload to worker clusters with `kueue.x-k8s.io/multikueue`.
- Worker clusters mirror namespaces, LocalQueues, service accounts, model artifact secrets, and image policy.
- `status.nominatedClusterNames` is watched while a Workload is pending.
- `status.clusterName` is recorded when a worker admits the Workload.
- The remote Job is linked to the selected Workload with `kueue.x-k8s.io/prebuilt-workload-name`.
- Canary promotion freezes if shadow replay or rollback smoke cannot dispatch inside the rollout SLO.

## Failure Recovery

If dispatch stalls, hold the canary, reduce replay shard count, and rerun on the smaller `serving-analysis-queue`. If rollback smoke cannot dispatch during an incident, move KServe traffic to the previous champion first, then rerun validation with the faster AllAtOnce dispatch mode. If GPU explainer capacity is unavailable, generate CPU-only explanation summaries and attach the missing GPU evidence to the release hold.

## References

- Kueue MultiKueue concept: <https://kueue.sigs.k8s.io/docs/concepts/multikueue/>
- MultiKueue setup: <https://kueue.sigs.k8s.io/docs/tasks/manage/setup_multikueue/>
- Kubernetes Job in Multi-Cluster: <https://kueue.sigs.k8s.io/docs/tasks/run/multikueue/job/>
- KServe canary rollout: <https://kserve.github.io/website/latest/modelserving/v1beta1/rollout/canary/>
