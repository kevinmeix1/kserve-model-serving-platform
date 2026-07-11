"""Airflow 3.3 stateful KServe rollout orchestration.

CI parses this module against Apache Airflow 3.3. The local dependency-light
demo does not start Airflow services, but this is executable DAG-authoring code.
"""

from __future__ import annotations

from datetime import timedelta

from airflow.sdk import (
    NEVER_EXPIRE,
    Asset,
    DAG,
    ExceptionRetryPolicy,
    FanOutMapper,
    FixedKeyMapper,
    MinimumCount,
    PartitionedAssetTimetable,
    PartitionedAtRuntime,
    RetryAction,
    RetryRule,
    RollupMapper,
    SegmentWindow,
    StartOfWeekMapper,
    WeekWindow,
    asset,
    task,
)


AIRFLOW_33_DAG_IDS = {
    "stateful_kserve_rollout_evidence",
    "challenger_daily_route_fanout",
}
SERVING_SEGMENTS = ["request-contract", "shadow-comparison", "route-observation"]

SERVING_RETRY_POLICY = ExceptionRetryPolicy(
    rules=[
        RetryRule(
            exception=ConnectionError,
            action=RetryAction.RETRY,
            retry_delay=timedelta(seconds=20),
            reason="Transient KServe or Gateway API connection failure",
        ),
        RetryRule(
            exception=PermissionError,
            action=RetryAction.FAIL,
            reason="Route mutation authorization failures require operator intervention",
        ),
    ],
)

SERVING_ROLLOUT_SEGMENTS = Asset.ref(name="serving_rollout_segments")
ROLLOUT_DECISION = Asset(
    uri="kserve://mlops-serving/credit-risk/stateful-rollout-decision",
    name="stateful_kserve_rollout_decision",
)
WEEKLY_CHALLENGER = Asset(
    uri="mlflow://models/credit-risk/weekly-challenger",
    name="weekly_credit_risk_challenger",
)


@asset(
    uri="s3://mlops-serving/credit-risk/rollout-evidence-segments.json",
    schedule=PartitionedAtRuntime(),
)
def serving_rollout_segments(self, outlet_events) -> None:
    """Emit rollout evidence partitions discovered during serving preflight."""

    outlet_events[self].add_partitions(SERVING_SEGMENTS)


with DAG(
    dag_id="stateful_kserve_rollout_evidence",
    schedule=PartitionedAssetTimetable(
        assets=SERVING_ROLLOUT_SEGMENTS,
        default_partition_mapper=RollupMapper(
            upstream_mapper=FixedKeyMapper("rollout-ready"),
            window=SegmentWindow(SERVING_SEGMENTS),
            wait_policy=MinimumCount(len(SERVING_SEGMENTS)),
            max_downstream_keys=1,
        ),
    ),
    catchup=False,
    max_active_runs=1,
    params={
        "challenger_digest": "sha256:replace-at-trigger-time",
        "route_generation": "replace-at-trigger-time",
    },
    tags=["airflow-3.3", "state-store", "kserve", "gateway-api"],
) as stateful_kserve_rollout_evidence:

    @task(
        inlets=[SERVING_ROLLOUT_SEGMENTS],
        outlets=[ROLLOUT_DECISION],
        retries=4,
        retry_delay=timedelta(seconds=45),
        retry_policy=SERVING_RETRY_POLICY,
    )
    def checkpoint_rollout_decision(**context) -> dict[str, str]:
        task_store = context["task_state_store"]
        operation_id = task_store.get("rollout_operation_id")
        if operation_id is None:
            operation_id = f"kserve-rollout:{context['run_id']}"
            task_store.set("rollout_operation_id", operation_id, retention=NEVER_EXPIRE)

        task_store.set(
            "rollout_progress",
            {"stage": "evidence_complete", "attempt": context["ti"].try_number},
        )
        decision_store = context["asset_state_store"][ROLLOUT_DECISION]
        decision_store.set("challenger_digest", context["params"]["challenger_digest"])
        decision_store.set(
            "observed_route_generation", context["params"]["route_generation"]
        )
        return {
            "operation_id": operation_id,
            "status": "ready_for_progressive_delivery",
        }

    checkpoint_rollout_decision()


with DAG(
    dag_id="challenger_daily_route_fanout",
    schedule=PartitionedAssetTimetable(
        assets=WEEKLY_CHALLENGER,
        default_partition_mapper=FanOutMapper(
            upstream_mapper=StartOfWeekMapper(),
            window=WeekWindow(),
            max_downstream_keys=7,
        ),
    ),
    catchup=False,
    max_active_runs=2,
    tags=["airflow-3.3", "asset-fanout", "kserve", "canary"],
) as challenger_daily_route_fanout:

    @task(inlets=[WEEKLY_CHALLENGER], retries=2, retry_policy=SERVING_RETRY_POLICY)
    def validate_daily_route_partition(dag_run=None) -> dict[str, str | None]:
        return {
            "partition_key": dag_run.partition_key if dag_run else None,
            "challenger_asset": WEEKLY_CHALLENGER.uri,
            "validation": "bounded_daily_route_canary",
        }

    validate_daily_route_partition()
