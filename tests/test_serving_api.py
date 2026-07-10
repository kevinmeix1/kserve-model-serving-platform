from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kserve_model_platform.registry import promote_challenger
from kserve_model_platform.serving import deploy

try:
    from fastapi.testclient import TestClient

    from kserve_model_platform.api import Settings, create_app
except (
    ImportError
):  # The dependency-light demo suite can run without the serving extra.
    TestClient = None
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

    def test_v2_health_metadata_and_batch_inference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with TestClient(self.app_for(Path(tmp))) as client:
                self.assertEqual(client.get("/v2/health/live").json(), {"live": True})
                self.assertEqual(client.get("/v2/health/ready").json(), {"ready": True})

                metadata = client.get("/v2/models/credit-risk-router")
                response = client.post(
                    "/v2/models/credit-risk-router/infer",
                    json=inference_payload(),
                )

                self.assertEqual(metadata.status_code, 200)
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
