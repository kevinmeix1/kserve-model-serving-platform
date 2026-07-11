from __future__ import annotations

import hashlib
import time
from pathlib import Path

from .io import append_jsonl, read_json, read_jsonl, write_json
from .models import risk_band, score, validate_payload
from .registry import aliases, model_by_alias


def request_hash(request_id: str) -> int:
    digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def deploy(root: str | Path, *, challenger_percent: int = 10, shadow: bool = True) -> dict:
    root = Path(root)
    current = aliases(root)
    state = {
        "service_name": "credit-risk-router",
        "namespace": "mlops-serving",
        "status": "Ready",
        "runtime": "kserve-v2-custom-runtime",
        "protocol": "v2",
        "champion": current["champion"],
        "challenger": current["challenger"],
        "traffic": {"champion": 100 - challenger_percent, "challenger": challenger_percent},
        "shadow_enabled": shadow,
        "autoscaling": {"min_replicas": 1, "max_replicas": 5, "target_concurrency": 8},
        "manifest": "kserve/inferenceservice-canary.yaml",
    }
    write_json(root / "deployments" / "kserve_state.json", state)
    return state


def health(root: str | Path) -> dict:
    path = Path(root) / "deployments" / "kserve_state.json"
    if not path.exists():
        return {"healthy": False, "reason": "not_deployed"}
    state = read_json(path)
    return {"healthy": state.get("status") == "Ready", **state}


def _cached_response(root: Path, request_id: str) -> dict | None:
    for record in reversed(read_jsonl(root / "logs" / "predictions.jsonl")):
        if record.get("request_id") == request_id and record.get("status") == "success":
            return {**record, "idempotent_replay": True}
    return None


def route_alias(state: dict, request_id: str) -> str:
    challenger_percent = int(state.get("traffic", {}).get("challenger", 0))
    if state.get("challenger") and request_hash(request_id) < challenger_percent:
        return "challenger"
    return "champion"


def predict(root: str | Path, payload: dict, *, timeout_ms: float = 40.0) -> dict:
    root = Path(root)
    if not health(root).get("healthy"):
        deploy(root)
    state = read_json(root / "deployments" / "kserve_state.json")
    validation = validate_payload(payload)
    started = time.perf_counter()
    request_id = str(payload.get("request_id", "adhoc"))

    if not validation["valid"]:
        response = {
            "request_id": request_id,
            "customer_id": payload.get("customer_id", "unknown"),
            "status": "rejected",
            "errors": validation["errors"],
            "latency_ms": 0.0,
        }
        append_jsonl(root / "logs" / "predictions.jsonl", response)
        return response

    cached = _cached_response(root, request_id)
    if cached:
        return cached

    selected_alias = route_alias(state, request_id)
    model = model_by_alias(root, selected_alias)
    risk_score = score(model, payload)
    shadow_score = None
    if state.get("shadow_enabled") and selected_alias == "champion" and state.get("challenger"):
        shadow_score = score(model_by_alias(root, "challenger"), payload)
    latency_ms = round((time.perf_counter() - started) * 1000, 4)
    if latency_ms > timeout_ms:
        response = {
            "request_id": request_id,
            "customer_id": payload["customer_id"],
            "status": "timeout",
            "selected_alias": selected_alias,
            "model_version": model["version"],
            "latency_ms": latency_ms,
        }
    else:
        response = {
            "request_id": request_id,
            "customer_id": payload["customer_id"],
            "product": payload["product"],
            "status": "success",
            "selected_alias": selected_alias,
            "model_version": model["version"],
            "risk_score": risk_score,
            "risk_band": risk_band(risk_score),
            "shadow_score": shadow_score,
            "latency_ms": latency_ms,
        }
    append_jsonl(root / "logs" / "predictions.jsonl", {**response, "features": payload})
    return response
