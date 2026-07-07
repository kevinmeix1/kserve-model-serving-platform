# ADR 0001: Explicit Canary Promotion

## Status

Accepted

## Context

Serving monitors can identify a healthy challenger, but automatic promotion can still be risky. Model changes may require product, risk, or compliance approval.

## Decision

The demo separates canary evaluation from promotion. `make monitor` writes a recommended action. `make promote` performs the alias change only when the gates pass.

## Consequences

Benefits:

- The release decision is auditable.
- A failed canary cannot become champion accidentally.
- The project mirrors real change-management workflows.

Trade-offs:

- The demo requires one extra command to complete a promotion.
- Production automation needs a policy layer to decide when recommendations become actions.

