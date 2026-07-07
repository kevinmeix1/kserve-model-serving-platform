# Advanced Rollout Control Plane

This repo now includes a rollout planner in `src/kserve_model_platform/rollout_control.py`.

## Operator Workflow

- Run `make demo` to deploy, simulate traffic, and collect canary metrics.
- Run `make plan-rollout` to generate `reports/rollout_control_plan.json`.
- Inspect the recommended action: `advance`, `hold`, `promote`, or `rollback`.

## What The Planner Uses

- KServe champion/challenger traffic split.
- P95 latency and shadow prediction delta.
- Wilson upper confidence bound for observed error rate.
- Minimum challenger sample requirements.
- KServe patch shape and Gateway API weights for the next step.

## Production Signal

The planner avoids promoting on a deceptively clean but tiny sample. It requires enough challenger traffic and uses a confidence bound before recommending the next canary percentage.
