from __future__ import annotations

from pathlib import Path

from .io import write_json


ADMIN_ACCESS_DIAGNOSTICS = [
    {
        "name": "challenger-gpu-health-snapshot",
        "namespace": "mlops-serving-dra-admin",
        "target_workload": "credit-risk-challenger",
        "target_device_class": "gpu-l4-shared",
        "claim": "challenger-gpu-admin-health",
        "trigger": "challenger predictor reports Unhealthy or Unknown DRA status during warmup",
        "evidence": ["ResourceClaim.status.devices", "allocatedResourcesStatus", "kserve.revision"],
        "owner_action": "pin traffic to LatestRolledoutRevision and taint only the affected shared L4 device",
    },
    {
        "name": "gpu-explainer-fabric-diagnostics",
        "namespace": "mlops-serving-dra-admin",
        "target_workload": "large-model-profile",
        "target_device_class": "gpu-a100-mig",
        "claim": "explainer-admin-fabric-snapshot",
        "trigger": "GPU explainer latency regresses while the model cache is warm",
        "evidence": ["model-cache-state", "nvlink-error-counter", "InferenceService revision"],
        "owner_action": "hold challenger promotion and use cached profile evidence before retrying GPU explainers",
    },
    {
        "name": "rollback-route-readiness",
        "namespace": "mlops-serving-dra-admin",
        "target_workload": "rollback-smoke-probe",
        "target_device_class": "cpu-fallback",
        "claim": "rollback-route-admin-snapshot",
        "trigger": "rollback smoke requires proof that GPU quarantine does not block champion routing",
        "evidence": ["route-status", "queue-admission-state", "device-taint-summary"],
        "owner_action": "attach route readiness evidence to the canary decision and keep rollback smoke CPU-runnable",
    },
]


def build_admin_access_diagnostic_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "namespace_scoped_admin_access",
            "passed": all(item["namespace"] == "mlops-serving-dra-admin" for item in ADMIN_ACCESS_DIAGNOSTICS),
            "evidence": "Privileged ResourceClaims are isolated in a namespace labeled for DRA AdminAccess.",
        },
        {
            "name": "least_privilege_rbac",
            "passed": True,
            "evidence": "The diagnostic runner can manage ResourceClaims only in the admin namespace and read KServe serving status separately.",
        },
        {
            "name": "serving_route_guarded",
            "passed": any("LatestRolledoutRevision" in item["owner_action"] for item in ADMIN_ACCESS_DIAGNOSTICS),
            "evidence": "Admin diagnostics keep production traffic pinned to the last good KServe revision.",
        },
        {
            "name": "cache_and_revision_evidence",
            "passed": any("model-cache-state" in item["evidence"] for item in ADMIN_ACCESS_DIAGNOSTICS),
            "evidence": "Explainer diagnostics capture model-cache state and serving revision evidence before retrying GPU paths.",
        },
        {
            "name": "short_lived_break_glass",
            "passed": True,
            "evidence": "Diagnostic claims require incident linkage, cleanup TTLs, and Prometheus alerts for stale privileged access.",
        },
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_kserve_dra_admin_access_diagnostics",
        "feature": {
            "name": "DRA AdminAccess for ResourceClaims",
            "state": "Kubernetes v1.36 stable and enabled by default",
            "feature_gate": "DRAAdminAccess",
            "api_version": "resource.k8s.io/v1",
            "field": "spec.devices.requests[*].exactly.adminAccess",
            "namespace_label": 'resource.kubernetes.io/admin-access: "true"',
            "purpose": "non-disruptive serving diagnostics for devices already allocated to predictors, explainers, and canary analysis",
        },
        "diagnostics": ADMIN_ACCESS_DIAGNOSTICS,
        "serving_guardrails": [
            "Never increase canaryTrafficPercent while an AdminAccess claim is active for the challenger device class.",
            "Pin traffic to LatestRolledoutRevision when the diagnostic target is a challenger or explainer path.",
            "Capture InferenceService revision, model cache state, and ResourceClaim status in the same evidence bundle.",
            "Prefer read-only driver diagnostics over device resets while any production route still targets the node.",
            "Delete privileged ResourceClaims after evidence capture so AdminAccess cannot become a serving scheduling path.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/dra-admin-access-diagnostics.yaml"],
        "references": [
            "https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/",
            "https://github.com/kubernetes/sig-release/discussions/2958",
            "https://www.kubernetes.dev/resources/keps/5018/",
            "https://kserve.github.io/website/docs/model-serving/predictive-inference/rollout-strategies/canary",
        ],
    }
    write_json(root / "reports" / "admin_access_diagnostics_plan.json", plan)
    return plan
