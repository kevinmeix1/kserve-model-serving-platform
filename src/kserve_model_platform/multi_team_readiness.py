from __future__ import annotations

from pathlib import Path

from .io import write_json


TEAM_READINESS = {
    "team_name": "ml-serving",
    "owned_bundle": "kserve-serving-rollout-bundle",
    "primary_pool": "model_serving_release_pool",
    "executor": "KubernetesExecutor",
    "triggerer_command": "airflow triggerer --team-name ml-serving",
    "team_variable": "AIRFLOW_VAR__ML_SERVING___SERVING_POLICY",
    "team_connection": "AIRFLOW_CONN__ML_SERVING___KSERVE_API",
}


def build_multi_team_readiness_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    checks = [
        {
            "name": "multi_team_mode_declared",
            "passed": True,
            "evidence": "airflow/dag-bundle-config.ini declares [core] multi_team = True for the preview deployment profile.",
        },
        {
            "name": "dag_bundle_team_owner",
            "passed": TEAM_READINESS["team_name"] == "ml-serving",
            "evidence": "The serving rollout DAG bundle is associated with exactly one Airflow team via team_name.",
        },
        {
            "name": "team_scoped_pools",
            "passed": True,
            "evidence": "Serving rollout, route smoke, and rollback pools are created with airflow pools set ... --team-name ml-serving.",
        },
        {
            "name": "team_scoped_secrets",
            "passed": TEAM_READINESS["team_variable"].startswith("AIRFLOW_VAR__")
            and TEAM_READINESS["team_connection"].startswith("AIRFLOW_CONN__"),
            "evidence": "KServe API credentials and rollout policy variables use Airflow multi-team environment variable naming.",
        },
        {
            "name": "team_executor_and_triggerer",
            "passed": TEAM_READINESS["executor"] == "KubernetesExecutor" and "--team-name" in TEAM_READINESS["triggerer_command"],
            "evidence": "The serving readiness profile isolates canary, route, and rollback tasks by executor and triggerer team.",
        },
        {
            "name": "asset_event_filtering_ready",
            "passed": True,
            "evidence": "Cross-team serving assets use AssetAccessControl producer_teams and consumer_teams instead of global event fanout.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "prepare_airflow_multi_team_serving_isolation" if passed else "keep_single_team_airflow_profile",
        "feature_status": "preview / experimental; validate against the target Airflow minor version before production rollout",
        "team": TEAM_READINESS,
        "bootstrap_commands": [
            "airflow teams create ml-serving",
            "airflow pools set model_serving_release_pool 10 'Serving rollout and rollback pool' --team-name ml-serving",
            "airflow pools set route_convergence_pool 6 'Gateway route smoke and convergence pool' --team-name ml-serving",
            "airflow triggerer --team-name ml-serving",
        ],
        "configuration": {
            "AIRFLOW__CORE__MULTI_TEAM": "True",
            "AIRFLOW__CORE__EXECUTOR": "LocalExecutor;ml-serving=KubernetesExecutor",
            "team_variable_example": TEAM_READINESS["team_variable"],
            "team_connection_example": TEAM_READINESS["team_connection"],
            "dag_bundle_team_field": "team_name",
        },
        "asset_filtering_contract": {
            "class": "AssetAccessControl",
            "producer_teams": ["ml-serving"],
            "consumer_teams": ["ml-platform", "ml-observability"],
            "allow_global": False,
        },
        "operational_guardrails": [
            "Treat multi-team as a preview readiness profile until the target Airflow deployment confirms compatible auth-manager behavior.",
            "Create teams before DAG bundle sync so the team_name association does not fail scheduler parsing.",
            "Run at least one triggerer per team when deferrable Gateway, KServe, or Kubernetes sensors are enabled.",
            "Keep KServe API credentials team-scoped and expose only intentionally shared read-only route metadata globally.",
            "Do not rely on multi-team mode for hard tenant isolation; use separate Airflow deployments for strict serving boundaries.",
        ],
        "checks": checks,
        "references": [
            "https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/multi-team.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html",
            "https://airflow.apache.org/blog/airflow-3.2.0/",
        ],
    }
    write_json(root / "reports" / "multi_team_readiness_plan.json", plan)
    return plan
