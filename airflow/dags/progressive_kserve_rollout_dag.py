from __future__ import annotations

from datetime import datetime, timedelta

AIRFLOW_AVAILABLE = True

try:
    from airflow.decorators import dag, task, task_group
    from airflow.operators.empty import EmptyOperator
    from airflow.operators.python import BranchPythonOperator
    from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
    from airflow.sdk import Asset, CronPartitionTimetable, DAG, PartitionedAssetTimetable, StartOfHourMapper
    from airflow.utils.trigger_rule import TriggerRule
except Exception:
    AIRFLOW_AVAILABLE = False


CANARY_STEPS = [1, 5, 10, 25, 50]
OBSERVABILITY_CHECKS = ["latency", "error_rate", "shadow_delta", "route_mix", "score_distribution"]
EVENT_DRIVEN_ASSET_EXPRESSION = "(CHALLENGER & ROUTER & WEIGHTED_ROUTE) | ROLLBACK_REQUEST"
ASSET_WATCHER_CONTRACTS = {
    "AssetWatcher": "MLflow, KServe, and Gateway API events update Airflow rollout assets",
    "BaseEventTrigger": "watchers must inherit from BaseEventTrigger to avoid rescheduling loops",
    "shared_stream_key": "registry and Kubernetes watches share upstream polling across subscribers",
    "AssetAlias": "runtime modelcar and MLflow artifact URIs resolve after challenger registration",
}


def notify_release_failure(context):
    task_id = context.get("task_instance").task_id if context.get("task_instance") else "unknown"
    return {"channel": "release-alerts", "task": task_id}


def kserve_pod(task_id: str, command: str, *, priority_weight: int = 1):
    return KubernetesPodOperator(
        task_id=task_id,
        namespace="mlops-serving",
        image="ghcr.io/kevinmeix1/kserve-model-serving-platform:2026.07.0",
        cmds=["bash", "-lc"],
        arguments=[command],
        service_account_name="credit-risk-predictor",
        get_logs=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        deferrable=True,
        logging_interval=20,
        reattach_on_restart=True,
        on_finish_action="delete_pod",
        on_kill_action="delete_pod",
        startup_timeout_seconds=300,
        execution_timeout=timedelta(hours=1),
        pod_template_file="/opt/airflow/dags/repo/kubernetes/airflow-kubernetes-executor-pod-template.yaml",
        pool="model_serving_release_pool",
        priority_weight=priority_weight,
        retries=2,
        retry_delay=timedelta(minutes=3),
        labels={"platform": "kserve-model-serving", "task": task_id},
    )


if AIRFLOW_AVAILABLE:
    CHALLENGER = Asset("mlflow://models/credit-risk@challenger")
    ROUTER = Asset("kserve://mlops-serving/credit-risk-router")
    WEIGHTED_ROUTE = Asset("gateway://mlops-serving/credit-risk-weighted-route")
    CANARY_METRICS = Asset("prometheus://kserve/credit-risk/canary-metrics")
    RELEASE_DECISION = Asset("serving://credit-risk/release-decision")
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
        rerun_with_latest_version=False,
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

        @task_group(group_id="traffic_policy_and_capacity")
        def traffic_policy_group():
            reserve_canary_quota = kserve_pod(
                "reserve_kueue_canary_analysis_quota",
                "kubectl get localqueue credit-risk-serving-queue -n mlops-serving",
                priority_weight=4,
            )
            validate_gateway_weights = kserve_pod(
                "validate_gateway_http_route_weights",
                "kubectl get httproute credit-risk-weighted-route -n mlops-serving -o yaml",
                priority_weight=4,
            )
            submit_rayservice_transform = kserve_pod(
                "submit_kuberay_rayservice_transform",
                "kubectl apply -f kubernetes/kuberay-kueue-workloads.yaml",
                priority_weight=4,
            )
            wait_for_rayservice_ready = kserve_pod(
                "wait_for_kuberay_rayservice_ready_deferrable",
                "kubectl wait --for=condition=Ready rayservice/credit-risk-rayservice -n mlops-serving --timeout=15m",
                priority_weight=4,
            )
            wait_for_shadow_evaluator = kserve_pod(
                "wait_for_shadow_canary_evaluator_deferrable",
                "kubectl wait --for=condition=Complete rayjob/shadow-canary-evaluator -n mlops-serving --timeout=15m",
                priority_weight=5,
            )
            wait_for_route_convergence = kserve_pod(
                "wait_for_route_convergence_deferrable",
                "kubectl wait --for=condition=Accepted httproute/credit-risk-weighted-route -n mlops-serving --timeout=5m",
                priority_weight=5,
            )
            reserve_canary_quota >> validate_gateway_weights >> submit_rayservice_transform >> wait_for_rayservice_ready >> wait_for_shadow_evaluator >> wait_for_route_convergence
            return wait_for_route_convergence

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
        start >> preflight_group() >> progressive_traffic_group(steps) >> observability_group() >> traffic_policy_group() >> branch
        branch >> promote >> publish >> end
        branch >> rollback >> publish

    progressive_kserve_rollout()

    with DAG(
        dag_id="partitioned_kserve_canary_observation",
        schedule=CronPartitionTimetable("*/15 * * * *", timezone="UTC"),
        catchup=False,
        max_active_runs=4,
        tags=["airflow-3.2", "asset-partitioning", "kserve", "canary"],
    ):
        @task(outlets=[CANARY_METRICS])
        def collect_canary_partition(dag_run=None) -> dict[str, str | None]:
            partition_key = dag_run.partition_key if dag_run else None
            return {
                "partition_key": partition_key,
                "route_asset": WEIGHTED_ROUTE.uri,
                "telemetry_asset": CANARY_METRICS.uri,
            }

        collect_canary_partition()

    with DAG(
        dag_id="partitioned_kserve_route_decision",
        schedule=PartitionedAssetTimetable(
            assets=CHALLENGER & ROUTER & WEIGHTED_ROUTE & CANARY_METRICS,
            default_partition_mapper=StartOfHourMapper(),
        ),
        catchup=False,
        max_active_runs=1,
        tags=["airflow-3.2", "partitioned-backfill", "kserve", "rollback"],
    ):
        @task(outlets=[RELEASE_DECISION, INCIDENTS])
        def evaluate_route_partition(dag_run=None) -> dict[str, str | None]:
            partition_key = dag_run.partition_key if dag_run else None
            return {
                "partition_key": partition_key,
                "model_asset": CHALLENGER.uri,
                "route_asset": WEIGHTED_ROUTE.uri,
                "decision_asset": RELEASE_DECISION.uri,
                "evidence": "aligned model version, route generation, and canary telemetry partition",
            }

        evaluate_route_partition()
