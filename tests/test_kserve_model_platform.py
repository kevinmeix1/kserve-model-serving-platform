from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kserve_model_platform.chaos import run_chaos_drill
from kserve_model_platform.cli import demo, monitor, promote, rollback, simulate
from kserve_model_platform.io import read_json, read_jsonl, write_json
from kserve_model_platform.models import generate_requests, validate_payload
from kserve_model_platform.monitoring import evaluate_canary
from kserve_model_platform.policy_audit import audit_platform_policy
from kserve_model_platform.registry import aliases
from kserve_model_platform.rollout_control import build_rollout_plan, evaluate_rollout, wilson_error_upper_bound
from kserve_model_platform.serving import deploy, predict, route_alias
from kserve_model_platform.traceability import build_trace_report


class KServeModelServingPlatformTest(unittest.TestCase):
    def test_advanced_rollout_dag_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        dag = repo / "airflow" / "dags" / "progressive_kserve_rollout_dag.py"
        workloads = repo / "kubernetes" / "serving-release-workloads.yaml"

        dag_text = dag.read_text(encoding="utf-8")
        workload_text = workloads.read_text(encoding="utf-8")

        for expected in ["KubernetesPodOperator", "task_group", "BranchPythonOperator", "Asset", "CANARY_STEPS", "expand("]:
            self.assertIn(expected, dag_text)
        for expected in ["deferrable=True", "pod_template_file", "traffic_policy_and_capacity", "reserve_kueue_canary_analysis_quota"]:
            self.assertIn(expected, dag_text)
        for expected in ["HorizontalPodAutoscaler", "Job", "RoleBinding", "ConfigMap", "securityContext", "kueue.x-k8s.io/queue-name"]:
            self.assertIn(expected, workload_text)

    def test_kubernetes_governance_and_airflow_pod_template_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        governance = (repo / "kubernetes" / "platform-governance.yaml").read_text(encoding="utf-8")
        pod_template = (repo / "kubernetes" / "airflow-kubernetes-executor-pod-template.yaml").read_text(encoding="utf-8")

        for expected in ["ResourceQuota", "LimitRange", "PriorityClass", "HTTPRoute"]:
            self.assertIn(expected, governance)
        for expected in ["initContainers", "startupProbe", "readinessProbe", "topologySpreadConstraints"]:
            self.assertIn(expected, pod_template)

    def test_kueue_and_weighted_gateway_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        admission = (repo / "kubernetes" / "kueue-admission-control.yaml").read_text(encoding="utf-8")
        traffic = (repo / "kubernetes" / "progressive-delivery-policy.yaml").read_text(encoding="utf-8")

        for expected in [
            "ResourceFlavor",
            "ClusterQueue",
            "LocalQueue",
            "WorkloadPriorityClass",
            "credit-risk-serving-queue",
            "borrowingLimit",
            "preemption",
        ]:
            self.assertIn(expected, admission)
        for expected in ["HTTPRoute", "credit-risk-weighted-route", "weight: 95", "weight: 5", "credit-risk-emergency-rollback-route"]:
            self.assertIn(expected, traffic)

    def test_event_driven_autoscaling_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        autoscaling = (repo / "kubernetes" / "event-driven-autoscaling.yaml").read_text(encoding="utf-8")

        for expected in ["ScaledObject", "prometheus", "fallback", "horizontalPodAutoscalerConfig", "activationThreshold"]:
            self.assertIn(expected, autoscaling)

    def test_admission_policies_and_policy_audit_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        admission = (repo / "kubernetes" / "admission-policies.yaml").read_text(encoding="utf-8")

        for expected in ["ValidatingAdmissionPolicy", "ValidatingAdmissionPolicyBinding", "ImageValidatingPolicy", "slsa-provenance"]:
            self.assertIn(expected, admission)
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_platform_policy(repo, output_root=tmp)
            passed = {check["name"] for check in report["checks"] if check["passed"]}
            self.assertIn("weighted_gateway_route", passed)
            self.assertIn("event_driven_scaling", passed)
            self.assertIn("no_latest_image_tags", report["failed_checks"])
            self.assertIn("immutable_image_digest", report["failed_checks"])

    def test_trace_report_and_otel_collector_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        collector = (repo / "kubernetes" / "opentelemetry-collector.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            trace = build_trace_report(tmp)

            self.assertEqual(trace["span_count"], 5)
            self.assertEqual(trace["root_service"], "gateway-api")
            self.assertTrue(any(span["name"] == "shadow.compare" for span in trace["spans"]))
            self.assertTrue((Path(tmp) / "reports" / "trace_report.json").exists())
        for expected in ["kind: ConfigMap", "otlp", "k8sattributes", "memory_limiter", "prometheus", "batch"]:
            self.assertIn(expected, collector)

    def test_chaos_drill_and_chaos_mesh_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        chaos_manifest = (repo / "kubernetes" / "chaos-experiments.yaml").read_text(encoding="utf-8")

        for expected in ["PodChaos", "NetworkChaos", "StressChaos", "Schedule", "concurrencyPolicy: Forbid", "credit-risk-challenger-pod-kill"]:
            self.assertIn(expected, chaos_manifest)
        with tempfile.TemporaryDirectory() as tmp:
            report = run_chaos_drill(tmp)

            self.assertTrue(report["passed"])
            self.assertEqual(report["scenario_count"], 3)
            self.assertTrue(any(scenario["fault"] == "PodChaos" for scenario in report["scenarios"]))
            self.assertTrue((Path(tmp) / "reports" / "chaos_drill_report.json").exists())

    def test_rollout_control_uses_confidence_bound_and_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(
                root / "reports" / "serving_observability.json",
                {
                    "request_count": 500,
                    "error_count": 0,
                    "latency_ms": {"p95": 12.0},
                    "shadow": {"mean_abs_delta": 0.03},
                    "route_counts": {"champion": 450, "challenger": 50},
                },
            )
            write_json(root / "deployments" / "kserve_state.json", {"service_name": "credit-risk-router", "traffic": {"challenger": 10}})

            plan = build_rollout_plan(root)
            failed = evaluate_rollout(
                {"request_count": 20, "error_count": 4, "latency_ms": {"p95": 80.0}, "shadow": {"mean_abs_delta": 0.2}, "route_counts": {"challenger": 2}},
                10,
            )

            self.assertLess(wilson_error_upper_bound(0, 500), 0.02)
            self.assertEqual(plan["recommended_action"], "advance")
            self.assertEqual(plan["next_percent"], 25)
            self.assertEqual(failed["action"], "rollback")

    def test_demo_writes_dashboard_and_passes_canary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = demo(root)

            self.assertTrue(result["canary"]["passed"])
            self.assertTrue(result["idempotent_replay"])
            self.assertTrue((root / "reports" / "kserve_serving_dashboard.html").exists())
            self.assertEqual(result["simulation"]["success_count"], 120)

    def test_payload_contract_rejects_bad_request(self) -> None:
        bad_payload = {
            "request_id": "bad-1",
            "customer_id": "cust",
            "product": "unknown",
            "income": "not-number",
            "debt_ratio": 3.0,
            "delinquencies": 0,
            "utilization": 2.0,
            "employment_years": 1.0,
        }

        validation = validate_payload(bad_payload)

        self.assertFalse(validation["valid"])
        self.assertIn("allowed:product", validation["errors"])
        self.assertIn("not_numeric:income", validation["errors"])
        self.assertIn("range:debt_ratio", validation["errors"])

    def test_prediction_is_idempotent_by_request_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deploy(root, challenger_percent=10)
            payload = generate_requests(1)[0]

            first = predict(root, payload)
            second = predict(root, payload)

            self.assertEqual(first["request_id"], second["request_id"])
            self.assertTrue(second["idempotent_replay"])
            self.assertEqual(len(read_jsonl(root / "logs" / "predictions.jsonl")), 1)

    def test_canary_routes_challenger_traffic(self) -> None:
        state = {"challenger": "risk-model-2026-07-15", "traffic": {"challenger": 100}}
        self.assertEqual(route_alias(state, "any-request"), "challenger")

    def test_canary_gate_fails_without_challenger_traffic(self) -> None:
        report = {
            "latency_ms": {"p95": 10.0},
            "error_rate": 0.0,
            "shadow": {"mean_abs_delta": 0.01},
            "route_counts": {"champion": 10},
        }

        decision = evaluate_canary(report)

        self.assertFalse(decision["passed"])
        self.assertEqual(decision["recommended_action"], "hold_rollout")

    def test_promote_and_rollback_restore_previous_champion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deploy(root, challenger_percent=10)
            simulate(root, requests=80)
            monitor(root)

            promoted = promote(root)
            after_promote = aliases(root)
            rolled_back = rollback(root)
            after_rollback = aliases(root)
            deployment = read_json(root / "deployments" / "kserve_state.json")

            self.assertTrue(promoted["promoted"])
            self.assertEqual(after_promote["champion"], "risk-model-2026-07-15")
            self.assertTrue(rolled_back["rolled_back"])
            self.assertEqual(after_rollback["champion"], "risk-model-2026-07-01")
            self.assertEqual(deployment["status"], "Ready")


if __name__ == "__main__":
    unittest.main()
