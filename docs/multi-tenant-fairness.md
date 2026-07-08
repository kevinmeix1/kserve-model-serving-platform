# Multi-Tenant Fairness

The demo writes `reports/tenancy_fairness_report.json`, which models a shared serving platform with online serving, canary analysis, and load-test tenants. The point is to show that model serving capacity is protected by tenancy controls, not just autoscaling.

## Controls

- `ResourceQuota` and `LimitRange` isolate online serving from analysis and load testing.
- Kueue `Cohort` and `ClusterQueue` resources let canary analysis borrow spare capacity without starving champion rollback.
- Airflow pools reserve slots for serving health and rollback checks.
- Cost-center labels allow serving, QA, and platform workloads to be charged back separately.
- Default-deny `NetworkPolicy` blocks direct predictor-to-predictor tenant traffic.

## References

- Kubernetes multi-tenancy: https://kubernetes.io/docs/concepts/security/multi-tenancy/
- Kubernetes ResourceQuota: https://kubernetes.io/docs/concepts/policy/resource-quotas/
- Kueue Cohorts: https://kueue.sigs.k8s.io/docs/concepts/cohort/
- Airflow Pools: https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html
