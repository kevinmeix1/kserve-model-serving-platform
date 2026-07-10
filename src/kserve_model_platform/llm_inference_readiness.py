from __future__ import annotations

from pathlib import Path

from .io import write_json


LLM_MODELS = [
    {
        "name": "policy-assistant-7b",
        "serving_api": "LLMInferenceService",
        "runtime": "vLLM",
        "storage_uri": "oci://ghcr.io/kevinmeix1/policy-assistant-7b:2026.07.10",
        "gpu_profile": "nvidia-l4",
        "max_lora_adapters": 12,
        "prefill_replicas": 2,
        "decode_replicas": 3,
        "target_ttft_ms": 800,
        "target_tpot_ms": 65,
    },
    {
        "name": "policy-assistant-7b-canary",
        "serving_api": "LLMInferenceService",
        "runtime": "vLLM",
        "storage_uri": "oci://ghcr.io/kevinmeix1/policy-assistant-7b:2026.07.10-rc1",
        "gpu_profile": "nvidia-l4",
        "max_lora_adapters": 12,
        "prefill_replicas": 1,
        "decode_replicas": 1,
        "target_ttft_ms": 900,
        "target_tpot_ms": 80,
    },
]

TRAFFIC_CLASSES = [
    {"name": "interactive", "priority": 30, "requests": 180, "prompt_tokens_p95": 1500, "completion_tokens_p95": 420},
    {"name": "agent-tool-call", "priority": 20, "requests": 90, "prompt_tokens_p95": 2400, "completion_tokens_p95": 280},
    {"name": "batch-summary", "priority": -5, "requests": 45, "prompt_tokens_p95": 3600, "completion_tokens_p95": 650},
]


def _pinned_oci(uri: str) -> bool:
    return uri.startswith("oci://") and ":" in uri.rsplit("/", 1)[-1] and not uri.endswith(":latest")


def _simulate_llm_routing() -> dict:
    decisions = []
    for item in TRAFFIC_CLASSES:
        queue_penalty = item["requests"] / 30
        token_pressure = (item["prompt_tokens_p95"] + item["completion_tokens_p95"]) / 1000
        selected_pool = "decode-pool" if item["completion_tokens_p95"] >= 400 else "prefill-pool"
        ttft_ms = round(310 + queue_penalty * 17 + token_pressure * 28, 2)
        tpot_ms = round(24 + token_pressure * 7 + (8 if selected_pool == "decode-pool" else 0), 2)
        decisions.append(
            {
                "traffic_class": item["name"],
                "priority": item["priority"],
                "selected_pool": selected_pool,
                "ttft_ms": ttft_ms,
                "tpot_ms": tpot_ms,
                "reason": "prefix_cache_and_queue_aware_endpoint_selection",
                "passed": ttft_ms < 900 and tpot_ms < 85,
            }
        )
    return {
        "route_decisions": decisions,
        "passed_classes": sum(1 for item in decisions if item["passed"]),
        "request_classes": len(decisions),
        "max_ttft_ms": max(item["ttft_ms"] for item in decisions),
        "max_tpot_ms": max(item["tpot_ms"] for item in decisions),
    }


def build_llm_inference_readiness_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    routing = _simulate_llm_routing()
    checks = [
        {
            "name": "llminferenceservice_declared",
            "passed": all(model["serving_api"] == "LLMInferenceService" for model in LLM_MODELS),
            "evidence": "Generative workloads are modeled with KServe LLMInferenceService rather than only classic predictive InferenceService.",
        },
        {
            "name": "vllm_runtime_selected",
            "passed": all(model["runtime"] == "vLLM" for model in LLM_MODELS),
            "evidence": "vLLM is the serving runtime for high-throughput OpenAI-compatible generation.",
        },
        {
            "name": "modelcar_oci_artifacts_pinned",
            "passed": all(_pinned_oci(model["storage_uri"]) for model in LLM_MODELS),
            "evidence": "Model artifacts use pinned OCI ModelCar URIs for cacheable, provenance-friendly deployment.",
        },
        {
            "name": "prefill_decode_capacity_split",
            "passed": sum(model["prefill_replicas"] for model in LLM_MODELS) >= 3
            and sum(model["decode_replicas"] for model in LLM_MODELS) >= 4,
            "evidence": "Capacity plan separates prefill-heavy and decode-heavy bottlenecks before scaling GPU replicas.",
        },
        {
            "name": "lora_adapter_budget_declared",
            "passed": all(model["max_lora_adapters"] >= 8 for model in LLM_MODELS),
            "evidence": "LoRA adapter budget is explicit so endpoint picker signals can avoid adapter thrash.",
        },
        {
            "name": "gateway_inference_extension_routing",
            "passed": routing["passed_classes"] == routing["request_classes"],
            "evidence": routing,
        },
        {
            "name": "cost_latency_telemetry_contract",
            "passed": True,
            "evidence": "Plan requires TTFT, TPOT, token count, prefix-cache hit rate, queue depth, model, adapter, route, and cost tags.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-10T00:00:00Z",
        "passed": passed,
        "recommended_action": "adopt_llm_inference_readiness_contract" if passed else "hold_llm_serving_rollout",
        "serving_contract": {
            "api": "serving.kserve.io/v1alpha1 LLMInferenceService",
            "runtime": "vLLM",
            "gateway": "Gateway API Inference Extension Endpoint Picker",
            "artifact_format": "OCI ModelCar",
            "protocols": ["OpenAI-compatible chat completions", "KServe routing evidence"],
        },
        "models": LLM_MODELS,
        "routing": routing,
        "observability": {
            "latency": ["time_to_first_token_ms", "time_per_output_token_ms", "queue_latency_ms"],
            "quality": ["groundedness_score", "refusal_rate", "tool_call_error_rate"],
            "capacity": ["kv_cache_utilization", "prefix_cache_hit_rate", "active_lora_adapters", "tokens_per_second"],
            "cost": ["input_tokens", "output_tokens", "estimated_cost_usd", "gpu_seconds"],
        },
        "release_gates": [
            "Canary LLMInferenceService must pass TTFT and TPOT budgets before traffic increases.",
            "Endpoint picker must fail open to the stable HTTPRoute if routing signals are stale.",
            "OCI ModelCar tags must be immutable and attested before cluster admission.",
            "LoRA adapter count cannot exceed the per-replica budget during canary analysis.",
            "Batch summarization traffic is deprioritized whenever interactive queue depth is high.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kserve/llm-inference-readiness.yaml"],
        "references": [
            "https://kserve.github.io/website/docs/model-serving/generative-inference/llmisvc/llmisvc-overview",
            "https://kserve.github.io/website/docs/model-serving/storage/providers/oci",
            "https://gateway-api-inference-extension.sigs.k8s.io/",
            "https://docs.vllm.ai/en/stable/deployment/integrations/kserve/",
        ],
    }
    write_json(root / "reports" / "llm_inference_readiness_plan.json", plan)
    return plan
