from __future__ import annotations

from pathlib import Path

from .io import write_json


def _read_all(repo_root: Path) -> tuple[str, list[Path]]:
    files = []
    chunks = []
    for folder in ["airflow", "kubernetes", "gitops", "docs", "src", ".github"]:
        base = repo_root / folder
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in {".ini", ".py", ".yaml", ".yml", ".md"}:
                files.append(path)
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks), files


def _line_count(paths: list[Path], name_fragment: str) -> int:
    total = 0
    for path in paths:
        if name_fragment in path.name:
            total += len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    return total


def _present(content: str, *needles: str) -> bool:
    return any(needle in content for needle in needles)


def build_orchestration_scorecard(
    root: str | Path,
    *,
    repo_root: str | Path | None = None,
    project: str,
) -> dict:
    root = Path(root)
    repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
    content, files = _read_all(repo_root)
    enterprise_dag_lines = max(
        _line_count(files, "enterprise"),
        _line_count(files, "progressive"),
        _line_count(files, "control_plane"),
    )
    checks = [
        ("enterprise_airflow_dag", enterprise_dag_lines >= 120, f"largest advanced DAG has {enterprise_dag_lines} lines"),
        ("dynamic_task_mapping", ".expand(" in content, "Airflow mapped tasks create runtime fanout"),
        ("task_groups", "task_group" in content, "TaskGroups separate quality, capacity, release, and incident phases"),
        ("dataset_outlets", _present(content, "outlets=[", "Dataset("), "Dataset outlets expose asset-aware lineage"),
        ("kubernetes_pod_operator", "KubernetesPodOperator" in content, "Airflow tasks run as isolated Kubernetes pods"),
        ("branching_and_trigger_rules", _present(content, "BranchPythonOperator") and _present(content, "TriggerRule"), "Release and recovery paths branch explicitly"),
        ("pools_priority_retries", _present(content, "pool=") and _present(content, "priority_weight"), "Airflow pools and priority weights protect scarce capacity"),
        ("kueue_admission", _present(content, "ClusterQueue", "kueue.x-k8s.io"), "Kueue queues gate batch and release work"),
        ("kuberay_elastic_jobs", _present(content, "RayJob", "RayService", "RayCluster") and _present(content, "enableInTreeAutoscaling", "elastic-job"), "KubeRay workloads scale serving transforms and canary analysis inside Kueue admission"),
        ("inference_gateway_extension", _present(content, "InferencePool", "endpointPickerRef") and _present(content, "InferenceObjective", "inference.networking.k8s.io/v1"), "Gateway API Inference Extension adds model-aware endpoint picking"),
        ("airflow_deadline_alerts", _present(content, "deadline_alert_plan.json", "Deadline Alerts") and _present(content, "AIRFLOW__CALLBACKS__CALLBACK_EXECUTION_TIMEOUT"), "Airflow 3 Deadline Alerts cover rollout queue, shadow warmup, route convergence, and rollback windows"),
        ("opencost_finops", _present(content, "cost_observability_report.json", "OpenCost", "node_gpu_hourly_cost") and _present(content, "KServeCostPerThousandPredictionsHigh"), "OpenCost and Prometheus budget alerts attribute serving, shadow, canary, route, and GPU explainer spend"),
        ("kueue_elastic_workloads", _present(content, "elastic_workload_plan.json", "ElasticJobsViaWorkloadSlices") and _present(content, "workload-slice-name", "JobSet"), "Kueue Workload Slices and JobSet support elastic shadow analysis, GPU explainer bursts, and rollback capacity recovery"),
        ("indexed_job_resilience", _present(content, "indexed_job_resilience_plan.json", "backoffLimitPerIndex", "podFailurePolicy") and _present(content, "successPolicy", "airflow backfill create"), "Indexed Jobs use per-shard retry budgets, success policy, pod failure policy, and bounded Airflow rollout recovery"),
        ("provisioning_admission_checks", _present(content, "provisioning_admission_plan.json", "ProvisioningRequestConfig", "kueue.x-k8s.io/provisioning-request") and _present(content, "online_predictor_excluded", "check-capacity.autoscaling.x-k8s.io"), "Kueue ProvisioningRequest admission confirms physical capacity for serving analysis while online predictors stay outside batch queues"),
        ("multikueue_dispatch", _present(content, "multikueue_dispatch_plan.json", "MultiKueueConfig", "MultiKueueCluster") and _present(content, "onlineServingBoundary", "status.clusterName"), "Kueue MultiKueue dispatch covers shadow replay, rollback smoke, GPU explainers, worker status sync, and online serving boundaries"),
        ("kserve_model_cache", _present(content, "model_cache_plan.json", "LocalModelNamespaceCache", "LocalModelNodeGroup") and _present(content, "oci://", "ModelDownloaded"), "KServe LocalModel cache and modelcar OCI storage gate canary and rollback cold-start risk"),
        ("airflow_dag_bundle_versioning", _present(content, "dag_bundle_versioning_plan.json", "GitDagBundle", "dag_bundle_config_list") and _present(content, "rerun_with_latest_version=False", "rerun_with_latest_version = False"), "Airflow 3 GitDagBundle versioning preserves rollout code across canary reruns, route replay, and incident recovery"),
        ("airflow_asset_partitioning", _present(content, "asset_partitioning_plan.json", "PartitionedAssetTimetable", "CronPartitionTimetable") and _present(content, "dag_run.partition_key", "StartOfHourMapper"), "Airflow 3.2 asset partitioning scopes KServe canary telemetry, route decisions, and rollback smoke to aligned partitions"),
        ("airflow_multi_team_readiness", _present(content, "multi_team_readiness_plan.json", "team_name", "multi_team = True") and _present(content, "AssetAccessControl", "airflow triggerer --team-name"), "Airflow multi-team preview readiness isolates serving DAG bundles, pools, triggerers, secrets, executors, and asset events"),
        ("airflow_event_driven_assets", _present(content, "event_driven_assets_plan.json", "AssetWatcher", "BaseEventTrigger") and _present(content, "shared_stream_key", "AssetAlias"), "Airflow 3 event-driven assets trigger KServe rollouts from model, router, and route events"),
        ("pod_resource_envelopes", _present(content, "pod_resource_envelope_plan.json", "PodLevelResources", "schedulingGates") and _present(content, "scheduler_pending_pods", "PodSchedulingReadiness"), "Kubernetes pod-level resource envelopes and scheduling gates prevent canary, shadow, and rollback scheduler churn"),
        ("kueue_cohort_fair_sharing", _present(content, "cohort_fair_sharing_plan.json", "AdmissionFairSharing", "preemptionStrategies") and _present(content, "borrowingLimit", "lendingLimit", "fairSharing"), "Kueue Fair Sharing and Admission Fair Sharing protect online serving while canary analysis borrows idle quota"),
        ("kueue_flavor_fungibility", _present(content, "flavor_fungibility_plan.json", "flavorFungibility", "TryNextFlavor") and _present(content, "BorrowingOverPreemption", "ResourceFlavor"), "Kueue ResourceFlavor fallback avoids premature borrowing or preemption across serving, analysis, and GPU pools"),
        ("kueue_pending_workload_visibility", _present(content, "pending_workload_visibility_plan.json", "VisibilityOnDemand", "pendingworkloads") and _present(content, "kueue_admission_wait_time_seconds", "kueue_cluster_queue_resource_pending"), "Kueue VisibilityOnDemand exposes pending serving-analysis workloads, route-smoke queue position, and admission-wait alerts"),
        ("kubernetes_workload_aware_scheduling", _present(content, "workload_aware_scheduling_plan.json", "scheduling.k8s.io/v1alpha2", "kind: PodGroup") and _present(content, "WorkloadWithJob", "completionMode: Indexed", "ResourceClaimTemplate"), "Kubernetes v1.36 Workload and PodGroup APIs prepare shadow replay, route conformance, and rollback smoke jobs for atomic gang scheduling, topology constraints, DRA ResourceClaims, and workload-aware preemption"),
        ("runtime_security_userns_kubelet_authz", _present(content, "runtime_security_plan.json", "hostUsers: false", "KubeletFineGrainedAuthz") and _present(content, "nodes/metrics", "nodes/stats", "ValidatingAdmissionPolicy"), "Kubernetes v1.36 user namespaces and fine-grained kubelet authorization reduce host and kubelet blast radius for KServe telemetry"),
        ("control_plane_freshness_diagnostics", _present(content, "control_plane_diagnostics_plan.json", "/statusz", "/flagz") and _present(content, "KServeRouteControllerCacheStale", "KubeletPSIMemoryStallHigh", "NativeHistogramMetrics"), "Kubernetes v1.36 controller staleness, ComponentStatusz, ComponentFlagz, PSI, and native histogram readiness protect KServe route automation from stale control-plane state"),
        ("memory_qos_tiered_protection", _present(content, "memory_qos_plan.json", "MemoryQoS", "TieredReservation") and _present(content, "memory.high", "memory.low", "KServeMemoryQoSPSIPressureHigh"), "Kubernetes v1.36 Memory QoS tiered protection keeps router and champion inference protected while canaries and shadow jobs yield under memory pressure"),
        ("hpa_scale_to_zero_external_metrics", _present(content, "hpa_scale_to_zero_plan.json", "HPAScaleToZero", "minReplicas: 0") and _present(content, "type: External", "type: Object", "KServeScaleToZeroWakeupFailed"), "Kubernetes v1.36 HPA scale-to-zero is limited to async serving helpers with Object or External wake metrics and explicit cold-start budgets"),
        ("suspended_job_resource_mutation", _present(content, "suspended_job_resources_plan.json", "MutablePodResourcesForSuspendedJobs", "suspend: true") and _present(content, "ValidatingAdmissionPolicy", "KServeSuspendedJobResizeStale"), "Kubernetes v1.36 suspended Job resource mutation right-sizes queued KServe analysis Jobs before unsuspend without rewriting active route probes"),
        ("dra_resource_health_status", _present(content, "resource_health_status_plan.json", "ResourceHealthStatus", "allocatedResourcesStatus") and _present(content, "DeviceTaintRule", "kube_resourceclaim_status_devices"), "Kubernetes v1.36 DRA ResourceHealthStatus, ResourceClaim device status, and DeviceTaintRule quarantine protect KServe canaries"),
        ("dra_advanced_device_sharing", _present(content, "advanced_device_sharing_plan.json", "DRAPrioritizedList", "DRAPartitionableDevices") and _present(content, "DRAConsumableCapacity", "DRADeviceBindingConditions"), "DRA prioritized alternatives, partitionable devices, consumable capacity, and binding conditions reduce KServe accelerator waste"),
        ("dra_admin_access_diagnostics", _present(content, "admin_access_diagnostics_plan.json", "DRAAdminAccess", "adminAccess: true") and _present(content, "resource.kubernetes.io/admin-access", "mlops-serving-dra-admin"), "Kubernetes v1.36 DRA AdminAccess diagnostics inspect in-use KServe devices while traffic stays pinned to the last good revision"),
        ("kubernetes_inplace_resize", _present(content, "inplace_resize_plan.json", "InPlaceOrRecreate", "PodResizePending") and _present(content, "pods/resize", "PodResizeInProgress"), "Kubernetes in-place Pod resize and pod-level resource resize protect KServe canaries from disruptive resource changes"),
        ("event_driven_scaling", _present(content, "ScaledObject", "ScaledJob"), "KEDA ScaledObjects or ScaledJobs react to operational backlog"),
        ("horizontal_autoscaling", "HorizontalPodAutoscaler" in content, "HPA rules keep workers and services elastic"),
        ("opentelemetry", _present(content, "opentelemetry-collector", "OpenTelemetry"), "OTel collector config captures runtime traces and metrics"),
        ("gitops_promotion", _present(content, "Argo CD", "Argo Rollouts", "gitops"), "GitOps promotion evidence links release state to deployment control"),
        ("supply_chain_provenance", _present(content, "ClusterImagePolicy") and _present(content, "actions/attest@v4"), "Sigstore and GitHub attestations protect generated artifacts"),
    ]
    passed = [name for name, ok, _ in checks if ok]
    gaps = [name for name, ok, _ in checks if not ok]
    score = round(100 * len(passed) / len(checks), 1)
    report = {
        "project": project,
        "generated_at": "2026-07-07T00:00:00Z",
        "score": score,
        "passed_count": len(passed),
        "total_count": len(checks),
        "passed": gaps == [],
        "checks": [
            {"name": name, "passed": ok, "evidence": evidence}
            for name, ok, evidence in checks
        ],
        "gaps": gaps,
        "research_basis": [
            "Airflow dynamic task mapping and task groups for runtime fanout and maintainability",
            "OpenLineage provider patterns for Airflow DAG lineage and inter-DAG visibility",
            "Kueue, KEDA, and HPA for Kubernetes admission control and adaptive capacity",
            "KubeRay with Kueue for elastic serving transforms and distributed canary analysis",
            "Gateway API Inference Extension for model-aware routing and endpoint picker fallback",
            "Airflow 3 Deadline Alerts as the replacement for legacy SLA callbacks",
            "Kubernetes PodLevelResources and Pod Scheduling Readiness gates for scheduler-efficient serving rollout pods",
            "Kueue Fair Sharing and Admission Fair Sharing for serving cohort scheduling fairness",
            "Kueue FlavorFungibility for ResourceFlavor fallback before borrowing or preempting online-serving capacity",
            "Kueue VisibilityOnDemand pending workload APIs for route-smoke, shadow-analysis, and load-test triage",
            "Kubernetes v1.36 Workload-Aware Scheduling with scheduling.k8s.io/v1alpha2 Workload/PodGroup, WorkloadWithJob, topology constraints, and PodGroup-scoped DRA ResourceClaims",
            "Kubernetes v1.36 user namespaces GA with pod.spec.hostUsers=false and fine-grained kubelet API authorization GA using nodes/metrics, nodes/stats, nodes/healthz, and nodes/pods instead of nodes/proxy",
            "Kubernetes v1.36 controller staleness mitigation, ComponentStatusz, ComponentFlagz, PSI metrics, and native histogram readiness",
            "Kubernetes v1.36 Memory QoS tiered protection with memoryReservationPolicy=TieredReservation, memory.min, memory.low, memory.high, PSI metrics, and kernel-version guardrails",
            "Kubernetes v1.36 HPA scale-to-zero for Object or External metrics with HPAScaleToZero feature gate and serving-path cold-start guardrails",
            "Kubernetes v1.36 MutablePodResourcesForSuspendedJobs for queue-controller KServe analysis resource patching before unsuspend",
            "Kubernetes v1.36 DRA ResourceHealthStatus, ResourceClaim status.devices, and DeviceTaintRule quarantine for serving accelerator incidents",
            "Kubernetes DRA prioritized alternatives, partitionable devices, consumable capacity, and device binding conditions for KServe accelerator efficiency",
            "Kubernetes v1.36 DRA AdminAccess for namespace-scoped KServe diagnostics on devices already in use",
            "Kubernetes v1.35 in-place Pod Resize and v1.36 pod-level resource resize for non-disruptive KServe rollout scaling",
            "OpenCost exporter metrics for KServe route, traffic-class, GPU, and cost-per-prediction allocation",
            "Kueue Elastic Workloads with Workload Slices and JobSet integration for dynamic serving-analysis scale changes",
            "Kubernetes Indexed Jobs with backoffLimitPerIndex, successPolicy, podFailurePolicy, and Airflow 3 backfill create controls",
            "Kueue ProvisioningRequest AdmissionChecks for shadow analysis, GPU explainers, and rollback-smoke capacity guarantees",
            "Kueue MultiKueue for manager-to-worker dispatch of serving analysis without queueing live InferenceService predictors",
            "KServe LocalModelCache, LocalModelNodeGroup, and modelcar OCI storage for cold-start control",
            "Airflow 3 DAG Bundles and DAG versioning for reproducible KServe rollout reruns and scheduler-managed backfills",
            "Airflow 3.2 asset partitioning with PartitionedAssetTimetable for partition-aware KServe rollout backfills",
            "Airflow multi-team preview mode for serving-owned DAG Bundles, team-scoped resources, triggerers, executors, and asset-event filtering",
            "Airflow 3 AssetWatchers, BaseEventTrigger compatibility, shared-stream polling, and conditional serving asset expressions",
            "GitHub artifact attestations, SLSA provenance, and Sigstore policy-controller for supply-chain integrity",
        ],
        "next_actions": [
            "Run this scorecard in CI whenever DAGs or manifests change.",
            "Keep large fanout behind Airflow pools and Kueue quotas before increasing parallelism.",
            "Promote policy-controller from warn to enforce only after all images are digest-pinned and attested.",
        ],
    }
    write_json(root / "reports" / "orchestration_scorecard.json", report)
    return report
