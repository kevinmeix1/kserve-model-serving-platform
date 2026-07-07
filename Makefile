.PHONY: demo deploy predict simulate monitor promote rollback health plan-rollout policy-audit trace-report chaos-drill optimize-resources network-security gitops-plan dr-plan minikube-up kubernetes-plan test clean

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
	@echo "  kubectl apply -f gitops/gitops-promotion.yaml"
	@echo "  kubectl apply -f monitoring/prometheus/prometheus.yml"

kubernetes-plan:
	@find kserve kubernetes monitoring gitops -name '*.yaml' -maxdepth 3 -print

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

clean:
	rm -rf .local
