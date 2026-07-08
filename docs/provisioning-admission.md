# Kueue Provisioning Admission

KServe online serving should not wait behind batch queue admission. The production need here is narrower and more useful: canary analysis, shadow replay, rollback smoke tests, and GPU explainers need real capacity before they can produce release evidence.

This project models that boundary with Kueue `AdmissionCheck` plus `ProvisioningRequest`.

## Serving Boundary

- Live `InferenceService` predictor replicas remain controlled by KServe rollout, HPA, and Gateway policy.
- Shadow analysis, batch replay, gateway conformance, rollback smoke tests, and GPU explainers run as queued Jobs.
- Queued jobs reserve Kueue quota first, then wait for the ProvisioningRequest capacity signal.
- Failed provisioning freezes canary promotion instead of silently skipping analysis.

## Admission Flow

1. Airflow starts the serving-analysis wave for a candidate model version.
2. Kueue reserves logical quota in the serving analysis ClusterQueue.
3. The provisioning admission controller creates a `ProvisioningRequest`.
4. Cluster Autoscaler checks whether CPU or GPU nodes can actually be provisioned.
5. Analysis starts only after the AdmissionCheck becomes `Ready`.

## Controls

- `AdmissionCheck` uses `kueue.x-k8s.io/provisioning-request`.
- `ProvisioningRequestConfig` sets `provisioningClassName`, `managedResources`, retry backoff, `podSetMergePolicy`, and `podSetUpdates`.
- `admissionChecksStrategy` scopes provisioning checks to expensive analysis flavors.
- Job annotations set `provreq.kueue.x-k8s.io/maxRunDurationSeconds` and capacity booking lifetime.
- Alerts cover pending admission, retry exhaustion, and expired bookings.

## Interview Talking Point

The subtle production issue is not "can Kubernetes run a Job?" It is whether rollout evidence is trustworthy when shadow analysis cannot obtain capacity. This design makes missing analysis capacity a release-blocking signal while leaving the live serving path isolated.
