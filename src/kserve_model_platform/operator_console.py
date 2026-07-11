# ruff: noqa: E501
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ConsoleIdentity:
    product: str
    short_name: str
    code: str
    environment: str
    primary: str
    primary_dark: str
    secondary: str
    warning: str
    dashboard: str


IDENTITY = ConsoleIdentity(
    product="KServe Inference Operations",
    short_name="ServeOps",
    code="KS",
    environment="kserve / canary-lab",
    primary="#2557a7",
    primary_dark="#1d4078",
    secondary="#0f766e",
    warning="#c35a20",
    dashboard="kserve_serving_dashboard.html",
)


_ICONS = {
    "dashboard": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>',
    "review": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/></svg>',
    "drill": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/></svg>',
    "signals": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="16" y="16" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="9" y="2" width="6" height="6" rx="1"/><path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/><path d="M12 12V8"/></svg>',
    "studio": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5"/><rect x="2" y="6" width="14" height="12" rx="2"/></svg>',
    "evidence": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/></svg>',
    "refresh": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5"/><path d="M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5"/></svg>',
}


_NAVIGATION = (
    ("dashboard", "Traffic control", IDENTITY.dashboard),
    ("review", "Release review", "judge_demo_cockpit.html"),
    ("drill", "Rollback drill", "operator_drill_lab.html"),
    ("signals", "Serving signals", "reliability_signal_mesh.html"),
    ("studio", "Demo runbook", "narrated_demo_studio.html"),
    ("evidence", "Runtime evidence", "index.html"),
)


def _navigation(active: str) -> str:
    links = []
    for key, label, href in _NAVIGATION:
        current = ' aria-current="page"' if key == active else ""
        links.append(
            f'<a class="ops-nav-link" href="{href}"{current}>'
            f'<span class="ops-nav-icon">{_ICONS[key]}</span><span>{label}</span></a>'
        )
    return "".join(links)


def _shell(active: str) -> str:
    page_label = next((label for key, label, _ in _NAVIGATION if key == active), "Workspace")
    return f"""
<a class="ops-skip" href="#main-content">Skip to workspace</a>
<aside class="ops-rail" aria-label="{IDENTITY.product} navigation">
  <a class="ops-brand" href="{IDENTITY.dashboard}" aria-label="Open control plane">
    <span class="ops-brand-mark">{IDENTITY.code}</span>
    <span><strong>{IDENTITY.short_name}</strong><small>operator console</small></span>
  </a>
  <div class="ops-environment"><span></span>{IDENTITY.environment}</div>
  <nav class="ops-navigation" aria-label="Primary">{_navigation(active)}</nav>
  <div class="ops-rail-foot"><span>Snapshot mode</span><strong>Deterministic evidence</strong><code>make demo</code></div>
</aside>
<div class="ops-workspace">
  <div class="ops-commandbar">
    <div><span>Workspace</span><strong>{page_label}</strong></div>
    <div class="ops-command-meta"><span class="ops-live"><i></i> generated locally</span><span class="ops-divider"></span><code>evidence://latest</code><button type="button" data-action="refresh" title="Refresh snapshot" aria-label="Refresh snapshot">{_ICONS['refresh']}</button></div>
  </div>
"""


def decorate_console(document: str, *, active: str) -> str:
    """Wrap a generated report in the offline, accessible operator-console shell."""
    if "data-ui-system=\"operator-console-v2\"" in document:
        return document

    document = document.replace(
        "</head>",
        f'<style data-ui-system="operator-console-v2">{_console_css()}</style></head>',
        1,
    )
    def open_body(match: re.Match[str]) -> str:
        attributes = match.group("attributes")
        class_match = re.search(r'\bclass=(["\'])(.*?)\1', attributes)
        if class_match:
            replacement = f'class={class_match.group(1)}operator-console {class_match.group(2)}{class_match.group(1)}'
            attributes = attributes[: class_match.start()] + replacement + attributes[class_match.end() :]
        else:
            attributes = f' class="operator-console"{attributes}'
        return f'<body{attributes} data-product="{IDENTITY.short_name}">{_shell(active)}'

    document, body_count = re.subn(
        r"<body(?P<attributes>[^>]*)>", open_body, document, count=1, flags=re.IGNORECASE
    )
    if body_count != 1:
        raise ValueError("generated console document must contain one body element")
    document = re.sub(
        r"<main(?![^>]*\bid=)(?P<attributes>[^>]*)>",
        r'<main id="main-content"\g<attributes>>',
        document,
        count=1,
        flags=re.IGNORECASE,
    )
    document = document.replace(
        "</body>",
        """</div><script data-ui-system="operator-console-v2">document.querySelector('[data-action="refresh"]')?.addEventListener('click',()=>window.location.reload());</script></body>""",
        1,
    )
    return document


def _console_css() -> str:
    return f"""
:root {{
  --ops-accent: {IDENTITY.primary};
  --ops-accent-dark: {IDENTITY.primary_dark};
  --ops-secondary: {IDENTITY.secondary};
  --ops-warning: {IDENTITY.warning};
  --ops-ink: #171b21;
  --ops-muted: #65707c;
  --ops-canvas: #edf0f2;
  --ops-panel: #ffffff;
  --ops-panel-subtle: #f7f8f9;
  --ops-line: #d5dadd;
  --ops-line-strong: #b9c1c7;
  --ops-rail: #11171c;
  --ops-rail-muted: #89949d;
  --ops-font: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
  --ops-mono: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
  color-scheme: light;
}}
body.operator-console {{ margin: 0; min-width: 320px; background: var(--ops-canvas); color: var(--ops-ink); font-family: var(--ops-font); letter-spacing: 0; }}
body.operator-console * {{ box-sizing: border-box; }}
.ops-skip {{ position: fixed; left: 16px; top: -60px; z-index: 100; background: #fff; color: #111; padding: 10px 14px; border: 2px solid var(--ops-accent); }}
.ops-skip:focus {{ top: 12px; }}
.ops-rail {{ position: fixed; inset: 0 auto 0 0; width: 224px; z-index: 30; display: flex; flex-direction: column; background: var(--ops-rail); color: #fff; border-right: 1px solid #273039; }}
.ops-brand {{ min-height: 82px; display: flex; align-items: center; gap: 12px; padding: 17px 18px; color: #fff; text-decoration: none; border-bottom: 1px solid #2b333a; }}
.ops-brand-mark {{ width: 36px; height: 36px; flex: 0 0 36px; display: grid; place-items: center; border: 1px solid color-mix(in srgb, var(--ops-accent) 72%, white); background: var(--ops-accent-dark); color: #fff; font: 700 12px/1 var(--ops-mono); }}
.ops-brand strong, .ops-brand small {{ display: block; }}
.ops-brand strong {{ font-size: 14px; letter-spacing: .02em; }}
.ops-brand small {{ margin-top: 3px; color: var(--ops-rail-muted); font: 10px/1.2 var(--ops-mono); text-transform: uppercase; }}
.ops-environment {{ margin: 15px 14px 8px; padding: 9px 10px; color: #c7d0d7; border: 1px solid #303942; font: 10px/1.2 var(--ops-mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.ops-environment span {{ display: inline-block; width: 7px; height: 7px; margin-right: 8px; background: #35b37e; box-shadow: 0 0 0 2px #183c31; }}
.ops-navigation {{ display: grid; gap: 2px; padding: 8px 10px; }}
.ops-nav-link {{ min-height: 41px; display: flex; align-items: center; gap: 11px; padding: 9px 10px; border-left: 2px solid transparent; color: #aeb7bf; text-decoration: none; font-size: 13px; }}
.ops-nav-link:hover {{ color: #fff; background: #1a2229; }}
.ops-nav-link[aria-current="page"] {{ color: #fff; border-left-color: var(--ops-accent); background: #202a31; }}
.ops-nav-icon {{ width: 18px; height: 18px; flex: 0 0 18px; }}
.ops-nav-icon svg, .ops-commandbar button svg {{ width: 100%; height: 100%; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }}
.ops-rail-foot {{ margin: auto 16px 18px; padding-top: 14px; border-top: 1px solid #2b333a; }}
.ops-rail-foot span, .ops-rail-foot strong, .ops-rail-foot code {{ display: block; }}
.ops-rail-foot span {{ color: var(--ops-rail-muted); font: 9px/1.4 var(--ops-mono); text-transform: uppercase; }}
.ops-rail-foot strong {{ margin: 4px 0 7px; color: #dfe5e9; font-size: 11px; }}
.ops-rail-foot code {{ color: #84d6b6; font: 10px/1.4 var(--ops-mono); }}
.ops-workspace {{ min-height: 100vh; margin-left: 224px; }}
.ops-commandbar {{ position: sticky; top: 0; z-index: 20; min-height: 50px; display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 7px 24px; background: rgba(255,255,255,.97); border-bottom: 1px solid var(--ops-line); }}
.ops-commandbar > div:first-child {{ display: flex; align-items: baseline; gap: 8px; }}
.ops-commandbar span {{ color: var(--ops-muted); font: 9px/1 var(--ops-mono); text-transform: uppercase; }}
.ops-commandbar strong {{ font-size: 12px; }}
.ops-command-meta {{ display: flex; align-items: center; gap: 10px; }}
.ops-command-meta code {{ color: #4e5963; font: 10px/1 var(--ops-mono); }}
.ops-live i {{ display: inline-block; width: 6px; height: 6px; margin-right: 6px; background: #2e9f70; }}
.ops-divider {{ width: 1px; height: 18px; background: var(--ops-line); }}
.ops-commandbar button {{ width: 30px; height: 30px; display: grid; place-items: center; border: 1px solid var(--ops-line-strong); border-radius: 2px; background: #fff; color: #44505a; cursor: pointer; }}
.ops-commandbar button:hover {{ border-color: var(--ops-accent); color: var(--ops-accent-dark); }}
.ops-commandbar button svg {{ width: 15px; height: 15px; }}
body.operator-console .ops-workspace > header {{ padding: 24px 28px 22px; background: var(--ops-panel); color: var(--ops-ink); border: 0; border-bottom: 1px solid var(--ops-line); }}
body.operator-console .ops-workspace > header::before, body.operator-console main > header::before {{ content: "OPERATIONS / EVIDENCE SNAPSHOT"; display: block; margin-bottom: 8px; color: var(--ops-accent-dark); font: 700 10px/1 var(--ops-mono); }}
body.operator-console header h1 {{ color: var(--ops-ink); font-size: 25px; line-height: 1.2; letter-spacing: 0; }}
body.operator-console header p {{ max-width: 980px; margin: 7px 0 0; color: var(--ops-muted); font-size: 13px; line-height: 1.5; }}
body.operator-console main {{ width: auto; max-width: none; margin: 0; padding: 18px 24px 40px; }}
body.operator-console main > header {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: end; gap: 16px 24px; margin: -18px -24px 18px; padding: 24px 28px 22px; background: var(--ops-panel); border: 0; border-bottom: 1px solid var(--ops-line); }}
body.operator-console main > header::before {{ grid-column: 1 / -1; }}
body.operator-console h1, body.operator-console h2, body.operator-console h3 {{ letter-spacing: 0; }}
body.operator-console h2 {{ font-size: 14px; line-height: 1.3; }}
body.operator-console .grid:not([aria-label="Generated artifacts"]) {{ grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0; margin: 0 0 14px; overflow: hidden; border: 1px solid var(--ops-line-strong); background: var(--ops-panel); }}
body.operator-console .grid[aria-label="Generated artifacts"] {{ grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 0; margin-top: 14px; border: 1px solid var(--ops-line-strong); }}
body.operator-console .metric {{ min-height: 96px; margin: 0; padding: 14px; border: 0; border-right: 1px solid var(--ops-line); border-bottom: 1px solid var(--ops-line); border-radius: 0; box-shadow: none; background: var(--ops-panel); }}
body.operator-console .metric span {{ color: var(--ops-muted); font: 10px/1.25 var(--ops-mono); text-transform: uppercase; }}
body.operator-console .metric strong {{ margin-top: 9px; font-size: 21px; font-weight: 650; }}
body.operator-console .panel {{ border: 1px solid var(--ops-line-strong); border-top: 3px solid #2f3941; border-radius: 2px; box-shadow: none; background: var(--ops-panel); }}
body.operator-console .panel h2 {{ padding-bottom: 10px; border-bottom: 1px solid var(--ops-line); }}
body.operator-console .layout, body.operator-console .lower-grid {{ gap: 12px; }}
body.operator-console table {{ border-color: var(--ops-line); border-radius: 0; background: #fff; }}
body.operator-console th, body.operator-console td {{ padding: 9px 10px; border-color: #e1e4e6; font-size: 12px; line-height: 1.4; }}
body.operator-console th {{ background: #f0f2f3; color: #3e4850; font: 700 10px/1.3 var(--ops-mono); text-transform: uppercase; }}
body.operator-console tbody tr:hover td {{ background: #f7faf9; }}
body.operator-console .badge, body.operator-console .sev, body.operator-console .chip {{ border-radius: 2px; font-family: var(--ops-mono); font-size: 10px; letter-spacing: .01em; }}
body.operator-console .pass {{ color: #075f46; background: #dff3ea; }}
body.operator-console .fail, body.operator-console .critical, body.operator-console .high {{ color: #9a2b31; background: #f8e3e5; }}
body.operator-console .neutral {{ color: #4b5560; background: #e9ecef; }}
body.operator-console .chip {{ color: var(--ops-secondary); background: #e8eef7; }}
body.operator-console button, body.operator-console .actions a, body.operator-console .theater-links a, body.operator-console .cue {{ border-radius: 2px; box-shadow: none; }}
body.operator-console .evidence-deck, body.operator-console .planner {{ border-left-width: 1px; border-top-color: var(--ops-secondary); }}
body.operator-console .evidence-grid {{ gap: 0; border: 1px solid var(--ops-line); }}
body.operator-console .evidence-card {{ min-height: 138px; border: 0; border-right: 1px solid var(--ops-line); border-bottom: 1px solid var(--ops-line); border-radius: 0; background: #fafbfb; }}
body.operator-console .evidence-card span {{ font-family: var(--ops-mono); }}
body.operator-console .demo-theater {{ border-left-width: 1px; border-top-color: var(--ops-warning); }}
body.operator-console .theater-stage {{ border-radius: 2px; border-color: #2c3943; background: #172129; color: #fff; }}
body.operator-console .theater-stage span {{ color: #8fd4b9; font-family: var(--ops-mono); }}
body.operator-console .theater-stage p {{ color: #c9d1d6; }}
body.operator-console .cue.active {{ background: var(--ops-accent-dark); border-color: var(--ops-accent-dark); }}
body.operator-console .theater-progress, body.operator-console .bar {{ height: 7px; border-radius: 0; }}
body.operator-console .theater-progress span, body.operator-console .bar span {{ background: var(--ops-accent); }}
body.operator-console .facts, body.operator-console .kpis, body.operator-console .theater-kpis {{ border-radius: 0; }}
body.operator-console .cards {{ gap: 0; border: 1px solid var(--ops-line-strong); }}
body.operator-console .card {{ min-height: 132px; padding: 14px; border: 0; border-right: 1px solid var(--ops-line); border-bottom: 1px solid var(--ops-line); border-radius: 0; box-shadow: none; background: var(--ops-panel); }}
body.operator-console .card:hover {{ transform: none; background: #f7faf9; border-color: var(--ops-line); }}
body.operator-console .card .label {{ color: var(--ops-accent-dark); font-family: var(--ops-mono); }}
body.operator-console code {{ font-family: var(--ops-mono); }}
body.operator-console a:focus-visible, body.operator-console button:focus-visible {{ outline: 3px solid color-mix(in srgb, var(--ops-accent) 45%, white); outline-offset: 2px; }}
@media (max-width: 960px) {{
  .ops-rail {{ position: relative; width: 100%; min-height: 0; border-right: 0; }}
  .ops-brand {{ min-height: 64px; }}
  .ops-environment, .ops-rail-foot {{ display: none; }}
  .ops-navigation {{ grid-template-columns: repeat(6, minmax(132px, 1fr)); overflow-x: auto; padding: 5px 10px 9px; }}
  .ops-nav-link {{ min-height: 38px; white-space: nowrap; }}
  .ops-workspace {{ margin-left: 0; }}
  .ops-commandbar {{ position: relative; padding: 7px 16px; }}
  .ops-command-meta code, .ops-divider {{ display: none; }}
  body.operator-console main {{ padding: 14px 14px 32px; }}
  body.operator-console main > header {{ grid-template-columns: 1fr; margin: -14px -14px 14px; padding: 20px 18px; }}
  body.operator-console .ops-workspace > header {{ padding: 20px 18px; }}
}}
@media (max-width: 620px) {{
  .ops-commandbar > div:first-child > span, .ops-live {{ display: none; }}
  body.operator-console header h1 {{ font-size: 21px; }}
  body.operator-console .metric strong {{ font-size: 18px; }}
  body.operator-console .evidence-grid {{ grid-template-columns: 1fr; }}
}}
@media (prefers-reduced-motion: reduce) {{ *, *::before, *::after {{ scroll-behavior: auto !important; transition: none !important; }} }}
"""
