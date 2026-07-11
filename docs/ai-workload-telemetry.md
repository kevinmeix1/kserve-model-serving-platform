# AI Workload Telemetry Readiness

`make demo` emits `reports/ai_workload_telemetry_plan.json`, a serving-focused
contract that maps KServe predictors, canaries, transformers, and explainers to
Kubernetes resource signals, Gateway routing evidence, OpenTelemetry attributes,
SLOs, and rollback actions.

This is intentionally operational: a reviewer can see which telemetry fields
must exist before traffic is shifted, which SLOs protect the champion model, and
which resource signals explain a bad canary.

Current practice reflected here:
- KServe serving systems separate predictor, transformer, explainer, and rollout concerns.
- Kubernetes pod-level resource and DRA status signals are used for serving readiness.
- Gateway route weights are part of the telemetry contract, not just deployment YAML.
- GenAI-style model/token attributes are allow-listed and kept away from raw feature payloads.
