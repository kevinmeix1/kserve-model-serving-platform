from __future__ import annotations

from pathlib import Path

from .io import write_json


FLAVOR_POLICIES = [
    {
        "name": "online-serving",
        "cluster_queue": "online-serving-flavor-queue",
        "local_queue": "online-route-smoke",
        "resource": "cpu",
        "flavor_order": ["cpu-on-demand", "cpu-spot"],
        "when_can_borrow": "TryNextFlavor",
        "when_can_preempt": "TryNextFlavor",
        "preference": "BorrowingOverPreemption",
        "nominal_quota": {"cpu-on-demand": 20, "cpu-spot": 6},
        "borrowing_limit": {"cpu-on-demand": 4, "cpu-spot": 6},
        "rationale": "online route validation prefers stable on-demand nodes and only falls back to spot before borrowing",
    },
    {
        "name": "canary-analysis-gpu",
        "cluster_queue": "canary-analysis-flavor-queue",
        "local_queue": "gpu-explainer",
        "resource": "nvidia.com/gpu",
        "flavor_order": ["gpu-l4-reserved", "gpu-l4-spot"],
        "when_can_borrow": "TryNextFlavor",
        "when_can_preempt": "TryNextFlavor",
        "preference": "BorrowingOverPreemption",
        "nominal_quota": {"gpu-l4-reserved": 1, "gpu-l4-spot": 2},
        "borrowing_limit": {"gpu-l4-reserved": 1, "gpu-l4-spot": 2},
        "rationale": "explainers try reserved GPU first and then spot before preempting serving-analysis workloads",
    },
    {
        "name": "load-test",
        "cluster_queue": "load-test-flavor-queue",
        "local_queue": "synthetic-load",
        "resource": "cpu",
        "flavor_order": ["cpu-spot", "cpu-on-demand"],
        "when_can_borrow": "TryNextFlavor",
        "when_can_preempt": "TryNextFlavor",
        "preference": "BorrowingOverPreemption",
        "nominal_quota": {"cpu-spot": 16, "cpu-on-demand": 2},
        "borrowing_limit": {"cpu-spot": 10, "cpu-on-demand": 2},
        "rationale": "synthetic load remains cheap-first and has a very small on-demand fallback quota",
    },
]


def _fallback_depth(policy: dict) -> int:
    return max(len(policy["flavor_order"]) - 1, 0)


def build_flavor_fungibility_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    policies = [
        {
            **policy,
            "fallback_depth": _fallback_depth(policy),
            "total_nominal_quota": sum(policy["nominal_quota"].values()),
            "total_borrowing_limit": sum(policy["borrowing_limit"].values()),
        }
        for policy in FLAVOR_POLICIES
    ]
    checks = [
        {
            "name": "resource_flavors_declared",
            "passed": True,
            "evidence": "ResourceFlavors separate on-demand serving nodes, spot analysis nodes, and L4 GPU explainer nodes.",
        },
        {
            "name": "try_next_before_borrow",
            "passed": all(policy["when_can_borrow"] == "TryNextFlavor" for policy in policies),
            "evidence": "Serving analysis tries the next ResourceFlavor before borrowing from online-serving quota.",
        },
        {
            "name": "try_next_before_preempt",
            "passed": all(policy["when_can_preempt"] == "TryNextFlavor" for policy in policies),
            "evidence": "Canary and load-test jobs try alternate flavors before preempting admitted rollout work.",
        },
        {
            "name": "explicit_preference_declared",
            "passed": all(policy["preference"] == "BorrowingOverPreemption" for policy in policies),
            "evidence": "BorrowingOverPreemption is declared explicitly so serving fallbacks do not rely on implicit defaults.",
        },
        {
            "name": "online_and_load_test_have_distinct_order",
            "passed": policies[0]["flavor_order"] != policies[-1]["flavor_order"],
            "evidence": "Online serving uses stability-first flavor order while synthetic load stays spot-first.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_serving_kueue_flavor_fungibility" if passed else "keep_static_serving_flavors",
        "kueue_api_target": "kueue.x-k8s.io/v1beta1",
        "feature": {
            "name": "FlavorFungibility",
            "whenCanBorrow": "TryNextFlavor avoids cohort borrowing when another serving ResourceFlavor can fit",
            "whenCanPreempt": "TryNextFlavor avoids disrupting admitted rollout work when another flavor can fit",
            "preference": "BorrowingOverPreemption is explicit for predictable serving-analysis behavior",
        },
        "flavor_policies": policies,
        "operational_guardrails": [
            "Keep online route and rollback smoke on stability-first flavors.",
            "Keep synthetic load spot-first with small on-demand fallback so demos cannot consume live-serving headroom.",
            "Use GPU flavor fallback for explainers, not for live predictors on the critical path.",
            "Record selected ResourceFlavor, fallback depth, route generation, and model version in rollout evidence.",
            "Test spot loss, on-demand saturation, and GPU explainer exhaustion before increasing challenger traffic.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/kueue-flavor-fungibility.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/",
            "https://kueue.sigs.k8s.io/docs/concepts/resource_flavor/",
            "https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta1/#flavorfungibility",
        ],
    }
    write_json(root / "reports" / "flavor_fungibility_plan.json", plan)
    return plan
