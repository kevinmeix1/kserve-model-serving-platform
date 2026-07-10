# Gateway API Inference Extension

`make inference-gateway-plan` writes `.local/reports/inference_gateway_plan.json` and pairs it with `kubernetes/inference-gateway-routing.yaml`.

## What It Shows

- Stable v1 `InferencePool` routing for self-hosted model-server pods.
- Endpoint Picker integration with `FailOpen` fallback to the existing KServe route.
- Alpha `InferenceObjective` priority examples for online and batch traffic.
- Gateway API `HTTPRoute` backend references that target an `InferencePool` instead of a Service.
- Alerts for endpoint-picker unavailability so rollback automation can react.
- A deterministic routing simulation that scores endpoint pressure from queue depth, KV-cache utilization, prefix-cache hit rate, token demand, and request criticality.
- Endpoint Picker HPA and PDB examples so the router is treated as production infrastructure instead of a single demo pod.
- A fail-open route that moves traffic to the champion-only KServe predictor when the Endpoint Picker becomes unavailable.

## Production Notes

The Inference Extension is useful when round-robin routing is not enough. Endpoint Pickers can use queue depth, KV-cache utilization, prefix-cache status, and adapter availability to route to the best model-server replica. The stable surface is `InferencePool`; `InferenceObjective` is still alpha in current provider docs, so this project keeps it explicit and guarded behind rollout notes.

## Demo Evidence

`make inference-gateway-plan` writes a report with:

- `simulation.route_decisions`: request class, objective priority, selected endpoint, p95 estimate, and SLO result.
- `simulation.endpoint_load`: assigned requests and weighted token demand per endpoint.
- `simulation.fail_open_drill`: expected behavior when the Endpoint Picker is unhealthy.
- `checks`: stable API, objective modeling, fallback definition, simulated SLO pass, and fail-open pass.

The main dashboard surfaces this evidence in the **Inference Gateway** panel after `make demo`.

## Interview Talking Points

- Use `InferencePool` as the stable routing target and keep `InferenceObjective` behind provider-specific rollout controls while it remains alpha.
- Endpoint Pickers should be horizontally scaled, protected by PDBs, monitored separately from model-server pods, and allowed to fail open to a known-safe KServe route.
- Critical online traffic should outrank batch explainability and shadow traffic; the generated simulation shows this with objective priorities.
- Routing decisions should be observable. The project records endpoint pressure inputs and estimated p95/SLO results so rollback analysis has evidence.

References: Kubernetes Gateway API Inference Extension, InferencePool v1 docs, Istio integration guide, and GKE Inference Gateway notes.
