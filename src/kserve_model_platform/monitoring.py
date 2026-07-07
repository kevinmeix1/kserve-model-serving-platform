from __future__ import annotations

from pathlib import Path

from .io import read_jsonl, write_json


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(int(round((len(ordered) - 1) * pct)), len(ordered) - 1)
    return round(ordered[index], 4)


def build_report(root: str | Path) -> dict:
    root = Path(root)
    rows = read_jsonl(root / "logs" / "predictions.jsonl")
    successes = [row for row in rows if row.get("status") == "success"]
    errors = [row for row in rows if row.get("status") != "success"]
    latencies = [float(row.get("latency_ms", 0)) for row in successes]
    route_counts: dict[str, int] = {}
    model_counts: dict[str, int] = {}
    shadow_deltas = []
    scores = []
    for row in successes:
        alias = row.get("selected_alias", "unknown")
        version = row.get("model_version", "unknown")
        route_counts[alias] = route_counts.get(alias, 0) + 1
        model_counts[version] = model_counts.get(version, 0) + 1
        scores.append(float(row.get("risk_score", 0)))
        if row.get("shadow_score") is not None:
            shadow_deltas.append(abs(float(row["risk_score"]) - float(row["shadow_score"])))
    report = {
        "request_count": len(rows),
        "success_count": len(successes),
        "error_count": len(errors),
        "error_rate": round(len(errors) / max(len(rows), 1), 4),
        "latency_ms": {
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
        },
        "route_counts": route_counts,
        "model_counts": model_counts,
        "risk_score": {
            "mean": round(sum(scores) / max(len(scores), 1), 6),
            "high_risk_share": round(sum(1 for value in scores if value >= 0.70) / max(len(scores), 1), 4),
        },
        "shadow": {
            "comparison_count": len(shadow_deltas),
            "mean_abs_delta": round(sum(shadow_deltas) / max(len(shadow_deltas), 1), 6),
            "max_abs_delta": round(max(shadow_deltas, default=0.0), 6),
        },
        "recent_predictions": successes[-20:],
    }
    write_json(root / "reports" / "serving_observability.json", report)
    return report


def evaluate_canary(report: dict, *, p95_limit_ms: float = 35.0, max_error_rate: float = 0.01, max_shadow_delta: float = 0.12) -> dict:
    checks = [
        {
            "name": "latency_p95",
            "passed": report.get("latency_ms", {}).get("p95", 999) <= p95_limit_ms,
            "observed": report.get("latency_ms", {}).get("p95"),
            "threshold": p95_limit_ms,
        },
        {
            "name": "error_rate",
            "passed": report.get("error_rate", 1) <= max_error_rate,
            "observed": report.get("error_rate"),
            "threshold": max_error_rate,
        },
        {
            "name": "shadow_delta",
            "passed": report.get("shadow", {}).get("mean_abs_delta", 1) <= max_shadow_delta,
            "observed": report.get("shadow", {}).get("mean_abs_delta"),
            "threshold": max_shadow_delta,
        },
        {
            "name": "challenger_receives_traffic",
            "passed": report.get("route_counts", {}).get("challenger", 0) > 0,
            "observed": report.get("route_counts", {}).get("challenger", 0),
            "threshold": ">0",
        },
    ]
    decision = {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "recommended_action": "promote_challenger" if all(check["passed"] for check in checks) else "hold_rollout",
    }
    return decision
