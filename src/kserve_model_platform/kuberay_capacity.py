from __future__ import annotations

from pathlib import Path

from .io import write_json


RAY_WORKLOADS = [
    {
        "name": "credit-risk-rayservice",
        "kind": "RayService",
        "queue": "credit-risk-serving-queue",
        "priority": "serving-critical",
        "min_workers": 2,
        "max_workers": 10,
        "gpus_per_worker": 0,
        "autoscaling": "elastic",
        "scheduling": "kueue_guarded_rayservice",
        "why": "scale Python feature transforms and explainability requests without coupling them to the predictor pod",
        "fallback": "route directly to KServe transformer and disable expensive explanations",
    },
    {
        "name": "shadow-canary-evaluator",
        "kind": "RayJob",
        "queue": "credit-risk-canary-queue",
        "priority": "release-critical",
        "min_workers": 1,
        "max_workers": 6,
        "gpus_per_worker": 0,
        "autoscaling": "elastic",
        "scheduling": "kueue_admitted_rayjob",
        "why": "parallelize challenger-versus-champion analysis before promotion",
        "fallback": "hold the canary at the current percentage and run serial Wilson interval checks",
    },
    {
        "name": "llm-risk-explainer",
        "kind": "RayJob",
        "queue": "credit-risk-explainer-queue",
        "priority": "opportunistic",
        "min_workers": 0,
        "max_workers": 4,
        "gpus_per_worker": 1,
        "autoscaling": "elastic",
        "scheduling": "preemptible_gpu_queue",
        "why": "batch low-priority explanation generation on idle GPUs",
        "fallback": "return deterministic feature-attribution reason codes only",
    },
]


def build_kuberay_capacity_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "rayservice_declared", "passed": any(workload["kind"] == "RayService" for workload in RAY_WORKLOADS)},
        {"name": "shadow_evaluator_declared", "passed": any(workload["name"] == "shadow-canary-evaluator" for workload in RAY_WORKLOADS)},
        {"name": "kueue_queue_labels_required", "passed": all(workload["queue"] for workload in RAY_WORKLOADS)},
        {"name": "elastic_autoscaling_modelled", "passed": all(workload["autoscaling"] == "elastic" for workload in RAY_WORKLOADS)},
        {"name": "fallbacks_defined", "passed": all(workload["fallback"] for workload in RAY_WORKLOADS)},
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_kuberay_shadow_analysis" if all(check["passed"] for check in checks) else "keep_shadow_analysis_serial",
        "workloads": RAY_WORKLOADS,
        "capacity": {
            "max_workers": sum(workload["max_workers"] for workload in RAY_WORKLOADS),
            "max_gpu_demand": sum(workload["max_workers"] * workload["gpus_per_worker"] for workload in RAY_WORKLOADS),
            "serving_reserved_workers": 3,
            "autoscaler_idle_timeout_seconds": 60,
        },
        "checks": checks,
        "guardrails": [
            "Keep predictor pods small and move bursty transforms to RayService workers.",
            "Run shadow and canary evaluation as Kueue-admitted RayJobs before promotion.",
            "Treat explanation generation as preemptible GPU work, never as a serving dependency.",
            "Rollback to the KServe transformer path when RayService readiness or queue admission fails.",
            "Expose RayService replica, queue wait, object-store spill, and request latency metrics.",
        ],
        "kubernetes_assets": ["kubernetes/kuberay-kueue-workloads.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/tasks/run/rayjobs/",
            "https://docs.ray.io/en/latest/cluster/kubernetes/k8s-ecosystem/kueue.html",
            "https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/rayservice.html",
        ],
    }
    write_json(root / "reports" / "kuberay_capacity_plan.json", plan)
    return plan
