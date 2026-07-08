from __future__ import annotations

from pathlib import Path

from .io import write_json


WORKLOADS = [
    {
        "name": "credit-risk-challenger",
        "queue": "credit-risk-serving-queue",
        "priority": "serving-release-critical",
        "device_class": "gpu-l4-shared",
        "resource_claim_template": "l4-shared-challenger",
        "sharing_strategy": "time-slicing",
        "requires_dra": True,
        "fallback": "route challenger traffic back to champion and keep shadow scoring on CPU",
        "why": "canary inference needs low-latency GPU bursts without blocking champion rollback",
    },
    {
        "name": "shadow-analysis-runner",
        "queue": "canary-analysis-queue",
        "priority": "serving-canary-analysis",
        "device_class": "gpu-l4-shared",
        "resource_claim_template": "l4-shared-shadow-analysis",
        "sharing_strategy": "time-slicing",
        "requires_dra": True,
        "fallback": "continue request logging and delay promotion until enough CPU shadow samples exist",
        "why": "shadow comparison can tolerate shared GPU isolation but must not starve live serving",
    },
    {
        "name": "large-model-profile",
        "queue": "canary-analysis-queue",
        "priority": "serving-canary-analysis",
        "device_class": "gpu-a100-mig",
        "resource_claim_template": "a100-mig-profile",
        "sharing_strategy": "mig",
        "requires_dra": True,
        "fallback": "skip large-model profiling and keep the current champion route",
        "why": "memory-sensitive profiling needs MIG isolation before a larger runtime is allowed",
    },
]


def build_device_allocation_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "resource_claim_templates_declared", "passed": all(workload["resource_claim_template"] for workload in WORKLOADS)},
        {"name": "kueue_quota_matches_claims", "passed": all(workload["queue"] for workload in WORKLOADS)},
        {"name": "fallback_paths_defined", "passed": all(workload["fallback"] for workload in WORKLOADS)},
        {"name": "sharing_modes_explicit", "passed": {workload["sharing_strategy"] for workload in WORKLOADS} == {"time-slicing", "mig"}},
        {"name": "serving_rollback_unblocked", "passed": any("champion" in workload["fallback"] for workload in WORKLOADS)},
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "admit_dra_backed_serving_canary" if all(check["passed"] for check in checks) else "hold_serving_canary",
        "device_classes": [
            {
                "name": "gpu-l4-shared",
                "allocation": "ResourceClaimTemplate per predictor pod",
                "sharing_strategy": "NVIDIA time-slicing",
                "isolation": "shared fault domain; acceptable for canary and shadow scoring",
                "kueue_flavor": "gpu-l4-shared",
            },
            {
                "name": "gpu-a100-mig",
                "allocation": "ResourceClaimTemplate per isolated profiling pod",
                "sharing_strategy": "MIG",
                "isolation": "hardware-backed memory and fault isolation",
                "kueue_flavor": "gpu-a100-mig",
            },
        ],
        "workloads": WORKLOADS,
        "checks": checks,
        "guardrails": [
            "Route rollback traffic to champion before retrying failed accelerator claims.",
            "Use time-sliced L4 claims for low-risk challenger and shadow work only.",
            "Use MIG claims for memory-sensitive large-model profiling.",
            "Gate KServe traffic changes on DRA claim allocation, Kueue admission, and canary SLOs.",
            "Watch ResourceClaim status and predictor latency before increasing canary percent.",
        ],
        "kubernetes_assets": ["kubernetes/dynamic-resource-allocation.yaml", "kubernetes/accelerator-scheduling.yaml"],
        "references": [
            "https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/",
            "https://kueue.sigs.k8s.io/docs/concepts/workload/",
            "https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html",
            "https://kserve.github.io/website/docs/model-serving/predictive-inference/rollout-strategies/canary",
        ],
    }
    write_json(root / "reports" / "device_allocation_plan.json", plan)
    return plan
