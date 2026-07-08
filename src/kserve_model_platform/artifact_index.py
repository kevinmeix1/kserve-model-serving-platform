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
        ("Performance Budget", "performance_budget.json", "p95/p99 latency, error-rate, canary-volume, and shadow-delta gates with rollback actions."),
        ("Queue Simulation", "queue_simulation.json", "Kueue quota, serving priority, GPU, Airflow pool, and rollback preemption simulation."),
        ("Release Admission", "release_admission_decision.json", "Fail-closed canary admission record combining rollout, SLO, queue, governance, and provenance evidence."),
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
