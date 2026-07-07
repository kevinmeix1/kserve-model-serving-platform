from __future__ import annotations

from pathlib import Path

from .io import write_json


def build_cloud_migration_plan(root: str | Path) -> dict:
    root = Path(root)
    plan = {
        "platform": "kserve-model-serving-platform",
        "primary_target": "AWS EKS Auto Mode",
        "managed_service_mapping": {
            "serving": "KServe Standard mode on EKS with Gateway API",
            "traffic": "Gateway API or AWS Load Balancer Controller for weighted routes",
            "model_artifacts": "S3 buckets with versioning and KMS encryption",
            "registry": "MLflow Model Registry backed by RDS PostgreSQL",
            "monitoring": "Amazon Managed Service for Prometheus and Grafana",
            "logs": "CloudWatch Logs, Firehose, or S3 partitioned inference logs",
        },
        "migration_phases": [
            {"phase": "foundation", "tasks": ["provision EKS", "enable IRSA", "create artifact buckets", "install Gateway API"]},
            {"phase": "serving", "tasks": ["install KServe", "apply canary InferenceService", "configure autoscaling", "wire prediction logs"]},
            {"phase": "release", "tasks": ["run canary analysis", "verify rollback patch", "publish governance and SLO evidence"]},
        ],
        "portability_controls": [
            "keep model storage URIs external to manifests",
            "separate cloud-specific IAM and storage from KServe resources",
            "use registry aliases instead of hard-coded production versions",
            "treat shadow scoring and canary gates as provider-neutral release policy",
        ],
        "cost_controls": [
            "use on-demand nodes for low-latency champion serving",
            "use separate spot-friendly pools for batch scoring",
            "set min replicas only where latency SLO requires warm capacity",
            "retain prediction logs with lifecycle policies by compliance tier",
        ],
    }
    write_json(root / "reports" / "cloud_migration_plan.json", plan)
    return plan
