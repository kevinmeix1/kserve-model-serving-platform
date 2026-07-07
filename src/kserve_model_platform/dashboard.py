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


def render_dashboard(output_path: str | Path, *, deployment: dict, report: dict, decision: dict, aliases: dict) -> Path:
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
            "request": row.get("request_id"),
            "route": row.get("selected_alias"),
            "model": row.get("model_version"),
            "score": row.get("risk_score"),
            "band": row.get("risk_band"),
            "latency": row.get("latency_ms"),
        }
        for row in report.get("recent_predictions", [])[-12:]
    ]
    route_counts = report.get("route_counts", {})
    action_label = str(decision.get("recommended_action", "")).replace("_", " ")
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
        .panel {{ padding: 16px; margin-top: 16px; }}
        table {{ width: 100%; table-layout: fixed; border-collapse: collapse; border: 1px solid #e3e9f0; border-radius: 6px; overflow: hidden; }}
        th, td {{ border-bottom: 1px solid #e8edf3; padding: 11px 12px; text-align: left; font-size: 14px; overflow-wrap: anywhere; vertical-align: top; }}
        th {{ background: #f8fafc; color: #334155; }}
        tr:last-child td {{ border-bottom: 0; }}
        .badge {{ display: inline-block; border-radius: 999px; padding: 4px 10px; font-size: 12px; font-weight: 800; }}
        .metric .badge {{ width: auto; max-width: max-content; }}
        .pass {{ color: #166534; background: #dcfce7; }}
        .fail {{ color: #991b1b; background: #fee2e2; }}
        .summary {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
        .summary div {{ border: 1px solid #e3e9f0; border-radius: 6px; padding: 12px; min-height: 74px; }}
        .summary span {{ display: block; color: #64748b; font-size: 12px; margin-bottom: 8px; }}
        .summary strong {{ display: block; font-size: 18px; overflow-wrap: anywhere; }}
        @media (max-width: 900px) {{ header {{ padding: 22px 18px; }} main {{ padding: 18px; }} .layout {{ grid-template-columns: 1fr; }} }}
      </style>
    </head>
    <body>
      <header>
        <h1>KServe Model Serving Platform</h1>
        <p>Champion/challenger rollout, shadow scoring, idempotent predictions, rollback, and serving observability.</p>
      </header>
      <main>
        <section class="grid">
          <div class="metric"><span>Champion</span><strong>{esc(aliases.get('champion'))}</strong></div>
          <div class="metric"><span>Challenger</span><strong>{esc(aliases.get('challenger') or 'none')}</strong></div>
          <div class="metric"><span>Canary status</span><strong>{badge(decision.get('passed', False))}</strong></div>
          <div class="metric"><span>Latency p95</span><strong>{esc(report.get('latency_ms', {}).get('p95'))} ms</strong></div>
        </section>
        <section class="layout">
          <div>
            <div class="panel">
              <h2>Canary Evaluation</h2>
              <table><tr><th>Check</th><th>Status</th><th>Observed</th><th>Threshold</th></tr>{rows(check_rows, ['check', 'status', 'observed', 'threshold'])}</table>
            </div>
            <div class="panel">
              <h2>KServe Deployment</h2>
              <table>
                <tr><th>Service</th><th>Namespace</th><th>Runtime</th><th>Traffic</th><th>Autoscaling</th></tr>
                <tr><td>{esc(deployment.get('service_name'))}</td><td>{esc(deployment.get('namespace'))}</td><td>{esc(deployment.get('runtime'))}</td><td>{esc(deployment.get('traffic'))}</td><td>{esc(deployment.get('autoscaling'))}</td></tr>
              </table>
            </div>
            <div class="panel">
              <h2>Recent Predictions</h2>
              <table><tr><th>Request</th><th>Route</th><th>Model</th><th>Score</th><th>Band</th><th>Latency</th></tr>{rows(prediction_rows, ['request', 'route', 'model', 'score', 'band', 'latency'])}</table>
            </div>
          </div>
          <div>
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
    </body>
    </html>
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body, encoding="utf-8")
    return output_path
