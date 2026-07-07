from __future__ import annotations

import hashlib
from pathlib import Path

from .io import write_json


def _hex(value: str, length: int) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def span(trace_id: str, name: str, *, parent: str | None, service: str, duration_ms: float, attributes: dict) -> dict:
    span_id = _hex(f"{trace_id}:{name}:{service}", 16)
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent,
        "name": name,
        "service": service,
        "kind": "internal",
        "status": "ok",
        "duration_ms": duration_ms,
        "attributes": attributes,
    }


def build_trace_report(root: str | Path) -> dict:
    root = Path(root)
    trace_id = _hex("credit-risk-serving-trace", 32)
    request = span(trace_id, "gateway.route", parent=None, service="gateway-api", duration_ms=1.4, attributes={"route": "credit-risk-weighted-route"})
    kserve = span(trace_id, "kserve.predict", parent=request["span_id"], service="kserve", duration_ms=23.0, attributes={"protocol": "v2"})
    model = span(trace_id, "model.score", parent=kserve["span_id"], service="sklearnserver", duration_ms=7.5, attributes={"model": "credit-risk"})
    shadow = span(trace_id, "shadow.compare", parent=kserve["span_id"], service="sklearnserver", duration_ms=6.2, attributes={"comparison": "champion_vs_challenger"})
    monitor = span(trace_id, "canary.evaluate", parent=kserve["span_id"], service="airflow", duration_ms=12.0, attributes={"policy": "wilson_error_bound"})
    spans = [request, kserve, model, shadow, monitor]
    report = {
        "trace_id": trace_id,
        "span_count": len(spans),
        "critical_path_ms": round(request["duration_ms"] + kserve["duration_ms"] + model["duration_ms"], 2),
        "root_service": "gateway-api",
        "leaf_service": "airflow",
        "spans": spans,
    }
    write_json(root / "reports" / "trace_report.json", report)
    return report
