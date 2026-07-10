from __future__ import annotations

from pathlib import Path

from .io import write_json


def build_ai_workload_telemetry_plan(root: str | Path) -> dict:
    root = Path(root)
    workloads = [
        {
            "name": "credit-risk-champion",
            "kind": "KServe Predictor",
            "route": "credit-risk-weighted-route",
            "traffic_percent": 90,
            "resource_signals": ["pod.resources.requests.cpu", "pod.resources.limits.memory", "dra.resourceclaim.status"],
            "otel_attributes": ["kserve.inferenceservice.name", "kserve.revision", "gen_ai.request.model", "gen_ai.usage.input_tokens"],
            "slo": {"latency_p95_ms": 95, "error_rate": 0.01, "redis_hit_rate": 0.95},
            "remediation": "hold challenger promotion and keep champion route above 90 percent until canary SLOs recover",
        },
        {
            "name": "credit-risk-challenger",
            "kind": "KServe Canary Predictor",
            "route": "credit-risk-weighted-route",
            "traffic_percent": 10,
            "resource_signals": ["pod.resources.requests.cpu", "pod.resources.limits.memory", "pod.scheduling.gate"],
            "otel_attributes": ["kserve.inferenceservice.name", "ml.model.version", "prediction.request.id", "canary.traffic.percent"],
            "slo": {"latency_p95_ms": 110, "error_rate": 0.015, "shadow_delta": 0.08},
            "remediation": "rollback the challenger, retain shadow logs, and require a new model registry approval before replay",
        },
        {
            "name": "transformer-explainer",
            "kind": "KServe Transformer",
            "route": "credit-risk-transformer",
            "traffic_percent": 100,
            "resource_signals": ["pod.resources.requests.cpu", "pod.resources.limits.memory", "dra.resource.claim.name"],
            "otel_attributes": ["kserve.transformer.name", "explanation.method", "request.schema.version", "http.route"],
            "slo": {"latency_p95_ms": 45, "error_rate": 0.005, "explanation_coverage": 0.98},
            "remediation": "fail closed on schema drift, route only validated payloads, and surface reason-code coverage in rollout evidence",
        },
    ]
    required_resource_fields = {field for workload in workloads for field in workload["resource_signals"]}
    required_otel_fields = {field for workload in workloads for field in workload["otel_attributes"]}
    plan = {
        "generated_at": "2026-07-11T00:00:00Z",
        "standard_alignment": {
            "kubernetes": "Pod-level resource budgets and DRA claim health are release inputs for each serving component.",
            "kserve": "Predictor, transformer, explainer, canary, and weighted Gateway routing are modeled as separate telemetry subjects.",
            "opentelemetry": "GenAI-style model and token attributes are allow-listed next to serving and request identifiers.",
        },
        "workloads": workloads,
        "required_resource_fields": sorted(required_resource_fields),
        "required_otel_fields": sorted(required_otel_fields),
        "checks": [
            {"name": "weighted_routes_have_telemetry", "passed": all(workload["route"] for workload in workloads)},
            {"name": "pod_level_resources_mapped", "passed": "pod.resources.requests.cpu" in required_resource_fields},
            {"name": "dra_health_mapped", "passed": any("dra." in field for field in required_resource_fields)},
            {"name": "model_identity_mapped", "passed": "gen_ai.request.model" in required_otel_fields or "ml.model.version" in required_otel_fields},
        ],
        "runbook": [
            "Evaluate canary latency, error rate, and shadow delta before increasing Gateway weight.",
            "Keep model identity, route, and request id in traces while redacting feature payloads.",
            "Attach DRA health and pod-level resource pressure to every rollback or promotion decision.",
        ],
    }
    plan["passed"] = all(check["passed"] for check in plan["checks"])
    write_json(root / "reports" / "ai_workload_telemetry_plan.json", plan)
    return plan
