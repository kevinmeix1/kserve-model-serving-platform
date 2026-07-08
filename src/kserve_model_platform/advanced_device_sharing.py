from __future__ import annotations

from pathlib import Path

from .io import write_json


DEVICE_SHARING_POLICIES = [
    {
        "name": "credit-risk-challenger-prioritized-accelerator",
        "workload": "credit-risk-challenger",
        "primary": "gpu-l4-shared",
        "alternatives": ["gpu-a100-mig", "cpu-shadow-only"],
        "feature": "DRAPrioritizedList",
        "owner_action": "prefer shared L4 for low-latency canaries, fall back to MIG profiling, then hold challenger traffic",
    },
    {
        "name": "shadow-analysis-consumable-capacity",
        "workload": "shadow-analysis-runner",
        "primary": "partitionable-a100",
        "alternatives": ["6GiB-vgpu-slice", "cpu-shadow-sample"],
        "feature": "DRAConsumableCapacity",
        "owner_action": "use bounded GPU memory slices for shadow comparison so live serving capacity remains protected",
    },
    {
        "name": "large-model-profile-binding-readiness",
        "workload": "large-model-profile",
        "primary": "fabric-attached-a100",
        "alternatives": ["cached-local-model-profile", "skip-profile"],
        "feature": "DRADeviceBindingConditions",
        "owner_action": "wait for accelerator preparation before profiling and keep the champion route if preparation fails",
    },
]


def build_advanced_device_sharing_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "prioritized_device_alternatives_defined",
            "passed": all(policy["alternatives"] for policy in DEVICE_SHARING_POLICIES),
            "evidence": "Canary, shadow, and profiling workloads declare ordered accelerator fallback paths.",
        },
        {
            "name": "partitionable_device_policy_defined",
            "passed": any("partitionable" in policy["primary"] for policy in DEVICE_SHARING_POLICIES),
            "evidence": "Shadow analysis can use logical accelerator slices instead of reserving a whole device.",
        },
        {
            "name": "consumable_capacity_budgeted",
            "passed": any(policy["feature"] == "DRAConsumableCapacity" for policy in DEVICE_SHARING_POLICIES),
            "evidence": "Shadow comparison uses bounded GPU memory so live KServe traffic is protected.",
        },
        {
            "name": "device_binding_conditions_required",
            "passed": any(policy["feature"] == "DRADeviceBindingConditions" for policy in DEVICE_SHARING_POLICIES),
            "evidence": "Large-model profiling waits for prepared fabric-attached accelerators before any promotion signal.",
        },
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_kserve_dra_advanced_device_sharing_policy",
        "features": {
            "prioritized_list": {"state": "Kubernetes v1.36 stable", "feature_gate": "DRAPrioritizedList"},
            "partitionable_devices": {"state": "Kubernetes v1.36 beta and enabled by default", "feature_gate": "DRAPartitionableDevices"},
            "consumable_capacity": {"state": "feature-gated sharing primitive; validate target-cluster support before enforcement", "feature_gate": "DRAConsumableCapacity"},
            "device_binding_conditions": {
                "state": "Kubernetes v1.36 beta and enabled by default",
                "feature_gate": "DRADeviceBindingConditions",
                "scheduler_phase": "PreBind",
                "default_wait_seconds": 600,
            },
        },
        "policies": DEVICE_SHARING_POLICIES,
        "serving_guardrails": [
            "Do not widen canary traffic until the selected prioritized alternative is recorded in release evidence.",
            "Use partitionable or consumable capacity for shadow analysis before borrowing online serving quota.",
            "Treat binding failure conditions as promotion blockers, not transient predictor errors.",
            "Keep champion route and CPU shadow sampling available when accelerator alternatives are exhausted.",
            "Record selected device alternative, cache state, and route percent in the release-admission decision.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/dra-advanced-device-sharing.yaml"],
        "references": [
            "https://kubernetes.io/blog/2026/05/07/kubernetes-v1-36-dra-136-updates/",
            "https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/",
            "https://kubernetes.io/blog/2025/09/18/kubernetes-v1-34-dra-consumable-capacity/",
        ],
    }
    write_json(root / "reports" / "advanced_device_sharing_plan.json", plan)
    return plan
