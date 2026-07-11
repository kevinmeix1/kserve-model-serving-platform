from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from kserve_model_platform.registry import promote_challenger
from kserve_model_platform.serving import deploy

try:
    from fastapi.testclient import TestClient

    from kserve_model_platform.api import Settings, create_app
    from kserve_model_platform.runtime_state import PredictionLedger
except (
    ImportError
):  # The dependency-light demo suite can run without the serving extra.
    TestClient = None
    PredictionLedger = None
    Settings = None
    create_app = None


def inference_payload(
    request_id: str = "api-request-001", *, income: float = 58000.0
) -> dict:
    values = {
        "customer_id": ("BYTES", ["customer-001", "customer-002"]),
        "product": ("BYTES", ["card", "mortgage"]),
        "income": ("FP64", [income, 112000.0]),
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


def output_data(response: dict, name: str) -> list:
    return next(
        output["data"] for output in response["outputs"] if output["name"] == name
    )


@unittest.skipIf(
    TestClient is None, "install the serving and test extras to run API contracts"
)
class ServingApiTest(unittest.TestCase):
    def app_for(self, root: Path, *, bootstrap: bool = True):
        return create_app(
            Settings(
                state_root=root,
                bootstrap_state=bootstrap,
                reload_interval_seconds=0,
                inference_timeout_seconds=1,
            )
        )

    def test_execution_claim_ttl_must_exceed_response_deadline(self) -> None:
        with self.assertRaisesRegex(ValueError, "claim TTL must exceed"):
            Settings(
                inference_timeout_seconds=1.0,
                idempotency_claim_ttl_seconds=0.5,
            )

    def test_v2_health_metadata_and_batch_inference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with TestClient(self.app_for(Path(tmp))) as client:
                self.assertEqual(client.get("/v2/health/live").json(), {"live": True})
                self.assertEqual(client.get("/v2/health/ready").json(), {"ready": True})

                server = client.get("/v2")
                metadata = client.get("/v2/models/credit-risk-router")
                response = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload(),
                )

                self.assertEqual(metadata.status_code, 200)
                self.assertIn(
                    "deadline-safe-idempotent-retry",
                    server.json()["extensions"],
                )
                self.assertEqual(
                    {item["name"] for item in metadata.json()["inputs"]},
                    {
                        "customer_id",
                        "product",
                        "income",
                        "debt_ratio",
                        "delinquencies",
                        "utilization",
                        "employment_years",
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["parameters"]["batch_size"], 2)
                self.assertEqual(len(output_data(response.json(), "risk_score")), 2)
                self.assertTrue(response.headers["x-model-version"])
                self.assertTrue(response.headers["x-snapshot-generation"])

    def test_console_status_exposes_bounded_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with TestClient(self.app_for(Path(tmp))) as client:
                initial = client.get("/api/console/status")
                prediction = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("console-evidence"),
                )
                status = client.get("/api/console/status")

            self.assertEqual(initial.status_code, 200)
            self.assertEqual(initial.json()["ledger"]["completed_requests"], 0)
            self.assertEqual(prediction.status_code, 200)
            self.assertEqual(status.status_code, 200)
            payload = status.json()
            self.assertTrue(payload["ready"])
            self.assertEqual(payload["ledger"]["completed_requests"], 1)
            self.assertEqual(payload["ledger"]["active_claims"], 0)
            self.assertEqual(
                payload["ledger"]["recent"][0]["request_id"],
                "console-evidence",
            )
            self.assertNotIn("response_json", payload["ledger"]["recent"][0])
            self.assertEqual(payload["runtime"]["detached_workers"], 0)
            self.assertTrue(payload["snapshot"]["generation"])

    def test_idempotency_survives_application_restart_and_rejects_key_reuse(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with TestClient(self.app_for(root)) as first_client:
                first = first_client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("persistent-key"),
                )
            with TestClient(self.app_for(root)) as restarted_client:
                replay = restarted_client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("persistent-key"),
                )
                conflict = restarted_client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("persistent-key", income=91000.0),
                )

            self.assertFalse(first.json()["parameters"]["idempotent_replay"])
            self.assertTrue(replay.json()["parameters"]["idempotent_replay"])
            self.assertEqual(first.json()["outputs"], replay.json()["outputs"])
            self.assertEqual(conflict.status_code, 409)
            self.assertIn("different payload", conflict.json()["error"])
            self.assertTrue((root / "api" / "idempotency.sqlite3").exists())

    def test_timeout_reserves_capacity_until_detached_worker_completes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(
                Settings(
                    state_root=root,
                    max_concurrency=1,
                    inference_timeout_seconds=0.02,
                    queue_timeout_seconds=0.01,
                    shutdown_grace_seconds=1.0,
                    reload_interval_seconds=0,
                )
            )
            original_resolve = app.state.ledger.resolve
            started = threading.Event()
            release = threading.Event()
            call_lock = threading.Lock()
            call_count = 0

            def delay_first_call(*args):
                nonlocal call_count
                with call_lock:
                    call_count += 1
                    should_delay = call_count == 1
                if should_delay:
                    started.set()
                    if not release.wait(timeout=1.0):
                        raise RuntimeError("test worker was not released")
                return original_resolve(*args)

            app.state.ledger.resolve = delay_first_call
            with TestClient(app) as client:
                timed_out = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("eventual-result"),
                )
                self.assertTrue(started.is_set())
                self.assertEqual(timed_out.status_code, 504)
                self.assertEqual(
                    timed_out.headers["x-inference-execution"],
                    "continuing",
                )
                self.assertEqual(timed_out.headers["retry-after"], "1")
                self.assertEqual(len(app.state.detached_workers), 1)

                overloaded = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("must-wait-for-capacity"),
                )
                self.assertEqual(overloaded.status_code, 503)

                release.set()
                deadline = time.monotonic() + 1.0
                while app.state.detached_workers and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertFalse(app.state.detached_workers)

                replay = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("eventual-result"),
                )
                metrics = client.get("/metrics").text

            self.assertEqual(replay.status_code, 200)
            self.assertTrue(replay.json()["parameters"]["idempotent_replay"])
            self.assertIn("kserve_inference_detached_completions_total", metrics)
            self.assertIn('reason="timeout"', metrics)

    def test_active_request_claim_blocks_duplicate_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(
                Settings(
                    state_root=Path(tmp),
                    max_concurrency=2,
                    inference_timeout_seconds=0.02,
                    queue_timeout_seconds=0.01,
                    shutdown_grace_seconds=1.0,
                    reload_interval_seconds=0,
                )
            )
            original_resolve = app.state.ledger.resolve
            started = threading.Event()
            release = threading.Event()
            compute_lock = threading.Lock()
            compute_calls = 0

            def single_flight_resolve(request_id, digest, generation, compute):
                def delayed_compute():
                    nonlocal compute_calls
                    with compute_lock:
                        compute_calls += 1
                        invocation = compute_calls
                    if invocation == 1:
                        started.set()
                        if not release.wait(timeout=1.0):
                            raise RuntimeError("test worker was not released")
                    return compute()

                return original_resolve(
                    request_id,
                    digest,
                    generation,
                    delayed_compute,
                )

            app.state.ledger.resolve = single_flight_resolve
            with TestClient(app) as client:
                first = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("single-flight"),
                )
                self.assertTrue(started.wait(timeout=1.0))
                self.assertEqual(first.status_code, 504)

                in_progress = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("single-flight"),
                )
                self.assertEqual(in_progress.status_code, 409)
                self.assertIn("still executing", in_progress.json()["error"])
                self.assertEqual(
                    in_progress.headers["x-inference-execution"],
                    "continuing",
                )
                self.assertEqual(compute_calls, 1)

                release.set()
                deadline = time.monotonic() + 1.0
                while app.state.detached_workers and time.monotonic() < deadline:
                    time.sleep(0.01)
                replay = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("single-flight"),
                )

            self.assertEqual(replay.status_code, 200)
            self.assertTrue(replay.json()["parameters"]["idempotent_replay"])
            self.assertEqual(compute_calls, 1)

    def test_stale_request_claim_can_be_recovered_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PredictionLedger(
                Path(tmp) / "ledger.sqlite3",
                claim_ttl_seconds=0.02,
            )
            started = threading.Event()
            release = threading.Event()
            first_result: list[tuple[dict, bool]] = []

            def slow_compute() -> dict:
                started.set()
                if not release.wait(timeout=1.0):
                    raise RuntimeError("test worker was not released")
                return {"winner": "expired-owner"}

            def run_first_owner() -> None:
                first_result.append(
                    ledger.resolve("lease-recovery", "digest", "generation", slow_compute)
                )

            first_owner = threading.Thread(target=run_first_owner)
            first_owner.start()
            self.assertTrue(started.wait(timeout=0.5))
            time.sleep(0.03)
            recovered, replayed = ledger.resolve(
                "lease-recovery",
                "digest",
                "generation",
                lambda: {"winner": "recovery-owner"},
            )
            release.set()
            first_owner.join(timeout=1.0)

            self.assertFalse(first_owner.is_alive())
            self.assertFalse(replayed)
            self.assertEqual(recovered, {"winner": "recovery-owner"})
            self.assertEqual(len(first_result), 1)
            self.assertEqual(first_result[0][0]["winner"], "recovery-owner")
            self.assertTrue(first_result[0][0]["parameters"]["idempotent_replay"])
            self.assertTrue(first_result[0][1])

    def test_version_endpoint_pins_every_row_to_requested_model(self) -> None:
        version = "risk-model-2026-07-15"
        with tempfile.TemporaryDirectory() as tmp:
            with TestClient(self.app_for(Path(tmp))) as client:
                response = client.post(
                    f"/v2/models/credit-risk-router/versions/{version}/infer",
                    json=inference_payload("version-pinned"),
                )
                ready = client.get(
                    f"/v2/models/credit-risk-router/versions/{version}/ready"
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                set(output_data(response.json(), "model_version")), {version}
            )
            self.assertEqual(
                set(output_data(response.json(), "selected_alias")), {"version"}
            )
            self.assertEqual(
                ready.json(),
                {"name": "credit-risk-router", "version": version, "ready": True},
            )

    def test_snapshot_reload_is_atomic_across_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with TestClient(self.app_for(root)) as client:
                before = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("before-promotion"),
                )
                before_generation = before.headers["x-snapshot-generation"]

                promote_challenger(root)
                # The manager keeps the last-known-good snapshot while aliases and deployment differ.
                during = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("during-promotion"),
                )
                deploy(root, challenger_percent=0, shadow=False)
                after = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("after-promotion"),
                )

            self.assertEqual(during.headers["x-snapshot-generation"], before_generation)
            self.assertNotEqual(
                after.headers["x-snapshot-generation"], before_generation
            )
            self.assertEqual(
                set(output_data(after.json(), "model_version")),
                {"risk-model-2026-07-15"},
            )

    def test_contract_rejects_bad_tensor_signature_and_oversized_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(
                Settings(
                    state_root=Path(tmp),
                    reload_interval_seconds=0,
                    max_batch_size=1,
                    inference_timeout_seconds=1,
                )
            )
            with TestClient(app) as client:
                wrong_type = inference_payload("wrong-type")
                for tensor in wrong_type["inputs"]:
                    tensor["shape"] = [1]
                    tensor["data"] = tensor["data"][:1]
                wrong_type["inputs"][2]["datatype"] = "INT64"
                invalid = client.post(
                    "/v2/models/credit-risk-router/infer", json=wrong_type
                )
                oversized = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("oversized"),
                )

            self.assertEqual(invalid.status_code, 422)
            self.assertIn("must use datatype FP64", invalid.json()["error"])
            self.assertEqual(oversized.status_code, 422)
            self.assertIn("exceeds limit", oversized.json()["error"])

    def test_readiness_fails_closed_without_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with TestClient(self.app_for(Path(tmp), bootstrap=False)) as client:
                live = client.get("/v2/health/live")
                ready = client.get("/v2/health/ready")

            self.assertEqual(live.status_code, 200)
            self.assertEqual(ready.status_code, 503)
            self.assertEqual(ready.json(), {"ready": False})

    def test_request_body_limit_runs_before_tensor_decoding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(
                Settings(
                    state_root=Path(tmp),
                    max_request_bytes=512,
                    reload_interval_seconds=0,
                    inference_timeout_seconds=1,
                )
            )
            payload = inference_payload("oversized-body")
            payload["parameters"] = {"padding": "x" * 1024}
            with TestClient(app) as client:
                response = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=payload,
                )

            self.assertEqual(response.status_code, 413)
            self.assertIn("configured limit", response.json()["error"])

    def test_metrics_do_not_include_customer_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with TestClient(self.app_for(Path(tmp))) as client:
                client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload("metrics-request"),
                )
                metrics = client.get("/metrics")

            self.assertEqual(metrics.status_code, 200)
            self.assertIn("kserve_inference_requests_total", metrics.text)
            self.assertNotIn("customer-001", metrics.text)


if __name__ == "__main__":
    unittest.main()
