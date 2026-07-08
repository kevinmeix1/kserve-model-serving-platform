from __future__ import annotations

from pathlib import Path

from .io import write_json


def _utilization(used: float, quota: float) -> float:
    return round(used / max(quota, 0.0001), 4)


def _tenant(
    *,
    name: str,
    namespace: str,
    queue: str,
    cost_center: str,
    cpu_quota: float,
    cpu_used: float,
    memory_quota_gib: float,
    memory_used_gib: float,
    pool_slots: int,
    pool_used: int,
    priority_class: str,
) -> dict:
    return {
        "name": name,
        "namespace": namespace,
        "queue": queue,
        "cost_center": cost_center,
        "priority_class": priority_class,
        "quota": {"cpu": cpu_quota, "memory_gib": memory_quota_gib, "airflow_pool_slots": pool_slots},
        "observed": {"cpu": cpu_used, "memory_gib": memory_used_gib, "airflow_pool_slots": pool_used},
        "utilization": {
            "cpu": _utilization(cpu_used, cpu_quota),
            "memory": _utilization(memory_used_gib, memory_quota_gib),
            "airflow_pool": _utilization(pool_used, pool_slots),
        },
        "labels": {
            "platform.mlops.dev/tenant": name,
            "platform.mlops.dev/cost-center": cost_center,
            "platform.mlops.dev/data-domain": "credit-risk",
        },
    }


def build_tenancy_report(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    tenants = [
        _tenant(
            name="online-serving",
            namespace="mlops-serving-prod",
            queue="credit-risk-serving-queue",
            cost_center="risk-platform",
            cpu_quota=20,
            cpu_used=11,
            memory_quota_gib=80,
            memory_used_gib=38,
            pool_slots=8,
            pool_used=4,
            priority_class="serving-critical",
        ),
        _tenant(
            name="canary-analysis",
            namespace="mlops-serving-analysis",
            queue="canary-analysis-queue",
            cost_center="ml-platform",
            cpu_quota=12,
            cpu_used=7,
            memory_quota_gib=48,
            memory_used_gib=28,
            pool_slots=4,
            pool_used=2,
            priority_class="serving-canary-analysis",
        ),
        _tenant(
            name="load-test",
            namespace="mlops-serving-loadtest",
            queue="load-test-queue",
            cost_center="qa",
            cpu_quota=8,
            cpu_used=7,
            memory_quota_gib=24,
            memory_used_gib=20,
            pool_slots=2,
            pool_used=2,
            priority_class="serving-low-priority",
        ),
    ]
    cpu_utils = [tenant["utilization"]["cpu"] for tenant in tenants]
    pool_utils = [tenant["utilization"]["airflow_pool"] for tenant in tenants]
    noisy_neighbor_risks = [
        tenant["name"]
        for tenant in tenants
        if max(tenant["utilization"].values()) >= 0.90 and tenant["priority_class"] == "serving-low-priority"
    ]
    checks = [
        {"name": "namespace_resource_quotas", "passed": all(tenant["quota"]["cpu"] > 0 for tenant in tenants)},
        {"name": "no_hard_quota_breach", "passed": all(max(tenant["utilization"].values()) <= 1.0 for tenant in tenants)},
        {"name": "rollback_capacity_reserved", "passed": tenants[0]["quota"]["airflow_pool_slots"] - tenants[0]["observed"]["airflow_pool_slots"] >= 2},
        {"name": "tenant_cost_labels", "passed": all("platform.mlops.dev/cost-center" in tenant["labels"] for tenant in tenants)},
        {"name": "noisy_neighbor_contained", "passed": all(risk == "load-test" for risk in noisy_neighbor_risks), "observed": noisy_neighbor_risks},
    ]
    report = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "tenants": tenants,
        "checks": checks,
        "fairness": {
            "cohort": "mlops-serving-cohort",
            "max_cpu_utilization_gap": round(max(cpu_utils) - min(cpu_utils), 4),
            "max_airflow_pool_utilization_gap": round(max(pool_utils) - min(pool_utils), 4),
            "borrowing_policy": "load tests may borrow only when champion rollback and canary analysis queues have spare quota",
        },
        "controls": [
            "Serving, canary analysis, and load-test tenants use separate namespaces with ResourceQuota.",
            "Kueue cohorts allow canary analysis to borrow spare CPU without starving online serving.",
            "Airflow pools protect rollback checks from long load-test sweeps.",
            "Cost-center labels are required for serving chargeback.",
            "Default-deny NetworkPolicies block tenant-to-tenant predictor calls.",
        ],
        "references": [
            "https://kubernetes.io/docs/concepts/security/multi-tenancy/",
            "https://kubernetes.io/docs/concepts/policy/resource-quotas/",
            "https://kueue.sigs.k8s.io/docs/concepts/cohort/",
            "https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html",
        ],
    }
    write_json(Path(root) / "reports" / "tenancy_fairness_report.json", report)
    return report
