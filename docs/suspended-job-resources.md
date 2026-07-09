# Suspended Job Resource Mutation

`make suspended-job-resources` writes `.local/reports/suspended_job_resources_plan.json`.

This project uses Kubernetes v1.36 `MutablePodResourcesForSuspendedJobs` for queued
KServe-adjacent Jobs such as shadow replay, route conformance, and GPU explainers.
The feature allows resource requests and limits to be changed while a Job is still
`spec.suspend: true`, before Pods start or resume.

The serving guardrail is deliberately strict: active router smoke checks and champion
rollback probes are excluded. They should use in-place Pod resize where appropriate,
or replacement Jobs, because the suspended Job feature is not for rewriting active
KServe traffic probes.

Operational gates before unsuspend:

- Kueue quota fit is recorded for CPU, memory, GPU, and extended resources.
- KServe model cache readiness is current for GPU explainers.
- HTTPRoute observedGeneration matches the desired route generation.
- Airflow pool slots are available for route conformance work.
- The route remains pinned to a known champion if the queued Job is delayed.

References:

- https://kubernetes.io/blog/2026/04/27/kubernetes-v1-36-mutable-pod-resources-for-suspended-jobs/
- https://kubernetes.io/docs/concepts/workloads/controllers/job/
