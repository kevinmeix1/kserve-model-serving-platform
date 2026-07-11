# Transformer And Explainer Readiness

`make transformer-explainer-readiness` writes `.local/reports/transformer_explainer_readiness_plan.json` and pairs it with `kserve/transformer-explainer-topology.yaml`.

## What It Shows

- KServe predictor, transformer, and explainer roles are modeled explicitly.
- Transformer readiness includes predictor health, not only transformer container health.
- The explainer path is asynchronous so high-risk explanations do not inflate p95 serving latency.
- The synchronous transformer plus predictor latency budget stays bounded.
- Collocation is treated as a design decision, not a default shortcut.
- Each stage declares a fallback so the champion prediction route stays available during transformer, predictor, or explainer incidents.

## Production Choice

KServe’s default transformer and predictor topology allows independent scaling. This project keeps that default for the credit-risk serving path, because transform latency, predictor latency, and explainer backlog fail in different ways.

The manifest still documents the collocation decision. Collocation is appropriate when the transformer and predictor are tightly coupled, when sidecar overhead dominates, or when network latency is larger than the transform cost. Here, the current choice is separate transformer plus async explainer so the champion route remains predictable during canary and incident windows.

## Operator Workflow

1. Check transformer readiness and predictor health-check evidence.
2. Hold canary traffic if transformer-predictor health diverges.
3. Keep explanations deferred when the async queue exceeds the budget.
4. Pin Gateway routing to champion if predictor health or transform correctness fails.
5. Attach transformer latency, predictor latency, queue depth, and route generation to canary evidence.

## References

- KServe architecture and data plane: <https://kserve.github.io/website/docs/intro>
- KServe transformer and predictor collocation: <https://kserve.github.io/website/docs/model-serving/predictive-inference/transformers/collocation>
- KServe ServingRuntime: <https://kserve.github.io/website/docs/concepts/resources/servingruntime>
