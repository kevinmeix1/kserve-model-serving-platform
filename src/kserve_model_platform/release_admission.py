from __future__ import annotations

from pathlib import Path

from .io import read_json, write_json


def _load(path: Path, default: dict) -> dict:
    return read_json(path) if path.exists() else default


def _check(name: str, passed: bool, observed: object, *, owner: str, action: str) -> dict:
    return {
        "name": name,
        "passed": passed,
        "observed": observed,
        "owner": owner,
        "action": action if not passed else "none",
    }


def evaluate_release_admission(
    *,
    slo: dict,
    performance: dict,
    queue: dict,
    governance: dict,
    supply_chain: dict,
    rollout_plan: dict,
    canary_decision: dict,
) -> dict:
    max_burn = float(slo.get("max_burn_rate", 0.0))
    release_freeze = bool(slo.get("release_freeze", False))
    performance_passed = bool(performance.get("passed", False))
    queue_passed = bool(queue.get("passed", False))
    rollback_pending = [
        item["name"]
        for item in queue.get("simulation", {}).get("pending", [])
        if int(item.get("priority", 0)) >= 900
    ]
    governance_decision = governance.get("release", {}).get("decision", "unknown")
    attestation_ready = (
        int(supply_chain.get("artifact_count", 0)) > 0
        and supply_chain.get("subject", {}).get("attestation_action") == "actions/attest@v4"
    )
    rollout_action = rollout_plan.get("recommended_action", "unknown")
    canary_passed = bool(canary_decision.get("passed", False))
    checks = [
        _check(
            "canary_analysis",
            canary_passed and rollout_action in {"advance", "promote"},
            {"canary_passed": canary_passed, "rollout_action": rollout_action, "next_percent": rollout_plan.get("next_percent")},
            owner="serving",
            action="rollback_challenger",
        ),
        _check(
            "slo_error_budget",
            not release_freeze and max_burn < 6.0,
            {"max_burn_rate": max_burn, "recommended_action": slo.get("recommended_action")},
            owner="sre",
            action="freeze_canary",
        ),
        _check(
            "performance_budget",
            performance_passed,
            {"failed": [check["name"] for check in performance.get("checks", []) if not check.get("passed")]},
            owner="ml-platform",
            action="hold_canary",
        ),
        _check(
            "rollback_capacity",
            queue_passed and not rollback_pending,
            {"pending_count": queue.get("pending_count", 0), "critical_pending": rollback_pending},
            owner="orchestration",
            action="reserve_rollback_capacity",
        ),
        _check(
            "governance_and_provenance",
            governance_decision in {"approved_for_challenger", "approved_for_serving", "approved_for_promotion"} and attestation_ready,
            {"governance": governance_decision, "attestation_ready": attestation_ready},
            owner="risk",
            action="require_signed_approval",
        ),
    ]
    if rollout_action == "rollback" or not canary_passed:
        action = "rollback_challenger"
    elif release_freeze or max_burn >= 14.4:
        action = "freeze_canary"
    elif not queue_passed or rollback_pending:
        action = "throttle_serving_queue"
    elif all(check["passed"] for check in checks) and rollout_action == "promote":
        action = "promote_challenger"
    elif all(check["passed"] for check in checks):
        action = "advance_canary"
    else:
        action = "hold_canary"
    return {
        "recommended_action": action,
        "admitted": action in {"advance_canary", "promote_challenger"},
        "unsafe_allow": action in {"advance_canary", "promote_challenger"} and not all(check["passed"] for check in checks),
        "checks": checks,
        "rollout_plan_action": rollout_action,
        "failure_policy": "fail_closed",
    }


def build_release_admission_decision(root: str | Path) -> dict:
    root = Path(root)
    decision = evaluate_release_admission(
        slo=_load(root / "reports" / "slo_error_budget.json", {}),
        performance=_load(root / "reports" / "performance_budget.json", {}),
        queue=_load(root / "reports" / "queue_simulation.json", {}),
        governance=_load(root / "reports" / "governance_evidence_bundle.json", {}),
        supply_chain=_load(root / "reports" / "supply_chain_evidence.json", {}),
        rollout_plan=_load(root / "reports" / "rollout_control_plan.json", {}),
        canary_decision=_load(root / "reports" / "canary_decision.json", {}),
    )
    record = {
        "project": "KServe Model Serving Platform",
        "target": "kserve://mlops-serving/credit-risk-router",
        "evaluated_at": "2026-07-08T00:00:00Z",
        "decision": decision,
        "policy_inputs": {
            "canary": "reports/canary_decision.json",
            "rollout": "reports/rollout_control_plan.json",
            "slo": "reports/slo_error_budget.json",
            "performance": "reports/performance_budget.json",
            "queue": "reports/queue_simulation.json",
            "governance": "reports/governance_evidence_bundle.json",
            "supply_chain": "reports/supply_chain_evidence.json",
        },
        "enforcement_points": [
            "Airflow progressive rollout DAG pauses unless the decision is advance_canary or promote_challenger.",
            "Kubernetes ValidatingAdmissionPolicy requires release-decision and evidence-sha annotations on InferenceService updates.",
            "Argo Rollouts analysis checks Prometheus latency, error, and shadow-delta signals before traffic changes.",
            "Kueue priority keeps emergency champion rollback ahead of batch scoring and load-test work.",
        ],
        "references": [
            "https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/",
            "https://argo-rollouts.readthedocs.io/en/stable/features/analysis/",
            "https://kserve.github.io/website/docs/model-serving/predictive-inference/rollout-strategies/canary",
            "https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html",
        ],
    }
    write_json(root / "reports" / "release_admission_decision.json", record)
    return record
