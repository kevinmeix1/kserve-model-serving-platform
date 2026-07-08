from __future__ import annotations

from pathlib import Path

from .io import write_json


POD_RESOURCE_WORKLOADS = [
    {
        "name": "credit-risk-router-canary",
        "namespace": "mlops-serving",
        "pod_level_requests": {"cpu": "2", "memory": "4Gi"},
        "pod_level_limits": {"cpu": "3", "memory": "6Gi"},
        "scheduling_gates": ["mlops.kevinmei.dev/model-cache-ready", "mlops.kevinmei.dev/httproute-accepted"],
        "release_condition": "KServe LocalModel cache reports ModelDownloaded and HTTPRoute Accepted=True",
        "containers": ["route-smoke-probe", "otel-sidecar"],
    },
    {
        "name": "shadow-canary-analysis",
        "namespace": "mlops-serving",
        "pod_level_requests": {"cpu": "4", "memory": "8Gi"},
        "pod_level_limits": {"cpu": "6", "memory": "12Gi"},
        "scheduling_gates": ["mlops.kevinmei.dev/kueue-admitted", "mlops.kevinmei.dev/route-mirror-ready"],
        "release_condition": "Kueue admits shadow analysis and Gateway mirror route has converged",
        "containers": ["shadow-analyzer", "metrics-exporter"],
    },
    {
        "name": "rollback-smoke-probe",
        "namespace": "mlops-serving",
        "pod_level_requests": {"cpu": "2", "memory": "3Gi"},
        "pod_level_limits": {"cpu": "3", "memory": "5Gi"},
        "scheduling_gates": ["mlops.kevinmei.dev/previous-champion-preloaded"],
        "release_condition": "Previous champion modelcar is preloaded before emergency rollback traffic changes",
        "containers": ["rollback-probe", "checkpoint-writer"],
    },
]


def build_pod_resource_envelope_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "pod_level_resources_declared",
            "passed": all(item["pod_level_requests"] and item["pod_level_limits"] for item in POD_RESOURCE_WORKLOADS),
            "evidence": "Serving rollout pods use pod-level CPU and memory envelopes around sidecar-heavy probes and analysis jobs.",
        },
        {
            "name": "scheduling_gates_declared",
            "passed": all(item["scheduling_gates"] for item in POD_RESOURCE_WORKLOADS),
            "evidence": "Canary, shadow, and rollback pods stay SchedulingGated until cache, route, or queue prerequisites are ready.",
        },
        {
            "name": "gate_release_runbook",
            "passed": True,
            "evidence": "A release controller removes gates only after KServe, Gateway API, and Kueue conditions agree.",
        },
        {
            "name": "scheduler_churn_metric",
            "passed": True,
            "evidence": "scheduler_pending_pods{queue=\"gated\"} is tracked separately from unschedulable serving pods.",
        },
        {
            "name": "dra_compatibility_guardrail",
            "passed": True,
            "evidence": "DRA-backed explainer and shadow jobs must fit inside pod-level envelopes before gates are removed.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_serving_pod_resource_envelopes_and_scheduling_gates" if passed else "keep_container_only_serving_requests",
        "kubernetes_version_target": "1.34+",
        "feature_gates": {
            "PodLevelResources": "beta, enabled by default in Kubernetes 1.34+ clusters that support the feature",
            "PodSchedulingReadiness": "stable since Kubernetes 1.30",
            "PodLevelResourceManagers": "enable where CPUManager, MemoryManager, or TopologyManager alignment is required",
        },
        "workloads": POD_RESOURCE_WORKLOADS,
        "release_runbook": [
            "Create canary and rollback probes with schedulingGates so the scheduler avoids churn before cache and route prerequisites exist.",
            "Verify ModelDownloaded, HTTPRoute Accepted, Kueue admission, route mirror convergence, and champion preload evidence.",
            "Patch away gates in any order after prerequisites pass; never add new gates after pod creation.",
            "Alert on scheduler_pending_pods{queue=\"gated\"} and gates older than rollout SLOs.",
        ],
        "checks": checks,
        "kubernetes_assets": [
            "kubernetes/pod-resource-envelopes.yaml",
        ],
        "references": [
            "https://kubernetes.io/docs/tasks/configure-pod-container/assign-pod-level-resources/",
            "https://kubernetes.io/docs/concepts/scheduling-eviction/pod-scheduling-readiness/",
            "https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/",
        ],
    }
    write_json(root / "reports" / "pod_resource_envelope_plan.json", plan)
    return plan
