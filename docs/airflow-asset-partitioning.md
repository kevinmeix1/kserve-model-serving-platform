# Airflow Asset Partitioning

`make asset-partitioning-plan` writes `.local/reports/asset_partitioning_plan.json` and pairs it with the partition-aware examples inside `airflow/dags/progressive_kserve_rollout_dag.py`.

## What It Shows

- Airflow 3.2 asset partitioning for KServe rollout and canary telemetry workflows.
- `CronPartitionTimetable` for scheduled canary observation partitions.
- `PartitionedAssetTimetable` and `StartOfHourMapper` for aligned model, route, and SLO partitions.
- `dag_run.partition_key` captured with model version, HTTPRoute generation, route convergence, OpenLineage facets, and rollback smoke evidence.
- scheduler-managed partition backfills instead of replaying every progressive rollout step.

## Production Notes

KServe rollouts fail in subtle ways when metrics, route state, and model versions are mixed across windows. Partitioned assets make the rollout decision narrower: the release DAG waits for the challenger model, router, weighted route, and canary metrics for the same partition before changing traffic.

The portfolio value is operational precision. A stale Prometheus scrape, missed route event, or failed rollback smoke job can be replayed for one partition without creating a broad canary replay that confuses incident evidence.

## References

- Airflow 3.2 release announcement: <https://airflow.apache.org/blog/airflow-3.2.0/>
- Airflow release notes: <https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html>
- Airflow assets: <https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html>
