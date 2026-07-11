from __future__ import annotations

import html
import json
from pathlib import Path

from .io import read_json, write_json


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _read_optional(path: Path) -> dict:
    return read_json(path) if path.exists() else {}


def _script_excerpt(path: Path) -> str:
    if not path.exists():
        return "Use the generated chapter script as the source narration track."
    text = path.read_text(encoding="utf-8").strip()
    return text[:900] if text else "Use the generated chapter script as the source narration track."


def build_narrated_demo_studio(
    root: str | Path,
    *,
    project_name: str,
    domain: str,
    primary_dashboard: str,
    demo_video: str,
    narration_script: str = "../../docs/demo-narration.txt",
) -> dict:
    root = Path(root)
    reports = root / "reports"
    readiness = _read_optional(reports / "operational_readiness_review.json")
    judge = _read_optional(reports / "judge_demo_cockpit_manifest.json")
    mesh = _read_optional(reports / "reliability_signal_mesh.json")
    script_path = (reports / narration_script).resolve()
    chapters = [
        {
            "chapter": "Open With The Production Claim",
            "duration_seconds": 28,
            "visual": primary_dashboard,
            "voice_note": "Calm, confident, judge-facing introduction.",
            "script": f"This is {project_name}. The goal is to show production behavior, not a toy notebook: {domain}.",
        },
        {
            "chapter": "Show The Evidence Map",
            "duration_seconds": 36,
            "visual": "judge_demo_cockpit.html",
            "voice_note": "Point at the generated artifacts and explain what each proves.",
            "script": "The cockpit links dashboards, gates, governance evidence, SLOs, and run metadata so every claim is inspectable.",
        },
        {
            "chapter": "Walk Through Observability",
            "duration_seconds": 42,
            "visual": "reliability_signal_mesh.html",
            "voice_note": "Use operational language: symptoms, signals, decision, recovery.",
            "script": "The signal mesh connects Airflow events, OpenTelemetry resource attributes, queue pressure, SLO burn, and release admission.",
        },
        {
            "chapter": "Rehearse Failure Recovery",
            "duration_seconds": 38,
            "visual": "operator_drill_lab.html",
            "voice_note": "Slow down for the incident path and make the rollback/freeze decision obvious.",
            "script": "The operator drill shows detection, triage, containment, recovery, and the postmortem contract from generated evidence.",
        },
        {
            "chapter": "Close With Production Migration",
            "duration_seconds": 30,
            "visual": "cloud_migration_plan.json",
            "voice_note": "End with portability and cloud migration rather than another feature list.",
            "script": "The project is local-first, but the contracts map cleanly to managed Kubernetes, MLflow, Airflow, and cloud observability stacks.",
        },
    ]
    total_duration = sum(item["duration_seconds"] for item in chapters)
    backends = [
        {
            "name": "kokoro_local",
            "command": "python -m kokoro --voice af_heart --text docs/demo-narration.txt --output .local/demo/demo.wav",
            "why": "Local open-weight narration path with natural pacing and no external service dependency.",
        },
        {
            "name": "edge_tts_neural",
            "command": "make demo-voice",
            "why": "Existing repo path for high-quality neural narration and generated subtitles.",
        },
        {
            "name": "remotion_video",
            "command": "npx remotion render Demo docs/demo/generated-demo.mp4 --props .local/reports/remotion_demo_props.json",
            "why": "Code-driven video rendering with reusable props for dashboards, chapters, timing, and captions.",
        },
    ]
    manifest = {
        "project": project_name,
        "domain": domain,
        "generated_at": "2026-07-11T00:00:00Z",
        "status": "ready",
        "primary_dashboard": primary_dashboard,
        "demo_video": demo_video,
        "narration_script": narration_script,
        "readiness_score": readiness.get("readiness_score", 0),
        "evidence_count": judge.get("evidence_count", 0),
        "mesh_status": mesh.get("status", "not_generated"),
        "total_duration_seconds": total_duration,
        "chapters": chapters,
        "natural_voice_backends": backends,
        "script_excerpt": _script_excerpt(script_path),
    }
    write_json(reports / "narrated_demo_studio.json", manifest)
    write_json(
        reports / "remotion_demo_props.json",
        {"project": project_name, "durationInFrames": total_duration * 30, "fps": 30, "width": 1920, "height": 1080, "chapters": chapters, "dashboard": primary_dashboard},
    )
    _write_subtitle_plan(reports / "narrated_demo_subtitle_plan.srt", chapters)
    _write_html(reports / "narrated_demo_studio.html", manifest)
    return manifest


def _timestamp(seconds: int) -> str:
    minutes, sec = divmod(seconds, 60)
    return f"00:{minutes:02d}:{sec:02d},000"


def _write_subtitle_plan(path: Path, chapters: list[dict]) -> Path:
    cursor = 0
    rows = []
    for index, chapter in enumerate(chapters, start=1):
        start = cursor
        cursor += int(chapter["duration_seconds"])
        rows.append(f"{index}\n{_timestamp(start)} --> {_timestamp(cursor)}\n{chapter['script']}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows), encoding="utf-8")
    return path


def _write_html(path: Path, manifest: dict) -> Path:
    payload = json.dumps(manifest, sort_keys=True).replace("</", "<\\/")
    chapters = "\n".join(
        f"""<article class="chapter"><div><span>{_esc(item["duration_seconds"])}s</span><strong>{_esc(item["chapter"])}</strong></div><p>{_esc(item["script"])}</p><a href="{_esc(item["visual"])}">{_esc(item["visual"])}</a></article>"""
        for item in manifest["chapters"]
    )
    backends = "\n".join(
        f"""<article class="backend"><strong>{_esc(item["name"])}</strong><code>{_esc(item["command"])}</code><p>{_esc(item["why"])}</p></article>"""
        for item in manifest["natural_voice_backends"]
    )
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><title>{_esc(manifest["project"])} Narrated Demo Studio</title><style>* {{ box-sizing: border-box; }} body {{ margin: 0; background: #f6f8fb; color: #172026; font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }} header {{ background: #111827; color: #fff; padding: 30px 36px; border-bottom: 5px solid #7c3aed; }} main {{ max-width: 1440px; margin: 0 auto; padding: 24px 36px 44px; }} h1 {{ margin: 0; font-size: 30px; line-height: 1.16; }} h2 {{ margin: 0 0 12px; font-size: 17px; }} p {{ line-height: 1.5; }} header p {{ max-width: 920px; color: #d8dee9; }} .hero {{ display: grid; grid-template-columns: minmax(280px, .68fr) minmax(0, 1.32fr); gap: 16px; align-items: stretch; }} .panel {{ background: #fff; border: 1px solid #d8e0ea; border-radius: 8px; padding: 16px; box-shadow: 0 1px 2px rgba(15, 23, 42, .05); }} .score strong {{ display: block; font-size: 44px; line-height: 1; }} .score span, .chapter span, .kpi span {{ color: #64748b; font-size: 12px; font-weight: 850; text-transform: uppercase; }} .actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }} .actions a {{ border: 1px solid #cbd5e1; border-radius: 6px; color: #5b21b6; padding: 9px 12px; font-size: 13px; font-weight: 850; text-decoration: none; }} .chapters {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }} .chapter, .backend {{ min-width: 0; border: 1px solid #dbe3ec; border-radius: 8px; padding: 13px; background: #fbfdff; overflow: hidden; }} .chapter {{ min-height: 210px; display: grid; align-content: space-between; }} .chapter strong, .chapter p, .chapter a, code {{ overflow-wrap: anywhere; }} .chapter strong {{ display: block; margin-top: 8px; font-size: 14px; line-height: 1.3; }} .chapter p, .backend p {{ color: #475569; font-size: 13px; margin: 10px 0; }} .chapter a {{ color: #1d4ed8; font-size: 12px; font-weight: 850; text-decoration: none; }} .backend-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }} code {{ display: block; background: #f1f5f9; border: 1px solid #dbe3ec; border-radius: 6px; padding: 10px; color: #334155; font-size: 12px; }} .kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border: 1px solid #dbe3ec; border-radius: 8px; overflow: hidden; margin-top: 16px; }} .kpi {{ min-height: 78px; padding: 12px; background: #f8fafc; border-right: 1px solid #dbe3ec; }} .kpi:last-child {{ border-right: 0; }} .kpi strong {{ display: block; margin-top: 7px; font-size: 17px; overflow-wrap: anywhere; }} @media (max-width: 980px) {{ header, main {{ padding-left: 18px; padding-right: 18px; }} .hero, .chapters, .backend-grid {{ grid-template-columns: 1fr; }} .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}</style></head><body><header><h1>{_esc(manifest["project"])} Narrated Demo Studio</h1><p>A judge-facing video plan with chapter timing, dashboard shots, evidence-backed narration, natural voice options, Remotion props, and subtitle planning.</p></header><main><section class="hero"><div class="panel score"><span>Total runtime</span><strong>{_esc(manifest["total_duration_seconds"])}s</strong><p>{_esc(manifest["domain"])}</p><div class="actions"><a href="{_esc(manifest["primary_dashboard"])}">Open dashboard</a><a href="{_esc(manifest["demo_video"])}">Open current video</a><a href="remotion_demo_props.json">Remotion props</a><a href="narrated_demo_subtitle_plan.srt">Subtitle plan</a></div></div><div class="panel"><h2>Chapter Timeline</h2><div class="chapters">{chapters}</div></div></section><section class="panel" style="margin-top:16px"><h2>Natural Voice And Video Backends</h2><div class="backend-grid">{backends}</div><div class="kpis"><div class="kpi"><span>Readiness</span><strong>{_esc(manifest["readiness_score"])}%</strong></div><div class="kpi"><span>Evidence</span><strong>{_esc(manifest["evidence_count"])} artifacts</strong></div><div class="kpi"><span>Mesh</span><strong>{_esc(manifest["mesh_status"])}</strong></div><div class="kpi"><span>Mode</span><strong>local-first</strong></div></div></section><section class="panel" style="margin-top:16px"><h2>Narration Source Excerpt</h2><p>{_esc(manifest["script_excerpt"])}</p></section></main><script>window.demoStudio = {payload};</script></body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path
