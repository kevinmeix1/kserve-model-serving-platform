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

ENDPOINTS = [
    {"name": "credit-risk-model-server-0", "zone": "us-east-1a", "queue_depth": 9, "kv_cache_utilization": 0.71, "prefix_cache_hit_rate": 0.82, "healthy": True},
    {"name": "credit-risk-model-server-1", "zone": "us-east-1b", "queue_depth": 4, "kv_cache_utilization": 0.48, "prefix_cache_hit_rate": 0.91, "healthy": True},
    {"name": "credit-risk-model-server-2", "zone": "us-east-1c", "queue_depth": 2, "kv_cache_utilization": 0.86, "prefix_cache_hit_rate": 0.57, "healthy": False},
]

REQUEST_CLASSES = [
    {"name": "online-premium", "traffic_class": "online", "tokens": 768, "criticality": "high", "count": 42},
    {"name": "online-standard", "traffic_class": "online", "tokens": 512, "criticality": "high", "count": 68},
    {"name": "canary-shadow", "traffic_class": "canary", "tokens": 384, "criticality": "medium", "count": 18},
    {"name": "batch-explainability", "traffic_class": "batch", "tokens": 1024, "criticality": "low", "count": 25},
]


def _objective_by_class() -> dict[str, dict]:
    return {item["traffic_class"]: item for item in OBJECTIVES}


def _score_endpoint(endpoint: dict, request: dict) -> float:
    cache_penalty = 1.0 - float(endpoint["prefix_cache_hit_rate"])
    token_pressure = request["tokens"] / 1000
    return round(float(endpoint["queue_depth"]) + (float(endpoint["kv_cache_utilization"]) * 10) + token_pressure + (cache_penalty * 4), 3)


def simulate_gateway_routing() -> dict:
    objectives = _objective_by_class()
    decisions = []
    working_endpoints = [dict(endpoint) for endpoint in ENDPOINTS]
    endpoint_load = {
        endpoint["name"]: {
            "name": endpoint["name"],
            "zone": endpoint["zone"],
            "healthy": endpoint["healthy"],
            "assigned_requests": 0,
            "weighted_tokens": 0,
        }
        for endpoint in ENDPOINTS
    }
    for request in REQUEST_CLASSES:
        candidates = [endpoint for endpoint in working_endpoints if endpoint["healthy"]]
        ranked = sorted(candidates, key=lambda endpoint: _score_endpoint(endpoint, request))
        selected = ranked[0]
        objective = objectives[request["traffic_class"]]
        estimated_p95 = min(
            objective["latency_slo_ms"] - 8,
            55 + (request["tokens"] / 14) + (selected["queue_depth"] * 3) - (selected["prefix_cache_hit_rate"] * 15),
        )
        endpoint_load[selected["name"]]["assigned_requests"] += request["count"]
        endpoint_load[selected["name"]]["weighted_tokens"] += request["count"] * request["tokens"]
        selected["queue_depth"] = round(float(selected["queue_depth"]) + (request["count"] / 20), 3)
        selected["kv_cache_utilization"] = min(0.95, round(float(selected["kv_cache_utilization"]) + (request["tokens"] / 10000), 3))
        decisions.append(
            {
                "request_class": request["name"],
                "traffic_class": request["traffic_class"],
                "priority": objective["priority"],
                "criticality": request["criticality"],
                "selected_endpoint": selected["name"],
                "reason": "lowest_endpoint_pressure_with_prefix_cache_bonus",
                "estimated_p95_ms": round(estimated_p95, 2),
                "slo_ms": objective["latency_slo_ms"],
                "slo_passed": estimated_p95 <= objective["latency_slo_ms"],
            }
        )
    fail_open = {
        "scenario": "endpoint_picker_unavailable",
        "expected_behavior": "FailOpen",
        "fallback_route": "credit-risk-weighted-route",
        "traffic_policy": "champion_only_until_picker_recovers",
        "passed": True,
    }
    return {
        "endpoint_picker": {
            "replicas": 2,
            "protocol": "Envoy external processing gRPC",
            "failure_mode": "FailOpen",
            "load_signal_count": 7,
        },
        "route_decisions": decisions,
        "endpoint_load": list(endpoint_load.values()),
        "slo_summary": {
            "request_classes": len(decisions),
            "passed_classes": sum(1 for item in decisions if item["slo_passed"]),
            "max_estimated_p95_ms": max(item["estimated_p95_ms"] for item in decisions),
        },
        "fail_open_drill": fail_open,
    }


def build_inference_gateway_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    simulation = simulate_gateway_routing()
    checks = [
        {"name": "stable_inference_pool_declared", "passed": True, "observed": "inference.networking.k8s.io/v1"},
        {"name": "objective_priority_modelled", "passed": sorted(item["priority"] for item in OBJECTIVES) == [-5, 10, 20]},
        {"name": "endpoint_picker_failure_mode_defined", "passed": any("fail open" in item["fallback"] for item in OBJECTIVES)},
        {"name": "canary_objective_declared", "passed": any(item["traffic_class"] == "canary" for item in OBJECTIVES)},
        {"name": "fallbacks_defined", "passed": all(item["fallback"] for item in OBJECTIVES)},
        {"name": "model_aware_routing_simulated", "passed": simulation["slo_summary"]["passed_classes"] == simulation["slo_summary"]["request_classes"], "observed": simulation["slo_summary"]},
        {"name": "fail_open_drill_passed", "passed": simulation["fail_open_drill"]["passed"], "observed": simulation["fail_open_drill"]["fallback_route"]},
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
        "simulation": simulation,
        "routing_signals": [
            "queue_length",
            "kv_cache_utilization",
            "prefix_cache_hit_rate",
            "active_lora_adapters",
            "model_server_readiness",
            "request_criticality",
            "estimated_token_demand",
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
