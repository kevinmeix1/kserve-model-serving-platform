.PHONY: demo deploy predict simulate monitor promote rollback health plan-rollout policy-audit trace-report chaos-drill optimize-resources network-security gitops-plan dr-plan governance-bundle slo-report cloud-plan supply-chain orchestration-scorecard accelerator-plan device-plan tenancy-report identity-report performance-budget queue-simulation release-admission ci-verify minikube-up kubernetes-plan test clean

demo:
	PYTHONPATH=src python3 -m kserve_model_platform demo --output .local

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

tenancy-report:
	PYTHONPATH=src python3 -m kserve_model_platform tenancy-report --output .local

identity-report:
	PYTHONPATH=src python3 -m kserve_model_platform identity-report --output .local

performance-budget:
	PYTHONPATH=src python3 -m kserve_model_platform performance-budget --output .local

queue-simulation:
	PYTHONPATH=src python3 -m kserve_model_platform queue-simulation --output .local

release-admission:
	PYTHONPATH=src python3 -m kserve_model_platform release-admission --output .local

ci-verify:
	PYTHONPATH=src python3 -m compileall -q src tests
	test -f .local/reports/kserve_serving_dashboard.html
	test -f .local/reports/index.html
	test -f .local/reports/governance_evidence_bundle.json
	test -f .local/reports/slo_error_budget.json
	test -f .local/reports/cloud_migration_plan.json
	test -f .local/reports/supply_chain_evidence.json
	test -f .local/reports/orchestration_scorecard.json
	test -f .local/reports/accelerator_capacity_plan.json
	test -f .local/reports/device_allocation_plan.json
	test -f .local/reports/tenancy_fairness_report.json
	test -f .local/reports/identity_access_report.json
	test -f .local/reports/performance_budget.json
	test -f .local/reports/queue_simulation.json
	test -f .local/reports/release_admission_decision.json
	test -f .local/supply-chain/subject.checksums.txt
	python3 -m json.tool .local/reports/governance_evidence_bundle.json >/dev/null
	python3 -m json.tool .local/reports/slo_error_budget.json >/dev/null
	python3 -m json.tool .local/reports/cloud_migration_plan.json >/dev/null
	python3 -m json.tool .local/reports/supply_chain_evidence.json >/dev/null
	python3 -m json.tool .local/reports/orchestration_scorecard.json >/dev/null
	python3 -m json.tool .local/reports/accelerator_capacity_plan.json >/dev/null
	python3 -m json.tool .local/reports/device_allocation_plan.json >/dev/null
	python3 -m json.tool .local/reports/tenancy_fairness_report.json >/dev/null
	python3 -m json.tool .local/reports/identity_access_report.json >/dev/null
	python3 -m json.tool .local/reports/performance_budget.json >/dev/null
	python3 -m json.tool .local/reports/queue_simulation.json >/dev/null
	python3 -m json.tool .local/reports/release_admission_decision.json >/dev/null

promote:
	PYTHONPATH=src python3 -m kserve_model_platform promote --output .local

rollback:
	PYTHONPATH=src python3 -m kserve_model_platform rollback --output .local

health:
	PYTHONPATH=src python3 -m kserve_model_platform health --output .local

minikube-up:
	@echo "Start Minikube and apply the serving stack:"
	@echo "  minikube start --cpus=4 --memory=8192"
	@echo "  kubectl create namespace mlops-serving --dry-run=client -o yaml | kubectl apply -f -"
	@echo "  kubectl apply -f kserve/production-hardening.yaml"
	@echo "  kubectl apply -f kserve/inferenceservice-canary.yaml"
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
	@echo "  kubectl apply -f kubernetes/multitenancy-fairness.yaml"
	@echo "  kubectl apply -f kubernetes/workload-identity.yaml"
	@echo "  kubectl apply -f kubernetes/performance-budget-policy.yaml"
	@echo "  kubectl apply -f kubernetes/queue-simulation-policy.yaml"
	@echo "  kubectl apply -f kubernetes/release-admission-policy.yaml"
	@echo "  kubectl apply -f gitops/gitops-promotion.yaml"
	@echo "  kubectl apply -f monitoring/prometheus/prometheus.yml"

kubernetes-plan:
	@find kserve kubernetes monitoring gitops -name '*.yaml' -maxdepth 3 -print

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

clean:
	rm -rf .local
