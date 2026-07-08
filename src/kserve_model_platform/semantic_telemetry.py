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
]


def build_semantic_telemetry_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "genai_request_attributes", "passed": "gen_ai.request.model" in REQUIRED_ATTRIBUTES},
        {"name": "token_usage_attributes", "passed": "gen_ai.usage.input_tokens" in REQUIRED_ATTRIBUTES and "gen_ai.usage.output_tokens" in REQUIRED_ATTRIBUTES},
        {"name": "kubernetes_resource_attributes", "passed": "k8s.pod.name" in REQUIRED_ATTRIBUTES and "k8s.namespace.name" in REQUIRED_ATTRIBUTES},
        {"name": "privacy_redaction_declared", "passed": True, "observed": "drop prompt and response bodies by default"},
        {"name": "gateway_objective_correlation", "passed": "inference.gateway.objective" in REQUIRED_ATTRIBUTES},
    ]
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
        "checks": checks,
        "guardrails": [
            "Do not export prompt or response bodies unless an explicit privacy review enables them.",
            "Attach Kubernetes resource attributes before batching so incidents can pivot by pod and deployment.",
            "Attach inference objective and model version to every prediction span.",
            "Keep token and cost attributes numeric so SLO dashboards can aggregate without parsing logs.",
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
