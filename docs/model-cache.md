# KServe Local Model Cache

`make model-cache` writes `.local/reports/model_cache_plan.json` and pairs it with `kserve/local-model-cache.yaml`.

This project models the production cold-start problem that shows up when model pods scale, roll back, or move nodes. The serving path keeps the existing PVC storage fallback, but the cache plan adds KServe LocalModel resources and modelcar OCI images so champion, challenger, and previous-champion artifacts can be preloaded on serving nodes.

## Operating Model

- Package each model as a modelcar OCI image with an explicit non-`latest` tag.
- Use `LocalModelNodeGroup` to define the serving node cache group and per-node storage limit.
- Use `LocalModelNamespaceCache` in `mlops-serving` so only serving `InferenceService` workloads in that namespace can use the cached model.
- Wait for enough cache copies to reach `ModelDownloaded` before increasing canary traffic.
- Keep the previous champion cached until the rollback window closes.
- Fall back to the existing `pvc://mlflow-models/...` storage URIs when the localmodel component is unavailable.

## Why It Matters

Canary and rollback decisions can be correct and still fail operationally if model pods cold-start slowly. KServe modelcars make the model artifact an immutable OCI object, and LocalModel cache status turns startup risk into an explicit release gate.

The plan intentionally blocks traffic shifts on cache readiness but does not classify cache misses as model-quality failures. A download error should hold the rollout and page the serving platform owner; it should not pollute model evaluation metrics.

## References

- KServe resource concepts: <https://kserve.github.io/website/docs/concepts/resources>
- KServe localmodel install component: <https://kserve.github.io/website/docs/install/overview>
- KServe OCI Modelcars: <https://kserve.github.io/website/docs/model-serving/storage/providers/oci>
- KServe control plane API: <https://kserve.github.io/website/docs/reference/crd-api>
