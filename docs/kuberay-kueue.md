# KubeRay and Kueue

`make kuberay-plan` writes `.local/reports/kuberay_capacity_plan.json` and pairs it with `kubernetes/kuberay-kueue-workloads.yaml`.

## What It Shows

- A `RayService` for bursty feature transform and explanation work around KServe predictors.
- A Kueue-admitted `RayJob` for parallel shadow and canary evaluation.
- Elastic worker bounds so Ray cannot grow beyond admitted serving capacity.
- GPU explanation work treated as opportunistic and preemptible.
- Rollback behavior that routes back through the baseline KServe transformer.

## Production Notes

KServe should keep real-time predictor pods lean. Ray is useful for bursty Python-heavy transforms, parallel canary analysis, and offline explanation generation, but it still needs admission control. This project models RayService/RayJob capacity as an explicit serving dependency with Kueue queues, Airflow readiness checks, and fallback routing.

References: Kueue RayJob integration, Ray KubeRay with Kueue, and RayService operations.
