from __future__ import annotations

from pathlib import Path

from .io import write_json


def _read_all(repo_root: Path) -> tuple[str, list[Path]]:
    files = []
    chunks = []
    for folder in ["airflow", "kubernetes", "gitops", "docs", ".github"]:
        base = repo_root / folder
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in {".py", ".yaml", ".yml", ".md"}:
                files.append(path)
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks), files


def _line_count(paths: list[Path], name_fragment: str) -> int:
    total = 0
    for path in paths:
        if name_fragment in path.name:
            total += len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    return total


def _present(content: str, *needles: str) -> bool:
    return any(needle in content for needle in needles)


def build_orchestration_scorecard(
    root: str | Path,
    *,
    repo_root: str | Path | None = None,
    project: str,
) -> dict:
    root = Path(root)
    repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
    content, files = _read_all(repo_root)
    enterprise_dag_lines = max(
        _line_count(files, "enterprise"),
        _line_count(files, "progressive"),
        _line_count(files, "control_plane"),
    )
    checks = [
        ("enterprise_airflow_dag", enterprise_dag_lines >= 120, f"largest advanced DAG has {enterprise_dag_lines} lines"),
        ("dynamic_task_mapping", ".expand(" in content, "Airflow mapped tasks create runtime fanout"),
        ("task_groups", "task_group" in content, "TaskGroups separate quality, capacity, release, and incident phases"),
        ("dataset_outlets", _present(content, "outlets=[", "Dataset("), "Dataset outlets expose asset-aware lineage"),
        ("kubernetes_pod_operator", "KubernetesPodOperator" in content, "Airflow tasks run as isolated Kubernetes pods"),
        ("branching_and_trigger_rules", _present(content, "BranchPythonOperator") and _present(content, "TriggerRule"), "Release and recovery paths branch explicitly"),
        ("pools_priority_retries", _present(content, "pool=") and _present(content, "priority_weight"), "Airflow pools and priority weights protect scarce capacity"),
        ("kueue_admission", _present(content, "ClusterQueue", "kueue.x-k8s.io"), "Kueue queues gate batch and release work"),
        ("event_driven_scaling", _present(content, "ScaledObject", "ScaledJob"), "KEDA ScaledObjects or ScaledJobs react to operational backlog"),
        ("horizontal_autoscaling", "HorizontalPodAutoscaler" in content, "HPA rules keep workers and services elastic"),
        ("opentelemetry", _present(content, "opentelemetry-collector", "OpenTelemetry"), "OTel collector config captures runtime traces and metrics"),
        ("gitops_promotion", _present(content, "Argo CD", "Argo Rollouts", "gitops"), "GitOps promotion evidence links release state to deployment control"),
        ("supply_chain_provenance", _present(content, "ClusterImagePolicy") and _present(content, "actions/attest@v4"), "Sigstore and GitHub attestations protect generated artifacts"),
    ]
    passed = [name for name, ok, _ in checks if ok]
    gaps = [name for name, ok, _ in checks if not ok]
    score = round(100 * len(passed) / len(checks), 1)
    report = {
        "project": project,
        "generated_at": "2026-07-07T00:00:00Z",
        "score": score,
        "passed_count": len(passed),
        "total_count": len(checks),
        "passed": gaps == [],
        "checks": [
            {"name": name, "passed": ok, "evidence": evidence}
            for name, ok, evidence in checks
        ],
        "gaps": gaps,
        "research_basis": [
            "Airflow dynamic task mapping and task groups for runtime fanout and maintainability",
            "OpenLineage provider patterns for Airflow DAG lineage and inter-DAG visibility",
            "Kueue, KEDA, and HPA for Kubernetes admission control and adaptive capacity",
            "GitHub artifact attestations, SLSA provenance, and Sigstore policy-controller for supply-chain integrity",
        ],
        "next_actions": [
            "Run this scorecard in CI whenever DAGs or manifests change.",
            "Keep large fanout behind Airflow pools and Kueue quotas before increasing parallelism.",
            "Promote policy-controller from warn to enforce only after all images are digest-pinned and attested.",
        ],
    }
    write_json(root / "reports" / "orchestration_scorecard.json", report)
    return report
