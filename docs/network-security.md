# Network Security

The serving platform uses a default-deny model for runtime traffic. The important boundary is that predictors accept traffic only from the gateway, while rollout operations remain owned by the Airflow rollout controller.

Run:

```bash
make network-security
```

The report is written to `.local/reports/network_security.json`.

## Controls

- Default deny for ingress and egress.
- Explicit DNS egress allow.
- Gateway ingress to champion and challenger predictors on the serving port.
- Rollout-controller egress to the KServe API for traffic weight and rollback changes.
- Istio strict mTLS and AuthorizationPolicy for serving calls.
- Direct predictor-to-predictor calls denied by default.

## References

Kubernetes NetworkPolicy starts from default allow until policies isolate pods. Default deny egress needs a DNS exception. Istio `PeerAuthentication` can require strict mutual TLS, and Gateway API separates north-south routing ownership from application backends.
