# Memory QoS Tiered Protection

`make memory-qos` writes `.local/reports/memory_qos_plan.json`.

## What It Shows

- Kubernetes v1.36 Memory QoS with `memoryReservationPolicy: TieredReservation`.
- cgroup v2 and kernel guardrails for KServe node pools.
- `memory.min` hard protection for the router and champion predictor.
- `memory.low` soft protection for challenger and shadow-analysis workloads.
- PSI and `memory.high` throttling alerts before latency regressions are blamed on the model.

## Production Notes

Serving systems fail badly when the fallback path is reclaimable. This plan makes the memory hierarchy explicit: the router and champion predictor are Guaranteed, challenger and shadow analysis are Burstable, and ad-hoc debugging stays reclaimable.

The v1.36 update separates throttling from reservation. Enabling `MemoryQoS` turns on `memory.high` throttling, while `TieredReservation` opts into `memory.min` and `memory.low` protection.

## Senior Review Angle

This shows node-level serving reliability judgment: protect rollback-safe inference first, use realistic memory requests for canaries, and rely on PSI plus `memory.high` signals before treating latency as a model regression.

References:

- https://kubernetes.io/blog/2026/04/29/kubernetes-v1-36-memory-qos-tiered-protection/
- https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/
