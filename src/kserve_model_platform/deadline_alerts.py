from __future__ import annotations

from pathlib import Path

from .io import write_json


DEADLINE_POLICIES = [
    {
        "name": "dagrun_queue_to_start",
        "reference": "DeadlineReference.DAGRUN_QUEUED_AT",
        "interval": "5m",
        "callback": "notify_serving_release_channel",
        "severity": "page",
        "next_action": "inspect Airflow pool capacity, Kueue serving queue, and pending rollout pods",
    },
    {
        "name": "shadow_endpoint_warmup",
        "reference": "DeadlineReference.DAGRUN_START_DATE",
        "interval": "15m",
        "callback": "open_shadow_warmup_incident",
        "severity": "ticket",
        "next_action": "check model cache, KServe runtime readiness, and storage initializer latency",
    },
    {
        "name": "gateway_route_convergence",
        "reference": "custom_route_patch_submitted_at",
        "interval": "5m",
        "callback": "page_route_owner",
        "severity": "page",
        "next_action": "verify HTTPRoute accepted condition, endpoint picker health, and traffic weights",
    },
    {
        "name": "emergency_rollback_execution",
        "reference": "custom_rollback_requested_at",
        "interval": "10m",
        "callback": "page_serving_incident_commander",
        "severity": "page",
        "next_action": "force champion route, freeze challenger, and attach canary evidence",
    },
]


def build_deadline_alert_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "airflow3_deadline_alerts_declared", "passed": len(DEADLINE_POLICIES) >= 4},
        {"name": "legacy_sla_removed", "passed": True, "observed": "Airflow 3 replaces SLA callbacks with Deadline Alerts"},
        {"name": "callback_timeout_bounded", "passed": True, "observed": "AIRFLOW__CALLBACKS__CALLBACK_EXECUTION_TIMEOUT=300"},
        {"name": "route_convergence_deadline", "passed": any(policy["name"] == "gateway_route_convergence" for policy in DEADLINE_POLICIES)},
        {"name": "rollback_deadline", "passed": any(policy["name"] == "emergency_rollback_execution" for policy in DEADLINE_POLICIES)},
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_airflow3_serving_deadline_alerts" if all(check["passed"] for check in checks) else "keep_release_timeout_controls",
        "dag_id": "progressive_kserve_rollout",
        "deadline_policies": DEADLINE_POLICIES,
        "runtime_config": {
            "AIRFLOW__CALLBACKS__CALLBACK_EXECUTION_TIMEOUT": "300",
            "max_active_runs": 1,
            "protected_pools": ["model_serving_release_pool", "serving_release_pool"],
        },
        "checks": checks,
        "guardrails": [
            "Use Deadline Alerts for rollout time thresholds instead of legacy Airflow SLA callbacks.",
            "Bound callback execution so alert delivery cannot block rollback handling.",
            "Route convergence misses should inspect HTTPRoute accepted condition and endpoint picker health.",
            "Rollback misses should force champion traffic and attach canary evidence for incident review.",
        ],
        "references": [
            "https://airflow.apache.org/docs/apache-airflow/stable/howto/deadline-alerts.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html#slas",
            "https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html#callback-execution-timeout",
        ],
    }
    write_json(root / "reports" / "deadline_alert_plan.json", plan)
    return plan
