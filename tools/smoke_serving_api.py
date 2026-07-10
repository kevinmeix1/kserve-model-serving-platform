from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request


def request_json(
    base_url: str, path: str, *, payload: dict | None = None
) -> tuple[int, dict, dict]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Request-ID": "smoke-correlation-001",
        },
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read()), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read()), dict(exc.headers)


def inference_payload(request_id: str = "smoke-inference-001") -> dict:
    values = {
        "customer_id": ("BYTES", ["customer-smoke-001", "customer-smoke-002"]),
        "product": ("BYTES", ["card", "mortgage"]),
        "income": ("FP64", [58000.0, 112000.0]),
        "debt_ratio": ("FP64", [0.72, 0.28]),
        "delinquencies": ("INT64", [2, 0]),
        "utilization": ("FP64", [0.84, 0.31]),
        "employment_years": ("FP64", [2.4, 8.2]),
    }
    return {
        "id": request_id,
        "inputs": [
            {"name": name, "shape": [2], "datatype": datatype, "data": data}
            for name, (datatype, data) in values.items()
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-test the KServe V2-compatible runtime"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args()

    live_status, live, _ = request_json(args.base_url, "/v2/health/live")
    ready_status, ready, _ = request_json(args.base_url, "/v2/health/ready")
    metadata_status, metadata, _ = request_json(
        args.base_url, "/v2/models/credit-risk-router"
    )
    first_status, first, first_headers = request_json(
        args.base_url,
        "/v2/models/credit-risk-router/infer",
        payload=inference_payload(),
    )
    first_headers = {key.lower(): value for key, value in first_headers.items()}
    replay_status, replay, _ = request_json(
        args.base_url,
        "/v2/models/credit-risk-router/infer",
        payload=inference_payload(),
    )
    with urllib.request.urlopen(
        f"{args.base_url.rstrip('/')}/metrics", timeout=5
    ) as response:
        metrics = response.read().decode("utf-8")

    assertions = {
        "live": live_status == 200 and live == {"live": True},
        "ready": ready_status == 200 and ready == {"ready": True},
        "metadata": metadata_status == 200
        and metadata.get("name") == "credit-risk-router",
        "batch_inference": first_status == 200
        and first.get("parameters", {}).get("batch_size") == 2,
        "model_header": bool(first_headers.get("x-model-version")),
        "durable_replay": replay_status == 200
        and replay.get("parameters", {}).get("idempotent_replay") is True,
        "metrics": "kserve_inference_requests_total" in metrics,
    }
    report = {
        "passed": all(assertions.values()),
        "checks": assertions,
        "model_version": first_headers.get("x-model-version"),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
