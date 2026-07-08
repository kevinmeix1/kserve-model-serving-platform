from __future__ import annotations

import html
from pathlib import Path


def _escape(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _breakable(value: object) -> str:
    escaped = _escape(value)
    return escaped.replace("/", "/<wbr>").replace("_", "_<wbr>").replace("-", "-<wbr>")


def render_artifact_index(root: str | Path, *, title: str, description: str, dashboard: str) -> Path:
    root = Path(root)
    cards = [
        ("Serving Dashboard", dashboard, "HTML control-room view for traffic split, canary health, latency, and prediction quality."),
        ("Canary Decision", "canary_decision.json", "Automated rollout gate showing whether the challenger should advance, hold, or roll back."),
        ("Governance Evidence", "governance_evidence_bundle.json", "Model card, approval record, registry aliases, risk register, and reproducibility hashes."),
        ("SLO Error Budget", "slo_error_budget.json", "Availability, latency, error-rate, and prediction-quality burn-rate evidence."),
        ("Supply Chain Evidence", "supply_chain_evidence.json", "Artifact hashes, GitHub attestations, SLSA provenance, and Sigstore policy controls."),
        ("Cloud Migration Plan", "cloud_migration_plan.json", "KServe deployment migration notes for managed Kubernetes and cloud model platforms."),
        ("Disaster Recovery Plan", "disaster_recovery_plan.json", "Backup, restore, registry, and serving failover plan for production inference."),
        ("Accelerator Plan", "accelerator_capacity_plan.json", "GPU, DRA, Kueue, MIG, and time-slicing plan for accelerator-aware serving."),
        ("Device Allocation", "device_allocation_plan.json", "DRA ResourceClaim templates, Kueue coupling, rollback fallback, and device-health guardrails."),
        ("DRA Resource Health", "resource_health_status_plan.json", "Kubernetes v1.36 ResourceHealthStatus, ResourceClaim device status, device quarantine, and KServe rollback policy."),
        ("Topology Placement", "topology_placement_plan.json", "Kueue TAS, LeaderWorkerSet co-location, serving spread constraints, and rollback fallbacks."),
        ("KubeRay Capacity", "kuberay_capacity_plan.json", "RayService transform capacity, Kueue-admitted shadow analysis, GPU explainer fallback, and serving guardrails."),
        ("Inference Gateway", "inference_gateway_plan.json", "Gateway API Inference Extension pool, endpoint picker fallback, traffic priority, and routing signals."),
        ("Semantic Telemetry", "semantic_telemetry_plan.json", "OpenTelemetry semantic attributes, GenAI token/cost fields, Kubernetes correlation, and redaction guardrails."),
        ("Deadline Alerts", "deadline_alert_plan.json", "Airflow 3 rollout queue, shadow warmup, route convergence, and rollback deadline policies."),
        ("Cost Observability", "cost_observability_report.json", "OpenCost serving unit cost, traffic-class budgets, GPU explainer spend, and allocation labels."),
        ("Elastic Workloads", "elastic_workload_plan.json", "Kueue Workload Slices, JobSet shadow analysis, replacement slices, GPU explainers, and rollback quota recovery."),
        ("Indexed Job Resilience", "indexed_job_resilience_plan.json", "Kubernetes Indexed Jobs, per-index retries, success policy, pod failure policy, and bounded Airflow rollout backfills."),
        ("Provisioning Admission", "provisioning_admission_plan.json", "Kueue ProvisioningRequest capacity checks for shadow analysis, rollback smoke, and GPU explainers."),
        ("MultiKueue Dispatch", "multikueue_dispatch_plan.json", "Kueue MultiKueue dispatch for shadow replay, route conformance, rollback smoke, and GPU explainers."),
        ("Model Cache", "model_cache_plan.json", "KServe LocalModel cache, modelcar OCI storage, cache-gated canaries, and rollback preloading."),
        ("DAG Bundle Versioning", "dag_bundle_versioning_plan.json", "Airflow 3 GitDagBundle versioning for progressive rollout reruns, route replay, and serving backfills."),
        ("Event-Driven Assets", "event_driven_assets_plan.json", "Airflow 3 AssetWatchers for challenger registration, KServe router readiness, and Gateway route convergence."),
        ("Pod Resource Envelopes", "pod_resource_envelope_plan.json", "Kubernetes pod-level resources, scheduling gates, KServe cache readiness, and scheduler-churn observability."),
        ("Cohort Fair Sharing", "cohort_fair_sharing_plan.json", "Kueue Fair Sharing, Admission Fair Sharing, serving queue weights, borrowing/lending limits, and preemption guardrails."),
        ("Flavor Fungibility", "flavor_fungibility_plan.json", "Kueue ResourceFlavor fallback, TryNextFlavor policies, explicit borrowing/preemption preference, and serving pool trade-offs."),
        ("Pending Workload Visibility", "pending_workload_visibility_plan.json", "Kueue VisibilityOnDemand, raw pendingworkloads API paths, serving queue triage, and admission-wait alerts."),
        ("Performance Budget", "performance_budget.json", "p95/p99 latency, error-rate, canary-volume, and shadow-delta gates with rollback actions."),
        ("Queue Simulation", "queue_simulation.json", "Kueue quota, serving priority, GPU, Airflow pool, and rollback preemption simulation."),
        ("Release Admission", "release_admission_decision.json", "Fail-closed canary admission record combining rollout, SLO, queue, governance, and provenance evidence."),
        ("Tenant Fairness", "tenancy_fairness_report.json", "Serving tenant quotas, Kueue cohorts, Airflow pools, rollback reservations, and cost labels."),
        ("Workload Identity", "identity_access_report.json", "Keyless serving identities for router, predictor, canary analysis, and registry access."),
        ("Resource Optimization", "resource_optimization.json", "Rightsizing, HPA, VPA, KEDA, and prewarm recommendations for serving workloads."),
        ("Network Security", "network_security.json", "mTLS, network policy, and router-to-predictor access topology for model serving."),
        ("Chaos Drill", "chaos_drill_report.json", "Serving failure-injection scenarios with blast radius and rollback controls."),
        ("GitOps Plan", "gitops_plan.json", "Promotion waves, route gates, rollback commands, and GitOps-controlled serving rollout."),
        ("Orchestration Scorecard", "orchestration_scorecard.json", "Automated scan of advanced Airflow, Kubernetes, lineage, and security controls."),
    ]
    card_html = "\n".join(
        f"""
        <a class="card" href="{_escape(href)}">
          <span class="label">{_escape(label)}</span>
          <strong>{_breakable(href)}</strong>
          <small>{_escape(summary)}</small>
        </a>"""
        for label, href, summary in cards
    )
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(title)} Evidence Index</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --ink: #182132;
      --muted: #5d6777;
      --line: #dce2ec;
      --accent: #0f6b8f;
      --accent-soft: #e6f3f8;
      --shadow: 0 18px 45px rgba(23, 39, 65, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.55;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 48px 24px 56px; }}
    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 28px;
      align-items: end;
      padding-bottom: 28px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0 0 10px; font-size: clamp(2rem, 4vw, 4rem); line-height: 1; letter-spacing: 0; }}
    p {{ margin: 0; color: var(--muted); max-width: 760px; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 36px;
      padding: 0 14px;
      border: 1px solid #9ecfe0;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 0.82rem;
      font-weight: 800;
      text-transform: uppercase;
    }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 28px; }}
    .card {{
      display: flex;
      min-height: 178px;
      flex-direction: column;
      justify-content: space-between;
      gap: 18px;
      padding: 22px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: var(--shadow);
      color: inherit;
      text-decoration: none;
    }}
    .card:hover {{ border-color: #6eb3cc; transform: translateY(-1px); }}
    .label {{ color: var(--accent); font-size: 0.78rem; font-weight: 800; text-transform: uppercase; }}
    strong {{ font-size: 0.96rem; line-height: 1.3; overflow-wrap: break-word; }}
    small {{ color: var(--muted); font-size: 0.9rem; }}
    footer {{ margin-top: 28px; color: var(--muted); font-size: 0.9rem; }}
    @media (max-width: 880px) {{
      header {{ grid-template-columns: 1fr; }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>{_escape(title)}</h1>
        <p>{_escape(description)}</p>
      </div>
      <span class="badge">Demo Evidence</span>
    </header>
    <section class="grid" aria-label="Generated artifacts">
      {card_html}
    </section>
    <footer>Generated by the local demo command. Open the dashboard first, then inspect the JSON evidence behind rollout and reliability decisions.</footer>
  </main>
</body>
</html>
"""
    output = root / "reports" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body, encoding="utf-8")
    return output
