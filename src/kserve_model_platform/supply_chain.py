from __future__ import annotations

import hashlib
from pathlib import Path

from .io import write_json


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_inventory(root: Path) -> list[dict]:
    reports_dir = root / "reports"
    output_name = "supply_chain_evidence.json"
    if not reports_dir.exists():
        return []
    artifacts = []
    for path in sorted(reports_dir.glob("*")):
        if not path.is_file() or path.name == output_name:
            continue
        artifacts.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return artifacts


def build_supply_chain_evidence(
    root: str | Path,
    *,
    project: str,
    artifact_name: str,
    workflow: str,
    namespace: str,
) -> dict:
    root = Path(root)
    artifacts = _artifact_inventory(root)
    checksums_path = root / "supply-chain" / "subject.checksums.txt"
    checksums_path.parent.mkdir(parents=True, exist_ok=True)
    checksums_path.write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in artifacts),
        encoding="utf-8",
    )
    evidence = {
        "project": project,
        "generated_at": "2026-07-07T00:00:00Z",
        "subject": {
            "artifact_name": artifact_name,
            "workflow": workflow,
            "attestation_action": "actions/attest@v4",
            "subject_glob": ".local/reports/**",
            "checksums_file": str(checksums_path.relative_to(root)),
        },
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "controls": [
            {
                "name": "GitHub artifact attestation",
                "status": "configured",
                "evidence": "CI grants id-token and attestations permissions, then signs generated reports with actions/attest@v4.",
            },
            {
                "name": "SLSA provenance",
                "status": "configured",
                "evidence": "The attestation emits SLSA build provenance in an in-toto predicate for demo report subjects.",
            },
            {
                "name": "Sigstore admission policy",
                "status": "documented",
                "evidence": "kubernetes/supply-chain-policy.yaml requires GitHub OIDC keyless identity for serving images.",
            },
            {
                "name": "Least-privilege CI token",
                "status": "configured",
                "evidence": "Workflow uses read-only contents permission plus scoped OIDC, attestation, and metadata write permissions.",
            },
            {
                "name": "OpenSSF-style posture",
                "status": "documented",
                "evidence": "The project records branch-protection, dependency-update, pinned-action, and vulnerability-scan expectations.",
            },
        ],
        "kubernetes_policy": {
            "namespace": namespace,
            "namespace_label": 'policy.sigstore.dev/include="true"',
            "policy_file": "kubernetes/supply-chain-policy.yaml",
            "mode": "warn-first, enforce-after-attestation-coverage",
        },
        "verification_commands": [
            "gh attestation verify .local/reports/index.html --owner kevinmeix1",
            "gh attestation verify .local/reports --repo kevinmeix1/kserve-model-serving-platform",
            "cosign verify-attestation --type slsaprovenance ghcr.io/kevinmeix1/kserve-model-serving-platform@sha256:<digest>",
        ],
        "residual_risks": [
            "Local demo reports are attested in CI; production container images still need registry digests from a real build job.",
            "Policy-controller should begin in warn mode until every workload image has signature and provenance coverage.",
            "OpenSSF Scorecard or equivalent repository scanning should run on a schedule for production adoption.",
        ],
    }
    write_json(root / "reports" / "supply_chain_evidence.json", evidence)
    return evidence
