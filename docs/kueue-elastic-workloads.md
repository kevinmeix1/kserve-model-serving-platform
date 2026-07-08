# Kueue Elastic Workloads

This project keeps online KServe predictor replicas on ordinary rollout controls and uses Elastic Workloads only for serving-adjacent analysis: shadow comparison, drift probes, GPU explainers, and emergency rollback validation. That boundary is intentional. The online path should stay predictable while analysis jobs can expand into spare quota and contract when rollback capacity is needed.

The design follows Kueue Workload Slices. A scale-up slice lets shadow analysis fan out under `serving-analysis-queue`; a replacement slice can shrink lower-priority shadow work when rollback validation needs quota; and a GPU explainer slice uses a separate queue so incident forensics does not compete directly with the router or predictor pods.

## Workload Slices

- `credit-risk-shadow-slice-a` grows canary and shadow comparison workers when spare quota is available.
- `credit-risk-shadow-slice-b` replaces the first slice when rollback validation needs quota.
- `credit-risk-explainer-slice-a` bursts GPU explanation workers for high-severity model incidents.

Each slice carries `kueue.x-k8s.io/workload-slice-name`. Replacement slices add `kueue.x-k8s.io/workload-slice-replacement-for` so operators can see which admitted slice is being contracted.

## JobSet Integration

The manifest uses JobSet-style replicated jobs for shadow analysis because a serving canary usually evaluates many partitions: traffic segments, model versions, feature cohorts, and drift windows. Airflow owns the release decision, but Kueue owns admission so the analysis fanout cannot starve rollback capacity.

## Rollback Behavior

Rollback capacity is protected by policy:

- online `InferenceService` replicas are not placed behind elastic batch admission;
- replacement slices reduce shadow analysis before any router or predictor scaling changes;
- rollback validation runs in a higher-priority queue than shadow analysis;
- the feature gate can be disabled if Workload Slice accounting or endpoint health diverges.

## Production Notes

Start this as an opt-in feature gate, publish Workload Slice metrics, and alert on pending slices. In a managed environment, bind the analysis queues to separate node pools so endpoint latency and GPU explainer cost can be governed independently.
