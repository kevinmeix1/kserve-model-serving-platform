# GitOps Promotion

This project models KServe deployment through Argo CD and Argo Rollouts. The generated report captures stage policy, gates, sync waves, and rollback commands; the manifest shows how serving changes move through pre-sync validation and canary analysis.

Run:

```bash
make gitops-plan
```

The report is written to `.local/reports/gitops_plan.json`.

## Design

- Keep predictor images pinned in environment manifests.
- Apply security, network, capacity, and route policy before serving runtime changes.
- Run payload contract and topology checks before sync.
- Use canary analysis for latency and error rate before full promotion.
- Keep production sync manual even when lower environments self-heal.

## References

Argo CD sync hooks and waves order release resources and checks. Automated sync can self-heal drift in lower environments. Argo Rollouts supports canary steps and AnalysisTemplates for metric-based promotion or abort decisions.
