from __future__ import annotations

from pathlib import Path

from .io import write_json


def build_accelerator_capacity_plan(root: str | Path, *, project: str, primary_workload: str) -> dict:
    root = Path(root)
    plan = {
        "project": project,
        "generated_at": "2026-07-07T00:00:00Z",
        "primary_workload": primary_workload,
        "profiles": [
            {
                "name": "cpu-burst",
                "use_case": "request validation, routing tests, and report generation",
                "node_selector": {"workload-class": "cpu-burst"},
                "kueue_flavor": "cpu-spot",
                "quota": {"cpu": "32", "memory": "128Gi"},
                "cost_control": "spot-first with on-demand fallback for release-critical tasks",
            },
            {
                "name": "gpu-shared-l4",
                "use_case": "online canary inference, profiling, and shadow evaluation",
                "node_selector": {"accelerator": "nvidia-l4"},
                "kueue_flavor": "gpu-l4-shared",
                "quota": {"nvidia.com/gpu": "4", "memory": "256Gi"},
                "sharing_mode": "NVIDIA GPU Operator time-slicing for non-isolated canary and smoke-test workloads",
            },
            {
                "name": "gpu-mig-a100",
                "use_case": "large model inference where memory and fault isolation matter",
                "node_selector": {"accelerator": "nvidia-a100"},
                "kueue_flavor": "gpu-a100-mig",
                "quota": {"nvidia.com/mig-1g.10gb": "8"},
                "sharing_mode": "MIG profiles for stronger isolation than time-slicing",
            },
        ],
        "scheduler_controls": [
            "Kueue ResourceFlavors map quotas to accelerator node labels and taints.",
            "Dynamic Resource Allocation is documented as the forward path for device-specific claims.",
            "KServe can combine concurrency-based autoscaling with GPU-specific node placement.",
            "KEDA backlog triggers scale workers while Kueue protects scarce GPU capacity.",
        ],
        "guardrails": [
            "Use CPU nodes for local demo and contract checks.",
            "Reserve shared L4 GPUs for canaries, profiling, and low-risk shadow scoring.",
            "Use MIG A100 slices only when isolation or memory guarantees are required.",
            "Require signed, digest-pinned images before enabling enforce mode in policy-controller.",
        ],
        "kubernetes_assets": ["kubernetes/accelerator-scheduling.yaml"],
    }
    write_json(root / "reports" / "accelerator_capacity_plan.json", plan)
    return plan
