from __future__ import annotations

from pathlib import Path

from .io import write_json


DELEGATIONS = [
    {
        "name": "serving-debugger-read-router",
        "namespace": "mlops-serving",
        "impersonator": "system:serviceaccount:mlops-serving:serving-debugger",
        "target_service_account": "router-reader",
        "identity_permission": "impersonate:serviceaccount",
        "action_permissions": [
            "impersonate-on:serviceaccount:get",
            "impersonate-on:serviceaccount:list",
            "impersonate-on:serviceaccount:watch",
        ],
        "resources": ["inferenceservices/status", "httproutes", "pods/log"],
        "risk_control": "Debug tooling can inspect KServe routing health without inheriting rollout patch authority.",
    },
    {
        "name": "rollback-controller-patch-serving-status",
        "namespace": "mlops-serving",
        "impersonator": "system:serviceaccount:mlops-serving:rollback-controller",
        "target_service_account": "serving-status-writer",
        "identity_permission": "impersonate:serviceaccount",
        "action_permissions": [
            "impersonate-on:serviceaccount:get",
            "impersonate-on:serviceaccount:patch",
        ],
        "resources": ["inferenceservices/status", "httproutes/status"],
        "risk_control": "Rollback automation can patch serving status but cannot delete routes or create arbitrary revisions.",
    },
]


def build_constrained_impersonation_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    feature = {
        "name": "ConstrainedImpersonation",
        "state": "Kubernetes v1.36 beta and enabled by default",
        "scope": "two-step authorization for impersonated identity plus scoped actions",
        "not_for": "broad legacy impersonate grants that inherit every target permission",
    }
    checks = [
        {
            "name": "beta_feature_status_recorded",
            "passed": feature["state"].startswith("Kubernetes v1.36 beta"),
            "evidence": "The plan records the feature status before relying on constrained impersonation.",
        },
        {
            "name": "identity_permission_is_separate",
            "passed": all(item["identity_permission"] == "impersonate:serviceaccount" for item in DELEGATIONS),
            "evidence": "Each delegation has an explicit service account identity grant.",
        },
        {
            "name": "action_permissions_are_constrained",
            "passed": all(
                all(verb.startswith("impersonate-on:serviceaccount:") for verb in item["action_permissions"])
                for item in DELEGATIONS
            ),
            "evidence": "Every delegated action uses impersonate-on service account verbs.",
        },
        {
            "name": "dangerous_verbs_excluded",
            "passed": all(
                not {"delete", "create"}.intersection({verb.rsplit(":", 1)[-1] for verb in item["action_permissions"]})
                for item in DELEGATIONS
            ),
            "evidence": "Debug and rollback delegation excludes broad create/delete authority.",
        },
        {
            "name": "audit_requirement_recorded",
            "passed": all(item["risk_control"] for item in DELEGATIONS),
            "evidence": "Each delegation documents the production risk it is narrowing.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-09T00:00:00Z",
        "recommended_action": "enable_constrained_impersonation_for_serving_debugging" if passed else "keep_legacy_impersonation_blocked",
        "passed": passed,
        "feature": feature,
        "delegations": DELEGATIONS,
        "checks": checks,
        "runbook": [
            "Grant impersonate:serviceaccount only for the exact target service account.",
            "Grant impersonate-on:serviceaccount verbs only for the KServe and Gateway API actions the workflow needs.",
            "Alert on legacy impersonate verbs that are not paired with constrained action grants.",
            "Inspect audit authenticationMetadata.impersonationConstraint during serving rollback investigations.",
        ],
        "references": [
            "https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/",
            "https://kubernetes.io/docs/reference/access-authn-authz/user-impersonation/",
        ],
    }
    write_json(root / "reports" / "constrained_impersonation_plan.json", plan)
    return plan
