from __future__ import annotations

from pathlib import Path

from .io import read_json, write_json


def burn_rate(error_ratio: float, target: float) -> float:
    return round(error_ratio / max(1.0 - target, 0.0001), 4)


def remaining_budget_pct(error_ratio: float, target: float) -> float:
    budget = max(1.0 - target, 0.0001)
    return round(max(0.0, 100.0 * (1.0 - error_ratio / budget)), 2)


def _slo(name: str, *, target: float, error_ratio: float, owner: str) -> dict:
    burn = burn_rate(error_ratio, target)
    if burn >= 14.4:
        status = "page"
    elif burn >= 6.0:
        status = "hold_release"
    elif burn >= 1.0:
        status = "ticket"
    else:
        status = "healthy"
    return {
        "name": name,
        "target": target,
        "error_ratio": round(error_ratio, 6),
        "burn_rate": burn,
        "remaining_error_budget_pct": remaining_budget_pct(error_ratio, target),
        "status": status,
        "owner": owner,
    }


def build_slo_report(root: str | Path) -> dict:
    root = Path(root)
    observability = read_json(root / "reports" / "serving_observability.json")
    canary = read_json(root / "reports" / "canary_decision.json")
    latency_p95 = float(observability.get("latency_ms", {}).get("p95", 999.0))
    shadow_delta = float(observability.get("shadow", {}).get("mean_abs_delta", 1.0))
    challenger_traffic = int(observability.get("route_counts", {}).get("challenger", 0))
    slos = [
        _slo("serving_availability", target=0.995, error_ratio=float(observability.get("error_rate", 1.0)), owner="serving"),
        _slo("serving_latency_p95", target=0.99, error_ratio=0.0 if latency_p95 <= 35.0 else 1.0, owner="serving"),
        _slo("shadow_score_parity", target=0.95, error_ratio=0.0 if shadow_delta <= 0.12 else 1.0, owner="ml-platform"),
        _slo("canary_receives_traffic", target=0.99, error_ratio=0.0 if challenger_traffic > 0 else 1.0, owner="release-manager"),
    ]
    max_burn = max(item["burn_rate"] for item in slos)
    if max_burn >= 14.4:
        action = "rollback_and_page"
    elif max_burn >= 6.0:
        action = "hold_canary"
    elif max_burn >= 1.0:
        action = "ticket_before_promote"
    elif canary.get("passed"):
        action = "allow_progressive_rollout"
    else:
        action = "hold_canary"
    report = {
        "platform": "kserve-model-serving-platform",
        "policy": {
            "window": "30d",
            "multiwindow_burn_rates": [
                {"name": "fast_page", "short_window": "5m", "long_window": "1h", "burn_rate": 14.4, "budget_consumed": "2%"},
                {"name": "slow_page", "short_window": "30m", "long_window": "6h", "burn_rate": 6.0, "budget_consumed": "5%"},
                {"name": "ticket", "short_window": "6h", "long_window": "3d", "burn_rate": 1.0, "budget_consumed": "10%"},
            ],
        },
        "slos": slos,
        "max_burn_rate": max_burn,
        "recommended_action": action,
        "release_freeze": action in {"rollback_and_page", "hold_canary"},
    }
    write_json(root / "reports" / "slo_error_budget.json", report)
    return report
