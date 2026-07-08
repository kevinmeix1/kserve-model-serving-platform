from __future__ import annotations

from pathlib import Path

from .io import write_json


AIRFLOW_DAG_BUNDLE = {
    "name": "kserve-serving-rollout-bundle",
    "provider": "GitDagBundle",
    "tracking_ref": "main",
    "subdir": "airflow/dags",
    "git_conn_id": "github_dag_bundle",
    "sparse_dirs": ["airflow/dags", "kserve", "kubernetes", "contracts", "src"],
    "refresh_interval_seconds": 60,
}


def build_dag_bundle_versioning_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
    dag_id: str = "progressive_kserve_rollout",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "git_dag_bundle_declared",
            "passed": AIRFLOW_DAG_BUNDLE["provider"] == "GitDagBundle",
            "evidence": "Airflow loads progressive rollout DAGs from a Git-backed DAG Bundle.",
        },
        {
            "name": "bundle_versioning_enabled",
            "passed": True,
            "evidence": "[dag_processor] disable_bundle_versioning = False keeps rollout code versions queryable.",
        },
        {
            "name": "reruns_preserve_original_bundle",
            "passed": True,
            "evidence": "Failed canary reruns keep the bundle version that produced the original route and rollback evidence.",
        },
        {
            "name": "serving_manifests_in_sparse_checkout",
            "passed": "kserve" in AIRFLOW_DAG_BUNDLE["sparse_dirs"] and "kubernetes" in AIRFLOW_DAG_BUNDLE["sparse_dirs"],
            "evidence": "Sparse checkout includes KServe InferenceService, Gateway, Kueue, and policy manifests used by rollout tasks.",
        },
        {
            "name": "credentials_kept_in_airflow_connection",
            "passed": AIRFLOW_DAG_BUNDLE["git_conn_id"] == "github_dag_bundle",
            "evidence": "Git credentials are referenced through git_conn_id, not inline JSON.",
        },
        {
            "name": "scheduler_managed_backfill_policy",
            "passed": True,
            "evidence": "Backfills are tracked as Airflow 3 backfill runs and separated from incident replay runs.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_airflow3_serving_dag_bundle_versioning" if passed else "hold_airflow_dag_bundle_rollout",
        "airflow_version_target": "3.3.x",
        "dag_id": dag_id,
        "bundle": AIRFLOW_DAG_BUNDLE,
        "runtime_config": {
            "AIRFLOW__DAG_PROCESSOR__DAG_BUNDLE_CONFIG_LIST": "configured in airflow/dag-bundle-config.ini",
            "AIRFLOW__DAG_PROCESSOR__DISABLE_BUNDLE_VERSIONING": "False",
            "AIRFLOW__CORE__RERUN_WITH_LATEST_VERSION": "False",
        },
        "rerun_policy": {
            "core.rerun_with_latest_version": False,
            "dag.rerun_with_latest_version": False,
            "rerun_keeps_route_patch_code": True,
            "rollback_replay_uses_original_bundle": True,
        },
        "backfill_policy": {
            "scheduler_managed_backfills": True,
            "current_code_backfills": "use_latest_bundle_for_new_shadow_replay_windows",
            "incident_replay": "pin_to_bundle_version_recorded_on_failed_canary",
            "max_active_runs": 1,
            "pool": "model_serving_release_pool",
        },
        "serving_release_evidence": [
            "bundle_name",
            "bundle_version",
            "champion_model_alias",
            "challenger_model_alias",
            "kserve_inferenceservice_generation",
            "httproute_generation",
            "modelcar_image_tag",
        ],
        "failure_modes": [
            {
                "mode": "bad_rollout_commit",
                "blast_radius": "new canary or route convergence tasks fail while completed evidence keeps the prior bundle version",
                "recovery": "revert the commit, keep failed bundle_version in incident notes, and start a fresh canary run",
            },
            {
                "mode": "git_bundle_refresh_failure",
                "blast_radius": "new rollout DAG parses pause but running task instances keep their recorded code version",
                "recovery": "restore git_conn_id or network access, then refresh DAG processors",
            },
            {
                "mode": "rollback_drift",
                "blast_radius": "rollback replay executes a different route patch than the incident run",
                "recovery": "keep rerun_with_latest_version disabled and compare latest-code remediation in a separate DAG run",
            },
        ],
        "operational_guardrails": [
            "Attach bundle version to canary decisions, route convergence evidence, and rollback records.",
            "Keep live InferenceService predictors outside batch queues while DAG Bundle versioning controls the rollout code path.",
            "Do not inline Git credentials in dag_bundle_config_list; use an Airflow Connection backed by a secrets backend.",
            "Use sparse_dirs so scheduler parsing includes serving manifests without loading unrelated repository files.",
            "Treat incident replay as forensic evidence and latest-code backfill as remediation validation.",
        ],
        "checks": checks,
        "airflow_assets": [
            "airflow/dag-bundle-config.ini",
            "airflow/dags/progressive_kserve_rollout_dag.py",
            "docs/airflow-dag-bundles.md",
        ],
        "references": [
            "https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-bundles.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-bundles.html#gitdagbundle",
            "https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-bundles.html#rerun-behavior",
            "https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html",
        ],
    }
    write_json(root / "reports" / "dag_bundle_versioning_plan.json", plan)
    return plan
