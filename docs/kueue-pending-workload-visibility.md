# Kueue Pending Workload Visibility

`make pending-workload-visibility` writes `.local/reports/pending_workload_visibility_plan.json` and pairs it with `kubernetes/kueue-pending-workload-visibility.yaml`.

## What It Shows

- Kueue `VisibilityOnDemand` for ClusterQueue and LocalQueue pending workload queries.
- RBAC for `visibility.kueue.x-k8s.io` `clusterqueues/pendingworkloads` and `localqueues/pendingworkloads`.
- API Priority and Fairness setup via the Kueue release `visibility-apf.yaml`.
- Prometheus signals for admission wait time and pending requested resources.
- Queue triage actions for route smoke, shadow canary analysis, GPU explainers, and synthetic load.

## Production Notes

Model serving teams need to know whether a canary is stuck because route smoke has not been admitted, GPU explainers are saturated, or load tests are consuming cheap spot capacity. Pending-workload visibility turns that into an operator workflow: query ClusterQueue visibility for platform triage, query LocalQueue visibility for tenant self-service, and attach the queue snapshot to canary or rollback evidence.

The demo protects the live predictor path by keeping KServe `InferenceService` replicas outside Kueue batch queues while surfacing the queued analysis and validation workloads that decide whether traffic should advance.

## References

- Kueue monitor pending workloads: <https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/>
- Kueue pending workloads on demand: <https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/pending_workloads_on_demand/>
- Kueue Prometheus metrics: <https://kueue.sigs.k8s.io/docs/reference/metrics/>
