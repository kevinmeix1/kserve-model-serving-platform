from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from prometheus_client import Counter, Gauge

from .io import read_json
from .registry import aliases as read_aliases
from .registry import registry_root, seed_registry
from .runtime_contract import MODEL_NAME
from .serving import deploy


LOGGER = logging.getLogger("kserve_model_platform.api")

MODEL_READY = Gauge(
    "kserve_model_ready",
    "Whether the model router has a valid last-known-good snapshot.",
    ("model_name",),
)
SNAPSHOT_RELOADS = Counter(
    "kserve_model_snapshot_reloads_total",
    "Atomic model snapshot reload attempts.",
    ("model_name", "outcome"),
)


@dataclass(frozen=True)
class Settings:
    state_root: Path = Path(".local")
    model_name: str = MODEL_NAME
    inference_timeout_seconds: float = 0.25
    queue_timeout_seconds: float = 0.05
    max_concurrency: int = 32
    max_batch_size: int = 128
    max_request_bytes: int = 262_144
    reload_interval_seconds: float = 0.25
    shutdown_grace_seconds: float = 5.0
    idempotency_claim_ttl_seconds: float = 30.0
    bootstrap_state: bool = True

    def __post_init__(self) -> None:
        if self.inference_timeout_seconds <= 0:
            raise ValueError("inference timeout must be positive")
        if self.queue_timeout_seconds <= 0:
            raise ValueError("queue timeout must be positive")
        if (
            self.max_concurrency <= 0
            or self.max_batch_size <= 0
            or self.max_request_bytes <= 0
        ):
            raise ValueError(
                "concurrency, batch size, and request size limits must be positive"
            )
        if self.reload_interval_seconds < 0:
            raise ValueError("reload interval cannot be negative")
        if self.shutdown_grace_seconds <= 0:
            raise ValueError("shutdown grace period must be positive")
        if self.idempotency_claim_ttl_seconds <= self.inference_timeout_seconds:
            raise ValueError("idempotency claim TTL must exceed the inference timeout")

    @classmethod
    def from_env(cls) -> Settings:
        bootstrap = os.getenv("SERVING_BOOTSTRAP_STATE", "true").strip().lower()
        return cls(
            state_root=Path(os.getenv("SERVING_STATE_ROOT", ".local")),
            model_name=os.getenv("SERVING_MODEL_NAME", MODEL_NAME),
            inference_timeout_seconds=float(
                os.getenv("INFERENCE_TIMEOUT_SECONDS", "0.25")
            ),
            queue_timeout_seconds=float(
                os.getenv("INFERENCE_QUEUE_TIMEOUT_SECONDS", "0.05")
            ),
            max_concurrency=int(os.getenv("INFERENCE_MAX_CONCURRENCY", "32")),
            max_batch_size=int(os.getenv("INFERENCE_MAX_BATCH_SIZE", "128")),
            max_request_bytes=int(os.getenv("INFERENCE_MAX_REQUEST_BYTES", "262144")),
            reload_interval_seconds=float(
                os.getenv("MODEL_RELOAD_INTERVAL_SECONDS", "0.25")
            ),
            shutdown_grace_seconds=float(
                os.getenv("INFERENCE_SHUTDOWN_GRACE_SECONDS", "5.0")
            ),
            idempotency_claim_ttl_seconds=float(
                os.getenv("IDEMPOTENCY_CLAIM_TTL_SECONDS", "30.0")
            ),
            bootstrap_state=bootstrap in {"1", "true", "yes", "on"},
        )


@dataclass(frozen=True)
class ModelSnapshot:
    generation: str
    champion: str
    challenger: str | None
    challenger_percent: int
    shadow_enabled: bool
    models: dict[str, dict]
    loaded_at: str


class SnapshotUnavailable(RuntimeError):
    pass


class IdempotencyConflict(RuntimeError):
    pass


class IdempotencyInProgress(RuntimeError):
    pass


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bootstrap_runtime(root: Path) -> None:
    alias_path = registry_root(root) / "aliases.json"
    deployment_path = root / "deployments" / "kserve_state.json"
    if not alias_path.exists():
        seed_registry(root)
    if not deployment_path.exists():
        deploy(root, challenger_percent=10, shadow=True)


def load_snapshot(root: Path, *, bootstrap: bool) -> ModelSnapshot:
    if bootstrap:
        _bootstrap_runtime(root)

    deployment_path = root / "deployments" / "kserve_state.json"
    alias_path = registry_root(root) / "aliases.json"
    if not deployment_path.exists() or not alias_path.exists():
        raise SnapshotUnavailable("registry aliases or deployment state are missing")

    before = read_aliases(root)
    deployment = read_json(deployment_path)
    after = read_aliases(root)
    if before != after:
        raise SnapshotUnavailable("registry aliases changed while loading a snapshot")
    if deployment.get("status") != "Ready" or deployment.get("protocol") != "v2":
        raise SnapshotUnavailable("deployment is not ready for the V2 protocol")
    if deployment.get("champion") != after.get("champion") or deployment.get(
        "challenger"
    ) != after.get("challenger"):
        raise SnapshotUnavailable(
            "registry aliases and deployment state are not converged"
        )

    traffic = deployment.get("traffic", {})
    champion_percent = int(traffic.get("champion", 0))
    challenger_percent = int(traffic.get("challenger", 0))
    if champion_percent + challenger_percent != 100:
        raise SnapshotUnavailable("traffic weights must total 100")
    if not 0 <= challenger_percent <= 100:
        raise SnapshotUnavailable("challenger traffic must be between 0 and 100")

    versions = [after.get("champion"), after.get("challenger")]
    models: dict[str, dict] = {}
    for version in versions:
        if not version:
            continue
        model_path = registry_root(root) / "versions" / str(version) / "model.json"
        if not model_path.exists():
            raise SnapshotUnavailable(f"model artifact is missing: {version}")
        model = read_json(model_path)
        if model.get("version") != version:
            raise SnapshotUnavailable(f"model artifact version mismatch: {version}")
        models[str(version)] = model

    champion = str(after.get("champion") or "")
    if not champion or champion not in models:
        raise SnapshotUnavailable("champion alias does not resolve to a model")

    generation_payload = {
        "aliases": {
            "champion": after.get("champion"),
            "challenger": after.get("challenger"),
        },
        "deployment": {
            "champion": champion,
            "challenger": after.get("challenger"),
            "traffic": traffic,
            "shadow_enabled": bool(deployment.get("shadow_enabled")),
            "protocol": deployment.get("protocol"),
        },
        "model_hashes": {
            version: canonical_hash(model) for version, model in models.items()
        },
    }
    return ModelSnapshot(
        generation=canonical_hash(generation_payload)[:16],
        champion=champion,
        challenger=after.get("challenger"),
        challenger_percent=challenger_percent,
        shadow_enabled=bool(deployment.get("shadow_enabled")),
        models=models,
        loaded_at=utc_iso(),
    )


class SnapshotManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.RLock()
        self._snapshot: ModelSnapshot | None = None
        self._last_check = 0.0
        self._last_reload_error: str | None = None

    @property
    def last_reload_error(self) -> str | None:
        with self._lock:
            return self._last_reload_error

    def get(self, *, force: bool = False) -> ModelSnapshot:
        with self._lock:
            now = time.monotonic()
            if (
                not force
                and self._snapshot is not None
                and now - self._last_check < self.settings.reload_interval_seconds
            ):
                return self._snapshot
            self._last_check = now
            try:
                candidate = load_snapshot(
                    self.settings.state_root,
                    bootstrap=self.settings.bootstrap_state,
                )
            except (OSError, ValueError, SnapshotUnavailable) as exc:
                self._last_reload_error = str(exc)
                SNAPSHOT_RELOADS.labels(self.settings.model_name, "failed").inc()
                LOGGER.warning(
                    "model_snapshot_reload_failed",
                    extra={"error": str(exc)},
                )
                if self._snapshot is not None:
                    return self._snapshot
                MODEL_READY.labels(self.settings.model_name).set(0)
                raise SnapshotUnavailable(str(exc)) from exc

            if (
                self._snapshot is None
                or self._snapshot.generation != candidate.generation
            ):
                self._snapshot = candidate
                SNAPSHOT_RELOADS.labels(self.settings.model_name, "applied").inc()
                LOGGER.info(
                    "model_snapshot_applied",
                    extra={
                        "generation": candidate.generation,
                        "champion": candidate.champion,
                        "challenger": candidate.challenger,
                    },
                )
            else:
                SNAPSHOT_RELOADS.labels(self.settings.model_name, "unchanged").inc()
            self._last_reload_error = None
            MODEL_READY.labels(self.settings.model_name).set(1)
            return self._snapshot

    def readiness(self) -> bool:
        try:
            self.get(force=True)
        except SnapshotUnavailable:
            return False
        return True


class PredictionLedger:
    def __init__(self, path: Path, *, claim_ttl_seconds: float = 30.0) -> None:
        if claim_ttl_seconds <= 0:
            raise ValueError("claim TTL must be positive")
        self.path = path
        self.claim_ttl_seconds = claim_ttl_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS inference_requests (
                    request_id TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    model_generation TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS inference_claims (
                    request_id TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    model_generation TEXT NOT NULL,
                    owner_token TEXT NOT NULL,
                    lease_expires_at REAL NOT NULL,
                    claimed_at TEXT NOT NULL
                )
                """
            )

    def stats(self, *, recent_limit: int = 8) -> dict[str, Any]:
        """Return bounded, payload-free evidence for the operator console."""
        if recent_limit < 0 or recent_limit > 100:
            raise ValueError("recent limit must be between 0 and 100")
        with self._connect() as connection:
            completed = int(
                connection.execute(
                    "SELECT COUNT(*) FROM inference_requests"
                ).fetchone()[0]
            )
            active_claims = int(
                connection.execute(
                    "SELECT COUNT(*) FROM inference_claims WHERE lease_expires_at > ?",
                    (time.time(),),
                ).fetchone()[0]
            )
            rows = connection.execute(
                """
                SELECT request_id, model_generation, created_at
                FROM inference_requests
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (recent_limit,),
            ).fetchall()
        return {
            "completed_requests": completed,
            "active_claims": active_claims,
            "journal_mode": "WAL",
            "recent": [dict(row) for row in rows],
        }

    @staticmethod
    def _replay(response_json: str) -> dict:
        response = json.loads(response_json)
        parameters = dict(response.get("parameters") or {})
        parameters["idempotent_replay"] = True
        response["parameters"] = parameters
        return response

    def resolve(
        self,
        request_id: str,
        request_digest: str,
        model_generation: str,
        compute: Callable[[], dict],
    ) -> tuple[dict, bool]:
        owner_token = uuid.uuid4().hex
        now = time.time()
        lease_expires_at = now + self.claim_ttl_seconds
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT request_hash, response_json FROM inference_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if existing is not None:
                if existing["request_hash"] != request_digest:
                    raise IdempotencyConflict(
                        "request id was already used with a different payload"
                    )
                return self._replay(existing["response_json"]), True

            claim = connection.execute(
                """
                SELECT request_hash, owner_token, lease_expires_at
                FROM inference_claims
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
            if claim is not None and claim["request_hash"] != request_digest:
                raise IdempotencyConflict(
                    "request id is executing with a different payload"
                )
            if claim is not None and float(claim["lease_expires_at"]) > now:
                raise IdempotencyInProgress(
                    "request id is still executing; retry after the current lease"
                )
            if claim is None:
                connection.execute(
                    """
                    INSERT INTO inference_claims (
                        request_id, request_hash, model_generation,
                        owner_token, lease_expires_at, claimed_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request_id,
                        request_digest,
                        model_generation,
                        owner_token,
                        lease_expires_at,
                        utc_iso(),
                    ),
                )
            else:
                connection.execute(
                    """
                    UPDATE inference_claims
                    SET model_generation = ?, owner_token = ?,
                        lease_expires_at = ?, claimed_at = ?
                    WHERE request_id = ?
                    """,
                    (
                        model_generation,
                        owner_token,
                        lease_expires_at,
                        utc_iso(),
                        request_id,
                    ),
                )

        try:
            response = compute()
        except Exception:
            self._release_claim(request_id, owner_token)
            raise
        response_json = json.dumps(response, sort_keys=True, separators=(",", ":"))
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT request_hash, response_json FROM inference_requests WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                if existing is not None:
                    connection.execute(
                        "DELETE FROM inference_claims WHERE request_id = ? AND owner_token = ?",
                        (request_id, owner_token),
                    )
                    if existing["request_hash"] != request_digest:
                        raise IdempotencyConflict(
                            "request id was already used with a different payload"
                        )
                    return self._replay(existing["response_json"]), True

                claim = connection.execute(
                    "SELECT owner_token FROM inference_claims WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                if claim is None or claim["owner_token"] != owner_token:
                    raise IdempotencyInProgress(
                        "request execution lease changed before completion"
                    )
                connection.execute(
                    """
                    INSERT INTO inference_requests (
                        request_id, request_hash, response_json, model_generation, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        request_id,
                        request_digest,
                        response_json,
                        model_generation,
                        utc_iso(),
                    ),
                )
                connection.execute(
                    "DELETE FROM inference_claims WHERE request_id = ? AND owner_token = ?",
                    (request_id, owner_token),
                )
        except Exception:
            self._release_claim(request_id, owner_token)
            raise
        return response, False

    def _release_claim(self, request_id: str, owner_token: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM inference_claims WHERE request_id = ? AND owner_token = ?",
                (request_id, owner_token),
            )
