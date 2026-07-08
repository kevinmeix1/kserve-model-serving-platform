# Runtime Security

`make runtime-security` writes `.local/reports/runtime_security_plan.json`.

## What It Shows

- Kubernetes v1.36 user namespaces GA readiness with `pod.spec.hostUsers: false`.
- Runtime prerequisites for user namespaces: Linux 6.3+, idmap-capable filesystems, containerd 2.0+ or CRI-O 1.25+, and runc 1.2+ or crun 1.13+.
- Kubernetes v1.36 fine-grained kubelet authorization (`KubeletFineGrainedAuthz`) using `nodes/metrics`, `nodes/stats`, `nodes/healthz`, and `nodes/pods`.
- A policy example that blocks new serving monitoring roles from granting broad `nodes/proxy`.
- Reduced blast radius for KServe canaries, telemetry readers, and rollback smoke probes.

## Production Notes

User namespaces let serving containers keep the compatibility benefits of container-root where needed while mapping the process to an unprivileged host UID. This is useful for model server images that still need local runtime setup but should not become host-root if compromised.

Fine-grained kubelet authorization removes the old pattern where telemetry agents needed `nodes/proxy` just to read kubelet metrics or health. The manifest grants only the kubelet subresources required for KServe telemetry and leaves privileged kubelet access as an audited break-glass path.

## Senior Review Angle

This shows that serving security is part of the rollout control plane. It links KServe predictors, telemetry, rollback probes, RBAC, admission policy, and node-pool readiness instead of treating runtime isolation as a generic cluster setting.

References:

- https://kubernetes.io/docs/concepts/workloads/pods/user-namespaces/
- https://kubernetes.io/docs/tasks/configure-pod-container/user-namespaces/
- https://kubernetes.io/blog/2026/04/24/kubernetes-v1-36-fine-grained-kubelet-authorization-ga/
- https://kubernetes.io/blog/2026/04/23/kubernetes-v1-36-userns-ga/
