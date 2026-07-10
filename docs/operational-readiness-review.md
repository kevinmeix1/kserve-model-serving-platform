# Operational Readiness Review

`make demo` writes `reports/operational_readiness_review.json` as the operator-facing packet for serving releases.

The review aggregates KServe rollout state, canary admission, SLO burn rate, AI inference telemetry, p95/p99 latency budgets, shadow-score parity, and supply-chain provenance. It is designed to explain why a challenger should advance, hold, promote, or roll back.

The packet is intentionally fail-closed. If release admission is missing, canary traffic is not decisioned, the serving SLO is paging, provenance is absent, telemetry lacks route/model fields, or latency budgets fail, the recommended action becomes remediation instead of promotion.

Judge demo talking points:

- The platform can explain a serving decision in terms a reviewer can audit.
- Registry aliases, Gateway route weights, KServe traffic, SLOs, and telemetry are treated as one release surface.
- The packet names the exact generated artifacts to inspect before allowing traffic movement.
