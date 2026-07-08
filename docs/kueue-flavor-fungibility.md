# Kueue Flavor Fungibility

`make flavor-fungibility` writes `.local/reports/flavor_fungibility_plan.json` and pairs it with `kubernetes/kueue-flavor-fungibility.yaml`.

## What It Shows

- `ResourceFlavor` objects for on-demand serving, spot analysis, reserved L4 GPU, and spot L4 GPU capacity.
- `ClusterQueue.spec.flavorFungibility.whenCanBorrow: TryNextFlavor`.
- `ClusterQueue.spec.flavorFungibility.whenCanPreempt: TryNextFlavor`.
- Explicit `flavorFungibility.preference: BorrowingOverPreemption`.
- Different flavor order for online serving, GPU canary analysis, and synthetic load.

## Production Notes

Serving platforms should not let shadow analysis or synthetic load steal hot-path capacity just because the first flavor is full. Flavor fungibility gives Kueue a better search order: try the next ResourceFlavor before borrowing quota or preempting admitted work.

The serving project uses a stability-first order for online route smoke checks, a GPU fallback order for explainers, and a spot-first order for load tests. That makes the trade-off visible: live routes optimize reliability, load tests optimize cost, and canary explainers stay off the hot path.

## References

- Kueue ClusterQueue: <https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/>
- Kueue ResourceFlavor: <https://kueue.sigs.k8s.io/docs/concepts/resource_flavor/>
- Kueue FlavorFungibility API: <https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta1/#flavorfungibility>
