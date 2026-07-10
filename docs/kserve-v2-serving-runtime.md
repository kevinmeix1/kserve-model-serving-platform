# KServe V2 Serving Runtime

This repository includes a runnable HTTP data plane instead of treating KServe only as deployment metadata. The server implements the required Open Inference Protocol V2 health, metadata, and inference routes for a batched credit-risk model router.

## What Is Executable

- `src/kserve_model_platform/api.py` owns HTTP transport, deadlines, metrics, and error mapping.
- `src/kserve_model_platform/v2_protocol.py` owns tensor schemas, batch decoding, model metadata, and response construction.
- `src/kserve_model_platform/runtime_state.py` owns atomic model snapshots and the durable idempotency ledger.
- `Dockerfile` builds the same process as a non-root, read-only-root-filesystem-compatible image.
- `compose.yaml` runs the focused `runtime-init` bootstrap, starts the predictor, waits for readiness, and optionally starts Prometheus.
- `kserve/custom-runtime-inferenceservice.yaml` deploys the image as a KServe custom predictor.
- `tools/smoke_serving_api.py` exercises health, metadata, batch inference, durable replay, response headers, and Prometheus metrics over HTTP.

The local model remains deliberately small. The engineering subject is the serving boundary: protocol correctness, release consistency, overload behavior, and operational evidence.

## Protocol Surface

| Endpoint | Responsibility |
| --- | --- |
| `GET /v2` | server name, version, and supported extensions |
| `GET /v2/health/live` | process-level liveness only |
| `GET /v2/health/ready` | fail-closed model snapshot readiness |
| `GET /v2/models/credit-risk-router` | model signature and loaded versions |
| `GET /v2/models/.../ready` | model and version readiness |
| `POST /v2/models/.../infer` | bounded, batched champion/challenger inference |
| `POST /v2/models/.../versions/{version}/infer` | version-pinned inference for rollback and conformance tests |
| `GET /metrics` | low-cardinality Prometheus metrics |

Every input is a one-dimensional tensor with a shared batch dimension. The contract accepts `BYTES`, `FP64`, and `INT64` datatypes and caps batches at 128 rows by default. Unsupported tensors, duplicate names, inconsistent shapes, invalid feature values, and unsupported outputs fail before model invocation.

An ASGI middleware also caps request bodies at 256 KiB before JSON decoding, including chunked bodies. Production ingress limits should be equal to or lower than the application limit.

## Consistent Model Reloads

The runtime does not read aliases and model files independently while scoring a request. It builds an immutable snapshot containing:

- champion and challenger aliases
- traffic weights
- model artifacts and hashes
- a deterministic generation identifier

The loader reads aliases before and after deployment state, verifies registry/deployment convergence, validates model versions, and swaps the snapshot under a lock. If promotion is temporarily half-applied, the process continues with its last-known-good snapshot. A first load without valid state fails readiness and receives no traffic.

This is a local analogue of resolving an MLflow alias to an immutable artifact digest before changing KServe traffic.

## Idempotency And Concurrency

Inference request IDs are persisted in a SQLite WAL ledger with a unique key and canonical payload hash. Reusing the same ID and payload returns the original response, including after a process restart. Reusing the ID with a different payload returns HTTP `409`.

Before scoring, the ledger also writes a single-flight execution claim. A same-ID
retry while that claim is active returns `409`, `Retry-After`, and
`X-Inference-Execution: continuing` without invoking the model again. Claims
carry a lease so a process crash cannot block a request ID forever. After
`IDEMPOTENCY_CLAIM_TTL_SECONDS`, another worker may recover the claim; an expired
owner cannot overwrite the recovery owner's committed response. The TTL must be
longer than the worst expected model execution, not merely the HTTP response
deadline.

The local ledger demonstrates the transaction boundary but is not a multi-pod database. The custom `InferenceService` therefore fixes this implementation at one replica, disables KServe-managed autoscaling in Standard mode, and records the shared-store requirement as a scaling blocker. A production deployment should use a shared low-latency store such as Redis or Postgres, define retention, decide whether idempotency is global or tenant-scoped, and only then raise `maxReplicas` and enable HPA or KEDA.

The server also enforces:

- a bounded in-process concurrency semaphore
- a short queue-wait budget with `503` and `Retry-After`
- a model-execution deadline with `504`, `Retry-After`, and an explicit continuing-execution header; the request-duration metric separately covers the full admitted HTTP path
- one Uvicorn worker per pod so Kubernetes, rather than local process workers, owns horizontal scaling
- JSON access and snapshot-reload logs without request features or customer identifiers

### Deadline And Cancellation Semantics

`asyncio.to_thread()` cannot stop a Python worker that has already begun running.
The runtime therefore shields the worker from the HTTP timeout and retains its
semaphore lease until the worker actually finishes. A timed-out client receives
`X-Inference-Execution: continuing` and must retry with the same request ID. The
SQLite claim rejects retries while work is active, then the response ledger
returns the eventual result.

Releasing the lease at response timeout would make the concurrency gauge and
overload control incorrect while abandoned threads continued to consume CPU.
The runtime instead exposes:

- `kserve_inference_detached_workers{model_name,reason}`
- `kserve_inference_detached_completions_total{model_name,reason,outcome}`

Client disconnects use the same lease path. During shutdown, the lifespan hook
waits for detached workers up to `INFERENCE_SHUTDOWN_GRACE_SECONDS`; Kubernetes'
termination grace remains the outer hard bound. This is cooperative accounting,
not forceful computation cancellation. Workloads that require hard cancellation
should use a process boundary or a model runtime with native cancellation.

## Probes And Failure Semantics

The custom `InferenceService` separates three concerns:

- startup checks whether the process has started
- liveness checks only whether the process can respond
- readiness checks whether a coherent model snapshot is available

A registry or deployment convergence error therefore removes the pod from service without causing a restart loop. The process can retain a last-known-good snapshot during a rollout, while a cold pod fails closed until it loads one.

## Run It

Python process:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[serving,test]'
make demo
make api-run
```

From another terminal:

```bash
make api-smoke
```

Container path:

```bash
make compose-up
make api-smoke
open http://127.0.0.1:8080/dashboard
make compose-down
```

Run `docker compose --profile observability up --build --wait` to include Prometheus at `http://127.0.0.1:9090`.

## Verification

`make test-api` covers:

- V2 liveness, readiness, metadata, and batched inference
- idempotent replay after application restart
- conflicting idempotency keys
- version-pinned inference
- atomic last-known-good behavior during promotion
- malformed tensors and batch limits
- fail-closed cold-start readiness
- timeout overrun, retained capacity, overload rejection, and eventual replay
- active single-flight rejection and stale execution-claim recovery
- metrics without customer identifiers

GitHub Actions also builds the container, starts the Compose stack, waits for health, and executes the HTTP smoke test against the running image.

`make package-smoke` builds the wheel without isolation from explicitly pinned
`build`, `setuptools`, and `wheel` versions, imports it under Python's isolated
mode with site packages disabled, and verifies that package metadata, the Python
package version, and the V2 server version agree. The runtime image only uses
these entries as constraints; build tools are not installed into the image.

`make verify-serving-lock` compares the complete contract environment against
`requirements-serving.lock`. It fails on an unpinned transitive distribution,
a missing lock entry, or a version mismatch; `pip check` remains a separate
dependency-compatibility gate.

`make kserve-schema-contract` downloads the pinned KServe `v0.18.0` `InferenceService` CRD and validates the custom runtime manifest against its published OpenAPI schema. This catches attractive-looking but unsupported CRD fields before cluster deployment.

## Production Boundary

This is a production-style portfolio implementation, not a hosted production service. A production rollout would additionally require an external model registry and artifact store, shared idempotency storage before horizontal scaling, authentication and tenant authorization at the gateway, TLS/mTLS, a real image digest in the `InferenceService`, distributed traces, load and soak testing, and a staged cluster promotion process.

## Research Basis

- [KServe Open Inference Protocol V2](https://kserve.github.io/website/docs/concepts/architecture/data-plane/v2-protocol)
- [KServe Python serving runtime SDK](https://kserve.github.io/website/docs/reference/python-runtime-sdk)
- [KServe predictive serving runtimes](https://kserve.github.io/website/docs/model-serving/predictive-inference/frameworks/overview)
- [KServe REST client timeout and retry semantics](https://kserve.github.io/website/docs/reference/inference-client/inference-rest-client)
- [Python 3.12 task cancellation, shielding, and timeouts](https://docs.python.org/3.12/library/asyncio-task.html)
- [Kubernetes liveness, readiness, and startup probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/)
- [Kubernetes pod and endpoint termination flow](https://kubernetes.io/docs/tutorials/services/pods-and-endpoint-termination-flow/)
