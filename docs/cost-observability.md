# Cost Observability and FinOps

`make cost-observability` writes `.local/reports/cost_observability_report.json` and validates the serving platform cost-allocation contract.

## What It Shows

- OpenCost exporter metrics scraped by Prometheus every minute.
- Cost allocation by `InferenceService`, revision, `HTTPRoute`, model, cost center, and traffic class.
- Separate budgets for champion serving, challenger canary traffic, shadow analysis, and GPU explainers.
- Cost-per-1000-predictions as a unit-economics guardrail beside p95 and p99 latency.
- Prometheus alerts for high serving unit cost, shadow budget overrun, idle GPU serving spend, and missing allocation labels.
- The split between OpenCost allocation evidence and Kubernetes `ResourceQuota` or `LimitRange` admission controls.

## Production Notes

Serving costs drift differently from training costs. A canary can pass technically while shadow scoring silently doubles compute, a GPU explainer can stay enabled after an incident, or a Gateway route can hide unowned traffic. The release gate should review cost per prediction, traffic-class budgets, and accelerator cost beside latency, error rate, and rollback capacity.

Labels are the contract. Every predictor, explainer, router, and canary-analysis workload should carry model, cost-center, and traffic-class labels so Prometheus, OpenCost, GitOps, and incident tooling agree on who owns the spend.

## Current Research Basis

- OpenCost can run as a Prometheus metric exporter and expose allocation metrics without requiring the full UI.
- OpenCost requires Prometheus for metric scraping and storage.
- OpenCost generated metrics include CPU, RAM, GPU, node, PVC, and load balancer cost signals.
- Kubernetes `ResourceQuota` constrains namespace consumption, and `LimitRange` can supply default resource requests or limits that make quota enforcement workable.
