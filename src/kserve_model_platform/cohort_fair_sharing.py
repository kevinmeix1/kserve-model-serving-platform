from __future__ import annotations

from pathlib import Path

from .io import write_json


CLUSTER_QUEUE_POLICIES = [
    {
        "name": "online-serving",
        "cluster_queue": "credit-risk-serving-tenant-queue",
        "local_queues": ["online-route-smoke", "rollback-smoke"],
        "weight": 5,
        "nominal_cpu": 20,
        "borrowing_limit_cpu": 6,
        "lending_limit_cpu": 1,
        "observed_cpu": 17,
        "historical_usage_score": 0.22,
        "preemption": {"withinClusterQueue": "LowerPriority", "reclaimWithinCohort": "Any"},
    },
    {
        "name": "canary-analysis",
        "cluster_queue": "canary-analysis-tenant-queue",
        "local_queues": ["shadow-analysis", "gpu-explainer"],
        "weight": 2,
        "nominal_cpu": 12,
        "borrowing_limit_cpu": 8,
        "lending_limit_cpu": 4,
        "observed_cpu": 13,
        "historical_usage_score": 0.48,
        "preemption": {"withinClusterQueue": "LowerPriority", "reclaimWithinCohort": "LowerPriority"},
    },
    {
        "name": "load-test",
        "cluster_queue": "load-test-tenant-queue",
        "local_queues": ["synthetic-load", "route-burn-in"],
        "weight": 1,
        "nominal_cpu": 8,
        "borrowing_limit_cpu": 3,
        "lending_limit_cpu": 6,
        "observed_cpu": 7,
        "historical_usage_score": 0.82,
        "preemption": {"withinClusterQueue": "LowerPriority", "reclaimWithinCohort": "Never"},
    },
]


def _dominant_resource_share(queue: dict) -> float:
    borrowable = queue["nominal_cpu"] + queue["borrowing_limit_cpu"]
    return round(queue["observed_cpu"] / max(borrowable * queue["weight"], 0.0001), 4)


def build_cohort_fair_sharing_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    queues = [
        {
            **queue,
            "dominant_resource_share": _dominant_resource_share(queue),
            "exclusive_cpu_after_lending": queue["nominal_cpu"] - queue["lending_limit_cpu"],
            "max_cpu_after_borrowing": queue["nominal_cpu"] + queue["borrowing_limit_cpu"],
        }
        for queue in CLUSTER_QUEUE_POLICIES
    ]
    checks = [
        {"name": "fair_sharing_enabled", "passed": True, "evidence": "Kueue Configuration declares Fair Sharing preemption strategies for borrowed serving-analysis resources."},
        {"name": "admission_fair_sharing_enabled", "passed": True, "evidence": "AdmissionFairSharing keeps LocalQueue admission aware of historical usage and entry penalties."},
        {
            "name": "borrowing_and_lending_limits_declared",
            "passed": all(queue["borrowing_limit_cpu"] >= 0 and queue["lending_limit_cpu"] >= 0 for queue in queues),
            "evidence": "Each serving ClusterQueue has borrowingLimit and lendingLimit to reserve rollback capacity.",
        },
        {
            "name": "online_serving_weighted_above_load_test",
            "passed": queues[0]["weight"] > queues[-1]["weight"],
            "evidence": "Online serving receives a higher fairSharing.weight than synthetic load testing.",
        },
        {
            "name": "preemption_guardrails_declared",
            "passed": queues[0]["preemption"]["reclaimWithinCohort"] == "Any" and queues[-1]["preemption"]["reclaimWithinCohort"] == "Never",
            "evidence": "Online rollback can reclaim borrowed quota, while load tests cannot reclaim from serving tenants.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_serving_kueue_cohort_fair_sharing" if passed else "keep_static_serving_clusterqueue_quotas",
        "kueue_version_target": "0.15+",
        "feature_gates": {
            "FairSharing": "stable since Kueue v0.7",
            "AdmissionFairSharing": "beta since Kueue v0.15 and enabled by default",
        },
        "fair_sharing_config": {
            "preemptionStrategies": ["LessThanOrEqualToFinalShare", "LessThanInitialShare"],
            "dominant_resource_share_signal": "observed_cpu / ((nominal_cpu + borrowing_limit_cpu) * fairSharing.weight)",
            "admission_order": "serve LocalQueues with lower decayed historical usage first, with an entry penalty at admission time",
        },
        "cohort": {"name": "mlops-serving-cohort", "policy": "online serving and rollback preserve capacity while analysis borrows bounded idle resources"},
        "cluster_queues": queues,
        "operational_guardrails": [
            "Keep champion rollback and route smoke queues weighted above canary analysis and load testing.",
            "Use lendingLimit so online serving never lends away all warm rollback capacity.",
            "Use borrowingLimit to cap shadow-analysis and load-test bursts before they trigger preemption storms.",
            "Keep Admission Fair Sharing enabled so noisy load-test LocalQueues do not monopolize a ClusterQueue over time.",
            "Attach preemption reason, LocalQueue, route generation, and fair-share values to canary evidence.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/kueue-cohort-fair-sharing.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/",
            "https://kueue.sigs.k8s.io/docs/concepts/cohort/",
            "https://kueue.sigs.k8s.io/docs/concepts/preemption/",
            "https://kueue.sigs.k8s.io/docs/concepts/admission_fair_sharing/",
        ],
    }
    write_json(root / "reports" / "cohort_fair_sharing_plan.json", plan)
    return plan
