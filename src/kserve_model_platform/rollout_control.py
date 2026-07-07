from __future__ import annotations

import math
from pathlib import Path

from .io import read_json, write_json


CANARY_STEPS = [1, 5, 10, 25, 50, 100]


def wilson_error_upper_bound(failures: int, total: int, *, z: float = 1.96) -> float:
    if total <= 0:
        return 1.0
    p_hat = failures / total
    denominator = 1 + z**2 / total
    centre = p_hat + z**2 / (2 * total)
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * total)) / total)
    return round((centre + margin) / denominator, 6)


def next_canary_percent(current_percent: int, *, passed: bool) -> int:
    if not passed:
        return current_percent
    for step in CANARY_STEPS:
        if step > current_percent:
            return step
    return 100


def evaluate_rollout(report: dict, current_percent: int) -> dict:
    total = int(report.get("request_count", 0))
    failures = int(report.get("error_count", 0))
    latency_p95 = float(report.get("latency_ms", {}).get("p95", 999.0))
    shadow_delta = float(report.get("shadow", {}).get("mean_abs_delta", 1.0))
    challenger_count = int(report.get("route_counts", {}).get("challenger", 0))
    error_upper = wilson_error_upper_bound(failures, total)
    checks = [
        {"name": "minimum_canary_sample", "passed": challenger_count >= max(5, current_percent), "observed": challenger_count},
        {"name": "wilson_error_upper_bound", "passed": error_upper <= 0.02, "observed": error_upper, "threshold": 0.02},
        {"name": "latency_p95", "passed": latency_p95 <= 35.0, "observed": latency_p95, "threshold": 35.0},
        {"name": "shadow_delta", "passed": shadow_delta <= 0.12, "observed": shadow_delta, "threshold": 0.12},
    ]
    passed = all(check["passed"] for check in checks)
    if error_upper > 0.05 or latency_p95 > 75.0:
        action = "rollback"
    elif current_percent >= 50 and passed:
        action = "promote"
    elif passed:
        action = "advance"
    else:
        action = "hold"
    return {
        "action": action,
        "checks": checks,
        "current_percent": current_percent,
        "next_percent": next_canary_percent(current_percent, passed=passed),
        "error_upper_bound": error_upper,
    }


def build_rollout_plan(root: str | Path) -> dict:
    root = Path(root)
    report = read_json(root / "reports" / "serving_observability.json")
    state = read_json(root / "deployments" / "kserve_state.json")
    current_percent = int(state.get("traffic", {}).get("challenger", 0))
    evaluation = evaluate_rollout(report, current_percent)
    next_percent = evaluation["next_percent"]
    plan = {
        "service": state.get("service_name", "credit-risk-router"),
        "current_percent": current_percent,
        "recommended_action": evaluation["action"],
        "next_percent": next_percent,
        "kserve_patch": {
            "spec": {
                "predictor": {
                    "canaryTrafficPercent": next_percent if evaluation["action"] == "advance" else current_percent
                }
            }
        },
        "gateway_weights": {
            "champion": max(0, 100 - next_percent),
            "challenger": next_percent,
        },
        "analysis": evaluation,
    }
    write_json(root / "reports" / "rollout_control_plan.json", plan)
    return plan
