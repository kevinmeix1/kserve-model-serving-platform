from __future__ import annotations

import html
from pathlib import Path


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def badge(value: bool) -> str:
    return f'<span class="badge {"pass" if value else "fail"}">{"PASS" if value else "FAIL"}</span>'


LABELS = {
    "latency_p95": "Latency p95",
    "error_rate": "Error rate",
    "shadow_delta": "Shadow delta",
    "challenger_receives_traffic": "Challenger traffic",
}


def traffic_chips(value: object) -> str:
    if not isinstance(value, dict):
        return esc(value)
    return "".join(f'<span class="chip">{esc(key)} {esc(amount)}%</span>' for key, amount in sorted(value.items()))


def autoscaling_chips(value: object) -> str:
    if not isinstance(value, dict):
        return esc(value)
    labels = {
        "min_replicas": "min",
        "max_replicas": "max",
        "target_concurrency": "target",
    }
    return "".join(f'<span class="chip">{labels.get(key, key)} {esc(amount)}</span>' for key, amount in value.items())


def gateway_decision_rows(plan: dict) -> list[dict]:
    decisions = plan.get("simulation", {}).get("route_decisions", []) if isinstance(plan, dict) else []
    return [
        {
            "class": compact_label(item.get("request_class")),
            "priority": item.get("priority"),
            "endpoint": compact_label(item.get("selected_endpoint")),
            "p95": f"{item.get('estimated_p95_ms')} / {item.get('slo_ms')} ms",
        }
        for item in decisions[:4]
    ]


def compact_label(value: object) -> str:
    text = "" if value is None else str(value)
    if text.startswith("risk-model-"):
        display = text.replace("risk-model-", "risk ")
    elif text.startswith("req_"):
        display = f"req {text.split('_')[-1].lstrip('0') or '0'}"
    else:
        display = {
            "kserve-sklearnserver": "KServe sklearn",
            "kserve-v2-custom-runtime": "KServe V2 custom",
        }.get(text, text.replace("-", " "))
    return f'<span class="nowrap" title="{esc(text)}">{esc(display)}</span>'


def rows(items: list[dict], columns: list[str]) -> str:
    if not items:
        return f"<tr><td colspan='{len(columns)}'>No records</td></tr>"
    output = []
    for item in items:
        cells = []
        for column in columns:
            value = item.get(column, "")
            if isinstance(value, str) and value.startswith("<span class="):
                cells.append(f"<td>{value}</td>")
            else:
                cells.append(f"<td>{esc(value)}</td>")
        output.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(output)


def render_dashboard(
    output_path: str | Path,
    *,
    deployment: dict,
    report: dict,
    decision: dict,
    aliases: dict,
    rollout_plan: dict | None = None,
    inference_gateway_plan: dict | None = None,
    semantic_telemetry_plan: dict | None = None,
    llm_readiness_plan: dict | None = None,
    transformer_explainer_plan: dict | None = None,
) -> Path:
    rollout_plan = rollout_plan or {}
    inference_gateway_plan = inference_gateway_plan or {}
    semantic_telemetry_plan = semantic_telemetry_plan or {}
    llm_readiness_plan = llm_readiness_plan or {}
    transformer_explainer_plan = transformer_explainer_plan or {}
    rollout_analysis = rollout_plan.get("analysis", {})
    genai_rollout = semantic_telemetry_plan.get("genai_rollout_metrics", {})
    genai_metrics = {item.get("name"): item for item in genai_rollout.get("metrics", [])}
    llm_contract = llm_readiness_plan.get("serving_contract", {})
    llm_routing = llm_readiness_plan.get("routing", {})
    llm_models = llm_readiness_plan.get("models", [])
    transformer_collocation = transformer_explainer_plan.get("collocation_decision", {})
    transformer_stages = transformer_explainer_plan.get("serving_stages", [])
    sync_budget_ms = sum(
        float(stage.get("latency_budget_ms", 0))
        for stage in transformer_stages
        if stage.get("role") in {"transformer", "predictor"}
    )
    declared_roles = sorted({str(stage.get("role")) for stage in transformer_stages if stage.get("role")})
    explainer_stage = next((stage for stage in transformer_stages if stage.get("role") == "explainer"), {})
    transformer_health = next((stage.get("health_gate") for stage in transformer_stages if stage.get("role") == "transformer"), "not planned")
    transformer_status = "Ready" if transformer_explainer_plan.get("passed") else "Needs review"
    transformer_collocation_label = (
        "Separate + async explainer"
        if transformer_collocation.get("current_choice") == "separate transformer, async explainer"
        else transformer_collocation.get("current_choice", "not planned")
    )
    transformer_health_label = (
        "Predictor health gated"
        if "predictor health" in str(transformer_health)
        else transformer_health
    )
    transformer_action_label = (
        "Enable topology"
        if transformer_explainer_plan.get("recommended_action") == "enable_transformer_explainer_topology"
        else transformer_explainer_plan.get("recommended_action", "not planned")
    )
    check_rows = [
        {
            "check": LABELS.get(check["name"], check["name"]),
            "status": badge(bool(check["passed"])),
            "observed": check.get("observed"),
            "threshold": check.get("threshold"),
        }
        for check in decision.get("checks", [])
    ]
    prediction_rows = [
        {
            "request": compact_label(row.get("request_id")),
            "route": row.get("selected_alias"),
            "model": compact_label(row.get("model_version")),
            "score": row.get("risk_score"),
            "band": row.get("risk_band"),
            "latency": row.get("latency_ms"),
        }
        for row in report.get("recent_predictions", [])[-12:]
    ]
    route_counts = report.get("route_counts", {})
    action_label = str(decision.get("recommended_action", "")).replace("_", " ")
    gateway_simulation = inference_gateway_plan.get("simulation", {})
    gateway_picker = gateway_simulation.get("endpoint_picker", {})
    gateway_slo = gateway_simulation.get("slo_summary", {})
    gateway_fail_open = gateway_simulation.get("fail_open_drill", {})
    gateway_rows = gateway_decision_rows(inference_gateway_plan)
    body = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <title>KServe Model Serving Platform</title>
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: #f5f7fa; color: #1c2733; font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
        header {{ background: #16202a; color: #fff; padding: 28px 36px; border-bottom: 5px solid #14b8a6; }}
        main {{ max-width: 1460px; margin: 0 auto; padding: 24px 36px 42px; }}
        h1 {{ margin: 0; font-size: 28px; line-height: 1.2; }}
        h2 {{ margin: 0 0 14px; font-size: 17px; }}
        header p {{ margin: 8px 0 0; color: #cbd5df; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; margin-bottom: 18px; }}
        .metric, .panel {{ background: #fff; border: 1px solid #d7dee7; border-radius: 8px; box-shadow: 0 1px 2px rgba(22, 32, 42, 0.04); }}
        .metric {{ min-height: 112px; padding: 16px; }}
        .metric span {{ display: block; color: #5b6b7d; font-size: 13px; margin-bottom: 10px; }}
        .metric strong {{ display: block; font-size: 24px; line-height: 1.2; overflow-wrap: anywhere; }}
        .layout {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(360px, .42fr); gap: 16px; align-items: start; }}
        .layout > div {{ min-width: 0; }}
        .panel {{ padding: 16px; margin-top: 16px; }}
        table {{ width: 100%; table-layout: fixed; border-collapse: collapse; border: 1px solid #e3e9f0; border-radius: 6px; overflow: hidden; }}
        th, td {{ border-bottom: 1px solid #e8edf3; padding: 11px 12px; text-align: left; font-size: 14px; overflow-wrap: anywhere; vertical-align: top; }}
        th {{ background: #f8fafc; color: #334155; }}
        tr:last-child td {{ border-bottom: 0; }}
        .badge {{ display: inline-block; border-radius: 999px; padding: 4px 10px; font-size: 12px; font-weight: 800; }}
        .metric .badge {{ width: auto; max-width: max-content; }}
        .pass {{ color: #166534; background: #dcfce7; }}
        .fail {{ color: #991b1b; background: #fee2e2; }}
        .chip {{ display: inline-block; margin: 0 5px 5px 0; padding: 4px 8px; border-radius: 999px; background: #ecfeff; color: #0e7490; font-size: 12px; font-weight: 800; white-space: nowrap; }}
        .nowrap {{ display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: bottom; }}
        .evidence-deck {{ border-left: 4px solid #2563eb; }}
        .evidence-head {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; margin-bottom: 14px; }}
        .evidence-head p {{ margin: 5px 0 0; color: #64748b; font-size: 13px; line-height: 1.45; max-width: 850px; }}
        .evidence-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
        .evidence-card {{ min-height: 154px; border: 1px solid #e3e9f0; border-radius: 6px; padding: 13px; background: #fbfcfe; }}
        .evidence-card span {{ display: block; color: #64748b; font-size: 11px; font-weight: 800; text-transform: uppercase; margin-bottom: 8px; }}
        .evidence-card strong {{ display: block; font-size: 15px; line-height: 1.25; margin-bottom: 8px; overflow-wrap: anywhere; }}
        .evidence-card p {{ margin: 0; color: #475569; font-size: 12px; line-height: 1.45; }}
        .demo-theater {{ border-left: 4px solid #7c3aed; }}
        .theater-grid {{ display: grid; grid-template-columns: minmax(0, .7fr) minmax(0, 1.3fr); gap: 16px; align-items: stretch; }}
        .theater-stage {{ min-height: 258px; border: 1px solid #dbe3ec; border-radius: 8px; padding: 16px; background: linear-gradient(135deg, #111827, #312e81); color: #fff; display: grid; align-content: space-between; }}
        .theater-stage span {{ color: #c4b5fd; font-size: 12px; font-weight: 800; text-transform: uppercase; }}
        .theater-stage strong {{ display: block; margin-top: 8px; font-size: 25px; line-height: 1.15; }}
        .theater-stage p {{ margin: 12px 0 0; color: #ddd6fe; line-height: 1.45; }}
        .theater-actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }}
        .cue {{ border: 1px solid #c4b5fd; border-radius: 6px; padding: 9px 11px; background: #fff; color: #4c1d95; font: inherit; font-size: 12px; font-weight: 900; cursor: pointer; }}
        .cue.active {{ background: #7c3aed; color: #fff; }}
        .theater-panel {{ display: grid; gap: 12px; }}
        .theater-kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border: 1px solid #e4e9f0; border-radius: 8px; overflow: hidden; }}
        .theater-kpis div {{ min-height: 78px; padding: 12px; background: #f8fafc; border-right: 1px solid #e4e9f0; }}
        .theater-kpis div:last-child {{ border-right: 0; }}
        .theater-kpis span {{ display: block; color: #64748b; font-size: 11px; margin-bottom: 7px; }}
        .theater-kpis strong {{ display: block; font-size: 16px; overflow-wrap: anywhere; }}
        .theater-progress {{ height: 10px; border-radius: 999px; overflow: hidden; background: #e2e8f0; }}
        .theater-progress span {{ display: block; height: 100%; width: 25%; background: #7c3aed; transition: width .18s ease; }}
        .theater-notes {{ margin: 0; color: #475569; line-height: 1.45; }}
        .theater-links {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .theater-links a {{ border: 1px solid #dbe3ec; border-radius: 6px; padding: 8px 10px; color: #1d4ed8; font-size: 12px; font-weight: 800; text-decoration: none; background: #fff; }}
        .summary {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); border: 1px solid #e3e9f0; border-radius: 6px; overflow: hidden; }}
        .summary div {{ padding: 12px; min-height: 74px; background: #fbfcfe; border-right: 1px solid #e3e9f0; border-bottom: 1px solid #e3e9f0; }}
        .summary div:nth-child(2n) {{ border-right: 0; }}
        .summary div:nth-last-child(-n+2) {{ border-bottom: 0; }}
        .summary span {{ display: block; color: #64748b; font-size: 12px; margin-bottom: 8px; }}
        .summary strong {{ display: block; font-size: 18px; overflow-wrap: anywhere; }}
        .live-panel {{ border-left: 4px solid #0f766e; margin-bottom: 18px; }}
        .live-heading {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }}
        .live-heading p {{ margin: 5px 0 0; color: #64748b; font-size: 13px; }}
        .live-state {{ display: inline-flex; align-items: center; gap: 7px; color: #475569; font-size: 13px; font-weight: 700; white-space: nowrap; }}
        .state-dot {{ width: 9px; height: 9px; border-radius: 50%; background: #94a3b8; }}
        .state-dot.ready {{ background: #16a34a; box-shadow: 0 0 0 3px #dcfce7; }}
        .state-dot.error {{ background: #dc2626; box-shadow: 0 0 0 3px #fee2e2; }}
        .live-layout {{ display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(360px, .8fr); gap: 18px; align-items: start; }}
        .form-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
        label {{ display: block; color: #475569; font-size: 12px; font-weight: 700; }}
        input, select {{ width: 100%; margin-top: 6px; padding: 9px 10px; border: 1px solid #cbd5e1; border-radius: 6px; background: white; color: #0f172a; font: inherit; }}
        input:focus, select:focus {{ outline: 2px solid #99f6e4; border-color: #0f766e; }}
        button {{ border: 0; border-radius: 6px; padding: 10px 14px; background: #0f766e; color: white; font: inherit; font-weight: 800; cursor: pointer; }}
        button:hover {{ background: #115e59; }}
        button:disabled {{ background: #94a3b8; cursor: wait; }}
        .form-actions {{ display: flex; align-items: center; gap: 12px; margin-top: 14px; }}
        .form-message {{ color: #64748b; font-size: 12px; }}
        .live-facts {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); border: 1px solid #e3e9f0; border-radius: 6px; overflow: hidden; }}
        .live-facts div {{ padding: 11px 12px; min-height: 68px; background: #f8fafc; border-right: 1px solid #e3e9f0; border-bottom: 1px solid #e3e9f0; }}
        .live-facts div:nth-child(2n) {{ border-right: 0; }}
        .live-facts div:nth-last-child(-n+2) {{ border-bottom: 0; }}
        .live-facts span {{ display: block; color: #64748b; font-size: 11px; margin-bottom: 7px; }}
        .live-facts strong {{ display: block; color: #0f172a; font-size: 15px; overflow-wrap: anywhere; }}
        .live-results {{ margin-top: 16px; overflow-x: auto; }}
        .live-results table {{ min-width: 760px; }}
        .empty-result {{ color: #64748b; text-align: center; }}
        @media (max-width: 900px) {{
          header {{ padding: 22px 18px; }}
          main {{ padding: 18px; }}
          .layout, .live-layout {{ grid-template-columns: 1fr; }}
          .form-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
          .panel {{ max-width: 100%; overflow-x: auto; }}
          .canary-table {{ min-width: 520px; }}
          .deployment-table {{ min-width: 720px; }}
          .predictions-table {{ min-width: 760px; }}
          .evidence-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
          th, td {{ overflow-wrap: normal; word-break: normal; }}
        }}
        @media (max-width: 600px) {{
          .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
          .grid .metric:last-child {{ grid-column: 1 / -1; }}
          .form-grid, .live-facts {{ grid-template-columns: 1fr; }}
          .live-facts div {{ border-right: 0; }}
          .live-heading {{ align-items: flex-start; flex-direction: column; }}
          .evidence-head {{ flex-direction: column; }}
          .evidence-grid {{ grid-template-columns: 1fr; }}
          .theater-grid, .theater-kpis {{ grid-template-columns: 1fr; }}
          .theater-kpis div {{ border-right: 0; border-bottom: 1px solid #e4e9f0; }}
          .theater-kpis div:last-child {{ border-bottom: 0; }}
        }}
      </style>
    </head>
    <body>
      <header>
        <h1>KServe Model Serving Platform</h1>
        <p>Champion/challenger rollout, shadow scoring, idempotent predictions, rollback, and serving observability.</p>
      </header>
      <main>
        <section class="grid">
          <div class="metric"><span>Champion</span><strong>{compact_label(aliases.get('champion'))}</strong></div>
          <div class="metric"><span>Challenger</span><strong>{compact_label(aliases.get('challenger') or 'none')}</strong></div>
          <div class="metric"><span>Canary status</span><strong>{badge(decision.get('passed', False))}</strong></div>
          <div class="metric"><span>Latency p95</span><strong>{esc(report.get('latency_ms', {}).get('p95'))} ms</strong></div>
          <div class="metric"><span>Serving protocol</span><strong>Open Inference V2</strong></div>
        </section>
        <section class="panel evidence-deck" data-testid="judge-evidence-deck">
          <div class="evidence-head">
            <div>
              <h2>Judge Evidence Deck</h2>
              <p>Use this deck to narrate the production serving story before opening the live lab: request contract, rollout control, routing, and observability are connected.</p>
            </div>
            <span class="badge">review path</span>
          </div>
          <div class="evidence-grid">
            <div class="evidence-card"><span>Request contract</span><strong>Open Inference V2 with idempotency</strong><p>The API validates request shape, writes prediction logs, and exposes bounded status without leaking feature payloads.</p></div>
            <div class="evidence-card"><span>KServe rollout</span><strong>Canary promotion is explicit</strong><p>Traffic split, shadow deltas, SLO budgets, and registry aliases stay separate from the manual promotion command.</p></div>
            <div class="evidence-card"><span>Gateway routing</span><strong>Endpoint picker fallback is modeled</strong><p>The dashboard covers priority objectives, fail-open behavior, HPA/PDB readiness, and model-aware routing evidence.</p></div>
            <div class="evidence-card"><span>Explainability</span><strong>Transformer and explainer are isolated</strong><p>Pre/post-processing, predictor health gates, and async explanations avoid hiding predictor failures behind a single endpoint.</p></div>
          </div>
        </section>
        <section class="panel demo-theater" data-testid="demo-theater">
          <div class="evidence-head">
            <div><h2>Judge Demo Theater</h2><p>Walk a reviewer through low-latency inference, progressive rollout, Gateway routing, and observability with the committed narrated video.</p></div>
            <span class="badge">narrated demo</span>
          </div>
          <div class="theater-grid">
            <div class="theater-stage" aria-live="polite">
              <div><span id="theaterCue">Opening</span><strong id="theaterTitle">Start with serving contracts</strong><p id="theaterBody">Show the runtime is not a loose FastAPI endpoint: it speaks Open Inference V2, preserves idempotency, and exposes bounded status.</p></div>
              <div class="theater-actions">
                <button type="button" class="cue active" data-demo-cue="0">Contract</button>
                <button type="button" class="cue" data-demo-cue="1">Live</button>
                <button type="button" class="cue" data-demo-cue="2">Rollout</button>
                <button type="button" class="cue" data-demo-cue="3">LLM</button>
              </div>
            </div>
            <div class="theater-panel">
              <div class="theater-kpis">
                <div><span>Video</span><strong>H.264 serving walkthrough</strong></div>
                <div><span>Voice</span><strong>edge-tts neural narration</strong></div>
                <div><span>Signals</span><strong>p95, errors, drift, route mix</strong></div>
                <div><span>Evidence</span><strong>OpenAPI + screenshots</strong></div>
              </div>
              <div class="theater-progress"><span id="theaterProgress"></span></div>
              <p id="theaterNotes" class="theater-notes">Reviewer path: run <code>make demo</code>, then <code>make api-run</code> for the live inference lab.</p>
              <div class="theater-links">
                <a href="../../docs/demo/kserve-judge-demo.mp4">Watch video</a>
                <a href="../../docs/judge-demo.md">Demo script</a>
                <a href="../../docs/demo-narration.txt">Narration text</a>
                <a href="/docs">API docs</a>
              </div>
            </div>
          </div>
        </section>
        <script>
          function renderDemoTheater(index) {{
            const cues = [
              {{cue: "Contract", title: "Start with serving contracts", body: "Show the runtime is not a loose FastAPI endpoint: it speaks Open Inference V2, preserves idempotency, and exposes bounded status.", notes: "Judges should see request validation, model version, and replay behavior before traffic controls."}},
              {{cue: "Live", title: "Run a real inference request", body: "Use the Live Inference Lab to create a prediction, then watch route, model version, latency, and ledger counts update.", notes: "This proves the UI is wired to executable runtime state when make api-run is active."}},
              {{cue: "Rollout", title: "Explain champion/challenger control", body: "Move from canary checks to Gateway weights, shadow deltas, and rollback-safe promotion.", notes: "Promotion stays explicit; monitoring recommends but does not mutate production blindly."}},
              {{cue: "LLM", title: "Show platform depth beyond tabular serving", body: "Finish with LLM readiness, transformer/explainer topology, token budgets, and groundedness gates.", notes: "This is the senior angle: one platform handles KServe primitives, GenAI telemetry, and operational rollback."}}
            ];
            const item = cues[index] || cues[0];
            document.getElementById("theaterCue").textContent = item.cue;
            document.getElementById("theaterTitle").textContent = item.title;
            document.getElementById("theaterBody").textContent = item.body;
            document.getElementById("theaterNotes").textContent = item.notes;
            document.getElementById("theaterProgress").style.width = (((index + 1) / cues.length) * 100) + "%";
            document.querySelectorAll("[data-demo-cue]").forEach((button) => button.classList.toggle("active", Number(button.dataset.demoCue) === index));
          }}
          document.querySelectorAll("[data-demo-cue]").forEach((button) => button.addEventListener("click", () => renderDemoTheater(Number(button.dataset.demoCue))));
          renderDemoTheater(0);
        </script>
        <section class="panel live-panel" data-testid="inference-lab">
          <div class="live-heading">
            <div><h2>Live Inference Lab</h2><p>Score a request against the running V2 service and inspect routing evidence.</p></div>
            <div class="live-state"><span id="statusDot" class="state-dot"></span><span id="statusText">Connecting</span></div>
          </div>
          <div class="live-layout">
            <form id="inferenceForm">
              <div class="form-grid">
                <label>Product<select id="product"><option value="card">Card</option><option value="loan">Loan</option><option value="mortgage">Mortgage</option></select></label>
                <label>Income<input id="income" type="number" min="1000" max="1000000" step="1000" value="58000"></label>
                <label>Debt ratio<input id="debtRatio" type="number" min="0" max="1" step="0.01" value="0.72"></label>
                <label>Delinquencies<input id="delinquencies" type="number" min="0" max="20" step="1" value="2"></label>
                <label>Utilization<input id="utilization" type="number" min="0" max="1" step="0.01" value="0.84"></label>
                <label>Employment years<input id="employmentYears" type="number" min="0" max="60" step="0.1" value="2.4"></label>
              </div>
              <div class="form-actions"><button id="scoreButton" type="submit">Run inference</button><span id="formMessage" class="form-message">Uses a unique idempotency key for each request.</span></div>
            </form>
            <div class="live-facts" aria-live="polite">
              <div><span>Snapshot generation</span><strong id="snapshotGeneration">not connected</strong></div>
              <div><span>Traffic split</span><strong id="trafficSplit">not connected</strong></div>
              <div><span>Ledger requests</span><strong id="ledgerRequests">0</strong></div>
              <div><span>Detached workers</span><strong id="detachedWorkers">0</strong></div>
            </div>
          </div>
          <div class="live-results">
            <table><thead><tr><th>Request</th><th>Route</th><th>Model</th><th>Risk score</th><th>Band</th><th>Latency</th><th>Replay</th></tr></thead><tbody id="liveResultRows"><tr id="emptyResult"><td class="empty-result" colspan="7">Run an inference to create live evidence.</td></tr></tbody></table>
          </div>
        </section>
        <section class="layout">
          <div>
            <div class="panel">
              <h2>Canary Evaluation</h2>
              <table class="canary-table"><tr><th>Check</th><th>Status</th><th>Observed</th><th>Threshold</th></tr>{rows(check_rows, ['check', 'status', 'observed', 'threshold'])}</table>
            </div>
            <div class="panel">
              <h2>KServe Deployment</h2>
              <table class="deployment-table">
                <tr><th>Service</th><th>Namespace</th><th>Runtime</th><th>Traffic</th><th>Autoscaling</th></tr>
                <tr><td>{compact_label(deployment.get('service_name'))}</td><td>{compact_label(deployment.get('namespace'))}</td><td>{compact_label(deployment.get('runtime'))}</td><td>{traffic_chips(deployment.get('traffic'))}</td><td>{autoscaling_chips(deployment.get('autoscaling'))}</td></tr>
              </table>
            </div>
            <div class="panel">
              <h2>Inference Gateway</h2>
              <div class="summary">
                <div><span>Inference pool</span><strong>{compact_label(inference_gateway_plan.get('pool', {}).get('name', 'not planned'))}</strong></div>
                <div><span>Endpoint picker</span><strong>{esc(gateway_picker.get('protocol', 'not planned'))}</strong></div>
                <div><span>Failure mode</span><strong>{esc(gateway_picker.get('failure_mode', 'n/a'))}</strong></div>
                <div><span>SLO classes</span><strong>{esc(gateway_slo.get('passed_classes', 0))}/{esc(gateway_slo.get('request_classes', 0))}</strong></div>
                <div><span>Fallback route</span><strong>{esc(gateway_fail_open.get('fallback_route', 'n/a'))}</strong></div>
              </div>
              <table class="gateway-table" style="margin-top: 12px;"><tr><th>Class</th><th>Priority</th><th>Endpoint</th><th>p95/SLO</th></tr>{rows(gateway_rows, ['class', 'priority', 'endpoint', 'p95'])}</table>
            </div>
            <div class="panel">
              <h2>Recent Predictions</h2>
              <table class="predictions-table"><tr><th>Request</th><th>Route</th><th>Model</th><th>Score</th><th>Band</th><th>Latency</th></tr>{rows(prediction_rows, ['request', 'route', 'model', 'score', 'band', 'latency'])}</table>
            </div>
          </div>
          <div>
            <div class="panel">
              <h2>Runtime Contract</h2>
              <div class="summary">
                <div><span>Readiness</span><strong>{esc(deployment.get('status'))}</strong></div>
                <div><span>Batch limit</span><strong>128</strong></div>
                <div><span>Concurrency limit</span><strong>32</strong></div>
                <div><span>Idempotency</span><strong>SQLite WAL</strong></div>
              </div>
            </div>
            <div class="panel">
              <h2>Rollout Control Plane</h2>
              <div class="summary">
                <div><span>Recommended action</span><strong>{esc(rollout_plan.get('recommended_action', 'not planned'))}</strong></div>
                <div><span>Next canary percent</span><strong>{esc(rollout_plan.get('next_percent', 'n/a'))}</strong></div>
                <div><span>Error upper bound</span><strong>{esc(rollout_analysis.get('error_upper_bound', 'n/a'))}</strong></div>
                <div><span>Gateway weights</span><strong>{traffic_chips(rollout_plan.get('gateway_weights', {}))}</strong></div>
              </div>
            </div>
            <div class="panel">
              <h2>GenAI Telemetry Gates</h2>
              <div class="summary">
                <div><span>Token p95</span><strong>{esc(genai_metrics.get('input_token_p95', {}).get('observed', 'n/a'))} / {esc(genai_metrics.get('input_token_p95', {}).get('threshold', 'n/a'))}</strong></div>
                <div><span>Cost per 1k</span><strong>${esc(genai_metrics.get('estimated_cost_per_1k', {}).get('observed', 'n/a'))}</strong></div>
                <div><span>Queue p95</span><strong>{esc(genai_metrics.get('queue_latency_p95_ms', {}).get('observed', 'n/a'))} ms</strong></div>
                <div><span>Prefix cache hit</span><strong>{esc(genai_metrics.get('prefix_cache_hit_ratio', {}).get('observed', 'n/a'))}</strong></div>
                <div><span>Groundedness p05</span><strong>{esc(genai_metrics.get('groundedness_score_p05', {}).get('observed', 'n/a'))}</strong></div>
                <div><span>Analysis</span><strong>{compact_label(genai_rollout.get('analysis_template', 'not planned'))}</strong></div>
              </div>
            </div>
            <div class="panel">
              <h2>LLM Inference Readiness</h2>
              <div class="summary">
                <div><span>Serving API</span><strong>{compact_label(llm_contract.get('api', 'not planned'))}</strong></div>
                <div><span>Runtime</span><strong>{compact_label(llm_contract.get('runtime', 'not planned'))}</strong></div>
                <div><span>Gateway</span><strong>{compact_label(llm_contract.get('gateway', 'not planned'))}</strong></div>
                <div><span>Artifact format</span><strong>{compact_label(llm_contract.get('artifact_format', 'not planned'))}</strong></div>
                <div><span>Routing SLOs</span><strong>{esc(llm_routing.get('passed_classes', 0))}/{esc(llm_routing.get('request_classes', 0))}</strong></div>
                <div><span>Prefill/decode replicas</span><strong>{esc(sum(item.get('prefill_replicas', 0) for item in llm_models))}/{esc(sum(item.get('decode_replicas', 0) for item in llm_models))}</strong></div>
              </div>
            </div>
            <div class="panel">
              <h2>Transformer And Explainer Readiness</h2>
              <div class="summary">
                <div><span>Status</span><strong>{badge(bool(transformer_explainer_plan.get('passed', False)))} {esc(transformer_status)}</strong></div>
                <div><span>Roles declared</span><strong>{esc(len(declared_roles))} roles</strong></div>
                <div><span>Sync budget</span><strong>{esc(round(sync_budget_ms, 1))} ms</strong></div>
                <div><span>Collocation</span><strong>{compact_label(transformer_collocation_label)}</strong></div>
                <div><span>Transformer health</span><strong>{compact_label(transformer_health_label)}</strong></div>
                <div><span>Explainer mode</span><strong>{compact_label(explainer_stage.get('deployment_mode', 'not planned'))}</strong></div>
                <div><span>Action</span><strong>{compact_label(transformer_action_label)}</strong></div>
              </div>
            </div>
            <div class="panel">
              <h2>Traffic And Errors</h2>
              <div class="summary">
                <div><span>Requests</span><strong>{esc(report.get('request_count'))}</strong></div>
                <div><span>Error rate</span><strong>{esc(report.get('error_rate'))}</strong></div>
                <div><span>Champion routes</span><strong>{esc(route_counts.get('champion', 0))}</strong></div>
                <div><span>Challenger routes</span><strong>{esc(route_counts.get('challenger', 0))}</strong></div>
              </div>
            </div>
            <div class="panel">
              <h2>Shadow Comparison</h2>
              <div class="summary">
                <div><span>Compared</span><strong>{esc(report.get('shadow', {}).get('comparison_count'))}</strong></div>
                <div><span>Mean delta</span><strong>{esc(report.get('shadow', {}).get('mean_abs_delta'))}</strong></div>
                <div><span>Max delta</span><strong>{esc(report.get('shadow', {}).get('max_abs_delta'))}</strong></div>
                <div><span>Action</span><strong>{esc(action_label)}</strong></div>
              </div>
            </div>
            <div class="panel">
              <h2>Risk Distribution</h2>
              <div class="summary">
                <div><span>Mean score</span><strong>{esc(report.get('risk_score', {}).get('mean'))}</strong></div>
                <div><span>High risk share</span><strong>{esc(report.get('risk_score', {}).get('high_risk_share'))}</strong></div>
              </div>
            </div>
          </div>
        </section>
      </main>
      <script>
        const byId = (id) => document.getElementById(id);
        const value = (id) => Number(byId(id).value);
        const tensor = (name, datatype, item) => ({{name, datatype, shape: [1], data: [item]}});
        const outputValue = (payload, name) => {{
          const output = (payload.outputs || []).find((item) => item.name === name);
          return output && output.data ? output.data[0] : "n/a";
        }};

        async function refreshConsoleStatus() {{
          const dot = byId("statusDot");
          try {{
            const response = await fetch("/api/console/status", {{cache: "no-store"}});
            if (!response.ok) throw new Error("status " + response.status);
            const state = await response.json();
            dot.className = "state-dot ready";
            byId("statusText").textContent = "Runtime ready";
            byId("snapshotGeneration").textContent = state.snapshot.generation;
            byId("trafficSplit").textContent = "champion " + (100 - state.snapshot.challenger_percent) + "% / challenger " + state.snapshot.challenger_percent + "%";
            byId("ledgerRequests").textContent = state.ledger.completed_requests;
            byId("detachedWorkers").textContent = state.runtime.detached_workers;
          }} catch (error) {{
            dot.className = "state-dot error";
            byId("statusText").textContent = "Start make api-run for live mode";
          }}
        }}

        byId("inferenceForm").addEventListener("submit", async (event) => {{
          event.preventDefault();
          const button = byId("scoreButton");
          const message = byId("formMessage");
          const requestId = "judge-" + Date.now();
          const payload = {{
            id: requestId,
            inputs: [
              tensor("customer_id", "BYTES", "portfolio-review"),
              tensor("product", "BYTES", byId("product").value),
              tensor("income", "FP64", value("income")),
              tensor("debt_ratio", "FP64", value("debtRatio")),
              tensor("delinquencies", "INT64", value("delinquencies")),
              tensor("utilization", "FP64", value("utilization")),
              tensor("employment_years", "FP64", value("employmentYears"))
            ]
          }};
          button.disabled = true;
          message.textContent = "Scoring against the live model router...";
          const started = performance.now();
          try {{
            const response = await fetch("/v2/models/credit-risk-router/infer", {{
              method: "POST",
              headers: {{"Content-Type": "application/json", "X-Request-ID": requestId}},
              body: JSON.stringify(payload)
            }});
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "inference failed");
            const latency = (performance.now() - started).toFixed(1) + " ms";
            const row = document.createElement("tr");
            [requestId, outputValue(result, "selected_alias"), outputValue(result, "model_version"), outputValue(result, "risk_score"), outputValue(result, "risk_band"), latency, String(result.parameters.idempotent_replay)].forEach((item) => {{
              const cell = document.createElement("td");
              cell.textContent = item;
              row.appendChild(cell);
            }});
            const empty = byId("emptyResult");
            if (empty) empty.remove();
            const rows = byId("liveResultRows");
            rows.prepend(row);
            while (rows.children.length > 8) rows.lastElementChild.remove();
            message.textContent = "Completed with snapshot " + result.parameters.snapshot_generation + ".";
            await refreshConsoleStatus();
          }} catch (error) {{
            message.textContent = "Request failed: " + error.message;
          }} finally {{
            button.disabled = false;
          }}
        }});

        refreshConsoleStatus();
        window.setInterval(refreshConsoleStatus, 10000);
      </script>
    </body>
    </html>
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body, encoding="utf-8")
    return output_path
