from __future__ import annotations

from pathlib import Path

from .io import write_json


def _fits(used: dict, workload: dict, quota: dict) -> bool:
    return (
        used["cpu"] + workload["cpu"] <= quota["cpu"]
        and used["memory_gib"] + workload["memory_gib"] <= quota["memory_gib"]
        and used["gpu"] + workload.get("gpu", 0) <= quota["gpu"]
        and used["airflow_pool_slots"] + workload["airflow_pool_slots"] <= quota["airflow_pool_slots"]
    )


def _add(used: dict, workload: dict, sign: int = 1) -> None:
    used["cpu"] += sign * workload["cpu"]
    used["memory_gib"] += sign * workload["memory_gib"]
    used["gpu"] += sign * workload.get("gpu", 0)
    used["airflow_pool_slots"] += sign * workload["airflow_pool_slots"]


def simulate_queue(workloads: list[dict], quota: dict) -> dict:
    used = {"cpu": 0.0, "memory_gib": 0.0, "gpu": 0.0, "airflow_pool_slots": 0.0}
    admitted: list[dict] = []
    pending: list[dict] = []
    preempted: list[dict] = []
    for workload in sorted(workloads, key=lambda item: (item["submitted_minute"], -item["priority"])):
        if _fits(used, workload, quota):
            _add(used, workload)
            admitted.append({**workload, "status": "admitted"})
            continue
        evicted = []
        for victim in sorted([item for item in admitted if item["priority"] < workload["priority"]], key=lambda item: item["priority"]):
            admitted.remove(victim)
            _add(used, victim, sign=-1)
            evicted.append(victim)
            if _fits(used, workload, quota):
                break
        if _fits(used, workload, quota):
            _add(used, workload)
            admitted.append({**workload, "status": "admitted", "preempted_workloads": [item["name"] for item in evicted]})
            preempted.extend({**item, "status": "preempted_by", "preemptor": workload["name"]} for item in evicted)
        else:
            for victim in evicted:
                _add(used, victim)
                admitted.append(victim)
            pending.append({**workload, "status": "pending", "reason": "quota_or_pool_exhausted"})
    return {"admitted": admitted, "pending": pending, "preempted": preempted, "used": {key: round(value, 2) for key, value in used.items()}}


def build_queue_simulation(root: str | Path, *, project: str = "KServe Model Serving Platform") -> dict:
    quota = {"cpu": 12.0, "memory_gib": 48.0, "gpu": 1.0, "airflow_pool_slots": 6.0}
    workloads = [
        {"name": "champion-predictor-prewarm", "queue": "credit-risk-serving-queue", "priority": 850, "cpu": 4.0, "memory_gib": 12.0, "gpu": 0.0, "airflow_pool_slots": 1.0, "duration_minutes": 20, "submitted_minute": 0},
        {"name": "challenger-shadow-analysis", "queue": "credit-risk-serving-queue", "priority": 650, "cpu": 4.0, "memory_gib": 12.0, "gpu": 1.0, "airflow_pool_slots": 2.0, "duration_minutes": 30, "submitted_minute": 0},
        {"name": "batch-score-replay", "queue": "serving-batch", "priority": 300, "cpu": 3.0, "memory_gib": 8.0, "gpu": 0.0, "airflow_pool_slots": 2.0, "duration_minutes": 45, "submitted_minute": 1},
        {"name": "load-test-sweep", "queue": "experimentation", "priority": 100, "cpu": 2.0, "memory_gib": 6.0, "gpu": 0.0, "airflow_pool_slots": 1.0, "duration_minutes": 40, "submitted_minute": 2},
        {"name": "emergency-champion-rollback", "queue": "credit-risk-serving-queue", "priority": 1000, "cpu": 3.0, "memory_gib": 8.0, "gpu": 0.0, "airflow_pool_slots": 2.0, "duration_minutes": 6, "submitted_minute": 5},
    ]
    simulation = simulate_queue(workloads, quota)
    critical_pending = [item for item in simulation["pending"] if item["priority"] >= 900]
    report = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "quota": quota,
        "workload_count": len(workloads),
        "admitted_count": len(simulation["admitted"]),
        "pending_count": len(simulation["pending"]),
        "preempted_count": len(simulation["preempted"]),
        "queue_pressure": round(simulation["used"]["cpu"] / quota["cpu"], 4),
        "passed": not critical_pending,
        "simulation": simulation,
        "controls": [
            "Champion predictor prewarm outranks batch replay and load tests.",
            "Emergency rollback can preempt low-priority serving experiments.",
            "Canary analysis consumes GPU and Airflow slots so traffic decisions stay capacity-aware.",
            "Pending non-critical replay work does not block rollback or champion availability.",
        ],
        "recommendations": [
            "Reserve two serving-release pool slots for rollback commands.",
            "Keep load tests outside the serving ClusterQueue during rollout windows.",
            "Use Kueue preemption events as incident annotations during emergency rollback.",
        ],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/",
            "https://kueue.sigs.k8s.io/docs/concepts/workload_priority_class/",
            "https://kueue.sigs.k8s.io/docs/concepts/preemption/",
            "https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html",
            "https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/",
        ],
    }
    write_json(Path(root) / "reports" / "queue_simulation.json", report)
    return report
