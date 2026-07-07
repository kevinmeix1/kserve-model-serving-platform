# Orchestration Scorecard

`make orchestration-scorecard` scans the repository and writes `.local/reports/orchestration_scorecard.json`. The scorecard is intentionally evidence-based: it checks the actual Airflow DAGs, Kubernetes manifests, GitOps files, CI workflow, and docs instead of relying on README claims.

## Controls Scored

- Large production-shaped Airflow DAGs
- Dynamic task mapping with mapped fanout
- TaskGroups for separable operational phases
- Dataset outlets for asset-aware lineage
- KubernetesPodOperator execution
- Branching and trigger rules for rollback and recovery
- Airflow pools and priority weights
- Kueue admission control
- KEDA event-driven scaling
- HPA elasticity
- OpenTelemetry collection
- GitOps promotion evidence
- GitHub/Sigstore/SLSA supply-chain provenance

## Why This Matters

Senior MLOps projects should be explainable under review. A scorecard gives interviewers a quick answer to "where is the complexity?" while keeping the proof tied to files they can inspect.

## Research Basis

- Airflow dynamic task mapping: https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/dynamic-task-mapping.html
- Airflow deferrable tasks and triggerer capacity: https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/deferring.html
- OpenLineage Airflow provider: https://airflow.apache.org/docs/apache-airflow-providers-openlineage/stable/guides/structure.html
- KServe production administrator guide: https://kserve.github.io/website/docs/admin-guide/overview
- Kubernetes Gateway API Inference Extension: https://gateway-api-inference-extension.sigs.k8s.io/
