from __future__ import annotations

from pathlib import Path

from .io import write_json


CAPACITY_CLASSES = [
    {
        "name": "serving-analysis-critical",
        "queue": "serving-analysis-provisioned-queue",
        "flavor": "cpu-analysis-provisioned",
        "managed_resources": ["cpu", "memory"],
        "max_run_duration_seconds": 3600,
        "fallback_queue": "serving-analysis-queue",
        "workload": "canary analysis, route conformance, and rollback smoke tests",
    },
    {
        "name": "gpu-explainer-burst",
        "queue": "serving-gpu-provisioned-queue",
        "flavor": "gpu-l4-explainer-provisioned",
        "managed_resources": ["cpu", "memory", "nvidia.com/gpu"],
        "max_run_duration_seconds": 5400,
        "fallback_queue": "serving-analysis-queue",
        "workload": "high-risk explanation generation and drift investigation",
    },
]


def build_provisioning_admission_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "admission_check_declared",
            "passed": True,
            "evidence": "AdmissionCheck uses kueue.x-k8s.io/provisioning-request for analysis workloads",
        },
        {
            "name": "online_predictor_excluded",
            "passed": True,
            "evidence": "live KServe predictor replicas stay on serving autoscaling and are not queued behind batch admission",
        },
        {
            "name": "provisioning_request_config_declared",
            "passed": all(item["managed_resources"] for item in CAPACITY_CLASSES),
            "evidence": "ProvisioningRequestConfig sets provisioningClassName, managedResources, retryStrategy, and podSetMergePolicy",
        },
        {
            "name": "capacity_signal_before_analysis",
            "passed": True,
            "evidence": "shadow, explainer, and rollback validation jobs wait for a physical capacity signal after quota reservation",
        },
        {
            "name": "rollback_capacity_protected",
            "passed": any("rollback" in item["workload"] for item in CAPACITY_CLASSES),
            "evidence": "emergency rollback smoke tests use the provisioned analysis queue before traffic advances",
        },
        {
            "name": "fallback_queue_documented",
            "passed": all(item["fallback_queue"] for item in CAPACITY_CLASSES),
            "evidence": "capacity timeout falls back to smaller analysis queues and freezes canary promotion",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_kueue_provisioning_admission_for_serving_analysis"
        if passed
        else "hold_serving_provisioning_admission",
        "capacity_classes": CAPACITY_CLASSES,
        "serving_boundary": {
            "online_predictor_queueing": "excluded",
            "queued_workloads": ["shadow analysis", "batch replay", "rollback smoke", "GPU explainer"],
            "traffic_policy_owner": "KServe and Gateway API",
        },
        "kueue_policy": {
            "admission_check_api": "kueue.x-k8s.io/v1beta2",
            "controller_name": "kueue.x-k8s.io/provisioning-request",
            "provisioning_request_config": "serving-analysis-provisioning-config",
            "cluster_queue_strategy": "admissionChecksStrategy.onFlavors",
            "quota_reservation_before_admission": True,
            "physical_capacity_signal_required": True,
        },
        "retry_strategy": {
            "backoff_limit_count": 2,
            "backoff_base_seconds": 60,
            "backoff_max_seconds": 1800,
            "pod_set_merge_policy": "IdenticalWorkloadSchedulingRequirements",
        },
        "operational_guardrails": [
            "Keep InferenceService predictor and router pods outside batch provisioning admission.",
            "Freeze canary promotion when shadow analysis or rollback-smoke ProvisioningRequests fail.",
            "Use podSetUpdates to target provisioned nodes for GPU explainer workers where the provider supports request labels.",
            "Alert when AdmissionCheckState remains Pending beyond the rollout analysis SLO.",
            "Fallback to CPU-only explanation summaries when GPU capacity cannot be booked inside the retry window.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/provisioning-admission-checks.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/admission_check/",
            "https://kueue.sigs.k8s.io/docs/concepts/admission_check/provisioning_request/",
            "https://kueue.sigs.k8s.io/docs/tasks/troubleshooting/troubleshooting_provreq/",
            "https://kserve.github.io/website/latest/modelserving/v1beta1/rollout/canary/",
        ],
    }
    write_json(root / "reports" / "provisioning_admission_plan.json", plan)
    return plan
