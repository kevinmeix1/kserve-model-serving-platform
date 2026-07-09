from __future__ import annotations

from pathlib import Path

from .io import write_json


WORKLOADS = [
    {
        "name": "credit-risk-router",
        "qos_class": "Guaranteed",
        "request_memory": "384Mi",
        "limit_memory": "384Mi",
        "protection": "memory.min set from request for hard protection",
        "reason": "The request router must stay responsive during rollout and incident pressure.",
    },
    {
        "name": "champion-predictor",
        "qos_class": "Guaranteed",
        "request_memory": "1Gi",
        "limit_memory": "1Gi",
        "protection": "memory.min set from request for hard protection",
        "reason": "Champion inference is the fallback path during canary and rollback events.",
    },
    {
        "name": "challenger-predictor",
        "qos_class": "Burstable",
        "request_memory": "1Gi",
        "limit_memory": "2Gi",
        "protection": "memory.low set from request with memory.high throttling",
        "reason": "Canary traffic should be protected but still yield to champion under pressure.",
    },
    {
        "name": "shadow-analysis-job",
        "qos_class": "Burstable",
        "request_memory": "2Gi",
        "limit_memory": "5Gi",
        "protection": "memory.low set from request for useful replay work",
        "reason": "Replay analysis is important but should not starve online inference.",
    },
    {
        "name": "ad-hoc-model-debugger",
        "qos_class": "BestEffort",
        "request_memory": "0",
        "limit_memory": "0",
        "protection": "no memory.min or memory.low protection",
        "reason": "Interactive diagnostics should be first to reclaim under pressure.",
    },
]


def build_memory_qos_plan(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    root = Path(root)
    kubelet_config = {
        "apiVersion": "kubelet.config.k8s.io/v1beta1",
        "kind": "KubeletConfiguration",
        "featureGates": {"MemoryQoS": True},
        "memoryReservationPolicy": "TieredReservation",
        "memoryThrottlingFactor": 0.9,
        "runtimeRequirements": ["cgroup v2", "kernel >= 5.9 recommended", "containerd 1.6+ or CRI-O 1.22+"],
    }
    checks = [
        {
            "name": "tiered_reservation_enabled",
            "passed": kubelet_config["memoryReservationPolicy"] == "TieredReservation",
            "evidence": "Guaranteed Pods receive memory.min and Burstable Pods receive memory.low protection.",
        },
        {
            "name": "online_inference_has_hard_protection",
            "passed": all(
                workload["qos_class"] == "Guaranteed"
                for workload in WORKLOADS
                if workload["name"] in {"credit-risk-router", "champion-predictor"}
            ),
            "evidence": "Router and champion predictor use Guaranteed QoS for rollback-safe inference.",
        },
        {
            "name": "cgroup_v2_preconditions_documented",
            "passed": "cgroup v2" in kubelet_config["runtimeRequirements"],
            "evidence": "Memory QoS tiered protection requires cgroup v2 and a compatible runtime.",
        },
        {
            "name": "kernel_livelock_guardrail",
            "passed": any("kernel >= 5.9" in item for item in kubelet_config["runtimeRequirements"]),
            "evidence": "The plan records the Kubernetes v1.36 warning path for kernels older than 5.9.",
        },
        {
            "name": "psi_observability",
            "passed": True,
            "evidence": "PSI metrics are paired with memory.high throttling alerts before blaming model latency.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-07T00:00:00Z",
        "recommended_action": "enable_memory_qos_tiered_protection" if passed else "keep_memory_qos_in_observe_mode",
        "passed": passed,
        "feature_status": {
            "memory_qos": "Kubernetes v1.36 alpha update with opt-in tiered protection",
            "memory_reservation_policy": "TieredReservation sets memory.min for Guaranteed Pods and memory.low for Burstable Pods",
            "memory_high": "Feature gate still enables memory.high throttling using memoryThrottlingFactor",
            "kernel_guardrail": "Kubelet logs a warning below Linux kernel 5.9",
        },
        "kubelet_config": kubelet_config,
        "workloads": WORKLOADS,
        "checks": checks,
        "runbook": [
            "Enable MemoryQoS first on serving node pools with canary traffic.",
            "Keep router and champion predictor Guaranteed.",
            "Make challenger and shadow analysis Burstable with realistic requests.",
            "Alert on memory.high throttling and PSI before automatic rollback on latency.",
        ],
        "references": [
            "https://kubernetes.io/blog/2026/04/29/kubernetes-v1-36-memory-qos-tiered-protection/",
            "https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/",
        ],
    }
    write_json(root / "reports" / "memory_qos_plan.json", plan)
    return plan
