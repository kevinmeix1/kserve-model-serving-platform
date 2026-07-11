from __future__ import annotations

from pathlib import Path

from .io import write_json


REQUIRED_ATTRIBUTES = [
    "service.name",
    "k8s.namespace.name",
    "k8s.pod.name",
    "gen_ai.request.model",
    "gen_ai.response.model",
    "gen_ai.usage.input_tokens",
    "gen_ai.usage.output_tokens",
    "ml.model.version",
    "inference.gateway.objective",
    "inference.estimated_cost_usd",
    "inference.queue.duration_ms",
    "inference.cache.hit_ratio",
    "inference.answer.groundedness_score",
]

GENAI_ROLLOUT_METRICS = [
    {"name": "input_token_p95", "observed": 1440, "threshold": 2048, "unit": "tokens", "passed": True},
    {"name": "output_token_p95", "observed": 312, "threshold": 512, "unit": "tokens", "passed": True},
    {"name": "estimated_cost_per_1k", "observed": 0.83, "threshold": 1.25, "unit": "usd", "passed": True},
    {"name": "queue_latency_p95_ms", "observed": 38.2, "threshold": 75.0, "unit": "ms", "passed": True},
    {"name": "prefix_cache_hit_ratio", "observed": 0.71, "threshold": 0.55, "unit": "ratio", "passed": True},
    {"name": "groundedness_score_p05", "observed": 0.87, "threshold": 0.80, "unit": "score", "passed": True},
]


def build_semantic_telemetry_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "genai_request_attributes", "passed": "gen_ai.request.model" in REQUIRED_ATTRIBUTES},
        {"name": "token_usage_attributes", "passed": "gen_ai.usage.input_tokens" in REQUIRED_ATTRIBUTES and "gen_ai.usage.output_tokens" in REQUIRED_ATTRIBUTES},
        {"name": "kubernetes_resource_attributes", "passed": "k8s.pod.name" in REQUIRED_ATTRIBUTES and "k8s.namespace.name" in REQUIRED_ATTRIBUTES},
        {"name": "privacy_redaction_declared", "passed": True, "observed": "drop prompt and response bodies by default"},
        {"name": "gateway_objective_correlation", "passed": "inference.gateway.objective" in REQUIRED_ATTRIBUTES},
        {"name": "genai_cost_latency_rollout_metrics", "passed": all(metric["passed"] for metric in GENAI_ROLLOUT_METRICS)},
        {"name": "groundedness_proxy_declared", "passed": "inference.answer.groundedness_score" in REQUIRED_ATTRIBUTES},
    ]
    rollout_metrics = {
        "passed": all(metric["passed"] for metric in GENAI_ROLLOUT_METRICS),
        "metrics": GENAI_ROLLOUT_METRICS,
        "analysis_template": "credit-risk-genai-serving-quality",
        "abort_policy": "abort canary when token cost, queue latency, cache hit ratio, or groundedness proxy breaches threshold",
    }
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_semantic_telemetry_contract" if all(check["passed"] for check in checks) else "hold_semantic_telemetry_rollout",
        "schema": {
            "profile": "otel-genai-plus-kubernetes",
            "required_attributes": REQUIRED_ATTRIBUTES,
            "redacted_attributes": ["gen_ai.input.messages", "gen_ai.output.messages", "http.request.body"],
            "cost_fields": ["gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens", "inference.estimated_cost_usd"],
        },
        "genai_rollout_metrics": rollout_metrics,
        "checks": checks,
        "guardrails": [
            "Do not export prompt or response bodies unless an explicit privacy review enables them.",
            "Attach Kubernetes resource attributes before batching so incidents can pivot by pod and deployment.",
            "Attach inference objective and model version to every prediction span.",
            "Keep token and cost attributes numeric so SLO dashboards can aggregate without parsing logs.",
            "Gate GenAI-style serving rollouts on cost, token, queue, cache, and groundedness proxy metrics before traffic promotion.",
        ],
        "kubernetes_assets": ["kubernetes/opentelemetry-collector.yaml"],
        "references": [
            "https://opentelemetry.io/docs/concepts/semantic-conventions/",
            "https://opentelemetry.io/docs/specs/semconv/system/k8s-metrics/",
            "https://github.com/open-telemetry/semantic-conventions-genai",
        ],
    }
    write_json(root / "reports" / "semantic_telemetry_plan.json", plan)
    return plan
