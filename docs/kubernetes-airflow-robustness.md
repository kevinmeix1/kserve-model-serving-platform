# Kubernetes And Airflow Robustness Layer

This repo now models a full serving release control plane.

## Airflow Features

- Progressive rollout DAG with 1, 5, 10, 25, and 50 percent steps.
- Dynamic task mapping over canary percentages.
- TaskGroups for preflight, rollout, and observability gates.
- Branching between promotion and rollback.
- KubernetesPodOperator tasks for release execution.
- Airflow KubernetesExecutor pod template that waits for KServe controller readiness.

## Kubernetes Features

- ResourceQuota and LimitRange for serving namespace governance.
- PriorityClass for canary and rollback operations.
- Gateway API HTTPRoute for inference routing.
- Canary analysis Job.
- HPA example for raw deployment mode.
- RBAC Role/RoleBinding for KServe patch/read permissions.
- Dedicated service account, NetworkPolicy, PodDisruptionBudget, and pod security labels.

## Why It Matters

Serving is an operational release system. The repo now demonstrates traffic policy, runtime isolation, rollout gates, autoscaling, and rollback primitives.
