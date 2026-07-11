# Semantic Telemetry

`make semantic-telemetry-plan` writes `.local/reports/semantic_telemetry_plan.json` and pairs it with `kubernetes/opentelemetry-collector.yaml`.

## What It Shows

- GenAI-style request, response, token, and cost attributes for inference spans.
- Kubernetes resource attributes for namespace, pod, and deployment correlation.
- Inference Gateway objective and model version on prediction spans.
- Collector-side redaction of prompt, response, and raw request bodies by default.
- A lightweight telemetry contract that dashboards and incident tooling can validate.
- Progressive rollout gates for token budget, cost per thousand requests, endpoint-picker queue latency, prefix-cache hit ratio, and groundedness proxy score.

## Production Notes

The point is not to export more data. It is to export predictable data. Portable semantic attributes let a serving incident move from gateway objective to model version to Kubernetes pod without custom parsing, while redaction keeps sensitive prompts and response content out of default telemetry.

For generative or long-context serving, success rate and p95 latency are not enough. A canary can be technically healthy while burning token budget, missing prefix-cache savings, or producing low-groundedness responses. The `credit-risk-genai-serving-quality` AnalysisTemplate models those checks as promotion gates so Argo Rollouts can abort before traffic moves further.
