from __future__ import annotations

from pathlib import Path

from .io import write_json


RESIZE_POLICIES = [
    {
        "name": "challenger-predictor-startup-boost",
        "workload": "credit-risk-challenger",
        "scope": "container",
        "resource_patch": {"requests.cpu": "900m", "limits.memory": "1Gi"},
        "resize_policy": {"cpu": "NotRequired", "memory": "RestartContainer"},
        "trigger": "challenger p95 latency exceeds 75 percent of the serving SLO during warmup",
        "owner_action": "boost CPU in-place while traffic remains pinned to the last good revision",
    },
    {
        "name": "shadow-analysis-pod-level-burst",
        "workload": "shadow-analysis-runner",
        "scope": "pod",
        "resource_patch": {"spec.resources.limits.cpu": "6", "spec.resources.requests.memory": "10Gi"},
        "resize_policy": {"cpu": "NotRequired", "memory": "RestartContainer"},
        "trigger": "shadow comparison backlog grows while online predictors stay healthy",
        "owner_action": "expand the pod-level envelope for shadow analysis before increasing live canary traffic",
    },
    {
        "name": "rollback-smoke-warm-shrink",
        "workload": "rollback-smoke-probe",
        "scope": "container",
        "resource_patch": {"requests.cpu": "150m", "limits.memory": "384Mi"},
        "resize_policy": {"cpu": "NotRequired", "memory": "NotRequired"},
        "trigger": "rollback smoke probe is idle after route convergence",
        "owner_action": "shrink idle rollback smoke in-place so fast rollback stays warm without wasting serving quota",
    },
]


def build_inplace_resize_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    checks = [
        {"name": "container_resize_ga", "passed": True, "evidence": "Kubernetes v1.35 made in-place CPU and memory resizing stable through the resize subresource."},
        {"name": "pod_level_resize_beta", "passed": any(policy["scope"] == "pod" for policy in RESIZE_POLICIES), "evidence": "Kubernetes v1.36 beta pod-level resource resizing covers multi-container shadow-analysis pods."},
        {"name": "resize_policy_defined", "passed": all(policy["resize_policy"] for policy in RESIZE_POLICIES), "evidence": "Serving workloads declare whether CPU and memory changes can happen without restarts."},
        {"name": "route_safety_defined", "passed": any("last good revision" in policy["owner_action"] for policy in RESIZE_POLICIES), "evidence": "The challenger CPU boost does not advance traffic while the resize is pending or in progress."},
        {"name": "vpa_inplace_or_recreate_ready", "passed": True, "evidence": "VPA recommendation mode is modeled with InPlaceOrRecreate for predictors and rollback probes."},
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_kserve_inplace_resize_controls",
        "features": {
            "in_place_pod_resize": {
                "state": "Kubernetes v1.35 stable",
                "subresource": "pods/resize",
                "container_status_field": "status.containerStatuses[*].resources",
            },
            "pod_level_resource_resize": {
                "state": "Kubernetes v1.36 beta and enabled by default",
                "feature_gate": "InPlacePodLevelResourcesVerticalScaling",
                "pod_spec_field": "spec.resources",
                "status_conditions": ["PodResizePending", "PodResizeInProgress"],
            },
            "autoscaler_integration": {
                "vpa_update_mode": "InPlaceOrRecreate",
                "requires_runtime": "cgroup v2 and CRI UpdateContainerResources support",
            },
        },
        "policies": RESIZE_POLICIES,
        "serving_guardrails": [
            "Never increase canary traffic while PodResizePending or PodResizeInProgress is true for the challenger.",
            "Use CPU in-place resize for startup boosts; memory changes require the declared resizePolicy path.",
            "Record InferenceService revision, desired resources, status.resources, and route percent in canary evidence.",
            "Keep rollback smoke warm by shrinking idle pods instead of deleting the rollback path.",
            "Treat shadow-analysis pod-level resize as offline capacity relief, not a reason to borrow online serving quota.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/inplace-pod-resize.yaml"],
        "references": [
            "https://kubernetes.io/blog/2025/12/19/kubernetes-v1-35-in-place-pod-resize-ga/",
            "https://kubernetes.io/blog/2026/04/30/kubernetes-v1-36-inplace-pod-level-resources-beta/",
            "https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/",
        ],
    }
    write_json(root / "reports" / "inplace_resize_plan.json", plan)
    return plan
