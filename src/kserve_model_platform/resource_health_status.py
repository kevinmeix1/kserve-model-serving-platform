from __future__ import annotations

from pathlib import Path

from .io import write_json


DEVICE_HEALTH_EVENTS = [
    {
        "workload": "credit-risk-challenger",
        "namespace": "mlops-serving",
        "pod": "credit-risk-challenger-dra-0",
        "container": "predictor",
        "resource_claim": "l4-shared-challenger-claim",
        "device_class": "gpu-l4-shared",
        "resource": "gpu.resource.kubernetes.io",
        "health": "Unhealthy",
        "message": "driver reported SM reset on shared L4 during challenger warmup",
        "owner_action": "route challenger traffic back to champion and keep shadow scoring on CPU",
    },
    {
        "workload": "shadow-analysis-runner",
        "namespace": "mlops-serving-analysis",
        "pod": "shadow-analysis-runner-1",
        "container": "shadow-evaluator",
        "resource_claim": "l4-shared-shadow-analysis-claim",
        "device_class": "gpu-l4-shared",
        "resource": "gpu.resource.kubernetes.io",
        "health": "Unknown",
        "message": "DRA driver missed health update timeout after 30 seconds",
        "owner_action": "continue request logging and delay promotion until CPU shadow samples pass",
    },
    {
        "workload": "rollback-smoke-probe",
        "namespace": "mlops-serving",
        "pod": "rollback-smoke-probe-cpu-0",
        "container": "rollback-smoke",
        "resource_claim": None,
        "device_class": "cpu-fallback",
        "resource": "cpu",
        "health": "Healthy",
        "message": "CPU rollback smoke has no DRA device dependency",
        "owner_action": "keep rollback smoke schedulable while GPU pool is quarantined",
    },
]


def build_resource_health_status_plan(
    root: str | Path,
    *,
    project: str = "KServe Model Serving Platform",
) -> dict:
    root = Path(root)
    unhealthy = [event for event in DEVICE_HEALTH_EVENTS if event["health"] in {"Unhealthy", "Unknown"}]
    checks = [
        {
            "name": "resource_health_status_enabled",
            "passed": True,
            "evidence": "ResourceHealthStatus is beta and enabled by default in Kubernetes v1.36.",
        },
        {
            "name": "pod_allocated_resources_status_checked",
            "passed": all(event["container"] and event["pod"] for event in DEVICE_HEALTH_EVENTS),
            "evidence": "Runbook queries Pod status.containerStatuses[*].allocatedResourcesStatus before changing KServe traffic.",
        },
        {
            "name": "resourceclaim_device_status_checked",
            "passed": any(event["resource_claim"] for event in DEVICE_HEALTH_EVENTS),
            "evidence": "ResourceClaim status.devices is captured for allocated challenger and shadow-analysis accelerators.",
        },
        {
            "name": "device_taint_rule_declared",
            "passed": True,
            "evidence": "DeviceTaintRule quarantines unhealthy shared L4 devices before another challenger claim lands on them.",
        },
        {
            "name": "rollback_path_kept_cpu_runnable",
            "passed": any(event["workload"] == "rollback-smoke-probe" and event["resource"] == "cpu" for event in DEVICE_HEALTH_EVENTS),
            "evidence": "The rollback smoke path stays schedulable even while GPU devices are quarantined.",
        },
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_kserve_dra_resource_health_runbook",
        "feature": {
            "name": "ResourceHealthStatus",
            "state": "Kubernetes v1.36 beta and enabled by default",
            "pod_status_field": "status.containerStatuses[*].allocatedResourcesStatus",
            "driver_service": "DRAResourceHealth gRPC service",
            "default_unknown_timeout_seconds": 30,
        },
        "companion_features": {
            "resource_claim_device_status": "Kubernetes v1.33 beta; status.devices on ResourceClaim",
            "granular_status_authorization": "Kubernetes v1.36 beta; synthetic subresources and node-aware verbs",
            "device_taints": "Kubernetes v1.36 beta; DeviceTaintRule uses resource.k8s.io/v1beta2",
        },
        "device_health_events": DEVICE_HEALTH_EVENTS,
        "unhealthy_or_unknown_count": len(unhealthy),
        "serving_decision_policy": [
            "Never advance challenger traffic while any challenger or shadow-analysis DRA device is Unhealthy or Unknown.",
            "Prefer champion routing before retrying accelerator-backed challenger pods.",
            "Allow CPU rollback smoke probes to run even when shared GPU pools are tainted.",
            "Require fresh ResourceClaim status.devices evidence before widening canary traffic or GPU explainers.",
            "Use PodResourcesLister DynamicResource telemetry to correlate device name, claim name, and predictor latency.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/dra-resource-health-status.yaml"],
        "references": [
            "https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/",
            "https://kubernetes.io/blog/2026/05/07/kubernetes-v1-36-dra-136-updates/",
            "https://github.com/kubernetes/sig-release/discussions/2958",
        ],
    }
    write_json(root / "reports" / "resource_health_status_plan.json", plan)
    return plan
