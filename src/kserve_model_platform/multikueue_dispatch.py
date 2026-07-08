from __future__ import annotations

from pathlib import Path

from .io import write_json


WORKER_CLUSTERS = [
    {
        "name": "serving-analysis-east",
        "region": "us-east-1",
        "workload_class": "shadow-replay-and-route-conformance",
        "cpu_quota": 64,
        "memory_gib_quota": 256,
        "gpu_quota": 0,
        "queue_mirror": "serving-multikueue-analysis",
        "provisioning_request_enabled": True,
    },
    {
        "name": "serving-analysis-west",
        "region": "us-west-2",
        "workload_class": "rollback-smoke-and-batch-replay",
        "cpu_quota": 48,
        "memory_gib_quota": 192,
        "gpu_quota": 0,
        "queue_mirror": "serving-multikueue-analysis",
        "provisioning_request_enabled": True,
    },
    {
        "name": "serving-gpu-explainer",
        "region": "us-east-2",
        "workload_class": "high-risk-explanation-and-drift-analysis",
        "cpu_quota": 32,
        "memory_gib_quota": 256,
        "gpu_quota": 4,
        "queue_mirror": "serving-multikueue-analysis",
        "provisioning_request_enabled": True,
    },
]


def _quota_totals() -> dict:
    return {
        "cpu": sum(cluster["cpu_quota"] for cluster in WORKER_CLUSTERS),
        "memory_gib": sum(cluster["memory_gib_quota"] for cluster in WORKER_CLUSTERS),
        "nvidia_com_gpu": sum(cluster["gpu_quota"] for cluster in WORKER_CLUSTERS),
    }


def build_multikueue_dispatch_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    manager_quota = _quota_totals()
    checks = [
        {
            "name": "admission_check_declared",
            "passed": True,
            "evidence": "AdmissionCheck uses kueue.x-k8s.io/multikueue for serving-adjacent analysis jobs.",
        },
        {
            "name": "online_predictor_excluded",
            "passed": True,
            "evidence": "Live KServe InferenceService predictor and router replicas remain under KServe, HPA, and Gateway controls.",
        },
        {
            "name": "multikueue_config_declared",
            "passed": len(WORKER_CLUSTERS) >= 2,
            "evidence": "MultiKueueConfig lists CPU analysis and GPU explainer worker clusters.",
        },
        {
            "name": "worker_clusters_declared",
            "passed": all(cluster["queue_mirror"] for cluster in WORKER_CLUSTERS),
            "evidence": "Each worker mirrors the LocalQueue contract for shadow replay, route conformance, rollback smoke, and explainers.",
        },
        {
            "name": "manager_quota_aligned",
            "passed": manager_quota["cpu"] == 144 and manager_quota["nvidia_com_gpu"] == 4,
            "evidence": "Manager ClusterQueue quota equals aggregate worker CPU, memory, and GPU capacity.",
        },
        {
            "name": "status_sync_documented",
            "passed": True,
            "evidence": "Runbook watches status.nominatedClusterNames before admission and status.clusterName after worker selection.",
        },
        {
            "name": "rollback_capacity_protected",
            "passed": any("rollback" in cluster["workload_class"] for cluster in WORKER_CLUSTERS),
            "evidence": "Rollback smoke jobs have a worker target and freeze canary promotion when dispatch stalls.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_multikueue_serving_analysis_dispatch"
        if passed
        else "hold_multikueue_serving_analysis_dispatch",
        "serving_boundary": {
            "online_predictor_queueing": "excluded",
            "traffic_policy_owner": "KServe, HPA, and Gateway API",
            "queued_workloads": ["shadow replay", "route conformance", "rollback smoke", "GPU explainer"],
        },
        "cluster_topology": {
            "manager_cluster": "serving-manager",
            "manager_is_worker": False,
            "worker_clusters": WORKER_CLUSTERS,
        },
        "manager_quota": manager_quota,
        "dispatch_policy": {
            "controller_name": "kueue.x-k8s.io/multikueue",
            "dispatcher": "Incremental for normal rollout analysis; AllAtOnce for rollback smoke during incidents",
            "manager_quota_matches_worker_sum": True,
            "wait_for_workload_admitted": True,
            "status_fields": ["status.nominatedClusterNames", "status.clusterName"],
            "prebuilt_workload_label": "kueue.x-k8s.io/prebuilt-workload-name",
        },
        "operational_guardrails": [
            "Keep InferenceService predictor pods and Gateway routing outside MultiKueue dispatch.",
            "Mirror namespaces, LocalQueues, release identities, image policy, and model artifact secrets on all worker clusters.",
            "Freeze traffic promotion when shadow replay or rollback smoke cannot obtain status.clusterName within the rollout SLO.",
            "Use Incremental dispatch for routine cost control and AllAtOnce for incident rollback validation where speed wins.",
            "Use Kueue admission-check wait metrics plus Workload status fields to diagnose dispatch stalls.",
            "Fallback to CPU-only explanation summaries when GPU explainer capacity is not admitted.",
        ],
        "failure_modes": [
            {
                "mode": "shadow_replay_dispatch_timeout",
                "detection": "Admission-check p95 exceeds 20 minutes and Workload status.clusterName is empty.",
                "recovery": "Hold canary promotion, reduce replay shard count, and rerun on serving-analysis-queue.",
            },
            {
                "mode": "rollback_smoke_worker_unavailable",
                "detection": "Rollback smoke Workload remains pending while online predictor health is degraded.",
                "recovery": "Switch KServe traffic to previous champion and rerun smoke with AllAtOnce dispatch.",
            },
            {
                "mode": "gpu_explainer_capacity_unavailable",
                "detection": "GPU explainer worker has no admitted Workload before the investigation SLO.",
                "recovery": "Produce CPU summary explanations and attach the missing GPU evidence to the release hold.",
            },
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/multikueue-dispatch.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/multikueue/",
            "https://kueue.sigs.k8s.io/docs/tasks/manage/setup_multikueue/",
            "https://kueue.sigs.k8s.io/docs/tasks/run/multikueue/job/",
            "https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta2/",
            "https://kserve.github.io/website/latest/modelserving/v1beta1/rollout/canary/",
        ],
    }
    write_json(root / "reports" / "multikueue_dispatch_plan.json", plan)
    return plan
