.PHONY: demo runtime-init deploy predict simulate monitor promote rollback health api-run api-smoke demo-voice demo-video test-api lint-api verify-serving-lock package package-smoke kserve-schema-contract compose-config compose-up compose-down compose-smoke plan-rollout policy-audit trace-report chaos-drill optimize-resources network-security gitops-plan dr-plan governance-bundle slo-report cloud-plan supply-chain orchestration-scorecard accelerator-plan device-plan resource-health-status advanced-device-sharing admin-access-diagnostics inplace-resize-plan topology-plan kuberay-plan inference-gateway-plan semantic-telemetry-plan deadline-alerts-plan cost-observability elastic-workload-plan indexed-job-resilience provisioning-admission multikueue-dispatch model-cache dag-bundle-plan asset-partitioning-plan airflow-stateful-orchestration airflow-sdk-contract multi-team-readiness event-driven-assets pod-resource-envelopes cohort-fair-sharing flavor-fungibility pending-workload-visibility tenancy-report identity-report performance-budget queue-simulation workload-aware-scheduling runtime-security control-plane-diagnostics memory-qos hpa-scale-zero suspended-job-resources constrained-impersonation release-admission ci-verify minikube-up kubernetes-plan test clean

PYTHON ?= python3
SERVING_FILES := \
	src/kserve_model_platform/api.py \
	src/kserve_model_platform/runtime_contract.py \
	src/kserve_model_platform/runtime_state.py \
	src/kserve_model_platform/v2_protocol.py \
	tests/test_kserve_model_platform.py \
	tests/test_serving_api.py \
	tools/smoke_wheel.py \
	tools/smoke_serving_api.py \
	tools/verify_locked_environment.py \
	tools/validate_kserve_manifest.py

demo:
	PYTHONPATH=src python3 -m kserve_model_platform demo --output .local

runtime-init:
	PYTHONPATH=src python3 -m kserve_model_platform runtime-init --output .local

deploy:
	PYTHONPATH=src python3 -m kserve_model_platform deploy --output .local

predict:
	PYTHONPATH=src python3 -m kserve_model_platform predict --output .local

simulate:
	PYTHONPATH=src python3 -m kserve_model_platform simulate --output .local

monitor:
	PYTHONPATH=src python3 -m kserve_model_platform monitor --output .local

plan-rollout:
	PYTHONPATH=src python3 -m kserve_model_platform plan-rollout --output .local

policy-audit:
	PYTHONPATH=src python3 -m kserve_model_platform policy-audit --output .local

trace-report:
	PYTHONPATH=src python3 -m kserve_model_platform trace-report --output .local

chaos-drill:
	PYTHONPATH=src python3 -m kserve_model_platform chaos-drill --output .local

optimize-resources:
	PYTHONPATH=src python3 -m kserve_model_platform optimize-resources --output .local

network-security:
	PYTHONPATH=src python3 -m kserve_model_platform network-security --output .local

gitops-plan:
	PYTHONPATH=src python3 -m kserve_model_platform gitops-plan --output .local

dr-plan:
	PYTHONPATH=src python3 -m kserve_model_platform dr-plan --output .local

governance-bundle:
	PYTHONPATH=src python3 -m kserve_model_platform governance-bundle --output .local

slo-report:
	PYTHONPATH=src python3 -m kserve_model_platform slo-report --output .local

cloud-plan:
	PYTHONPATH=src python3 -m kserve_model_platform cloud-plan --output .local

supply-chain:
	PYTHONPATH=src python3 -m kserve_model_platform supply-chain --output .local

orchestration-scorecard:
	PYTHONPATH=src python3 -m kserve_model_platform orchestration-scorecard --output .local

accelerator-plan:
	PYTHONPATH=src python3 -m kserve_model_platform accelerator-plan --output .local

device-plan:
	PYTHONPATH=src python3 -m kserve_model_platform device-plan --output .local

resource-health-status:
	PYTHONPATH=src python3 -m kserve_model_platform resource-health-status --output .local

advanced-device-sharing:
	PYTHONPATH=src python3 -m kserve_model_platform advanced-device-sharing --output .local

admin-access-diagnostics:
	PYTHONPATH=src python3 -m kserve_model_platform admin-access-diagnostics --output .local

inplace-resize-plan:
	PYTHONPATH=src python3 -m kserve_model_platform inplace-resize-plan --output .local

topology-plan:
	PYTHONPATH=src python3 -m kserve_model_platform topology-plan --output .local

kuberay-plan:
	PYTHONPATH=src python3 -m kserve_model_platform kuberay-plan --output .local

inference-gateway-plan:
	PYTHONPATH=src python3 -m kserve_model_platform inference-gateway-plan --output .local

semantic-telemetry-plan:
	PYTHONPATH=src python3 -m kserve_model_platform semantic-telemetry-plan --output .local

deadline-alerts-plan:
	PYTHONPATH=src python3 -m kserve_model_platform deadline-alerts-plan --output .local

cost-observability:
	PYTHONPATH=src python3 -m kserve_model_platform cost-observability --output .local

elastic-workload-plan:
	PYTHONPATH=src python3 -m kserve_model_platform elastic-workload-plan --output .local

indexed-job-resilience:
	PYTHONPATH=src python3 -m kserve_model_platform indexed-job-resilience --output .local

provisioning-admission:
	PYTHONPATH=src python3 -m kserve_model_platform provisioning-admission --output .local

multikueue-dispatch:
	PYTHONPATH=src python3 -m kserve_model_platform multikueue-dispatch --output .local

model-cache:
	PYTHONPATH=src python3 -m kserve_model_platform model-cache --output .local

dag-bundle-plan:
	PYTHONPATH=src python3 -m kserve_model_platform dag-bundle-plan --output .local

asset-partitioning-plan:
	PYTHONPATH=src python3 -m kserve_model_platform asset-partitioning-plan --output .local

airflow-stateful-orchestration:
	PYTHONPATH=src python3 -m kserve_model_platform airflow-stateful-orchestration --output .local

airflow-sdk-contract:
	python3 tools/validate_airflow33_dag.py airflow/dags/airflow33_stateful_serving_dag.py

multi-team-readiness:
	PYTHONPATH=src python3 -m kserve_model_platform multi-team-readiness --output .local

event-driven-assets:
	PYTHONPATH=src python3 -m kserve_model_platform event-driven-assets --output .local

pod-resource-envelopes:
	PYTHONPATH=src python3 -m kserve_model_platform pod-resource-envelopes --output .local

cohort-fair-sharing:
	PYTHONPATH=src python3 -m kserve_model_platform cohort-fair-sharing --output .local

flavor-fungibility:
	PYTHONPATH=src python3 -m kserve_model_platform flavor-fungibility --output .local

pending-workload-visibility:
	PYTHONPATH=src python3 -m kserve_model_platform pending-workload-visibility --output .local

tenancy-report:
	PYTHONPATH=src python3 -m kserve_model_platform tenancy-report --output .local

identity-report:
	PYTHONPATH=src python3 -m kserve_model_platform identity-report --output .local

performance-budget:
	PYTHONPATH=src python3 -m kserve_model_platform performance-budget --output .local

queue-simulation:
	PYTHONPATH=src python3 -m kserve_model_platform queue-simulation --output .local

workload-aware-scheduling:
	PYTHONPATH=src python3 -m kserve_model_platform workload-aware-scheduling --output .local

runtime-security:
	PYTHONPATH=src python3 -m kserve_model_platform runtime-security --output .local

control-plane-diagnostics:
	PYTHONPATH=src python3 -m kserve_model_platform control-plane-diagnostics --output .local

memory-qos:
	PYTHONPATH=src python3 -m kserve_model_platform memory-qos --output .local

hpa-scale-zero:
	PYTHONPATH=src python3 -m kserve_model_platform hpa-scale-zero --output .local

suspended-job-resources:
	PYTHONPATH=src python3 -m kserve_model_platform suspended-job-resources --output .local

constrained-impersonation:
	PYTHONPATH=src python3 -m kserve_model_platform constrained-impersonation --output .local

release-admission:
	PYTHONPATH=src python3 -m kserve_model_platform release-admission --output .local

ci-verify:
	PYTHONPATH=src python3 -m compileall -q src tests tools
	test -f Dockerfile
	test -f compose.yaml
	test -f requirements-serving.lock
	test -f src/kserve_model_platform/api.py
	test -f src/kserve_model_platform/runtime_state.py
	test -f src/kserve_model_platform/v2_protocol.py
	test -f kserve/custom-runtime-inferenceservice.yaml
	test -f docs/kserve-v2-serving-runtime.md
	test -f docs/screenshots/dashboard.png
	test -f .local/reports/kserve_serving_dashboard.html
	test -f .local/reports/index.html
	test -f .local/reports/governance_evidence_bundle.json
	test -f .local/reports/slo_error_budget.json
	test -f .local/reports/cloud_migration_plan.json
	test -f .local/reports/supply_chain_evidence.json
	test -f .local/reports/orchestration_scorecard.json
	test -f .local/reports/accelerator_capacity_plan.json
	test -f .local/reports/device_allocation_plan.json
	test -f .local/reports/resource_health_status_plan.json
	test -f .local/reports/advanced_device_sharing_plan.json
	test -f .local/reports/admin_access_diagnostics_plan.json
	test -f .local/reports/inplace_resize_plan.json
	test -f .local/reports/topology_placement_plan.json
	test -f .local/reports/kuberay_capacity_plan.json
	test -f .local/reports/inference_gateway_plan.json
	test -f .local/reports/semantic_telemetry_plan.json
	test -f .local/reports/deadline_alert_plan.json
	test -f .local/reports/cost_observability_report.json
	test -f .local/reports/elastic_workload_plan.json
	test -f .local/reports/indexed_job_resilience_plan.json
	test -f .local/reports/provisioning_admission_plan.json
	test -f .local/reports/multikueue_dispatch_plan.json
	test -f .local/reports/model_cache_plan.json
	test -f .local/reports/dag_bundle_versioning_plan.json
	test -f .local/reports/asset_partitioning_plan.json
	test -f .local/reports/airflow_stateful_orchestration_plan.json
	test -f .local/reports/multi_team_readiness_plan.json
	test -f .local/reports/event_driven_assets_plan.json
	test -f .local/reports/pod_resource_envelope_plan.json
	test -f .local/reports/cohort_fair_sharing_plan.json
	test -f .local/reports/flavor_fungibility_plan.json
	test -f .local/reports/pending_workload_visibility_plan.json
	test -f .local/reports/tenancy_fairness_report.json
	test -f .local/reports/identity_access_report.json
	test -f .local/reports/performance_budget.json
	test -f .local/reports/queue_simulation.json
	test -f .local/reports/workload_aware_scheduling_plan.json
	test -f .local/reports/runtime_security_plan.json
	test -f .local/reports/control_plane_diagnostics_plan.json
	test -f .local/reports/memory_qos_plan.json
	test -f .local/reports/hpa_scale_to_zero_plan.json
	test -f .local/reports/suspended_job_resources_plan.json
	test -f .local/reports/constrained_impersonation_plan.json
	test -f .local/reports/release_admission_decision.json
	test -f .local/supply-chain/subject.checksums.txt
	python3 -m json.tool .local/reports/governance_evidence_bundle.json >/dev/null
	python3 -m json.tool .local/reports/slo_error_budget.json >/dev/null
	python3 -m json.tool .local/reports/cloud_migration_plan.json >/dev/null
	python3 -m json.tool .local/reports/supply_chain_evidence.json >/dev/null
	python3 -m json.tool .local/reports/orchestration_scorecard.json >/dev/null
	python3 -m json.tool .local/reports/accelerator_capacity_plan.json >/dev/null
	python3 -m json.tool .local/reports/device_allocation_plan.json >/dev/null
	python3 -m json.tool .local/reports/resource_health_status_plan.json >/dev/null
	python3 -m json.tool .local/reports/advanced_device_sharing_plan.json >/dev/null
	python3 -m json.tool .local/reports/admin_access_diagnostics_plan.json >/dev/null
	python3 -m json.tool .local/reports/inplace_resize_plan.json >/dev/null
	python3 -m json.tool .local/reports/topology_placement_plan.json >/dev/null
	python3 -m json.tool .local/reports/kuberay_capacity_plan.json >/dev/null
	python3 -m json.tool .local/reports/inference_gateway_plan.json >/dev/null
	python3 -m json.tool .local/reports/semantic_telemetry_plan.json >/dev/null
	python3 -m json.tool .local/reports/deadline_alert_plan.json >/dev/null
	python3 -m json.tool .local/reports/cost_observability_report.json >/dev/null
	python3 -m json.tool .local/reports/elastic_workload_plan.json >/dev/null
	python3 -m json.tool .local/reports/indexed_job_resilience_plan.json >/dev/null
	python3 -m json.tool .local/reports/provisioning_admission_plan.json >/dev/null
	python3 -m json.tool .local/reports/multikueue_dispatch_plan.json >/dev/null
	python3 -m json.tool .local/reports/model_cache_plan.json >/dev/null
	python3 -m json.tool .local/reports/dag_bundle_versioning_plan.json >/dev/null
	python3 -m json.tool .local/reports/asset_partitioning_plan.json >/dev/null
	python3 -m json.tool .local/reports/airflow_stateful_orchestration_plan.json >/dev/null
	python3 -m json.tool .local/reports/multi_team_readiness_plan.json >/dev/null
	python3 -m json.tool .local/reports/event_driven_assets_plan.json >/dev/null
	python3 -m json.tool .local/reports/pod_resource_envelope_plan.json >/dev/null
	python3 -m json.tool .local/reports/cohort_fair_sharing_plan.json >/dev/null
	python3 -m json.tool .local/reports/flavor_fungibility_plan.json >/dev/null
	python3 -m json.tool .local/reports/pending_workload_visibility_plan.json >/dev/null
	python3 -m json.tool .local/reports/tenancy_fairness_report.json >/dev/null
	python3 -m json.tool .local/reports/identity_access_report.json >/dev/null
	python3 -m json.tool .local/reports/performance_budget.json >/dev/null
	python3 -m json.tool .local/reports/queue_simulation.json >/dev/null
	python3 -m json.tool .local/reports/workload_aware_scheduling_plan.json >/dev/null
	python3 -m json.tool .local/reports/runtime_security_plan.json >/dev/null
	python3 -m json.tool .local/reports/control_plane_diagnostics_plan.json >/dev/null
	python3 -m json.tool .local/reports/memory_qos_plan.json >/dev/null
	python3 -m json.tool .local/reports/hpa_scale_to_zero_plan.json >/dev/null
	python3 -m json.tool .local/reports/suspended_job_resources_plan.json >/dev/null
	python3 -m json.tool .local/reports/constrained_impersonation_plan.json >/dev/null
	python3 -m json.tool .local/reports/release_admission_decision.json >/dev/null

promote:
	PYTHONPATH=src python3 -m kserve_model_platform promote --output .local

rollback:
	PYTHONPATH=src python3 -m kserve_model_platform rollback --output .local

health:
	PYTHONPATH=src python3 -m kserve_model_platform health --output .local

api-run:
	LOG_LEVEL=INFO SERVING_STATE_ROOT=.local PYTHONPATH=src $(PYTHON) -m uvicorn kserve_model_platform.api:app --host 0.0.0.0 --port 8080 --workers 1 --no-access-log

api-smoke:
	$(PYTHON) tools/smoke_serving_api.py --base-url "$${SERVING_BASE_URL:-http://127.0.0.1:8080}"

demo-voice:
	$(PYTHON) tools/generate_demo_voice.py

demo-video:
	bash tools/build_demo_video.sh

test-api:
	PYTHONPATH=src $(PYTHON) -m unittest tests.test_serving_api -v

lint-api:
	$(PYTHON) -m ruff check --ignore E501,I001 $(SERVING_FILES)

verify-serving-lock:
	$(PYTHON) tools/verify_locked_environment.py requirements-serving.lock

package:
	rm -rf build dist
	$(PYTHON) -m build --no-isolation --wheel

package-smoke: package
	$(PYTHON) tools/smoke_wheel.py

kserve-schema-contract:
	$(PYTHON) tools/validate_kserve_manifest.py

compose-config:
	docker compose config --quiet

compose-up:
	docker compose up --build --wait

compose-down:
	docker compose down --volumes --remove-orphans

compose-smoke:
	@set -eu; \
		mkdir -p .local/reports; \
		cleanup() { docker compose logs --no-color > .local/reports/compose-smoke.log 2>&1 || true; docker compose down --volumes --remove-orphans >/dev/null 2>&1 || true; }; \
		trap cleanup EXIT; \
		docker compose up --build --wait; \
		$(MAKE) api-smoke

minikube-up:
	@echo "Start Minikube and apply the serving stack:"
	@echo "  minikube start --cpus=4 --memory=8192"
	@echo "  kubectl create namespace mlops-serving --dry-run=client -o yaml | kubectl apply -f -"
	@echo "  kubectl apply -f kserve/production-hardening.yaml"
	@echo "  kubectl apply -f kserve/custom-runtime-inferenceservice.yaml"
	@echo "  kubectl apply -f kserve/inferenceservice-canary.yaml"
	@echo "  kubectl apply -f kserve/local-model-cache.yaml"
	@echo "  kubectl apply -f kubernetes/serving-release-workloads.yaml"
	@echo "  kubectl apply -f kubernetes/resource-optimization.yaml"
	@echo "  kubectl apply -f kubernetes/network-security.yaml"
	@echo "  kubectl apply -f kubernetes/chaos-experiments.yaml"
	@echo "  kubectl apply -f kubernetes/disaster-recovery.yaml"
	@echo "  kubectl apply -f kubernetes/governance-evidence.yaml"
	@echo "  kubectl apply -f kubernetes/slo-alerts.yaml"
	@echo "  kubectl apply -f kubernetes/cloud-nodepools.yaml"
	@echo "  kubectl apply -f kubernetes/supply-chain-policy.yaml"
	@echo "  kubectl apply -f kubernetes/accelerator-scheduling.yaml"
	@echo "  kubectl apply -f kubernetes/dynamic-resource-allocation.yaml"
	@echo "  kubectl apply -f kubernetes/dra-resource-health-status.yaml"
	@echo "  kubectl apply -f kubernetes/dra-advanced-device-sharing.yaml"
	@echo "  kubectl apply -f kubernetes/dra-admin-access-diagnostics.yaml"
	@echo "  kubectl apply -f kubernetes/inplace-pod-resize.yaml"
	@echo "  kubectl apply -f kubernetes/topology-aware-scheduling.yaml"
	@echo "  kubectl apply -f kubernetes/kuberay-kueue-workloads.yaml"
	@echo "  kubectl apply -f kubernetes/kueue-elastic-workloads.yaml"
	@echo "  kubectl apply -f kubernetes/indexed-job-resilience.yaml"
	@echo "  kubectl apply -f kubernetes/provisioning-admission-checks.yaml"
	@echo "  kubectl apply -f kubernetes/multikueue-dispatch.yaml"
	@echo "  kubectl apply -f kubernetes/pod-resource-envelopes.yaml"
	@echo "  kubectl apply -f kubernetes/kueue-cohort-fair-sharing.yaml"
	@echo "  kubectl apply -f kubernetes/kueue-flavor-fungibility.yaml"
	@echo "  kubectl apply -f kubernetes/kueue-pending-workload-visibility.yaml"
	@echo "  kubectl apply -f kubernetes/inference-gateway-routing.yaml"
	@echo "  kubectl apply -f kubernetes/multitenancy-fairness.yaml"
	@echo "  kubectl apply -f kubernetes/workload-identity.yaml"
	@echo "  kubectl apply -f kubernetes/performance-budget-policy.yaml"
	@echo "  kubectl apply -f kubernetes/queue-simulation-policy.yaml"
	@echo "  kubectl apply -f kubernetes/control-plane-diagnostics.yaml"
	@echo "  kubectl apply -f kubernetes/memory-qos.yaml"
	@echo "  kubectl apply -f kubernetes/hpa-scale-to-zero.yaml"
	@echo "  kubectl apply -f kubernetes/suspended-job-resources.yaml"
	@echo "  kubectl apply -f kubernetes/constrained-impersonation.yaml"
	@echo "  kubectl apply -f kubernetes/release-admission-policy.yaml"
	@echo "  kubectl apply -f kubernetes/opencost-finops.yaml"
	@echo "  kubectl apply -f gitops/gitops-promotion.yaml"
	@echo "  kubectl apply -f monitoring/prometheus/prometheus.yml"

kubernetes-plan:
	@find kserve kubernetes monitoring gitops -name '*.yaml' -maxdepth 3 -print

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

clean:
	rm -rf .local
