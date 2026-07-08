from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kserve_model_platform.accelerator_plan import build_accelerator_capacity_plan
from kserve_model_platform.chaos import run_chaos_drill
from kserve_model_platform.cloud_migration import build_cloud_migration_plan
from kserve_model_platform.cli import demo, monitor, promote, rollback, simulate
from kserve_model_platform.cohort_fair_sharing import build_cohort_fair_sharing_plan
from kserve_model_platform.cost_observability import build_cost_observability_report
from kserve_model_platform.dag_bundle_versioning import build_dag_bundle_versioning_plan
from kserve_model_platform.deadline_alerts import build_deadline_alert_plan
from kserve_model_platform.disaster_recovery import build_disaster_recovery_plan
from kserve_model_platform.device_allocation import build_device_allocation_plan
from kserve_model_platform.elastic_workload import build_elastic_workload_plan
from kserve_model_platform.event_driven_assets import build_event_driven_assets_plan
from kserve_model_platform.flavor_fungibility import build_flavor_fungibility_plan
from kserve_model_platform.gitops_release import build_gitops_plan
from kserve_model_platform.governance import build_governance_bundle
from kserve_model_platform.identity import build_identity_access_report
from kserve_model_platform.indexed_job_resilience import build_indexed_job_resilience_plan
from kserve_model_platform.inference_gateway import build_inference_gateway_plan
from kserve_model_platform.io import read_json, read_jsonl, write_json
from kserve_model_platform.kuberay_capacity import build_kuberay_capacity_plan
from kserve_model_platform.model_cache import build_model_cache_plan
from kserve_model_platform.models import generate_requests, validate_payload
from kserve_model_platform.monitoring import evaluate_canary
from kserve_model_platform.multikueue_dispatch import build_multikueue_dispatch_plan
from kserve_model_platform.network_security import build_network_security_report
from kserve_model_platform.orchestration_scorecard import build_orchestration_scorecard
from kserve_model_platform.policy_audit import audit_platform_policy
from kserve_model_platform.performance_budget import build_performance_budget_report
from kserve_model_platform.pod_resource_envelopes import build_pod_resource_envelope_plan
from kserve_model_platform.provisioning_admission import build_provisioning_admission_plan
from kserve_model_platform.queue_simulator import build_queue_simulation
from kserve_model_platform.release_admission import build_release_admission_decision, evaluate_release_admission
from kserve_model_platform.registry import aliases
from kserve_model_platform.resource_optimizer import build_resource_optimization_report
from kserve_model_platform.rollout_control import build_rollout_plan, evaluate_rollout, wilson_error_upper_bound
from kserve_model_platform.serving import deploy, predict, route_alias
from kserve_model_platform.semantic_telemetry import build_semantic_telemetry_plan
from kserve_model_platform.slo import build_slo_report
from kserve_model_platform.supply_chain import build_supply_chain_evidence
from kserve_model_platform.tenancy import build_tenancy_report
from kserve_model_platform.topology_placement import build_topology_placement_plan
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

    def test_queue_simulation_models_serving_rollback_priority(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "queue-simulation-policy.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_queue_simulation(root)

            self.assertTrue(report["passed"])
            self.assertGreaterEqual(report["preempted_count"], 1)
            self.assertTrue(any(item["name"] == "emergency-champion-rollback" for item in report["simulation"]["admitted"]))
            self.assertTrue((root / "reports" / "queue_simulation.json").exists())
            self.assertIn("PriorityClass", manifest)
            self.assertIn("CreditRiskServingQueuePressureHigh", manifest)

    def test_release_admission_advances_or_rolls_back_canary(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "release-admission-policy.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root / "reports" / "slo_error_budget.json", {"max_burn_rate": 0.2, "release_freeze": False, "recommended_action": "allow_release"})
            write_json(root / "reports" / "performance_budget.json", {"passed": True, "checks": []})
            write_json(root / "reports" / "queue_simulation.json", {"passed": True, "pending_count": 0, "simulation": {"pending": []}})
            write_json(root / "reports" / "governance_evidence_bundle.json", {"release": {"decision": "approved_for_promotion"}})
            write_json(root / "reports" / "supply_chain_evidence.json", {"artifact_count": 8, "subject": {"attestation_action": "actions/attest@v4"}})
            write_json(root / "reports" / "rollout_control_plan.json", {"recommended_action": "advance", "next_percent": 25})
            write_json(root / "reports" / "canary_decision.json", {"passed": True})

            decision = build_release_admission_decision(root)
            rollback_decision = evaluate_release_admission(
                slo={"max_burn_rate": 0.2, "release_freeze": False},
                performance={"passed": True, "checks": []},
                queue={"passed": True, "pending_count": 0, "simulation": {"pending": []}},
                governance={"release": {"decision": "approved_for_promotion"}},
                supply_chain={"artifact_count": 8, "subject": {"attestation_action": "actions/attest@v4"}},
                rollout_plan={"recommended_action": "rollback", "next_percent": 10},
                canary_decision={"passed": False},
            )

            self.assertEqual(decision["decision"]["recommended_action"], "advance_canary")
            self.assertFalse(decision["decision"]["unsafe_allow"])
            self.assertEqual(rollback_decision["recommended_action"], "rollback_challenger")
            self.assertTrue((root / "reports" / "release_admission_decision.json").exists())
            self.assertIn("ValidatingAdmissionPolicy", manifest)
            self.assertIn("AnalysisTemplate", manifest)
            self.assertIn("CreditRiskReleaseAdmissionUnsafeAllow", manifest)

    def test_performance_budget_report_and_prometheus_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "performance-budget-policy.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = demo(root)
            report = build_performance_budget_report(root)
            names = {check["name"] for check in report["checks"]}

            self.assertTrue(result["performance_budget"]["passed"])
            self.assertTrue(report["passed"])
            self.assertIn("inference_p95_ms", names)
            self.assertIn("shadow_score_delta", names)
            self.assertIn("request_volume_for_canary", names)
            self.assertTrue((root / "reports" / "performance_budget.json").exists())
            self.assertIn("PrometheusRule", manifest)
            self.assertIn("histogram_quantile", manifest)
            self.assertIn("CreditRiskServingP95BudgetExceeded", manifest)

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
            self.assertIn("immutable_image_digest", passed)
            self.assertIn("no_latest_image_tags", passed)

    def test_trace_report_and_otel_collector_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        collector = (repo / "kubernetes" / "opentelemetry-collector.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            trace = build_trace_report(tmp)

            self.assertEqual(trace["span_count"], 5)
            self.assertEqual(trace["root_service"], "gateway-api")
            self.assertTrue(any(span["name"] == "shadow.compare" for span in trace["spans"]))
            self.assertTrue(any(span["attributes"].get("gen_ai.request.model") == "credit-risk-v2" for span in trace["spans"]))
            self.assertTrue(any(span["attributes"].get("gen_ai.usage.input_tokens") == 64 for span in trace["spans"]))
            self.assertTrue((Path(tmp) / "reports" / "trace_report.json").exists())
        for expected in ["kind: ConfigMap", "otlp", "k8sattributes", "memory_limiter", "prometheus", "batch", "attributes/semantic_redaction", "gen_ai.input.messages"]:
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

    def test_resource_optimization_and_autoscaling_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        optimization = (repo / "kubernetes" / "resource-optimization.yaml").read_text(encoding="utf-8")

        for expected in ["VerticalPodAutoscaler", "HorizontalPodAutoscaler", "PrometheusRule", "airflow-capacity-pools", "stabilizationWindowSeconds: 300"]:
            self.assertIn(expected, optimization)
        with tempfile.TemporaryDirectory() as tmp:
            report = build_resource_optimization_report(tmp)

            self.assertEqual(report["summary"]["workload_count"], 3)
            self.assertIn("asymmetric HPA", " ".join(report["guardrails"]))
            self.assertTrue(any("prewarm_replicas" in item["actions"] for item in report["recommendations"]))
            self.assertTrue((Path(tmp) / "reports" / "resource_optimization.json").exists())

    def test_network_security_topology_and_manifests_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        network_security = (repo / "kubernetes" / "network-security.yaml").read_text(encoding="utf-8")

        for expected in ["kind: NetworkPolicy", "default-deny-all", "PeerAuthentication", "mode: STRICT", "AuthorizationPolicy"]:
            self.assertIn(expected, network_security)
        with tempfile.TemporaryDirectory() as tmp:
            report = build_network_security_report(tmp)

            self.assertEqual(report["mtls_mode"], "STRICT")
            self.assertEqual(report["allowed_flow_count"], 3)
            self.assertTrue(any(flow["destination"] == "challenger-predictor" for flow in report["allowed_flows"]))
            self.assertTrue((Path(tmp) / "reports" / "network_security.json").exists())

    def test_gitops_plan_and_progressive_delivery_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        gitops = (repo / "gitops" / "gitops-promotion.yaml").read_text(encoding="utf-8")

        for expected in ["kind: Application", "kind: AppProject", "AnalysisTemplate", "Rollout", "argocd.argoproj.io/sync-wave"]:
            self.assertIn(expected, gitops)
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_gitops_plan(tmp)

            self.assertEqual(plan["deployment_controller"], "Argo CD")
            self.assertIn("shadow-analysis", plan["progressive_delivery"])
            self.assertTrue(any("Wilson" in gate for gate in plan["gates"]))
            self.assertTrue((Path(tmp) / "reports" / "gitops_plan.json").exists())

    def test_disaster_recovery_plan_and_backup_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        dr = (repo / "kubernetes" / "disaster-recovery.yaml").read_text(encoding="utf-8")

        for expected in ["kind: Schedule", "BackupStorageLocation", "VolumeSnapshotClass", "restore-order"]:
            self.assertIn(expected, dr)
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_disaster_recovery_plan(tmp)

            self.assertLessEqual(plan["rpo_minutes"], 15)
            self.assertEqual(plan["restore_sequence"][0]["asset"], "namespace and serving CRDs")
            self.assertTrue(any(item["asset"] == "idempotency cache" for item in plan["restore_sequence"]))
            self.assertTrue((Path(tmp) / "reports" / "disaster_recovery_plan.json").exists())

    def test_governance_evidence_bundle_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        governance = (repo / "kubernetes" / "governance-evidence.yaml").read_text(encoding="utf-8")

        for expected in ["kind: ConfigMap", "kind: Job", "model-card", "risk-register", "reproducibility-manifest"]:
            self.assertIn(expected, governance)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = demo(root)
            bundle = build_governance_bundle(root)
            approval = read_json(root / "governance" / "approval_record.json")
            manifest = read_json(root / "governance" / "reproducibility_manifest.json")

            self.assertEqual(result["governance_bundle"]["release"]["decision"], "approved_for_promotion")
            self.assertEqual(bundle["release"]["model_name"], "credit-risk")
            self.assertEqual(approval["decision"], "approved_for_promotion")
            self.assertTrue(any(item["exists"] and len(item["sha256"]) == 64 for item in manifest["artifact_hashes"]))
            self.assertTrue((root / "reports" / "governance_evidence_bundle.json").exists())

    def test_slo_error_budget_report_and_alert_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        alerts = (repo / "kubernetes" / "slo-alerts.yaml").read_text(encoding="utf-8")

        for expected in ["PrometheusRule", "SLOBurnRateHigh", "multiwindow", "error-budget-freeze"]:
            self.assertIn(expected, alerts)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = demo(root)
            report = build_slo_report(root)

            self.assertEqual(result["slo_error_budget"]["recommended_action"], "allow_progressive_rollout")
            self.assertEqual(report["slos"][0]["name"], "serving_availability")
            self.assertTrue(any(item["name"] == "shadow_score_parity" for item in report["slos"]))
            self.assertTrue((root / "reports" / "slo_error_budget.json").exists())

    def test_cloud_migration_plan_and_infra_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        nodepools = (repo / "kubernetes" / "cloud-nodepools.yaml").read_text(encoding="utf-8")
        terraform = (repo / "infra" / "terraform" / "aws" / "main.tf").read_text(encoding="utf-8")

        for expected in ["NodePool", "EC2NodeClass", "WhenEmptyOrUnderutilized"]:
            self.assertIn(expected, nodepools)
        for expected in ["cluster_compute_config", "node_pools", "aws_s3_bucket"]:
            self.assertIn(expected, terraform)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = demo(root)
            plan = build_cloud_migration_plan(root)

            self.assertEqual(result["cloud_migration"]["primary_target"], "AWS EKS Auto Mode")
            self.assertEqual(plan["managed_service_mapping"]["serving"], "KServe Standard mode on EKS with Gateway API")
            self.assertTrue((root / "reports" / "cloud_migration_plan.json").exists())

    def test_ci_workflow_uploads_artifacts_and_validates_outputs(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        workflow = (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        makefile = (repo / "Makefile").read_text(encoding="utf-8")

        for expected in ["actions/upload-artifact@v6", "actions/attest@v4", "attestations: write", "GITHUB_STEP_SUMMARY", "make ci-verify", "concurrency"]:
            self.assertIn(expected, workflow)
        for expected in ["ci-verify:", "index.html", "tenancy_fairness_report.json", "identity_access_report.json", "flavor_fungibility_plan.json", "cohort_fair_sharing_plan.json", "pod_resource_envelope_plan.json", "event_driven_assets_plan.json", "dag_bundle_versioning_plan.json", "model_cache_plan.json", "multikueue_dispatch_plan.json", "provisioning_admission_plan.json", "indexed_job_resilience_plan.json", "elastic_workload_plan.json", "cost_observability_report.json", "deadline_alert_plan.json", "semantic_telemetry_plan.json", "inference_gateway_plan.json", "kuberay_capacity_plan.json", "topology_placement_plan.json", "device_allocation_plan.json", "release_admission_decision.json", "queue_simulation.json", "performance_budget.json", "accelerator_capacity_plan.json", "orchestration_scorecard.json", "supply_chain_evidence.json", "governance_evidence_bundle.json", "cloud_migration_plan.json"]:
            self.assertIn(expected, makefile)

    def test_accelerator_capacity_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "accelerator-scheduling.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = build_accelerator_capacity_plan(root, project="KServe Model Serving Platform", primary_workload="serving")

            self.assertEqual(len(plan["profiles"]), 3)
            self.assertIn("gpu-a100-mig", {profile["kueue_flavor"] for profile in plan["profiles"]})
            self.assertTrue((root / "reports" / "accelerator_capacity_plan.json").exists())
            self.assertIn("ResourceFlavor", manifest)
            self.assertIn("ResourceClaimTemplate", manifest)
            self.assertIn("nvidia.com/mig-1g.10gb", manifest)

    def test_device_allocation_plan_and_dra_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "dynamic-resource-allocation.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "dynamic-resource-allocation.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_device_allocation_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "admit_dra_backed_serving_canary")
            self.assertTrue((root / "reports" / "device_allocation_plan.json").exists())
            self.assertTrue(any(workload["sharing_strategy"] == "mig" for workload in report["workloads"]))
        for expected in ["DeviceClass", "ResourceClaimTemplate", "InferenceService", "kueue.x-k8s.io/queue-name", "kube_resourceclaim_status_phase"]:
            self.assertIn(expected, manifest)
        for expected in ["Dynamic Resource Allocation", "KServe", "time-sliced", "MIG"]:
            self.assertIn(expected, docs)

    def test_topology_placement_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "topology-aware-scheduling.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "topology-aware-scheduling.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_topology_placement_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_topology_aware_serving_rollout")
            self.assertTrue((root / "reports" / "topology_placement_plan.json").exists())
            self.assertTrue(any(workload["placement"] == "spread" for workload in report["workloads"]))
        for expected in ["kind: Topology", "topologyName", "LeaderWorkerSet", "kueue.x-k8s.io/podset-group-name", "topologySpreadConstraints", "ServingTopologyAssignmentDelayed"]:
            self.assertIn(expected, manifest)
        for expected in ["Topology-Aware Scheduling", "LeaderWorkerSet", "topology spread constraints", "AdmissionChecks"]:
            self.assertIn(expected, docs)

    def test_kuberay_capacity_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "kuberay-kueue-workloads.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "kuberay-kueue.md").read_text(encoding="utf-8")
        dag = (repo / "airflow" / "dags" / "progressive_kserve_rollout_dag.py").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_kuberay_capacity_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_kuberay_shadow_analysis")
            self.assertTrue((root / "reports" / "kuberay_capacity_plan.json").exists())
            self.assertEqual(report["capacity"]["max_gpu_demand"], 4)
        for expected in ["RayService", "RayJob", "serveConfigV2", "enableInTreeAutoscaling", "kueue.x-k8s.io/elastic-job", "CreditRiskRayServiceDegraded"]:
            self.assertIn(expected, manifest)
        for expected in ["RayService", "Kueue", "shadow", "KServe"]:
            self.assertIn(expected, docs)
        for expected in ["submit_kuberay_rayservice_transform", "wait_for_kuberay_rayservice_ready_deferrable", "rayjob/shadow-canary-evaluator"]:
            self.assertIn(expected, dag)

    def test_inference_gateway_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "inference-gateway-routing.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "inference-gateway.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_inference_gateway_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_gateway_inference_extension")
            self.assertEqual(report["pool"]["api_version"], "inference.networking.k8s.io/v1")
            self.assertTrue((root / "reports" / "inference_gateway_plan.json").exists())
        for expected in ["InferencePool", "InferenceObjective", "endpointPickerRef", "FailOpen", "HTTPRoute", "CreditRiskEndpointPickerUnavailable"]:
            self.assertIn(expected, manifest)
        for expected in ["Gateway API Inference Extension", "InferencePool", "Endpoint Picker", "InferenceObjective"]:
            self.assertIn(expected, docs)

    def test_semantic_telemetry_plan_and_collector_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        collector = (repo / "kubernetes" / "opentelemetry-collector.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "semantic-telemetry.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_semantic_telemetry_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_semantic_telemetry_contract")
            self.assertIn("gen_ai.request.model", report["schema"]["required_attributes"])
            self.assertTrue((root / "reports" / "semantic_telemetry_plan.json").exists())
        for expected in ["attributes/semantic_redaction", "gen_ai.input.messages", "gen_ai.output.messages", "deployment.environment.name"]:
            self.assertIn(expected, collector)
        for expected in ["Semantic Telemetry", "GenAI", "Kubernetes", "redaction"]:
            self.assertIn(expected, docs)

    def test_airflow_deadline_alert_plan_and_docs_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        docs = (repo / "docs" / "airflow-deadline-alerts.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_deadline_alert_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_airflow3_serving_deadline_alerts")
            self.assertEqual(report["runtime_config"]["AIRFLOW__CALLBACKS__CALLBACK_EXECUTION_TIMEOUT"], "300")
            self.assertTrue(any(policy["name"] == "gateway_route_convergence" for policy in report["deadline_policies"]))
            self.assertTrue((root / "reports" / "deadline_alert_plan.json").exists())
        for expected in ["Deadline Alerts", "legacy Airflow 2 SLA", "HTTPRoute", "rollback"]:
            self.assertIn(expected, docs)

    def test_cost_observability_report_and_opencost_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "opencost-finops.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "cost-observability.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_cost_observability_report(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_kserve_opencost_guardrails")
            self.assertIn("cost_per_1000_predictions", report["unit_economics"]["primary_kpi"])
            self.assertTrue(any(item["traffic_class"] == "shadow" for item in report["serving_budgets"]))
            self.assertTrue((root / "reports" / "cost_observability_report.json").exists())
        for expected in ["PrometheusRule", "opencost", "KServeCostPerThousandPredictionsHigh", "KServeShadowModelBudgetExceeded", "label_traffic_class"]:
            self.assertIn(expected, manifest)
        for expected in ["OpenCost", "InferenceService", "HTTPRoute", "GPU"]:
            self.assertIn(expected, docs)

    def test_elastic_workload_plan_and_jobset_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "kueue-elastic-workloads.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "kueue-elastic-workloads.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_elastic_workload_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_kueue_elastic_serving_analysis_slices")
            self.assertEqual(report["feature_gate"], "ElasticJobsViaWorkloadSlices")
            self.assertTrue(any(item["replacement_for"] for item in report["workload_slices"]))
            self.assertTrue((root / "reports" / "elastic_workload_plan.json").exists())
        for expected in ["JobSet", "workload-slice-name", "workload-slice-replacement-for", "KServeElasticWorkloadSlicePending"]:
            self.assertIn(expected, manifest)
        for expected in ["Elastic Workloads", "Workload Slices", "JobSet", "rollback"]:
            self.assertIn(expected, docs)

    def test_indexed_job_resilience_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "indexed-job-resilience.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "indexed-job-resilience.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_indexed_job_resilience_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_indexed_serving_job_resilience")
            self.assertEqual(report["kubernetes_job"]["completion_mode"], "Indexed")
            self.assertEqual(report["retry_policy"]["backoff_limit_per_index"], 1)
            self.assertTrue(any(item["stage"] == "rollback_smoke" for item in report["serving_shards"]))
            self.assertTrue((root / "reports" / "indexed_job_resilience_plan.json").exists())
        for expected in ["completionMode: Indexed", "backoffLimitPerIndex", "maxFailedIndexes", "successPolicy", "podFailurePolicy", "JOB_COMPLETION_INDEX", "KServeIndexedJobFailedIndexesHigh"]:
            self.assertIn(expected, manifest)
        for expected in ["Indexed Job Resilience", "Airflow Backfill Create", "successPolicy", "podFailurePolicy", "backoffLimitPerIndex"]:
            self.assertIn(expected, docs)

    def test_provisioning_admission_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "provisioning-admission-checks.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "provisioning-admission.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_provisioning_admission_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_kueue_provisioning_admission_for_serving_analysis")
            self.assertEqual(report["serving_boundary"]["online_predictor_queueing"], "excluded")
            self.assertTrue(any(check["name"] == "rollback_capacity_protected" for check in report["checks"]))
            self.assertTrue((root / "reports" / "provisioning_admission_plan.json").exists())
        for expected in ["AdmissionCheck", "ProvisioningRequestConfig", "kueue.x-k8s.io/provisioning-request", "admissionChecksStrategy", "check-capacity.autoscaling.x-k8s.io", "podSetUpdates", "KServeProvisioningAdmissionPendingTooLong"]:
            self.assertIn(expected, manifest)
        for expected in ["Kueue Provisioning Admission", "InferenceService", "ProvisioningRequest", "online serving"]:
            self.assertIn(expected, docs)

    def test_multikueue_dispatch_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "multikueue-dispatch.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "multikueue-dispatch.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_multikueue_dispatch_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_multikueue_serving_analysis_dispatch")
            self.assertEqual(report["serving_boundary"]["online_predictor_queueing"], "excluded")
            self.assertEqual(report["dispatch_policy"]["controller_name"], "kueue.x-k8s.io/multikueue")
            self.assertIn("status.clusterName", report["dispatch_policy"]["status_fields"])
            self.assertEqual(report["manager_quota"]["nvidia_com_gpu"], 4)
            self.assertTrue(any(check["name"] == "rollback_capacity_protected" for check in report["checks"]))
            self.assertTrue((root / "reports" / "multikueue_dispatch_plan.json").exists())
        for expected in ["MultiKueueConfig", "MultiKueueCluster", "kueue.x-k8s.io/multikueue", "admissionChecksStrategy", "onlineServingBoundary", "kueue.x-k8s.io/prebuilt-workload-name", "KServeMultiKueueDispatchStalled"]:
            self.assertIn(expected, manifest)
        for expected in ["MultiKueue Dispatch", "InferenceService", "worker clusters", "status.clusterName"]:
            self.assertIn(expected, docs)

    def test_model_cache_plan_and_kserve_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kserve" / "local-model-cache.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "model-cache.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_model_cache_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_kserve_local_model_cache")
            self.assertEqual(report["cache_policy"]["namespace_scope"], "LocalModelNamespaceCache")
            self.assertFalse(report["cache_policy"]["latest_tag_allowed"])
            self.assertEqual(report["status_gates"]["minimum_challenger_copies"], 2)
            self.assertTrue(any(item["alias"] == "previous-champion" for item in report["model_artifacts"]))
            self.assertTrue(any(check["name"] == "modelcar_oci_uri_pinned" for check in report["checks"]))
            self.assertTrue((root / "reports" / "model_cache_plan.json").exists())
        for expected in ["LocalModelNamespaceCache", "LocalModelNodeGroup", "sourceModelUri", "modelSize", "nodeGroups", "oci://", "credit-risk-router-modelcar"]:
            self.assertIn(expected, manifest)
        for expected in ["KServe Local Model Cache", "modelcar OCI", "ModelDownloaded", "PVC"]:
            self.assertIn(expected, docs)

    def test_dag_bundle_versioning_plan_and_airflow_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        config = (repo / "airflow" / "dag-bundle-config.ini").read_text(encoding="utf-8")
        docs = (repo / "docs" / "airflow-dag-bundles.md").read_text(encoding="utf-8")
        dag = (repo / "airflow" / "dags" / "progressive_kserve_rollout_dag.py").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_dag_bundle_versioning_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_airflow3_serving_dag_bundle_versioning")
            self.assertFalse(report["rerun_policy"]["core.rerun_with_latest_version"])
            self.assertTrue(report["backfill_policy"]["scheduler_managed_backfills"])
            self.assertIn("httproute_generation", report["serving_release_evidence"])
            self.assertTrue((root / "reports" / "dag_bundle_versioning_plan.json").exists())
        for expected in ["GitDagBundle", "dag_bundle_config_list", "git_conn_id", "disable_bundle_versioning = False", "rerun_with_latest_version = False", "sparse_dirs"]:
            self.assertIn(expected, config)
        for expected in ["Airflow DAG Bundles", "GitDagBundle", "Scheduler-managed backfills", "incident replay"]:
            self.assertIn(expected, docs)
        self.assertIn("rerun_with_latest_version=False", dag)

    def test_event_driven_assets_plan_and_docs_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        docs = (repo / "docs" / "event-driven-assets.md").read_text(encoding="utf-8")
        dag = (repo / "airflow" / "dags" / "progressive_kserve_rollout_dag.py").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_event_driven_assets_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_airflow3_serving_event_assets")
            self.assertEqual(report["asset_expression"], "(CHALLENGER & ROUTER & WEIGHTED_ROUTE) | ROLLBACK_REQUEST")
            self.assertTrue(all(asset["trigger_base_class"] == "BaseEventTrigger" for asset in report["event_assets"]))
            self.assertTrue((root / "reports" / "event_driven_assets_plan.json").exists())
        for expected in ["AssetWatcher", "BaseEventTrigger", "shared_stream_key", "AssetAlias", "conditional asset expression"]:
            self.assertIn(expected, docs)
        for expected in ["EVENT_DRIVEN_ASSET_EXPRESSION", "AssetWatcher", "BaseEventTrigger", "shared_stream_key", "AssetAlias"]:
            self.assertIn(expected, dag)

    def test_pod_resource_envelope_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        docs = (repo / "docs" / "pod-resource-envelopes.md").read_text(encoding="utf-8")
        manifest = (repo / "kubernetes" / "pod-resource-envelopes.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_pod_resource_envelope_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_serving_pod_resource_envelopes_and_scheduling_gates")
            self.assertEqual(report["feature_gates"]["PodSchedulingReadiness"], "stable since Kubernetes 1.30")
            self.assertTrue(all(workload["scheduling_gates"] for workload in report["workloads"]))
            self.assertTrue((root / "reports" / "pod_resource_envelope_plan.json").exists())
        for expected in ["PodLevelResources", "schedulingGates", "scheduler_pending_pods", "PodLevelResourceManagers"]:
            self.assertIn(expected, docs)
        for expected in ["schedulingGates", "resources:", "credit-risk-router-canary", "shadow-canary-analysis", "rollback-smoke-probe"]:
            self.assertIn(expected, manifest)

    def test_cohort_fair_sharing_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        docs = (repo / "docs" / "kueue-cohort-fair-sharing.md").read_text(encoding="utf-8")
        manifest = (repo / "kubernetes" / "kueue-cohort-fair-sharing.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_cohort_fair_sharing_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_serving_kueue_cohort_fair_sharing")
            self.assertEqual(report["feature_gates"]["AdmissionFairSharing"], "beta since Kueue v0.15 and enabled by default")
            self.assertGreater(report["cluster_queues"][0]["weight"], report["cluster_queues"][-1]["weight"])
            self.assertTrue((root / "reports" / "cohort_fair_sharing_plan.json").exists())
        for expected in ["Fair Sharing", "Admission Fair Sharing", "borrowingLimit", "lendingLimit", "preemptionStrategies"]:
            self.assertIn(expected, docs)
        for expected in ["AdmissionFairSharing", "LessThanInitialShare", "fairSharing", "borrowingLimit", "lendingLimit", "LocalQueue"]:
            self.assertIn(expected, manifest)

    def test_flavor_fungibility_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        docs = (repo / "docs" / "kueue-flavor-fungibility.md").read_text(encoding="utf-8")
        manifest = (repo / "kubernetes" / "kueue-flavor-fungibility.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_flavor_fungibility_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_serving_kueue_flavor_fungibility")
            self.assertTrue(all(policy["when_can_preempt"] == "TryNextFlavor" for policy in report["flavor_policies"]))
            self.assertTrue(any(policy["name"] == "canary-analysis-gpu" for policy in report["flavor_policies"]))
            self.assertTrue((root / "reports" / "flavor_fungibility_plan.json").exists())
        for expected in ["ResourceFlavor", "flavorFungibility", "TryNextFlavor", "BorrowingOverPreemption", "gpu-l4-reserved"]:
            self.assertIn(expected, manifest)
        for expected in ["Kueue Flavor Fungibility", "ResourceFlavor", "TryNextFlavor", "BorrowingOverPreemption"]:
            self.assertIn(expected, docs)

    def test_tenancy_fairness_report_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "multitenancy-fairness.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_tenancy_report(root)
            tenant_names = {tenant["name"] for tenant in report["tenants"]}

            self.assertTrue(report["passed"])
            self.assertIn("online-serving", tenant_names)
            self.assertIn("mlops-serving-cohort", report["fairness"]["cohort"])
            self.assertTrue((root / "reports" / "tenancy_fairness_report.json").exists())
            for expected in ["ResourceQuota", "LimitRange", "RoleBinding", "NetworkPolicy", "Cohort", "ClusterQueue", "airflow-tenant-pools"]:
                self.assertIn(expected, manifest)

    def test_identity_access_report_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "workload-identity.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_identity_access_report(root)
            service_accounts = {identity["service_account"] for identity in report["identities"]}

            self.assertTrue(report["passed"])
            self.assertIn("canary-analysis-runner", service_accounts)
            self.assertTrue((root / "reports" / "identity_access_report.json").exists())
            for expected in ["ServiceAccount", "automountServiceAccountToken: false", "SecretStore", "ExternalSecret", "refreshInterval: 30m", "eks.amazonaws.com/role-arn", "spiffe.io/spiffe-id", "airflow-workload-identity-policy"]:
                self.assertIn(expected, manifest)

    def test_orchestration_scorecard_covers_advanced_controls(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scorecard = build_orchestration_scorecard(root, repo_root=repo, project="KServe Model Serving Platform")
            names = {check["name"] for check in scorecard["checks"] if check["passed"]}

            self.assertTrue(scorecard["passed"])
            self.assertGreaterEqual(scorecard["score"], 90.0)
            self.assertIn("dynamic_task_mapping", names)
            self.assertIn("kueue_admission", names)
            self.assertIn("airflow_deadline_alerts", names)
            self.assertIn("opencost_finops", names)
            self.assertIn("kueue_elastic_workloads", names)
            self.assertIn("indexed_job_resilience", names)
            self.assertIn("provisioning_admission_checks", names)
            self.assertIn("multikueue_dispatch", names)
            self.assertIn("kserve_model_cache", names)
            self.assertIn("airflow_dag_bundle_versioning", names)
            self.assertIn("airflow_event_driven_assets", names)
            self.assertIn("pod_resource_envelopes", names)
            self.assertIn("kueue_cohort_fair_sharing", names)
            self.assertIn("kueue_flavor_fungibility", names)
            self.assertIn("supply_chain_provenance", names)
            self.assertTrue((root / "reports" / "orchestration_scorecard.json").exists())

    def test_supply_chain_evidence_and_policy_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        policy = (repo / "kubernetes" / "supply-chain-policy.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root / "reports" / "demo.json", {"status": "ok"})
            evidence = build_supply_chain_evidence(
                root,
                project="KServe Model Serving Platform",
                artifact_name="kserve-serving-demo-artifacts",
                workflow="KServe Serving CI",
                namespace="mlops-serving",
            )

            self.assertEqual(evidence["artifact_count"], 1)
            self.assertEqual(len(evidence["artifacts"][0]["sha256"]), 64)
            self.assertEqual(evidence["subject"]["attestation_action"], "actions/attest@v4")
            self.assertTrue((root / "supply-chain" / "subject.checksums.txt").exists())
            self.assertIn("ClusterImagePolicy", policy)
            self.assertIn("predicateType: https://slsa.dev/provenance/v1", policy)
            self.assertIn("policy.sigstore.dev/include", policy)

    def test_artifact_index_links_key_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = demo(root)
            index = (root / "reports" / "index.html").read_text(encoding="utf-8")

            self.assertTrue(result["artifact_index"].endswith("index.html"))
            for expected in [
                "kserve_serving_dashboard.html",
                "canary_decision.json",
                "governance_evidence_bundle.json",
                "slo_error_budget.json",
                "accelerator_capacity_plan.json",
                "device_allocation_plan.json",
                "topology_placement_plan.json",
                "kuberay_capacity_plan.json",
                "inference_gateway_plan.json",
                "semantic_telemetry_plan.json",
                "deadline_alert_plan.json",
                "cost_observability_report.json",
                "elastic_workload_plan.json",
                "indexed_job_resilience_plan.json",
                "provisioning_admission_plan.json",
                "multikueue_dispatch_plan.json",
                "model_cache_plan.json",
                "dag_bundle_versioning_plan.json",
                "event_driven_assets_plan.json",
                "pod_resource_envelope_plan.json",
                "cohort_fair_sharing_plan.json",
                "flavor_fungibility_plan.json",
                "tenancy_fairness_report.json",
                "identity_access_report.json",
                "performance_budget.json",
                "queue_simulation.json",
                "release_admission_decision.json",
                "resource_optimization.json",
                "network_security.json",
                "chaos_drill_report.json",
                "gitops_plan.json",
                "orchestration_scorecard.json",
                "supply_chain_evidence.json",
                "cloud_migration_plan.json",
            ]:
                self.assertIn(expected, index)

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
            self.assertTrue((root / "reports" / "index.html").exists())
            self.assertTrue((root / "reports" / "accelerator_capacity_plan.json").exists())
            self.assertTrue((root / "reports" / "device_allocation_plan.json").exists())
            self.assertTrue((root / "reports" / "topology_placement_plan.json").exists())
            self.assertTrue((root / "reports" / "kuberay_capacity_plan.json").exists())
            self.assertTrue((root / "reports" / "inference_gateway_plan.json").exists())
            self.assertTrue((root / "reports" / "semantic_telemetry_plan.json").exists())
            self.assertTrue((root / "reports" / "deadline_alert_plan.json").exists())
            self.assertTrue((root / "reports" / "cost_observability_report.json").exists())
            self.assertTrue((root / "reports" / "elastic_workload_plan.json").exists())
            self.assertTrue((root / "reports" / "indexed_job_resilience_plan.json").exists())
            self.assertTrue((root / "reports" / "multikueue_dispatch_plan.json").exists())
            self.assertTrue((root / "reports" / "model_cache_plan.json").exists())
            self.assertTrue((root / "reports" / "dag_bundle_versioning_plan.json").exists())
            self.assertTrue((root / "reports" / "event_driven_assets_plan.json").exists())
            self.assertTrue((root / "reports" / "pod_resource_envelope_plan.json").exists())
            self.assertTrue((root / "reports" / "cohort_fair_sharing_plan.json").exists())
            self.assertTrue((root / "reports" / "flavor_fungibility_plan.json").exists())
            self.assertTrue((root / "reports" / "tenancy_fairness_report.json").exists())
            self.assertTrue((root / "reports" / "identity_access_report.json").exists())
            self.assertTrue((root / "reports" / "performance_budget.json").exists())
            self.assertTrue((root / "reports" / "queue_simulation.json").exists())
            self.assertTrue((root / "reports" / "release_admission_decision.json").exists())
            self.assertTrue((root / "reports" / "orchestration_scorecard.json").exists())
            self.assertTrue((root / "reports" / "supply_chain_evidence.json").exists())
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
