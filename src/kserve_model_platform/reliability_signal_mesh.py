from __future__ import annotations

import html
from pathlib import Path

from .io import read_json, write_json


REQUIRED_EVIDENCE = [
    ("airflow_assets", "event_driven_assets_plan.json", "Airflow event-driven assets and queued-event recovery"),
    ("semantic_telemetry", "semantic_telemetry_plan.json", "OpenTelemetry resource and signal attributes"),
    ("slo_budget", "slo_error_budget.json", "Multi-window SLO burn-rate release signal"),
    ("queue_admission", "pending_workload_visibility_plan.json", "Kueue pending workload and admission-wait signal"),
    ("release_admission", "release_admission_decision.json", "Fail-closed release or rollback decision"),
    ("readiness_packet", "operational_readiness_review.json", "Operator review packet and readiness score"),
]

SIGNALS = [
    {
        "name": "asset_event_to_dag",
        "layer": "orchestration",
        "source": "Airflow AssetWatcher / queued event",
        "semantic_fields": ["airflow.dag_id", "airflow.run_id", "asset.uri", "asset.partition"],
        "query": 'airflow_asset_event_lag_seconds{project="$project"}',
        "decision": "start DAG only when event payload and asset partition are both present",
    },
    {
        "name": "resource_context",
        "layer": "telemetry",
        "source": "OpenTelemetry resource semantic conventions",
        "semantic_fields": ["service.name", "deployment.environment.name", "k8s.namespace.name", "k8s.pod.name"],
        "query": 'count by (service_name, k8s_namespace_name) (otelcol_receiver_accepted_spans)',
        "decision": "drop or quarantine telemetry that cannot be joined back to a workload owner",
    },
    {
        "name": "queue_pressure",
        "layer": "capacity",
        "source": "Kueue admission, fair sharing, and priority",
        "semantic_fields": ["kueue.cluster_queue", "kueue.local_queue", "kueue.workload_priority", "kueue.weighted_share"],
        "query": "kueue_admission_wait_time_seconds_bucket and kueue_cluster_queue_weighted_share",
        "decision": "reserve rollback and incident work before admitting elastic analysis jobs",
    },
    {
        "name": "slo_burn",
        "layer": "reliability",
        "source": "Prometheus multi-window burn alerts",
        "semantic_fields": ["slo.name", "slo.burn_rate", "error_budget.policy", "release.id"],
        "query": 'slo_error_budget_burn_rate{window=~"5m|1h"}',
        "decision": "freeze promotion when fast burn and slow burn both exceed policy",
    },
    {
        "name": "release_admission",
        "layer": "governance",
        "source": "Fail-closed release controller",
        "semantic_fields": ["release.id", "release.decision", "supply_chain.digest", "ml.model.version"],
        "query": 'release_admission_decision{decision!="advance"}',
        "decision": "move traffic or launch backfill only after evidence hashes match the reviewed packet",
    },
]

EDGES = [
    ("asset_event_to_dag", "resource_context", "asset event starts work that must emit stable resource attributes"),
    ("resource_context", "queue_pressure", "resource labels join telemetry to queue owner and workload priority"),
    ("queue_pressure", "slo_burn", "capacity pressure changes latency, freshness, and recovery burn rate"),
    ("slo_burn", "release_admission", "burn-rate policy controls promotion, rollback, and freeze decisions"),
    ("release_admission", "asset_event_to_dag", "operator replay emits a new guarded asset event"),
]


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _load(root: Path, name: str) -> dict:
    path = root / "reports" / name
    return read_json(path) if path.exists() else {}


def _status(root: Path) -> list[dict]:
    items = []
    for key, file_name, purpose in REQUIRED_EVIDENCE:
        path = root / "reports" / file_name
        payload = read_json(path) if path.exists() else {}
        items.append(
            {
                "key": key,
                "file": file_name,
                "purpose": purpose,
                "present": path.exists(),
                "field_count": len(payload) if isinstance(payload, dict) else 0,
            }
        )
    return items


def _write_html(path: Path, report: dict) -> Path:
    signal_rows = "\n".join(
        f"""
        <article class="signal" data-layer="{_esc(signal['layer'])}">
          <span>{_esc(signal['layer'])}</span>
          <strong>{_esc(signal['name'])}</strong>
          <p>{_esc(signal['decision'])}</p>
          <code>{_esc(signal['query'])}</code>
        </article>"""
        for signal in report["signals"]
    )
    edge_rows = "\n".join(
        f"<li><b>{_esc(edge['from'])}</b><span>{_esc(edge['reason'])}</span><b>{_esc(edge['to'])}</b></li>"
        for edge in report["edges"]
    )
    evidence_rows = "\n".join(
        f"""
        <tr>
          <td>{_esc(item['key'])}</td>
          <td><a href="{_esc(item['file'])}">{_esc(item['file'])}</a></td>
          <td>{'ready' if item['present'] else 'missing'}</td>
          <td>{_esc(item['purpose'])}</td>
        </tr>"""
        for item in report["evidence"]
    )
    field_buttons = "\n".join(f"<button>{_esc(field)}</button>" for field in report["semantic_contract"])
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(report['project'])} Reliability Signal Mesh</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f6f8fb; color: #172033; font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    header {{ background: #0f172a; color: white; padding: 30px 36px; border-bottom: 5px solid #2563eb; }}
    main {{ max-width: 1440px; margin: 0 auto; padding: 24px 36px 44px; }}
    h1 {{ margin: 0; font-size: 31px; line-height: 1.16; }}
    h2 {{ margin: 0 0 12px; font-size: 17px; }}
    header p {{ color: #cbd5e1; max-width: 900px; line-height: 1.5; }}
    .hero, .lower {{ display: grid; grid-template-columns: minmax(280px, .62fr) minmax(0, 1.38fr); gap: 16px; align-items: start; }}
    .panel, .signal {{ background: white; border: 1px solid #d8e0ea; border-radius: 8px; padding: 16px; box-shadow: 0 1px 2px rgba(15, 23, 42, .05); }}
    .score strong {{ display: block; font-size: 50px; line-height: 1; }}
    .score span, .signal span, th {{ color: #64748b; font-size: 12px; font-weight: 850; text-transform: uppercase; }}
    .bar {{ height: 12px; border-radius: 999px; background: #e2e8f0; overflow: hidden; margin: 16px 0; }}
    .bar span {{ display: block; height: 100%; width: calc(var(--value) * 1%); background: #2563eb; }}
    .mesh {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }}
    .signal {{ min-width: 0; min-height: 194px; display: grid; align-content: space-between; }}
    .signal strong {{ display: block; margin-top: 8px; font-size: 15px; overflow-wrap: anywhere; }}
    .signal p {{ margin: 10px 0; color: #475569; font-size: 13px; line-height: 1.42; }}
    code {{ display: block; padding: 9px; border-radius: 6px; background: #eff6ff; color: #1d4ed8; font-size: 12px; overflow-wrap: anywhere; }}
    .lower {{ margin-top: 16px; }}
    ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 9px; }}
    li {{ display: grid; grid-template-columns: minmax(0,.8fr) minmax(0,1.4fr) minmax(0,.8fr); gap: 10px; align-items: center; border: 1px solid #e2e8f0; border-radius: 7px; padding: 10px; background: #fbfdff; }}
    li span, td {{ color: #475569; overflow-wrap: anywhere; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #e2e8f0; font-size: 13px; }}
    a {{ color: #1d4ed8; font-weight: 850; text-decoration: none; overflow-wrap: anywhere; }}
    .buttons {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }}
    button {{ border: 1px solid #cbd5e1; border-radius: 6px; background: white; color: #1d4ed8; padding: 9px 12px; font: inherit; font-size: 13px; font-weight: 850; }}
    @media (max-width: 980px) {{ header, main {{ padding-left: 18px; padding-right: 18px; }} .hero, .lower, .mesh {{ grid-template-columns: 1fr; }} li {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>{_esc(report['project'])} Reliability Signal Mesh</h1>
    <p>{_esc(report['domain'])} control plane that connects asset events, semantic telemetry, queue admission, SLO burn, and fail-closed release decisions.</p>
  </header>
  <main>
    <section class="hero">
      <div class="panel score">
        <span>Mesh readiness</span>
        <strong>{_esc(report['readiness_score'])}%</strong>
        <div class="bar" style="--value:{_esc(report['readiness_score'])}"><span></span></div>
        <p>{_esc(report['status'].replace('_', ' '))}</p>
        <div class="buttons"><a href="{_esc(report['primary_dashboard'])}">Open dashboard</a><a href="reliability_signal_mesh.json">Mesh JSON</a></div>
      </div>
      <div class="mesh">{signal_rows}</div>
    </section>
    <section class="lower">
      <div class="panel"><h2>Causal Signal Edges</h2><ul>{edge_rows}</ul></div>
      <div class="panel"><h2>Evidence Contract</h2><table><thead><tr><th>Signal</th><th>Artifact</th><th>Status</th><th>Purpose</th></tr></thead><tbody>{evidence_rows}</tbody></table><div class="buttons">{field_buttons}</div></div>
    </section>
  </main>
</body>
</html>"""
    path.write_text(body, encoding="utf-8")
    return path


def build_reliability_signal_mesh(
    root: str | Path,
    *,
    project_name: str,
    domain: str,
    primary_dashboard: str,
) -> dict:
    root = Path(root)
    evidence = _status(root)
    present = sum(1 for item in evidence if item["present"])
    readiness_score = round((present / len(evidence)) * 100, 1)
    release = _load(root, "release_admission_decision.json")
    readiness = _load(root, "operational_readiness_review.json")
    report = {
        "project": project_name,
        "domain": domain,
        "generated_at": "2026-07-11T00:00:00Z",
        "status": "ready" if present == len(evidence) else "needs_evidence",
        "readiness_score": readiness_score,
        "primary_dashboard": primary_dashboard,
        "signals": SIGNALS,
        "edges": [{"from": source, "to": target, "reason": reason} for source, target, reason in EDGES],
        "evidence": evidence,
        "release_action": release.get("decision", {}).get("action", release.get("recommended_action", "review_required")),
        "operator_readiness": readiness.get("readiness_score", 0),
        "semantic_contract": sorted({field for signal in SIGNALS for field in signal["semantic_fields"]}),
        "sources": [
            "https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/event-scheduling.html",
            "https://opentelemetry.io/docs/specs/semconv/resource/",
            "https://kueue.sigs.k8s.io/docs/concepts/preemption/",
            "https://kserve.github.io/website/docs/model-serving/predictive-inference/rollout-strategies/canary",
        ],
    }
    write_json(root / "reports" / "reliability_signal_mesh.json", report)
    _write_html(root / "reports" / "reliability_signal_mesh.html", report)
    return report
