from __future__ import annotations

import html
import json
from pathlib import Path

from .io import read_json, write_json


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _read_optional(path: Path) -> dict:
    return read_json(path) if path.exists() else {}


def _percent(value: object) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def _check_passed(check: dict) -> bool:
    if "passed" in check:
        return bool(check.get("passed"))
    if "status" in check:
        return str(check.get("status")).lower() in {"pass", "passed", "success", "ready"}
    return bool(check)


def _load_evidence(root: Path) -> list[dict]:
    reports = root / "reports"
    selected = [
        "operational_readiness_review.json",
        "release_admission_decision.json",
        "slo_error_budget.json",
        "performance_budget.json",
        "ai_workload_telemetry_plan.json",
        "supply_chain_evidence.json",
        "orchestration_scorecard.json",
        "kserve_canary_readiness_plan.json",
        "cost_observability_report.json",
        "runtime_security_plan.json",
        "control_plane_diagnostics_plan.json",
    ]
    evidence = []
    for name in selected:
        payload = _read_optional(reports / name)
        if not payload:
            continue
        checks = payload.get("checks", [])
        passed = sum(1 for check in checks if isinstance(check, dict) and _check_passed(check))
        total = len(checks) if isinstance(checks, list) else 0
        evidence.append(
            {
                "artifact": name,
                "title": name.replace("_", " ").replace(".json", "").title(),
                "category": _category(name),
                "score": _artifact_score(payload, passed, total),
                "status": _artifact_status(payload, passed, total),
                "detail": _artifact_detail(payload),
            }
        )
    return evidence


def _category(name: str) -> str:
    if "telemetry" in name or "slo" in name or "performance" in name or "cost" in name:
        return "observability"
    if "admission" in name or "canary" in name:
        return "release"
    if "security" in name or "supply" in name:
        return "governance"
    return "operations"


def _artifact_score(payload: dict, passed: int, total: int) -> int:
    if "readiness_score" in payload:
        return _percent(payload.get("readiness_score"))
    if total:
        return _percent(100 * passed / total)
    if payload.get("passed") is not None:
        return 100 if payload.get("passed") else 0
    return 80


def _artifact_status(payload: dict, passed: int, total: int) -> str:
    if payload.get("recommended_action"):
        return str(payload["recommended_action"]).replace("_", " ")
    if total:
        return f"{passed}/{total} checks passed"
    return "evidence captured"


def _artifact_detail(payload: dict) -> str:
    for key in ("summary", "target", "decision", "policy", "recommended_action"):
        value = payload.get(key)
        if value:
            return str(value)[:160]
    return "Open the JSON artifact for full run evidence."


def build_judge_demo_cockpit(
    root: str | Path,
    *,
    project_name: str,
    primary_dashboard: str,
    demo_video: str,
) -> dict:
    root = Path(root)
    reports = root / "reports"
    readiness = _read_optional(reports / "operational_readiness_review.json")
    evidence = _load_evidence(root)
    scenarios = [
        {
            "name": "Release Gate",
            "focus": "release",
            "talk_track": "Show that a production rollout is admitted only when offline gates, SLO burn, queue pressure, and rollback evidence agree.",
        },
        {
            "name": "Observability Drill",
            "focus": "observability",
            "talk_track": "Walk through p95 latency, error budget, cost guardrails, and telemetry coverage before the system promotes traffic.",
        },
        {
            "name": "Governance Review",
            "focus": "governance",
            "talk_track": "Prove that image provenance, runtime policy, identity, and audit evidence are generated as reviewable artifacts.",
        },
        {
            "name": "Operator Handoff",
            "focus": "operations",
            "talk_track": "Close with the runbook path, recovery decision, and the exact files a platform operator would inspect after the demo.",
        },
    ]
    manifest = {
        "project": project_name,
        "generated_at": "2026-07-11T00:00:00Z",
        "readiness_score": _percent(readiness.get("readiness_score", 0)),
        "recommended_action": readiness.get("recommended_action", "review_required"),
        "primary_dashboard": primary_dashboard,
        "demo_video": demo_video,
        "scenario_count": len(scenarios),
        "evidence_count": len(evidence),
        "scenarios": scenarios,
        "evidence": evidence,
    }
    write_json(reports / "judge_demo_cockpit_manifest.json", manifest)
    _write_html(reports / "judge_demo_cockpit.html", manifest)
    return manifest


def _write_html(path: Path, manifest: dict) -> Path:
    payload = json.dumps(manifest, sort_keys=True).replace("</", "<\\/")
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(manifest["project"])} Judge Demo Cockpit</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f6f8fb; color: #172026; font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    header {{ background: #111827; color: #fff; padding: 30px 36px; border-bottom: 5px solid #2563eb; }}
    main {{ max-width: 1440px; margin: 0 auto; padding: 24px 36px 44px; }}
    h1 {{ margin: 0; font-size: 30px; line-height: 1.16; }}
    h2 {{ margin: 0 0 12px; font-size: 17px; }}
    p {{ line-height: 1.5; }}
    header p {{ margin: 9px 0 0; max-width: 900px; color: #cbd5e1; }}
    .hero {{ display: grid; grid-template-columns: minmax(280px, .75fr) minmax(0, 1.25fr); gap: 18px; align-items: stretch; margin-bottom: 18px; }}
    .score, .panel {{ background: #fff; border: 1px solid #d8e0ea; border-radius: 8px; box-shadow: 0 1px 2px rgba(15, 23, 42, .05); }}
    .score {{ padding: 18px; display: grid; gap: 14px; }}
    .score span, .kpi span {{ color: #64748b; font-size: 12px; font-weight: 800; text-transform: uppercase; }}
    .score strong {{ font-size: 46px; line-height: 1; }}
    .bar {{ height: 12px; border-radius: 999px; background: #e2e8f0; overflow: hidden; }}
    .bar span {{ display: block; height: 100%; background: #2563eb; width: calc(var(--value) * 1%); }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .actions a, button {{ border: 1px solid #cbd5e1; border-radius: 6px; padding: 9px 12px; background: #fff; color: #1d4ed8; font: inherit; font-size: 13px; font-weight: 850; text-decoration: none; cursor: pointer; }}
    button.active {{ background: #1d4ed8; color: #fff; border-color: #1d4ed8; }}
    .panel {{ padding: 16px; margin-top: 16px; }}
    .scenario-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
    .scenario {{ min-height: 130px; border: 1px solid #dbe3ec; border-radius: 8px; padding: 13px; background: #fbfdff; }}
    .scenario strong {{ display: block; margin-bottom: 8px; }}
    .scenario p {{ margin: 0; color: #475569; font-size: 13px; }}
    .evidence-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(235px, 1fr)); gap: 12px; }}
    .card {{ min-width: 0; min-height: 166px; display: grid; align-content: space-between; border: 1px solid #dbe3ec; border-radius: 8px; padding: 14px; background: #fff; overflow: hidden; }}
    .card * {{ min-width: 0; }}
    .card[data-hidden="true"] {{ display: none; }}
    .card .top {{ display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }}
    .card strong {{ font-size: 15px; line-height: 1.25; overflow-wrap: anywhere; }}
    .pill {{ display: inline-block; border-radius: 999px; padding: 4px 8px; background: #eef2ff; color: #3730a3; font-size: 11px; font-weight: 900; white-space: nowrap; }}
    .detail {{ margin: 10px 0; color: #475569; font-size: 13px; overflow-wrap: anywhere; }}
    .mini {{ color: #64748b; font-size: 12px; font-weight: 800; overflow-wrap: anywhere; }}
    .kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border: 1px solid #dbe3ec; border-radius: 8px; overflow: hidden; }}
    .kpi {{ padding: 13px; min-height: 82px; background: #f8fafc; border-right: 1px solid #dbe3ec; }}
    .kpi:last-child {{ border-right: 0; }}
    .kpi strong {{ display: block; margin-top: 7px; font-size: 18px; overflow-wrap: anywhere; }}
    @media (max-width: 920px) {{ header, main {{ padding-left: 18px; padding-right: 18px; }} .hero, .scenario-grid {{ grid-template-columns: 1fr; }} .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
  </style>
</head>
<body>
  <header>
    <h1>{esc(manifest["project"])} Judge Demo Cockpit</h1>
    <p>An interactive review surface that connects the runnable dashboard, narrated demo, operational readiness packet, and generated evidence artifacts.</p>
  </header>
  <main>
    <section class="hero">
      <div class="score">
        <span>Operational readiness</span>
        <strong>{esc(manifest["readiness_score"])}%</strong>
        <div class="bar" style="--value:{esc(manifest["readiness_score"])}"><span></span></div>
        <div class="mini">{esc(str(manifest["recommended_action"]).replace("_", " "))}</div>
        <div class="actions">
          <a href="{esc(manifest["primary_dashboard"])}">Open dashboard</a>
          <a href="{esc(manifest["demo_video"])}">Open video</a>
          <a href="operational_readiness_review.json">Readiness JSON</a>
        </div>
      </div>
      <div class="panel" style="margin-top:0">
        <h2>Demo Storyline</h2>
        <div class="scenario-grid" id="scenarios"></div>
      </div>
    </section>
    <section class="panel">
      <h2>Evidence Filters</h2>
      <div class="actions" id="filters"></div>
    </section>
    <section class="panel">
      <h2>Reviewable Evidence</h2>
      <div class="evidence-grid" id="evidence"></div>
    </section>
    <section class="panel">
      <h2>Run Manifest</h2>
      <div class="kpis">
        <div class="kpi"><span>Scenarios</span><strong>{esc(manifest["scenario_count"])}</strong></div>
        <div class="kpi"><span>Evidence artifacts</span><strong>{esc(manifest["evidence_count"])}</strong></div>
        <div class="kpi"><span>Generated</span><strong>{esc(manifest["generated_at"])}</strong></div>
        <div class="kpi"><span>Mode</span><strong>local-first</strong></div>
      </div>
    </section>
  </main>
  <script>
    const manifest = {payload};
    const scenarioRoot = document.querySelector("#scenarios");
    const evidenceRoot = document.querySelector("#evidence");
    const filterRoot = document.querySelector("#filters");
    let active = "all";
    function renderScenarios() {{
      scenarioRoot.innerHTML = manifest.scenarios.map(item => `
        <button class="scenario ${{active === item.focus ? "active" : ""}}" data-focus="${{item.focus}}">
          <strong>${{item.name}}</strong><p>${{item.talk_track}}</p>
        </button>`).join("");
      scenarioRoot.querySelectorAll("button").forEach(button => button.addEventListener("click", () => {{
        active = button.dataset.focus;
        render();
      }}));
    }}
    function renderFilters() {{
      const filters = ["all", ...new Set(manifest.evidence.map(item => item.category))];
      filterRoot.innerHTML = filters.map(value => `<button class="${{active === value ? "active" : ""}}" data-filter="${{value}}">${{value.replace("_", " ")}}</button>`).join("");
      filterRoot.querySelectorAll("button").forEach(button => button.addEventListener("click", () => {{
        active = button.dataset.filter;
        render();
      }}));
    }}
    function renderEvidence() {{
      evidenceRoot.innerHTML = manifest.evidence.map(item => {{
        const hidden = active !== "all" && item.category !== active;
        return `<article class="card" data-hidden="${{hidden}}">
          <div><div class="top"><strong>${{item.title}}</strong><span class="pill">${{item.score}}%</span></div>
          <p class="detail">${{item.detail}}</p></div>
          <div class="mini">${{item.category}} &middot; ${{item.status}}</div>
        </article>`;
      }}).join("");
    }}
    function render() {{
      renderScenarios();
      renderFilters();
      renderEvidence();
    }}
    render();
  </script>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path
