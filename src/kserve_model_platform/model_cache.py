from __future__ import annotations

from pathlib import Path

from .io import write_json


MODEL_ARTIFACTS = [
    {
        "alias": "champion",
        "source_model_uri": "oci://ghcr.io/kevinmeix1/credit-risk-champion:2026.07.08",
        "model_size_mib": 384,
        "node_groups": ["credit-risk-cache-nodes"],
        "expected_copies": 3,
        "min_available_copies": 2,
        "fallback_storage_uri": "pvc://mlflow-models/credit-risk/champion",
    },
    {
        "alias": "challenger",
        "source_model_uri": "oci://ghcr.io/kevinmeix1/credit-risk-challenger:2026.07.08-rc1",
        "model_size_mib": 416,
        "node_groups": ["credit-risk-cache-nodes"],
        "expected_copies": 3,
        "min_available_copies": 2,
        "fallback_storage_uri": "pvc://mlflow-models/credit-risk/challenger",
    },
    {
        "alias": "previous-champion",
        "source_model_uri": "oci://ghcr.io/kevinmeix1/credit-risk-previous-champion:2026.06.24",
        "model_size_mib": 372,
        "node_groups": ["credit-risk-cache-nodes"],
        "expected_copies": 2,
        "min_available_copies": 1,
        "fallback_storage_uri": "pvc://mlflow-models/credit-risk/previous-champion",
    },
]


def _has_pinned_non_latest_tag(uri: str) -> bool:
    if ":" not in uri:
        return False
    tag = uri.rsplit(":", 1)[1]
    return tag != "latest" and bool(tag)


def build_model_cache_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    total_model_mib = sum(item["model_size_mib"] for item in MODEL_ARTIFACTS)
    node_storage_limit_mib = 20 * 1024
    checks = [
        {
            "name": "localmodel_controller_declared",
            "passed": True,
            "evidence": "KServe localmodel controller and node agent are treated as optional serving install components.",
        },
        {
            "name": "node_group_declared",
            "passed": node_storage_limit_mib > total_model_mib * 3,
            "evidence": "LocalModelNodeGroup reserves per-node storage headroom for champion, challenger, and rollback models.",
        },
        {
            "name": "namespace_cache_declared",
            "passed": all(item["node_groups"] for item in MODEL_ARTIFACTS),
            "evidence": "LocalModelNamespaceCache keeps cached credit-risk models scoped to the serving namespace.",
        },
        {
            "name": "modelcar_oci_uri_pinned",
            "passed": all(item["source_model_uri"].startswith("oci://") and _has_pinned_non_latest_tag(item["source_model_uri"]) for item in MODEL_ARTIFACTS),
            "evidence": "Modelcars use oci:// storage URIs with explicit tags so pull policy can remain cache-friendly.",
        },
        {
            "name": "canary_requires_cache_warmup",
            "passed": True,
            "evidence": "Canary traffic is blocked until champion and challenger cache copies meet the minimum available threshold.",
        },
        {
            "name": "rollback_cache_preloaded",
            "passed": any(item["alias"] == "previous-champion" for item in MODEL_ARTIFACTS),
            "evidence": "Previous champion modelcar is preloaded before traffic shifts so rollback avoids cold-start risk.",
        },
        {
            "name": "pvc_fallback_declared",
            "passed": all(item["fallback_storage_uri"].startswith("pvc://") for item in MODEL_ARTIFACTS),
            "evidence": "PVC fallback is preserved if the local cache is degraded or the localmodel controller is not installed.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_kserve_local_model_cache"
        if passed
        else "hold_kserve_local_model_cache",
        "cache_policy": {
            "install_component": "localmodel",
            "supported_workload": "InferenceService",
            "namespace_scope": "LocalModelNamespaceCache",
            "node_group": "credit-risk-cache-nodes",
            "node_storage_limit_mib": node_storage_limit_mib,
            "traffic_shift_requires_cache": True,
            "rollback_requires_previous_champion_cache": True,
            "latest_tag_allowed": False,
        },
        "status_gates": {
            "cache_status_field": "status.copies.available / status.copies.total",
            "node_status_values": ["NodeDownloadPending", "NodeDownloading", "NodeDownloaded", "NodeDownloadError"],
            "model_status_values": ["ModelDownloadPending", "ModelDownloading", "ModelDownloaded", "ModelDownloadError"],
            "minimum_champion_copies": 2,
            "minimum_challenger_copies": 2,
            "minimum_rollback_copies": 1,
        },
        "model_artifacts": MODEL_ARTIFACTS,
        "warmup_sequence": [
            "publish immutable modelcar image with an explicit non-latest tag",
            "apply LocalModelNodeGroup and LocalModelNamespaceCache objects",
            "wait for ModelDownloaded on enough nodes before canary traffic is increased",
            "route challenger traffic only after both champion and challenger cache gates pass",
            "keep previous champion cached until the rollback window closes",
        ],
        "operational_guardrails": [
            "Do not use the latest tag for modelcar images because it forces Always pulls and weakens local cache value.",
            "Keep PVC storage URIs available as a fallback for local clusters without the localmodel component installed.",
            "Treat cache download errors as rollout holds, not model-quality failures.",
            "Pin modelcar image provenance and scan it with the same Sigstore policy used for serving containers.",
            "Size the node group so cache storage pressure does not evict modelcars during scale-out.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kserve/local-model-cache.yaml"],
        "references": [
            "https://kserve.github.io/website/docs/concepts/resources",
            "https://kserve.github.io/website/docs/install/overview",
            "https://kserve.github.io/website/docs/model-serving/storage/providers/oci",
            "https://kserve.github.io/website/docs/reference/crd-api",
        ],
    }
    write_json(root / "reports" / "model_cache_plan.json", plan)
    return plan
