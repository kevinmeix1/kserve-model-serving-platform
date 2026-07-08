# Release Admission Control

This project writes `reports/release_admission_decision.json`, a fail-closed canary admission record for KServe model serving. It combines canary gates, the rollout plan, SLO burn, performance budgets, queue capacity, governance approval, and supply-chain provenance.

The controller has explicit serving actions: `advance_canary`, `promote_challenger`, `hold_canary`, `freeze_canary`, `rollback_challenger`, and `throttle_serving_queue`. It never advances traffic when any required gate is missing or failed.

## Production Shape

- Airflow owns the progressive rollout DAG and pauses traffic changes unless the generated decision admits the canary.
- Kubernetes `ValidatingAdmissionPolicy` requires release-decision and evidence-sha annotations on KServe `InferenceService` updates.
- Argo Rollouts analysis checks canary error rate and shadow-score delta in Prometheus.
- Kueue and Airflow pools keep emergency champion rollback capacity ahead of batch scoring and load tests.

## Why This Is Senior-Level

The project now models a production control point rather than a loose dashboard. The same evidence used in the README demo is consumed by rollout automation, admission policy, and alerts. That is the useful interview story: model serving is a release system with traffic, evidence, rollback, and fail-closed policy.

## Current References

- Kubernetes `ValidatingAdmissionPolicy`: https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/
- Argo Rollouts analysis: https://argo-rollouts.readthedocs.io/en/stable/features/analysis/
- KServe canary rollout strategy: https://kserve.github.io/website/docs/model-serving/predictive-inference/rollout-strategies/canary
- Airflow assets: https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html
