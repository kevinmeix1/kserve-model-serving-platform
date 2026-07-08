# Indexed Job Resilience

KServe serving should not depend on a batch Job completing, but rollout analysis often does: shadow comparisons, batch scoring replay, endpoint-picker checks, GPU explainers, drift probes, and rollback smoke tests. Those finite tasks need deterministic shard ownership and bounded retry behavior.

## Kubernetes Controls

- `completionMode: Indexed` gives every analysis shard a deterministic `JOB_COMPLETION_INDEX`.
- `backoffLimitPerIndex` limits retries for one bad cohort without delaying unrelated rollout checks.
- `maxFailedIndexes` stops wasteful waves before analysis consumes rollback quota.
- `podFailurePolicy` marks bad cohort records as `FailIndex`, image/config problems as `FailJob`, and node disruption as `Ignore`.
- `successPolicy` can declare quorum success while preserving failed-index evidence for targeted replay.

The serving boundary is explicit: online KServe predictor replicas stay on the normal serving autoscaling path. Indexed Jobs are for rollout evidence and recovery only.

## Airflow Backfill Create

Historical rollout repair uses failed-only reprocessing:

```bash
airflow backfill create \
  --dag-id progressive_kserve_rollout \
  --from-date 2026-07-01 \
  --to-date 2026-07-07 \
  --reprocess-behavior failed \
  --max-active-runs 2 \
  --run-backwards
```

Use reverse ordering so recent rollout evidence recovers first, and keep backfill concurrency below the live rollout concurrency.

## Failure Semantics

| Failure | Policy | Outcome |
| --- | --- | --- |
| Bad scoring cohort | `FailIndex` | Mark that shard failed and keep unrelated shadow checks running. |
| Bad image or command | `FailJob` | Stop the wave because retries would be wasteful. |
| Node drain or preemption | `Ignore` | Do not count infrastructure churn against the retry budget. |
| Too many failed shards | `maxFailedIndexes` | Stop the wave and preserve rollback validation capacity. |

## Recovery Flow

1. Inspect `status.failedIndexes` and `status.completedIndexes`.
2. Rerun only failed cohorts or rollout-check shards.
3. Keep rollback smoke checks ahead of shadow replay in Airflow pools and Kueue priority.
4. Attach `indexed_job_resilience_plan.json` to rollout evidence.
