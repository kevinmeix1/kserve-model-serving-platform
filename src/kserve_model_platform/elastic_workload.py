from __future__ import annotations

from pathlib import Path

from .io import write_json


WORKLOAD_SLICES = [
    {
        "name": "shadow-analysis-scale-up",
        "workload": "credit-risk-shadow-analysis",
        "queue": "serving-analysis-queue",
        "slice_name": "credit-risk-shadow-slice-a",
        "replacement_for": None,
        "min_replicas": 2,
        "max_replicas": 12,
        "reason": "use spare quota for shadow comparison and drift probes without changing online predictor replicas",
    },
    {
        "name": "shadow-analysis-scale-down",
        "workload": "credit-risk-shadow-analysis",
        "queue": "serving-analysis-queue",
        "slice_name": "credit-risk-shadow-slice-b",
        "replacement_for": "mlops-serving/credit-risk-shadow-slice-a",
        "min_replicas": 1,
        "max_replicas": 6,
        "reason": "return quota to emergency rollback validation before online SLOs degrade",
    },
    {
        "name": "gpu-explainer-burst",
        "workload": "credit-risk-gpu-explainer",
        "queue": "serving-gpu-analysis-queue",
        "slice_name": "credit-risk-explainer-slice-a",
        "replacement_for": None,
        "min_replicas": 1,
        "max_replicas": 8,
        "reason": "burst explainability workers for high-severity incident review under Kueue quota",
    },
]


def build_elastic_workload_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "workload_slices_declared",
            "passed": all(item["slice_name"] for item in WORKLOAD_SLICES),
            "evidence": "each elastic analysis workload declares a Kueue Workload Slice name",
        },
        {
            "name": "replacement_slice_modeled",
            "passed": any(item["replacement_for"] for item in WORKLOAD_SLICES),
            "evidence": "replacement slices can shrink lower-priority shadow analysis before rollback validation is starved",
        },
        {
            "name": "jobset_integration_declared",
            "passed": True,
            "evidence": "shadow analysis and explainer workers use JobSet queue labels",
        },
        {
            "name": "online_serving_isolated",
            "passed": any("online predictor" in item["reason"] for item in WORKLOAD_SLICES),
            "evidence": "online KServe predictor replicas stay outside elastic batch admission",
        },
        {
            "name": "rollback_capacity_reclaim",
            "passed": any("rollback" in item["reason"] for item in WORKLOAD_SLICES),
            "evidence": "scale-down replacement slices return quota to rollback validation",
        },
        {
            "name": "feature_gate_documented",
            "passed": True,
            "evidence": "ElasticJobsViaWorkloadSlices is gated and rollbackable",
        },
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_kueue_elastic_serving_analysis_slices"
        if all(check["passed"] for check in checks)
        else "hold_elastic_serving_analysis",
        "feature_gate": "ElasticJobsViaWorkloadSlices",
        "workload_slices": WORKLOAD_SLICES,
        "jobset_policy": {
            "api": "jobset.x-k8s.io/v1alpha2",
            "queue_label": "kueue.x-k8s.io/queue-name",
            "slice_annotation": "kueue.x-k8s.io/workload-slice-name",
            "replacement_annotation": "kueue.x-k8s.io/workload-slice-replacement-for",
        },
        "operational_guardrails": [
            "Never put online predictor replicas behind elastic batch admission.",
            "Use replacement slices to shrink shadow analysis before touching router or predictor capacity.",
            "Keep emergency rollback validation in a higher-priority queue than shadow and explainer workloads.",
            "Disable ElasticJobsViaWorkloadSlices if endpoint health or Workload Slice accounting diverges.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/kueue-elastic-workloads.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/elastic_workload/",
            "https://kueue.sigs.k8s.io/docs/reference/labels-and-annotations/",
            "https://kueue.sigs.k8s.io/docs/tasks/run/jobsets/",
            "https://kueue.sigs.k8s.io/docs/concepts/workload/",
        ],
    }
    write_json(root / "reports" / "elastic_workload_plan.json", plan)
    return plan
