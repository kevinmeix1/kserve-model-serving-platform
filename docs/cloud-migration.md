# Cloud Migration Plan

Generate the machine-readable plan with:

```bash
make cloud-plan
```

## AWS Target

- Run KServe Standard mode on EKS with Gateway API.
- Store model artifacts in versioned, encrypted S3 buckets.
- Use MLflow Model Registry backed by RDS PostgreSQL.
- Use EKS Auto Mode or Karpenter-style NodePools for low-latency serving and batch scoring pools.
- Send metrics to Amazon Managed Service for Prometheus and Grafana.
- Send prediction logs to CloudWatch, Firehose, or partitioned S3 logs.

## Portability Notes

- Keep model storage URIs outside application code.
- Keep registry aliases as the production pointer.
- Keep canary, shadow, rollback, SLO, and governance evidence provider-neutral.
- Put cloud-specific IAM and storage in `infra/terraform/aws`.
