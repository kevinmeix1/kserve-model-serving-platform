from __future__ import annotations

from pathlib import Path

from .io import write_json


SERVING_STAGES = [
    {
        "name": "feature-transformer",
        "role": "transformer",
        "deployment_mode": "separate",
        "scaling": "independent HPA on request rate and transform latency",
        "health_gate": "transformer readiness plus predictor health probe",
        "latency_budget_ms": 8.0,
        "fallback": "route directly to predictor with cached feature defaults",
    },
    {
        "name": "credit-risk-predictor",
        "role": "predictor",
        "deployment_mode": "KServe custom ServingRuntime",
        "scaling": "KServe autoscaling on concurrency and p95 latency",
        "health_gate": "Open Inference V2 health and model metadata",
        "latency_budget_ms": 35.0,
        "fallback": "pin Gateway route to champion revision",
    },
    {
        "name": "risk-explainer",
        "role": "explainer",
        "deployment_mode": "async side path",
        "scaling": "scale-to-zero worker for high-risk or incident requests",
        "health_gate": "bounded explanation queue depth and GPU/DRA health",
        "latency_budget_ms": 250.0,
        "fallback": "return prediction with deferred explanation ticket",
    },
]


def build_transformer_explainer_readiness_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    total_sync_budget = sum(
        stage["latency_budget_ms"]
        for stage in SERVING_STAGES
        if stage["role"] in {"transformer", "predictor"}
    )
    checks = [
        {
            "name": "predictor_transformer_explainer_roles_declared",
            "passed": {stage["role"] for stage in SERVING_STAGES}
            == {"predictor", "transformer", "explainer"},
            "evidence": "KServe data plane roles are modeled explicitly.",
        },
        {
            "name": "transformer_predictor_health_gate",
            "passed": any(
                stage["role"] == "transformer" and "predictor health" in stage["health_gate"]
                for stage in SERVING_STAGES
            ),
            "evidence": "Transformer readiness checks include predictor health.",
        },
        {
            "name": "explainer_is_off_hot_path",
            "passed": any(
                stage["role"] == "explainer" and stage["deployment_mode"] == "async side path"
                for stage in SERVING_STAGES
            ),
            "evidence": "Explanations are deferred for latency-sensitive inference.",
        },
        {
            "name": "sync_latency_budget_bounded",
            "passed": total_sync_budget <= 50.0,
            "evidence": {"sync_budget_ms": total_sync_budget, "limit_ms": 50.0},
        },
        {
            "name": "fallbacks_keep_champion_route_available",
            "passed": all(stage["fallback"] for stage in SERVING_STAGES),
            "evidence": "Each stage has a failure-mode-specific fallback.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-10T00:00:00Z",
        "passed": passed,
        "recommended_action": (
            "enable_transformer_explainer_topology"
            if passed
            else "hold_transformer_explainer_rollout"
        ),
        "kserve_data_plane": {
            "predictor": "serves Open Inference V2 predictions",
            "transformer": "pre/post processing and feature normalization",
            "explainer": "interpretability and incident evidence",
        },
        "collocation_decision": {
            "mode": "separate_by_default",
            "collocate_when": [
                "transformer and predictor are tightly coupled",
                "sidecar resource overhead dominates",
                "network latency is larger than transform cost",
            ],
            "current_choice": "separate transformer, async explainer",
            "reason": "preserve independent scaling and keep explanations off the synchronous path",
        },
        "serving_stages": SERVING_STAGES,
        "checks": checks,
        "kubernetes_assets": ["kserve/transformer-explainer-topology.yaml"],
        "references": [
            "https://kserve.github.io/website/docs/intro",
            "https://kserve.github.io/website/docs/model-serving/predictive-inference/transformers/collocation",
            "https://kserve.github.io/website/docs/concepts/resources/servingruntime",
        ],
    }
    write_json(root / "reports" / "transformer_explainer_readiness_plan.json", plan)
    return plan
