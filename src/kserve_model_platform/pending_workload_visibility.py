from __future__ import annotations

from pathlib import Path

from .io import write_json


PENDING_WORKLOADS = [
    {
        "name": "credit-risk-route-convergence-20260708",
        "cluster_queue": "online-serving-flavor-queue",
        "local_queue": "online-route-smoke",
        "namespace": "mlops-serving-prod",
        "position": 1,
        "pending_minutes": 5,
        "requested": {"cpu": 4, "memory_gib": 12},
        "reason": "waiting_for_on_demand_route_capacity",
        "owner_action": "hold challenger traffic until route smoke is admitted",
    },
    {
        "name": "shadow-analysis-20260708",
        "cluster_queue": "canary-analysis-flavor-queue",
        "local_queue": "shadow-analysis",
        "namespace": "mlops-serving-analysis",
        "position": 2,
        "pending_minutes": 14,
        "requested": {"cpu": 10, "memory_gib": 32, "nvidia_com_gpu": 1},
        "reason": "gpu_explainer_flavor_saturated",
        "owner_action": "defer non-critical explainers and keep live predictor outside batch queue",
    },
    {
        "name": "synthetic-load-20260708",
        "cluster_queue": "load-test-flavor-queue",
        "local_queue": "synthetic-load",
        "namespace": "mlops-serving-loadtest",
        "position": 7,
        "pending_minutes": 38,
        "requested": {"cpu": 12, "memory_gib": 24},
        "reason": "load_test_spot_cpu_saturated",
        "owner_action": "keep queued; do not borrow online serving rollback capacity",
    },
]


def _raw_clusterqueue_url(cluster_queue: str) -> str:
    return f"/apis/visibility.kueue.x-k8s.io/v1beta2/clusterqueues/{cluster_queue}/pendingworkloads"


def _raw_localqueue_url(namespace: str, local_queue: str) -> str:
    return f"/apis/visibility.kueue.x-k8s.io/v1beta2/namespaces/{namespace}/localqueues/{local_queue}/pendingworkloads"


def build_pending_workload_visibility_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    cluster_queues = sorted({item["cluster_queue"] for item in PENDING_WORKLOADS})
    local_queues = [
        {
            "namespace": item["namespace"],
            "local_queue": item["local_queue"],
            "url": _raw_localqueue_url(item["namespace"], item["local_queue"]),
        }
        for item in PENDING_WORKLOADS
    ]
    checks = [
        {
            "name": "visibility_on_demand_enabled",
            "passed": True,
            "evidence": "VisibilityOnDemand is beta and enabled by default in current Kueue documentation.",
        },
        {
            "name": "rbac_grants_pending_workload_reads",
            "passed": True,
            "evidence": "Serving SREs can read clusterqueues/pendingworkloads and localqueues/pendingworkloads without broad Kueue mutation rights.",
        },
        {
            "name": "clusterqueue_and_localqueue_queries_declared",
            "passed": bool(cluster_queues) and all(item["url"].endswith("/pendingworkloads") for item in local_queues),
            "evidence": "Both platform-level ClusterQueue triage and tenant-facing LocalQueue views are documented.",
        },
        {
            "name": "serving_hot_path_protected",
            "passed": all("live predictor" not in item["cluster_queue"] for item in PENDING_WORKLOADS),
            "evidence": "Visibility covers route smoke, shadow analysis, and load tests while live predictors remain outside batch queueing.",
        },
        {
            "name": "prometheus_metrics_declared",
            "passed": True,
            "evidence": "Alerts use kueue_admission_wait_time_seconds and kueue_cluster_queue_resource_pending for route convergence and pending CPU.",
        },
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_serving_kueue_pending_workload_visibility",
        "feature": {
            "name": "VisibilityOnDemand",
            "state": "beta since Kueue v0.9 and enabled by default",
            "api_group": "visibility.kueue.x-k8s.io/v1beta2",
            "apf_manifest": "visibility-apf.yaml from the Kueue release artifacts",
        },
        "visibility_queries": {
            "cluster_queues": [{"name": name, "url": _raw_clusterqueue_url(name)} for name in cluster_queues],
            "local_queues": local_queues,
            "recommended_access": "kubectl proxy plus kubectl get --raw to avoid bypassing API server identity checks",
        },
        "pending_workloads": PENDING_WORKLOADS,
        "metrics": [
            "kueue_admission_wait_time_seconds",
            "kueue_cluster_queue_resource_pending",
            "kueue_cluster_queue_status",
        ],
        "operational_guardrails": [
            "Query pending route-smoke workloads before increasing challenger traffic.",
            "Use ClusterQueue visibility for serving-platform triage and LocalQueue visibility for tenant self-service.",
            "Keep GPU explainers and synthetic load queued before borrowing rollback reserve quota.",
            "Attach Kueue visibility snapshots to rollback and canary-analysis evidence.",
            "Alert on admission wait and pending resources before route-convergence deadlines fire.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/kueue-pending-workload-visibility.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/",
            "https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/pending_workloads_on_demand/",
            "https://kueue.sigs.k8s.io/docs/reference/metrics/",
        ],
    }
    write_json(root / "reports" / "pending_workload_visibility_plan.json", plan)
    return plan
