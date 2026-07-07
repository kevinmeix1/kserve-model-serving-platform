from __future__ import annotations

from pathlib import Path

from .io import write_json


def build_disaster_recovery_plan(root: str | Path) -> dict:
    root = Path(root)
    plan = {
        "platform": "kserve-model-serving-platform",
        "rpo_minutes": 15,
        "rto_minutes": 45,
        "backup_policy": {
            "cluster_objects": "Velero serving namespace backup every 15 minutes",
            "persistent_volumes": "CSI VolumeSnapshot with Retain deletion policy",
            "registry_aliases": "versioned registry metadata backup before promotion",
            "prediction_logs": "append-only log export for replay and audit",
        },
        "restore_sequence": [
            {"order": 1, "asset": "namespace and serving CRDs", "validation": "kubectl get inferenceservice"},
            {"order": 2, "asset": "network and gateway routes", "validation": "HTTPRoute accepted"},
            {"order": 3, "asset": "registry aliases and model artifacts", "validation": "champion and challenger aliases resolve"},
            {"order": 4, "asset": "idempotency cache", "validation": "replayed request IDs do not duplicate logs"},
            {"order": 5, "asset": "KServe runtime", "validation": "health endpoint reports Ready"},
        ],
        "drills": [
            "restore into mlops-serving-restore namespace monthly",
            "replay sampled prediction requests and compare ids",
            "abort an in-progress canary and verify champion traffic is restored",
        ],
    }
    write_json(root / "reports" / "disaster_recovery_plan.json", plan)
    return plan
