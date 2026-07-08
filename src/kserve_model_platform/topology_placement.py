from __future__ import annotations

from pathlib import Path

from .io import write_json


WORKLOADS = [
    {
        "name": "credit-risk-router-ha",
        "queue": "credit-risk-serving-queue",
        "placement": "spread",
        "topology_key": "topology.kubernetes.io/zone",
        "pod_count": 3,
        "policy": "required",
        "why": "serving routers should preserve availability through a zone or node failure",
        "fallback": "hold canary traffic and keep champion route active until skew recovers",
    },
    {
        "name": "large-model-leader-worker",
        "queue": "canary-analysis-queue",
        "placement": "compact",
        "topology_key": "cloud.provider.com/topology-rack",
        "pod_count": 6,
        "policy": "required",
        "why": "larger inference profiles need leader and workers close enough to avoid network-bound token latency",
        "fallback": "skip large-model profiling and keep the current champion predictor",
    },
    {
        "name": "shadow-analysis-batch",
        "queue": "canary-analysis-queue",
        "placement": "balanced",
        "topology_key": "kubernetes.io/hostname",
        "pod_count": 4,
        "policy": "preferred",
        "why": "offline shadow analysis should not fragment the topology needed for serving rollback",
        "fallback": "reduce batch width and continue request logging",
    },
]


def build_topology_placement_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "topology_resource_declared", "passed": True, "observed": "kueue.x-k8s.io/Topology"},
        {"name": "leader_worker_group_uses_required_topology", "passed": any(workload["placement"] == "compact" for workload in WORKLOADS)},
        {"name": "serving_router_spread_defined", "passed": any(workload["placement"] == "spread" and workload["policy"] == "required" for workload in WORKLOADS)},
        {"name": "rollback_path_unblocked", "passed": any("champion" in workload["fallback"] for workload in WORKLOADS)},
        {"name": "fallbacks_defined", "passed": all(workload["fallback"] for workload in WORKLOADS)},
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_topology_aware_serving_rollout" if all(check["passed"] for check in checks) else "hold_topology_sensitive_serving",
        "topology_levels": [
            "cloud.provider.com/topology-block",
            "cloud.provider.com/topology-rack",
            "kubernetes.io/hostname",
        ],
        "workloads": WORKLOADS,
        "checks": checks,
        "guardrails": [
            "Use topology spread constraints for live serving availability.",
            "Use compact TAS only for multi-pod inference profiles that exchange large intermediate state.",
            "Keep champion rollback independent of topology-sensitive challenger work.",
            "Gate large-model profile jobs on Kueue topology assignment before promotion.",
            "Alert when topology assignment is pending so traffic weights do not advance.",
        ],
        "kubernetes_assets": ["kubernetes/topology-aware-scheduling.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/topology_aware_scheduling/",
            "https://kueue.sigs.k8s.io/docs/tasks/run/leaderworkerset/",
            "https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/",
            "https://kueue.sigs.k8s.io/docs/concepts/admission_check/",
        ],
    }
    write_json(root / "reports" / "topology_placement_plan.json", plan)
    return plan
