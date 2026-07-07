from __future__ import annotations

import argparse
import json
from pathlib import Path

from .chaos import run_chaos_drill
from .dashboard import render_dashboard
from .io import read_json, write_csv, write_json
from .models import generate_requests
from .monitoring import build_report, evaluate_canary
from .policy_audit import audit_platform_policy
from .registry import aliases as registry_aliases
from .registry import promote_challenger, rollback as rollback_registry, seed_registry
from .rollout_control import build_rollout_plan
from .serving import deploy as deploy_kserve
from .serving import health, predict
from .traceability import build_trace_report


def root_path(output: str | Path) -> Path:
    return Path(output)


def deploy(output: str | Path, *, challenger_percent: int = 10) -> dict:
    root = root_path(output)
    seed_registry(root)
    return deploy_kserve(root, challenger_percent=challenger_percent, shadow=True)


def sample_payload() -> dict:
    return {
        "request_id": "req_live_001",
        "customer_id": "cust_live_001",
        "product": "card",
        "income": 58000,
        "debt_ratio": 0.72,
        "delinquencies": 2,
        "utilization": 0.84,
        "employment_years": 2.4,
    }


def predict_once(output: str | Path) -> dict:
    root = root_path(output)
    if not health(root).get("healthy"):
        deploy(root)
    return predict(root, sample_payload())


def simulate(output: str | Path, *, requests: int = 120) -> dict:
    root = root_path(output)
    if not health(root).get("healthy"):
        deploy(root)
    payloads = generate_requests(requests)
    write_csv(root / "data" / "incoming_requests.csv", payloads)
    responses = [predict(root, payload) for payload in payloads]
    return {
        "request_count": len(payloads),
        "success_count": sum(1 for row in responses if row.get("status") == "success"),
        "rejected_count": sum(1 for row in responses if row.get("status") == "rejected"),
    }


def monitor(output: str | Path) -> dict:
    root = root_path(output)
    if not (root / "logs" / "predictions.jsonl").exists():
        simulate(root)
    report = build_report(root)
    decision = evaluate_canary(report)
    write_json(root / "reports" / "canary_decision.json", decision)
    deployment = read_json(root / "deployments" / "kserve_state.json")
    rollout_plan = build_rollout_plan(root)
    dashboard = render_dashboard(
        root / "reports" / "kserve_serving_dashboard.html",
        deployment=deployment,
        report=report,
        decision=decision,
        aliases=registry_aliases(root),
        rollout_plan=rollout_plan,
    )
    return {"report": report, "decision": decision, "rollout_plan": rollout_plan, "dashboard": str(dashboard)}


def promote(output: str | Path) -> dict:
    root = root_path(output)
    decision_path = root / "reports" / "canary_decision.json"
    if not decision_path.exists():
        monitor(root)
    decision = read_json(decision_path)
    if not decision.get("passed"):
        return {"promoted": False, "reason": "canary_gates_failed", "decision": decision}
    result = promote_challenger(root)
    deploy_kserve(root, challenger_percent=0, shadow=False)
    return result


def rollback(output: str | Path) -> dict:
    root = root_path(output)
    result = rollback_registry(root)
    deploy_kserve(root, challenger_percent=10, shadow=True)
    return result


def demo(output: str | Path) -> dict:
    root = root_path(output)
    deployment = deploy(root, challenger_percent=10)
    simulation = simulate(root, requests=120)
    monitoring = monitor(root)
    policy_audit = audit_platform_policy(Path.cwd(), output_root=root)
    trace_report = build_trace_report(root)
    chaos_drill = run_chaos_drill(root)
    idempotent = predict(root, generate_requests(1)[0])
    return {
        "deployment": deployment,
        "simulation": simulation,
        "canary": monitoring["decision"],
        "rollout_plan": monitoring["rollout_plan"],
        "policy_audit": policy_audit,
        "trace_report": trace_report,
        "chaos_drill": chaos_drill,
        "dashboard": monitoring["dashboard"],
        "idempotent_replay": idempotent.get("idempotent_replay", False),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KServe model serving platform")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in [
        "demo",
        "deploy",
        "predict",
        "simulate",
        "monitor",
        "promote",
        "rollback",
        "health",
        "plan-rollout",
        "policy-audit",
        "trace-report",
        "chaos-drill",
    ]:
        cmd = sub.add_parser(command)
        cmd.add_argument("--output", default=".local")
        if command in {"deploy", "simulate"}:
            cmd.add_argument("--requests", type=int, default=120)
    args = parser.parse_args(argv)
    if args.command == "demo":
        print(json.dumps(demo(args.output), indent=2, sort_keys=True))
    elif args.command == "deploy":
        print(json.dumps(deploy(args.output), indent=2, sort_keys=True))
    elif args.command == "predict":
        print(json.dumps(predict_once(args.output), indent=2, sort_keys=True))
    elif args.command == "simulate":
        print(json.dumps(simulate(args.output, requests=args.requests), indent=2, sort_keys=True))
    elif args.command == "monitor":
        print(json.dumps(monitor(args.output), indent=2, sort_keys=True))
    elif args.command == "promote":
        print(json.dumps(promote(args.output), indent=2, sort_keys=True))
    elif args.command == "rollback":
        print(json.dumps(rollback(args.output), indent=2, sort_keys=True))
    elif args.command == "health":
        print(json.dumps(health(args.output), indent=2, sort_keys=True))
    elif args.command == "plan-rollout":
        print(json.dumps(build_rollout_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "policy-audit":
        print(json.dumps(audit_platform_policy(Path.cwd(), output_root=args.output), indent=2, sort_keys=True))
    elif args.command == "trace-report":
        print(json.dumps(build_trace_report(args.output), indent=2, sort_keys=True))
    elif args.command == "chaos-drill":
        print(json.dumps(run_chaos_drill(args.output), indent=2, sort_keys=True))
    return 0
