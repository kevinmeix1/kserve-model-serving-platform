# Airflow DAG Bundles

`make dag-bundle-plan` writes `.local/reports/dag_bundle_versioning_plan.json` and pairs it with `airflow/dag-bundle-config.ini`.

## What It Shows

- Airflow 3 `GitDagBundle` configuration for progressive KServe rollout DAGs.
- Bundle versioning kept on with `disable_bundle_versioning = False`.
- Reruns set to `rerun_with_latest_version = False` so failed canary and rollback reruns preserve the original rollout code.
- `sparse_dirs` includes Airflow DAGs, KServe manifests, Kubernetes policies, contracts, and package code.
- Git credentials referenced through `git_conn_id`, so deploy keys or tokens belong in Airflow Connections or a secrets backend.
- Scheduler-managed backfills separated from incident replay so shadow replay can use current code while forensic reruns keep the failed bundle version.

## Production Notes

Serving rollouts mutate traffic, route weights, cache gates, and rollback state. When a canary fails, the team needs to know whether a rerun is reproducing the exact failed route patch or validating a new fix.

This project records the DAG Bundle alongside champion and challenger aliases, modelcar tags, InferenceService generation, HTTPRoute generation, and canary decision evidence. That makes a rollback explanation credible: the model, route, image, and orchestration code are all tied together.

## Failure Recovery

- If Git bundle refresh fails, restore the `github_dag_bundle` connection and refresh the DAG processor before starting new rollout runs.
- If a bad rollout commit is deployed, revert the commit and launch a fresh canary rather than changing the failed run's evidence.
- If the rollback command must be tested after a hotfix, run original-bundle replay for incident evidence and latest-code replay for remediation evidence.

## References

- Airflow DAG Bundles: <https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-bundles.html>
- Airflow `GitDagBundle`: <https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-bundles.html#gitdagbundle>
- Airflow rerun behavior: <https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-bundles.html#rerun-behavior>
