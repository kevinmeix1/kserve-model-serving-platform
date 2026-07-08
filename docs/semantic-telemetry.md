# Semantic Telemetry

`make semantic-telemetry-plan` writes `.local/reports/semantic_telemetry_plan.json` and pairs it with `kubernetes/opentelemetry-collector.yaml`.

## What It Shows

- GenAI-style request, response, token, and cost attributes for inference spans.
- Kubernetes resource attributes for namespace, pod, and deployment correlation.
- Inference Gateway objective and model version on prediction spans.
- Collector-side redaction of prompt, response, and raw request bodies by default.
- A lightweight telemetry contract that dashboards and incident tooling can validate.

## Production Notes

The point is not to export more data. It is to export predictable data. Portable semantic attributes let a serving incident move from gateway objective to model version to Kubernetes pod without custom parsing, while redaction keeps sensitive prompts and response content out of default telemetry.
