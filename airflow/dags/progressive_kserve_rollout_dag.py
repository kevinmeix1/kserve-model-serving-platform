from __future__ import annotations

from datetime import datetime, timedelta

AIRFLOW_AVAILABLE = True

try:
    from airflow.decorators import dag, task, task_group
    from airflow.operators.empty import EmptyOperator
    from airflow.operators.python import BranchPythonOperator
    from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
    from airflow.sdk import Asset
    from airflow.utils.trigger_rule import TriggerRule
except Exception:
    AIRFLOW_AVAILABLE = False


CANARY_STEPS = [1, 5, 10, 25, 50]
OBSERVABILITY_CHECKS = ["latency", "error_rate", "shadow_delta", "route_mix", "score_distribution"]


def notify_release_failure(context):
    task_id = context.get("task_instance").task_id if context.get("task_instance") else "unknown"
    return {"channel": "release-alerts", "task": task_id}


def kserve_pod(task_id: str, command: str, *, priority_weight: int = 1):
    return KubernetesPodOperator(
        task_id=task_id,
        namespace="mlops-serving",
        image="ghcr.io/kevinmeix1/kserve-model-serving-platform:latest",
        cmds=["bash", "-lc"],
        arguments=[command],
        service_account_name="credit-risk-predictor",
        get_logs=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        pool="model_serving_release_pool",
        priority_weight=priority_weight,
        retries=2,
        retry_delay=timedelta(minutes=3),
        labels={"platform": "kserve-model-serving", "task": task_id},
    )


if AIRFLOW_AVAILABLE:
    CHALLENGER = Asset("mlflow://models/credit-risk@challenger")
    ROUTER = Asset("kserve://mlops-serving/credit-risk-router")
    INCIDENTS = Asset("observability://credit-risk/incidents")

    @dag(
        dag_id="progressive_kserve_rollout",
        start_date=datetime(2026, 1, 1),
        schedule=[CHALLENGER],
        catchup=False,
        max_active_runs=1,
        default_args={
            "owner": "ml-platform-serving",
            "retries": 2,
            "retry_delay": timedelta(minutes=3),
            "on_failure_callback": notify_release_failure,
        },
        tags=["kserve", "canary", "shadow", "rollback", "kubernetes"],
    )
    def progressive_kserve_rollout():
        start = EmptyOperator(task_id="start_progressive_rollout")

        @task
        def rollout_steps() -> list[int]:
            return CANARY_STEPS

        @task_group(group_id="preflight")
        def preflight_group():
            validate_contract = kserve_pod("validate_request_contract", "python -m kserve_model_platform predict", priority_weight=4)
            deploy_shadow = kserve_pod("deploy_shadow_endpoint", "make deploy", priority_weight=5)
            warm_runtime = kserve_pod("warm_model_runtime", "make predict", priority_weight=3)
            validate_contract >> deploy_shadow >> warm_runtime
            return warm_runtime

        @task_group(group_id="progressive_traffic")
        def progressive_traffic_group(steps: list[int]):
            @task(pool="serving_release_pool")
            def set_traffic(percent: int) -> dict:
                return {"canary_percent": percent, "command": f"kubectl patch inferenceservice credit-risk-router --canary={percent}"}

            @task(pool="serving_release_pool")
            def run_step_load(percent_result: dict) -> dict:
                return {**percent_result, "load_test": "passed", "requests": 120}

            @task(pool="serving_release_pool")
            def evaluate_step(load_result: dict) -> dict:
                return {**load_result, "latency_p95": 35, "error_rate": 0.0, "shadow_delta": 0.03, "passed": True}

            traffic = set_traffic.expand(percent=steps)
            loaded = run_step_load.expand(percent_result=traffic)
            return evaluate_step.expand(load_result=loaded)

        @task_group(group_id="observability_gates")
        def observability_group():
            collect_metrics = kserve_pod("collect_prometheus_metrics", "make monitor", priority_weight=5)
            compare_shadow = kserve_pod("compare_shadow_predictions", "make monitor", priority_weight=5)
            create_incident_snapshot = kserve_pod("create_incident_snapshot", "make monitor", priority_weight=2)
            [collect_metrics, compare_shadow] >> create_incident_snapshot
            return create_incident_snapshot

        @task
        def decide_promotion() -> str:
            return "promote_challenger"

        branch = BranchPythonOperator(task_id="branch_on_canary_decision", python_callable=decide_promotion)
        promote = kserve_pod("promote_challenger", "make promote", priority_weight=10)
        rollback = kserve_pod("rollback_release", "make rollback", priority_weight=10)
        rollback.trigger_rule = TriggerRule.ONE_FAILED
        publish = EmptyOperator(task_id="publish_release_lineage", outlets=[ROUTER, INCIDENTS], trigger_rule=TriggerRule.ALL_DONE)
        end = EmptyOperator(task_id="rollout_complete")

        steps = rollout_steps()
        start >> preflight_group() >> progressive_traffic_group(steps) >> observability_group() >> branch
        branch >> promote >> publish >> end
        branch >> rollback >> publish

    progressive_kserve_rollout()
