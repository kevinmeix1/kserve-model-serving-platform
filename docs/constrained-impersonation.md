# Constrained Impersonation

`make constrained-impersonation` writes `.local/reports/constrained_impersonation_plan.json`.

## What It Shows

- Kubernetes v1.36 `ConstrainedImpersonation` beta behavior.
- Separate authorization for the impersonated service account identity and the actions performed while impersonating.
- Serving support and rollback workflows that can inspect KServe/Gateway state without broad route control.
- Audit expectations for `authenticationMetadata.impersonationConstraint`.
- Alerts for legacy broad `impersonate` grants that bypass least-privilege intent.

## Production Notes

Serving debuggers and rollback controllers often need to act through a platform
identity during incidents. Constrained impersonation keeps that safe by requiring
both `impersonate:serviceaccount` on the target service account and
`impersonate-on:serviceaccount:<verb>` on specific KServe or Gateway API
resources.

The result is a narrower support path: read router health, inspect logs, or patch
serving status without inheriting delete or arbitrary rollout authority.

References:

- https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/
- https://kubernetes.io/docs/reference/access-authn-authz/user-impersonation/
