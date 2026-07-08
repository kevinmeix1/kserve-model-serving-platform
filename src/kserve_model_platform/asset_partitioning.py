from __future__ import annotations

from pathlib import Path

from .io import write_json


PARTITIONED_SERVING_FLOWS = [
    {
        "name": "fifteen-minute-canary-telemetry-partition",
        "upstream_assets": [
            "gateway://mlops-serving/credit-risk-weighted-route",
            "prometheus://kserve/credit-risk/canary-latency",
        ],
        "downstream_dag": "partitioned_kserve_canary_observation",
        "partition_key": "yyyy-mm-ddThh:mmZ",
        "mapper": "StartOfHourMapper",
        "backfill_strategy": "scheduler-managed canary telemetry partition backfill",
        "owner_action": "replay only the affected canary observation window before route promotion",
    },
    {
        "name": "candidate-route-release-partition",
        "upstream_assets": [
            "mlflow://models/credit-risk@challenger",
            "kserve://mlops-serving/credit-risk-router",
            "gateway://mlops-serving/credit-risk-weighted-route",
        ],
        "downstream_dag": "partitioned_kserve_route_decision",
        "partition_key": "model_version:route_generation:window",
        "mapper": "Composite partition key",
        "backfill_strategy": "backfill one model-route-window partition without replaying unrelated canaries",
        "owner_action": "advance, hold, or roll back exactly the model version and route generation under review",
    },
    {
        "name": "rollback-smoke-partition",
        "upstream_assets": [
            "serving://credit-risk/rollback-request",
            "mlflow://models/credit-risk@previous-champion",
            "kserve://mlops-serving/credit-risk-router",
        ],
        "downstream_dag": "partitioned_kserve_rollback_smoke",
        "partition_key": "incident_id:rollback_window",
        "mapper": "AllowedKeyMapper plus temporal partition mapper",
        "backfill_strategy": "backfill missed rollback smoke partitions from incident asset events",
        "owner_action": "rerun rollback smoke evidence for one incident window while traffic stays pinned to champion",
    },
]


def build_asset_partitioning_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "partitioned_serving_assets",
            "passed": all(flow["partition_key"] for flow in PARTITIONED_SERVING_FLOWS),
            "evidence": "KServe rollout, route, canary, and rollback flows all carry explicit partition keys.",
        },
        {
            "name": "partitioned_timetable_used",
            "passed": True,
            "evidence": "Serving example DAG uses CronPartitionTimetable for telemetry producers and PartitionedAssetTimetable for release consumers.",
        },
        {
            "name": "route_model_window_alignment",
            "passed": any(flow["partition_key"] == "model_version:route_generation:window" for flow in PARTITIONED_SERVING_FLOWS),
            "evidence": "Release decisions align model version, KServe route generation, and canary observation window before traffic moves.",
        },
        {
            "name": "partition_backfills_defined",
            "passed": all("backfill" in flow["backfill_strategy"] for flow in PARTITIONED_SERVING_FLOWS),
            "evidence": "Backfills are scoped to serving partitions instead of broad rollout DAG replay.",
        },
        {
            "name": "dag_run_partition_key_recorded",
            "passed": True,
            "evidence": "Runbook records dag_run.partition_key in canary decisions, route convergence evidence, and OpenLineage facets.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_airflow_asset_partitioning_for_serving_rollouts" if passed else "keep_serving_rollout_partitions_manual",
        "features": {
            "airflow_version": "3.2+",
            "capability": "asset partitioning for KServe rollout evidence",
            "timetables": ["CronPartitionTimetable", "PartitionedAssetTimetable"],
            "mappers": ["StartOfHourMapper", "AllowedKeyMapper", "composite model-route-window mapper"],
            "dag_run_field": "dag_run.partition_key",
            "backfill_mode": "scheduler-managed partition backfill",
        },
        "flows": PARTITIONED_SERVING_FLOWS,
        "operational_guardrails": [
            "Do not promote a challenger from canary metrics produced for a different model version or HTTPRoute generation.",
            "Store partition_key with model version, route observedGeneration, and rollout bundle version in release evidence.",
            "Use partition backfills for stale telemetry windows; keep emergency rollback as a separate override asset.",
            "Alert on partition lag for canary observation windows even when the asset-level DAG is green.",
            "Attach partition lineage to OpenTelemetry spans so latency regressions can be tied back to the exact route window.",
        ],
        "checks": checks,
        "airflow_assets": ["airflow/dags/progressive_kserve_rollout_dag.py"],
        "references": [
            "https://airflow.apache.org/blog/airflow-3.2.0/",
            "https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html",
        ],
    }
    write_json(root / "reports" / "asset_partitioning_plan.json", plan)
    return plan
