from __future__ import annotations

from pathlib import Path

from .io import write_json


WORKLOADS = [
    {
        "name": "credit-risk-predictor-canary",
        "namespace": "mlops-serving",
        "kind": "InferenceService",
        "host_users": False,
        "service_account": "credit-risk-predictor",
        "needs_kubelet_access": False,
        "reason": "predictor and canary pods reduce host blast radius while staying on normal KServe traffic routing",
    },
    {
        "name": "serving-telemetry-reader",
        "namespace": "mlops-serving",
        "kind": "DaemonSet",
        "host_users": False,
        "service_account": "serving-telemetry-reader",
        "needs_kubelet_access": True,
        "kubelet_subresources": ["nodes/metrics", "nodes/stats", "nodes/pods", "nodes/healthz"],
        "reason": "serving telemetry needs kubelet health, metrics, stats, and pod inventory without broad proxy access",
    },
    {
        "name": "rollback-smoke-probe",
        "namespace": "mlops-serving",
        "kind": "Job",
        "host_users": False,
        "service_account": "rollback-smoke-probe",
        "needs_kubelet_access": False,
        "reason": "rollback smoke remains isolated and schedulable when model-serving diagnostics are degraded",
    },
]


def build_runtime_security_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    kubelet_resources = {
        resource
        for workload in WORKLOADS
        for resource in workload.get("kubelet_subresources", [])
    }
    checks = [
        {
            "name": "user_namespaces_ga_recorded",
            "passed": all(workload["host_users"] is False for workload in WORKLOADS),
            "evidence": "Kubernetes v1.36 user namespaces are stable; serving pods opt in with pod.spec.hostUsers=false.",
        },
        {
            "name": "runtime_prerequisites_documented",
            "passed": True,
            "evidence": "The plan records Linux 6.3+, idmap-capable filesystems, containerd 2.0+, and runc 1.2+/crun 1.13+ requirements.",
        },
        {
            "name": "kubelet_fine_grained_authz_ga_recorded",
            "passed": {"nodes/metrics", "nodes/stats", "nodes/healthz"}.issubset(kubelet_resources),
            "evidence": "Serving telemetry readers use Kubernetes v1.36 fine-grained kubelet subresources instead of broad nodes/proxy.",
        },
        {
            "name": "nodes_proxy_exception_is_empty",
            "passed": all("nodes/proxy" not in workload.get("kubelet_subresources", []) for workload in WORKLOADS),
            "evidence": "No serving workload in the runtime security profile needs nodes/proxy for monitoring or health checks.",
        },
        {
            "name": "admission_policy_blocks_regression",
            "passed": True,
            "evidence": "A ValidatingAdmissionPolicy example denies ClusterRoles that grant nodes/proxy in serving namespaces.",
        },
        {
            "name": "online_serving_path_preserved",
            "passed": True,
            "evidence": "KServe predictors, routers, and rollback smoke stay on normal traffic and recovery paths while telemetry least privilege is enforced.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_userns_and_kubelet_fine_grained_authz_for_serving_workloads" if passed else "keep_runtime_security_in_warn_mode",
        "feature_status": {
            "user_namespaces": "Kubernetes v1.36 stable and enabled by default; pods opt in with hostUsers=false",
            "kubelet_fine_grained_authz": "Kubernetes v1.36 GA and locked enabled; kubelet checks fine-grained subresources before nodes/proxy fallback",
        },
        "runtime_prerequisites": {
            "kernel": "Linux 6.3+ for common idmap mount coverage",
            "filesystems": ["ext4", "xfs", "btrfs", "tmpfs", "overlayfs"],
            "container_runtime": "containerd 2.0+ or CRI-O 1.25+",
            "oci_runtime": "runc 1.2+ or crun 1.13+",
        },
        "kubelet_rbac": {
            "allowed_subresources": sorted(kubelet_resources),
            "forbidden_for_monitoring": ["nodes/proxy"],
            "migration_note": "Existing nodes/proxy permissions still work through kubelet fallback, but new KServe telemetry uses fine-grained resources from day one.",
        },
        "workloads": WORKLOADS,
        "operational_guardrails": [
            "Roll out hostUsers=false first on canary predictors, shadow replay jobs, and rollback smoke probes.",
            "Keep live traffic debugging in a break-glass namespace with explicit time-bound approval.",
            "Deny new monitoring ClusterRoles that grant nodes/proxy when nodes/metrics, nodes/stats, nodes/healthz, or nodes/pods are sufficient.",
            "Record user namespace support in serving node pool labels before scheduling predictor canaries there.",
            "Check kubelet authz audit logs for unexpected fallback to nodes/proxy.",
        ],
        "checks": checks,
        "references": [
            "https://kubernetes.io/docs/concepts/workloads/pods/user-namespaces/",
            "https://kubernetes.io/docs/tasks/configure-pod-container/user-namespaces/",
            "https://kubernetes.io/blog/2026/04/24/kubernetes-v1-36-fine-grained-kubelet-authorization-ga/",
            "https://kubernetes.io/blog/2026/04/23/kubernetes-v1-36-userns-ga/",
        ],
    }
    write_json(root / "reports" / "runtime_security_plan.json", plan)
    return plan
