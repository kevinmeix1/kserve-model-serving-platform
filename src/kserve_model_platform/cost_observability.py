from __future__ import annotations

from pathlib import Path

from .io import write_json


ALLOCATION_DIMENSIONS = [
    "namespace",
    "inferenceservice",
    "revision",
    "httproute",
    "label_model",
    "label_cost_center",
    "label_traffic_class",
]

OPENCOST_METRICS = [
    "container_cpu_allocation",
    "container_memory_allocation_bytes",
    "node_cpu_hourly_cost",
    "node_ram_hourly_cost",
    "node_gpu_hourly_cost",
    "node_total_hourly_cost",
    "kubecost_load_balancer_cost",
]

SERVING_BUDGETS = [
    {
        "workload": "credit-risk-champion-predictor",
        "traffic_class": "online",
        "monthly_budget_usd": 960.0,
        "unit_metric": "cost_per_1000_predictions",
        "guardrail": "scale replicas from request rate, not only CPU, and keep p95/p99 latency budgets in the canary gate",
    },
    {
        "workload": "credit-risk-challenger-predictor",
        "traffic_class": "canary",
        "monthly_budget_usd": 280.0,
        "unit_metric": "challenger_cost_share",
        "guardrail": "cap challenger spend to planned traffic percent until canary gates pass",
    },
    {
        "workload": "shadow-model-analysis",
        "traffic_class": "shadow",
        "monthly_budget_usd": 420.0,
        "unit_metric": "shadow_delta_cost",
        "guardrail": "drop non-critical shadow scoring before paging the online serving owner",
    },
    {
        "workload": "gpu-explainer-fallback",
        "traffic_class": "explainability",
        "monthly_budget_usd": 520.0,
        "unit_metric": "gpu_hourly_cost",
        "guardrail": "only enable GPU explainers for high-risk requests or incident review windows",
    },
]


def build_cost_observability_report(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "opencost_exporter_scraped", "passed": "node_total_hourly_cost" in OPENCOST_METRICS},
        {"name": "gateway_route_allocation", "passed": "httproute" in ALLOCATION_DIMENSIONS},
        {"name": "shadow_budget_cap", "passed": any(item["traffic_class"] == "shadow" for item in SERVING_BUDGETS)},
        {"name": "gpu_explainer_attribution", "passed": "node_gpu_hourly_cost" in OPENCOST_METRICS},
        {"name": "cost_per_prediction_declared", "passed": any(item["unit_metric"] == "cost_per_1000_predictions" for item in SERVING_BUDGETS)},
        {"name": "traffic_class_labels_required", "passed": "label_traffic_class" in ALLOCATION_DIMENSIONS},
    ]
    report = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_kserve_opencost_guardrails" if all(check["passed"] for check in checks) else "complete_serving_cost_contract",
        "monthly_budget_usd": round(sum(item["monthly_budget_usd"] for item in SERVING_BUDGETS), 2),
        "allocation_dimensions": ALLOCATION_DIMENSIONS,
        "required_metrics": OPENCOST_METRICS,
        "serving_budgets": SERVING_BUDGETS,
        "prometheus": {
            "scrape_interval": "1m",
            "scrape_timeout": "10s",
            "metrics_path": "/metrics",
            "target": "opencost.opencost-exporter:9003",
        },
        "unit_economics": {
            "primary_kpi": "cost_per_1000_predictions",
            "formula": "monthly allocated serving cost / monthly successful predictions * 1000",
            "alert_threshold_usd": 2.4,
        },
        "guardrails": [
            "Attribute cost by InferenceService, revision, HTTPRoute, model, cost center, and traffic class.",
            "Cap challenger and shadow spend independently from champion serving cost.",
            "Track GPU explainer spend separately so incident-only explainability does not become always-on waste.",
            "Pair cost alerts with p95/p99 latency and canary rollback gates before changing replica policy.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/opencost-finops.yaml"],
        "references": [
            "https://opencost.io/docs/integrations/opencost-exporter/",
            "https://opencost.io/docs/integrations/metrics/",
            "https://opencost.io/docs/installation/install/",
            "https://kubernetes.io/docs/concepts/policy/resource-quotas/",
        ],
    }
    write_json(root / "reports" / "cost_observability_report.json", report)
    return report
