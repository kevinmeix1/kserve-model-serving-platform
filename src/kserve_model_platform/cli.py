from __future__ import annotations

import argparse
import json
from pathlib import Path

from .accelerator_plan import build_accelerator_capacity_plan
from .admin_access_diagnostics import build_admin_access_diagnostic_plan
from .advanced_device_sharing import build_advanced_device_sharing_plan
from .ai_workload_telemetry import build_ai_workload_telemetry_plan
from .airflow_stateful_orchestration import build_airflow_stateful_orchestration_plan
from .artifact_index import render_artifact_index
from .asset_partitioning import build_asset_partitioning_plan
from .chaos import run_chaos_drill
from .cloud_migration import build_cloud_migration_plan
from .cohort_fair_sharing import build_cohort_fair_sharing_plan
from .control_plane_diagnostics import build_control_plane_diagnostics_plan
from .constrained_impersonation import build_constrained_impersonation_plan
from .cost_observability import build_cost_observability_report
from .dag_bundle_versioning import build_dag_bundle_versioning_plan
from .dashboard import render_dashboard
from .deadline_alerts import build_deadline_alert_plan
from .disaster_recovery import build_disaster_recovery_plan
from .device_allocation import build_device_allocation_plan
from .elastic_workload import build_elastic_workload_plan
from .event_driven_assets import build_event_driven_assets_plan
from .flavor_fungibility import build_flavor_fungibility_plan
from .gitops_release import build_gitops_plan
from .governance import build_governance_bundle
from .hpa_scale_to_zero import build_hpa_scale_to_zero_plan
from .identity import build_identity_access_report
from .indexed_job_resilience import build_indexed_job_resilience_plan
from .inplace_resize import build_inplace_resize_plan
from .inference_gateway import build_inference_gateway_plan
from .io import read_json, write_csv, write_json
from .kuberay_capacity import build_kuberay_capacity_plan
from .llm_inference_readiness import build_llm_inference_readiness_plan
from .memory_qos import build_memory_qos_plan
from .model_cache import build_model_cache_plan
from .models import generate_requests
from .monitoring import build_report, evaluate_canary
from .multi_team_readiness import build_multi_team_readiness_plan
from .multikueue_dispatch import build_multikueue_dispatch_plan
from .network_security import build_network_security_report
from .orchestration_scorecard import build_orchestration_scorecard
from .operational_readiness import build_operational_readiness_review
from .pending_workload_visibility import build_pending_workload_visibility_plan
from .policy_audit import audit_platform_policy
from .performance_budget import build_performance_budget_report
from .pod_resource_envelopes import build_pod_resource_envelope_plan
from .provisioning_admission import build_provisioning_admission_plan
from .queue_simulator import build_queue_simulation
from .release_admission import build_release_admission_decision
from .registry import aliases as registry_aliases
from .registry import promote_challenger, rollback as rollback_registry, seed_registry
from .resource_health_status import build_resource_health_status_plan
from .resource_optimizer import build_resource_optimization_report
from .rollout_control import build_rollout_plan
from .runtime_security import build_runtime_security_plan
from .serving import deploy as deploy_kserve
from .serving import health, predict
from .semantic_telemetry import build_semantic_telemetry_plan
from .slo import build_slo_report
from .supply_chain import build_supply_chain_evidence
from .suspended_job_resources import build_suspended_job_resource_plan
from .tenancy import build_tenancy_report
from .topology_placement import build_topology_placement_plan
from .traceability import build_trace_report
from .transformer_explainer_readiness import build_transformer_explainer_readiness_plan
from .workload_aware_scheduling import build_workload_aware_scheduling_plan


def root_path(output: str | Path) -> Path:
    return Path(output)


def deploy(output: str | Path, *, challenger_percent: int = 10) -> dict:
    root = root_path(output)
    seed_registry(root)
    return deploy_kserve(root, challenger_percent=challenger_percent, shadow=True)


def sample_payload() -> dict:
    return {
        "request_id": "req_live_001",
        "customer_id": "cust_live_001",
        "product": "card",
        "income": 58000,
        "debt_ratio": 0.72,
        "delinquencies": 2,
        "utilization": 0.84,
        "employment_years": 2.4,
    }


def predict_once(output: str | Path) -> dict:
    root = root_path(output)
    if not health(root).get("healthy"):
        deploy(root)
    return predict(root, sample_payload())


def simulate(output: str | Path, *, requests: int = 120) -> dict:
    root = root_path(output)
    if not health(root).get("healthy"):
        deploy(root)
    payloads = generate_requests(requests)
    write_csv(root / "data" / "incoming_requests.csv", payloads)
    responses = [predict(root, payload) for payload in payloads]
    return {
        "request_count": len(payloads),
        "success_count": sum(1 for row in responses if row.get("status") == "success"),
        "rejected_count": sum(1 for row in responses if row.get("status") == "rejected"),
    }


def monitor(output: str | Path) -> dict:
    root = root_path(output)
    if not (root / "logs" / "predictions.jsonl").exists():
        simulate(root)
    report = build_report(root)
    decision = evaluate_canary(report)
    write_json(root / "reports" / "canary_decision.json", decision)
    deployment = read_json(root / "deployments" / "kserve_state.json")
    rollout_plan = build_rollout_plan(root)
    inference_gateway_path = root / "reports" / "inference_gateway_plan.json"
    inference_gateway_plan = read_json(inference_gateway_path) if inference_gateway_path.exists() else None
    semantic_telemetry_path = root / "reports" / "semantic_telemetry_plan.json"
    semantic_telemetry_plan = read_json(semantic_telemetry_path) if semantic_telemetry_path.exists() else build_semantic_telemetry_plan(root)
    llm_readiness_path = root / "reports" / "llm_inference_readiness_plan.json"
    llm_readiness = read_json(llm_readiness_path) if llm_readiness_path.exists() else None
    transformer_explainer_path = root / "reports" / "transformer_explainer_readiness_plan.json"
    transformer_explainer = (
        read_json(transformer_explainer_path)
        if transformer_explainer_path.exists()
        else build_transformer_explainer_readiness_plan(root)
    )
    dashboard = render_dashboard(
        root / "reports" / "kserve_serving_dashboard.html",
        deployment=deployment,
        report=report,
        decision=decision,
        aliases=registry_aliases(root),
        rollout_plan=rollout_plan,
        inference_gateway_plan=inference_gateway_plan,
        semantic_telemetry_plan=semantic_telemetry_plan,
        llm_readiness_plan=llm_readiness,
        transformer_explainer_plan=transformer_explainer,
    )
    return {
        "report": report,
        "decision": decision,
        "rollout_plan": rollout_plan,
        "transformer_explainer": transformer_explainer,
        "dashboard": str(dashboard),
    }


def runtime_init(output: str | Path, *, requests: int = 120) -> dict:
    root = root_path(output)
    deployment = deploy(root, challenger_percent=10)
    simulation = simulate(root, requests=requests)
    monitoring = monitor(root)
    return {
        "deployment": deployment,
        "simulation": simulation,
        "canary": monitoring["decision"],
        "dashboard": monitoring["dashboard"],
    }


def governance(output: str | Path) -> dict:
    root = root_path(output)
    if not (root / "reports" / "canary_decision.json").exists():
        monitor(root)
    return build_governance_bundle(root)


def slo_report(output: str | Path) -> dict:
    root = root_path(output)
    if not (root / "reports" / "canary_decision.json").exists():
        monitor(root)
    return build_slo_report(root)


def promote(output: str | Path) -> dict:
    root = root_path(output)
    decision_path = root / "reports" / "canary_decision.json"
    if not decision_path.exists():
        monitor(root)
    decision = read_json(decision_path)
    if not decision.get("passed"):
        return {"promoted": False, "reason": "canary_gates_failed", "decision": decision}
    result = promote_challenger(root)
    deploy_kserve(root, challenger_percent=0, shadow=False)
    return result


def rollback(output: str | Path) -> dict:
    root = root_path(output)
    result = rollback_registry(root)
    deploy_kserve(root, challenger_percent=10, shadow=True)
    return result


def demo(output: str | Path) -> dict:
    root = root_path(output)
    deployment = deploy(root, challenger_percent=10)
    simulation = simulate(root, requests=120)
    monitoring = monitor(root)
    policy_audit = audit_platform_policy(Path.cwd(), output_root=root)
    trace_report = build_trace_report(root)
    chaos_drill = run_chaos_drill(root)
    resource_optimization = build_resource_optimization_report(root)
    network_security = build_network_security_report(root)
    gitops_plan = build_gitops_plan(root)
    disaster_recovery = build_disaster_recovery_plan(root)
    governance_bundle = build_governance_bundle(root)
    slo_error_budget = build_slo_report(root)
    cloud_migration = build_cloud_migration_plan(root)
    accelerator_capacity = build_accelerator_capacity_plan(
        root,
        project="KServe Model Serving Platform",
        primary_workload="online inference, shadow scoring, and canary analysis",
    )
    device_allocation = build_device_allocation_plan(root)
    resource_health_status = build_resource_health_status_plan(root)
    advanced_device_sharing = build_advanced_device_sharing_plan(root)
    admin_access_diagnostics = build_admin_access_diagnostic_plan(root)
    inplace_resize = build_inplace_resize_plan(root)
    topology_placement = build_topology_placement_plan(root)
    kuberay_capacity = build_kuberay_capacity_plan(root)
    inference_gateway = build_inference_gateway_plan(root)
    semantic_telemetry = build_semantic_telemetry_plan(root)
    llm_readiness = build_llm_inference_readiness_plan(root)
    transformer_explainer = build_transformer_explainer_readiness_plan(root)
    render_dashboard(
        root / "reports" / "kserve_serving_dashboard.html",
        deployment=deployment,
        report=monitoring["report"],
        decision=monitoring["decision"],
        aliases=registry_aliases(root),
        rollout_plan=monitoring["rollout_plan"],
        inference_gateway_plan=inference_gateway,
        semantic_telemetry_plan=semantic_telemetry,
        llm_readiness_plan=llm_readiness,
        transformer_explainer_plan=transformer_explainer,
    )
    deadline_alerts = build_deadline_alert_plan(root)
    cost_observability = build_cost_observability_report(root)
    elastic_workload = build_elastic_workload_plan(root)
    indexed_job_resilience = build_indexed_job_resilience_plan(root)
    provisioning_admission = build_provisioning_admission_plan(root)
    multikueue_dispatch = build_multikueue_dispatch_plan(root)
    model_cache = build_model_cache_plan(root)
    dag_bundle_versioning = build_dag_bundle_versioning_plan(root)
    asset_partitioning = build_asset_partitioning_plan(root)
    airflow_stateful_orchestration = build_airflow_stateful_orchestration_plan(root)
    multi_team_readiness = build_multi_team_readiness_plan(root)
    event_driven_assets = build_event_driven_assets_plan(root)
    pod_resource_envelopes = build_pod_resource_envelope_plan(root)
    cohort_fair_sharing = build_cohort_fair_sharing_plan(root)
    flavor_fungibility = build_flavor_fungibility_plan(root)
    pending_workload_visibility = build_pending_workload_visibility_plan(root)
    tenancy = build_tenancy_report(root)
    identity_access = build_identity_access_report(root)
    performance_budget = build_performance_budget_report(root)
    queue_simulation = build_queue_simulation(root)
    workload_aware_scheduling = build_workload_aware_scheduling_plan(root)
    runtime_security = build_runtime_security_plan(root)
    control_plane_diagnostics = build_control_plane_diagnostics_plan(root)
    memory_qos = build_memory_qos_plan(root)
    hpa_scale_to_zero = build_hpa_scale_to_zero_plan(root)
    suspended_job_resources = build_suspended_job_resource_plan(root)
    constrained_impersonation = build_constrained_impersonation_plan(root)
    ai_workload_telemetry = build_ai_workload_telemetry_plan(root)
    supply_chain = build_supply_chain_evidence(
        root,
        project="KServe Model Serving Platform",
        artifact_name="kserve-serving-demo-artifacts",
        workflow="KServe Serving CI",
        namespace="mlops-serving",
    )
    release_admission = build_release_admission_decision(root)
    operational_readiness = build_operational_readiness_review(root)
    artifact_index = render_artifact_index(
        root,
        title="KServe Model Serving Platform",
        description="Reviewer landing page for generated serving dashboard, rollout evidence, SLOs, migration, and reliability artifacts.",
        dashboard="kserve_serving_dashboard.html",
    )
    orchestration_scorecard = build_orchestration_scorecard(root, project="KServe Model Serving Platform")
    idempotent = predict(root, generate_requests(1)[0])
    return {
        "deployment": deployment,
        "simulation": simulation,
        "canary": monitoring["decision"],
        "rollout_plan": monitoring["rollout_plan"],
        "policy_audit": policy_audit,
        "trace_report": trace_report,
        "chaos_drill": chaos_drill,
        "resource_optimization": resource_optimization,
        "network_security": network_security,
        "gitops_plan": gitops_plan,
        "disaster_recovery": disaster_recovery,
        "governance_bundle": governance_bundle,
        "slo_error_budget": slo_error_budget,
        "cloud_migration": cloud_migration,
        "accelerator_capacity": accelerator_capacity,
        "device_allocation": device_allocation,
        "resource_health_status": resource_health_status,
        "advanced_device_sharing": advanced_device_sharing,
        "admin_access_diagnostics": admin_access_diagnostics,
        "inplace_resize": inplace_resize,
        "topology_placement": topology_placement,
        "kuberay_capacity": kuberay_capacity,
        "inference_gateway": inference_gateway,
        "semantic_telemetry": semantic_telemetry,
        "llm_readiness": llm_readiness,
        "transformer_explainer": transformer_explainer,
        "deadline_alerts": deadline_alerts,
        "cost_observability": cost_observability,
        "elastic_workload": elastic_workload,
        "indexed_job_resilience": indexed_job_resilience,
        "provisioning_admission": provisioning_admission,
        "multikueue_dispatch": multikueue_dispatch,
        "model_cache": model_cache,
        "dag_bundle_versioning": dag_bundle_versioning,
        "asset_partitioning": asset_partitioning,
        "airflow_stateful_orchestration": airflow_stateful_orchestration,
        "multi_team_readiness": multi_team_readiness,
        "event_driven_assets": event_driven_assets,
        "pod_resource_envelopes": pod_resource_envelopes,
        "cohort_fair_sharing": cohort_fair_sharing,
        "flavor_fungibility": flavor_fungibility,
        "pending_workload_visibility": pending_workload_visibility,
        "tenancy": tenancy,
        "identity_access": identity_access,
        "performance_budget": performance_budget,
        "queue_simulation": queue_simulation,
        "workload_aware_scheduling": workload_aware_scheduling,
        "runtime_security": runtime_security,
        "control_plane_diagnostics": control_plane_diagnostics,
        "memory_qos": memory_qos,
        "hpa_scale_to_zero": hpa_scale_to_zero,
        "suspended_job_resources": suspended_job_resources,
        "constrained_impersonation": constrained_impersonation,
        "ai_workload_telemetry": ai_workload_telemetry,
        "release_admission": release_admission,
        "operational_readiness": operational_readiness,
        "artifact_index": str(artifact_index),
        "orchestration_scorecard": orchestration_scorecard,
        "supply_chain": supply_chain,
        "dashboard": monitoring["dashboard"],
        "idempotent_replay": idempotent.get("idempotent_replay", False),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KServe model serving platform")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in [
        "demo",
        "runtime-init",
        "deploy",
        "predict",
        "simulate",
        "monitor",
        "promote",
        "rollback",
        "health",
        "plan-rollout",
        "policy-audit",
        "trace-report",
        "chaos-drill",
        "optimize-resources",
        "network-security",
        "gitops-plan",
        "dr-plan",
        "governance-bundle",
        "slo-report",
        "cloud-plan",
        "supply-chain",
        "orchestration-scorecard",
        "accelerator-plan",
        "device-plan",
        "resource-health-status",
        "advanced-device-sharing",
        "admin-access-diagnostics",
        "inplace-resize-plan",
        "topology-plan",
        "kuberay-plan",
        "inference-gateway-plan",
        "semantic-telemetry-plan",
        "llm-inference-readiness",
        "transformer-explainer-readiness",
        "deadline-alerts-plan",
        "cost-observability",
        "elastic-workload-plan",
        "indexed-job-resilience",
        "provisioning-admission",
        "multikueue-dispatch",
        "model-cache",
        "dag-bundle-plan",
        "asset-partitioning-plan",
        "airflow-stateful-orchestration",
        "multi-team-readiness",
        "event-driven-assets",
        "pod-resource-envelopes",
        "cohort-fair-sharing",
        "flavor-fungibility",
        "pending-workload-visibility",
        "tenancy-report",
        "identity-report",
        "performance-budget",
        "queue-simulation",
        "workload-aware-scheduling",
        "runtime-security",
        "control-plane-diagnostics",
        "memory-qos",
        "hpa-scale-zero",
        "suspended-job-resources",
        "constrained-impersonation",
        "release-admission",
    ]:
        cmd = sub.add_parser(command)
        cmd.add_argument("--output", default=".local")
        if command in {"deploy", "simulate", "runtime-init"}:
            cmd.add_argument("--requests", type=int, default=120)
    args = parser.parse_args(argv)
    if args.command == "demo":
        print(json.dumps(demo(args.output), indent=2, sort_keys=True))
    elif args.command == "runtime-init":
        print(json.dumps(runtime_init(args.output, requests=args.requests), indent=2, sort_keys=True))
    elif args.command == "deploy":
        print(json.dumps(deploy(args.output), indent=2, sort_keys=True))
    elif args.command == "predict":
        print(json.dumps(predict_once(args.output), indent=2, sort_keys=True))
    elif args.command == "simulate":
        print(json.dumps(simulate(args.output, requests=args.requests), indent=2, sort_keys=True))
    elif args.command == "monitor":
        print(json.dumps(monitor(args.output), indent=2, sort_keys=True))
    elif args.command == "promote":
        print(json.dumps(promote(args.output), indent=2, sort_keys=True))
    elif args.command == "rollback":
        print(json.dumps(rollback(args.output), indent=2, sort_keys=True))
    elif args.command == "health":
        print(json.dumps(health(args.output), indent=2, sort_keys=True))
    elif args.command == "plan-rollout":
        print(json.dumps(build_rollout_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "policy-audit":
        print(json.dumps(audit_platform_policy(Path.cwd(), output_root=args.output), indent=2, sort_keys=True))
    elif args.command == "trace-report":
        print(json.dumps(build_trace_report(args.output), indent=2, sort_keys=True))
    elif args.command == "chaos-drill":
        print(json.dumps(run_chaos_drill(args.output), indent=2, sort_keys=True))
    elif args.command == "optimize-resources":
        print(json.dumps(build_resource_optimization_report(args.output), indent=2, sort_keys=True))
    elif args.command == "network-security":
        print(json.dumps(build_network_security_report(args.output), indent=2, sort_keys=True))
    elif args.command == "gitops-plan":
        print(json.dumps(build_gitops_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "dr-plan":
        print(json.dumps(build_disaster_recovery_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "governance-bundle":
        print(json.dumps(governance(args.output), indent=2, sort_keys=True))
    elif args.command == "slo-report":
        print(json.dumps(slo_report(args.output), indent=2, sort_keys=True))
    elif args.command == "cloud-plan":
        print(json.dumps(build_cloud_migration_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "supply-chain":
        print(json.dumps(build_supply_chain_evidence(args.output, project="KServe Model Serving Platform", artifact_name="kserve-serving-demo-artifacts", workflow="KServe Serving CI", namespace="mlops-serving"), indent=2, sort_keys=True))
    elif args.command == "orchestration-scorecard":
        print(json.dumps(build_orchestration_scorecard(args.output, project="KServe Model Serving Platform"), indent=2, sort_keys=True))
    elif args.command == "accelerator-plan":
        print(json.dumps(build_accelerator_capacity_plan(args.output, project="KServe Model Serving Platform", primary_workload="online inference, shadow scoring, and canary analysis"), indent=2, sort_keys=True))
    elif args.command == "device-plan":
        print(json.dumps(build_device_allocation_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "resource-health-status":
        print(json.dumps(build_resource_health_status_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "advanced-device-sharing":
        print(json.dumps(build_advanced_device_sharing_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "admin-access-diagnostics":
        print(json.dumps(build_admin_access_diagnostic_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "inplace-resize-plan":
        print(json.dumps(build_inplace_resize_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "topology-plan":
        print(json.dumps(build_topology_placement_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "kuberay-plan":
        print(json.dumps(build_kuberay_capacity_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "inference-gateway-plan":
        print(json.dumps(build_inference_gateway_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "semantic-telemetry-plan":
        print(json.dumps(build_semantic_telemetry_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "llm-inference-readiness":
        print(json.dumps(build_llm_inference_readiness_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "transformer-explainer-readiness":
        print(json.dumps(build_transformer_explainer_readiness_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "deadline-alerts-plan":
        print(json.dumps(build_deadline_alert_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "cost-observability":
        print(json.dumps(build_cost_observability_report(args.output), indent=2, sort_keys=True))
    elif args.command == "elastic-workload-plan":
        print(json.dumps(build_elastic_workload_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "indexed-job-resilience":
        print(json.dumps(build_indexed_job_resilience_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "provisioning-admission":
        print(json.dumps(build_provisioning_admission_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "multikueue-dispatch":
        print(json.dumps(build_multikueue_dispatch_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "model-cache":
        print(json.dumps(build_model_cache_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "dag-bundle-plan":
        print(json.dumps(build_dag_bundle_versioning_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "asset-partitioning-plan":
        print(json.dumps(build_asset_partitioning_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "airflow-stateful-orchestration":
        print(json.dumps(build_airflow_stateful_orchestration_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "multi-team-readiness":
        print(json.dumps(build_multi_team_readiness_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "event-driven-assets":
        print(json.dumps(build_event_driven_assets_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "pod-resource-envelopes":
        print(json.dumps(build_pod_resource_envelope_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "cohort-fair-sharing":
        print(json.dumps(build_cohort_fair_sharing_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "flavor-fungibility":
        print(json.dumps(build_flavor_fungibility_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "pending-workload-visibility":
        print(json.dumps(build_pending_workload_visibility_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "tenancy-report":
        print(json.dumps(build_tenancy_report(args.output), indent=2, sort_keys=True))
    elif args.command == "identity-report":
        print(json.dumps(build_identity_access_report(args.output), indent=2, sort_keys=True))
    elif args.command == "performance-budget":
        print(json.dumps(build_performance_budget_report(args.output), indent=2, sort_keys=True))
    elif args.command == "queue-simulation":
        print(json.dumps(build_queue_simulation(args.output), indent=2, sort_keys=True))
    elif args.command == "workload-aware-scheduling":
        print(json.dumps(build_workload_aware_scheduling_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "runtime-security":
        print(json.dumps(build_runtime_security_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "control-plane-diagnostics":
        print(json.dumps(build_control_plane_diagnostics_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "memory-qos":
        print(json.dumps(build_memory_qos_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "hpa-scale-zero":
        print(json.dumps(build_hpa_scale_to_zero_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "suspended-job-resources":
        print(json.dumps(build_suspended_job_resource_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "constrained-impersonation":
        print(json.dumps(build_constrained_impersonation_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "release-admission":
        print(json.dumps(build_release_admission_decision(args.output), indent=2, sort_keys=True))
    return 0
