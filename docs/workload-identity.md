# Workload Identity and Secretless Access

This serving platform models production access without static object-store or registry keys in model-serving pods. The gateway, predictor, and canary analysis workloads each get a dedicated Kubernetes `ServiceAccount`, namespace-scoped RBAC, projected one-hour tokens, and a federated cloud role.

## Controls

- `kubernetes/workload-identity.yaml` disables default service account token automounting and documents projected token expectations.
- `SecretStore` and `ExternalSecret` examples synchronize TLS, registry, and webhook material with a 30 minute refresh window.
- Airflow rollout tasks pin the `canary-analysis-runner` service account rather than inheriting broad scheduler permissions.
- SPIFFE IDs document identities for the router, predictor, and rollout-analysis workloads.
- `.local/reports/identity_access_report.json` proves that token TTL, ExternalSecret refresh, RBAC scope, SPIFFE IDs, and static-key avoidance pass.

## Production Notes

Use IRSA, Azure Workload Identity, or GKE Workload Identity Federation for model artifact reads and prediction-log writes. Keep serving credentials separated from rollout-analysis credentials so a load test or canary job cannot mutate the champion route without the release controller identity.

References: Kubernetes service account token projection, External Secrets Operator, SPIFFE/SPIRE, and Airflow KubernetesPodOperator service-account configuration.
