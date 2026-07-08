# Accelerator Scheduling

`make accelerator-plan` writes `.local/reports/accelerator_capacity_plan.json` and pairs it with `kubernetes/accelerator-scheduling.yaml`.

The design separates CPU burst capacity, shared L4 GPU capacity, and isolated A100 MIG capacity. Kueue ResourceFlavors model the quota boundary, while the ResourceClaimTemplate sketches the newer Kubernetes Dynamic Resource Allocation path for device-specific claims.

## Production Notes

- Keep Airflow pool slots below Kueue GPU quota so the scheduler cannot over-admit scarce accelerators.
- Use NVIDIA GPU Operator time-slicing only for low-risk non-isolated canary or development workloads.
- Use MIG when memory and fault isolation matter more than raw utilization.
- Prefer KServe concurrency or request-based scaling for GPU inference before trying to scale on noisy GPU utilization metrics.

## Research Basis

- Kubernetes Dynamic Resource Allocation: https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/
- Kueue ResourceFlavors: https://kueue.sigs.k8s.io/docs/concepts/resource_flavor/
- KServe multi-node and multi-GPU inference: https://kserve.github.io/website/docs/model-serving/generative-inference/multi-node
- NVIDIA GPU Operator sharing: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html
