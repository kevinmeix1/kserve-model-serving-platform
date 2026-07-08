# KServe In-Place Pod Resize Controls

`make inplace-resize-plan` writes `.local/reports/inplace_resize_plan.json` and pairs it with `kubernetes/inplace-pod-resize.yaml`.

## What It Shows

- Kubernetes v1.35 stable in-place CPU and memory resizing through the `pods/resize` subresource.
- Kubernetes v1.36 beta in-place vertical scaling for pod-level resources through `spec.resources`.
- KServe-specific resize policies for challenger predictors, shadow-analysis pods, and rollback smoke probes.
- VPA `InPlaceOrRecreate` wiring for autoscaler-compatible predictor recommendations.
- Alerts for `PodResizePending` and `PodResizeInProgress` so canary automation does not mix old and new resource envelopes.

## Production Notes

Serving traffic makes resize semantics high stakes. The rollout controller should not advance `canaryTrafficPercent` while a challenger or shadow-analysis pod has resize conditions active. CPU startup boosts are useful for warmup and cold-cache pressure, but memory changes should respect `resizePolicy` and may require a restart.

The demo treats resize as a resource-efficiency control around KServe rollouts: keep the last good revision serving, record the resource state in canary evidence, and shrink idle rollback smoke probes rather than deleting the fast rollback path.

## References

- Kubernetes v1.35 in-place Pod Resize GA: <https://kubernetes.io/blog/2025/12/19/kubernetes-v1-35-in-place-pod-resize-ga/>
- Kubernetes v1.36 pod-level resource resize beta: <https://kubernetes.io/blog/2026/04/30/kubernetes-v1-36-inplace-pod-level-resources-beta/>
- Kubernetes resize container resources task: <https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/>
