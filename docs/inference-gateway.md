# Gateway API Inference Extension

`make inference-gateway-plan` writes `.local/reports/inference_gateway_plan.json` and pairs it with `kubernetes/inference-gateway-routing.yaml`.

## What It Shows

- Stable v1 `InferencePool` routing for self-hosted model-server pods.
- Endpoint Picker integration with `FailOpen` fallback to the existing KServe route.
- Alpha `InferenceObjective` priority examples for online and batch traffic.
- Gateway API `HTTPRoute` backend references that target an `InferencePool` instead of a Service.
- Alerts for endpoint-picker unavailability so rollback automation can react.

## Production Notes

The Inference Extension is useful when round-robin routing is not enough. Endpoint Pickers can use queue depth, KV-cache utilization, prefix-cache status, and adapter availability to route to the best model-server replica. The stable surface is `InferencePool`; `InferenceObjective` is still alpha in current provider docs, so this project keeps it explicit and guarded behind rollout notes.

References: Kubernetes Gateway API Inference Extension, InferencePool v1 docs, Istio integration guide, and GKE Inference Gateway notes.
