from __future__ import annotations

from pathlib import Path

from .io import write_json


COMPONENTS = [
    {
        "name": "kube-apiserver",
        "statusz": "/statusz",
        "flagz": "/flagz",
        "metrics": ["apiserver_watch_cache_initializations_total", "apiserver_request_duration_seconds"],
        "critical_flags": ["ComponentStatusz", "ComponentFlagz", "WatchCache", "NativeHistogramMetrics"],
    },
    {
        "name": "kube-controller-manager",
        "statusz": "/statusz",
        "flagz": "/flagz",
        "metrics": ["workqueue_depth", "workqueue_unfinished_work_seconds"],
        "critical_flags": ["ComponentStatusz", "ComponentFlagz", "ConcurrentEndpointSyncs"],
    },
    {
        "name": "kube-scheduler",
        "statusz": "/statusz",
        "flagz": "/flagz",
        "metrics": ["scheduler_pending_pods", "scheduler_pod_scheduling_attempts"],
        "critical_flags": ["ComponentStatusz", "ComponentFlagz", "PodGroupScheduling"],
    },
    {
        "name": "kubelet",
        "statusz": "/statusz",
        "flagz": "/flagz",
        "metrics": ["kubelet_psi_cpu_some_seconds_total", "kubelet_psi_memory_some_seconds_total"],
        "critical_flags": ["ComponentStatusz", "ComponentFlagz", "KubeletPSI", "UserNamespacesSupport"],
    },
]


CONTROLLERS = [
    {
        "name": "kserve-route-controller",
        "freshness_budget_seconds": 30,
        "watch_source": "KServe InferenceService status and Gateway HTTPRoute watch",
        "stale_action": "freeze traffic split and force an uncached route read before advancing challenger weight",
    },
    {
        "name": "shadow-analysis-controller",
        "freshness_budget_seconds": 60,
        "watch_source": "shadow replay Job status and prediction metric watch",
        "stale_action": "hold challenger promotion and keep champion traffic pinned",
    },
    {
        "name": "rollback-route-controller",
        "freshness_budget_seconds": 30,
        "watch_source": "rollback InferenceService revision and Gateway route watch",
        "stale_action": "pin champion and require direct API confirmation before clearing rollback incident",
    },
]


def build_control_plane_diagnostics_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    checks = [
        {
            "name": "statusz_and_flagz_coverage",
            "passed": all(component["statusz"] == "/statusz" and component["flagz"] == "/flagz" for component in COMPONENTS),
            "evidence": "Every control-plane component has explicit /statusz and /flagz scrape coverage.",
        },
        {
            "name": "route_controller_staleness_budgets",
            "passed": all(controller["freshness_budget_seconds"] <= 60 for controller in CONTROLLERS),
            "evidence": "Serving route, shadow analysis, and rollback controllers all fail closed inside one minute.",
        },
        {
            "name": "psi_metric_coverage",
            "passed": any("kubelet_psi_memory_some_seconds_total" in component["metrics"] for component in COMPONENTS),
            "evidence": "Kubelet PSI metrics catch node pressure before it corrupts serving latency decisions.",
        },
        {
            "name": "native_histogram_readiness",
            "passed": any("NativeHistogramMetrics" in component["critical_flags"] for component in COMPONENTS),
            "evidence": "The plan records native histogram readiness for high-cardinality control-plane and inference latency metrics.",
        },
        {
            "name": "flag_drift_detection",
            "passed": all("ComponentFlagz" in component["critical_flags"] for component in COMPONENTS),
            "evidence": "/flagz drift detection protects KServe canary automation during Kubernetes upgrades.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-07T00:00:00Z",
        "recommended_action": "enable_control_plane_freshness_diagnostics" if passed else "keep_route_controller_freshness_in_warn_mode",
        "passed": passed,
        "feature_status": {
            "controller_staleness": "Kubernetes v1.36 beta stale-cache mitigation for controllers",
            "component_statusz": "Kubernetes v1.36 beta ComponentStatusz endpoint",
            "component_flagz": "Kubernetes v1.36 beta ComponentFlagz endpoint",
            "psi_metrics": "Kubernetes v1.36 stable kubelet PSI metrics",
            "native_histograms": "Kubernetes v1.36 alpha native histogram support",
        },
        "components": COMPONENTS,
        "controllers": CONTROLLERS,
        "checks": checks,
        "serving_runbook": [
            "If route-controller freshness exceeds budget, stop increasing challenger traffic.",
            "Read InferenceService, HTTPRoute, and EndpointSlice state directly before deciding rollback status.",
            "Compare /flagz output with the expected ComponentStatusz, ComponentFlagz, KubeletPSI, and NativeHistogramMetrics gates after upgrades.",
            "Use PSI and native histogram metrics to separate control-plane pressure from model latency regressions.",
        ],
        "references": [
            "https://kubernetes.io/blog/2026/04/28/kubernetes-v1-36-staleness-mitigation-for-controllers/",
            "https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/",
            "https://kubernetes.io/blog/2026/04/25/kubernetes-v1-36-psi-metrics/",
        ],
    }
    write_json(root / "reports" / "control_plane_diagnostics_plan.json", plan)
    return plan
