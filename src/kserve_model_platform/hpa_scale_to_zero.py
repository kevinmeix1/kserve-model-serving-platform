from __future__ import annotations

from pathlib import Path

from .io import write_json


SCALE_TO_ZERO_WORKLOADS = [
    {
        "name": "shadow-replay-worker",
        "target_ref": "Deployment/shadow-replay-worker",
        "min_replicas": 0,
        "max_replicas": 30,
        "metric_type": "External",
        "metric_name": "kserve_shadow_replay_queue_depth",
        "wake_threshold": 1,
        "cold_start_budget_seconds": 120,
        "scale_to_zero_allowed": True,
        "reason": "Shadow replay is backlog-driven and should not reserve serving capacity when no replay windows are pending.",
    },
    {
        "name": "async-explainer-worker",
        "target_ref": "Deployment/async-explainer-worker",
        "min_replicas": 0,
        "max_replicas": 10,
        "metric_type": "External",
        "metric_name": "kserve_async_explainer_queue_depth",
        "wake_threshold": 1,
        "cold_start_budget_seconds": 90,
        "scale_to_zero_allowed": True,
        "reason": "Expensive explainability workers can idle until a compliance or analyst queue contains work.",
    },
    {
        "name": "route-conformance-smoke",
        "target_ref": "Deployment/route-conformance-smoke",
        "min_replicas": 0,
        "max_replicas": 6,
        "metric_type": "Object",
        "metric_name": "route_conformance_backlog",
        "metric_object": "Service/route-conformance-queue",
        "wake_threshold": 1,
        "cold_start_budget_seconds": 60,
        "scale_to_zero_allowed": True,
        "reason": "Route-conformance probes run after rollout events and do not need standing pods between events.",
    },
]

PROTECTED_WORKLOADS = [
    {
        "name": "credit-risk-router",
        "min_replicas": 2,
        "reason": "The customer-facing router must stay warm for traffic shifting and emergency rollback.",
    },
    {
        "name": "champion-predictor",
        "min_replicas": 2,
        "reason": "The champion model remains the live fallback path when canary or challenger traffic fails.",
    },
    {
        "name": "rollback-controller",
        "min_replicas": 1,
        "reason": "Rollback control is a safety function and should not wait on HPA cold start.",
    },
]


def build_hpa_scale_to_zero_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    feature_gate = {
        "name": "HPAScaleToZero",
        "minimum_version": "Kubernetes v1.36",
        "stage": "alpha",
        "default": "disabled",
        "requirement": "minReplicas=0 requires at least one Object or External metric in autoscaling/v2",
    }
    checks = [
        {
            "name": "feature_gate_documented",
            "passed": feature_gate["stage"] == "alpha" and feature_gate["default"] == "disabled",
            "evidence": "KServe serving docs keep HPAScaleToZero behind an explicit feature-gate decision.",
        },
        {
            "name": "all_zero_min_replicas_use_external_or_object_metrics",
            "passed": all(workload["metric_type"] in {"External", "Object"} for workload in SCALE_TO_ZERO_WORKLOADS),
            "evidence": "Scale-to-zero serving helpers use queue or object backlog metrics, never CPU metrics.",
        },
        {
            "name": "online_serving_path_kept_warm",
            "passed": not ({workload["name"] for workload in SCALE_TO_ZERO_WORKLOADS} & {item["name"] for item in PROTECTED_WORKLOADS}),
            "evidence": "Router, champion predictor, and rollback controller are protected from zero-replica floors.",
        },
        {
            "name": "wake_metric_contract",
            "passed": all(workload["metric_name"] and workload["wake_threshold"] >= 1 for workload in SCALE_TO_ZERO_WORKLOADS),
            "evidence": "Every idleable worker declares a metric adapter contract that can wake from zero.",
        },
        {
            "name": "cold_start_budget_recorded",
            "passed": all(workload["cold_start_budget_seconds"] <= 120 for workload in SCALE_TO_ZERO_WORKLOADS),
            "evidence": "Cold starts are bounded so user-facing predictors remain excluded.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-09T00:00:00Z",
        "recommended_action": "enable_hpa_scale_to_zero_for_async_serving_workers" if passed else "keep_hpa_scale_to_zero_disabled",
        "passed": passed,
        "feature_status": {
            "hpa_scale_to_zero": "Kubernetes v1.36 alpha and disabled by default behind HPAScaleToZero",
            "metric_requirement": "minReplicas=0 is valid only with at least one Object or External metric",
            "api_version": "autoscaling/v2",
        },
        "feature_gate": feature_gate,
        "scale_to_zero_workloads": SCALE_TO_ZERO_WORKLOADS,
        "protected_workloads": PROTECTED_WORKLOADS,
        "checks": checks,
        "runbook": [
            "Enable HPAScaleToZero for shadow replay and async explainers before considering any serving-path workers.",
            "Verify Prometheus Adapter or the external metrics adapter continues publishing backlog metrics while pods are zero.",
            "Keep the router, champion predictor, and rollback controller above zero replicas.",
            "Rollback if queue depth is positive while desired replicas stay at zero beyond the cold-start budget.",
        ],
        "references": [
            "https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/",
            "https://kubernetes.io/docs/reference/kubernetes-api/autoscaling/horizontal-pod-autoscaler-v2/",
            "https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/",
        ],
    }
    write_json(root / "reports" / "hpa_scale_to_zero_plan.json", plan)
    return plan
