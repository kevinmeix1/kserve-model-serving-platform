# DRA Advanced Device Sharing For KServe

`make advanced-device-sharing` writes `.local/reports/advanced_device_sharing_plan.json` and pairs it with `kubernetes/dra-advanced-device-sharing.yaml`.

## What It Shows

- DRA prioritized device alternatives for challenger predictors and profiling jobs.
- Partitionable devices for shadow analysis instead of whole-device reservations.
- Consumable capacity examples for bounded GPU memory during shadow comparison.
- Device binding conditions that delay scheduler binding until fabric-attached accelerator setup is ready.

## Production Notes

Serving releases need accelerator fallback without hiding what happened. The selected alternative should be part of the release evidence, especially when a canary falls back from shared L4 to MIG profiling or CPU shadow scoring.

Partitionable devices and consumable capacity reduce waste for shadow analysis, while binding conditions prevent large-model profiling from producing promotion evidence before the device is prepared. A binding failure keeps the champion route in place.

## References

- Kubernetes v1.36 DRA update: <https://kubernetes.io/blog/2026/05/07/kubernetes-v1-36-dra-136-updates/>
- Kubernetes Dynamic Resource Allocation: <https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/>
- Kubernetes DRA consumable capacity: <https://kubernetes.io/blog/2025/09/18/kubernetes-v1-34-dra-consumable-capacity/>
