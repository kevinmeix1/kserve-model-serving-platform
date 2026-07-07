# Serving Runbook

## Canary Fails

Symptoms:

- `make monitor` returns `"recommended_action": "hold_rollout"`
- `.local/reports/canary_decision.json` has a failed check

Actions:

1. Inspect the failed canary check.
2. For latency failures, check p95 and p99 before increasing traffic.
3. For error rate failures, inspect rejected requests and timeout records.
4. For shadow delta failures, compare champion and challenger scores by product segment.
5. Keep challenger traffic fixed or roll it back to 0 percent until the cause is understood.

## Rollback

Use rollback when a promoted model causes serving issues.

```bash
make rollback
make health
```

The local registry restores `previous_champion` as `champion` and moves the rolled-back model to `challenger`. In Kubernetes, apply `kserve/rollback-patch.yaml` or update the `storageUri` to the previous champion artifact.

## Bad Request Spike

Symptoms:

- error rate increases
- logs contain `status = rejected`
- validation errors include missing, range, or allowed value failures

Actions:

1. Inspect `contracts/prediction_request_contract.yml`.
2. Compare the failing payloads with the contract.
3. Check whether an upstream application deployed a schema change.
4. Add a contract test before accepting any contract change.

## High Latency

Actions:

1. Check KServe pod readiness and autoscaling.
2. Inspect cold starts and request concurrency.
3. Compare champion and challenger latency.
4. Increase min replicas for latency-sensitive services.
5. Add queue latency and model inference latency as separate metrics.

