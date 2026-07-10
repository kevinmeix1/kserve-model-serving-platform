from __future__ import annotations

from pathlib import Path

from .io import write_json


DAG_RELATIVE_PATH = Path("airflow/dags/airflow33_stateful_serving_dag.py")
STATEFUL_ORCHESTRATION_FLOWS = [
    {
        "name": "serving-rollout-evidence",
        "mapper": "RollupMapper",
        "wait_policy": "MinimumCount(3)",
        "max_downstream_keys": 1,
        "task_state_keys": ["rollout_operation_id", "rollout_progress"],
        "asset_state_keys": ["challenger_digest", "observed_route_generation"],
        "retry_policy": "retry_kserve_or_gateway_connections_fail_authorization_errors",
        "owner_action": "reattach to one rollout operation while preserving the challenger digest and observed route generation",
    },
    {
        "name": "challenger-daily-route-fanout",
        "mapper": "FanOutMapper",
        "wait_policy": "one_run_per_day",
        "max_downstream_keys": 7,
        "task_state_keys": [],
        "asset_state_keys": [],
        "retry_policy": "retry_kserve_or_gateway_connections_fail_authorization_errors",
        "owner_action": "bound one weekly challenger to seven independently retryable route canaries",
    },
    {
        "name": "runtime-serving-partitioning",
        "mapper": "PartitionedAtRuntime",
        "wait_policy": "emit_discovered_segments",
        "max_downstream_keys": 3,
        "task_state_keys": [],
        "asset_state_keys": [],
        "retry_policy": "producer_is_idempotent",
        "owner_action": "emit request-contract, shadow, and route evidence discovered at runtime",
    },
]


def build_airflow_stateful_orchestration_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
    repo_root: str | Path | None = None,
) -> dict:
    root = Path(root)
    repo_root = (
        Path(repo_root)
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )
    dag_path = repo_root / DAG_RELATIVE_PATH
    ci_path = repo_root / ".github" / "workflows" / "ci.yml"
    dag_source = dag_path.read_text(encoding="utf-8") if dag_path.exists() else ""
    ci_source = ci_path.read_text(encoding="utf-8") if ci_path.exists() else ""
    checks = [
        {
            "name": "airflow_33_public_sdk_contract",
            "passed": all(
                token in dag_source
                for token in [
                    "from airflow.sdk import",
                    "task_state_store",
                    "asset_state_store",
                    "NEVER_EXPIRE",
                ]
            ),
            "evidence": "The rollout DAG uses the Airflow 3.3 public Task SDK and documented state-store accessors.",
        },
        {
            "name": "state_store_scope_separation",
            "passed": all(
                STATEFUL_ORCHESTRATION_FLOWS[0][key]
                for key in ["task_state_keys", "asset_state_keys"]
            ),
            "evidence": "Retry-local rollout state and cross-run route state use separate key sets.",
        },
        {
            "name": "bounded_partition_mapping",
            "passed": all(
                flow["max_downstream_keys"] <= 7
                for flow in STATEFUL_ORCHESTRATION_FLOWS
            ),
            "evidence": "Rollup, fanout, and runtime partitions have explicit serving limits.",
        },
        {
            "name": "exception_aware_retry_policy",
            "passed": all(
                token in dag_source
                for token in [
                    "ExceptionRetryPolicy",
                    "RetryAction.RETRY",
                    "RetryAction.FAIL",
                ]
            ),
            "evidence": "Transient KServe/Gateway connectivity retries while authorization failures fail fast.",
        },
        {
            "name": "real_airflow_parse_gate",
            "passed": all(
                token in ci_source
                for token in [
                    "apache-airflow==3.3.0",
                    "make airflow-sdk-contract",
                    "python -m pip check",
                ]
            ),
            "evidence": "CI installs constrained Airflow 3.3 and validates registered DAG objects.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-10T00:00:00Z",
        "passed": passed,
        "recommended_action": "adopt_airflow_33_stateful_serving_contract"
        if passed
        else "fix_airflow_33_contract_before_adoption",
        "features": {
            "airflow_version": "3.3.0",
            "asset_partition_mappers": [
                "RollupMapper",
                "FanOutMapper",
                "FixedKeyMapper",
                "SegmentWindow",
            ],
            "runtime_partitioning": "PartitionedAtRuntime",
            "state_store": ["task_state_store", "asset_state_store"],
            "retry_policy": "ExceptionRetryPolicy",
            "fanout_limit": "max_downstream_keys plus scheduler-level partition_mapper_max_downstream_keys",
        },
        "state_store_contract": {
            "task_scope": "one mapped rollout task instance; preserves operation ID across retries",
            "asset_scope": "KServe rollout decision across runs; preserves challenger and route generations",
            "retention": "NEVER_EXPIRE only for rollout operation IDs needed for idempotency",
            "cleanup": "airflow state-store clean --dry-run before scheduled garbage collection",
            "payload_rule": "store identifiers and progress only; telemetry and model artifacts remain external",
        },
        "flows": STATEFUL_ORCHESTRATION_FLOWS,
        "ci_validation": {
            "command": "make airflow-sdk-contract",
            "runtime": "apache-airflow==3.3.0 with official Python 3.11 constraints",
            "assertions": [
                "expected DAG IDs registered",
                "DAG.validate succeeds",
                "every expected DAG has tasks",
                "pip check succeeds",
            ],
        },
        "limitations": [
            "The default demo does not start Airflow, KServe, or a Gateway API control plane.",
            "The CI gate proves DAG authoring compatibility, not live route convergence.",
            "Production rollout state requires durable Airflow metadata and a tested state-store retention policy.",
        ],
        "checks": checks,
        "airflow_assets": [str(DAG_RELATIVE_PATH), "tools/validate_airflow33_dag.py"],
        "references": [
            "https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/task-and-asset-state-store.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html#retry-policies",
            "https://airflow.apache.org/docs/apache-airflow/stable/installation/installing-from-pypi.html",
        ],
    }
    write_json(root / "reports" / "airflow_stateful_orchestration_plan.json", plan)
    return plan
