from __future__ import annotations

from pathlib import Path

from .io import write_json


CHECKS = [
    ("pod_security_restricted", ["pod-security.kubernetes.io/enforce: restricted"]),
    ("resource_requests", ["requests:"]),
    ("resource_limits", ["limits:"]),
    ("run_as_non_root", ["runAsNonRoot: true"]),
    ("drop_all_capabilities", ['drop: ["ALL"]']),
    ("read_only_root_filesystem", ["readOnlyRootFilesystem: true"]),
    ("queue_admission", ["kueue.x-k8s.io/queue-name"]),
    ("event_driven_scaling", ["kind: ScaledObject", "kind: ScaledJob"]),
    ("weighted_gateway_route", ["weight: 95", "weight: 5"]),
    ("no_latest_image_tags", [":latest"]),
    ("immutable_image_digest", ["@sha256:"]),
]


def manifest_files(root: str | Path) -> list[Path]:
    root = Path(root)
    folders = [root / "kubernetes", root / "kserve", root / "monitoring"]
    files: list[Path] = []
    for folder in folders:
        if folder.exists():
            files.extend(sorted(folder.rglob("*.yaml")))
            files.extend(sorted(folder.rglob("*.yml")))
    return files


def evaluate_check(name: str, patterns: list[str], combined_text: str) -> bool:
    if name == "no_latest_image_tags":
        return not any(pattern in combined_text for pattern in patterns)
    if name == "event_driven_scaling":
        return any(pattern in combined_text for pattern in patterns)
    return all(pattern in combined_text for pattern in patterns)


def audit_platform_policy(repo_root: str | Path = ".", *, output_root: str | Path | None = None) -> dict:
    repo_root = Path(repo_root)
    output_root = Path(output_root) if output_root is not None else repo_root / ".local"
    files = manifest_files(repo_root)
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    checks = [
        {
            "name": name,
            "passed": evaluate_check(name, patterns, combined),
            "patterns": patterns,
        }
        for name, patterns in CHECKS
    ]
    failed = [check["name"] for check in checks if not check["passed"]]
    report = {
        "manifest_count": len(files),
        "score": round(100 * sum(1 for check in checks if check["passed"]) / len(checks), 2),
        "passed": not failed,
        "checks": checks,
        "failed_checks": failed,
        "recommendations": {
            "no_latest_image_tags": "Pin images to immutable semantic tags or digests before production rollout.",
            "immutable_image_digest": "Publish signed images and reference them by digest after vulnerability scanning.",
        },
    }
    write_json(output_root / "reports" / "policy_audit.json", report)
    return report
