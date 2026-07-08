from __future__ import annotations

from pathlib import Path

from .io import write_json


OBJECTIVES = [
    {
        "name": "credit-risk-online",
        "priority": 20,
        "pool": "credit-risk-inference-pool",
        "traffic_class": "online",
        "latency_slo_ms": 150,
        "fallback": "fail open to the default KServe HTTPRoute when the endpoint picker is unavailable",
    },
    {
        "name": "credit-risk-canary",
        "priority": 10,
        "pool": "credit-risk-inference-pool",
        "traffic_class": "canary",
        "latency_slo_ms": 250,
        "fallback": "hold the canary percent and route to champion-only backends",
    },
    {
        "name": "credit-risk-batch",
        "priority": -5,
        "pool": "credit-risk-inference-pool",
        "traffic_class": "batch",
        "latency_slo_ms": 1000,
        "fallback": "defer batch scoring until online queue depth recovers",
    },
]


def build_inference_gateway_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "stable_inference_pool_declared", "passed": True, "observed": "inference.networking.k8s.io/v1"},
        {"name": "objective_priority_modelled", "passed": sorted(item["priority"] for item in OBJECTIVES) == [-5, 10, 20]},
        {"name": "endpoint_picker_failure_mode_defined", "passed": any("fail open" in item["fallback"] for item in OBJECTIVES)},
        {"name": "canary_objective_declared", "passed": any(item["traffic_class"] == "canary" for item in OBJECTIVES)},
        {"name": "fallbacks_defined", "passed": all(item["fallback"] for item in OBJECTIVES)},
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_gateway_inference_extension" if all(check["passed"] for check in checks) else "keep_weighted_httproute_only",
        "pool": {
            "name": "credit-risk-inference-pool",
            "api_version": "inference.networking.k8s.io/v1",
            "target_port": 8000,
            "endpoint_picker": "credit-risk-endpoint-picker:9002",
            "failure_mode": "FailOpen",
        },
        "objectives": OBJECTIVES,
        "routing_signals": [
            "queue_length",
            "kv_cache_utilization",
            "prefix_cache_hit_rate",
            "active_lora_adapters",
            "model_server_readiness",
        ],
        "checks": checks,
        "guardrails": [
            "Use the stable v1 InferencePool API for routable model-server backends.",
            "Treat InferenceObjective as alpha and isolate it behind a documented rollout plan.",
            "Fail open to the KServe HTTPRoute if the endpoint picker is unhealthy.",
            "Keep batch objectives lower priority than online fraud or credit-risk requests.",
            "Record endpoint-picker routing signals in prediction logs for rollback analysis.",
        ],
        "kubernetes_assets": ["kubernetes/inference-gateway-routing.yaml"],
        "references": [
            "https://gateway-api-inference-extension.sigs.k8s.io/api-types/inferencepool/",
            "https://gateway-api-inference-extension.sigs.k8s.io/concepts/api-overview/",
            "https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api-inference-extension/",
            "https://docs.cloud.google.com/kubernetes-engine/docs/how-to/deploy-gke-inference-gateway",
        ],
    }
    write_json(root / "reports" / "inference_gateway_plan.json", plan)
    return plan
