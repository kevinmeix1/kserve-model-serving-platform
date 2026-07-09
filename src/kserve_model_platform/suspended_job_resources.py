from __future__ import annotations

from pathlib import Path

from .io import write_json


RESOURCE_MUTATIONS = [
    {
        "name": "shadow-replay-job",
        "suspended": True,
        "current_requests": {"cpu": "8", "memory": "16Gi"},
        "proposed_requests": {"cpu": "5", "memory": "12Gi"},
        "quota_reason": "Shadow replay can shrink CPU while live traffic remains on the KServe router.",
        "unsuspend_gate": "quota_fit_and_route_generation_current",
    },
    {
        "name": "gpu-explainer-job",
        "suspended": True,
        "current_requests": {"cpu": "4", "memory": "16Gi", "nvidia.com/gpu": "1"},
        "proposed_requests": {"cpu": "3", "memory": "12Gi", "nvidia.com/gpu": "1"},
        "quota_reason": "Explainer diagnostics fit the serving GPU quota after model cache warmup.",
        "unsuspend_gate": "quota_fit_and_model_cache_warm",
    },
    {
        "name": "route-conformance-job",
        "suspended": True,
        "current_requests": {"cpu": "2", "memory": "4Gi"},
        "proposed_requests": {"cpu": "3", "memory": "6Gi"},
        "quota_reason": "Route convergence checks need extra memory before validating HTTPRoute observedGeneration.",
        "unsuspend_gate": "pool_slots_available_and_route_observed_generation_match",
    },
]

PROTECTED_JOBS = [
    {
        "name": "active-credit-risk-router-smoke",
        "suspended": False,
        "reason": "Active route smoke checks should not be rewritten while KServe traffic probes are running.",
    },
    {
        "name": "running-champion-rollback-probe",
        "suspended": False,
        "reason": "Rollback validation stays pinned to the last known champion and should use replacement Jobs if resources change.",
    },
]


def _resource_delta_ok(item: dict) -> bool:
    current_cpu = float(item["current_requests"]["cpu"])
    proposed_cpu = float(item["proposed_requests"]["cpu"])
    return 0.25 <= proposed_cpu / current_cpu <= 1.5


def build_suspended_job_resource_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    feature = {
        "name": "MutablePodResourcesForSuspendedJobs",
        "state": "Kubernetes v1.36 beta and enabled by default",
        "scope": "resource requests and limits in the Pod template of suspended Jobs",
        "not_for": "actively running KServe route probes; use in-place resize or a replacement Job instead",
    }
    checks = [
        {
            "name": "beta_feature_status_recorded",
            "passed": feature["state"].startswith("Kubernetes v1.36 beta"),
            "evidence": "The plan records the Kubernetes v1.36 beta status before recommending use.",
        },
        {
            "name": "only_suspended_jobs_mutated",
            "passed": all(item["suspended"] for item in RESOURCE_MUTATIONS),
            "evidence": "Every mutable resource plan starts from spec.suspend=true.",
        },
        {
            "name": "active_kserve_smoke_jobs_not_resized",
            "passed": all(not item["suspended"] for item in PROTECTED_JOBS),
            "evidence": "Active router smoke and rollback probes are explicitly excluded.",
        },
        {
            "name": "queue_controller_reason_recorded",
            "passed": all(item["quota_reason"] for item in RESOURCE_MUTATIONS),
            "evidence": "Every mutation is tied to route, cache, Kueue quota, or Airflow pool evidence.",
        },
        {
            "name": "resource_delta_bounded",
            "passed": all(_resource_delta_ok(item) for item in RESOURCE_MUTATIONS),
            "evidence": "CPU request changes are bounded so admission cannot silently rewrite serving economics.",
        },
        {
            "name": "unsuspend_gate_requires_route_or_quota_fit",
            "passed": all("quota" in item["unsuspend_gate"] or "pool" in item["unsuspend_gate"] or "route" in item["unsuspend_gate"] for item in RESOURCE_MUTATIONS),
            "evidence": "Unsuspend gates require quota, Airflow pool, model cache, or current route generation evidence.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-09T00:00:00Z",
        "recommended_action": "enable_suspended_job_resource_mutation_for_queued_serving_jobs" if passed else "keep_suspended_job_resources_observe_only",
        "passed": passed,
        "feature": feature,
        "resource_mutations": RESOURCE_MUTATIONS,
        "protected_jobs": PROTECTED_JOBS,
        "checks": checks,
        "runbook": [
            "Create shadow replay, route conformance, and explainer Jobs with spec.suspend=true when queue admission owns start time.",
            "Patch CPU, memory, GPU, or extended resource requests only while the serving-analysis Job is suspended.",
            "Record Kueue quota, model cache readiness, and HTTPRoute observedGeneration before unsuspending.",
            "Use in-place resize or replacement Jobs for active route probes; do not mutate active KServe smoke templates.",
        ],
        "references": [
            "https://kubernetes.io/blog/2026/04/27/kubernetes-v1-36-mutable-pod-resources-for-suspended-jobs/",
            "https://kubernetes.io/docs/concepts/workloads/controllers/job/",
        ],
    }
    write_json(root / "reports" / "suspended_job_resources_plan.json", plan)
    return plan
