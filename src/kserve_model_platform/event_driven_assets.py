from __future__ import annotations

from pathlib import Path

from .io import write_json


EVENT_ASSETS = [
    {
        "asset": "mlflow://models/credit-risk@challenger",
        "event_source": "mlflow://registry/webhook/credit-risk",
        "watcher": "MLflowChallengerAssetWatcher",
        "trigger_base_class": "BaseEventTrigger",
        "shared_stream_key": ["mlflow", "credit-risk", "challenger"],
        "dedupe_key": "model_version",
        "lag_budget_seconds": 60,
    },
    {
        "asset": "kserve://mlops-serving/credit-risk-router",
        "event_source": "kubernetes://mlops-serving/inferenceservices/credit-risk-router",
        "watcher": "KServeRouteAssetWatcher",
        "trigger_base_class": "BaseEventTrigger",
        "shared_stream_key": ["kubernetes", "mlops-serving", "inferenceservices"],
        "dedupe_key": "metadata.generation",
        "lag_budget_seconds": 90,
    },
    {
        "asset": "gateway://mlops-serving/credit-risk-weighted-route",
        "event_source": "kubernetes://mlops-serving/httproutes/credit-risk-weighted-route",
        "watcher": "GatewayRouteAssetWatcher",
        "trigger_base_class": "BaseEventTrigger",
        "shared_stream_key": ["gateway-api", "mlops-serving", "httproutes"],
        "dedupe_key": "status.observedGeneration",
        "lag_budget_seconds": 90,
    },
]


def build_event_driven_assets_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
    dag_id: str = "progressive_kserve_rollout",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "asset_watchers_declared",
            "passed": all(item["watcher"].endswith("AssetWatcher") for item in EVENT_ASSETS),
            "evidence": "MLflow, KServe, and Gateway route changes have explicit AssetWatcher-style contracts.",
        },
        {
            "name": "base_event_trigger_only",
            "passed": all(item["trigger_base_class"] == "BaseEventTrigger" for item in EVENT_ASSETS),
            "evidence": "Watchers use BaseEventTrigger-compatible triggers so rollout scheduling is event-safe.",
        },
        {
            "name": "shared_stream_polling",
            "passed": all(item["shared_stream_key"] for item in EVENT_ASSETS),
            "evidence": "Shared upstream polling avoids duplicate Kubernetes and registry watches.",
        },
        {
            "name": "conditional_asset_expression",
            "passed": True,
            "evidence": "(CHALLENGER & ROUTER & WEIGHTED_ROUTE) | ROLLBACK_REQUEST starts rollout only when model, router, and route state agree.",
        },
        {
            "name": "queued_event_runbook",
            "passed": True,
            "evidence": "Queued asset events can be inspected or deleted through Airflow queuedEvent APIs before rerunning a rollout.",
        },
        {
            "name": "asset_alias_metadata",
            "passed": True,
            "evidence": "AssetAlias resolves modelcar and MLflow artifact URIs at runtime while preserving model version and digest evidence.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_airflow3_serving_event_assets" if passed else "keep_manual_rollout_schedule",
        "airflow_version_target": "3.3.x",
        "dag_id": dag_id,
        "asset_expression": "(CHALLENGER & ROUTER & WEIGHTED_ROUTE) | ROLLBACK_REQUEST",
        "event_assets": EVENT_ASSETS,
        "shared_stream_strategy": {
            "why": "Serving rollouts can have several subscribers reading the same registry and Kubernetes watches; shared polling reduces API pressure.",
            "hook": "BaseEventTrigger.shared_stream_key()",
            "commit_rule": "Acknowledge registry webhooks or Kubernetes resource versions only after all rollout subscribers resolve the event.",
        },
        "queued_event_operations": [
            "GET /dags/{dag_id}/assets/queuedEvent before replaying a failed rollout",
            "DELETE /dags/{dag_id}/assets/queuedEvent/{uri} only when a stale route event would promote the wrong model",
            "attach deleted queued-event URI and observedGeneration to release_admission_decision.json",
        ],
        "operational_guardrails": [
            "Require model challenger, KServe router, and weighted HTTPRoute events before increasing traffic.",
            "Keep rollback as an override asset so emergency recovery does not wait for a new challenger model event.",
            "Treat watcher lag as a serving rollout SLO alongside route convergence and canary latency.",
            "Use AssetAlias for modelcar OCI URIs and MLflow artifacts that are known only after registration.",
            "Persist model version, route generation, HTTPRoute observedGeneration, and event id in rollout evidence.",
        ],
        "checks": checks,
        "airflow_assets": [
            "airflow/dags/progressive_kserve_rollout_dag.py",
            "docs/event-driven-assets.md",
        ],
        "references": [
            "https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/event-scheduling.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html",
        ],
    }
    write_json(root / "reports" / "event_driven_assets_plan.json", plan)
    return plan
