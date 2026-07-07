from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kserve_model_platform.cli import demo, monitor, promote, rollback, simulate
from kserve_model_platform.io import read_json, read_jsonl
from kserve_model_platform.models import generate_requests, validate_payload
from kserve_model_platform.monitoring import evaluate_canary
from kserve_model_platform.registry import aliases
from kserve_model_platform.serving import deploy, predict, route_alias


class KServeModelServingPlatformTest(unittest.TestCase):
    def test_advanced_rollout_dag_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        dag = repo / "airflow" / "dags" / "progressive_kserve_rollout_dag.py"
        workloads = repo / "kubernetes" / "serving-release-workloads.yaml"

        dag_text = dag.read_text(encoding="utf-8")
        workload_text = workloads.read_text(encoding="utf-8")

        for expected in ["KubernetesPodOperator", "task_group", "BranchPythonOperator", "Asset", "CANARY_STEPS", "expand("]:
            self.assertIn(expected, dag_text)
        for expected in ["HorizontalPodAutoscaler", "Job", "RoleBinding", "ConfigMap", "securityContext"]:
            self.assertIn(expected, workload_text)

    def test_kubernetes_governance_and_airflow_pod_template_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        governance = (repo / "kubernetes" / "platform-governance.yaml").read_text(encoding="utf-8")
        pod_template = (repo / "kubernetes" / "airflow-kubernetes-executor-pod-template.yaml").read_text(encoding="utf-8")

        for expected in ["ResourceQuota", "LimitRange", "PriorityClass", "HTTPRoute"]:
            self.assertIn(expected, governance)
        for expected in ["initContainers", "startupProbe", "readinessProbe", "topologySpreadConstraints"]:
            self.assertIn(expected, pod_template)

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
