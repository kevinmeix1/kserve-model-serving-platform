from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.types import ASGIApp, Receive, Scope, Send

from .runtime_contract import SERVER_VERSION
from .runtime_state import (
    IdempotencyConflict,
    ModelSnapshot,
    PredictionLedger,
    Settings,
    SnapshotManager,
    SnapshotUnavailable,
    canonical_hash,
)
from .v2_protocol import (
    InferenceRequest,
    ModelVersionNotFound,
    ProtocolError,
    infer,
    model_metadata,
    output_values,
)


LOGGER = logging.getLogger("kserve_model_platform.api")

REQUESTS = Counter(
    "kserve_inference_requests_total",
    "Open Inference requests received by outcome and route.",
    ("model_name", "route", "outcome"),
)
REQUEST_DURATION = Histogram(
    "kserve_inference_request_duration_seconds",
    "End-to-end Open Inference request duration.",
    ("model_name", "outcome"),
    buckets=(0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)
IN_FLIGHT = Gauge(
    "kserve_inference_requests_in_flight",
    "Inference requests currently executing.",
    ("model_name",),
)
IDEMPOTENT_REPLAYS = Counter(
    "kserve_inference_idempotent_replays_total",
    "Inference requests served from the durable idempotency ledger.",
    ("model_name",),
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
        }
        for key in [
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "generation",
            "champion",
            "challenger",
            "error",
        ]:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def configure_logging() -> None:
    if not any(getattr(handler, "kserve_json", False) for handler in LOGGER.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        handler.kserve_json = True  # type: ignore[attr-defined]
        LOGGER.addHandler(handler)
    LOGGER.setLevel(os.getenv("LOG_LEVEL", "WARNING").upper())
    LOGGER.propagate = False


configure_logging()


class RequestBodyTooLarge(RuntimeError):
    pass


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                response = JSONResponse(
                    status_code=400,
                    content={"error": "invalid Content-Length header"},
                )
                await response(scope, receive, send)
                return
            if declared_size > self.max_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={"error": "request body exceeds the configured limit"},
                    headers={"Connection": "close"},
                )
                await response(scope, receive, send)
                return

        received_bytes = 0

        async def limited_receive() -> dict:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_bytes:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            response = JSONResponse(
                status_code=413,
                content={"error": "request body exceeds the configured limit"},
                headers={"Connection": "close"},
            )
            await response(scope, receive, send)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    manager = SnapshotManager(settings)
    ledger = PredictionLedger(settings.state_root / "api" / "idempotency.sqlite3")
    concurrency = asyncio.Semaphore(settings.max_concurrency)

    app = FastAPI(
        title="KServe Credit Risk Runtime",
        version=SERVER_VERSION,
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=settings.max_request_bytes,
    )
    app.state.settings = settings
    app.state.snapshot_manager = manager
    app.state.ledger = ledger

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc.detail)},
            headers=exc.headers or {},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = [
            {
                "location": ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": "request schema validation failed",
                "details": errors,
            },
        )

    @app.middleware("http")
    async def request_context(request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.correlation_id = correlation_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        response.headers["X-Request-ID"] = correlation_id
        response.headers["Server-Timing"] = f"app;dur={duration_ms}"
        response.headers["Cache-Control"] = "no-store"
        LOGGER.info(
            "http_request_completed",
            extra={
                "request_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    def snapshot_or_503(*, force: bool = False) -> ModelSnapshot:
        try:
            return manager.get(force=force)
        except SnapshotUnavailable as exc:
            raise HTTPException(
                status_code=503,
                detail=f"model snapshot unavailable: {exc}",
            ) from exc

    def check_model_name(model_name: str) -> None:
        if model_name != settings.model_name:
            raise HTTPException(
                status_code=404,
                detail=f"model is not loaded: {model_name}",
            )

    def metadata_or_404(
        model_name: str,
        snapshot: ModelSnapshot,
        model_version: str | None = None,
    ) -> dict:
        try:
            return model_metadata(model_name, snapshot, model_version)
        except ModelVersionNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/dashboard", status_code=307)

    @app.get("/dashboard", include_in_schema=False)
    async def dashboard() -> FileResponse:
        path = settings.state_root / "reports" / "kserve_serving_dashboard.html"
        if not path.exists():
            raise HTTPException(
                status_code=404,
                detail="run the demo to generate the dashboard",
            )
        return FileResponse(path, media_type="text/html")

    @app.get("/v2")
    async def server_metadata() -> dict:
        return {
            "name": "kserve-model-serving-platform",
            "version": SERVER_VERSION,
            "extensions": [
                "parameters",
                "durable-idempotency",
                "atomic-model-snapshot",
            ],
        }

    @app.get("/v2/health/live")
    async def server_live() -> dict:
        return {"live": True}

    @app.get("/v2/health/ready")
    async def server_ready() -> Response:
        ready = manager.readiness()
        return JSONResponse(
            status_code=200 if ready else 503,
            content={"ready": ready},
        )

    @app.get("/v2/models/{model_name}")
    async def get_model_metadata(model_name: str) -> dict:
        check_model_name(model_name)
        return metadata_or_404(model_name, snapshot_or_503())

    @app.get("/v2/models/{model_name}/versions/{model_version}")
    async def get_model_version_metadata(
        model_name: str,
        model_version: str,
    ) -> dict:
        check_model_name(model_name)
        return metadata_or_404(
            model_name,
            snapshot_or_503(),
            model_version,
        )

    @app.get("/v2/models/{model_name}/ready")
    async def model_ready(model_name: str) -> dict:
        check_model_name(model_name)
        snapshot_or_503(force=True)
        return {"name": model_name, "ready": True}

    @app.get("/v2/models/{model_name}/versions/{model_version}/ready")
    async def model_version_ready(
        model_name: str,
        model_version: str,
    ) -> dict:
        check_model_name(model_name)
        snapshot = snapshot_or_503(force=True)
        if model_version not in snapshot.models:
            raise HTTPException(
                status_code=404,
                detail=f"model version is not loaded: {model_version}",
            )
        return {
            "name": model_name,
            "version": model_version,
            "ready": True,
        }

    async def execute_inference(
        model_name: str,
        body: InferenceRequest,
        request: Request,
        response: Response,
        *,
        model_version: str | None = None,
    ) -> dict:
        check_model_name(model_name)
        inference_id = body.id or request.state.correlation_id
        normalized = body.model_copy(update={"id": inference_id})
        acquired = False
        started = time.perf_counter()
        outcome = "error"
        route = "unknown"
        try:
            await asyncio.wait_for(
                concurrency.acquire(),
                timeout=settings.queue_timeout_seconds,
            )
            acquired = True
        except TimeoutError as exc:
            REQUESTS.labels(model_name, "queue", "overloaded").inc()
            REQUEST_DURATION.labels(model_name, "overloaded").observe(
                time.perf_counter() - started
            )
            raise HTTPException(
                status_code=503,
                detail="inference concurrency limit reached",
                headers={"Retry-After": "1"},
            ) from exc

        IN_FLIGHT.labels(model_name).inc()
        try:
            snapshot = snapshot_or_503()
            request_digest = canonical_hash(
                {
                    "model_name": model_name,
                    "model_version": model_version,
                    "request": normalized.model_dump(
                        mode="json",
                        exclude_none=True,
                    ),
                }
            )

            def compute() -> dict:
                return infer(
                    normalized,
                    request_id=inference_id,
                    snapshot=snapshot,
                    model_name=model_name,
                    requested_version=model_version,
                    max_batch_size=settings.max_batch_size,
                )

            result, replayed = await asyncio.wait_for(
                asyncio.to_thread(
                    ledger.resolve,
                    inference_id,
                    request_digest,
                    snapshot.generation,
                    compute,
                ),
                timeout=settings.inference_timeout_seconds,
            )
            routes = sorted(set(output_values(result, "selected_alias")))
            route = (
                routes[0]
                if len(routes) == 1
                else ("mixed" if routes else "not_returned")
            )
            outcome = "replay" if replayed else "success"
            if replayed:
                IDEMPOTENT_REPLAYS.labels(model_name).inc()

            versions = sorted(set(output_values(result, "model_version")))
            if len(versions) == 1:
                header_version = versions[0]
            elif versions:
                header_version = "mixed"
            else:
                header_version = str(result.get("model_version", "unknown"))
            response.headers["X-Model-Version"] = header_version
            response.headers["X-Snapshot-Generation"] = snapshot.generation
            return result
        except ProtocolError as exc:
            outcome = "rejected"
            route = "validation"
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ModelVersionNotFound as exc:
            outcome = "not_found"
            route = "version"
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except IdempotencyConflict as exc:
            outcome = "conflict"
            route = "idempotency"
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except TimeoutError as exc:
            outcome = "timeout"
            route = "runtime"
            raise HTTPException(
                status_code=504,
                detail="inference deadline exceeded",
            ) from exc
        finally:
            IN_FLIGHT.labels(model_name).dec()
            if acquired:
                concurrency.release()
            REQUESTS.labels(model_name, route, outcome).inc()
            REQUEST_DURATION.labels(model_name, outcome).observe(
                time.perf_counter() - started
            )

    @app.post("/v2/models/{model_name}/infer")
    async def model_infer(
        model_name: str,
        body: InferenceRequest,
        request: Request,
        response: Response,
    ) -> dict:
        return await execute_inference(
            model_name,
            body,
            request,
            response,
        )

    @app.post("/v2/models/{model_name}/versions/{model_version}/infer")
    async def model_version_infer(
        model_name: str,
        model_version: str,
        body: InferenceRequest,
        request: Request,
        response: Response,
    ) -> dict:
        return await execute_inference(
            model_name,
            body,
            request,
            response,
            model_version=model_version,
        )

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    return app


app = create_app()
