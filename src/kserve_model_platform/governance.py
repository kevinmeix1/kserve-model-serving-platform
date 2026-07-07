from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .io import read_json, write_json


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_optional_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return read_json(path)


def _sha256(path: Path) -> dict:
    if not path.exists() or not path.is_file():
        return {"path": str(path), "exists": False, "sha256": None}
    return {"path": str(path), "exists": True, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def build_governance_bundle(root: str | Path) -> dict:
    root = Path(root)
    aliases = _read_optional_json(root / "registry" / "credit-risk" / "aliases.json", {})
    deployment = _read_optional_json(root / "deployments" / "kserve_state.json", {})
    observability = _read_optional_json(root / "reports" / "serving_observability.json", {})
    canary = _read_optional_json(root / "reports" / "canary_decision.json", {"passed": False, "checks": []})
    champion_version = aliases.get("champion", "unknown")
    challenger_version = aliases.get("challenger")

    artifact_paths = [
        root / "registry" / "credit-risk" / "aliases.json",
        root / "registry" / "credit-risk" / "versions" / str(champion_version) / "model.json",
        root / "deployments" / "kserve_state.json",
        root / "logs" / "predictions.jsonl",
        root / "reports" / "serving_observability.json",
        root / "reports" / "canary_decision.json",
    ]
    reproducibility_manifest = {
        "generated_at": _utc_iso(),
        "platform": "kserve-model-serving-platform",
        "champion_version": champion_version,
        "challenger_version": challenger_version,
        "artifact_hashes": [_sha256(path) for path in artifact_paths],
        "environment": {
            "serving_runtime": deployment.get("runtime", "kserve"),
            "protocol": deployment.get("protocol", "v2"),
            "registry": "MLflow-style aliases for champion, challenger, and previous champion",
            "traffic_policy": deployment.get("traffic", {}),
        },
    }

    model_card = {
        "name": "credit-risk",
        "champion_version": champion_version,
        "challenger_version": challenger_version,
        "intended_use": "Return a risk score and risk band for validated credit-risk requests.",
        "out_of_scope_use": "Do not bypass manual review or regulated decision controls with this demo model.",
        "signature": {
            "inputs": ["product", "income", "debt_ratio", "delinquencies", "utilization", "employment_years"],
            "outputs": ["risk_score", "risk_band"],
        },
        "canary_decision": canary.get("recommended_action", "hold_rollout"),
        "latency_ms": observability.get("latency_ms", {}),
        "limitations": [
            "Synthetic request traffic is used for local repeatability.",
            "Canary gates are operational gates, not a complete compliance review.",
            "Shadow deltas must be interpreted with production traffic mix context.",
        ],
    }

    data_card = {
        "dataset": "synthetic_credit_risk_requests",
        "owner": "ml-serving-platform",
        "source": "deterministic request generator in src/kserve_model_platform/models.py",
        "schema_contract": "contracts/prediction_request_contract.yml",
        "request_count": observability.get("request_count"),
        "error_rate": observability.get("error_rate"),
        "sensitive_data": "Synthetic payloads only; production mapping should tokenize customer identifiers.",
        "retention": "Prediction logs are append-only locally; production should use partitioned immutable storage with access controls.",
    }

    risk_register = [
        {
            "risk": "unsafe challenger promoted",
            "impact": "higher latency, errors, or score divergence reaches all traffic",
            "control": "canary gates for p95 latency, error rate, shadow delta, and live challenger traffic",
            "evidence": "reports/canary_decision.json",
            "status": "controlled" if canary.get("passed") else "hold",
        },
        {
            "risk": "request contract drift",
            "impact": "model receives malformed or semantically invalid features",
            "control": "serving request contract validation and rejected request logging",
            "evidence": "contracts/prediction_request_contract.yml",
            "status": "controlled",
        },
        {
            "risk": "duplicate prediction side effects",
            "impact": "retries create duplicate logs, alerts, or customer actions",
            "control": "idempotent request handling by request_id",
            "evidence": "logs/predictions.jsonl",
            "status": "controlled",
        },
        {
            "risk": "rollback path is untested",
            "impact": "operators cannot restore the previous champion during an incident",
            "control": "previous_champion alias and rollback command",
            "evidence": "registry/credit-risk/aliases.json",
            "status": "controlled",
        },
    ]

    approval_record = {
        "approval_id": f"credit-risk-{champion_version}",
        "decision": "approved_for_promotion" if canary.get("passed") else "hold_rollout",
        "generated_at": _utc_iso(),
        "approvers": ["serving-owner", "ml-release-manager"],
        "required_evidence": [
            "canary gates passed",
            "registry aliases captured",
            "serving observability report captured",
            "request contract available",
            "reproducibility hashes captured",
        ],
        "gate_summary": canary,
    }

    bundle = {
        "platform": "kserve-model-serving-platform",
        "framework_alignment": {
            "nist_ai_rmf": ["Govern", "Map", "Measure", "Manage"],
            "mlflow_registry": "use explicit aliases for champion, challenger, and previous champion",
            "model_transparency": "model card plus serving-data card and risk register",
        },
        "release": {
            "model_name": "credit-risk",
            "champion_version": champion_version,
            "challenger_version": challenger_version,
            "decision": approval_record["decision"],
        },
        "evidence_files": {
            "model_card": "governance/model_card.json",
            "data_card": "governance/data_card.json",
            "risk_register": "governance/risk_register.json",
            "approval_record": "governance/approval_record.json",
            "reproducibility_manifest": "governance/reproducibility_manifest.json",
        },
    }

    write_json(root / "governance" / "model_card.json", model_card)
    write_json(root / "governance" / "data_card.json", data_card)
    write_json(root / "governance" / "risk_register.json", risk_register)
    write_json(root / "governance" / "approval_record.json", approval_record)
    write_json(root / "governance" / "reproducibility_manifest.json", reproducibility_manifest)
    write_json(root / "reports" / "governance_evidence_bundle.json", bundle)
    return bundle
