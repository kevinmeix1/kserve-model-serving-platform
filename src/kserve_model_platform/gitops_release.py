from __future__ import annotations

from pathlib import Path

from .io import write_json


def build_gitops_plan(root: str | Path) -> dict:
    root = Path(root)
    plan = {
        "platform": "kserve-model-serving-platform",
        "deployment_controller": "Argo CD",
        "progressive_delivery": "Argo Rollouts canary with route and shadow-analysis gates",
        "config_repo_pattern": "separate environment manifests with pinned predictor images",
        "sync_waves": [
            {"wave": -3, "name": "security-and-network", "resources": ["NetworkPolicy", "PeerAuthentication", "AuthorizationPolicy"]},
            {"wave": -2, "name": "capacity-and-routing", "resources": ["Kueue queues", "HPA", "VPA recommender", "HTTPRoute"]},
            {"wave": -1, "name": "pre-sync-serving-gates", "resources": ["payload contract job", "policy audit job"]},
            {"wave": 0, "name": "serving-runtime", "resources": ["KServe InferenceService", "gateway route"]},
            {"wave": 1, "name": "rollout-analysis", "resources": ["shadow delta check", "latency analysis", "rollback verifier"]},
        ],
        "promotion_stages": [
            {"environment": "dev", "sync": "automated", "self_heal": True, "approval": "pull request"},
            {"environment": "staging", "sync": "automated", "self_heal": True, "approval": "serving owner approval"},
            {"environment": "prod", "sync": "manual", "self_heal": False, "approval": "change ticket plus canary analysis"},
        ],
        "gates": [
            "payload contract tests pass",
            "shadow mean absolute delta stays below threshold",
            "canary Wilson error upper bound is acceptable",
            "p95 latency analysis passes",
            "network topology blocks runtime-to-runtime calls",
        ],
        "rollback": {
            "command": "argocd app rollback kserve-model-serving-platform <history-id>",
            "runtime": "argo rollouts abort credit-risk-router -n mlops-serving",
            "evidence": ".local/reports/canary_decision.json and .local/reports/serving_observability.json",
        },
    }
    write_json(root / "reports" / "gitops_plan.json", plan)
    return plan
