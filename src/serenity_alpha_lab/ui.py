from __future__ import annotations

from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
from socketserver import TCPServer, ThreadingMixIn
import threading
from typing import Callable, Mapping, Sequence
from urllib.parse import parse_qs, quote, urlencode, urlparse
from uuid import uuid4

from .evidence import EvidenceItem, load_evidence_files, tokenize
from .stock_universe import StockUniverseEntry
from .topic_resolver import resolve_topic


TableRow = dict[str, str]
AnalyzeCallback = Callable[..., Path]
IngestCallback = Callable[[Mapping[str, str]], Path]
ResolveCallback = Callable[..., Mapping[str, object]]
METRIC_FIELDS = ["revenue_growth", "gross_margin", "valuation", "momentum", "cycle_position"]


class ReusableTCPServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True
    daemon_threads = True


RUN_RECORD_LOCK = threading.Lock()


def load_metrics_catalog(path: Path | str) -> dict[str, dict[str, str]]:
    metrics_path = Path(path)
    if not metrics_path.exists():
        return {}
    try:
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, list):
        return {}

    catalog: dict[str, dict[str, str]] = {}
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        ticker = str(entry.get("ticker", "")).strip().upper().lstrip("$")
        if not ticker:
            continue
        catalog[ticker] = {
            field: str(entry.get(field, "") or "").strip()
            for field in METRIC_FIELDS
        }
    return catalog


def _load_metrics_for_output(output_path: Path) -> dict[str, dict[str, str]]:
    config_metrics = Path("config") / "financial_metrics.json"
    metrics = load_metrics_catalog(config_metrics) if _is_project_output(output_path) else {}
    if metrics:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config_metrics, output_path.parent / "metrics.json")
        return metrics

    for directory in (output_path.parent, *output_path.parent.parents):
        metrics = load_metrics_catalog(directory / "metrics.json")
        if metrics:
            return metrics
    return {}


def _is_project_output(output_path: Path) -> bool:
    try:
        output_path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        return False
    return True


def build_dashboard(
    *,
    readiness_path: Path | str = "output/reports/cpo-readiness-guarded.md",
    pack_dir: Path | str = "output/packs/cpo-guarded",
    output_path: Path | str = "output/ui/index.html",
    language: str = "both",
) -> Path:
    readiness = Path(readiness_path)
    memo_pack_dir = Path(pack_dir)
    output = Path(output_path)
    if language not in {"en", "zh", "both"}:
        raise ValueError("language must be one of: en, zh, both")

    readiness_text = readiness.read_text(encoding="utf-8")
    index_text = (memo_pack_dir / "index.md").read_text(encoding="utf-8")
    sources_text = (memo_pack_dir / "sources.md").read_text(encoding="utf-8")

    readiness_rows = _parse_readiness_rows(readiness_text)
    memo_rows = _parse_pack_rows(index_text)
    analysis_history = _load_analysis_history(output.parent / "analyses" / "manifest.json")
    metrics_by_ticker = _load_metrics_for_output(output)
    imported_evidence = _load_imported_evidence_for_output(output)
    served_pack_dir = _copy_pack_for_serving(memo_pack_dir, output.parent / "pack")
    _copy_reports_for_serving(output.parent)
    memo_rows = _attach_memo_hrefs(memo_rows, served_pack_dir, output.parent)
    memo_previews = _load_memo_previews(memo_rows, served_pack_dir, output.parent)
    primary_sources = _parse_primary_sources(sources_text)
    query = _extract_bold_value(readiness_text, "Research question") or _extract_bold_value(index_text, "Research question")
    _write_deliverable_report(
        output.parent,
        query or "Research dashboard",
        memo_rows,
        memo_previews,
        primary_sources,
    )
    operational_reports = _load_operational_reports(output.parent)

    output.parent.mkdir(parents=True, exist_ok=True)
    if language in {"en", "both"}:
        output.write_text(
            render_dashboard_html(
                title="Serenity Alpha Lab",
                query=query or "Research dashboard",
                readiness_rows=readiness_rows,
                memo_rows=memo_rows,
                memo_previews=memo_previews,
                analysis_history=analysis_history,
                operational_reports=operational_reports,
                metrics_by_ticker=metrics_by_ticker,
                primary_sources=primary_sources,
                imported_evidence=imported_evidence,
                language="en",
                alternate_href="index.zh.html" if language == "both" else "",
            ),
            encoding="utf-8",
        )
    if language in {"zh", "both"}:
        zh_output = _localized_output_path(output, "zh") if language == "both" else output
        zh_output.write_text(
            render_dashboard_html(
                title="Serenity Alpha Lab",
                query=query or "Research dashboard",
                readiness_rows=readiness_rows,
                memo_rows=memo_rows,
                memo_previews=memo_previews,
                analysis_history=analysis_history,
                operational_reports=operational_reports,
                metrics_by_ticker=metrics_by_ticker,
                primary_sources=primary_sources,
                imported_evidence=imported_evidence,
                language="zh",
                alternate_href=output.name if language == "both" else "",
            ),
            encoding="utf-8",
        )
    return output


def serve_dashboard(
    *,
    output_path: Path | str = "output/ui/index.html",
    host: str = "127.0.0.1",
    port: int = 8000,
    analyze_callback: AnalyzeCallback | None = None,
    ingest_callback: IngestCallback | None = None,
    resolve_callback: ResolveCallback | None = None,
) -> None:
    output = Path(output_path)
    if not output.exists():
        raise FileNotFoundError(f"Dashboard HTML does not exist: {output}")

    handler = _build_dashboard_handler(
        output.parent,
        analyze_callback,
        ingest_callback=ingest_callback,
        resolve_callback=resolve_callback,
    )
    with ReusableTCPServer((host, port), handler) as server:
        print(f"Serving Serenity Alpha Lab UI at http://{host}:{port}/{output.name}")
        server.serve_forever()


def render_dashboard_html(
    *,
    title: str,
    query: str,
    readiness_rows: Sequence[Mapping[str, str]],
    memo_rows: Sequence[Mapping[str, str]],
    memo_previews: Sequence[Mapping[str, object]],
    primary_sources: Sequence[Mapping[str, str]],
    analysis_history: Sequence[Mapping[str, object]] = (),
    operational_reports: Sequence[Mapping[str, str]] = (),
    metrics_by_ticker: Mapping[str, Mapping[str, str]] | None = None,
    imported_evidence: Sequence[Mapping[str, object]] = (),
    language: str = "en",
    alternate_href: str = "",
) -> str:
    copy = _copy(language)
    copy["query"] = query
    ready_count = sum(1 for row in memo_rows if row.get("status") == "ready")
    skipped_count = sum(1 for row in memo_rows if row.get("status") != "ready")
    evidence_total = sum(_to_int(row.get("evidence", "0")) for row in memo_rows)
    primary_total = sum(_to_int(row.get("primary", "0")) for row in memo_rows)
    risk_total = sum(_to_int(row.get("risk", "0")) for row in memo_rows)
    pack_health = "Ready" if memo_rows and skipped_count == 0 else "Needs Review"

    readiness_table = _render_readiness_table(readiness_rows, copy)
    memo_cards = _render_memo_cards(memo_rows, copy)
    memo_sections = _render_memo_previews(memo_previews, copy)
    comparison_table = _render_candidate_comparison(memo_rows, memo_previews, copy, metrics_by_ticker or {})
    report_library = _render_analysis_history(analysis_history, copy, language)
    localized_operational_reports = _localize_operational_reports(operational_reports, copy)
    analysis_briefing = _render_analysis_briefing(
        memo_rows=memo_rows,
        memo_previews=memo_previews,
        operational_reports=localized_operational_reports,
        copy=copy,
    )
    research_action_workbench = _render_research_action_workbench(
        memo_rows=memo_rows,
        memo_previews=memo_previews,
        operational_reports=localized_operational_reports,
        copy=copy,
    )
    decision_workbench = _render_decision_workbench(
        memo_rows=memo_rows,
        memo_previews=memo_previews,
        metrics_by_ticker=metrics_by_ticker or {},
        copy=copy,
    )
    quality_snapshot = _report_quality_snapshot(memo_rows, memo_previews)
    report_quality_gate = _render_report_quality_gate(
        memo_rows=memo_rows,
        memo_previews=memo_previews,
        copy=copy,
        snapshot=quality_snapshot,
    )
    saved_workspace = _render_saved_workspace(copy)
    research_project_library = _render_research_project_library(copy)
    deliverable_report = _render_deliverable_report(copy)
    delivery_package = _render_delivery_package(localized_operational_reports, copy, quality_snapshot)
    evidence_tasks = _render_evidence_tasks(
        localized_operational_reports,
        copy,
        imported_evidence,
        quality_snapshot=quality_snapshot,
    )
    operational_report_cards = _render_operational_reports(localized_operational_reports, copy)
    sources = _render_sources(primary_sources, copy)
    status_options = _render_status_options(memo_rows)
    lang_switch = (
        f'<a href="{escape(alternate_href)}">{escape(copy["alternate_language"])}</a>'
        if alternate_href
        else ""
    )
    html_lang = "zh-CN" if language == "zh" else "en"
    localized_pack_health = _localized_status(pack_health, language)
    language_value = "zh" if language == "zh" else "en"

    return f"""<!doctype html>
<html lang="{html_lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} | {escape(copy["title_suffix"])}</title>
  <style>
    :root {{
      --bg: #f5f2eb;
      --surface: #fffdf8;
      --surface-2: #f1f6f4;
      --ink: #18212b;
      --muted: #5d6975;
      --line: #d9ded9;
      --accent: #0f766e;
      --accent-2: #8b5e34;
      --success-bg: #dff5e8;
      --success-ink: #14532d;
      --warn-bg: #fff1d6;
      --warn-ink: #7c3d12;
      --risk: #9f1239;
      --shadow: 0 18px 50px rgba(24, 33, 43, 0.10);
      color-scheme: light;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background:
        linear-gradient(135deg, rgba(15, 118, 110, 0.11), transparent 34rem),
        linear-gradient(315deg, rgba(139, 94, 52, 0.10), transparent 30rem),
        var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 16px;
      line-height: 1.55;
    }}
    a {{ color: inherit; }}
    a:focus-visible, button:focus-visible {{
      outline: 3px solid rgba(15, 118, 110, 0.45);
      outline-offset: 3px;
    }}
    .skip {{
      position: absolute;
      left: -999px;
      top: 1rem;
      background: var(--ink);
      color: white;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      z-index: 10;
    }}
    .skip:focus {{ left: 1rem; }}
    .shell {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}
    .topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 24px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }}
    .mark {{
      width: 44px;
      height: 44px;
      border-radius: 8px;
      background: linear-gradient(135deg, var(--accent), #153f3b);
      box-shadow: 0 10px 24px rgba(15, 118, 110, 0.25);
      display: grid;
      place-items: center;
      color: #fff;
      font-weight: 800;
      font-variant-numeric: tabular-nums;
    }}
    h1, h2, h3 {{ margin: 0; line-height: 1.15; }}
    h1 {{ font-size: clamp(1.7rem, 4vw, 3.2rem); letter-spacing: 0; }}
    h2 {{ font-size: clamp(1.25rem, 2.2vw, 1.75rem); }}
    h3 {{ font-size: 1rem; }}
    .eyebrow {{
      color: var(--accent-2);
      font-size: 0.78rem;
      font-weight: 760;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .nav {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .nav a, .memo-link {{
      min-height: 44px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0.65rem 0.9rem;
      background: rgba(255, 253, 248, 0.72);
      color: var(--ink);
      text-decoration: none;
      font-weight: 650;
    }}
    .memo-link {{
      cursor: pointer;
    }}
    .launcher {{
      display: grid;
      grid-template-columns: minmax(240px, 1fr) auto;
      gap: 10px;
      align-items: end;
      margin-bottom: 20px;
      padding: 18px;
      background: rgba(241, 246, 244, 0.92);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .launcher p {{
      grid-column: 1 / -1;
      margin: 0;
      color: var(--muted);
    }}
    .launcher-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: end;
    }}
    .launcher-actions button {{
      flex: 1 1 180px;
    }}
    .input-preview {{
      grid-column: 1 / -1;
      display: grid;
      gap: 12px;
      padding: 16px;
      border: 1px solid rgba(15, 118, 110, 0.24);
      border-radius: 8px;
      background: #edf7f3;
    }}
    .input-preview header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
    }}
    .input-preview-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}
    .input-preview-grid div {{
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
    }}
    .input-preview-grid dt {{
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 800;
    }}
    .input-preview-grid dd {{
      margin: 4px 0 0;
      font-weight: 800;
      word-break: break-word;
    }}
    .candidate-coverage {{
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
    }}
    .candidate-coverage strong {{
      color: var(--ink);
      font-size: 0.9rem;
    }}
    .candidate-coverage-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .candidate-coverage-chip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #f8fafc;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 700;
      line-height: 1.35;
    }}
    .candidate-coverage-chip b {{
      color: var(--ink);
      font-size: 0.82rem;
    }}
    .filters {{
      display: grid;
      grid-template-columns: minmax(240px, 1fr) minmax(160px, 220px) auto;
      gap: 10px;
      align-items: end;
      margin-bottom: 20px;
      padding: 16px;
      background: rgba(255, 253, 248, 0.82);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .field {{
      display: grid;
      gap: 6px;
    }}
    label {{
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 750;
    }}
    input[type="search"], select {{
      min-height: 44px;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      color: var(--ink);
      font: inherit;
      padding: 0.65rem 0.8rem;
    }}
    button {{
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #163f3b;
      color: #fff;
      cursor: pointer;
      font: inherit;
      font-weight: 760;
      padding: 0.65rem 0.9rem;
    }}
    button:disabled {{
      cursor: wait;
      opacity: 0.78;
    }}
    .launch-status {{
      grid-column: 1 / -1;
      margin: 0;
      color: var(--accent);
      font-weight: 760;
    }}
    .workbench {{
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(280px, 0.85fr);
      gap: 14px;
      margin-bottom: 20px;
    }}
    .workflow-card,
    .example-card {{
      padding: 18px;
      background: rgba(255, 253, 248, 0.9);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .workflow-steps {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }}
    .workflow-step {{
      display: grid;
      gap: 6px;
      padding: 12px;
      min-height: 116px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f7f6f0;
    }}
    .workflow-step span {{
      display: inline-grid;
      place-items: center;
      width: 28px;
      height: 28px;
      border-radius: 999px;
      background: var(--accent);
      color: #fff;
      font-size: 0.82rem;
      font-weight: 850;
      font-variant-numeric: tabular-nums;
    }}
    .workflow-step strong {{
      display: block;
    }}
    .workflow-step p,
    .example-card p {{
      margin: 0;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .example-actions {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 14px;
    }}
    .example-actions button {{
      background: var(--surface);
      color: var(--ink);
    }}
    .run-center {{
      display: grid;
      grid-template-columns: minmax(0, 0.75fr) minmax(0, 1.25fr) auto;
      gap: 14px;
      align-items: stretch;
      margin-bottom: 20px;
      padding: 18px;
      background: rgba(255, 253, 248, 0.92);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .run-summary {{
      display: grid;
      gap: 8px;
    }}
    .run-summary p {{
      margin: 0;
      color: var(--muted);
    }}
    .run-steps {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
    }}
    .run-step {{
      display: grid;
      gap: 4px;
      min-height: 92px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f7f6f0;
      color: var(--muted);
      font-size: 0.88rem;
    }}
    .run-step strong {{
      color: var(--ink);
      font-size: 0.92rem;
    }}
    .run-step[data-run-state="active"] {{
      border-color: rgba(15, 118, 110, 0.42);
      background: #ecf7f3;
      color: var(--accent);
    }}
    .run-step[data-run-state="done"] {{
      background: var(--success-bg);
      color: var(--success-ink);
    }}
    .run-actions {{
      display: grid;
      align-content: center;
      gap: 8px;
    }}
    .run-actions button {{
      white-space: nowrap;
    }}
    .run-history {{
      grid-column: 1 / -1;
      display: grid;
      gap: 10px;
      padding-top: 2px;
    }}
    .run-history h3 {{
      margin: 0;
      font-size: 1rem;
    }}
    .run-history-list {{
      display: grid;
      gap: 8px;
    }}
    .run-history-empty {{
      margin: 0;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .run-history-item {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
    }}
    .run-history-item[data-run-status="failed"] {{
      border-color: rgba(185, 28, 28, 0.28);
      background: #fff7f2;
    }}
    .run-history-meta {{
      display: grid;
      gap: 3px;
      min-width: 0;
    }}
    .run-history-meta strong {{
      color: var(--ink);
    }}
    .run-history-meta span,
    .run-history-meta small {{
      color: var(--muted);
      word-break: break-word;
    }}
    .run-history-controls {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
    }}
    .run-history-controls button {{
      min-height: 38px;
      padding: 0.48rem 0.7rem;
      white-space: nowrap;
    }}
    .run-history-controls button[disabled] {{
      opacity: 0.5;
      cursor: not-allowed;
    }}
    .result-count {{
      margin: -6px 0 16px;
      color: var(--muted);
      font-weight: 700;
    }}
    [hidden] {{ display: none !important; }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
      gap: 20px;
      align-items: stretch;
      margin-bottom: 20px;
    }}
    .panel {{
      background: rgba(255, 253, 248, 0.90);
      border: 1px solid rgba(217, 222, 217, 0.95);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }}
    .hero-copy {{ padding: clamp(22px, 4vw, 36px); }}
    .subtitle {{
      max-width: 68ch;
      margin-top: 14px;
      color: var(--muted);
      font-size: 1.05rem;
    }}
    .query {{
      margin-top: 20px;
      padding: 14px 16px;
      border-left: 4px solid var(--accent);
      background: var(--surface-2);
      border-radius: 8px;
      font-weight: 680;
    }}
    .status-card {{
      padding: 22px;
      display: grid;
      gap: 14px;
    }}
    .health {{
      display: inline-flex;
      align-items: center;
      width: fit-content;
      min-height: 32px;
      border-radius: 999px;
      padding: 0.25rem 0.75rem;
      background: {("#dff5e8" if pack_health == "Ready" else "#fff1d6")};
      color: {("#14532d" if pack_health == "Ready" else "#7c3d12")};
      font-weight: 800;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}
    .analysis-briefing {{
      display: grid;
      grid-template-columns: 1.15fr 1fr;
      gap: 14px;
      margin-bottom: 20px;
      padding: 18px;
      background: rgba(255, 253, 248, 0.9);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .briefing-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }}
    .briefing-card {{
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
    }}
    .briefing-card span {{
      display: block;
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 750;
    }}
    .briefing-card strong {{
      display: block;
      margin-top: 4px;
      font-size: 1.02rem;
    }}
    .briefing-actions {{
      display: grid;
      align-content: start;
      gap: 10px;
    }}
    .briefing-actions ul {{
      margin: 0;
      padding-left: 1.1rem;
      color: var(--muted);
      display: grid;
      gap: 8px;
    }}
    .briefing-action-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .research-action-workbench {{
      display: grid;
      grid-template-columns: 1.05fr 1.35fr;
      gap: 14px;
      margin-bottom: 20px;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.98);
      box-shadow: 0 12px 30px rgba(24, 33, 43, 0.06);
    }}
    .research-action-summary {{
      display: grid;
      align-content: start;
      gap: 10px;
    }}
    .research-action-list {{
      display: grid;
      gap: 10px;
    }}
    .research-action-card {{
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(247, 250, 249, 0.95);
    }}
    .research-action-card span {{
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .research-action-card strong {{
      overflow-wrap: anywhere;
    }}
    .research-action-controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .decision-workbench {{
      display: grid;
      grid-template-columns: 0.95fr 1.35fr;
      gap: 14px;
      margin-bottom: 20px;
      padding: 18px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .decision-summary {{
      display: grid;
      align-content: start;
      gap: 10px;
      padding-right: 8px;
    }}
    .decision-disclaimer {{
      width: fit-content;
      padding: 6px 10px;
      border-radius: 999px;
      background: #eef2ff;
      color: #3730a3;
      font-size: 0.82rem;
      font-weight: 800;
    }}
    .decision-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .decision-card {{
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
    }}
    .decision-card h3 {{
      margin: 0;
      font-size: 0.96rem;
    }}
    .decision-card p, .decision-card ul {{
      margin: 0;
      color: var(--muted);
    }}
    .decision-card ul {{
      padding-left: 1.1rem;
      display: grid;
      gap: 6px;
    }}
    .decision-controls {{
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .decision-controls label {{
      font-weight: 800;
      color: var(--ink);
    }}
    .decision-controls select {{
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0 12px;
      background: var(--surface-2);
      color: var(--ink);
      font: inherit;
    }}
    .decision-rank-list {{
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }}
    .decision-rank-card {{
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 10px;
      align-items: center;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
    }}
    .decision-rank-card strong {{
      display: block;
    }}
    .decision-rank-card small {{
      color: var(--muted);
    }}
    .decision-rank-card .rank {{
      display: inline-grid;
      place-items: center;
      min-width: 30px;
      height: 30px;
      border-radius: 999px;
      background: var(--ink);
      color: #fff;
      font-weight: 850;
      font-variant-numeric: tabular-nums;
    }}
    .decision-rank-card .rank-score {{
      color: var(--muted);
      font-weight: 800;
      font-variant-numeric: tabular-nums;
    }}
    .report-quality-gate {{
      display: grid;
      grid-template-columns: 0.9fr 1.4fr;
      gap: 14px;
      margin-bottom: 20px;
      padding: 18px;
      background: rgba(248, 250, 252, 0.96);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .quality-summary {{
      display: grid;
      align-content: start;
      gap: 10px;
    }}
    .quality-status {{
      width: fit-content;
      min-height: 32px;
      display: inline-flex;
      align-items: center;
      padding: 0.25rem 0.75rem;
      border-radius: 999px;
      background: #fff1d6;
      color: #7c3d12;
      font-weight: 850;
    }}
    .quality-status[data-quality-status="publishable"] {{
      background: #dff5e8;
      color: #14532d;
    }}
    .quality-status[data-quality-status="not-publishable"] {{
      background: #fee2e2;
      color: #991b1b;
    }}
    .quality-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .quality-card {{
      display: grid;
      gap: 6px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
    }}
    .quality-card span {{
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 800;
    }}
    .quality-card strong {{
      font-size: 1.08rem;
    }}
    .quality-checklist {{
      grid-column: 1 / -1;
      margin: 0;
      padding-left: 1.1rem;
      color: var(--muted);
      display: grid;
      gap: 6px;
    }}
    .saved-workspace {{
      display: grid;
      grid-template-columns: 0.9fr 1.4fr;
      gap: 14px;
      margin-bottom: 20px;
      padding: 18px;
      background: rgba(255, 253, 248, 0.96);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .workspace-summary {{
      display: grid;
      align-content: start;
      gap: 10px;
    }}
    .workspace-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .workspace-actions button {{
      min-height: 44px;
    }}
    .workspace-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .workspace-card {{
      display: grid;
      gap: 6px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
      min-width: 0;
    }}
    .workspace-card span {{
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 800;
    }}
    .workspace-card strong {{
      overflow-wrap: anywhere;
    }}
    .workspace-card small {{
      color: var(--muted);
      overflow-wrap: anywhere;
    }}
    .research-project-library {{
      display: grid;
      grid-template-columns: 0.9fr 1.4fr;
      gap: 14px;
      margin-bottom: 20px;
      padding: 18px;
      background: rgba(248, 250, 252, 0.98);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .project-library-summary {{
      display: grid;
      align-content: start;
      gap: 10px;
    }}
    .project-library-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .project-library-actions button {{
      min-height: 44px;
    }}
    .project-library-tools {{
      display: grid;
      grid-template-columns: 0.9fr 1.4fr;
      gap: 10px;
      align-items: stretch;
      margin-bottom: 10px;
    }}
    .project-library-filter {{
      display: grid;
      gap: 6px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .project-library-filter label {{
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 800;
    }}
    .project-library-filter select {{
      min-height: 44px;
      border-radius: 8px;
      border: 1px solid var(--line);
      padding: 0.45rem 0.55rem;
      background: #fff;
    }}
    .project-library-filter input {{
      min-height: 44px;
      border-radius: 8px;
      border: 1px solid var(--line);
      padding: 0.45rem 0.55rem;
      background: #fff;
    }}
    .project-comparison-summary {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .project-comparison-summary span {{
      color: var(--muted);
      font-size: 0.76rem;
      font-weight: 800;
    }}
    .project-comparison-summary strong {{
      display: block;
      font-size: 1rem;
      margin-top: 3px;
    }}
    .project-next-action-queue-summary,
    .project-owner-queue-summary {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 10px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .project-next-action-queue-summary header,
    .project-owner-queue-summary header {{
      grid-column: 1 / -1;
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: baseline;
    }}
    .project-next-action-queue-summary h3,
    .project-owner-queue-summary h3 {{
      margin: 0;
      font-size: 0.98rem;
    }}
    .project-next-action-queue-summary small,
    .project-owner-queue-summary small {{
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 700;
    }}
    .project-next-action-queue-summary button,
    .project-owner-queue-summary button {{
      min-height: 44px;
      text-align: left;
      border: 1px solid var(--line);
      background: rgba(248, 250, 252, 0.96);
      color: var(--text);
    }}
    .project-next-action-queue-summary button strong,
    .project-owner-queue-summary button strong {{
      display: block;
      font-size: 1rem;
      margin-top: 2px;
    }}
    .project-queue-handoff-preview {{
      display: grid;
      gap: 8px;
      margin-bottom: 10px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .project-queue-handoff-preview header {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: flex-start;
    }}
    .project-queue-handoff-preview h3 {{
      margin: 0;
      font-size: 0.98rem;
    }}
    .project-queue-handoff-preview small {{
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 700;
    }}
    .project-queue-handoff-preview strong {{
      color: var(--text);
      font-size: 0.92rem;
    }}
    .project-queue-handoff-preview pre {{
      max-height: 180px;
      margin: 0;
      padding: 10px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(248, 250, 252, 0.96);
      color: var(--text);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      font-size: 0.78rem;
      line-height: 1.5;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }}
    .project-comparison-matrix {{
      display: grid;
      gap: 10px;
      margin-bottom: 10px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .project-comparison-matrix header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
    }}
    .project-comparison-matrix h3 {{
      margin: 0;
      font-size: 1rem;
    }}
    .project-comparison-matrix p {{
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 0.86rem;
    }}
    .project-comparison-table-wrap {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
    }}
    .project-comparison-table {{
      width: 100%;
      min-width: 720px;
      border-collapse: collapse;
      font-size: 0.86rem;
    }}
    .project-comparison-table th,
    .project-comparison-table td {{
      padding: 0.6rem 0.65rem;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    .project-comparison-table th {{
      color: var(--muted);
      font-size: 0.74rem;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      background: rgba(248, 250, 252, 0.96);
    }}
    .project-comparison-table tr:last-child td {{
      border-bottom: 0;
    }}
    .project-library-list {{
      display: grid;
      gap: 10px;
      max-height: 360px;
      overflow: auto;
      padding-right: 2px;
    }}
    .project-library-item {{
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
    }}
    .project-library-item header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
    }}
    .project-library-item strong,
    .project-library-item small {{
      overflow-wrap: anywhere;
    }}
    .project-library-item small {{
      color: var(--muted);
    }}
    .project-library-controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .project-library-controls select {{
      min-height: 40px;
      border-radius: 8px;
      border: 1px solid var(--line);
      padding: 0.45rem 0.55rem;
      background: #fff;
    }}
    .project-detail-drawer {{
      position: fixed;
      inset: 0 0 0 auto;
      width: min(460px, 100vw);
      padding: 22px;
      background: #fff;
      border-left: 1px solid var(--line);
      box-shadow: -22px 0 50px rgba(24, 33, 43, 0.18);
      transform: translateX(105%);
      transition: transform 220ms ease;
      z-index: 70;
      overflow: auto;
    }}
    .project-detail-drawer.is-open {{
      transform: translateX(0);
    }}
    .project-detail-drawer header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 14px;
    }}
    .project-detail-grid {{
      display: grid;
      gap: 10px;
    }}
    .project-detail-card {{
      display: grid;
      gap: 4px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
    }}
    .project-detail-card span {{
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 800;
    }}
    .project-detail-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }}
    .project-review-action-panel {{
      margin-top: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: rgba(246, 248, 250, 0.95);
    }}
    .project-review-action-panel header {{
      margin-bottom: 10px;
    }}
    .project-review-action-panel h3 {{
      margin: 0;
      font-size: 1rem;
    }}
    .project-review-action-list {{
      display: grid;
      gap: 8px;
    }}
    .project-review-action-list button {{
      width: 100%;
      justify-content: flex-start;
      text-align: left;
    }}
    .project-review-loop-status {{
      margin: 12px 0 0;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
      color: var(--muted);
      font-size: 0.86rem;
      font-weight: 700;
    }}
    .project-review-timeline {{
      margin-top: 16px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }}
    .project-review-timeline header {{
      margin-bottom: 10px;
    }}
    .project-review-timeline h3 {{
      margin: 0;
      font-size: 1rem;
    }}
    .project-review-event-controls {{
      display: grid;
      gap: 10px;
      margin: 10px 0 12px;
    }}
    .project-review-event-controls label {{
      display: grid;
      gap: 5px;
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 800;
    }}
    .project-review-event-summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
      gap: 8px;
    }}
    .project-review-event-summary button {{
      display: grid;
      gap: 3px;
      justify-items: start;
      padding: 9px 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
      color: var(--text);
      text-align: left;
    }}
    .project-review-event-summary strong {{
      font-size: 1rem;
    }}
    .project-activity-summary {{
      display: block;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
    }}
    .project-review-timeline ul {{
      display: grid;
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}
    .project-review-timeline li {{
      display: grid;
      gap: 3px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
    }}
    .project-review-timeline time {{
      color: var(--muted);
      font-size: 0.76rem;
      font-weight: 700;
    }}
    .project-evidence-audit-log {{
      margin-top: 16px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }}
    .project-evidence-audit-log header {{
      margin-bottom: 10px;
    }}
    .project-evidence-audit-log h3 {{
      margin: 0;
      font-size: 1rem;
    }}
    .project-evidence-audit-log ul {{
      display: grid;
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}
    .project-evidence-audit-log li {{
      display: grid;
      gap: 4px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
    }}
    .project-evidence-audit-log time {{
      color: var(--muted);
      font-size: 0.76rem;
      font-weight: 700;
    }}
    .project-status-pill {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      border: 1px solid var(--line);
      padding: 0.18rem 0.55rem;
      color: var(--muted);
      font-size: 0.8rem;
      font-weight: 800;
    }}
    .deliverable-report {{
      display: grid;
      grid-template-columns: 0.9fr 1.4fr;
      gap: 14px;
      margin-bottom: 20px;
      padding: 18px;
      background: rgba(237, 247, 243, 0.96);
      border: 1px solid rgba(15, 118, 110, 0.24);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .deliverable-summary {{
      display: grid;
      align-content: start;
      gap: 10px;
    }}
    .deliverable-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .share-handoff {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin-top: 2px;
    }}
    .share-handoff span {{
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .delivery-package {{
      display: grid;
      gap: 14px;
      margin-bottom: 20px;
      padding: 18px;
      background: rgba(255, 255, 255, 0.98);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 12px 30px rgba(24, 33, 43, 0.06);
    }}
    .delivery-package header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: end;
    }}
    .delivery-package header p {{
      margin: 6px 0 0;
      color: var(--muted);
    }}
    .delivery-package-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }}
    .delivery-quality-summary {{
      display: grid;
      gap: 10px;
      padding: 12px;
      border: 1px solid rgba(22, 101, 52, 0.18);
      border-radius: 8px;
      background: linear-gradient(135deg, rgba(247, 250, 249, 0.98), rgba(255, 251, 235, 0.92));
    }}
    .delivery-quality-heading {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .delivery-quality-heading strong {{
      display: block;
      margin-top: 3px;
      color: var(--ink);
    }}
    .research-only-badge {{
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 5px 9px;
      border: 1px solid rgba(146, 64, 14, 0.24);
      border-radius: 999px;
      color: #7c2d12;
      background: rgba(255, 247, 237, 0.96);
      font-size: 0.78rem;
      font-weight: 800;
    }}
    .delivery-quality-strip {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }}
    .delivery-quality-strip span {{
      display: grid;
      gap: 4px;
      padding: 9px 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.88);
      min-width: 0;
    }}
    .delivery-quality-strip small {{
      color: var(--muted);
      font-size: 0.72rem;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .delivery-quality-strip strong {{
      overflow-wrap: anywhere;
    }}
    .delivery-package-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}
    .package-artifact {{
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(247, 250, 249, 0.95);
    }}
    .package-artifact h3 {{
      margin: 0;
      font-size: 0.98rem;
    }}
    .package-artifact p {{
      margin: 0;
      color: var(--muted);
      font-size: 0.88rem;
    }}
    .package-artifact small {{
      color: var(--muted);
      overflow-wrap: anywhere;
    }}
    .deliverable-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .deliverable-card {{
      display: grid;
      gap: 6px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
    }}
    .deliverable-card span {{
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 800;
    }}
    .metric {{
      padding: 18px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 700;
    }}
    .metric strong {{
      display: block;
      margin-top: 8px;
      font-size: 2rem;
      line-height: 1;
      font-variant-numeric: tabular-nums;
    }}
    section {{ margin-top: 20px; }}
    .section-head {{
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
      margin-bottom: 12px;
    }}
    .section-head p {{
      margin: 6px 0 0;
      color: var(--muted);
      max-width: 72ch;
    }}
    .table-wrap {{
      overflow-x: auto;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: var(--surface);
    }}
    table {{
      width: 100%;
      min-width: 720px;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 14px 16px;
      text-align: left;
      border-bottom: 1px solid var(--line);
      vertical-align: middle;
    }}
    th {{
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: #f7f6f0;
    }}
    td.num, th.num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 0.2rem 0.65rem;
      border-radius: 999px;
      font-weight: 800;
      font-size: 0.82rem;
      white-space: nowrap;
    }}
    .pill.ready {{ background: var(--success-bg); color: var(--success-ink); }}
    .pill.needs_work, .pill.blocked {{ background: var(--warn-bg); color: var(--warn-ink); }}
    .memo-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }}
    .memo-card {{
      padding: 18px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .memo-card header {{
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 12px;
    }}
    .memo-card dl {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin: 12px 0 0;
    }}
    .memo-card dt {{
      color: var(--muted);
      font-size: 0.75rem;
      font-weight: 700;
    }}
    .memo-card dd {{
      margin: 2px 0 0;
      font-size: 1.15rem;
      font-weight: 800;
      font-variant-numeric: tabular-nums;
    }}
    .preview-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 14px;
    }}
    .preview-grid.is-compact {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .preview {{
      padding: 20px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .preview-top {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
    }}
    .score {{
      color: var(--accent);
      font-weight: 900;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }}
    .preview p {{ color: var(--muted); }}
    .columns {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 14px;
    }}
    .note {{
      background: #f7f6f0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .note ul {{ margin: 8px 0 0; padding-left: 1.1rem; }}
    .source-list {{
      display: grid;
      gap: 12px;
    }}
    .report-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }}
    .report-card {{
      padding: 16px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 12px 30px rgba(24, 33, 43, 0.06);
    }}
    .report-card h3 {{
      margin-bottom: 8px;
    }}
    .report-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }}
    .report-workbench {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(180px, 260px);
      gap: 12px;
      align-items: end;
      margin-bottom: 14px;
      padding: 16px;
      background: rgba(241, 246, 244, 0.92);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 33, 43, 0.06);
    }}
    .report-workbench p {{
      margin: 6px 0 0;
      color: var(--muted);
    }}
    .report-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }}
    .report-frame {{
      width: 100%;
      min-height: calc(100dvh - 150px);
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
    }}
    .task-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .task-card {{
      display: grid;
      gap: 10px;
      padding: 16px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 12px 30px rgba(24, 33, 43, 0.06);
    }}
    .task-card.is-project-focus,
    .task-card[data-project-evidence-focus="true"] {{
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(48, 98, 184, 0.16), 0 12px 30px rgba(24, 33, 43, 0.08);
    }}
    .task-card header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
    }}
    .task-card p {{
      margin: 0;
      color: var(--muted);
    }}
    .task-prompt {{
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f7f6f0;
      color: var(--ink);
      font: 0.92rem/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      word-break: break-word;
    }}
    .task-playbook {{
      display: grid;
      gap: 8px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfaf5;
    }}
    .task-playbook p {{
      margin: 0;
    }}
    .task-status-control {{
      display: grid;
      gap: 6px;
    }}
    .task-status-control select {{
      width: 100%;
    }}
    .verified-task-rerun-loop {{
      display: grid;
      gap: 8px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
    }}
    .verified-task-rerun-loop small {{
      color: var(--muted);
      font-weight: 700;
    }}
    .evidence-import {{
      display: grid;
      gap: 10px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfaf5;
    }}
    .evidence-import .field {{
      gap: 4px;
    }}
    .evidence-import input,
    .evidence-import textarea {{
      min-height: 44px;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      color: var(--ink);
      font: inherit;
      padding: 0.65rem 0.8rem;
    }}
    .evidence-import textarea {{
      min-height: 88px;
      resize: vertical;
    }}
    .evidence-import-help,
    .import-status,
    .import-history {{
      margin: 0;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .import-history {{
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f7f6f0;
    }}
    .source {{
      padding: 16px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .source a {{
      font-weight: 800;
      text-decoration-thickness: 0.08em;
      text-underline-offset: 0.18em;
    }}
    .source-meta {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    blockquote {{
      margin: 12px 0 0;
      border-left: 4px solid var(--accent-2);
      padding: 8px 0 8px 12px;
      color: var(--muted);
      background: #faf8f0;
      border-radius: 0 8px 8px 0;
    }}
    footer {{
      margin-top: 24px;
      padding: 18px;
      border: 1px solid var(--line);
      background: rgba(255, 253, 248, 0.78);
      border-radius: 8px;
      color: var(--muted);
    }}
    .drawer-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(24, 33, 43, 0.28);
      z-index: 40;
    }}
    .memo-drawer {{
      position: fixed;
      top: 0;
      right: 0;
      width: min(620px, 100vw);
      height: 100dvh;
      padding: 22px;
      background: var(--surface);
      border-left: 1px solid var(--line);
      box-shadow: -24px 0 60px rgba(24, 33, 43, 0.18);
      overflow-y: auto;
      z-index: 50;
    }}
    .drawer-head {{
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 14px;
      position: sticky;
      top: -22px;
      padding: 0 0 14px;
      background: var(--surface);
      border-bottom: 1px solid var(--line);
      z-index: 1;
    }}
    .drawer-toolbar {{
      display: grid;
      gap: 10px;
      margin: 14px 0;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(247, 250, 249, 0.96);
    }}
    .drawer-toolbar[hidden] {{
      display: none;
    }}
    .drawer-toolbar span {{
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .drawer-toolbar code {{
      display: block;
      margin-top: 4px;
      color: var(--ink);
      font-size: 0.84rem;
      overflow-wrap: anywhere;
      white-space: normal;
    }}
    .drawer-toolbar-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .reader-navigation {{
      display: grid;
      gap: 10px;
      margin: 12px 0 0;
    }}
    .reader-outline,
    .reader-highlights {{
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.92);
    }}
    .reader-outline[hidden],
    .reader-highlights[hidden] {{
      display: none;
    }}
    .reader-outline strong,
    .reader-highlights strong {{
      font-size: 0.86rem;
    }}
    .reader-outline-list,
    .reader-highlight-list {{
      display: grid;
      gap: 6px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}
    .reader-outline button {{
      width: 100%;
      min-height: 34px;
      padding: 6px 8px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(247, 250, 249, 0.96);
      color: var(--ink);
      text-align: left;
      font-size: 0.84rem;
      font-weight: 800;
    }}
    .reader-highlight-list li {{
      color: var(--muted);
      font-size: 0.86rem;
      line-height: 1.45;
    }}
    .drawer-close {{
      flex: 0 0 auto;
      background: var(--ink);
    }}
    .drawer-body {{
      padding-top: 16px;
      color: var(--ink);
    }}
    .drawer-body.is-rendered {{
      display: grid;
      gap: 12px;
    }}
    .markdown-body {{
      display: grid;
      gap: 12px;
      line-height: 1.65;
    }}
    .markdown-body h1 {{
      font-size: 1.55rem;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--line);
    }}
    .markdown-body h2 {{
      margin-top: 8px;
      padding-top: 12px;
      border-top: 1px solid var(--line);
      font-size: 1.15rem;
    }}
    .markdown-body p {{
      margin: 0;
      color: var(--ink);
    }}
    .markdown-body ul {{
      margin: 0;
      padding-left: 1.2rem;
      display: grid;
      gap: 8px;
    }}
    .markdown-body li {{
      color: var(--muted);
    }}
    .markdown-body strong {{
      color: var(--ink);
      font-weight: 850;
    }}
    .drawer-body pre {{
      white-space: pre-wrap;
      word-break: break-word;
      font: 0.92rem/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      margin: 0;
    }}
    .drawer-empty {{
      color: var(--muted);
      font-weight: 700;
    }}
    @media (max-width: 900px) {{
      .topbar, .hero, .section-head, .preview-top {{ grid-template-columns: 1fr; flex-direction: column; align-items: stretch; }}
      .metric-grid, .memo-grid, .columns, .preview-grid.is-compact, .report-grid, .task-grid, .workbench, .run-center, .analysis-briefing, .research-action-workbench, .decision-workbench, .report-quality-gate, .saved-workspace, .deliverable-report, .delivery-package-grid {{ grid-template-columns: 1fr 1fr; }}
      .workflow-steps {{ grid-template-columns: 1fr 1fr; }}
      .run-steps {{ grid-template-columns: 1fr 1fr; }}
      .nav {{ justify-content: flex-start; }}
    }}
    @media (max-width: 640px) {{
      .shell {{ width: min(100% - 24px, 1180px); padding-top: 18px; }}
      .launcher, .filters, .report-workbench {{ grid-template-columns: 1fr; }}
      .launcher button, .filters button {{ width: 100%; }}
      .metric-grid, .memo-grid, .columns, .preview-grid.is-compact, .report-grid, .task-grid, .workbench, .workflow-steps, .run-center, .run-steps, .input-preview-grid, .analysis-briefing, .briefing-grid, .research-action-workbench, .decision-workbench, .decision-grid, .report-quality-gate, .quality-grid, .saved-workspace, .workspace-grid, .research-project-library, .project-library-tools, .project-comparison-summary, .project-comparison-matrix, .deliverable-report, .deliverable-grid, .delivery-package-grid, .delivery-quality-strip {{ grid-template-columns: 1fr; }}
      .brand {{ align-items: flex-start; }}
      .mark {{ flex: 0 0 auto; }}
      .nav a, .memo-link {{ width: 100%; }}
      .run-actions button {{ width: 100%; }}
      table {{ min-width: 640px; }}
      .memo-drawer {{ width: 100vw; padding: 18px; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      html {{ scroll-behavior: auto; }}
      *, *::before, *::after {{ animation-duration: 0.001ms !important; transition-duration: 0.001ms !important; }}
    }}
  </style>
</head>
<body>
  <a class="skip" href="#main">{escape(copy["skip"])}</a>
  <div class="shell">
    <header class="topbar" aria-label="Dashboard header">
      <div class="brand">
        <div class="mark" aria-hidden="true">SA</div>
        <div>
          <div class="eyebrow">{escape(copy["eyebrow"])}</div>
          <h1>{escape(title)}</h1>
        </div>
      </div>
      <nav class="nav" aria-label="Primary navigation">
        <a href="#readiness">{escape(copy["readiness"])}</a>
        <a href="#memos">{escape(copy["memo_pack"])}</a>
        <a href="#provenance">{escape(copy["evidence"])}</a>
        {lang_switch}
      </nav>
    </header>

    <main id="main">
      <div class="hero">
        <div class="panel hero-copy">
          <div class="eyebrow">{escape(copy["overview"])}</div>
          <h2>{escape(copy["hero_title"])}</h2>
          <p class="subtitle">{escape(copy["hero_subtitle"])}</p>
          <div class="query">{escape(copy["research_question"])}: {escape(query)}</div>
        </div>
        <aside class="panel status-card" aria-label="Pack health">
          <span class="health">{escape(localized_pack_health)}</span>
          <div>
            <div class="eyebrow">{escape(copy["pack_status"])}</div>
            <h2>{ready_count} {escape(copy["ready_memos_lower"])}</h2>
            <p class="subtitle">{skipped_count} {escape(copy["skipped_summary"])} {primary_total} {escape(copy["primary_summary"])} {risk_total} {escape(copy["risk_summary"])}</p>
          </div>
        </aside>
      </div>

      <div class="metric-grid" aria-label="Dashboard metrics">
        <div class="metric"><span>{escape(copy["total_evidence"])}</span><strong>{evidence_total}</strong></div>
        <div class="metric"><span>{escape(copy["ready_memos"])}</span><strong>{ready_count}</strong></div>
        <div class="metric"><span>{escape(copy["primary_fact"])}</span><strong>{primary_total}</strong></div>
        <div class="metric"><span>{escape(copy["risk_items"])}</span><strong>{risk_total}</strong></div>
      </div>

      {analysis_briefing}

      {research_action_workbench}

      {decision_workbench}

      {report_quality_gate}

      {saved_workspace}

      {research_project_library}

      {deliverable_report}

      {delivery_package}

      <form class="launcher" action="/analyze" method="get" aria-label="{escape(copy["launch_aria"])}" onsubmit="return handleLaunchSubmit(this);">
        <div class="field">
          <label for="analysis-query">{escape(copy["launch_label"])}</label>
          <input id="analysis-query" name="query" type="search" placeholder="{escape(copy["launch_placeholder"])}" autocomplete="off" required>
        </div>
        <input type="hidden" name="language" value="{escape(language_value)}">
        <div class="launcher-actions">
          <button type="button" onclick="renderAnalysisInputPreview(this.form)">{escape(copy["preview_scope"])}</button>
          <button type="submit" data-loading-text="{escape(copy["launch_loading"])}">{escape(copy["launch_button"])}</button>
        </div>
        <section id="analysis-input-preview" class="input-preview" data-preview-intent="" aria-labelledby="analysis-input-preview-title" aria-live="polite" hidden>
          <header>
            <div>
              <div class="eyebrow">{escape(copy["input_preview_eyebrow"])}</div>
              <h2 id="analysis-input-preview-title">{escape(copy["input_preview"])}</h2>
            </div>
            <button type="button" onclick="confirmAnalysisLaunch(this.form)">{escape(copy["confirm_generate"])}</button>
          </header>
          <dl class="input-preview-grid">
            <div><dt>{escape(copy["detected_input_type"])}</dt><dd id="preview-intent">{escape(copy["preview_waiting"])}</dd></div>
            <div><dt>{escape(copy["canonical_theme"])}</dt><dd id="preview-canonical-theme">{escape(copy["preview_waiting"])}</dd></div>
            <div><dt>{escape(copy["candidate_tickers"])}</dt><dd id="preview-candidate-tickers">{escape(copy["preview_waiting"])}</dd></div>
            <div><dt>{escape(copy["evidence_coverage"])}</dt><dd id="preview-evidence-coverage">{escape(copy["preview_waiting"])}</dd></div>
          </dl>
          <div id="preview-candidate-coverage" class="candidate-coverage" aria-label="{escape(copy["candidate_coverage_detail"])}">
            <strong>{escape(copy["candidate_coverage_detail"])}</strong>
            <div class="candidate-coverage-list">{escape(copy["preview_waiting"])}</div>
          </div>
          <div id="preview-evidence-gap-tasks" class="candidate-coverage" aria-label="{escape(copy["preflight_evidence_tasks"])}">
            <strong>{escape(copy["preflight_evidence_tasks"])}</strong>
            <div class="candidate-coverage-list">{escape(copy["preview_waiting"])}</div>
          </div>
          <p><strong>{escape(copy["expected_outputs"])}:</strong> <span id="preview-expected-outputs">{escape(copy["expected_outputs_value"])}</span></p>
          <p><strong>{escape(copy["preview_source"])}:</strong> <span id="preview-source">{escape(copy["preview_waiting"])}</span></p>
        </section>
        <p>{escape(copy["launch_help"])}</p>
        <p id="launch-status" class="launch-status" aria-live="polite" hidden>{escape(copy["launch_loading"])}</p>
      </form>

      <section class="workbench" aria-labelledby="workbench-title">
        <div class="workflow-card">
          <div class="eyebrow">{escape(copy["workbench_eyebrow"])}</div>
          <h2 id="workbench-title">{escape(copy["research_workflow"])}</h2>
          <p class="subtitle">{escape(copy["workbench_description"])}</p>
          <div class="workflow-steps">
            <div class="workflow-step"><span>1</span><strong>{escape(copy["workflow_scope"])}</strong><p>{escape(copy["workflow_scope_description"])}</p></div>
            <div class="workflow-step"><span>2</span><strong>{escape(copy["workflow_compare"])}</strong><p>{escape(copy["workflow_compare_description"])}</p></div>
            <div class="workflow-step"><span>3</span><strong>{escape(copy["workflow_reports"])}</strong><p>{escape(copy["workflow_reports_description"])}</p></div>
            <div class="workflow-step"><span>4</span><strong>{escape(copy["workflow_evidence"])}</strong><p>{escape(copy["workflow_evidence_description"])}</p></div>
          </div>
        </div>
        <aside class="example-card" aria-labelledby="examples-title">
          <div class="eyebrow">{escape(copy["quick_examples_eyebrow"])}</div>
          <h2 id="examples-title">{escape(copy["quick_examples"])}</h2>
          <p>{escape(copy["quick_examples_description"])}</p>
          <div class="example-actions">
            <button type="button" data-example-query="{escape(copy["example_query_primary"])}" onclick="launchExampleAnalysis(this)">{escape(copy["example_primary"])}</button>
            <button type="button" data-example-query="{escape(copy["example_query_secondary"])}" onclick="launchExampleAnalysis(this)">{escape(copy["example_secondary"])}</button>
          </div>
        </aside>
      </section>

      <section id="run-center" class="run-center" aria-labelledby="run-center-title">
        <div class="run-summary">
          <div class="eyebrow">{escape(copy["run_center_eyebrow"])}</div>
          <h2 id="run-center-title">{escape(copy["run_center"])}</h2>
          <p><strong>{escape(copy["current_run"])}:</strong> <span id="run-current-query">{escape(copy["run_waiting"])}</span></p>
          <p id="run-status" aria-live="polite">{escape(copy["run_waiting"])}</p>
        </div>
        <div class="run-steps" aria-label="{escape(copy["run_steps_aria"])}">
          <div class="run-step" data-run-step="resolve" data-run-state="idle"><strong>{escape(copy["run_step_resolve"])}</strong><span>{escape(copy["run_step_resolve_detail"])}</span></div>
          <div class="run-step" data-run-step="pack" data-run-state="idle"><strong>{escape(copy["run_step_pack"])}</strong><span>{escape(copy["run_step_pack_detail"])}</span></div>
          <div class="run-step" data-run-step="publish" data-run-state="idle"><strong>{escape(copy["run_step_publish"])}</strong><span>{escape(copy["run_step_publish_detail"])}</span></div>
          <div class="run-step" data-run-step="open" data-run-state="idle"><strong>{escape(copy["run_step_open"])}</strong><span>{escape(copy["run_step_open_detail"])}</span></div>
        </div>
        <div class="run-actions">
          <button type="button" onclick="retryLastRun()">{escape(copy["retry_last_run"])}</button>
          <button id="latest-run-report-button" type="button" onclick="openLatestRunReport()" hidden>{escape(copy["open_latest_report"])}</button>
        </div>
        <div id="job-detail-panel" class="run-history" hidden aria-live="polite">
          <h3>{escape(copy["job_detail"])}</h3>
          <div id="job-detail-body" class="run-history-list">
            <p class="run-history-empty">{escape(copy["run_history_empty"])}</p>
          </div>
        </div>
        <div class="run-history" aria-labelledby="run-history-title" data-run-polling="idle">
          <h3 id="run-history-title">{escape(copy["run_history"])}</h3>
          <div id="run-history-list" class="run-history-list" aria-live="polite">
            <p class="run-history-empty">{escape(copy["run_history_empty"])}</p>
          </div>
        </div>
      </section>

      <section id="reports" aria-labelledby="reports-title">
        <div class="section-head">
          <div>
            <div class="eyebrow">{escape(copy["report_library_eyebrow"])}</div>
            <h2 id="reports-title">{escape(copy["recent_reports"])}</h2>
            <p>{escape(copy["recent_reports_description"])}</p>
          </div>
        </div>
        <div class="report-workbench" aria-label="{escape(copy["report_workbench"])}">
          <div>
            <h3>{escape(copy["report_workbench"])}</h3>
            <p>{escape(copy["report_workbench_description"])}</p>
          </div>
          <div class="field">
            <label for="report-workbench-type">{escape(copy["report_type_label"])}</label>
            <select id="report-workbench-type" onchange="filterReportWorkbench()">
              <option value="">{escape(copy["all_report_types"])}</option>
              <option value="generated">{escape(copy["generated_analysis_reports"])}</option>
              <option value="deliverable">{escape(copy["deliverable_report_type"])}</option>
              <option value="operational">{escape(copy["operational_report_type"])}</option>
            </select>
          </div>
        </div>
        {report_library}
        {operational_report_cards}
      </section>

      {evidence_tasks}

      <form class="filters" role="search" aria-label="Dashboard filters" onsubmit="return false;">
        <div class="field">
          <label for="dashboard-search">{escape(copy["search_label"])}</label>
          <input id="dashboard-search" type="search" placeholder="{escape(copy["search_placeholder"])}" autocomplete="off" oninput="filterDashboard()">
        </div>
        <div class="field">
          <label for="status-filter">{escape(copy["status"])}</label>
          <select id="status-filter" onchange="filterDashboard()">
            <option value="">{escape(copy["all_statuses"])}</option>
            {status_options}
          </select>
        </div>
        <button type="button" onclick="resetDashboardFilters()">{escape(copy["reset_filters"])}</button>
      </form>
      <div id="result-count" class="result-count" aria-live="polite">{escape(copy["showing_all"])}</div>

      <section id="readiness" aria-labelledby="readiness-title">
        <div class="section-head">
          <div>
            <div class="eyebrow">Coverage gate</div>
            <h2 id="readiness-title">{escape(copy["readiness"])}</h2>
            <p>{escape(copy["readiness_description"])}</p>
          </div>
        </div>
        {readiness_table}
      </section>

      <section id="memos" aria-labelledby="memos-title">
        <div class="section-head">
          <div>
            <div class="eyebrow">{escape(copy["generated_research"])}</div>
            <h2 id="memos-title">{escape(copy["memo_pack"])}</h2>
            <p>{escape(copy["memo_description"])}</p>
          </div>
        </div>
        {memo_cards}
      </section>

      <section id="comparison" aria-labelledby="comparison-title">
        <div class="section-head">
          <div>
            <div class="eyebrow">{escape(copy["comparison_eyebrow"])}</div>
            <h2 id="comparison-title">{escape(copy["candidate_comparison"])}</h2>
            <p>{escape(copy["candidate_comparison_description"])}</p>
          </div>
        </div>
        {comparison_table}
      </section>

      <section aria-labelledby="preview-title">
        <div class="section-head">
          <div>
            <div class="eyebrow">{escape(copy["analyst_preview"])}</div>
            <h2 id="preview-title">{escape(copy["featured_preview"])}</h2>
            <p>{escape(copy["preview_description"])}</p>
          </div>
        </div>
        {memo_sections}
      </section>

      <section id="provenance" aria-labelledby="provenance-title">
        <div class="section-head">
          <div>
            <div class="eyebrow">{escape(copy["traceability"])}</div>
            <h2 id="provenance-title">{escape(copy["evidence_provenance"])}</h2>
            <p>{escape(copy["provenance_description"])}</p>
          </div>
        </div>
        {sources}
      </section>
    </main>

    <footer>
      <strong>{escape(copy["research_only"])}</strong> {escape(copy["disclaimer"])}
    </footer>
  </div>
  <div id="drawer-backdrop" class="drawer-backdrop" hidden onclick="closeMemoDrawer()"></div>
  <aside id="memo-drawer" class="memo-drawer" aria-labelledby="memo-drawer-title" aria-hidden="true" hidden>
    <div class="drawer-head">
      <div>
        <div class="eyebrow">{escape(copy["report_reader"])}</div>
        <h2 id="memo-drawer-title">{escape(copy["select_report"])}</h2>
      </div>
      <button type="button" class="drawer-close" onclick="closeMemoDrawer()">{escape(copy["close_report"])}</button>
    </div>
    <div id="memo-drawer-toolbar" class="drawer-toolbar" aria-label="{escape(copy["reader_toolbar"])}" hidden>
      <div>
        <span>{escape(copy["current_report_link"])}</span>
        <code id="memo-drawer-current-link">{escape(copy["not_generated"])}</code>
      </div>
      <div class="drawer-toolbar-actions">
        <button type="button" class="memo-link" data-copied-text="{escape(copy["copied_link"])}" onclick="copyCurrentReaderLink(this)">{escape(copy["copy_current_link"])}</button>
        <button type="button" class="memo-link" onclick="openCurrentReaderReport()">{escape(copy["open_full_page"])}</button>
      </div>
      <div class="reader-navigation">
        <nav id="memo-drawer-outline" class="reader-outline" aria-label="{escape(copy["reader_outline"])}" hidden>
          <strong>{escape(copy["reader_outline"])}</strong>
          <ul id="memo-drawer-outline-list" class="reader-outline-list"></ul>
        </nav>
        <aside id="memo-drawer-highlights" class="reader-highlights" aria-label="{escape(copy["report_highlights"])}" hidden>
          <strong>{escape(copy["report_highlights"])}</strong>
          <ul id="memo-drawer-highlight-list" class="reader-highlight-list"></ul>
        </aside>
      </div>
    </div>
    <div id="memo-drawer-body" class="drawer-body">
      <p class="drawer-empty">{escape(copy["drawer_empty"])}</p>
    </div>
  </aside>
  <script>
    function normalizeText(value) {{
      return (value || '').toString().toLowerCase();
    }}
    function filterDashboard() {{
      var query = normalizeText(document.getElementById('dashboard-search').value);
      var status = normalizeText(document.getElementById('status-filter').value);
      var items = Array.prototype.slice.call(document.querySelectorAll('[data-dashboard-item]'));
      var shown = 0;
      items.forEach(function(item) {{
        var text = normalizeText(item.getAttribute('data-search') || item.textContent);
        var itemStatus = normalizeText(item.getAttribute('data-status'));
        var matchesQuery = !query || text.indexOf(query) !== -1;
        var matchesStatus = !status || itemStatus === status || !itemStatus;
        var visible = matchesQuery && matchesStatus;
        item.hidden = !visible;
        if (visible) shown += 1;
      }});
      var count = document.getElementById('result-count');
      if (count) {{
        count.textContent = '{escape(copy["showing"])} ' + shown + ' {escape(copy["of"])} ' + items.length + ' {escape(copy["dashboard_items"])}';
      }}
    }}
    function resetDashboardFilters() {{
      document.getElementById('dashboard-search').value = '';
      document.getElementById('status-filter').value = '';
      filterDashboard();
    }}
    function filterReportWorkbench() {{
      var select = document.getElementById('report-workbench-type');
      var type = normalizeText(select ? select.value : '');
      var items = Array.prototype.slice.call(document.querySelectorAll('[data-report-workbench-item]'));
      items.forEach(function(item) {{
        var itemType = normalizeText(item.getAttribute('data-report-type'));
        item.hidden = Boolean(type && itemType !== type);
      }});
    }}
    function reviewReportWorkbench(button) {{
      openMemoDrawer(button);
    }}
    function getDecisionMetric(card, sortKey) {{
      var value = Number(card.getAttribute('data-decision-' + sortKey) || 0);
      return Number.isFinite(value) ? value : 0;
    }}
    function updateDecisionRanking() {{
      var select = document.getElementById('decision-sort');
      var list = document.getElementById('decision-rank-list');
      var explanation = document.getElementById('decision-sort-explanation');
      if (!select || !list) return;
      var sortKey = select.value || 'score';
      var cards = Array.prototype.slice.call(list.querySelectorAll('[data-decision-candidate]'));
      cards.sort(function(a, b) {{
        return getDecisionMetric(b, sortKey) - getDecisionMetric(a, sortKey);
      }});
      cards.forEach(function(card, index) {{
        var rank = card.querySelector('[data-decision-rank]');
        if (rank) rank.textContent = String(index + 1);
        list.appendChild(card);
      }});
      if (explanation) {{
        var selected = select.options[select.selectedIndex];
        var label = selected ? selected.textContent : sortKey;
        var top = cards[0];
        var ticker = top ? top.getAttribute('data-decision-ticker') : '';
        var value = top ? getDecisionMetric(top, sortKey) : 0;
        explanation.textContent = '{escape(copy["sort_explanation_prefix"])} ' + label + ': ' + (ticker || '{escape(copy["not_generated"])}') + ' (' + value + ').';
      }}
      persistWorkspacePreference();
    }}
    function initializeDecisionRanking() {{
      updateDecisionRanking();
    }}
    function workspaceStorageKey() {{
      return 'serenity-alpha-lab:saved-workspace:' + window.location.pathname;
    }}
    function readWorkspaceState() {{
      try {{
        return JSON.parse(window.localStorage.getItem(workspaceStorageKey()) || 'null') || {{}};
      }} catch (error) {{
        return {{}};
      }}
    }}
    function writeWorkspaceState(state) {{
      try {{
        window.localStorage.setItem(workspaceStorageKey(), JSON.stringify(state || {{}}));
      }} catch (error) {{}}
    }}
    function collectWorkspaceReports() {{
      return Array.prototype.slice.call(document.querySelectorAll('[data-report-workbench-item][data-report-type="generated"]')).slice(0, 4).map(function(item) {{
        var button = item.querySelector('[data-memo-href]');
        var link = item.querySelector('a[href]');
        return {{
          title: item.querySelector('h3') ? item.querySelector('h3').textContent.trim() : '{escape(copy["recent_reports"])}',
          href: button ? button.getAttribute('data-memo-href') : (link ? link.getAttribute('href') : ''),
          meta: item.querySelector('.source-meta') ? item.querySelector('.source-meta').textContent.trim() : ''
        }};
      }}).filter(function(report) {{ return report.title || report.href; }});
    }}
    function collectWorkspaceCandidates() {{
      return Array.prototype.slice.call(document.querySelectorAll('[data-decision-candidate]')).slice(0, 5).map(function(card) {{
        return {{
          ticker: card.getAttribute('data-decision-ticker') || '',
          score: card.getAttribute('data-decision-score') || '0',
          mark: card.getAttribute('data-workspace-candidate-mark') || '{escape(copy["workspace_mark_tracking"])}'
        }};
      }}).filter(function(candidate) {{ return candidate.ticker; }});
    }}
    function collectWorkspaceQualitySnapshot() {{
      var gate = document.getElementById('report-quality-gate');
      if (!gate) return {{ status: '{escape(copy["not_generated"])}', score: 'n/a' }};
      var status = gate.querySelector('.quality-status');
      var scoreCard = Array.prototype.slice.call(gate.querySelectorAll('.quality-card')).find(function(card) {{
        return normalizeText(card.textContent).indexOf(normalizeText('{escape(copy["quality_score"])}')) !== -1;
      }});
      var score = scoreCard && scoreCard.querySelector('strong') ? scoreCard.querySelector('strong').textContent.trim() : 'n/a';
      return {{
        status: status ? status.textContent.trim() : gate.getAttribute('data-quality-status') || '{escape(copy["not_generated"])}',
        score: score
      }};
    }}
    function currentWorkspaceSortPreference() {{
      var select = document.getElementById('decision-sort');
      if (!select) return '{escape(copy["not_generated"])}';
      var selected = select.options[select.selectedIndex];
      return selected ? selected.textContent : select.value;
    }}
    function saveWorkspaceState() {{
      var state = {{
        savedAt: new Date().toISOString(),
        reports: collectWorkspaceReports(),
        candidates: collectWorkspaceCandidates(),
        sortPreference: currentWorkspaceSortPreference(),
        quality: collectWorkspaceQualitySnapshot()
      }};
      writeWorkspaceState(state);
      renderSavedWorkspace(state);
      return false;
    }}
    function clearWorkspaceState() {{
      writeWorkspaceState({{}});
      renderSavedWorkspace({{}});
      return false;
    }}
    function persistWorkspacePreference() {{
      var state = readWorkspaceState();
      if (!state.savedAt) return;
      state.sortPreference = currentWorkspaceSortPreference();
      state.candidates = collectWorkspaceCandidates();
      writeWorkspaceState(state);
      renderSavedWorkspace(state);
    }}
    function renderSavedWorkspace(state) {{
      var workspace = document.getElementById('saved-workspace');
      if (!workspace) return;
      var nextState = state || readWorkspaceState();
      var reports = Array.isArray(nextState.reports) ? nextState.reports : [];
      var candidates = Array.isArray(nextState.candidates) ? nextState.candidates : [];
      var reportEl = document.getElementById('workspace-saved-reports');
      var candidateEl = document.getElementById('workspace-candidate-marks');
      var sortEl = document.getElementById('workspace-sort-preference');
      var qualityEl = document.getElementById('workspace-quality-snapshot');
      var savedAtEl = document.getElementById('workspace-saved-at');
      if (reportEl) {{
        reportEl.innerHTML = reports.length ? reports.map(function(report) {{
          return '<div data-workspace-report><strong>' + escapeHtml(report.title || '{escape(copy["recent_reports"])}') + '</strong><small>' + escapeHtml(report.meta || report.href || '') + '</small></div>';
        }}).join('') : '<small>{escape(copy["workspace_no_saved_reports"])}</small>';
      }}
      if (candidateEl) {{
        candidateEl.innerHTML = candidates.length ? candidates.map(function(candidate) {{
          return '<div data-workspace-candidate><strong>' + escapeHtml(candidate.ticker || '') + '</strong><small>' + escapeHtml(candidate.mark || '{escape(copy["workspace_mark_tracking"])}') + ' · ' + escapeHtml(candidate.score || '0') + '</small></div>';
        }}).join('') : '<small>{escape(copy["workspace_no_candidate_marks"])}</small>';
      }}
      if (sortEl) sortEl.textContent = nextState.sortPreference || currentWorkspaceSortPreference();
      if (qualityEl) {{
        var quality = nextState.quality || collectWorkspaceQualitySnapshot();
        qualityEl.textContent = (quality.status || '{escape(copy["not_generated"])}') + ' · ' + (quality.score || 'n/a');
      }}
      if (savedAtEl) savedAtEl.textContent = nextState.savedAt ? '{escape(copy["workspace_last_saved"])} ' + nextState.savedAt : '{escape(copy["workspace_not_saved"])}';
    }}
    function initializeSavedWorkspace() {{
      var cards = Array.prototype.slice.call(document.querySelectorAll('[data-decision-candidate]'));
      cards.forEach(function(card) {{
        card.setAttribute('data-workspace-candidate', card.getAttribute('data-decision-ticker') || '');
        card.setAttribute('data-workspace-candidate-mark', '{escape(copy["workspace_mark_tracking"])}');
      }});
      renderSavedWorkspace(readWorkspaceState());
    }}
    function projectLibraryStorageKey() {{
      return 'serenity-alpha-lab:research-project-library';
    }}
    function readResearchProjectLibrary() {{
      try {{
        var projects = JSON.parse(window.localStorage.getItem(projectLibraryStorageKey()) || '[]');
        return Array.isArray(projects) ? projects : [];
      }} catch (error) {{
        return [];
      }}
    }}
    function writeResearchProjectLibrary(projects) {{
      try {{
        window.localStorage.setItem(projectLibraryStorageKey(), JSON.stringify(Array.isArray(projects) ? projects : []));
      }} catch (error) {{}}
    }}
    function syncResearchProjectLibraryFromServer() {{
      if (!window.fetch) return;
      fetch('/api/projects', {{ headers: {{ 'Accept': 'application/json' }} }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var projects = payload && Array.isArray(payload.projects) ? payload.projects : [];
          writeResearchProjectLibrary(projects);
          renderResearchProjectLibrary(projects);
        }})
        .catch(function() {{
          renderResearchProjectLibrary(readResearchProjectLibrary());
        }});
    }}
    function syncProjectReviewTimelineFromServer(projectId) {{
      if (!window.fetch) {{
        renderProjectReviewTimeline(projectId || '');
        return;
      }}
      var suffix = projectId ? '?projectId=' + encodeURIComponent(projectId) : '';
      fetch('/api/project-events' + suffix, {{ headers: {{ 'Accept': 'application/json' }} }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var events = payload && Array.isArray(payload.events) ? payload.events : [];
          writeProjectReviewTimeline(events);
          renderProjectReviewTimeline(projectId || '');
        }})
        .catch(function() {{
          renderProjectReviewTimeline(projectId || '');
        }});
    }}
    function writeProjectReviewEventToServer(event) {{
      if (!window.fetch || !event) return;
      fetch('/api/project-events', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
        body: JSON.stringify({{ event: event }})
      }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var events = payload && Array.isArray(payload.events) ? payload.events : readProjectReviewTimeline();
          writeProjectReviewTimeline(events);
          renderProjectReviewTimeline(event.projectId || '');
        }})
        .catch(function() {{}});
    }}
    function clearProjectReviewEventsOnServer() {{
      if (!window.fetch) return;
      fetch('/api/project-events', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
        body: JSON.stringify({{ clear: true }})
      }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var events = payload && Array.isArray(payload.events) ? payload.events : [];
          writeProjectReviewTimeline(events);
          renderProjectReviewTimeline('');
        }})
        .catch(function() {{}});
    }}
    function syncProjectEvidenceAuditLogFromServer(projectId) {{
      if (!window.fetch) {{
        renderProjectEvidenceAuditLog(projectId || '');
        return;
      }}
      var suffix = projectId ? '?projectId=' + encodeURIComponent(projectId) : '';
      fetch('/api/project-evidence-audits' + suffix, {{ headers: {{ 'Accept': 'application/json' }} }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var audits = payload && Array.isArray(payload.audits) ? payload.audits : [];
          writeProjectEvidenceAuditLog(audits);
          renderProjectEvidenceQualityDeltaSummary(payload && payload.summary ? payload.summary : null);
          renderProjectEvidenceAuditLog(projectId || '');
        }})
        .catch(function() {{
          renderProjectEvidenceAuditLog(projectId || '');
        }});
    }}
    function writeProjectEvidenceAuditEntryToServer(audit) {{
      if (!window.fetch || !audit) return;
      fetch('/api/project-evidence-audits', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
        body: JSON.stringify({{ audit: audit }})
      }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var audits = payload && Array.isArray(payload.audits) ? payload.audits : readProjectEvidenceAuditLog();
          writeProjectEvidenceAuditLog(audits);
          renderProjectEvidenceQualityDeltaSummary(payload && payload.summary ? payload.summary : null);
          renderProjectEvidenceAuditLog(audit.projectId || '');
        }})
        .catch(function() {{}});
    }}
    function clearProjectEvidenceAuditLogOnServer() {{
      if (!window.fetch) return;
      fetch('/api/project-evidence-audits', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
        body: JSON.stringify({{ clear: true }})
      }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var audits = payload && Array.isArray(payload.audits) ? payload.audits : [];
          writeProjectEvidenceAuditLog(audits);
          renderProjectEvidenceQualityDeltaSummary(payload && payload.summary ? payload.summary : null);
          renderProjectEvidenceAuditLog('');
        }})
        .catch(function() {{}});
    }}
    function taskStatusRecord(card, statusValue) {{
      var taskId = card ? card.getAttribute('data-task-id') || '' : '';
      return {{
        id: taskId,
        projectId: window.location.pathname,
        taskId: taskId,
        ticker: card ? card.getAttribute('data-ticker') || '' : '',
        status: statusValue || (card ? card.getAttribute('data-task-status') || 'to_collect' : 'to_collect'),
        updatedAt: new Date().toISOString()
      }};
    }}
    function applyTaskStatusRecords(statuses) {{
      var records = Array.isArray(statuses) ? statuses : [];
      var byTaskId = {{}};
      records.forEach(function(record) {{
        if (record && record.taskId) byTaskId[record.taskId] = record;
      }});
      Array.prototype.slice.call(document.querySelectorAll('[data-task-status-select]')).forEach(function(select) {{
        var card = select.closest('[data-task-id]');
        if (!card) return;
        var taskId = card.getAttribute('data-task-id') || '';
        var record = byTaskId[taskId];
        if (!record || !record.status) return;
        select.value = record.status;
        card.setAttribute('data-task-status', record.status);
        try {{
          window.localStorage.setItem(taskStorageKey(taskId), record.status);
        }} catch (error) {{}}
        updateVerifiedTaskRerunLoop(card);
      }});
    }}
    function syncTaskStatusesFromServer() {{
      if (!window.fetch) {{
        initializeTaskStatuses();
        return;
      }}
      var suffix = '?projectId=' + encodeURIComponent(window.location.pathname);
      fetch('/api/task-statuses' + suffix, {{ headers: {{ 'Accept': 'application/json' }} }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var statuses = payload && Array.isArray(payload.statuses) ? payload.statuses : [];
          if (statuses.length) applyTaskStatusRecords(statuses);
        }})
        .catch(function() {{}});
    }}
    function writeTaskStatusToServer(record) {{
      if (!window.fetch || !record) return;
      fetch('/api/task-statuses', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
        body: JSON.stringify({{ status: record }})
      }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var statuses = payload && Array.isArray(payload.statuses) ? payload.statuses : [];
          applyTaskStatusRecords(statuses);
        }})
        .catch(function() {{}});
    }}
    function clearTaskStatusesOnServer() {{
      if (!window.fetch) return;
      fetch('/api/task-statuses', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
        body: JSON.stringify({{ clear: true }})
      }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var statuses = payload && Array.isArray(payload.statuses) ? payload.statuses : [];
          applyTaskStatusRecords(statuses);
        }})
        .catch(function() {{}});
    }}
    function writeResearchProjectToServer(projects) {{
      if (!window.fetch) return;
      var project = Array.isArray(projects) && projects.length ? projects[0] : null;
      if (!project) return;
      fetch('/api/projects', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
        body: JSON.stringify({{ project: project }})
      }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var serverProjects = payload && Array.isArray(payload.projects) ? payload.projects : projects;
          writeResearchProjectLibrary(serverProjects);
          renderResearchProjectLibrary(serverProjects);
        }})
        .catch(function() {{}});
    }}
    function clearResearchProjectsOnServer() {{
      if (!window.fetch) return;
      fetch('/api/projects', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
        body: JSON.stringify({{ clear: true }})
      }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var projects = payload && Array.isArray(payload.projects) ? payload.projects : [];
          writeResearchProjectLibrary(projects);
          renderResearchProjectLibrary(projects);
        }})
        .catch(function() {{}});
    }}
    function parseProjectQualityScore(project) {{
      var quality = project && project.quality ? project.quality : {{}};
      var raw = String(quality.score || '');
      var match = raw.match(/\d+/);
      return match ? Number(match[0]) : null;
    }}
    function projectComparisonSelectionKey() {{
      return 'serenity.alpha.project.comparison.selection';
    }}
    function readProjectComparisonSelection() {{
      try {{
        var parsed = JSON.parse(localStorage.getItem(projectComparisonSelectionKey()) || '[]');
        return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
      }} catch (error) {{
        return [];
      }}
    }}
    function writeProjectComparisonSelection(ids) {{
      try {{
        localStorage.setItem(projectComparisonSelectionKey(), JSON.stringify(Array.isArray(ids) ? ids : []));
      }} catch (error) {{}}
    }}
    function selectedProjectComparisonIds() {{
      return readProjectComparisonSelection();
    }}
    function updateProjectComparisonMatrix(projects) {{
      renderProjectComparisonMatrix(Array.isArray(projects) ? projects : readResearchProjectLibrary());
    }}
    function renderProjectComparisonMatrix(projects) {{
      var table = document.getElementById('project-comparison-table');
      if (!table) return;
      var records = Array.isArray(projects) ? projects : [];
      var selectedIds = selectedProjectComparisonIds();
      var selected = records.filter(function(project) {{
        return selectedIds.indexOf(project.id || '') !== -1;
      }});
      if (!selected.length) {{
        table.innerHTML =
          '<tbody><tr><td colspan="6"><small>{escape(copy["project_comparison_empty"])}</small></td></tr></tbody>';
        return;
      }}
      table.innerHTML =
        '<thead><tr>' +
        '<th>{escape(copy["comparison_topic"])}</th>' +
        '<th>{escape(copy["comparison_top_candidate"])}</th>' +
        '<th>{escape(copy["comparison_quality"])}</th>' +
        '<th>{escape(copy["comparison_gap"])}</th>' +
        '<th>{escape(copy["comparison_status"])}</th>' +
        '<th>{escape(copy["comparison_report"])}</th>' +
        '</tr></thead><tbody>' +
        selected.map(function(project) {{
          var quality = project.quality || {{}};
          var qualityText = (quality.status || '{escape(copy["not_generated"])}') + ' · ' + (quality.score || 'n/a');
          var href = project.href || '';
          var report = href ? '<button type="button" onclick="window.location.href=\\'' + escapeHtml(href) + '\\'">{escape(copy["open_project_report"])}</button>' : 'n/a';
          return '<tr data-project-compare-selected="' + escapeHtml(project.id || '') + '">' +
            '<td>' + escapeHtml(project.query || '{escape(copy["not_generated"])}') + '</td>' +
            '<td>' + escapeHtml(project.topTicker || 'n/a') + '</td>' +
            '<td>' + escapeHtml(qualityText) + '</td>' +
            '<td>' + escapeHtml(project.gap || 'n/a') + '</td>' +
            '<td>' + projectStatusLabel(project.status || 'pending-evidence') + '</td>' +
            '<td>' + report + '</td>' +
            '</tr>';
        }}).join('') +
        '</tbody>';
    }}
    function buildProjectComparisonBrief(projects) {{
      var records = Array.isArray(projects) ? projects : readResearchProjectLibrary();
      var selectedIds = selectedProjectComparisonIds();
      var selected = records.filter(function(project) {{
        return selectedIds.indexOf(project.id || '') !== -1;
      }});
      var lines = [
        '{escape(copy["research_only_comparison_brief"])}',
        '{escape(copy["comparison_brief_boundary"])}',
        ''
      ];
      if (!selected.length) {{
        lines.push('{escape(copy["project_comparison_empty"])}');
        return lines.join('\\n');
      }}
      selected.forEach(function(project, index) {{
        var quality = project.quality || {{}};
        var qualityText = (quality.status || '{escape(copy["not_generated"])}') + ' · ' + (quality.score || 'n/a');
        lines.push(String(index + 1) + '. ' + (project.query || '{escape(copy["not_generated"])}'));
        lines.push('   - {escape(copy["comparison_top_candidate"])}: ' + (project.topTicker || 'n/a'));
        lines.push('   - {escape(copy["comparison_quality"])}: ' + qualityText);
        lines.push('   - {escape(copy["comparison_gap"])}: ' + (project.gap || 'n/a'));
        lines.push('   - {escape(copy["comparison_status"])}: ' + projectStatusLabel(project.status || 'pending-evidence'));
        lines.push('   - {escape(copy["comparison_report"])}: ' + (project.href || 'n/a'));
      }});
      return lines.join('\\n');
    }}
    function copyProjectComparisonBrief(button) {{
      var text = buildProjectComparisonBrief(readResearchProjectLibrary());
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(text).catch(function() {{}});
      }}
      if (button) button.textContent = button.getAttribute('data-copied-text') || button.textContent;
      appendProjectReviewEvent({{ id: 'comparison', query: '{escape(copy["compare_selected_projects"])}' }}, 'comparison-brief-copied', '{escape(copy["review_event_comparison_copied"])}');
      return false;
    }}
    function toggleProjectComparisonSelection(button) {{
      var projectId = button ? button.getAttribute('data-project-compare-id') : '';
      if (!projectId) return false;
      var selected = selectedProjectComparisonIds();
      var index = selected.indexOf(projectId);
      if (index === -1) selected.push(projectId);
      else selected.splice(index, 1);
      writeProjectComparisonSelection(selected);
      renderResearchProjectLibrary(readResearchProjectLibrary());
      return false;
    }}
    function renderProjectComparisonSummary(projects) {{
      var summary = document.getElementById('project-comparison-summary');
      if (!summary) return;
      var records = Array.isArray(projects) ? projects : [];
      var scores = records.map(parseProjectQualityScore).filter(function(score) {{
        return Number.isFinite(score);
      }});
      var average = scores.length ? Math.round(scores.reduce(function(total, score) {{ return total + score; }}, 0) / scores.length) + '/100' : 'n/a';
      var backlog = records.filter(function(project) {{ return (project.status || '') === 'pending-evidence'; }}).length;
      var delivered = records.filter(function(project) {{ return (project.status || '') === 'delivered'; }}).length;
      summary.innerHTML =
        '<div><span>{escape(copy["project_total_projects"])}</span><strong data-project-total>' + records.length + '</strong></div>' +
        '<div><span>{escape(copy["project_average_quality"])}</span><strong data-project-average-quality>' + escapeHtml(average) + '</strong></div>' +
        '<div><span>{escape(copy["project_evidence_backlog"])}</span><strong data-project-evidence-backlog>' + backlog + '</strong></div>' +
        '<div><span>{escape(copy["project_delivered_projects"])}</span><strong data-project-delivered-count>' + delivered + '</strong></div>';
    }}
    function projectTagForRecord(project) {{
      var status = project && project.status ? project.status : 'pending-evidence';
      var score = parseProjectQualityScore(project);
      if (status === 'delivered') return 'delivered';
      if (score !== null && score >= 70) return 'high-quality';
      return 'needs-evidence';
    }}
    function projectTagLabel(tag) {{
      if (tag === 'delivered') return '{escape(copy["project_tag_delivered"])}';
      if (tag === 'high-quality') return '{escape(copy["project_tag_high_quality"])}';
      return '{escape(copy["project_tag_needs_evidence"])}';
    }}
    function projectNextActionLabel(type) {{
      if (type === 'collect-evidence') return '{escape(copy["project_next_action_collect_evidence_projects"])}';
      if (type === 'rerun-analysis') return '{escape(copy["project_next_action_rerun_analysis_projects"])}';
      if (type === 'archive-project') return '{escape(copy["project_next_action_archive_projects"])}';
      return '{escape(copy["project_next_action_review_report_projects"])}';
    }}
    function projectNextActionQueueButtonLabel(type) {{
      if (type === 'collect-evidence') return '{escape(copy["filter_to_collect_evidence"])}';
      if (type === 'rerun-analysis') return '{escape(copy["filter_to_rerun_analysis"])}';
      if (type === 'archive-project') return '{escape(copy["filter_to_archive_projects"])}';
      return '{escape(copy["filter_to_review_reports"])}';
    }}
    function projectOwnerForRecord(project) {{
      if (project && project.owner) return project.owner;
      var action = projectNextActionSummary(project);
      var type = action.type || 'review-report';
      if (type === 'collect-evidence') return 'evidence-owner';
      if (type === 'rerun-analysis') return 'rerun-owner';
      if (type === 'archive-project') return 'archive-owner';
      if (type === 'review-report') return 'report-reviewer';
      return 'unassigned-owner';
    }}
    function projectOwnerLabel(owner) {{
      if (owner === 'evidence-owner') return '{escape(copy["project_owner_evidence"])}';
      if (owner === 'report-reviewer') return '{escape(copy["project_owner_reviewer"])}';
      if (owner === 'rerun-owner') return '{escape(copy["project_owner_rerun"])}';
      if (owner === 'archive-owner') return '{escape(copy["project_owner_archive"])}';
      return '{escape(copy["project_owner_unassigned"])}';
    }}
    function projectOwnerOptions(selectedOwner) {{
      var selected = selectedOwner || '';
      var owners = [
        ['unassigned-owner', '{escape(copy["project_owner_unassigned"])}'],
        ['evidence-owner', '{escape(copy["project_owner_evidence"])}'],
        ['report-reviewer', '{escape(copy["project_owner_reviewer"])}'],
        ['rerun-owner', '{escape(copy["project_owner_rerun"])}'],
        ['archive-owner', '{escape(copy["project_owner_archive"])}']
      ];
      return owners.map(function(item) {{
        return '<option value="' + escapeHtml(item[0]) + '"' + (selected === item[0] ? ' selected' : '') + '>' + escapeHtml(item[1]) + '</option>';
      }}).join('');
    }}
    function renderProjectOwnerQueueSummary(projects) {{
      var summary = document.getElementById('project-owner-queue-summary');
      if (!summary) return;
      var records = Array.isArray(projects) ? projects : [];
      var owners = ['unassigned-owner', 'evidence-owner', 'report-reviewer', 'rerun-owner', 'archive-owner'];
      var counts = {{
        'unassigned-owner': 0,
        'evidence-owner': 0,
        'report-reviewer': 0,
        'rerun-owner': 0,
        'archive-owner': 0
      }};
      records.forEach(function(project) {{
        var owner = projectOwnerForRecord(project);
        if (!Object.prototype.hasOwnProperty.call(counts, owner)) counts[owner] = 0;
        counts[owner] += 1;
      }});
      summary.innerHTML =
        '<header><div><h3>{escape(copy["project_owner_queue"])}</h3><small>{escape(copy["project_owner_queue_description"])}</small></div></header>' +
        owners.map(function(owner) {{
          var count = counts[owner] || 0;
          return '<button type="button" data-project-owner-queue="' + escapeHtml(owner) + '" data-project-owner-count="' + escapeHtml(String(count)) + '" onclick="filterProjectOwnerQueue(\\'' + escapeHtml(owner) + '\\')">' +
            '<small>' + escapeHtml(projectOwnerLabel(owner)) + '</small>' +
            '<strong>' + escapeHtml(String(count)) + '</strong>' +
            '</button>';
        }}).join('');
    }}
    function filterProjectOwnerQueue(owner) {{
      var select = document.getElementById('project-owner-filter');
      if (select) select.value = owner || '';
      filterResearchProjects();
      return false;
    }}
    function projectActivityState(project) {{
      var activity = projectReviewActivitySummary(project);
      return activity.count > 0 ? 'has-activity' : 'no-activity';
    }}
    function projectActivityStateLabel(state) {{
      if (state === 'has-activity') return '{escape(copy["has_activity"])}';
      if (state === 'no-activity') return '{escape(copy["no_activity"])}';
      return '{escape(copy["all_activity_states"])}';
    }}
    function filterProjectActivity(state) {{
      var select = document.getElementById('project-activity-filter');
      if (select) select.value = state || '';
      filterResearchProjects();
      return false;
    }}
    function renderProjectNextActionQueueSummary(projects) {{
      var summary = document.getElementById('project-next-action-queue-summary');
      if (!summary) return;
      var records = Array.isArray(projects) ? projects : [];
      var actionTypes = ['collect-evidence', 'review-report', 'rerun-analysis', 'archive-project'];
      var counts = {{
        'collect-evidence': 0,
        'review-report': 0,
        'rerun-analysis': 0,
        'archive-project': 0
      }};
      records.forEach(function(project) {{
        var action = projectNextActionSummary(project);
        var type = action.type || 'review-report';
        if (!Object.prototype.hasOwnProperty.call(counts, type)) counts[type] = 0;
        counts[type] += 1;
      }});
      summary.innerHTML =
        '<header><div><h3>{escape(copy["next_action_queue"])}</h3><small>{escape(copy["queue_by_workflow_step"])}</small></div>' +
        '<div class="project-library-actions">' +
        '<button type="button" data-project-queue-handoff="research-only" data-project-queue-handoff-action="copy" data-copied-text="{escape(copy["project_queue_handoff_copied"])}" onclick="copyProjectQueueHandoffBrief(this)">{escape(copy["copy_project_queue_handoff"])}</button>' +
        '<button type="button" data-filtered-project-handoff="research-only" data-filtered-project-handoff-action="copy" data-copied-text="{escape(copy["filtered_handoff_copied"])}" onclick="copyFilteredProjectQueueHandoffBrief(this)">{escape(copy["copy_filtered_handoff"])}</button>' +
        '</div></header>' +
        actionTypes.map(function(type) {{
          var count = counts[type] || 0;
          return '<button type="button" data-project-next-action-queue="' + escapeHtml(type) + '" data-project-next-action-count="' + escapeHtml(String(count)) + '" onclick="filterProjectNextActionQueue(\\'' + escapeHtml(type) + '\\')">' +
            '<small>' + escapeHtml(projectNextActionQueueButtonLabel(type)) + '</small>' +
            '<strong>' + escapeHtml(String(count)) + '</strong>' +
            '</button>';
        }}).join('');
    }}
    function filterProjectNextActionQueue(type) {{
      var select = document.getElementById('project-next-action-filter');
      if (select) select.value = type || '';
      filterResearchProjects();
      return false;
    }}
    function buildProjectQueueHandoffBrief(projects) {{
      var records = Array.isArray(projects) ? projects : [];
      var actionTypes = ['collect-evidence', 'review-report', 'rerun-analysis', 'archive-project'];
      var lines = [
        '{escape(copy["research_only_queue_handoff"])}',
        '{escape(copy["project_queue_handoff"])}',
        '{escape(copy["comparison_brief_boundary"])}'
      ];
      actionTypes.forEach(function(type) {{
        var grouped = records.filter(function(project) {{
          return (projectNextActionSummary(project).type || 'review-report') === type;
        }});
        lines.push('');
        lines.push('{escape(copy["queue_handoff_action"])}: ' + projectNextActionLabel(type) + ' (' + grouped.length + ')');
        if (!grouped.length) {{
          lines.push('- {escape(copy["project_comparison_empty"])}');
          return;
        }}
        grouped.slice(0, 8).forEach(function(project) {{
          var action = projectNextActionSummary(project);
          var quality = project.quality || {{}};
          var qualityText = (quality.status || '{escape(copy["not_generated"])}') + ' · ' + (quality.score || 'n/a');
          lines.push('- ' + [
            project.query || '{escape(copy["not_generated"])}',
            project.topTicker || 'n/a',
            qualityText,
            action.reason || '{escape(copy["project_next_action_review_reason"])}',
            project.href || ''
          ].filter(Boolean).join(' | '));
        }});
      }});
      return lines.join('\\n');
    }}
    function renderProjectQueueHandoffPreview(projects) {{
      var preview = document.getElementById('project-queue-handoff-preview');
      if (!preview) return;
      var records = Array.isArray(projects) ? projects : [];
      var previewLines = buildProjectQueueHandoffBrief(records).split('\\n').slice(0, 18);
      var hiddenLines = Math.max(0, buildProjectQueueHandoffBrief(records).split('\\n').length - previewLines.length);
      var body = previewLines.join('\\n');
      if (hiddenLines > 0) {{
        body += '\\n... +' + hiddenLines + ' lines';
      }}
      preview.setAttribute('data-project-queue-handoff-preview', 'research-only');
      preview.setAttribute('data-project-queue-handoff-items', String(records.length));
      preview.innerHTML =
        '<header><div><h3>{escape(copy["queue_handoff_preview"])}</h3><small>{escape(copy["review_handoff_before_copying"])}</small></div>' +
        '<strong>{escape(copy["handoff_item_count"])}: ' + escapeHtml(String(records.length)) + '</strong></header>' +
        '<pre>' + escapeHtml(body) + '</pre>';
    }}
    function copyProjectQueueHandoffBrief(button) {{
      var text = buildProjectQueueHandoffBrief(readResearchProjectLibrary());
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(text).catch(function() {{}});
      }}
      if (button) button.textContent = button.getAttribute('data-copied-text') || button.textContent;
      appendProjectReviewEvent({{ id: 'queue-handoff', query: '{escape(copy["project_queue_handoff"])}' }}, 'queue-handoff-copied', '{escape(copy["project_queue_handoff_copied"])}');
      return false;
    }}
    function buildFilteredProjectQueueHandoffBrief(projects) {{
      var source = Array.isArray(projects) ? projects : readResearchProjectLibrary();
      return buildProjectQueueHandoffBrief(projectLibraryFilteredRecords(source));
    }}
    function renderFilteredProjectQueueHandoffPreview(projects) {{
      var preview = document.getElementById('filtered-project-handoff-preview');
      if (!preview) return;
      var source = Array.isArray(projects) ? projects : readResearchProjectLibrary();
      var records = projectLibraryFilteredRecords(source);
      var handoff = buildProjectQueueHandoffBrief(records).split('\\n');
      var previewLines = handoff.slice(0, 18);
      var hiddenLines = Math.max(0, handoff.length - previewLines.length);
      var body = previewLines.join('\\n');
      if (hiddenLines > 0) {{
        body += '\\n... +' + hiddenLines + ' lines';
      }}
      preview.setAttribute('data-filtered-project-handoff-preview', 'research-only');
      preview.setAttribute('data-filtered-project-handoff-items', String(records.length));
      preview.innerHTML =
        '<header><div><h3>{escape(copy["filtered_handoff_preview"])}</h3><small>{escape(copy["review_handoff_before_copying"])}</small></div>' +
        '<strong>{escape(copy["filtered_item_count"])}: ' + escapeHtml(String(records.length)) + '</strong></header>' +
        '<pre>' + escapeHtml(body) + '</pre>';
    }}
    function copyFilteredProjectQueueHandoffBrief(button) {{
      var text = buildFilteredProjectQueueHandoffBrief(readResearchProjectLibrary());
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(text).catch(function() {{}});
      }}
      if (button) button.textContent = button.getAttribute('data-copied-text') || button.textContent;
      appendProjectReviewEvent({{ id: 'filtered-queue-handoff', query: '{escape(copy["filtered_project_handoff"])}' }}, 'queue-handoff-copied', '{escape(copy["filtered_handoff_copied"])}');
      return false;
    }}
    function projectLibraryFilteredRecords(projects) {{
      var records = Array.isArray(projects) ? projects.slice() : [];
      var select = document.getElementById('project-status-filter');
      var selectedStatus = select ? select.value : '';
      var searchInput = document.getElementById('project-library-search');
      var searchText = searchInput ? normalizeText(searchInput.value || '') : '';
      var tagSelect = document.getElementById('project-tag-filter');
      var selectedTag = tagSelect ? tagSelect.value : '';
      var nextActionSelect = document.getElementById('project-next-action-filter');
      var selectedNextAction = nextActionSelect ? nextActionSelect.value : '';
      var ownerSelect = document.getElementById('project-owner-filter');
      var selectedOwner = ownerSelect ? ownerSelect.value : '';
      var activitySelect = document.getElementById('project-activity-filter');
      var selectedActivity = activitySelect ? activitySelect.value : '';
      var sortSelect = document.getElementById('project-library-sort');
      var sortMode = sortSelect ? sortSelect.value : 'recent';
      records = records.filter(function(project) {{
        var status = project.status || 'pending-evidence';
        var tag = projectTagForRecord(project);
        var nextAction = projectNextActionSummary(project);
        var nextActionType = nextAction.type || 'review-report';
        var owner = projectOwnerForRecord(project);
        var activity = projectReviewActivitySummary(project);
        var activityState = projectActivityState(project);
        var quality = project.quality || {{}};
        var haystack = normalizeText([
          project.query || '',
          project.topTicker || '',
          project.gap || '',
          status,
          tag,
          nextActionType,
          projectNextActionLabel(nextActionType),
          nextAction.label || '',
          nextAction.reason || '',
          owner,
          projectOwnerLabel(owner),
          activityState,
          projectActivityStateLabel(activityState),
          activity.summary || '',
          activity.latestLabel || '',
          quality.status || '',
          quality.score || ''
        ].join(' '));
        if (selectedStatus && status !== selectedStatus) return false;
        if (selectedTag && tag !== selectedTag) return false;
        if (selectedNextAction && nextActionType !== selectedNextAction) return false;
        if (selectedOwner && owner !== selectedOwner) return false;
        if (selectedActivity && activityState !== selectedActivity) return false;
        if (searchText && haystack.indexOf(searchText) === -1) return false;
        return true;
      }});
      records.sort(function(a, b) {{
        if (sortMode === 'activity') {{
          return projectReviewActivitySummary(b).count - projectReviewActivitySummary(a).count;
        }}
        if (sortMode === 'quality') {{
          return (parseProjectQualityScore(b) || 0) - (parseProjectQualityScore(a) || 0);
        }}
        if (sortMode === 'topic') {{
          return String(a.query || '').localeCompare(String(b.query || ''));
        }}
        return String(b.savedAt || '').localeCompare(String(a.savedAt || ''));
      }});
      return records;
    }}
    function projectReviewAction(project) {{
      var status = project && project.status ? project.status : 'pending-evidence';
      var gap = project && project.gap ? project.gap : '';
      if (status === 'delivered') return '{escape(copy["project_review_action_delivered"])}';
      if (status === 'needs-rerun') return '{escape(copy["project_review_action_rerun"])}';
      if (gap) return '{escape(copy["project_review_action_gap"])}';
      return '{escape(copy["project_review_action_report"])}';
    }}
    function projectReviewTimelineStorageKey() {{
      return 'serenity-alpha-lab-project-review-timeline-v1';
    }}
    function readProjectReviewTimeline() {{
      try {{
        return JSON.parse(localStorage.getItem(projectReviewTimelineStorageKey()) || '[]');
      }} catch (error) {{
        return [];
      }}
    }}
    function writeProjectReviewTimeline(events) {{
      var bounded = (Array.isArray(events) ? events : []).slice(0, 50);
      try {{
        localStorage.setItem(projectReviewTimelineStorageKey(), JSON.stringify(bounded));
      }} catch (error) {{}}
      return bounded;
    }}
    function projectEvidenceAuditLogStorageKey() {{
      return 'serenity-alpha-lab-project-evidence-audit-log-v1';
    }}
    function readProjectEvidenceAuditLog() {{
      try {{
        return JSON.parse(localStorage.getItem(projectEvidenceAuditLogStorageKey()) || '[]');
      }} catch (error) {{
        return [];
      }}
    }}
    function writeProjectEvidenceAuditLog(entries) {{
      var bounded = (Array.isArray(entries) ? entries : []).slice(0, 50);
      try {{
        localStorage.setItem(projectEvidenceAuditLogStorageKey(), JSON.stringify(bounded));
      }} catch (error) {{}}
      return bounded;
    }}
    function appendProjectEvidenceAuditEntry(entry) {{
      var payload = entry || {{}};
      var quality = collectWorkspaceQualitySnapshot();
      var qualityBefore = payload.qualityBefore || 'n/a';
      var qualityAfter = payload.qualityAfter || quality.score || 'n/a';
      var auditEntry = {{
        id: String(Date.now()) + '-' + String(Math.random()).slice(2, 8),
        projectId: payload.projectId || window.location.pathname || '',
        projectQuery: payload.projectQuery || '{escape(copy["query"])}' || document.title || '',
        taskId: payload.taskId || '',
        ticker: payload.ticker || '',
        type: payload.type || 'verified-task',
        label: payload.label || '{escape(copy["verified_task_audit_trail"])}',
        qualityBefore: qualityBefore,
        qualityAfter: qualityAfter,
        qualityDelta: payload.qualityDelta || qualityDeltaAfterRerun(qualityBefore, qualityAfter),
        at: new Date().toISOString()
      }};
      var entries = readProjectEvidenceAuditLog();
      entries.unshift(auditEntry);
      writeProjectEvidenceAuditLog(entries);
      renderProjectEvidenceAuditLog(auditEntry.projectId || '');
      writeProjectEvidenceAuditEntryToServer(auditEntry);
      return auditEntry;
    }}
    function renderProjectEvidenceAuditLog(projectId) {{
      var list = document.getElementById('project-evidence-audit-list');
      if (!list) return;
      var entries = readProjectEvidenceAuditLog().filter(function(entry) {{
        if (!projectId) return true;
        return entry.projectId === projectId || entry.projectId === window.location.pathname;
      }}).slice(0, 8);
      if (!entries.length) {{
        list.innerHTML = '<li data-project-evidence-audit="empty" data-project-evidence-audit-type="empty" data-project-evidence-audit-quality-delta="n/a"><small>{escape(copy["project_evidence_audit_empty"])}</small></li>';
        return;
      }}
      list.innerHTML = entries.map(function(entry) {{
        var label = entry.label || '{escape(copy["verified_task_audit_trail"])}';
        var delta = entry.qualityDelta || 'n/a';
        var detail = (entry.ticker || 'n/a') + ' · ' + (entry.taskId || 'n/a') + ' · {escape(copy["quality_contribution"])} ' + delta;
        return '<li data-project-evidence-audit="' + escapeHtml(entry.id || '') + '" data-project-evidence-audit-type="' + escapeHtml(entry.type || 'verified-task') + '" data-project-evidence-audit-quality-delta="' + escapeHtml(delta) + '">' +
          '<strong>' + escapeHtml(label) + '</strong>' +
          '<small>' + escapeHtml(detail) + '</small>' +
          '<small>' + escapeHtml((entry.qualityBefore || 'n/a') + ' → ' + (entry.qualityAfter || 'n/a')) + '</small>' +
          '<time datetime="' + escapeHtml(entry.at || '') + '">' + escapeHtml(entry.at || '') + '</time>' +
          '</li>';
      }}).join('');
    }}
    function renderProjectEvidenceQualityDeltaSummary(summary) {{
      var target = document.getElementById('project-evidence-quality-delta-summary');
      if (!target) return;
      var item = summary || {{}};
      if (!item.qualityDelta) {{
        target.setAttribute('data-project-evidence-quality-delta', 'n/a');
        target.innerHTML = '<strong>{escape(copy["latest_quality_delta"])}</strong><small>{escape(copy["quality_delta_summary_empty"])}</small>';
        return;
      }}
      var ticker = item.ticker || 'n/a';
      var taskId = item.taskId || 'n/a';
      var before = item.qualityBefore || 'n/a';
      var after = item.qualityAfter || 'n/a';
      var delta = item.qualityDelta || 'n/a';
      target.setAttribute('data-project-evidence-quality-delta', delta);
      target.innerHTML = '<strong>{escape(copy["latest_quality_delta"])}</strong>' +
        '<small>' + escapeHtml(ticker + ' · ' + taskId) + '</small>' +
        '<span>' + escapeHtml(before + ' → ' + after + ' · ' + delta) + '</span>';
    }}
    function projectEvidenceQualitySummary(project) {{
      var summary = project && project.evidenceQualitySummary ? project.evidenceQualitySummary : {{}};
      return summary && summary.qualityDelta ? summary : {{}};
    }}
    function renderProjectEvidenceImpactSummary(project) {{
      var summary = projectEvidenceQualitySummary(project);
      if (!summary.qualityDelta) {{
        return '<small data-project-evidence-impact="empty"><strong>{escape(copy["latest_evidence_impact"])}:</strong> {escape(copy["quality_delta_summary_empty"])}</small>';
      }}
      var before = summary.qualityBefore || 'n/a';
      var after = summary.qualityAfter || 'n/a';
      var delta = summary.qualityDelta || 'n/a';
      var ticker = summary.ticker || 'n/a';
      var taskId = summary.taskId || 'n/a';
      return '<small data-project-evidence-impact="' + escapeHtml(delta) + '"><strong>{escape(copy["latest_evidence_impact"])}:</strong> ' +
        escapeHtml(before + ' → ' + after + ' · ' + delta + ' · ' + ticker + ' · ' + taskId) + '</small>';
    }}
    function projectEvidenceProgressSummary(project) {{
      var summary = project && project.evidenceProgressSummary ? project.evidenceProgressSummary : {{}};
      return summary && Number(summary.total || 0) > 0 ? summary : {{}};
    }}
    function renderProjectEvidenceProgressSummary(project) {{
      var progress = projectEvidenceProgressSummary(project);
      var total = Number(progress.total || 0);
      var verified = Number(progress.verified || 0);
      var collected = Number(progress.collected || 0);
      var toCollect = Number(progress.toCollect || 0);
      if (!total) {{
        return '<small data-project-evidence-progress="empty" data-project-verified-tasks="0"><strong>{escape(copy["evidence_progress"])}:</strong> {escape(copy["evidence_progress_empty"])}</small>';
      }}
      var label = progress.label || (String(verified) + '/' + String(total) + ' verified');
      return '<small data-project-evidence-progress="' + escapeHtml(label) + '" data-project-verified-tasks="' + escapeHtml(String(verified)) + '"><strong>{escape(copy["evidence_progress"])}:</strong> ' +
        escapeHtml(label + ' · ' + String(collected) + ' {escape(copy["task_collected"])} · ' + String(toCollect) + ' {escape(copy["task_to_collect"])}') + '</small>';
    }}
    function projectNextActionSummary(project) {{
      var summary = project && project.nextActionSummary ? project.nextActionSummary : {{}};
      if (summary && summary.type) return summary;
      return {{
        type: 'review-report',
        priority: 'medium',
        label: '{escape(copy["project_next_action_review_report"])}',
        reason: '{escape(copy["project_next_action_review_reason"])}'
      }};
    }}
    function renderProjectNextActionSummary(project) {{
      var action = projectNextActionSummary(project);
      return '<small data-project-next-action="' + escapeHtml(action.type || 'review-report') + '" data-project-next-action-priority="' + escapeHtml(action.priority || 'medium') + '"><strong>{escape(copy["workflow_next_step"])}:</strong> ' +
        escapeHtml((action.label || '{escape(copy["project_next_action_review_report"])}') + ' · ' + (action.reason || '{escape(copy["project_next_action_review_reason"])}')) + '</small>';
    }}
    function appendProjectReviewEvent(project, type, label) {{
      var target = project || {{}};
      var event = {{
        id: String(Date.now()) + '-' + String(Math.random()).slice(2, 8),
        projectId: target.id || '',
        projectQuery: target.query || target.id || '{escape(copy["not_generated"])}',
        type: type || 'review-event',
        label: label || '{escape(copy["log_review_event"])}',
        at: new Date().toISOString()
      }};
      var events = readProjectReviewTimeline();
      events.unshift(event);
      writeProjectReviewTimeline(events);
      renderProjectReviewTimeline(target.id || '');
      writeProjectReviewEventToServer(event);
      return event;
    }}
    function projectReviewEventLabel(type) {{
      if (type === 'status-changed') return '{escape(copy["review_event_status_changed"])}';
      if (type === 'detail-opened') return '{escape(copy["review_event_detail_opened"])}';
      if (type === 'owner-changed') return '{escape(copy["review_event_owner_changed"])}';
      if (type === 'comparison-brief-copied') return '{escape(copy["review_event_comparison_copied"])}';
      if (type === 'queue-handoff-copied') return '{escape(copy["review_event_queue_handoff_copied"])}';
      return '{escape(copy["log_review_event"])}';
    }}
    function projectReviewEventTypeLabel(type) {{
      if (type === 'status-changed') return '{escape(copy["status_events"])}';
      if (type === 'owner-changed') return '{escape(copy["owner_events"])}';
      if (type === 'detail-opened') return '{escape(copy["detail_events"])}';
      if (type === 'comparison-brief-copied') return '{escape(copy["comparison_events"])}';
      if (type === 'queue-handoff-copied') return '{escape(copy["queue_handoff_events"])}';
      return '{escape(copy["all_review_events"])}';
    }}
    function projectReviewEventFilterValue() {{
      var select = document.getElementById('project-review-event-filter');
      return select ? select.value : '';
    }}
    function filterProjectReviewEvents(type) {{
      var select = document.getElementById('project-review-event-filter');
      if (select) select.value = type || '';
      renderProjectReviewTimeline('');
    }}
    function renderProjectReviewEventSummary(events) {{
      var summary = document.getElementById('project-review-event-summary');
      if (!summary) return;
      var types = ['', 'status-changed', 'owner-changed', 'detail-opened', 'comparison-brief-copied', 'queue-handoff-copied'];
      var counts = {{}};
      types.forEach(function(type) {{ counts[type] = type ? 0 : events.length; }});
      events.forEach(function(event) {{
        var type = event.type || 'review-event';
        if (Object.prototype.hasOwnProperty.call(counts, type)) counts[type] += 1;
      }});
      summary.innerHTML = types.map(function(type) {{
        return '<button type="button" data-project-review-event-filter="' + escapeHtml(type || 'all') + '" data-project-review-event-count="' + String(counts[type] || 0) + '" onclick="filterProjectReviewEvents(\\'' + escapeHtml(type) + '\\')">' +
          '<small>' + escapeHtml(projectReviewEventTypeLabel(type)) + '</small>' +
          '<strong>' + String(counts[type] || 0) + '</strong>' +
          '</button>';
      }}).join('');
    }}
    function projectReviewActivitySummary(project) {{
      var target = project || {{}};
      var projectId = target.id || '';
      var events = readProjectReviewTimeline().filter(function(event) {{
        return projectId && event.projectId === projectId;
      }}).sort(function(left, right) {{
        return String(right.at || '').localeCompare(String(left.at || ''));
      }});
      var latest = events[0] || null;
      var latestType = latest ? (latest.type || 'review-event') : 'empty';
      var latestLabel = latest ? (latest.label || projectReviewEventLabel(latestType)) : '{escape(copy["no_activity_yet"])}';
      return {{
        count: events.length,
        latestType: latestType,
        latestLabel: latestLabel,
        latestAt: latest ? (latest.at || '') : '',
        summary: latestLabel + ' · {escape(copy["activity_count"])}: ' + String(events.length)
      }};
    }}
    function renderProjectActivitySummary(project) {{
      var activity = projectReviewActivitySummary(project);
      return '<small class="project-activity-summary" data-project-activity-summary="' + escapeHtml(activity.summary) + '" data-project-activity-count="' + String(activity.count) + '" data-project-latest-activity="' + escapeHtml(activity.latestLabel) + '" data-project-latest-activity-label="{escape(copy["latest_activity"])}">' +
        '<strong>{escape(copy["latest_project_activity"])}:</strong> ' + escapeHtml(activity.latestLabel) +
        ' · <strong>{escape(copy["activity_count"])}:</strong> ' + String(activity.count) +
        (activity.latestAt ? ' · ' + escapeHtml(activity.latestAt) : '') +
        '</small>';
    }}
    function renderProjectReviewTimeline(projectId) {{
      var list = document.getElementById('project-review-timeline-list');
      if (!list) return;
      var events = readProjectReviewTimeline().filter(function(event) {{
        if (!projectId) return true;
        return event.projectId === projectId || event.projectId === 'comparison';
      }});
      renderProjectReviewEventSummary(events);
      var filterType = projectReviewEventFilterValue();
      if (filterType) {{
        events = events.filter(function(event) {{ return (event.type || 'review-event') === filterType; }});
      }}
      events = events.slice(0, 8);
      if (!events.length) {{
        list.innerHTML = '<li data-project-review-event="empty" data-project-review-event-type="empty" data-project-review-event-project=""><small>{escape(copy["project_review_timeline_empty"])}</small></li>';
        return;
      }}
      list.innerHTML = events.map(function(event) {{
        var type = event.type || 'review-event';
        var label = event.label || projectReviewEventLabel(type);
        return '<li data-project-review-event="' + escapeHtml(event.id || '') + '" data-project-review-event-type="' + escapeHtml(type) + '" data-project-review-event-project="' + escapeHtml(event.projectId || '') + '">' +
          '<strong>' + escapeHtml(label) + '</strong>' +
          '<small>' + escapeHtml(event.projectQuery || '{escape(copy["not_generated"])}') + '</small>' +
          '<time datetime="' + escapeHtml(event.at || '') + '">' + escapeHtml(event.at || '') + '</time>' +
          '</li>';
      }}).join('');
    }}
    function projectReviewActionPanelItems(project) {{
      var target = project || {{}};
      var href = target.href || '';
      var evidenceTarget = projectEvidenceTaskTarget(target);
      var rerunContext = persistProjectRerunContext(target, false);
      return [
        {{
          type: 'close-evidence-gap',
          label: '{escape(copy["close_evidence_gap"])}',
          detail: '{escape(copy["evidence_gap_linked_task"])} · ' + (target.gap || '{escape(copy["project_detail_boundary"])}'),
          enabled: true,
          evidenceTarget: evidenceTarget
        }},
        {{
          type: 'rerun-analysis',
          label: '{escape(copy["rerun_analysis"])}',
          detail: '{escape(copy["rerun_with_project_context"])} · ' + (target.query || '{escape(copy["not_generated"])}'),
          enabled: true,
          rerunContext: rerunContext
        }},
        {{
          type: 'mark-delivered',
          label: '{escape(copy["mark_delivered"])}',
          detail: projectStatusLabel(target.status || 'pending-evidence'),
          enabled: true
        }},
        {{
          type: 'open-report',
          label: '{escape(copy["open_report_from_action_panel"])}',
          detail: href || 'n/a',
          enabled: !!href
        }}
      ];
    }}
    function renderProjectReviewActionPanel(project) {{
      var panel = document.getElementById('project-review-action-list');
      if (!panel || !project) return;
      panel.innerHTML = projectReviewActionPanelItems(project).map(function(action) {{
        var disabled = action.enabled ? '' : ' disabled';
        var evidenceAttr = action.evidenceTarget ? ' data-project-evidence-task-target="' + escapeHtml(action.evidenceTarget) + '"' : '';
        var rerunAttr = action.rerunContext ? ' data-project-rerun-context="' + escapeHtml(action.rerunContext) + '"' : '';
        return '<button type="button" data-project-review-action-type="' + escapeHtml(action.type) + '" data-project-review-action-project="' + escapeHtml(project.id || '') + '"' + evidenceAttr + rerunAttr + ' onclick="handleProjectReviewAction(this)"' + disabled + '>' +
          '<strong>' + escapeHtml(action.label) + '</strong><small>' + escapeHtml(action.detail || '') + '</small>' +
          '</button>';
      }}).join('');
    }}
    function projectEvidenceTaskTarget(project) {{
      var target = project || {{}};
      var topTicker = String(target.topTicker || '').toUpperCase();
      var gap = String(target.gap || '').toLowerCase();
      var cards = Array.prototype.slice.call(document.querySelectorAll('[data-task-id]'));
      var match = cards.filter(function(card) {{
        var ticker = String(card.getAttribute('data-ticker') || '').toUpperCase();
        var search = String(card.getAttribute('data-search') || '').toLowerCase();
        return (topTicker && ticker === topTicker) || (gap && search.indexOf(gap) >= 0);
      }})[0];
      if (match) {{
        if (!match.id) match.id = 'project-evidence-task-' + (match.getAttribute('data-task-id') || 'target').replace(/[^a-zA-Z0-9_-]+/g, '-');
        return '#' + match.id;
      }}
      return '#evidence-tasks';
    }}
    function updateProjectReviewLoopStatus(text, context) {{
      var status = document.getElementById('project-review-loop-status');
      if (!status) return;
      status.textContent = text || '{escape(copy["project_review_loop_idle"])}';
      if (context) status.setAttribute('data-project-rerun-context', context);
      status.setAttribute('data-project-quality-after-rerun', collectWorkspaceQualitySnapshot().score || 'n/a');
    }}
    function focusProjectEvidenceTask(project) {{
      var selector = projectEvidenceTaskTarget(project);
      var target = selector ? document.querySelector(selector) : null;
      Array.prototype.slice.call(document.querySelectorAll('[data-project-evidence-focus="true"]')).forEach(function(card) {{
        card.removeAttribute('data-project-evidence-focus');
        card.classList.remove('is-project-focus');
      }});
      if (target) {{
        target.setAttribute('data-project-evidence-focus', 'true');
        target.classList.add('is-project-focus');
        if (target.scrollIntoView) target.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
      }}
      updateProjectReviewLoopStatus('{escape(copy["jump_to_evidence_task"])} · ' + (project && project.gap ? project.gap : selector), '');
      appendProjectReviewEvent(project || {{}}, 'evidence-task-focused', '{escape(copy["jump_to_evidence_task"])}');
      return !!target;
    }}
    function projectRerunUrl(project) {{
      var target = project || {{}};
      var params = new URLSearchParams();
      params.set('query', target.query || '');
      params.set('language', '{escape(copy["language"])}');
      if (target.id) params.set('projectId', target.id);
      if (target.href) params.set('projectHref', target.href);
      var quality = target.quality || collectWorkspaceQualitySnapshot();
      if (quality && quality.score) params.set('qualityBefore', quality.score);
      return '/analyze?' + params.toString();
    }}
    function persistProjectRerunContext(project, shouldWrite) {{
      var target = project || {{}};
      var quality = target.quality || collectWorkspaceQualitySnapshot();
      var context = {{
        projectId: target.id || '',
        query: target.query || '',
        href: target.href || '',
        topTicker: target.topTicker || '',
        gap: target.gap || '',
        qualityBefore: quality.score || 'n/a',
        qualityStatusBefore: quality.status || 'n/a',
        qualityAfter: collectWorkspaceQualitySnapshot().score || 'n/a',
        at: new Date().toISOString()
      }};
      var encoded = encodeURIComponent(JSON.stringify(context));
      if (shouldWrite) {{
        try {{
          window.localStorage.setItem('serenity-alpha-lab:project-rerun-context', JSON.stringify(context));
        }} catch (error) {{}}
        updateProjectReviewLoopStatus('{escape(copy["quality_after_rerun"])} · ' + context.qualityAfter, encoded);
      }}
      return encoded;
    }}
    function applyProjectRerunContext() {{
      var raw = '';
      try {{
        raw = window.localStorage.getItem('serenity-alpha-lab:project-rerun-context') || '';
      }} catch (error) {{}}
      if (!raw) return null;
      var context = null;
      try {{
        context = JSON.parse(raw);
      }} catch (error) {{
        return null;
      }}
      var encoded = encodeURIComponent(JSON.stringify(context));
      updateProjectReviewLoopStatus('{escape(copy["quality_after_rerun"])} · ' + (context.qualityAfter || 'n/a') + ' / ' + (context.qualityBefore || 'n/a'), encoded);
      return context;
    }}
    function projectFromReviewActionButton(button) {{
      var projectId = button ? button.getAttribute('data-project-review-action-project') : '';
      var projects = readResearchProjectLibrary();
      return projects.filter(function(record) {{ return record.id === projectId; }})[0] || {{
        id: projectId,
        query: document.getElementById('project-detail-title') ? document.getElementById('project-detail-title').textContent : projectId,
        href: ''
      }};
    }}
    function markProjectDeliveredFromDrawer(project) {{
      if (!project || !project.id) return false;
      var projects = readResearchProjectLibrary().map(function(record) {{
        if (record.id === project.id) {{
          record.status = 'delivered';
          record.savedAt = new Date().toISOString();
          project = record;
        }}
        return record;
      }});
      writeResearchProjectLibrary(projects);
      renderResearchProjectLibrary(projects);
      writeResearchProjectToServer(projects);
      renderProjectDetailDrawer(project);
      return true;
    }}
    function rerunProjectAnalysisFromDrawer(project) {{
      if (!project || !project.query) return false;
      window.location.href = projectRerunUrl(project);
      return true;
    }}
    function handleProjectReviewAction(button) {{
      var actionType = button ? button.getAttribute('data-project-review-action-type') : '';
      var project = projectFromReviewActionButton(button);
      if (!project) return false;
      if (actionType === 'mark-delivered') {{
        markProjectDeliveredFromDrawer(project);
      }} else if (actionType === 'rerun-analysis') {{
        persistProjectRerunContext(project, true);
        appendProjectReviewEvent(project, 'rerun-analysis', '{escape(copy["rerun_analysis"])}');
        rerunProjectAnalysisFromDrawer(project);
        return false;
      }} else if (actionType === 'close-evidence-gap') {{
        focusProjectEvidenceTask(project);
        if (button) button.setAttribute('data-project-review-action-logged', 'true');
        return false;
      }} else if (actionType === 'open-report') {{
        appendProjectReviewEvent(project, 'open-report', '{escape(copy["open_report_from_action_panel"])}');
        if (project.href) window.location.href = project.href;
        return false;
      }}
      appendProjectReviewEvent(project, actionType || 'review-action', '{escape(copy["action_logged"])}');
      if (button) button.setAttribute('data-project-review-action-logged', 'true');
      return false;
    }}
    function renderProjectDetailDrawer(project) {{
      var drawer = document.getElementById('project-detail-drawer');
      var title = document.getElementById('project-detail-title');
      var body = document.getElementById('project-detail-body');
      var qualityEl = document.getElementById('project-detail-quality');
      var actions = document.getElementById('project-detail-actions');
      if (!drawer || !project || !body) return false;
      var quality = project.quality || {{}};
      var qualityText = (quality.status || '{escape(copy["not_generated"])}') + ' · ' + (quality.score || 'n/a');
      var status = project.status || 'pending-evidence';
      var tag = projectTagForRecord(project);
      var reviewAction = projectReviewAction(project);
      var evidenceSummary = projectEvidenceQualitySummary(project);
      var evidenceDelta = evidenceSummary.qualityDelta || 'n/a';
      var progressSummary = projectEvidenceProgressSummary(project);
      var progressLabel = progressSummary.label || 'n/a';
      var nextAction = projectNextActionSummary(project);
      var activity = projectReviewActivitySummary(project);
      if (title) title.textContent = project.query || '{escape(copy["project_review_panel"])}';
      if (qualityEl) qualityEl.textContent = qualityText;
      body.innerHTML =
        '<div class="project-detail-grid" data-project-detail-id="' + escapeHtml(project.id || '') + '">' +
        '<article class="project-detail-card" data-project-detail-quality="' + escapeHtml(qualityText) + '"><span>{escape(copy["project_detail_quality"])}</span><strong>' + escapeHtml(qualityText) + '</strong><small>' + escapeHtml(project.topTicker || 'n/a') + '</small></article>' +
        '<article class="project-detail-card" data-project-detail-gap="' + escapeHtml(project.gap || 'n/a') + '"><span>{escape(copy["project_detail_gap"])}</span><strong>' + escapeHtml(project.gap || 'n/a') + '</strong><small>' + escapeHtml(projectTagLabel(tag)) + '</small></article>' +
        '<article class="project-detail-card"><span>{escape(copy["project_detail_status"])}</span><strong>' + projectStatusLabel(status) + '</strong><small>' + escapeHtml(project.savedAt || '') + '</small></article>' +
        '<article class="project-detail-card" data-project-quality-delta="' + escapeHtml(evidenceDelta) + '"><span>{escape(copy["latest_evidence_impact"])}</span><strong>' + escapeHtml(evidenceDelta) + '</strong><small>' + escapeHtml((evidenceSummary.qualityBefore || 'n/a') + ' → ' + (evidenceSummary.qualityAfter || 'n/a')) + '</small></article>' +
        '<article class="project-detail-card" data-project-evidence-progress="' + escapeHtml(progressLabel) + '" data-project-verified-tasks="' + escapeHtml(String(progressSummary.verified || 0)) + '"><span>{escape(copy["evidence_progress"])}</span><strong>' + escapeHtml(progressLabel) + '</strong><small>' + escapeHtml(String(progressSummary.collected || 0) + ' {escape(copy["task_collected"])} · ' + String(progressSummary.toCollect || 0) + ' {escape(copy["task_to_collect"])}') + '</small></article>' +
        '<article class="project-detail-card" data-project-next-action="' + escapeHtml(nextAction.type || '') + '" data-project-next-action-priority="' + escapeHtml(nextAction.priority || '') + '"><span>{escape(copy["workflow_next_step"])}</span><strong>' + escapeHtml(nextAction.label || 'n/a') + '</strong><small>' + escapeHtml(nextAction.reason || 'n/a') + '</small></article>' +
        '<article class="project-detail-card" data-project-activity-summary="' + escapeHtml(activity.summary) + '" data-project-activity-count="' + String(activity.count) + '" data-project-latest-activity="' + escapeHtml(activity.latestLabel) + '" data-project-latest-activity-label="{escape(copy["latest_activity"])}"><span>{escape(copy["project_activity_summary"])}</span><strong>' + escapeHtml(activity.latestLabel) + '</strong><small>{escape(copy["latest_activity"])} · {escape(copy["activity_count"])}: ' + String(activity.count) + (activity.latestAt ? ' · ' + escapeHtml(activity.latestAt) : '') + '</small></article>' +
        '<article class="project-detail-card" data-project-review-action="' + escapeHtml(reviewAction) + '"><span>{escape(copy["next_review_action"])}</span><strong>' + escapeHtml(reviewAction) + '</strong><small>{escape(copy["project_detail_boundary"])}</small></article>' +
        '</div>';
      if (actions) {{
        var href = project.href || '';
        actions.innerHTML = href ?
          '<button type="button" onclick="window.location.href=\\'' + escapeHtml(href) + '\\'">{escape(copy["open_report_from_detail"])}</button>' :
          '<button type="button" disabled>{escape(copy["open_report_from_detail"])}</button>';
      }}
      renderProjectReviewActionPanel(project);
      renderProjectReviewTimeline(project.id || '');
      syncProjectEvidenceAuditLogFromServer(project.id || '');
      return true;
    }}
    function openProjectDetailDrawer(button) {{
      var item = button ? button.closest('[data-project-query]') : null;
      var projectId = item ? item.getAttribute('data-project-id') : '';
      var projects = readResearchProjectLibrary();
      var project = projects.filter(function(record) {{ return record.id === projectId; }})[0];
      if (!project && item) {{
        project = {{
          id: projectId,
          query: item.getAttribute('data-project-query') || '',
          href: item.getAttribute('data-project-href') || '',
          status: item.getAttribute('data-project-status') || 'pending-evidence',
          gap: item.getAttribute('data-project-detail-gap') || '',
          topTicker: item.getAttribute('data-project-top-ticker') || 'n/a',
          quality: {{ score: item.getAttribute('data-project-quality-score') || 'n/a' }}
        }};
      }}
      if (!project) return false;
      renderProjectDetailDrawer(project);
      appendProjectReviewEvent(project, 'detail-opened', '{escape(copy["review_event_detail_opened"])}');
      syncProjectReviewTimelineFromServer(project.id || '');
      var drawer = document.getElementById('project-detail-drawer');
      if (drawer) {{
        drawer.classList.add('is-open');
        drawer.removeAttribute('hidden');
      }}
      return false;
    }}
    function closeProjectDetailDrawer() {{
      var drawer = document.getElementById('project-detail-drawer');
      if (drawer) {{
        drawer.classList.remove('is-open');
        drawer.setAttribute('hidden', '');
      }}
      return false;
    }}
    function sortResearchProjects() {{
      renderResearchProjectLibrary(readResearchProjectLibrary());
      return false;
    }}
    function filterResearchProjects() {{
      renderResearchProjectLibrary(readResearchProjectLibrary());
      return false;
    }}
    function projectStatusOptions(selectedStatus) {{
      var statuses = [
        ['pending-evidence', '{escape(copy["project_status_pending_evidence"])}'],
        ['reviewable', '{escape(copy["project_status_reviewable"])}'],
        ['delivered', '{escape(copy["project_status_delivered"])}'],
        ['needs-rerun', '{escape(copy["project_status_needs_rerun"])}']
      ];
      return statuses.map(function(status) {{
        var selected = status[0] === selectedStatus ? ' selected' : '';
        return '<option value="' + status[0] + '"' + selected + '>' + status[1] + '</option>';
      }}).join('');
    }}
    function projectStatusLabel(status) {{
      if (status === 'reviewable') return '{escape(copy["project_status_reviewable"])}';
      if (status === 'delivered') return '{escape(copy["project_status_delivered"])}';
      if (status === 'needs-rerun') return '{escape(copy["project_status_needs_rerun"])}';
      return '{escape(copy["project_status_pending_evidence"])}';
    }}
    function currentResearchProjectStatus() {{
      var gate = document.getElementById('report-quality-gate');
      var status = gate ? gate.getAttribute('data-quality-status') : '';
      if (status === 'publishable') return 'reviewable';
      if (status === 'not-publishable') return 'needs-rerun';
      return 'pending-evidence';
    }}
    function collectResearchProjectSnapshot() {{
      var action = document.getElementById('research-action-workbench');
      var briefing = document.getElementById('analysis-briefing');
      var quality = collectWorkspaceQualitySnapshot();
      var query = '{escape(copy["query"])}' || document.title || '{escape(copy["not_generated"])}';
      var topTicker = action ? action.getAttribute('data-research-action-ticker') : '';
      if (!topTicker && briefing) topTicker = briefing.getAttribute('data-briefing-top-ticker') || '';
      return {{
        id: window.location.pathname || query,
        savedAt: new Date().toISOString(),
        query: query,
        href: window.location.pathname,
        status: currentResearchProjectStatus(),
        quality: quality,
        topTicker: topTicker || 'n/a',
        gap: action ? (action.getAttribute('data-research-action-gap') || '') : ''
      }};
    }}
    function saveResearchProject() {{
      var project = collectResearchProjectSnapshot();
      var projects = readResearchProjectLibrary();
      projects = projects.filter(function(item) {{ return item.id !== project.id; }});
      projects.unshift(project);
      projects = projects.slice(0, 12);
      writeResearchProjectLibrary(projects);
      renderResearchProjectLibrary(projects);
      writeResearchProjectToServer(projects);
      return false;
    }}
    function clearResearchProjectLibrary() {{
      writeResearchProjectLibrary([]);
      renderResearchProjectLibrary([]);
      clearResearchProjectsOnServer();
      return false;
    }}
    function updateResearchProjectStatus(select) {{
      var item = select.closest('[data-project-query]');
      var projectId = item ? item.getAttribute('data-project-id') : '';
      if (!projectId) return false;
      var changedProject = null;
      var projects = readResearchProjectLibrary().map(function(project) {{
        if (project.id === projectId) {{
          project.status = select.value || 'pending-evidence';
          project.savedAt = new Date().toISOString();
          changedProject = project;
        }}
        return project;
      }});
      writeResearchProjectLibrary(projects);
      renderResearchProjectLibrary(projects);
      writeResearchProjectToServer(projects);
      if (changedProject) appendProjectReviewEvent(changedProject, 'status-changed', '{escape(copy["review_event_status_changed"])}');
      return false;
    }}
    function updateResearchProjectOwner(select) {{
      var item = select.closest('[data-project-query]');
      var projectId = item ? item.getAttribute('data-project-id') : '';
      if (!projectId) return false;
      var changedProject = null;
      var projects = readResearchProjectLibrary().map(function(project) {{
        if (project.id === projectId) {{
          project.owner = select.value || 'unassigned-owner';
          project.savedAt = new Date().toISOString();
          changedProject = project;
        }}
        return project;
      }});
      writeResearchProjectLibrary(projects);
      renderResearchProjectLibrary(projects);
      writeResearchProjectToServer(projects);
      if (changedProject) appendProjectReviewEvent(changedProject, 'owner-changed', '{escape(copy["review_event_owner_changed"])}');
      return false;
    }}
    function openResearchProject(button) {{
      var item = button.closest('[data-project-query]');
      var href = item ? item.getAttribute('data-project-href') : '';
      if (href) window.location.href = href;
      return false;
    }}
    function renderResearchProjectLibrary(projects) {{
      var list = document.getElementById('project-library-list');
      var count = document.getElementById('project-library-count');
      if (!list) return;
      var records = Array.isArray(projects) ? projects : readResearchProjectLibrary();
      if (count) count.textContent = String(records.length);
      renderProjectComparisonSummary(records);
      renderProjectNextActionQueueSummary(records);
      renderProjectOwnerQueueSummary(records);
      renderProjectQueueHandoffPreview(records);
      renderFilteredProjectQueueHandoffPreview(records);
      renderProjectComparisonMatrix(records);
      var visibleRecords = projectLibraryFilteredRecords(records);
      if (!records.length) {{
        list.innerHTML = '<p><small>{escape(copy["project_library_empty"])}</small></p>';
        return;
      }}
      if (!visibleRecords.length) {{
        list.innerHTML = '<p><small>{escape(copy["project_library_no_matches"])}</small></p>';
        return;
      }}
      var selectedIds = selectedProjectComparisonIds();
      list.innerHTML = visibleRecords.map(function(project) {{
        var status = project.status || 'pending-evidence';
        var quality = project.quality || {{}};
        var qualityText = (quality.status || '{escape(copy["not_generated"])}') + ' · ' + (quality.score || 'n/a');
        var qualityScore = parseProjectQualityScore(project);
        var evidenceSummary = projectEvidenceQualitySummary(project);
        var evidenceDelta = evidenceSummary.qualityDelta || 'n/a';
        var progressSummary = projectEvidenceProgressSummary(project);
        var progressLabel = progressSummary.label || 'n/a';
        var nextAction = projectNextActionSummary(project);
        var owner = projectOwnerForRecord(project);
        var activity = projectReviewActivitySummary(project);
        var activityState = projectActivityState(project);
        var tag = projectTagForRecord(project);
        var gap = project.gap ? '<small><strong>{escape(copy["project_gap_label"])}:</strong> ' + escapeHtml(project.gap) + '</small>' : '';
        var selected = selectedIds.indexOf(project.id || '') !== -1;
        var selectedLabel = selected ? 'true' : 'false';
        var searchText = [project.query || '', project.topTicker || '', project.gap || '', status, tag, qualityText, evidenceDelta, progressLabel, nextAction.label || '', nextAction.reason || '', owner, projectOwnerLabel(owner), activityState, projectActivityStateLabel(activityState), activity.summary || '', activity.latestLabel || ''].join(' ');
        return '<article class="project-library-item" data-project-id="' + escapeHtml(project.id || '') + '" data-project-query="' + escapeHtml(project.query || '') + '" data-project-status="' + escapeHtml(status) + '" data-project-filter-status="' + escapeHtml(status) + '" data-project-quality-score="' + escapeHtml(qualityScore === null ? '' : String(qualityScore)) + '" data-project-quality-delta="' + escapeHtml(evidenceDelta) + '" data-project-evidence-progress="' + escapeHtml(progressLabel) + '" data-project-verified-tasks="' + escapeHtml(String(progressSummary.verified || 0)) + '" data-project-next-action="' + escapeHtml(nextAction.type || '') + '" data-project-next-action-filter="' + escapeHtml(nextAction.type || '') + '" data-project-next-action-priority="' + escapeHtml(nextAction.priority || '') + '" data-project-owner-filter="' + escapeHtml(owner) + '" data-project-owner-value="' + escapeHtml(owner) + '" data-project-activity-filter="' + escapeHtml(activityState) + '" data-project-activity-state="' + escapeHtml(projectActivityStateLabel(activityState)) + '" data-project-activity-summary="' + escapeHtml(activity.summary) + '" data-project-activity-count="' + String(activity.count) + '" data-project-latest-activity="' + escapeHtml(activity.latestLabel) + '" data-project-tag="' + escapeHtml(tag) + '" data-project-search-text="' + escapeHtml(searchText) + '" data-project-detail-id="' + escapeHtml(project.id || '') + '" data-project-detail-quality="' + escapeHtml(qualityText) + '" data-project-detail-gap="' + escapeHtml(project.gap || '') + '" data-project-review-action="' + escapeHtml(projectReviewAction(project)) + '" data-project-top-ticker="' + escapeHtml(project.topTicker || 'n/a') + '" data-project-href="' + escapeHtml(project.href || '') + '">' +
          '<header><div><strong>' + escapeHtml(project.query || '{escape(copy["not_generated"])}') + '</strong><small>' + escapeHtml(project.topTicker || 'n/a') + ' · ' + escapeHtml(project.savedAt || '') + '</small></div><span class="project-status-pill">' + projectStatusLabel(status) + '</span></header>' +
          '<small><strong>{escape(copy["project_tags"])}:</strong> ' + escapeHtml(projectTagLabel(tag)) + '</small>' +
          '<small><strong>{escape(copy["project_owner_filter_label"])}:</strong> ' + escapeHtml(projectOwnerLabel(owner)) + '</small>' +
          renderProjectActivitySummary(project) +
          renderProjectEvidenceImpactSummary(project) +
          renderProjectEvidenceProgressSummary(project) +
          renderProjectNextActionSummary(project) +
          '<small><strong>{escape(copy["project_quality_label"])}:</strong> ' + escapeHtml(qualityText) + '</small>' + gap +
          '<div class="project-library-controls"><label>{escape(copy["project_status"])} <select onchange="updateResearchProjectStatus(this)">' + projectStatusOptions(status) + '</select></label>' +
          '<label>{escape(copy["assign_project_owner"])} <select data-project-owner-select="' + escapeHtml(project.id || '') + '" onchange="updateResearchProjectOwner(this)">' + projectOwnerOptions(owner) + '</select></label>' +
          '<button type="button" onclick="openProjectDetailDrawer(this)">{escape(copy["review_project"])}</button>' +
          '<button type="button" data-project-compare-id="' + escapeHtml(project.id || '') + '" data-project-compare-selected="' + selectedLabel + '" aria-pressed="' + selectedLabel + '" onclick="toggleProjectComparisonSelection(this)">{escape(copy["select_for_comparison"])}</button>' +
          '<button type="button" onclick="openResearchProject(this)">{escape(copy["open_project_report"])}</button></div>' +
          '</article>';
      }}).join('');
    }}
    function initializeResearchProjectLibrary() {{
      renderResearchProjectLibrary(readResearchProjectLibrary());
      syncResearchProjectLibraryFromServer();
      syncProjectReviewTimelineFromServer('');
    }}
    function printDeliverableReport() {{
      var button = document.querySelector('[data-deliverable-href]');
      var href = button ? button.getAttribute('data-deliverable-href') : '';
      if (href) {{
        openMemoDrawer(button);
      }}
      window.setTimeout(function() {{ window.print(); }}, 250);
      return false;
    }}
    function launchExampleAnalysis(button) {{
      var input = document.getElementById('analysis-query');
      var form = input ? input.closest('form') : null;
      var query = button.getAttribute('data-example-query') || '';
      if (!input || !form || !query) return;
      input.value = query;
      form.removeAttribute('data-confirmed-launch');
      renderAnalysisInputPreview(form);
    }}
    function parseAnalysisInputPreview(query) {{
      var raw = String(query || '').trim();
      var lowered = raw.toLowerCase();
      var preview = {{
        intent: '{escape(copy["intent_theme"])}',
        canonical: raw || '{escape(copy["preview_waiting"])}',
        candidates: collectPreviewTickers(),
        coverage: '{escape(str(evidence_total))} {escape(copy["coverage_evidence_items"])}, {escape(str(primary_total))} {escape(copy["coverage_primary_items"])}, {escape(str(risk_total))} {escape(copy["coverage_risk_items"])}',
        candidateCoverage: [],
        evidenceGapTasks: [],
        outputs: '{escape(copy["expected_outputs_value"])}',
        source: '{escape(copy["preview_source_local"])}'
      }};
      if (!raw) return preview;
      if (lowered.indexOf('存储') !== -1 || lowered.indexOf('memory') !== -1) {{
        preview.intent = '{escape(copy["intent_industry"])}';
        preview.canonical = 'memory';
        preview.candidates = ['MU', 'SNDK', 'GIGADEVICE'];
      }} else if (lowered.indexOf('hbm') !== -1) {{
        preview.intent = '{escape(copy["intent_industry"])}';
        preview.canonical = 'HBM';
        preview.candidates = ['MU', 'SNDK', 'NVDA'];
      }} else if (lowered.indexOf('半导体设备') !== -1 || lowered.indexOf('equipment') !== -1) {{
        preview.intent = '{escape(copy["intent_sector"])}';
        preview.canonical = '{escape(copy["semiconductor_equipment_theme"])}';
        preview.candidates = ['ASML', 'AMAT', 'LRCX'];
      }} else if (/^\\$?[a-z]{{1,5}}(?:\\.[a-z]{{1,3}})?$/i.test(raw)) {{
        preview.intent = '{escape(copy["intent_ticker"])}';
        preview.canonical = raw.toUpperCase().replace(/^\\$/, '');
        preview.candidates = [preview.canonical].concat(collectPreviewTickers()).slice(0, 4);
      }}
      return preview;
    }}
    function fetchAnalysisInputPreview(query) {{
      var languageField = document.querySelector('input[name="language"]');
      var language = languageField ? languageField.value : '{escape(language_value)}';
      var url = '/api/resolve-topic?query=' + encodeURIComponent(query || '') + '&language=' + encodeURIComponent(language || 'en');
      return fetch(url, {{ headers: {{ 'Accept': 'application/json' }} }})
        .then(function(response) {{
          if (!response.ok) throw new Error('resolve-topic failed');
          return response.json();
        }})
        .then(function(payload) {{
          return {{
            intent: payload.intent_label || payload.intent || '{escape(copy["intent_theme"])}',
            canonical: payload.canonical_theme || '{escape(copy["preview_waiting"])}',
            candidates: Array.isArray(payload.candidate_tickers) && payload.candidate_tickers.length ? payload.candidate_tickers : collectPreviewTickers(),
            coverage: payload.coverage_label || '{escape(str(evidence_total))} {escape(copy["coverage_evidence_items"])}',
            candidateCoverage: Array.isArray(payload.candidate_coverage) ? payload.candidate_coverage : [],
            evidenceGapTasks: Array.isArray(payload.evidence_gap_tasks) ? payload.evidence_gap_tasks : [],
            outputs: payload.expected_outputs || '{escape(copy["expected_outputs_value"])}',
            source: '{escape(copy["preview_source_backend"])}'
          }};
        }});
    }}
    function collectPreviewTickers() {{
      var tickers = [];
      Array.prototype.slice.call(document.querySelectorAll('[data-ticker]')).forEach(function(item) {{
        var ticker = (item.getAttribute('data-ticker') || '').toUpperCase();
        if (ticker && tickers.indexOf(ticker) === -1) tickers.push(ticker);
      }});
      return tickers.length ? tickers.slice(0, 4) : ['SIVE', 'AAOI'];
    }}
    function renderCandidateCoverageSummary(items) {{
      var rows = Array.isArray(items) ? items.slice(0, 6) : [];
      if (!rows.length) return '<span class="candidate-coverage-chip">{escape(copy["candidate_coverage_empty"])}</span>';
      return rows.map(function(item) {{
        var ticker = escapeHtml(item.ticker || 'n/a');
        var evidence = item.evidence_count === 0 || item.evidence_count ? String(item.evidence_count) : '0';
        var primary = item.primary_count === 0 || item.primary_count ? String(item.primary_count) : '0';
        var risk = item.risk_count === 0 || item.risk_count ? String(item.risk_count) : '0';
        return '<span class="candidate-coverage-chip"><b>' + ticker + '</b>' +
          '<span>' + evidence + ' {escape(copy["coverage_evidence_items"])} · ' + primary + ' {escape(copy["coverage_primary_items"])} · ' + risk + ' {escape(copy["coverage_risk_items"])}</span></span>';
      }}).join('');
    }}
    function evidenceTaskImportHref(reportHref) {{
      if (!reportHref) return '';
      return reportHref.replace(/#.*$/, '') + '#evidence-tasks';
    }}
    function openEvidenceTaskImportHandoff(button) {{
      var href = button ? button.getAttribute('data-import-handoff-href') || '' : '';
      if (href) window.location.href = href;
    }}
    function renderPreflightEvidenceTasks(items, reportHref) {{
      var rows = Array.isArray(items) ? items.slice(0, 6) : [];
      if (!rows.length) return '<span class="candidate-coverage-chip">{escape(copy["preflight_evidence_tasks_empty"])}</span>';
      var importHref = evidenceTaskImportHref(reportHref || '');
      return rows.map(function(item) {{
        var ticker = escapeHtml(item.ticker || 'n/a');
        var priority = escapeHtml(item.priority || 'medium');
        var gap = escapeHtml(item.gap || item.gap_code || 'evidence_gap');
        var prompt = escapeHtml(item.search_prompt || '');
        var label = escapeHtml(item.copy_label || '{escape(copy["copy_evidence_gap_prompt"])}');
        var handoffHref = item.import_handoff_href || importHref;
        var handoff = handoffHref ? '<button type="button" data-import-handoff-href="' + escapeHtml(handoffHref) + '" onclick="openEvidenceTaskImportHandoff(this)">{escape(copy["open_evidence_import_handoff"])}</button>' : '';
        return '<span class="candidate-coverage-chip evidence-gap-task-chip"><b>' + ticker + '</b>' +
          '<span>' + priority + ' · ' + gap + '</span>' +
          '<button type="button" data-copy-text="' + prompt + '" data-copied-text="{escape(copy["copied_prompt"])}" onclick="copyTaskPrompt(this)">' + label + '</button>' + handoff + '</span>';
      }}).join('');
    }}
    function renderAnalysisInputPreview(form) {{
      var input = form ? form.querySelector('input[name="query"]') : null;
      var query = input ? input.value : '';
      var preview = parseAnalysisInputPreview(query);
      var panel = document.getElementById('analysis-input-preview');
      if (!panel) return false;
      applyAnalysisInputPreview(preview);
      var status = document.getElementById('launch-status');
      if (status) {{
        status.hidden = false;
        status.textContent = '{escape(copy["preview_resolving"])}';
      }}
      fetchAnalysisInputPreview(query).then(function(resolvedPreview) {{
        applyAnalysisInputPreview(resolvedPreview);
        if (status) status.textContent = '{escape(copy["preview_ready"])}';
      }}).catch(function() {{
        applyAnalysisInputPreview(preview);
        if (status) status.textContent = '{escape(copy["preview_fallback"])}';
      }});
      return false;
    }}
    function applyAnalysisInputPreview(preview) {{
      var panel = document.getElementById('analysis-input-preview');
      if (!panel) return;
      panel.hidden = false;
      panel.setAttribute('data-preview-intent', preview.intent);
      document.getElementById('preview-intent').textContent = preview.intent;
      document.getElementById('preview-canonical-theme').textContent = preview.canonical;
      document.getElementById('preview-candidate-tickers').textContent = preview.candidates.join(', ');
      document.getElementById('preview-evidence-coverage').textContent = preview.coverage;
      var candidateCoverage = document.querySelector('#preview-candidate-coverage .candidate-coverage-list');
      if (candidateCoverage) candidateCoverage.innerHTML = renderCandidateCoverageSummary(preview.candidateCoverage || []);
      var evidenceGapTasks = document.querySelector('#preview-evidence-gap-tasks .candidate-coverage-list');
      if (evidenceGapTasks) evidenceGapTasks.innerHTML = renderPreflightEvidenceTasks(preview.evidenceGapTasks || []);
      document.getElementById('preview-expected-outputs').textContent = preview.outputs;
      var source = document.getElementById('preview-source');
      if (source) source.textContent = preview.source || '{escape(copy["preview_source_local"])}';
    }}
    function confirmAnalysisLaunch(form) {{
      if (!form) return;
      form.setAttribute('data-confirmed-launch', 'true');
      if (form.requestSubmit) {{
        form.requestSubmit();
      }} else {{
        form.submit();
      }}
    }}
    function runCenterStorageKey() {{
      return 'serenity-alpha-lab:run-center:' + window.location.pathname;
    }}
    var runPollInterval = null;
    var latestRunHref = '';
    function updateRunCenter(state) {{
      var runCenter = document.getElementById('run-center');
      if (!runCenter) return;
      var nextState = state || {{}};
      var query = nextState.query || '';
      var phase = nextState.phase || nextState.status || 'idle';
      if (phase === 'queued') phase = 'queued';
      if (phase === 'completed') phase = 'complete';
      if (phase === 'failed') phase = 'failed';
      var activeIndex = typeof nextState.activeIndex === 'number' ? nextState.activeIndex : -1;
      var queryEl = document.getElementById('run-current-query');
      var statusEl = document.getElementById('run-status');
      var latestButton = document.getElementById('latest-run-report-button');
      var steps = Array.prototype.slice.call(runCenter.querySelectorAll('[data-run-step]'));
      if (phase === 'complete' && activeIndex < 0) {{
        activeIndex = steps.length;
      }}
      if (phase === 'queued' && activeIndex < 0) {{
        activeIndex = 0;
      }}
      if (phase === 'failed' && activeIndex < 0) {{
        activeIndex = 0;
      }}
      if (queryEl) {{
        queryEl.textContent = query || '{escape(copy["run_waiting"])}';
      }}
      if (statusEl) {{
        if (phase === 'queued') {{
          statusEl.textContent = query ? '{escape(copy["run_queued"])} ' + query : '{escape(copy["run_queued_generic"])}';
        }} else if (phase === 'running') {{
          statusEl.textContent = query ? '{escape(copy["run_running"])} ' + query : '{escape(copy["run_running_generic"])}';
        }} else if (phase === 'complete') {{
          statusEl.textContent = query ? '{escape(copy["run_complete"])} ' + query : '{escape(copy["run_complete_generic"])}';
        }} else if (phase === 'failed') {{
          statusEl.textContent = query ? '{escape(copy["run_failed"])} ' + query : '{escape(copy["run_failed_generic"])}';
        }} else {{
          statusEl.textContent = '{escape(copy["run_waiting"])}';
        }}
      }}
      steps.forEach(function(step, index) {{
        var stepState = 'idle';
        if (phase === 'queued') {{
          stepState = index === activeIndex ? 'active' : 'idle';
        }} else if (phase === 'running') {{
          stepState = index < activeIndex ? 'done' : (index === activeIndex ? 'active' : 'idle');
        }} else if (phase === 'complete') {{
          stepState = 'done';
        }} else if (phase === 'failed') {{
          stepState = index === activeIndex ? 'active' : 'idle';
        }}
        step.setAttribute('data-run-state', stepState);
      }});
      latestRunHref = nextState.href || latestRunHref || '';
      if (latestButton) {{
        latestButton.hidden = !(phase === 'complete' && latestRunHref);
      }}
      try {{
        window.localStorage.setItem(runCenterStorageKey(), JSON.stringify({{
          query: query,
          phase: phase,
          activeIndex: activeIndex,
          href: nextState.href || '',
          queued_at: nextState.queued_at || '',
          completed_at: nextState.completed_at || '',
          error: nextState.error || ''
        }}));
      }} catch (error) {{}}
    }}
    function runStatusLabel(status) {{
      if (status === 'completed' || status === 'complete') return '{escape(copy["run_status_completed"])}';
      if (status === 'failed') return '{escape(copy["run_status_failed"])}';
      if (status === 'running') return '{escape(copy["run_status_running"])}';
      if (status === 'queued') return '{escape(copy["run_status_queued"])}';
      if (status === 'cancelled') return '{escape(copy["run_status_cancelled"])}';
      return '{escape(copy["run_status_unknown"])}';
    }}
    function openLatestRunReport() {{
      if (latestRunHref) window.location.href = latestRunHref;
    }}
    function setRunPollingState(state) {{
      var panel = document.querySelector('[data-run-polling]');
      if (panel) panel.setAttribute('data-run-polling', state || 'idle');
    }}
    function stopRunPolling() {{
      if (runPollInterval) {{
        window.clearTimeout(runPollInterval);
        runPollInterval = null;
      }}
      setRunPollingState('idle');
    }}
    function scheduleRunPolling() {{
      if (runPollInterval) return;
      setRunPollingState('active');
      runPollInterval = window.setTimeout(function() {{
        runPollInterval = null;
        syncRunCenterFromServer({{ polling: true }});
      }}, 1500);
    }}
    function startRunPolling() {{
      stopRunPolling();
      setRunPollingState('active');
      scheduleRunPolling();
    }}
    function renderRunHistory(runs) {{
      var list = document.getElementById('run-history-list');
      if (!list) return;
      var records = Array.isArray(runs) ? runs : [];
      if (!records.length) {{
        list.innerHTML = '<p class="run-history-empty">{escape(copy["run_history_empty"])}</p>';
        return;
      }}
      list.innerHTML = records.slice(0, 5).map(function(run, index) {{
        var query = escapeHtml(run.query || '');
        var status = run.status || 'unknown';
        var href = escapeHtml(run.href || '');
        var manifestHref = escapeHtml(run.manifest_href || '');
        var jobId = escapeHtml(run.job_id || '');
        var retryOfJobId = escapeHtml(run.retry_of_job_id || '');
        var language = escapeHtml(run.language || '');
        var completedAt = escapeHtml(run.completed_at || '');
        var error = escapeHtml(run.error || '');
        var openDisabled = href ? '' : ' disabled';
        var manifestDisabled = manifestHref ? '' : ' disabled';
        var qualityScore = run.quality_score === 0 || run.quality_score ? String(run.quality_score) + '/100' : 'n/a';
        var qualityStatus = escapeHtml(run.quality_status || '');
        var qualityLine = '<small><strong>{escape(copy["run_history_quality"])}:</strong> ' + escapeHtml(qualityScore) + (qualityStatus ? ' · ' + qualityStatus : '') + '</small>';
        var candidates = Array.isArray(run.candidate_tickers) ? run.candidate_tickers.join(', ') : (run.candidate_tickers || '');
        var canonicalTheme = run.canonical_theme || '';
        var candidateLine = '<small><strong>{escape(copy["run_history_candidates"])}:</strong> ' + escapeHtml(candidates || 'n/a') + (canonicalTheme ? ' · ' + escapeHtml(canonicalTheme) : '') + '</small>';
        var coverageLine = run.coverage_label ? '<small><strong>{escape(copy["evidence_coverage"])}:</strong> ' + escapeHtml(run.coverage_label) + '</small>' : '';
        var candidateCoverageLine = Array.isArray(run.candidate_coverage) && run.candidate_coverage.length ? '<div class="candidate-coverage-list">' + renderCandidateCoverageSummary(run.candidate_coverage) + '</div>' : '';
        var evidenceGapLine = Array.isArray(run.evidence_gap_tasks) && run.evidence_gap_tasks.length ? '<div class="candidate-coverage"><strong>{escape(copy["preflight_evidence_tasks"])}</strong><div class="candidate-coverage-list">' + renderPreflightEvidenceTasks(run.evidence_gap_tasks, run.href || '') + '</div></div>' : '';
        var errorLine = error ? '<small><strong>{escape(copy["failure_details"])}:</strong> ' + error + '</small>' : '';
        var cancelDisabled = status === 'queued' || status === 'running' ? '' : ' disabled';
        return '<article class="run-history-item" data-run-history-index="' + index + '" data-run-status="' + escapeHtml(status) + '" data-run-query="' + query + '" data-run-href="' + href + '" data-run-manifest-href="' + manifestHref + '" data-run-job-id="' + jobId + '" data-run-retry-of-job-id="' + retryOfJobId + '">' +
          '<div class="run-history-meta"><strong>' + (query || '{escape(copy["unknown_run"])}') + '</strong>' +
          '<span>' + runStatusLabel(status) + (language ? ' · ' + language : '') + (completedAt ? ' · ' + completedAt : '') + '</span>' +
          qualityLine + candidateLine + coverageLine + candidateCoverageLine + evidenceGapLine + errorLine + '</div>' +
          '<div class="run-history-controls">' +
          '<button type="button" onclick="openJobDetailPanel(this)">{escape(copy["job_detail"])}</button>' +
          '<button type="button" onclick="cancelAnalyzeJob(this)"' + cancelDisabled + '>{escape(copy["cancel_job"])}</button>' +
          '<button type="button" onclick="openRunReport(this)"' + openDisabled + '>{escape(copy["open_run_report"])}</button>' +
          '<button type="button" onclick="openRunManifest(this)"' + manifestDisabled + '>{escape(copy["open_run_manifest"])}</button>' +
          '<button type="button" onclick="retryAnalyzeJob(this)">{escape(copy["rerun_run"])}</button>' +
          '</div></article>';
      }}).join('');
    }}
    function openRunReport(button) {{
      var item = button.closest('[data-run-history-index]');
      var href = item ? item.getAttribute('data-run-href') : '';
      if (!href) return;
      window.location.href = href;
    }}
    function openRunManifest(button) {{
      var item = button.closest('[data-run-history-index]');
      var href = item ? item.getAttribute('data-run-manifest-href') : '';
      if (!href) return;
      window.location.href = href;
    }}
    function rerunRunRecord(button) {{
      var item = button.closest('[data-run-history-index]');
      var query = item ? item.getAttribute('data-run-query') : '';
      var input = document.getElementById('analysis-query');
      var form = input ? input.closest('form') : null;
      if (!input || !form || !query) return;
      input.value = query;
      if (form.requestSubmit) {{
        form.requestSubmit();
      }} else {{
        form.submit();
      }}
    }}
    function retryAnalyzeJob(button) {{
      var item = button.closest('[data-run-history-index]');
      var jobId = item ? item.getAttribute('data-run-job-id') : '';
      if (jobId && window.fetch) {{
        fetch('/api/analyze-jobs', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
          body: JSON.stringify({{ retry_job_id: jobId }})
        }})
          .then(function(response) {{
            if (!response.ok) throw new Error('HTTP ' + response.status);
            return response.json();
          }})
          .then(function(payload) {{
            var job = payload && payload.job ? payload.job : {{}};
            updateRunCenter({{
              query: job.query || '',
              phase: job.status || 'queued',
              activeIndex: 0,
              job_id: job.job_id || '',
              retry_job_id: job.retry_of_job_id || jobId,
              queued_at: job.queued_at || ''
            }});
            startRunPolling();
          }})
          .catch(function() {{
            rerunRunRecord(button);
          }});
        return;
      }}
      rerunRunRecord(button);
    }}
    function renderJobDetailPanel(job) {{
      var panel = document.getElementById('job-detail-panel');
      var body = document.getElementById('job-detail-body');
      if (!panel || !body) return;
      var target = job || {{}};
      var detailCandidates = Array.isArray(target.candidate_tickers) ? target.candidate_tickers.join(', ') : (target.candidate_tickers || 'n/a');
      var detailCandidateCoverage = Array.isArray(target.candidate_coverage) && target.candidate_coverage.length ? renderCandidateCoverageSummary(target.candidate_coverage) : renderCandidateCoverageSummary([]);
      var detailEvidenceGapTasks = Array.isArray(target.evidence_gap_tasks) && target.evidence_gap_tasks.length ? renderPreflightEvidenceTasks(target.evidence_gap_tasks, target.href || '') : renderPreflightEvidenceTasks([]);
      panel.hidden = false;
      body.innerHTML = '<article class="run-history-item" data-job-detail-job-id="' + escapeHtml(target.job_id || '') + '">' +
        '<div class="run-history-meta">' +
        '<strong>' + escapeHtml(target.query || '{escape(copy["unknown_run"])}') + '</strong>' +
        '<span>' + runStatusLabel(target.status || 'unknown') + ' · ' + escapeHtml(target.language || '') + '</span>' +
        '<small><strong>{escape(copy["canonical_theme"])}:</strong> ' + escapeHtml(target.canonical_theme || 'n/a') + '</small>' +
        '<small><strong>{escape(copy["candidate_tickers"])}:</strong> ' + escapeHtml(detailCandidates || 'n/a') + '</small>' +
        '<small><strong>{escape(copy["evidence_coverage"])}:</strong> ' + escapeHtml(target.coverage_label || 'n/a') + '</small>' +
        '<div class="candidate-coverage"><strong>{escape(copy["candidate_coverage_detail"])}</strong><div class="candidate-coverage-list">' + detailCandidateCoverage + '</div></div>' +
        '<div class="candidate-coverage"><strong>{escape(copy["preflight_evidence_tasks"])}</strong><div class="candidate-coverage-list">' + detailEvidenceGapTasks + '</div></div>' +
        '<small><strong>job_id:</strong> ' + escapeHtml(target.job_id || 'n/a') + '</small>' +
        '<small><strong>retry_job_id:</strong> ' + escapeHtml(target.retry_of_job_id || 'n/a') + '</small>' +
        '<small><strong>attempt:</strong> ' + escapeHtml(target.attempt || '1') + '</small>' +
        '<small><strong>{escape(copy["failure_details"])}:</strong> ' + escapeHtml(target.error || 'n/a') + '</small>' +
        '</div></article>';
    }}
    function openJobDetailPanel(button) {{
      var item = button.closest('[data-run-history-index]');
      var jobId = item ? item.getAttribute('data-run-job-id') : '';
      if (!jobId || !window.fetch) return;
      fetch('/api/analyze-jobs?jobId=' + encodeURIComponent(jobId), {{ headers: {{ 'Accept': 'application/json' }} }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          renderJobDetailPanel(payload && payload.job ? payload.job : {{}});
        }})
        .catch(function() {{}});
    }}
    function cancelAnalyzeJob(button) {{
      var item = button.closest('[data-run-history-index]');
      var jobId = item ? item.getAttribute('data-run-job-id') : '';
      if (!jobId || !window.fetch) return;
      fetch('/api/analyze-jobs', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
        body: JSON.stringify({{ job_id: jobId, cancel: true }})
      }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var job = payload && payload.job ? payload.job : {{}};
          renderJobDetailPanel(job);
          updateRunCenter({{
            query: job.query || '',
            phase: job.status || 'cancelled',
            activeIndex: 0,
            job_id: job.job_id || jobId,
            completed_at: job.completed_at || '',
            error: job.error || ''
          }});
          syncRunCenterFromServer();
        }})
        .catch(function() {{}});
    }}
    function syncRunCenterFromServer(options) {{
      if (!window.fetch) return;
      fetch('/api/runs', {{ headers: {{ 'Accept': 'application/json' }} }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var runs = payload && Array.isArray(payload.runs) ? payload.runs : [];
          renderRunHistory(runs);
          if (!runs.length) return;
          var run = runs[0] || {{}};
          if (run.href) latestRunHref = run.href;
          updateRunCenter({{
            query: run.query || '',
            phase: run.status === 'completed' ? 'complete' : run.status,
            activeIndex: run.status === 'failed' ? 0 : -1,
            href: run.href || '',
            queued_at: run.queued_at || '',
            completed_at: run.completed_at || '',
            error: run.error || ''
          }});
          var status = run.status || '';
          var statusEl = document.getElementById('run-status');
          if (status === 'queued' || status === 'running') {{
            if (statusEl && options && options.polling) statusEl.textContent = '{escape(copy["run_polling"])}';
            scheduleRunPolling();
          }} else if (status === 'completed') {{
            stopRunPolling();
            if (statusEl && options && options.polling) statusEl.textContent = '{escape(copy["run_report_ready"])}';
          }} else if (status === 'failed') {{
            stopRunPolling();
          }}
        }})
        .catch(function() {{
          renderRunHistory([]);
        }});
    }}
    function submitAnalyzeJob(form) {{
      if (!window.fetch) return false;
      var input = form ? form.querySelector('input[name="query"]') : null;
      var languageInput = form ? form.querySelector('input[name="language"]') : null;
      var query = input ? input.value.trim() : '';
      var language = languageInput ? languageInput.value : document.documentElement.lang || 'en';
      if (!query) return false;
      fetch('/api/analyze-jobs', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
        body: JSON.stringify({{ query: query, language: language }})
      }})
        .then(function(response) {{
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        }})
        .then(function(payload) {{
          var job = payload && payload.job ? payload.job : {{}};
          updateRunCenter({{
            query: job.query || query,
            phase: job.status || 'queued',
            activeIndex: 0,
            job_id: job.job_id || '',
            queued_at: job.queued_at || ''
          }});
          startRunPolling();
        }})
        .catch(function() {{
          if (form) form.submit();
        }});
      return true;
    }}
    function initializeRunCenter() {{
      var runCenter = document.getElementById('run-center');
      if (!runCenter) return;
      var saved = null;
      try {{
        saved = JSON.parse(window.localStorage.getItem(runCenterStorageKey()) || 'null');
      }} catch (error) {{}}
      if (saved && saved.query) {{
        updateRunCenter(saved);
      }} else {{
        updateRunCenter({{ phase: 'idle' }});
      }}
      renderRunHistory([]);
      syncRunCenterFromServer();
    }}
    function retryLastRun() {{
      var saved = null;
      try {{
        saved = JSON.parse(window.localStorage.getItem(runCenterStorageKey()) || 'null');
      }} catch (error) {{}}
      var query = saved && saved.query ? saved.query : '';
      var input = document.getElementById('analysis-query');
      var form = input ? input.closest('form') : null;
      if (!input || !form || !query) return;
      input.value = query;
      if (form.requestSubmit) {{
        form.requestSubmit();
      }} else {{
        form.submit();
      }}
    }}
    function copyTaskPrompt(button) {{
      var text = button.getAttribute('data-copy-text') || '';
      if (!text) return;
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(text).catch(function() {{}});
      }}
      button.textContent = button.getAttribute('data-copied-text') || button.textContent;
    }}
    function copyShareLink(button) {{
      var href = button.getAttribute('data-share-href') || '';
      if (!href) return;
      var link = '';
      try {{
        link = new URL(href, window.location.href).href;
      }} catch (error) {{
        link = href;
      }}
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(link).catch(function() {{}});
      }}
      button.textContent = button.getAttribute('data-copied-text') || button.textContent;
    }}
    var currentReaderHref = '';
    function absoluteReportHref(href) {{
      if (!href) return '';
      try {{
        return new URL(href, window.location.href).href;
      }} catch (error) {{
        return href;
      }}
    }}
    function updateReaderToolbar(href) {{
      currentReaderHref = href || '';
      var toolbar = document.getElementById('memo-drawer-toolbar');
      var link = document.getElementById('memo-drawer-current-link');
      if (!toolbar || !link) return;
      if (!currentReaderHref) {{
        toolbar.hidden = true;
        link.textContent = '{escape(copy["not_generated"])}';
        return;
      }}
      toolbar.hidden = false;
      link.textContent = absoluteReportHref(currentReaderHref);
    }}
    function resetReaderNavigation() {{
      renderReaderOutline([]);
      renderReaderHighlights([]);
    }}
    function copyCurrentReaderLink(button) {{
      var link = absoluteReportHref(currentReaderHref);
      if (!link) return;
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(link).catch(function() {{}});
      }}
      button.textContent = button.getAttribute('data-copied-text') || button.textContent;
    }}
    function openCurrentReaderReport() {{
      var link = absoluteReportHref(currentReaderHref);
      if (link) window.location.href = link;
    }}
    function copyHandoffBundle(button) {{
      var packageEl = button.closest('#delivery-package') || document;
      var cards = Array.prototype.slice.call(packageEl.querySelectorAll('[data-handoff-artifact-href]'));
      if (!cards.length) return;
      var lines = ['{escape(copy["delivery_package"])}'];
      cards.forEach(function(card) {{
        var title = card.getAttribute('data-handoff-artifact-title') || '';
        var href = card.getAttribute('data-handoff-artifact-href') || '';
        if (title && href) lines.push('- ' + title + ': ' + absoluteReportHref(href));
      }});
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(lines.join('\\n')).catch(function() {{}});
      }}
      button.textContent = button.getAttribute('data-copied-text') || button.textContent;
    }}
    function taskStorageKey(taskId) {{
      return 'serenity-alpha-lab:task-status:' + window.location.pathname + ':' + taskId;
    }}
    function verifiedTaskRerunContext(card) {{
      var quality = collectWorkspaceQualitySnapshot();
      var context = {{
        taskId: card ? card.getAttribute('data-task-id') || '' : '',
        ticker: card ? card.getAttribute('data-ticker') || '' : '',
        query: '{escape(copy["query"])}',
        href: window.location.pathname,
        qualityBefore: card ? card.getAttribute('data-quality-before-rerun') || quality.score || 'n/a' : quality.score || 'n/a',
        qualityAfter: quality.score || 'n/a',
        qualityStatus: quality.status || 'n/a',
        at: new Date().toISOString()
      }};
      return encodeURIComponent(JSON.stringify(context));
    }}
    function qualityDeltaAfterRerun(beforeScore, afterScore) {{
      function parseScore(value) {{
        var match = String(value || '').match(/-?\\d+/);
        return match ? parseInt(match[0], 10) : null;
      }}
      var before = parseScore(beforeScore);
      var after = parseScore(afterScore);
      if (before === null || after === null) return 'n/a';
      var delta = after - before;
      return (delta >= 0 ? '+' : '') + String(delta);
    }}
    function updateVerifiedTaskRerunLoop(card) {{
      if (!card) return;
      var loop = card.querySelector('[data-verified-task-rerun]');
      if (!loop) return;
      var context = verifiedTaskRerunContext(card);
      var quality = collectWorkspaceQualitySnapshot();
      var before = card.getAttribute('data-quality-before-rerun') || quality.score || 'n/a';
      var delta = qualityDeltaAfterRerun(before, quality.score || 'n/a');
      loop.setAttribute('data-verified-task-rerun-context', context);
      loop.setAttribute('data-quality-delta-after-rerun', delta);
      var status = loop.querySelector('[data-verified-task-rerun-status]');
      if (status) {{
        status.textContent = card.getAttribute('data-task-status') === 'verified'
          ? '{escape(copy["quality_delta_after_rerun"])}: ' + delta
          : '{escape(copy["auto_rerun_after_verification"])}';
      }}
      var button = loop.querySelector('[data-verified-task-rerun-button]');
      if (button) button.disabled = card.getAttribute('data-task-status') !== 'verified';
      if (card.getAttribute('data-task-status') === 'verified' && card.getAttribute('data-project-evidence-audit-captured') !== 'true') {{
        card.setAttribute('data-project-evidence-audit-captured', 'true');
        appendProjectEvidenceAuditEntry({{
          projectId: window.location.pathname,
          projectQuery: '{escape(copy["query"])}',
          taskId: card.getAttribute('data-task-id') || '',
          ticker: card.getAttribute('data-ticker') || '',
          type: 'verified-task',
          label: '{escape(copy["verified_task_audit_trail"])}',
          qualityBefore: before,
          qualityAfter: quality.score || 'n/a',
          qualityDelta: delta
        }});
      }}
    }}
    function handleVerifiedTaskRerun(button) {{
      var card = button ? button.closest('[data-task-id]') : null;
      if (!card) return false;
      var context = verifiedTaskRerunContext(card);
      var quality = collectWorkspaceQualitySnapshot();
      var before = card.getAttribute('data-quality-before-rerun') || quality.score || 'n/a';
      var delta = qualityDeltaAfterRerun(before, quality.score || 'n/a');
      appendProjectEvidenceAuditEntry({{
        projectId: window.location.pathname,
        projectQuery: '{escape(copy["query"])}',
        taskId: card.getAttribute('data-task-id') || '',
        ticker: card.getAttribute('data-ticker') || '',
        type: 'verified-task-rerun',
        label: '{escape(copy["quality_contribution"])}',
        qualityBefore: before,
        qualityAfter: quality.score || 'n/a',
        qualityDelta: delta
      }});
      try {{
        window.localStorage.setItem('serenity-alpha-lab:verified-task-rerun-context', decodeURIComponent(context));
      }} catch (error) {{}}
      var query = '{escape(copy["query"])}' || document.title || '';
      var params = new URLSearchParams();
      params.set('query', query);
      params.set('language', '{escape(copy["language"])}');
      params.set('verifiedTaskId', card.getAttribute('data-task-id') || '');
      params.set('verifiedTicker', card.getAttribute('data-ticker') || '');
      params.set('qualityBefore', card.getAttribute('data-quality-before-rerun') || collectWorkspaceQualitySnapshot().score || 'n/a');
      window.location.href = '/analyze?' + params.toString();
      return false;
    }}
    function updateTaskStatus(select) {{
      var card = select.closest('[data-task-id]');
      if (!card) return;
      var taskId = card.getAttribute('data-task-id');
      var value = select.value || 'to_collect';
      card.setAttribute('data-task-status', value);
      try {{
        window.localStorage.setItem(taskStorageKey(taskId), value);
      }} catch (error) {{}}
      updateVerifiedTaskRerunLoop(card);
      writeTaskStatusToServer(taskStatusRecord(card, value));
    }}
    function initializeTaskStatuses() {{
      var selects = Array.prototype.slice.call(document.querySelectorAll('[data-task-status-select]'));
      selects.forEach(function(select) {{
        var card = select.closest('[data-task-id]');
        if (!card) return;
        var taskId = card.getAttribute('data-task-id');
        var saved = '';
        try {{
          saved = window.localStorage.getItem(taskStorageKey(taskId)) || '';
        }} catch (error) {{}}
        select.value = saved || card.getAttribute('data-task-status') || select.value || 'to_collect';
        updateTaskStatus(select);
      }});
      syncTaskStatusesFromServer();
    }}
    function openMemoDrawer(button) {{
      var href = button.getAttribute('data-memo-href');
      var title = button.getAttribute('data-memo-title') || '{escape(copy["report_reader"])}';
      var drawer = document.getElementById('memo-drawer');
      var backdrop = document.getElementById('drawer-backdrop');
      var heading = document.getElementById('memo-drawer-title');
      var body = document.getElementById('memo-drawer-body');
      if (!href || !drawer || !body) return;
      drawer.hidden = false;
      drawer.setAttribute('aria-hidden', 'false');
      if (backdrop) backdrop.hidden = false;
      if (heading) heading.textContent = title;
      updateReaderToolbar(href);
      resetReaderNavigation();
      body.classList.remove('is-rendered');
      body.innerHTML = '<p class="drawer-empty">{escape(copy["loading_report"])}</p>';
      if (/\\.html?(#.*)?$/i.test(href)) {{
        body.classList.add('is-rendered');
        body.innerHTML = '<iframe class="report-frame" title="' + escapeHtml(title) + '" src="' + escapeHtml(href) + '"></iframe>';
        return;
      }}
      fetch(href).then(function(response) {{
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.text();
      }}).then(function(text) {{
        body.classList.add('is-rendered');
        body.innerHTML = renderMemoMarkdown(text);
      }}).catch(function() {{
        body.classList.remove('is-rendered');
        body.innerHTML = '<p class="drawer-empty">{escape(copy["report_load_failed"])}</p>';
      }});
    }}
    function closeMemoDrawer() {{
      var drawer = document.getElementById('memo-drawer');
      var backdrop = document.getElementById('drawer-backdrop');
      if (drawer) {{
        drawer.hidden = true;
        drawer.setAttribute('aria-hidden', 'true');
      }}
      if (backdrop) backdrop.hidden = true;
      updateReaderToolbar('');
      resetReaderNavigation();
    }}
    function renderMemoMarkdown(markdown) {{
      var lines = String(markdown || '').split(/\\r?\\n/);
      var html = [];
      var sections = [];
      var inList = false;
      function closeList() {{
        if (inList) {{
          html.push('</ul>');
          inList = false;
        }}
      }}
      lines.forEach(function(line) {{
        if (!line.trim()) {{
          closeList();
          return;
        }}
        if (line.startsWith('# ')) {{
          closeList();
          var title = line.slice(2).trim();
          var id = readerSectionId(title, sections.length);
          sections.push({{ id: id, title: title }});
          html.push('<h1 id="' + escapeHtml(id) + '" data-reader-section-id="' + escapeHtml(id) + '">' + formatInlineMarkdown(title) + '</h1>');
          return;
        }}
        if (line.startsWith('## ')) {{
          closeList();
          var sectionTitle = line.slice(3).trim();
          var sectionId = readerSectionId(sectionTitle, sections.length);
          sections.push({{ id: sectionId, title: sectionTitle }});
          html.push('<h2 id="' + escapeHtml(sectionId) + '" data-reader-section-id="' + escapeHtml(sectionId) + '">' + formatInlineMarkdown(line.slice(3)) + '</h2>');
          return;
        }}
        if (line.startsWith('- ')) {{
          if (!inList) {{
            html.push('<ul>');
            inList = true;
          }}
          html.push('<li>' + formatInlineMarkdown(line.slice(2)) + '</li>');
          return;
        }}
        closeList();
        html.push('<p>' + formatInlineMarkdown(line) + '</p>');
      }});
      closeList();
      renderReaderOutline(sections);
      renderReaderHighlights(extractReaderHighlights(lines));
      return '<div class="markdown-body">' + html.join('') + '</div>';
    }}
    function readerSectionId(title, index) {{
      var normalized = String(title || 'section').toLowerCase().replace(/[^a-z0-9\\u4e00-\\u9fa5]+/g, '-').replace(/^-+|-+$/g, '');
      return 'reader-section-' + (normalized || index || 'section');
    }}
    function renderReaderOutline(sections) {{
      var outline = document.getElementById('memo-drawer-outline');
      var list = document.getElementById('memo-drawer-outline-list');
      if (!outline || !list) return;
      if (!sections || !sections.length) {{
        outline.hidden = true;
        list.innerHTML = '';
        return;
      }}
      outline.hidden = false;
      list.innerHTML = sections.slice(0, 10).map(function(section) {{
        return '<li data-reader-outline><button type="button" data-reader-section-id="' + escapeHtml(section.id) + '" onclick="scrollReaderSection(this.getAttribute(\\'data-reader-section-id\\'))">{escape(copy["jump_to_section"])}: ' + escapeHtml(section.title) + '</button></li>';
      }}).join('');
    }}
    function renderReaderHighlights(highlights) {{
      var panel = document.getElementById('memo-drawer-highlights');
      var list = document.getElementById('memo-drawer-highlight-list');
      if (!panel || !list) return;
      if (!highlights || !highlights.length) {{
        panel.hidden = true;
        list.innerHTML = '';
        return;
      }}
      panel.hidden = false;
      list.innerHTML = highlights.slice(0, 4).map(function(item) {{
        return '<li>' + formatInlineMarkdown(item) + '</li>';
      }}).join('');
    }}
    function extractReaderHighlights(lines) {{
      return String(lines ? lines.join('\\n') : '').split(/\\r?\\n/)
        .map(function(line) {{ return line.trim(); }})
        .filter(function(line) {{
          return line.startsWith('- ') || line.indexOf('**') >= 0;
        }})
        .map(function(line) {{ return line.replace(/^-\\s+/, ''); }})
        .filter(Boolean)
        .slice(0, 4);
    }}
    function scrollReaderSection(sectionId) {{
      if (!sectionId) return;
      var target = document.getElementById(sectionId);
      if (target && target.scrollIntoView) target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
    }}
    function formatInlineMarkdown(value) {{
      return escapeHtml(value).replace(/\\*\\*([^*]+):\\*\\*/g, '<strong>$1:</strong>').replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
    }}
    function escapeHtml(value) {{
      return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }}
    function handleLaunchSubmit(form) {{
      var button = form.querySelector('button[type="submit"]');
      var status = document.getElementById('launch-status');
      var input = form.querySelector('input[name="query"]');
      var loadingText = button ? button.getAttribute('data-loading-text') : '{escape(copy["launch_loading"])}';
      var query = input ? input.value.trim() : '';
      if (form.getAttribute('data-confirmed-launch') !== 'true') {{
        return renderAnalysisInputPreview(form);
      }}
      form.removeAttribute('data-confirmed-launch');
      updateRunCenter({{ query: query, phase: 'queued', activeIndex: 0 }});
      startRunPolling();
      if (button) {{
        button.disabled = true;
        button.textContent = loadingText;
      }}
      if (status) {{
        status.hidden = false;
        status.textContent = query ? loadingText + ' ' + query : loadingText;
      }}
      if (submitAnalyzeJob(form)) {{
        return false;
      }}
      return true;
    }}
    function handleEvidenceImportSubmit(form) {{
      var button = form.querySelector('button[type="submit"]');
      var status = form.querySelector('[data-import-status]');
      var loadingText = button ? button.getAttribute('data-loading-text') : '{escape(copy["import_loading"])}';
      if (button) {{
        button.disabled = true;
        button.textContent = loadingText;
      }}
      if (status) {{
        status.hidden = false;
        status.textContent = loadingText;
      }}
      return true;
    }}
    document.addEventListener('DOMContentLoaded', function() {{
      initializeRunCenter();
      initializeTaskStatuses();
      initializeDecisionRanking();
      initializeSavedWorkspace();
      initializeResearchProjectLibrary();
      applyProjectRerunContext();
      filterDashboard();
      filterReportWorkbench();
    }});
    document.addEventListener('keydown', function(event) {{
      if (event.key === 'Escape') closeMemoDrawer();
    }});
  </script>
</body>
</html>
"""


def _render_readiness_table(rows: Sequence[Mapping[str, str]], copy: Mapping[str, str]) -> str:
    if not rows:
        return f'<div class="note">{escape(copy["no_readiness"])}</div>'
    body = []
    for row in rows:
        body.append(
            f"<tr data-dashboard-item data-ticker=\"{escape(row.get('ticker', ''))}\" data-status=\"{escape(row.get('status', ''))}\" data-search=\"{escape(_search_blob(row))}\">"
            f"<td><strong>{escape(row.get('ticker', ''))}</strong></td>"
            f"<td>{_status_pill(row.get('status', ''))}</td>"
            f"<td class=\"num\">{escape(row.get('evidence', '0'))}</td>"
            f"<td class=\"num\">{escape(row.get('primary', '0'))}</td>"
            f"<td class=\"num\">{escape(row.get('risk', '0'))}</td>"
            f"<td>{escape(row.get('flags', 'none'))}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table>'
        f"<thead><tr><th>{escape(copy['ticker'])}</th><th>{escape(copy['status'])}</th><th class=\"num\">{escape(copy['evidence_count'])}</th>"
        f"<th class=\"num\">{escape(copy['primary_fact'])}</th><th class=\"num\">{escape(copy['risk'])}</th><th>{escape(copy['flags'])}</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def _render_analysis_briefing(
    *,
    memo_rows: Sequence[Mapping[str, str]],
    memo_previews: Sequence[Mapping[str, object]],
    operational_reports: Sequence[Mapping[str, object]],
    copy: Mapping[str, str],
) -> str:
    if not memo_rows:
        return (
            f'<section id="analysis-briefing" class="analysis-briefing" data-briefing-top-ticker="">'
            f'<div><div class="eyebrow">{escape(copy["analysis_briefing_eyebrow"])}</div>'
            f'<h2>{escape(copy["analysis_briefing"])}</h2>'
            f'<p>{escape(copy["analysis_briefing_empty"])}</p></div></section>'
        )

    preview_by_ticker = {
        str(preview.get("ticker", "")).upper(): preview
        for preview in memo_previews
        if str(preview.get("ticker", "")).strip()
    }
    top_row = _select_top_candidate(memo_rows, preview_by_ticker)
    ticker = str(top_row.get("ticker") or "")
    top_preview = preview_by_ticker.get(ticker.upper(), {})
    score = str(top_preview.get("score") or top_row.get("score") or "n/a")
    rating = str(top_preview.get("rating") or top_row.get("rating") or copy["not_generated"])
    confidence = str(top_preview.get("confidence") or top_row.get("confidence") or copy["not_generated"])
    gaps = str(top_preview.get("gaps") or top_row.get("gaps") or "none")
    coverage_state = _briefing_coverage_state(top_row, copy)
    primary_gap = _briefing_primary_gap(top_row, gaps, copy)
    memo_href = str(top_row.get("memo_href") or top_row.get("memo_file") or "")
    task_count = _briefing_task_count(operational_reports)
    actions = [
        copy["briefing_action_compare"],
        copy["briefing_action_evidence"] if task_count else copy["briefing_action_monitor"],
        copy["briefing_action_verify"],
    ]
    action_items = "".join(f"<li>{escape(action)}</li>" for action in actions)
    top_report_title = f"{ticker} {copy['report_reader']}".strip()
    top_report_button = (
        f'<button type="button" class="memo-link" data-memo-href="{escape(memo_href)}" '
        f'data-memo-title="{escape(top_report_title)}" onclick="openMemoDrawer(this)">{escape(copy["open_top_report"])}</button>'
        if memo_href and memo_href != "not generated"
        else f'<span class="memo-link" aria-disabled="true">{escape(copy["not_generated"])}</span>'
    )
    return (
        f'<section id="analysis-briefing" class="analysis-briefing" data-briefing-top-ticker="{escape(ticker)}">'
        "<div>"
        f'<div class="eyebrow">{escape(copy["analysis_briefing_eyebrow"])}</div>'
        f'<h2>{escape(copy["analysis_briefing"])}</h2>'
        f'<p>{escape(copy["analysis_briefing_description"])}</p>'
        '<div class="briefing-grid">'
        f'<div class="briefing-card"><span>{escape(copy["top_candidate"])}</span><strong>{escape(ticker or "n/a")}</strong><small>{escape(score)} · {escape(rating)} · {escape(confidence)}</small></div>'
        f'<div class="briefing-card"><span>{escape(copy["coverage_state"])}</span><strong>{escape(coverage_state)}</strong><small>{escape(top_row.get("evidence", "0"))} {escape(copy["coverage_evidence_items"])}, {escape(top_row.get("primary", "0"))} {escape(copy["coverage_primary_items"])}, {escape(top_row.get("risk", "0"))} {escape(copy["coverage_risk_items"])}</small></div>'
        f'<div class="briefing-card"><span>{escape(copy["primary_gap"])}</span><strong>{escape(primary_gap)}</strong><small>{escape(copy["key_gaps"])}: {escape(gaps)}</small></div>'
        "</div>"
        "</div>"
        '<div class="briefing-actions">'
        f'<h3>{escape(copy["next_actions"])}</h3>'
        f"<ul>{action_items}</ul>"
        '<div class="briefing-action-links">'
        f"{top_report_button}"
        f'<a class="memo-link" href="#evidence-tasks">{escape(copy["review_evidence_tasks"])}</a>'
        "</div>"
        "</div>"
        "</section>"
    )


def _render_research_action_workbench(
    *,
    memo_rows: Sequence[Mapping[str, str]],
    memo_previews: Sequence[Mapping[str, object]],
    operational_reports: Sequence[Mapping[str, object]],
    copy: Mapping[str, str],
) -> str:
    if not memo_rows:
        return (
            '<section id="research-action-workbench" class="research-action-workbench" '
            'data-research-action-gap="" data-research-action-ticker="">'
            '<div class="research-action-summary">'
            f'<div class="eyebrow">{escape(copy["research_action_eyebrow"])}</div>'
            f'<h2>{escape(copy["research_action_workbench"])}</h2>'
            f'<p>{escape(copy["research_action_empty"])}</p>'
            '</div></section>'
        )

    preview_by_ticker = {
        str(preview.get("ticker", "")).upper(): preview
        for preview in memo_previews
        if str(preview.get("ticker", "")).strip()
    }
    top_row = _select_top_candidate(memo_rows, preview_by_ticker)
    ticker = str(top_row.get("ticker") or "n/a").upper()
    top_preview = preview_by_ticker.get(ticker, {})
    gaps = str(top_preview.get("gaps") or top_row.get("gaps") or "none")
    memo_href = str(top_row.get("memo_href") or top_row.get("memo_file") or "")
    queue_href = next(
        (
            str(row.get("href") or "")
            for row in operational_reports
            if row.get("title_key") == "acquisition_queue_title"
        ),
        "reports/evidence-acquisition-queue.md",
    )
    normalized_gap_terms = re.sub(r"[^A-Za-z0-9_\u4e00-\u9fa5]+", " ", gaps).strip()
    prompt = " ".join(part for part in [ticker, normalized_gap_terms, "evidence"] if part).strip()
    if not normalized_gap_terms or normalized_gap_terms.lower() == "none":
        prompt = f"{ticker} evidence validation"
    top_report_title = f"{ticker} {copy['report_reader']}".strip()
    top_report_action = (
        f'<button type="button" class="memo-link" data-memo-href="{escape(memo_href)}" '
        f'data-memo-title="{escape(top_report_title)}" onclick="openMemoDrawer(this)">{escape(copy["open_top_report"])}</button>'
        if memo_href and memo_href != "not generated"
        else f'<span class="memo-link" aria-disabled="true">{escape(copy["not_generated"])}</span>'
    )
    queue_action = (
        f'<button type="button" class="memo-link" data-memo-href="{escape(queue_href)}" '
        f'data-memo-title="{escape(copy["acquisition_queue_title"])}" onclick="openMemoDrawer(this)">{escape(copy["open_acquisition_queue_action"])}</button>'
        if queue_href
        else f'<span class="memo-link" aria-disabled="true">{escape(copy["not_generated"])}</span>'
    )
    return (
        '<section id="research-action-workbench" class="research-action-workbench" '
        f'data-research-action-gap="{escape(gaps)}" data-research-action-ticker="{escape(ticker)}">'
        '<div class="research-action-summary">'
        f'<div class="eyebrow">{escape(copy["research_action_eyebrow"])}</div>'
        f'<h2>{escape(copy["research_action_workbench"])}</h2>'
        f'<p>{escape(copy["research_action_description"])}</p>'
        '<div class="research-action-controls">'
        f'<a class="memo-link" href="#evidence-tasks">{escape(copy["open_evidence_tasks"])}</a>'
        f'<button type="button" class="memo-link" data-memo-href="reports/deliverable-research-report.md" '
        f'data-memo-title="{escape(copy["deliverable_research_report"])}" onclick="openMemoDrawer(this)">{escape(copy["open_deliverable_report"])}</button>'
        f'{queue_action}'
        f'<button type="button" class="memo-link" data-copy-text="{escape(prompt)}" '
        f'data-copied-text="{escape(copy["copied_prompt"])}" onclick="copyTaskPrompt(this)">{escape(copy["copy_next_research_prompt"])}</button>'
        '</div>'
        '</div>'
        f'<div class="research-action-list" aria-label="{escape(copy["action_queue"])}">'
        f'<article class="research-action-card"><span>{escape(copy["action_queue"])}</span><strong>{escape(copy["research_action_sequence"])}</strong><small>{escape(copy["research_action_sequence_description"])}</small></article>'
        f'<article class="research-action-card"><span>{escape(copy["quality_gap_to_close"])}</span><strong>{escape(gaps)}</strong><small>{escape(copy["quality_candidate_prefix"])} {escape(ticker)}</small></article>'
        f'<article class="research-action-card"><span>{escape(copy["copy_next_research_prompt"])}</span><strong>{escape(prompt)}</strong><small>{escape(copy["research_prompt_description"])}</small></article>'
        f'<article class="research-action-card"><span>{escape(copy["open_top_report"])}</span><strong>{escape(ticker)}</strong><div class="research-action-controls">{top_report_action}</div></article>'
        '</div>'
        '</section>'
    )


def _render_decision_workbench(
    *,
    memo_rows: Sequence[Mapping[str, str]],
    memo_previews: Sequence[Mapping[str, object]],
    metrics_by_ticker: Mapping[str, Mapping[str, str]],
    copy: Mapping[str, str],
) -> str:
    if not memo_rows:
        return (
            f'<section id="decision-workbench" class="decision-workbench" data-decision-top-ticker="">'
            f'<div class="decision-summary"><div class="eyebrow">{escape(copy["decision_workbench_eyebrow"])}</div>'
            f'<h2>{escape(copy["decision_workbench"])}</h2>'
            f'<p>{escape(copy["decision_workbench_empty"])}</p></div></section>'
        )

    preview_by_ticker = {
        str(preview.get("ticker", "")).upper(): preview
        for preview in memo_previews
        if str(preview.get("ticker", "")).strip()
    }
    top_row = _select_top_candidate(memo_rows, preview_by_ticker)
    ticker = str(top_row.get("ticker") or "")
    top_preview = preview_by_ticker.get(ticker.upper(), {})
    score = str(top_preview.get("score") or top_row.get("score") or "n/a")
    rating = str(top_preview.get("rating") or top_row.get("rating") or copy["not_generated"])
    confidence = str(top_preview.get("confidence") or top_row.get("confidence") or copy["not_generated"])
    gaps = str(top_preview.get("gaps") or top_row.get("gaps") or "none")
    metrics = metrics_by_ticker.get(ticker.upper(), {})
    drivers = _decision_key_drivers(top_row, metrics, copy)
    counter_risks = _decision_counter_risks(top_preview, top_row, gaps, copy)
    runner_up_text = _decision_runner_up_text(memo_rows, preview_by_ticker, ticker, copy)
    rationale = copy["decision_rationale_body"].format(
        ticker=ticker or "n/a",
        score=score,
        rating=rating,
        confidence=confidence,
        evidence=str(top_row.get("evidence", "0")),
        primary=str(top_row.get("primary", "0")),
        risk=str(top_row.get("risk", "0")),
    )
    driver_items = "".join(f"<li>{escape(item)}</li>" for item in drivers)
    risk_items = "".join(f"<li>{escape(item)}</li>" for item in counter_risks)
    rank_cards = _render_decision_rank_cards(memo_rows, preview_by_ticker, copy)

    return (
        f'<section id="decision-workbench" class="decision-workbench" data-decision-top-ticker="{escape(ticker)}">'
        '<div class="decision-summary">'
        f'<div class="eyebrow">{escape(copy["decision_workbench_eyebrow"])}</div>'
        f'<h2>{escape(copy["decision_workbench"])}</h2>'
        f'<p>{escape(copy["decision_workbench_description"])}</p>'
        f'<span class="decision-disclaimer">{escape(copy["research_triage_only"])}</span>'
        '<div class="decision-controls">'
        f'<label id="decision-sort-label" for="decision-sort">{escape(copy["sort_candidates_by"])}</label>'
        '<select id="decision-sort" onchange="updateDecisionRanking()" aria-describedby="decision-sort-explanation">'
        f'<option value="score">{escape(copy["sort_serenity_score"])}</option>'
        f'<option value="evidence">{escape(copy["sort_evidence_coverage"])}</option>'
        f'<option value="primary">{escape(copy["sort_primary_coverage"])}</option>'
        f'<option value="risk">{escape(copy["sort_risk_coverage"])}</option>'
        '</select>'
        f'<p id="decision-sort-explanation">{escape(copy["sort_explanation"])}</p>'
        '</div>'
        f'<h3>{escape(copy["interactive_candidate_ranking"])}</h3>'
        f'<div id="decision-rank-list" class="decision-rank-list">{rank_cards}</div>'
        "</div>"
        '<div class="decision-grid">'
        f'<article class="decision-card"><h3>{escape(copy["ranking_rationale"])}</h3><p>{escape(rationale)}</p></article>'
        f'<article class="decision-card"><h3>{escape(copy["key_drivers"])}</h3><ul>{driver_items}</ul></article>'
        f'<article class="decision-card"><h3>{escape(copy["counter_thesis_risks"])}</h3><ul>{risk_items}</ul></article>'
        f'<article class="decision-card"><h3>{escape(copy["why_not_other_candidates"])}</h3><p>{escape(runner_up_text)}</p></article>'
        "</div>"
        "</section>"
    )


def _render_decision_rank_cards(
    memo_rows: Sequence[Mapping[str, str]],
    preview_by_ticker: Mapping[str, Mapping[str, object]],
    copy: Mapping[str, str],
) -> str:
    cards = []
    ranked_rows = sorted(memo_rows, key=lambda row: _candidate_rank_tuple(row, preview_by_ticker), reverse=True)
    for index, row in enumerate(ranked_rows, start=1):
        ticker = str(row.get("ticker") or "n/a").upper()
        preview = preview_by_ticker.get(ticker, {})
        score_text = str(preview.get("score") or row.get("score") or "0")
        score_match = re.search(r"\d+", score_text)
        score_value = int(score_match.group(0)) if score_match else 0
        evidence_value = _to_int(row.get("evidence", "0"))
        primary_value = _to_int(row.get("primary", "0"))
        risk_value = _to_int(row.get("risk", "0"))
        rating = str(preview.get("rating") or row.get("rating") or copy["not_generated"])
        confidence = str(preview.get("confidence") or row.get("confidence") or copy["not_generated"])
        cards.append(
            '<article class="decision-rank-card" data-decision-candidate '
            f'data-decision-ticker="{escape(ticker)}" data-decision-score="{score_value}" '
            f'data-decision-evidence="{evidence_value}" data-decision-primary="{primary_value}" data-decision-risk="{risk_value}">'
            f'<span class="rank" data-decision-rank>{index}</span>'
            f'<div><strong>{escape(ticker)}</strong><small>{escape(rating)} · {escape(confidence)} · {evidence_value} {escape(copy["coverage_evidence_items"])}, {primary_value} {escape(copy["coverage_primary_items"])}, {risk_value} {escape(copy["coverage_risk_items"])}</small></div>'
            f'<span class="rank-score">{escape(score_text)}</span>'
            '</article>'
        )
    return "".join(cards)


def _render_report_quality_gate(
    *,
    memo_rows: Sequence[Mapping[str, str]],
    memo_previews: Sequence[Mapping[str, object]],
    copy: Mapping[str, str],
    snapshot: Mapping[str, object] | None = None,
) -> str:
    snapshot = snapshot or _report_quality_snapshot(memo_rows, memo_previews)
    if not snapshot:
        return (
            f'<section id="report-quality-gate" class="report-quality-gate" data-quality-status="not-publishable">'
            f'<div class="quality-summary"><div class="eyebrow">{escape(copy["report_quality_eyebrow"])}</div>'
            f'<h2>{escape(copy["report_quality_gate"])}</h2>'
            f'<p>{escape(copy["report_quality_empty"])}</p></div></section>'
        )

    top_row = snapshot.get("row", {})
    top_ticker = str(snapshot.get("ticker") or "").upper()
    evidence_value = int(snapshot.get("evidence") or 0)
    primary_value = int(snapshot.get("primary") or 0)
    risk_value = int(snapshot.get("risk") or 0)
    gaps = str(snapshot.get("gaps") or "none")
    quality_score = int(snapshot.get("score") or 0)
    status_key = str(snapshot.get("status") or "not-publishable")
    checklist = _report_quality_checklist(
        evidence=evidence_value,
        primary=primary_value,
        risk=risk_value,
        gaps=gaps,
        copy=copy,
    )
    checklist_items = "".join(f"<li>{escape(item)}</li>" for item in checklist)
    status_copy = copy[f"quality_status_{status_key.replace('-', '_')}"]
    return (
        f'<section id="report-quality-gate" class="report-quality-gate" data-quality-status="{escape(status_key)}">'
        '<div class="quality-summary">'
        f'<div class="eyebrow">{escape(copy["report_quality_eyebrow"])}</div>'
        f'<h2>{escape(copy["report_quality_gate"])}</h2>'
        f'<p>{escape(copy["report_quality_description"])}</p>'
        f'<span class="quality-status" data-quality-status="{escape(status_key)}">{escape(status_copy)}</span>'
        '</div>'
        '<div class="quality-grid">'
        f'<article class="quality-card"><span>{escape(copy["publish_status"])}</span><strong>{escape(status_copy)}</strong><small>{escape(copy["quality_candidate_prefix"])} {escape(top_ticker or "n/a")}</small></article>'
        f'<article class="quality-card"><span>{escape(copy["quality_score"])}</span><strong>{quality_score}/100</strong><small>{escape(copy["quality_score_basis"])}</small></article>'
        f'<article class="quality-card"><span>{escape(copy["evidence_depth"])}</span><strong>{evidence_value}</strong><small>{escape(copy["coverage_evidence_items"])}</small></article>'
        f'<article class="quality-card"><span>{escape(copy["primary_source_depth"])}</span><strong>{primary_value}</strong><small>{escape(copy["coverage_primary_items"])}</small></article>'
        f'<article class="quality-card"><span>{escape(copy["risk_coverage_label"])}</span><strong>{risk_value}</strong><small>{escape(copy["coverage_risk_items"])}</small></article>'
        f'<article class="quality-card"><span>{escape(copy["quality_gaps"])}</span><strong>{escape(gaps)}</strong><small>{escape(copy["quality_gap_basis"])}</small></article>'
        f'<ul class="quality-checklist" aria-label="{escape(copy["quality_checklist"])}"><li><strong>{escape(copy["quality_checklist"])}</strong></li>{checklist_items}</ul>'
        '</div>'
        '</section>'
    )


def _render_saved_workspace(copy: Mapping[str, str]) -> str:
    return (
        '<section id="saved-workspace" class="saved-workspace" aria-labelledby="saved-workspace-title">'
        '<div class="workspace-summary">'
        f'<div class="eyebrow">{escape(copy["saved_workspace_eyebrow"])}</div>'
        f'<h2 id="saved-workspace-title">{escape(copy["saved_research_workspace"])}</h2>'
        f'<p>{escape(copy["saved_workspace_description"])}</p>'
        '<div class="workspace-actions">'
        f'<button type="button" onclick="saveWorkspaceState()">{escape(copy["save_workspace"])}</button>'
        f'<button type="button" onclick="clearWorkspaceState()">{escape(copy["clear_workspace"])}</button>'
        '</div>'
        f'<small id="workspace-saved-at">{escape(copy["workspace_not_saved"])}</small>'
        '</div>'
        '<div class="workspace-grid">'
        '<article class="workspace-card">'
        f'<span>{escape(copy["saved_reports"])}</span>'
        f'<div id="workspace-saved-reports" aria-live="polite"><small>{escape(copy["workspace_no_saved_reports"])}</small></div>'
        '</article>'
        '<article class="workspace-card">'
        f'<span>{escape(copy["candidate_marks"])}</span>'
        f'<div id="workspace-candidate-marks" aria-live="polite"><small>{escape(copy["workspace_no_candidate_marks"])}</small></div>'
        '</article>'
        '<article class="workspace-card">'
        f'<span>{escape(copy["saved_sort_preference"])}</span>'
        f'<strong id="workspace-sort-preference">{escape(copy["not_generated"])}</strong>'
        f'<small>{escape(copy["saved_sort_description"])}</small>'
        '</article>'
        '<article class="workspace-card">'
        f'<span>{escape(copy["quality_gate_snapshot"])}</span>'
        f'<strong id="workspace-quality-snapshot">{escape(copy["not_generated"])} · n/a</strong>'
        f'<small>{escape(copy["quality_snapshot_description"])}</small>'
        '</article>'
        '</div>'
        '</section>'
    )


def _render_research_project_library(copy: Mapping[str, str]) -> str:
    return (
        '<section id="research-project-library" class="research-project-library" aria-labelledby="research-project-library-title">'
        '<div class="project-library-summary">'
        f'<div class="eyebrow">{escape(copy["project_library_eyebrow"])}</div>'
        f'<h2 id="research-project-library-title">{escape(copy["research_project_library"])}</h2>'
        f'<p>{escape(copy["project_library_description"])}</p>'
        '<div class="project-library-actions">'
        f'<button type="button" onclick="saveResearchProject()">{escape(copy["save_as_project"])}</button>'
        f'<button type="button" onclick="clearResearchProjectLibrary()">{escape(copy["clear_projects"])}</button>'
        '</div>'
        f'<small>{escape(copy["project_library_count"])} <strong id="project-library-count">0</strong></small>'
        '</div>'
        '<div>'
        '<div class="project-library-tools">'
        '<div class="project-library-filter">'
        f'<label for="project-library-search">{escape(copy["project_search_label"])}</label>'
        f'<input id="project-library-search" type="search" placeholder="{escape(copy["project_search_placeholder"])}" oninput="filterResearchProjects()">'
        '</div>'
        '<div class="project-library-filter">'
        f'<label for="project-library-sort">{escape(copy["project_sort_label"])}</label>'
        '<select id="project-library-sort" onchange="sortResearchProjects()">'
        f'<option value="recent">{escape(copy["project_sort_recent"])}</option>'
        f'<option value="activity">{escape(copy["project_sort_activity"])}</option>'
        f'<option value="quality">{escape(copy["project_sort_quality"])}</option>'
        f'<option value="topic">{escape(copy["project_sort_topic"])}</option>'
        '</select>'
        '</div>'
        '<div class="project-library-filter">'
        f'<label for="project-status-filter">{escape(copy["project_filter_label"])}</label>'
        '<select id="project-status-filter" onchange="filterResearchProjects()">'
        f'<option value="">{escape(copy["all_project_statuses"])}</option>'
        f'<option value="pending-evidence">{escape(copy["project_status_pending_evidence"])}</option>'
        f'<option value="reviewable">{escape(copy["project_status_reviewable"])}</option>'
        f'<option value="delivered">{escape(copy["project_status_delivered"])}</option>'
        f'<option value="needs-rerun">{escape(copy["project_status_needs_rerun"])}</option>'
        '</select>'
        '</div>'
        '<div class="project-library-filter">'
        f'<label for="project-tag-filter">{escape(copy["project_tags"])}</label>'
        '<select id="project-tag-filter" onchange="filterResearchProjects()">'
        f'<option value="">{escape(copy["all_project_tags"])}</option>'
        f'<option value="needs-evidence">{escape(copy["project_tag_needs_evidence"])}</option>'
        f'<option value="high-quality">{escape(copy["project_tag_high_quality"])}</option>'
        f'<option value="delivered">{escape(copy["project_tag_delivered"])}</option>'
        '</select>'
        '</div>'
        '<div class="project-library-filter">'
        f'<label for="project-next-action-filter">{escape(copy["project_next_action_filter_label"])}</label>'
        '<select id="project-next-action-filter" onchange="filterResearchProjects()">'
        f'<option value="">{escape(copy["all_project_next_actions"])}</option>'
        f'<option value="collect-evidence">{escape(copy["project_next_action_collect_evidence_projects"])}</option>'
        f'<option value="review-report">{escape(copy["project_next_action_review_report_projects"])}</option>'
        f'<option value="rerun-analysis">{escape(copy["project_next_action_rerun_analysis_projects"])}</option>'
        f'<option value="archive-project">{escape(copy["project_next_action_archive_projects"])}</option>'
        '</select>'
        '</div>'
        '<div class="project-library-filter">'
        f'<label for="project-owner-filter">{escape(copy["project_owner_filter_label"])}</label>'
        '<select id="project-owner-filter" onchange="filterResearchProjects()">'
        f'<option value="">{escape(copy["all_project_owners"])}</option>'
        f'<option value="unassigned-owner">{escape(copy["project_owner_unassigned"])}</option>'
        f'<option value="evidence-owner">{escape(copy["project_owner_evidence"])}</option>'
        f'<option value="report-reviewer">{escape(copy["project_owner_reviewer"])}</option>'
        f'<option value="rerun-owner">{escape(copy["project_owner_rerun"])}</option>'
        f'<option value="archive-owner">{escape(copy["project_owner_archive"])}</option>'
        '</select>'
        '</div>'
        '<div class="project-library-filter">'
        f'<label for="project-activity-filter">{escape(copy["project_activity_filter"])}</label>'
        '<select id="project-activity-filter" onchange="filterProjectActivity(this.value)">'
        f'<option value="">{escape(copy["all_activity_states"])}</option>'
        f'<option value="has-activity">{escape(copy["has_activity"])}</option>'
        f'<option value="no-activity">{escape(copy["no_activity"])}</option>'
        '</select>'
        '</div>'
        f'<div id="project-comparison-summary" class="project-comparison-summary" aria-label="{escape(copy["project_comparison_summary"])}">'
        f'<div><span>{escape(copy["project_total_projects"])}</span><strong data-project-total>0</strong></div>'
        f'<div><span>{escape(copy["project_average_quality"])}</span><strong data-project-average-quality>n/a</strong></div>'
        f'<div><span>{escape(copy["project_evidence_backlog"])}</span><strong data-project-evidence-backlog>0</strong></div>'
        f'<div><span>{escape(copy["project_delivered_projects"])}</span><strong data-project-delivered-count>0</strong></div>'
        '</div>'
        '</div>'
        f'<div id="project-next-action-queue-summary" class="project-next-action-queue-summary" aria-label="{escape(copy["next_action_queue"])}">'
        f'<header><div><h3>{escape(copy["next_action_queue"])}</h3><small>{escape(copy["queue_by_workflow_step"])}</small></div>'
        '<div class="project-library-actions">'
        f'<button type="button" data-project-queue-handoff="research-only" data-project-queue-handoff-action="copy" '
        f'data-copied-text="{escape(copy["project_queue_handoff_copied"])}" '
        f'onclick="copyProjectQueueHandoffBrief(this)">{escape(copy["copy_project_queue_handoff"])}</button>'
        f'<button type="button" data-filtered-project-handoff="research-only" data-filtered-project-handoff-action="copy" '
        f'data-copied-text="{escape(copy["filtered_handoff_copied"])}" '
        f'onclick="copyFilteredProjectQueueHandoffBrief(this)">{escape(copy["copy_filtered_handoff"])}</button>'
        '</div></header>'
        f'<button type="button" data-project-next-action-queue="collect-evidence" data-project-next-action-count="0" onclick="filterProjectNextActionQueue(\'collect-evidence\')"><small>{escape(copy["filter_to_collect_evidence"])}</small><strong>0</strong></button>'
        f'<button type="button" data-project-next-action-queue="review-report" data-project-next-action-count="0" onclick="filterProjectNextActionQueue(\'review-report\')"><small>{escape(copy["filter_to_review_reports"])}</small><strong>0</strong></button>'
        f'<button type="button" data-project-next-action-queue="rerun-analysis" data-project-next-action-count="0" onclick="filterProjectNextActionQueue(\'rerun-analysis\')"><small>{escape(copy["filter_to_rerun_analysis"])}</small><strong>0</strong></button>'
        f'<button type="button" data-project-next-action-queue="archive-project" data-project-next-action-count="0" onclick="filterProjectNextActionQueue(\'archive-project\')"><small>{escape(copy["filter_to_archive_projects"])}</small><strong>0</strong></button>'
        '</div>'
        f'<div id="project-owner-queue-summary" class="project-owner-queue-summary" aria-label="{escape(copy["project_owner_queue"])}">'
        f'<header><div><h3>{escape(copy["project_owner_queue"])}</h3><small>{escape(copy["project_owner_queue_description"])}</small></div></header>'
        f'<button type="button" data-project-owner-queue="unassigned-owner" data-project-owner-count="0" onclick="filterProjectOwnerQueue(\'unassigned-owner\')"><small>{escape(copy["project_owner_unassigned"])}</small><strong>0</strong></button>'
        f'<button type="button" data-project-owner-queue="evidence-owner" data-project-owner-count="0" onclick="filterProjectOwnerQueue(\'evidence-owner\')"><small>{escape(copy["project_owner_evidence"])}</small><strong>0</strong></button>'
        f'<button type="button" data-project-owner-queue="report-reviewer" data-project-owner-count="0" onclick="filterProjectOwnerQueue(\'report-reviewer\')"><small>{escape(copy["project_owner_reviewer"])}</small><strong>0</strong></button>'
        f'<button type="button" data-project-owner-queue="rerun-owner" data-project-owner-count="0" onclick="filterProjectOwnerQueue(\'rerun-owner\')"><small>{escape(copy["project_owner_rerun"])}</small><strong>0</strong></button>'
        f'<button type="button" data-project-owner-queue="archive-owner" data-project-owner-count="0" onclick="filterProjectOwnerQueue(\'archive-owner\')"><small>{escape(copy["project_owner_archive"])}</small><strong>0</strong></button>'
        '</div>'
        f'<div id="project-queue-handoff-preview" class="project-queue-handoff-preview" aria-label="{escape(copy["queue_handoff_preview"])}" data-project-queue-handoff-preview="research-only" data-project-queue-handoff-items="0">'
        f'<header><div><h3>{escape(copy["queue_handoff_preview"])}</h3><small>{escape(copy["review_handoff_before_copying"])}</small></div>'
        f'<strong>{escape(copy["handoff_item_count"])}: 0</strong></header>'
        f'<pre>{escape(copy["research_only_queue_handoff"])}</pre>'
        '</div>'
        f'<div id="filtered-project-handoff-preview" class="project-queue-handoff-preview" aria-label="{escape(copy["filtered_handoff_preview"])}" data-filtered-project-handoff-preview="research-only" data-filtered-project-handoff-items="0">'
        f'<header><div><h3>{escape(copy["filtered_handoff_preview"])}</h3><small>{escape(copy["review_handoff_before_copying"])}</small></div>'
        f'<strong>{escape(copy["filtered_item_count"])}: 0</strong></header>'
        f'<pre>{escape(copy["research_only_queue_handoff"])}</pre>'
        '</div>'
        '<div id="project-comparison-matrix" class="project-comparison-matrix" aria-labelledby="project-comparison-matrix-title">'
        '<header>'
        '<div>'
        f'<h3 id="project-comparison-matrix-title">{escape(copy["historical_comparison_matrix"])}</h3>'
        f'<p>{escape(copy["historical_comparison_description"])}</p>'
        '</div>'
        '<div class="project-library-actions">'
        f'<strong>{escape(copy["compare_selected_projects"])}</strong>'
        f'<button type="button" data-project-comparison-brief="research-only" '
        f'data-copied-text="{escape(copy["comparison_brief_copied"])}" '
        f'onclick="copyProjectComparisonBrief(this)">{escape(copy["copy_comparison_brief"])}</button>'
        '</div>'
        '</header>'
        '<div class="project-comparison-table-wrap">'
        '<table id="project-comparison-table" class="project-comparison-table">'
        f'<tbody><tr><td colspan="6"><small>{escape(copy["project_comparison_empty"])}</small></td></tr></tbody>'
        '</table>'
        '</div>'
        '</div>'
        '<div id="project-library-list" class="project-library-list" aria-live="polite">'
        f'<p><small>{escape(copy["project_library_empty"])}</small></p>'
        '</div>'
        '<aside id="project-detail-drawer" class="project-detail-drawer" aria-labelledby="project-detail-title" hidden>'
        '<header>'
        '<div>'
        f'<div class="eyebrow">{escape(copy["project_detail_drawer"])}</div>'
        f'<h2 id="project-detail-title">{escape(copy["project_review_panel"])}</h2>'
        f'<p>{escape(copy["project_detail_description"])}</p>'
        '</div>'
        f'<button type="button" class="drawer-close" onclick="closeProjectDetailDrawer()">{escape(copy["close_report"])}</button>'
        '</header>'
        f'<p><strong>{escape(copy["project_detail_quality"])}:</strong> <span id="project-detail-quality">{escape(copy["not_generated"])}</span></p>'
        '<div id="project-detail-body">'
        f'<p class="drawer-empty">{escape(copy["project_detail_empty"])}</p>'
        '</div>'
        '<div id="project-detail-actions" class="project-detail-actions"></div>'
        '<section id="project-review-action-panel" class="project-review-action-panel" aria-labelledby="project-review-action-title">'
        '<header>'
        '<div>'
        f'<div class="eyebrow">{escape(copy["recommended_review_actions"])}</div>'
        f'<h3 id="project-review-action-title">{escape(copy["project_review_action_panel"])}</h3>'
        '</div>'
        f'<small>{escape(copy["action_logged"])}</small>'
        '</header>'
        '<div id="project-review-action-list" class="project-review-action-list">'
        f'<button type="button" data-project-review-action-type="close-evidence-gap" data-project-review-action-project="" disabled>{escape(copy["close_evidence_gap"])}</button>'
        f'<button type="button" data-project-review-action-type="rerun-analysis" data-project-review-action-project="" disabled>{escape(copy["rerun_analysis"])}</button>'
        f'<button type="button" data-project-review-action-type="mark-delivered" data-project-review-action-project="" disabled>{escape(copy["mark_delivered"])}</button>'
        f'<button type="button" data-project-review-action-type="open-report" data-project-review-action-project="" disabled>{escape(copy["open_report_from_action_panel"])}</button>'
        '</div>'
        f'<p id="project-review-loop-status" class="project-review-loop-status" aria-live="polite" data-project-rerun-context="" data-project-quality-after-rerun="">{escape(copy["evidence_gap_linked_task"])} · {escape(copy["quality_after_rerun"])}</p>'
        '</section>'
        '<section id="project-review-timeline" class="project-review-timeline" aria-labelledby="project-review-timeline-title">'
        '<header>'
        '<div>'
        f'<div class="eyebrow">{escape(copy["review_event_history"])}</div>'
        f'<h3 id="project-review-timeline-title">{escape(copy["project_review_timeline"])}</h3>'
        f'<p>{escape(copy["server_backed_review_event_log"])}</p>'
        '</div>'
        f'<small>{escape(copy["log_review_event"])}</small>'
        '</header>'
        '<div class="project-review-event-controls" aria-label="'
        f'{escape(copy["collaboration_event_view"])}'
        '">'
        f'<div class="eyebrow">{escape(copy["collaboration_event_view"])}</div>'
        f'<label for="project-review-event-filter">{escape(copy["filter_review_events"])}'
        '<select id="project-review-event-filter" onchange="filterProjectReviewEvents(this.value)">'
        f'<option value="">{escape(copy["all_review_events"])}</option>'
        f'<option value="status-changed">{escape(copy["status_events"])}</option>'
        f'<option value="owner-changed">{escape(copy["owner_events"])}</option>'
        f'<option value="detail-opened">{escape(copy["detail_events"])}</option>'
        f'<option value="comparison-brief-copied">{escape(copy["comparison_events"])}</option>'
        f'<option value="queue-handoff-copied">{escape(copy["queue_handoff_events"])}</option>'
        '</select>'
        '</label>'
        '<div id="project-review-event-summary" class="project-review-event-summary" aria-live="polite">'
        f'<button type="button" data-project-review-event-filter="all" data-project-review-event-count="0" onclick="filterProjectReviewEvents(\'\')"><small>{escape(copy["all_review_events"])}</small><strong>0</strong></button>'
        f'<button type="button" data-project-review-event-filter="status-changed" data-project-review-event-count="0" onclick="filterProjectReviewEvents(\'status-changed\')"><small>{escape(copy["status_events"])}</small><strong>0</strong></button>'
        f'<button type="button" data-project-review-event-filter="owner-changed" data-project-review-event-count="0" onclick="filterProjectReviewEvents(\'owner-changed\')"><small>{escape(copy["owner_events"])}</small><strong>0</strong></button>'
        f'<button type="button" data-project-review-event-filter="detail-opened" data-project-review-event-count="0" onclick="filterProjectReviewEvents(\'detail-opened\')"><small>{escape(copy["detail_events"])}</small><strong>0</strong></button>'
        f'<button type="button" data-project-review-event-filter="comparison-brief-copied" data-project-review-event-count="0" onclick="filterProjectReviewEvents(\'comparison-brief-copied\')"><small>{escape(copy["comparison_events"])}</small><strong>0</strong></button>'
        f'<button type="button" data-project-review-event-filter="queue-handoff-copied" data-project-review-event-count="0" onclick="filterProjectReviewEvents(\'queue-handoff-copied\')"><small>{escape(copy["queue_handoff_events"])}</small><strong>0</strong></button>'
        '</div>'
        '</div>'
        '<ul id="project-review-timeline-list">'
        f'<li data-project-review-event="empty" data-project-review-event-type="empty" data-project-review-event-project=""><small>{escape(copy["project_review_timeline_empty"])}</small></li>'
        '</ul>'
        '</section>'
        '<section id="project-evidence-audit-log" class="project-evidence-audit-log" aria-labelledby="project-evidence-audit-title">'
        '<header>'
        '<div>'
        f'<div class="eyebrow">{escape(copy["evidence_contribution_history"])}</div>'
        f'<h3 id="project-evidence-audit-title">{escape(copy["project_evidence_audit_log"])}</h3>'
        f'<p>{escape(copy["verified_task_audit_trail"])}</p>'
        '</div>'
        f'<small>{escape(copy["quality_contribution"])}</small>'
        '</header>'
        '<div id="project-evidence-quality-delta-summary" class="project-evidence-quality-delta-summary" data-project-evidence-quality-delta="n/a">'
        f'<strong>{escape(copy["latest_quality_delta"])}</strong>'
        f'<small>{escape(copy["quality_delta_summary_empty"])}</small>'
        '</div>'
        '<ul id="project-evidence-audit-list">'
        f'<li data-project-evidence-audit="empty" data-project-evidence-audit-type="empty" data-project-evidence-audit-quality-delta="n/a"><small>{escape(copy["project_evidence_audit_empty"])}</small></li>'
        '</ul>'
        '</section>'
        '</aside>'
        '</div>'
        '</section>'
    )


def _render_deliverable_report(copy: Mapping[str, str]) -> str:
    href = "reports/deliverable-research-report.md"
    return (
        '<section id="deliverable-report" class="deliverable-report" data-report-type="deliverable" aria-labelledby="deliverable-report-title">'
        '<div class="deliverable-summary">'
        f'<div class="eyebrow">{escape(copy["deliverable_report_eyebrow"])}</div>'
        f'<h2 id="deliverable-report-title">{escape(copy["deliverable_research_report"])}</h2>'
        f'<p>{escape(copy["deliverable_report_description"])}</p>'
        '<div class="deliverable-actions">'
        f'<button type="button" class="memo-link" data-deliverable-href="{escape(href)}" '
        f'data-memo-href="{escape(href)}" data-memo-title="{escape(copy["deliverable_research_report"])}" '
        f'onclick="openMemoDrawer(this)">{escape(copy["open_deliverable_report"])}</button>'
        f'<button type="button" onclick="printDeliverableReport()">{escape(copy["print_save_pdf"])}</button>'
        '</div>'
        f'<div class="share-handoff" aria-label="{escape(copy["share_handoff"])}">'
        f'<span>{escape(copy["share_handoff"])}</span>'
        f'<button type="button" class="memo-link" data-share-href="{escape(href)}" '
        f'data-copied-text="{escape(copy["copied_link"])}" onclick="copyShareLink(this)">{escape(copy["copy_report_link"])}</button>'
        f'<button type="button" class="memo-link" data-share-href="analysis-manifest.json" '
        f'data-copied-text="{escape(copy["copied_link"])}" onclick="copyShareLink(this)">{escape(copy["copy_manifest_link"])}</button>'
        '</div>'
        f'<small>{escape(href)}</small>'
        '</div>'
        '<div class="deliverable-grid">'
        '<article class="deliverable-card">'
        f'<span>{escape(copy["export_ready_brief"])}</span>'
        f'<strong>{escape(copy["deliverable_report_type"])}</strong>'
        f'<small>{escape(copy["deliverable_brief_description"])}</small>'
        '</article>'
        '<article class="deliverable-card">'
        f'<span>{escape(copy["deliverable_contents"])}</span>'
        f'<strong>{escape(copy["deliverable_contents_summary"])}</strong>'
        f'<small>{escape(copy["deliverable_contents_description"])}</small>'
        '</article>'
        '</div>'
        '</section>'
    )


def _render_delivery_package(
    rows: Sequence[Mapping[str, str]],
    copy: Mapping[str, str],
    quality_snapshot: Mapping[str, object] | None = None,
) -> str:
    report_lookup = {str(row.get("title_key") or ""): str(row.get("href") or "") for row in rows}
    artifacts = [
        {
            "key": "deliverable-report",
            "title": copy["deliverable_research_report"],
            "description": copy["delivery_package_deliverable_description"],
            "href": "reports/deliverable-research-report.md",
            "open": copy["open_deliverable_report"],
            "copy": copy["copy_report_link"],
        },
        {
            "key": "analysis-manifest",
            "title": copy["analysis_manifest_title"],
            "description": copy["delivery_package_manifest_description"],
            "href": report_lookup.get("analysis_manifest_title", "analysis-manifest.json"),
            "open": copy["open_analysis_manifest"],
            "copy": copy["copy_manifest_link"],
        },
        {
            "key": "coverage-matrix",
            "title": copy["coverage_matrix_title"],
            "description": copy["delivery_package_coverage_description"],
            "href": report_lookup.get("coverage_matrix_title", "reports/universe-coverage-matrix.md"),
            "open": copy["open_coverage_matrix"],
            "copy": copy["copy_report_link"],
        },
        {
            "key": "evidence-queue",
            "title": copy["acquisition_queue_title"],
            "description": copy["delivery_package_queue_description"],
            "href": report_lookup.get("acquisition_queue_title", "reports/evidence-acquisition-queue.md"),
            "open": copy["open_acquisition_queue"],
            "copy": copy["copy_report_link"],
        },
    ]
    cards = []
    for artifact in artifacts:
        href = artifact["href"]
        actions = (
            '<div class="report-actions">'
            f'<button type="button" class="memo-link" data-memo-href="{escape(href)}" '
            f'data-memo-title="{escape(artifact["title"])}" onclick="openMemoDrawer(this)">{escape(artifact["open"])}</button>'
            f'<button type="button" class="memo-link" data-share-href="{escape(href)}" '
            f'data-copied-text="{escape(copy["copied_link"])}" onclick="copyShareLink(this)">{escape(artifact["copy"])}</button>'
            '</div>'
            if href
            else f'<span class="memo-link" aria-disabled="true">{escape(copy["not_generated"])}</span>'
        )
        cards.append(
            f'<article class="package-artifact" data-package-artifact="{escape(artifact["key"])}" '
            f'data-handoff-artifact-title="{escape(artifact["title"])}" data-handoff-artifact-href="{escape(href)}">'
            f'<h3>{escape(artifact["title"])}</h3>'
            f'<p>{escape(artifact["description"])}</p>'
            f'{actions}'
            f'<small>{escape(href or copy["not_generated"])}</small>'
            '</article>'
        )
    return (
        '<section id="delivery-package" class="delivery-package" aria-labelledby="delivery-package-title">'
        '<header>'
        '<div>'
        f'<div class="eyebrow">{escape(copy["delivery_package_eyebrow"])}</div>'
        f'<h2 id="delivery-package-title">{escape(copy["delivery_package"])}</h2>'
        f'<p>{escape(copy["delivery_package_description"])}</p>'
        '</div>'
        '<div class="delivery-package-actions">'
        f'<button type="button" class="memo-link" data-copied-text="{escape(copy["handoff_bundle_copied"])}" onclick="copyHandoffBundle(this)">{escape(copy["copy_handoff_bundle"])}</button>'
        '</div>'
        '</header>'
        f'{_render_delivery_quality_summary(quality_snapshot or {}, copy)}'
        f'<div class="delivery-package-grid">{"".join(cards)}</div>'
        '</section>'
    )


def _render_delivery_quality_summary(snapshot: Mapping[str, object], copy: Mapping[str, str]) -> str:
    status_key = str(snapshot.get("status") or "not-publishable")
    quality_score = int(snapshot.get("score") or 0)
    top_ticker = str(snapshot.get("ticker") or "n/a").upper() or "n/a"
    gaps = str(snapshot.get("gaps") or "none")
    gaps_display = copy["delivery_quality_no_remaining_gaps"] if gaps.lower() == "none" else gaps
    status_copy = copy.get(f"quality_status_{status_key.replace('-', '_')}", status_key)
    return (
        '<div class="delivery-quality-summary" '
        f'data-delivery-quality-status="{escape(status_key)}" '
        f'data-delivery-quality-score="{quality_score}" '
        f'data-delivery-quality-candidate="{escape(top_ticker)}">'
        '<div class="delivery-quality-heading">'
        '<div>'
        f'<div class="eyebrow">{escape(copy["delivery_quality_summary"])}</div>'
        f'<strong>{escape(status_copy)}</strong>'
        '</div>'
        f'<span class="research-only-badge">{escape(copy["research_only_package"])}</span>'
        '</div>'
        '<div class="delivery-quality-strip">'
        f'<span><small>{escape(copy["quality_score"])}</small><strong>{quality_score}/100</strong></span>'
        f'<span><small>{escape(copy["top_candidate"])}</small><strong>{escape(top_ticker)}</strong></span>'
        f'<span><small>{escape(copy["remaining_gaps"])}</small><strong>{escape(gaps_display)}</strong></span>'
        '</div>'
        '</div>'
    )


def _report_quality_score(score: int, evidence: int, primary: int, risk: int) -> int:
    evidence_points = min(evidence * 2, 20)
    primary_points = min(primary * 8, 24)
    risk_points = min(risk * 4, 16)
    return max(0, min(100, int(round(score * 0.4 + evidence_points + primary_points + risk_points))))


def _report_quality_snapshot(
    memo_rows: Sequence[Mapping[str, str]],
    memo_previews: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    if not memo_rows:
        return {}
    preview_by_ticker = {
        str(preview.get("ticker", "")).upper(): preview
        for preview in memo_previews
        if str(preview.get("ticker", "")).strip()
    }
    top_row = _select_top_candidate(memo_rows, preview_by_ticker)
    top_ticker = str(top_row.get("ticker") or "").upper()
    top_preview = preview_by_ticker.get(top_ticker, {})
    score_text = str(top_preview.get("score") or top_row.get("score") or "0")
    score_match = re.search(r"\d+", score_text)
    score_value = int(score_match.group(0)) if score_match else 0
    evidence_value = _to_int(top_row.get("evidence", "0"))
    primary_value = _to_int(top_row.get("primary", "0"))
    risk_value = _to_int(top_row.get("risk", "0"))
    gaps = str(top_preview.get("gaps") or top_row.get("gaps") or "none")
    quality_score = _report_quality_score(score_value, evidence_value, primary_value, risk_value)
    status_key = _report_quality_status(quality_score, primary_value, risk_value, gaps, top_row)
    return {
        "ticker": top_ticker,
        "score": quality_score,
        "status": status_key,
        "evidence": evidence_value,
        "primary": primary_value,
        "risk": risk_value,
        "gaps": gaps,
        "row": top_row,
    }


def _report_quality_status(
    quality_score: int,
    primary: int,
    risk: int,
    gaps: str,
    row: Mapping[str, str],
) -> str:
    normalized_gaps = gaps.lower()
    if str(row.get("status", "")).lower() != "ready" or quality_score < 35:
        return "not-publishable"
    if primary < 2 or risk < 2 or "primary" in normalized_gaps or "low_score" in normalized_gaps:
        return "needs-evidence"
    if quality_score >= 70:
        return "publishable"
    return "needs-evidence"


def _report_quality_checklist(
    *,
    evidence: int,
    primary: int,
    risk: int,
    gaps: str,
    copy: Mapping[str, str],
) -> list[str]:
    items = []
    items.append(copy["quality_check_evidence_ok"] if evidence >= 10 else copy["quality_check_evidence_gap"])
    items.append(copy["quality_check_primary_ok"] if primary >= 2 and "primary" not in gaps.lower() else copy["quality_check_primary_gap"])
    items.append(copy["quality_check_risk_ok"] if risk >= 2 else copy["quality_check_risk_gap"])
    items.append(copy["quality_check_gap_ok"] if gaps == "none" else copy["quality_check_gap_review"].format(gaps=gaps))
    return items


def _decision_key_drivers(
    row: Mapping[str, str],
    metrics: Mapping[str, str],
    copy: Mapping[str, str],
) -> list[str]:
    drivers = [
        copy["decision_driver_evidence"].format(
            evidence=str(row.get("evidence", "0")),
            primary=str(row.get("primary", "0")),
            risk=str(row.get("risk", "0")),
        )
    ]
    revenue_growth = _localize_metric_value(str(metrics.get("revenue_growth") or "n/a"), copy)
    gross_margin = _localize_metric_value(str(metrics.get("gross_margin") or "n/a"), copy)
    valuation = _localize_metric_value(str(metrics.get("valuation") or "n/a"), copy)
    momentum = _localize_metric_value(str(metrics.get("momentum") or "n/a"), copy)
    cycle_position = _localize_metric_value(str(metrics.get("cycle_position") or "n/a"), copy)
    if revenue_growth != "n/a" and revenue_growth != "暂无":
        drivers.append(copy["decision_driver_revenue"].format(value=revenue_growth))
    if gross_margin != "n/a" and gross_margin != "暂无":
        drivers.append(copy["decision_driver_margin"].format(value=gross_margin))
    if valuation != "n/a" and valuation != "暂无":
        drivers.append(copy["decision_driver_valuation"].format(value=valuation))
    if momentum != "n/a" and momentum != "暂无":
        drivers.append(copy["decision_driver_momentum"].format(value=momentum))
    if cycle_position != "n/a" and cycle_position != "暂无":
        drivers.append(copy["decision_driver_cycle"].format(value=cycle_position))
    return drivers[:3] or [copy["decision_driver_fallback"]]


def _decision_counter_risks(
    preview: Mapping[str, object],
    row: Mapping[str, str],
    gaps: str,
    copy: Mapping[str, str],
) -> list[str]:
    risks = [str(item) for item in preview.get("risks", []) if str(item).strip()]
    invalidations = [str(item) for item in preview.get("invalidations", []) if str(item).strip()]
    items = risks[:1] + invalidations[:1]
    if _to_int(row.get("primary", "0")) <= 0 or "primary" in gaps.lower():
        items.append(copy["decision_risk_primary_gap"])
    if not items:
        items.append(copy["decision_risk_fallback"])
    return items[:3]


def _decision_runner_up_text(
    memo_rows: Sequence[Mapping[str, str]],
    preview_by_ticker: Mapping[str, Mapping[str, object]],
    top_ticker: str,
    copy: Mapping[str, str],
) -> str:
    runner_ups = [
        row for row in sorted(memo_rows, key=lambda row: _candidate_rank_tuple(row, preview_by_ticker), reverse=True)
        if str(row.get("ticker") or "").upper() != top_ticker.upper()
    ]
    if not runner_ups:
        return copy["decision_no_runner_up"]
    runner = runner_ups[0]
    runner_ticker = str(runner.get("ticker") or "n/a")
    runner_preview = preview_by_ticker.get(runner_ticker.upper(), {})
    runner_score = str(runner_preview.get("score") or runner.get("score") or "n/a")
    runner_gaps = str(runner_preview.get("gaps") or runner.get("gaps") or "none")
    return copy["decision_runner_up_body"].format(
        ticker=runner_ticker,
        score=runner_score,
        gaps=runner_gaps,
    )


def _candidate_rank_tuple(
    row: Mapping[str, str],
    preview_by_ticker: Mapping[str, Mapping[str, object]],
) -> tuple[int, int, int, int]:
    ticker = str(row.get("ticker") or "").upper()
    preview = preview_by_ticker.get(ticker, {})
    score_text = str(preview.get("score") or row.get("score") or "0")
    match = re.search(r"\d+", score_text)
    numeric_score = int(match.group(0)) if match else 0
    ready_bonus = 1 if str(row.get("status", "")).lower() == "ready" else 0
    return (ready_bonus, numeric_score, _to_int(row.get("primary", "0")), _to_int(row.get("risk", "0")))


def _select_top_candidate(
    memo_rows: Sequence[Mapping[str, str]],
    preview_by_ticker: Mapping[str, Mapping[str, object]],
) -> Mapping[str, str]:
    return max(memo_rows, key=lambda row: _candidate_rank_tuple(row, preview_by_ticker))


def _briefing_coverage_state(row: Mapping[str, str], copy: Mapping[str, str]) -> str:
    if str(row.get("status", "")).lower() != "ready":
        return copy["briefing_needs_evidence"]
    if _to_int(row.get("primary", "0")) <= 0:
        return copy["briefing_needs_primary"]
    if _to_int(row.get("risk", "0")) <= 0:
        return copy["briefing_needs_risk"]
    return copy["briefing_reviewable"]


def _briefing_primary_gap(row: Mapping[str, str], gaps: str, copy: Mapping[str, str]) -> str:
    normalized = gaps.lower()
    if _to_int(row.get("primary", "0")) <= 0 or "primary" in normalized or "missing_primary" in normalized:
        return copy["primary_gap_present"]
    return copy["primary_gap_closed"]


def _briefing_task_count(operational_reports: Sequence[Mapping[str, object]]) -> int:
    total = 0
    for report in operational_reports:
        tasks = report.get("tasks")
        if isinstance(tasks, list):
            total += len(tasks)
    return total


def _render_candidate_comparison(
    memo_rows: Sequence[Mapping[str, str]],
    memo_previews: Sequence[Mapping[str, object]],
    copy: Mapping[str, str],
    metrics_by_ticker: Mapping[str, Mapping[str, str]],
) -> str:
    if not memo_rows:
        return f'<div class="note">{escape(copy["no_memos"])}</div>'

    preview_by_ticker = {
        str(preview.get("ticker", "")).upper(): preview
        for preview in memo_previews
        if str(preview.get("ticker", "")).strip()
    }
    body = []
    for row in memo_rows:
        ticker = row.get("ticker", "")
        preview = preview_by_ticker.get(ticker.upper(), {})
        score = str(preview.get("score") or row.get("score") or "n/a")
        rating = str(preview.get("rating") or row.get("rating") or copy["not_generated"])
        confidence = str(preview.get("confidence") or row.get("confidence") or copy["not_generated"])
        gaps = str(preview.get("gaps") or row.get("gaps") or "none")
        metrics = metrics_by_ticker.get(ticker.upper(), {})
        revenue_growth = _localize_metric_value(str(metrics.get("revenue_growth") or "n/a"), copy)
        gross_margin = _localize_metric_value(str(metrics.get("gross_margin") or "n/a"), copy)
        valuation = _localize_metric_value(str(metrics.get("valuation") or "n/a"), copy)
        momentum = _localize_metric_value(str(metrics.get("momentum") or "n/a"), copy)
        cycle_position = _localize_metric_value(str(metrics.get("cycle_position") or "n/a"), copy)
        body.append(
            f"<tr data-dashboard-item data-ticker=\"{escape(ticker)}\" data-status=\"{escape(row.get('status', ''))}\" data-search=\"{escape(_search_blob({**dict(row), 'score': score, 'rating': rating, 'confidence': confidence, 'gaps': gaps, 'revenue_growth': revenue_growth, 'gross_margin': gross_margin, 'valuation': valuation, 'momentum': momentum, 'cycle_position': cycle_position}))}\">"
            f"<td>{escape(ticker)}</td>"
            f"<td>{_status_pill(row.get('status', ''))}</td>"
            f"<td class=\"num\">{escape(score)}</td>"
            f"<td>{escape(rating)}</td>"
            f"<td>{escape(confidence)}</td>"
            f"<td>{escape(gaps)}</td>"
            f"<td>{escape(revenue_growth)}</td>"
            f"<td>{escape(gross_margin)}</td>"
            f"<td>{escape(valuation)}</td>"
            f"<td>{escape(momentum)}</td>"
            f"<td>{escape(cycle_position)}</td>"
            f"<td class=\"num\">{escape(row.get('evidence', '0'))}</td>"
            f"<td class=\"num\">{escape(row.get('primary', '0'))}</td>"
            f"<td class=\"num\">{escape(row.get('risk', '0'))}</td>"
            "</tr>"
        )

    return (
        '<div class="table-wrap"><table>'
        f"<thead><tr><th>{escape(copy['ticker'])}</th><th>{escape(copy['status'])}</th><th class=\"num\">{escape(copy['score'])}</th>"
        f"<th>{escape(copy['rating'])}</th><th>{escape(copy['confidence'])}</th><th>{escape(copy['key_gaps'])}</th>"
        f"<th>{escape(copy['revenue_growth'])}</th><th>{escape(copy['gross_margin'])}</th><th>{escape(copy['valuation'])}</th>"
        f"<th>{escape(copy['momentum'])}</th><th>{escape(copy['cycle_position'])}</th>"
        f"<th class=\"num\">{escape(copy['evidence_count'])}</th><th class=\"num\">{escape(copy['primary_fact'])}</th><th class=\"num\">{escape(copy['risk'])}</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def _localize_metric_value(value: str, copy: Mapping[str, str]) -> str:
    if copy.get("language") != "zh":
        return value
    if value == "n/a":
        return "暂无"
    replacements = {
        "reported profitable": "已披露盈利",
        "reported loss": "已披露亏损",
        "source-backed revenue base": "来源支持收入基数",
        "revenue ramp / loss-making": "收入爬坡 / 仍处亏损",
        "40% YoY official report": "官方报告披露同比增长 40%",
    }
    if value in replacements:
        return replacements[value]
    if value.startswith("source-backed revenue "):
        return value.replace("source-backed revenue ", "来源支持收入 ", 1)
    return value


def _render_memo_cards(rows: Sequence[Mapping[str, str]], copy: Mapping[str, str]) -> str:
    if not rows:
        return f'<div class="note">{escape(copy["no_memos"])}</div>'
    cards = []
    for row in rows:
        memo_file = row.get("memo_file", "")
        link = row.get("memo_href") or memo_file
        title = f"{row.get('ticker', '')} {copy['report_reader']}".strip()
        open_link = (
            f'<button type="button" class="memo-link" data-memo-href="{escape(link)}" data-memo-title="{escape(title)}" onclick="openMemoDrawer(this)">{escape(copy["view_report"])}</button>'
            if memo_file and memo_file != "not generated"
            else f'<span class="memo-link" aria-disabled="true">{escape(copy["not_generated"])}</span>'
        )
        cards.append(
            f"<article class=\"memo-card\" data-dashboard-item data-ticker=\"{escape(row.get('ticker', ''))}\" data-status=\"{escape(row.get('status', ''))}\" data-filter-status=\"{escape(row.get('status', ''))}\" data-search=\"{escape(_search_blob(row))}\">"
            "<header>"
            f"<div><div class=\"eyebrow\">{escape(row.get('ticker', ''))}</div><h3>{escape(row.get('status', '').replace('_', ' ').title())}</h3></div>"
            f"{_status_pill(row.get('status', ''))}"
            "</header>"
            f"{open_link}"
            "<dl>"
            f"<div><dt>{escape(copy['evidence_count'])}</dt><dd>{escape(row.get('evidence', '0'))}</dd></div>"
            f"<div><dt>{escape(copy['primary'])}</dt><dd>{escape(row.get('primary', '0'))}</dd></div>"
            f"<div><dt>{escape(copy['risk'])}</dt><dd>{escape(row.get('risk', '0'))}</dd></div>"
            "</dl>"
            f"<p class=\"source-meta\">{escape(copy['serenity_rating'])}: {escape(row.get('rating', copy['not_generated']))} | {escape(copy['confidence'])}: {escape(row.get('confidence', copy['not_generated']))}</p>"
            f"<p class=\"source-meta\">{escape(copy['key_gaps'])}: {escape(row.get('gaps', 'none'))}</p>"
            f"<p class=\"source-meta\">{escape(copy['flags'])}: {escape(row.get('flags', 'none'))}</p>"
            "</article>"
        )
    return f'<div class="memo-grid">{"".join(cards)}</div>'


def _render_memo_previews(previews: Sequence[Mapping[str, object]], copy: Mapping[str, str]) -> str:
    if not previews:
        return f'<div class="note">{escape(copy["no_previews"])}</div>'
    items = []
    for preview in previews:
        risks = _render_list(preview.get("risks", []))
        invalidations = _render_list(preview.get("invalidations", []))
        memo_href = str(preview.get("memo_href") or preview.get("memo_file") or "")
        title = f"{preview.get('ticker', '')} {copy['report_reader']}".strip()
        memo_link = (
            f'<button type="button" class="memo-link" data-memo-href="{escape(memo_href)}" data-memo-title="{escape(title)}" onclick="openMemoDrawer(this)">{escape(copy["view_report"])}</button>'
            if memo_href
            else ""
        )
        items.append(
            f"<article class=\"preview\" data-dashboard-item data-ticker=\"{escape(str(preview.get('ticker', '')))}\" data-search=\"{escape(_search_blob(preview))}\">"
            '<div class="preview-top">'
            f"<div><div class=\"eyebrow\">{escape(str(preview.get('ticker', '')))}</div><h3>{escape(str(preview.get('memo_file', 'Memo')))}</h3></div>"
            f"<div class=\"score\">{escape(str(preview.get('score', 'n/a')))}</div>"
            "</div>"
            f"<p class=\"source-meta\">{escape(copy['serenity_rating'])}: {escape(str(preview.get('rating', copy['not_generated'])))} | {escape(copy['confidence'])}: {escape(str(preview.get('confidence', copy['not_generated'])))}</p>"
            f"<p class=\"source-meta\">{escape(copy['key_gaps'])}: {escape(str(preview.get('gaps', 'none')))}</p>"
            f"<p>{escape(str(preview.get('thesis', copy['no_thesis'])))}</p>"
            f"<div class=\"note\"><strong>{escape(copy['source_coverage'])}:</strong> {escape(str(preview.get('coverage', copy['no_coverage'])))}</div>"
            '<div class="columns">'
            f"<div class=\"note\"><strong>{escape(copy['risks'])}</strong>{risks}</div>"
            f"<div class=\"note\"><strong>{escape(copy['invalidation_conditions'])}</strong>{invalidations}</div>"
            "</div>"
            f"{memo_link}"
            "</article>"
        )
    return f'<div class="preview-grid is-compact">{"".join(items)}</div>'


def _render_sources(sources: Sequence[Mapping[str, str]], copy: Mapping[str, str]) -> str:
    if not sources:
        return f'<div class="note">{escape(copy["no_sources"])}</div>'
    rendered = []
    for source in sources[:18]:
        title = source.get("title") or source.get("id", "Source")
        url = source.get("url", "")
        link = f'<a href="{escape(url)}">{escape(title)}</a>' if url else f"<strong>{escape(title)}</strong>"
        rendered.append(
            f"<article class=\"source\" data-dashboard-item data-ticker=\"{escape(source.get('tickers', ''))}\" data-search=\"{escape(_search_blob(source))}\">"
            f"{link}"
            f"<div class=\"source-meta\">{escape(source.get('id', ''))} | {escape(copy['ticker'])}: {escape(source.get('tickers', ''))} | {escape(copy['used_in'])}: {escape(source.get('memos', ''))}</div>"
            f"<p>{escape(source.get('claim', copy['no_claim']))}</p>"
            f"<blockquote>{escape(source.get('excerpt', copy['no_excerpt']))}</blockquote>"
            "</article>"
        )
    return f'<div class="source-list">{"".join(rendered)}</div>'


def _status_pill(status: str) -> str:
    normalized = (status or "unknown").strip().lower()
    class_name = re.sub(r"[^a-z0-9_-]+", "_", normalized)
    return f'<span class="pill {escape(class_name)}">{escape(normalized.replace("_", " ").title())}</span>'


def _localized_output_path(output: Path, language: str) -> Path:
    if language == "zh":
        return output.with_name(f"{output.stem}.zh{output.suffix}")
    return output


def _localized_status(status: str, language: str) -> str:
    if language != "zh":
        return status
    return {
        "Ready": "就绪",
        "Needs Review": "需要复核",
        "ready": "就绪",
        "needs_work": "需补充",
        "blocked": "阻塞",
    }.get(status, status)


def _localize_priority_label(priority: str, copy: Mapping[str, str]) -> str:
    if copy.get("language") != "zh":
        return priority or "n/a"
    return {
        "high": "高",
        "medium": "中",
        "low": "低",
        "高": "高",
        "中": "中",
        "低": "低",
    }.get(priority, priority or "暂无")


def _localize_gap_label(gap: str, copy: Mapping[str, str]) -> str:
    if copy.get("language") != "zh":
        return gap or "n/a"
    return {
        "missing_primary_source": "缺少 primary/fact 来源",
        "缺少 primary/fact 来源": "缺少 primary/fact 来源",
        "missing_risk_coverage": "缺少风险证据",
        "缺少风险证据": "缺少风险证据",
        "methodology_concentration": "方法论证据过度集中",
        "方法论证据过度集中": "方法论证据过度集中",
        "placeholder_concentration": "SERENITY 占位证据过度集中",
        "SERENITY 占位证据过度集中": "SERENITY 占位证据过度集中",
    }.get(gap, gap or "暂无")


def _localize_source_target_label(source_target: str, copy: Mapping[str, str]) -> str:
    if copy.get("language") != "zh":
        return source_target or "n/a"
    return {
        "Primary filing, company release, audited fact, or official investor material": "Primary filing、公司公告、审计事实或官方投资者材料",
        "Primary filing、公司公告、审计事实或官方投资者材料": "Primary filing、公司公告、审计事实或官方投资者材料",
        "Risk, negative, or invalidation evidence from filings, earnings calls, or credible third-party sources": "来自 filings、业绩会或可信第三方来源的风险、负面或失效证据",
        "来自 filings、业绩会或可信第三方来源的风险、负面或失效证据": "来自 filings、业绩会或可信第三方来源的风险、负面或失效证据",
        "Company-specific non-methodology evidence that supports or challenges the thesis": "支持或挑战论点的公司级非方法论证据",
        "支持或挑战论点的公司级非方法论证据": "支持或挑战论点的公司级非方法论证据",
        "Resolved ticker-specific evidence replacing SERENITY placeholder records": "替换 SERENITY 占位记录的标的级证据",
        "替换 SERENITY 占位记录的标的级证据": "替换 SERENITY 占位记录的标的级证据",
    }.get(source_target, source_target or "暂无")


def _default_task_rationale(gap: str) -> str:
    canonical = _canonical_gap(gap)
    if canonical == "missing_primary_source":
        return "Primary/fact evidence is required before this candidate can clear the research confidence gate."
    if canonical == "missing_risk_coverage":
        return "Risk coverage is required to avoid a one-sided thesis before promotion."
    if canonical == "methodology_concentration":
        return "Company-specific evidence is required to reduce reliance on methodology-only records."
    if canonical == "placeholder_concentration":
        return "Ticker-specific evidence is required to replace SERENITY placeholder records."
    return "Traceable evidence is required before this research task can be promoted."


def _default_task_acceptance_criteria(gap: str) -> str:
    canonical = _canonical_gap(gap)
    if canonical == "missing_risk_coverage":
        return "Evidence should include a negative, downside, or invalidation claim tied to the ticker."
    if canonical == "methodology_concentration":
        return "Evidence should support or challenge the ticker-specific thesis with a traceable source excerpt."
    if canonical == "placeholder_concentration":
        return "Evidence should name the ticker and include a traceable source excerpt."
    return "Source title, URL, and source excerpt must directly support the task claim."


def _default_task_after_import(gap: str) -> str:
    return "Import the evidence, rerun the analysis, and confirm the quality gate improves."


def _localize_task_playbook_text(value: str, copy: Mapping[str, str]) -> str:
    if copy.get("language") != "zh":
        return value or "n/a"
    return {
        "Primary/fact evidence is required before this candidate can clear the research confidence gate.": "需要 primary/fact 证据才能提升研究置信度门禁。",
        "Risk coverage is required to avoid a one-sided thesis before promotion.": "需要风险覆盖，避免在提升研究置信度前形成单边论点。",
        "Company-specific evidence is required to reduce reliance on methodology-only records.": "需要公司级证据，降低对纯方法论记录的依赖。",
        "Ticker-specific evidence is required to replace SERENITY placeholder records.": "需要标的级证据替换 SERENITY 占位记录。",
        "Traceable evidence is required before this research task can be promoted.": "提升研究任务前需要补充可追溯证据。",
        "Source title, URL, and source excerpt must directly support the task claim.": "来源标题、链接和原文摘录必须能直接支撑任务声明。",
        "Evidence should include a negative, downside, or invalidation claim tied to the ticker.": "证据应包含与标的相关的负面、下行或失效声明。",
        "Evidence should support or challenge the ticker-specific thesis with a traceable source excerpt.": "证据应通过可追溯摘录支持或挑战标的级论点。",
        "Evidence should name the ticker and include a traceable source excerpt.": "证据应点名标的，并包含可追溯原文摘录。",
        "Import the evidence, rerun the analysis, and confirm the quality gate improves.": "导入证据后重新生成分析，并确认质量门禁改善。",
    }.get(value, value or "暂无")


def _copy(language: str) -> dict[str, str]:
    if language == "zh":
        return {
            "language": "zh",
            "title_suffix": "本地研究仪表盘",
            "skip": "跳到主要内容",
            "eyebrow": "本地研究仪表盘",
            "readiness": "就绪状态",
            "memo_pack": "备忘录包",
            "evidence": "证据",
            "alternate_language": "English",
            "overview": "CPO 研究包总览",
            "hero_title": "把投资研究包整理成一个可交互的产品视图。",
            "hero_subtitle": "先查看候选标的就绪状态、备忘录覆盖、风险检查和来源溯源，再打开详细 Markdown 备忘录。",
            "research_question": "研究问题",
            "pack_status": "研究包状态",
            "ready_memos_lower": "份就绪备忘录",
            "skipped_summary": "个候选标的被跳过或需要复核。",
            "primary_summary": "条 primary/fact 证据，",
            "risk_summary": "条风险证据已纳入。",
            "total_evidence": "证据总数",
            "ready_memos": "就绪备忘录",
            "primary_fact": "Primary / Fact",
            "risk_items": "风险项",
            "launch_aria": "启动新的行业主题分析",
            "launch_label": "输入新的行业主题",
            "launch_placeholder": "例如：存储芯片、HBM、半导体设备",
            "launch_button": "启动分析",
            "launch_loading": "正在生成分析...",
            "launch_help": "这会基于当前本地证据库重新生成一个主题研究包；搜索框只筛选当前页面内容。",
            "preview_scope": "预览分析范围",
            "confirm_generate": "确认并生成",
            "input_preview_eyebrow": "分析前确认",
            "input_preview": "输入解析预览",
            "detected_input_type": "识别输入类型",
            "evidence_coverage": "证据覆盖",
            "candidate_coverage_detail": "候选覆盖明细",
            "candidate_coverage_empty": "暂无候选覆盖明细",
            "preflight_evidence_tasks": "预检补证动作",
            "preflight_evidence_tasks_empty": "暂无预检补证动作",
            "copy_evidence_gap_prompt": "复制补证提示",
            "open_evidence_import_handoff": "打开补证导入",
            "expected_outputs": "预计输出",
            "expected_outputs_value": "报告、候选对比、证据任务和运营报告",
            "preview_waiting": "等待输入",
            "preview_ready": "已生成解析预览，请确认后生成报告。",
            "preview_resolving": "正在用后端解析器预览分析范围...",
            "preview_fallback": "预览暂不可用，已使用本地兜底解析。",
            "preview_source": "解析来源",
            "preview_source_backend": "后端解析器",
            "preview_source_local": "本地兜底解析",
            "intent_theme": "主题",
            "intent_industry": "行业",
            "intent_sector": "板块",
            "intent_ticker": "个股",
            "coverage_evidence_items": "条证据",
            "coverage_primary_items": "条 primary/fact",
            "coverage_risk_items": "条风险证据",
            "semiconductor_equipment_theme": "半导体设备",
            "workbench_eyebrow": "产品工作台",
            "research_workflow": "研究工作台",
            "workbench_description": "从行业、板块或个股输入开始，按 Serenity 框架完成候选比较、报告阅读、证据补齐和复核。",
            "workflow_scope": "定义范围",
            "workflow_scope_description": "输入行业、主题、板块或股票代码，系统解析候选标的和相关证据。",
            "workflow_compare": "比较候选标的",
            "workflow_compare_description": "用评分、评级、置信层级、关键短板和覆盖度做横向筛选。",
            "workflow_reports": "阅读报告",
            "workflow_reports_description": "在右侧报告阅读器中查看备忘录、覆盖矩阵和采集队列。",
            "workflow_evidence": "补齐证据缺口",
            "workflow_evidence_description": "按任务补充 primary source、风险和失效证据，再重新生成分析。",
            "quick_examples_eyebrow": "快速开始",
            "quick_examples": "示例入口",
            "quick_examples_description": "不确定怎么开始时，先用示例主题跑一份完整行业分析。",
            "example_primary": "试试 HBM",
            "example_secondary": "试试 存储芯片",
            "example_query_primary": "HBM",
            "example_query_secondary": "存储芯片",
            "run_center_eyebrow": "运行状态",
            "run_center": "运行中心",
            "current_run": "当前运行",
            "run_waiting": "等待启动分析。",
            "run_queued": "分析已排队：",
            "run_queued_generic": "分析已排队...",
            "run_running": "正在运行分析：",
            "run_running_generic": "正在运行分析...",
            "run_complete": "最近完成：",
            "run_complete_generic": "最近运行已完成。",
            "run_failed": "最近运行失败：",
            "run_failed_generic": "最近运行失败。",
            "run_history": "运行历史",
            "run_history_empty": "暂无运行历史。",
            "run_status_completed": "已完成",
            "run_status_failed": "失败",
            "run_status_running": "运行中",
            "run_status_queued": "已排队",
            "run_status_cancelled": "已取消",
            "run_status_unknown": "未知状态",
            "open_run_report": "打开报告",
            "job_detail": "任务详情",
            "cancel_job": "取消任务",
            "rerun_run": "重新生成",
            "run_history_quality": "运行历史质量",
            "run_history_candidates": "运行历史候选标的",
            "open_run_manifest": "打开分析清单",
            "failure_details": "失败原因",
            "unknown_run": "未命名运行",
            "run_polling": "正在刷新运行状态...",
            "run_report_ready": "报告已生成。",
            "open_latest_report": "打开最新报告",
            "analysis_failed_title": "分析生成失败",
            "analysis_failed_recovery": "本次分析没有完成。请检查失败原因，或直接重新生成该分析。",
            "retry_analysis": "重新生成",
            "back_home": "返回首页",
            "run_steps_aria": "分析运行步骤",
            "run_step_resolve": "解析股票池",
            "run_step_resolve_detail": "识别行业、主题、板块或个股对应的候选标的。",
            "run_step_pack": "生成备忘录包",
            "run_step_pack_detail": "检索证据、评分并生成候选报告。",
            "run_step_publish": "发布仪表盘",
            "run_step_publish_detail": "写入可打开的中英文分析页面和报告资产。",
            "run_step_open": "打开报告",
            "run_step_open_detail": "跳转到生成后的分析页面继续复核。",
            "retry_last_run": "重试上次运行",
            "analysis_briefing_eyebrow": "报告摘要",
            "analysis_briefing": "分析简报",
            "analysis_briefing_description": "先用候选排序、覆盖状态和证据缺口判断这份报告应该从哪里读起。",
            "analysis_briefing_empty": "暂无可摘要的候选数据。请先生成分析报告。",
            "top_candidate": "首选候选",
            "coverage_state": "覆盖状态",
            "primary_gap": "主要缺口",
            "next_actions": "下一步动作",
            "open_top_report": "打开首选报告",
            "review_evidence_tasks": "复核证据任务",
            "briefing_reviewable": "可进入人工复核",
            "briefing_needs_evidence": "需要补齐证据",
            "briefing_needs_primary": "需要 primary/fact 来源",
            "briefing_needs_risk": "需要风险证据",
            "primary_gap_present": "Primary evidence 仍需补强",
            "primary_gap_closed": "Primary evidence 已达最低门槛",
            "briefing_action_compare": "先比较候选评分、评级、置信层级和关键短板。",
            "briefing_action_evidence": "优先处理高优先级证据任务，再重新生成分析。",
            "briefing_action_monitor": "继续监控报告库和运行历史，等待新增证据。",
            "briefing_action_verify": "打开首选报告，复核论点、风险和失效条件。",
            "research_action_eyebrow": "研究闭环",
            "research_action_workbench": "研究动作工作台",
            "research_action_description": "把下一步补证、报告复核和可复制检索词集中在一个面板里，方便继续推进研究闭环。",
            "research_action_empty": "暂无可执行研究动作。请先生成分析报告。",
            "action_queue": "动作队列",
            "quality_gap_to_close": "待关闭质量缺口",
            "open_evidence_tasks": "打开证据任务",
            "open_acquisition_queue_action": "打开采集队列",
            "copy_next_research_prompt": "复制下一步研究提示",
            "research_action_sequence": "补证据 → 读交付报告 → 打开采集队列 → 重新生成",
            "research_action_sequence_description": "先关闭影响质量门禁的缺口，再复核交付版报告和采集队列。",
            "research_prompt_description": "复制后可直接用于继续搜索 primary source、风险和失效证据。",
            "decision_workbench_eyebrow": "研究分诊",
            "decision_workbench": "决策工作台",
            "decision_workbench_description": "把候选排序拆成可审计的理由、驱动因子、反证风险和备选解释，帮助用户判断下一步应读哪份报告。",
            "decision_workbench_empty": "暂无候选数据可用于决策分诊。请先生成分析报告。",
            "research_triage_only": "仅用于研究分诊",
            "ranking_rationale": "排序理由",
            "key_drivers": "关键驱动因子",
            "counter_thesis_risks": "反证风险",
            "why_not_other_candidates": "为什么不是其他候选",
            "decision_rationale_body": "{ticker} 当前排在最前，依据是 {score}、{rating}、{confidence}，并且覆盖 {evidence} 条证据、{primary} 条 primary/fact、{risk} 条风险证据。",
            "decision_driver_evidence": "证据覆盖：{evidence} 条证据、{primary} 条 primary/fact、{risk} 条风险证据。",
            "decision_driver_revenue": "收入增速：{value}。",
            "decision_driver_margin": "毛利率：{value}。",
            "decision_driver_valuation": "估值：{value}。",
            "decision_driver_momentum": "价格动量：{value}。",
            "decision_driver_cycle": "周期位置：{value}。",
            "decision_driver_fallback": "当前驱动因子不足，需要先补齐更多来源。",
            "decision_risk_primary_gap": "Primary/fact 来源仍需补强，不能直接提升置信度。",
            "decision_risk_fallback": "反证材料不足，需要继续补采风险和失效条件。",
            "decision_no_runner_up": "当前只有一个候选，无法形成备选对比；请扩展股票池或补齐更多行业候选。",
            "decision_runner_up_body": "下一候选是 {ticker}，评分为 {score}，但仍需处理这些短板：{gaps}。",
            "sort_candidates_by": "按维度排序候选",
            "sort_serenity_score": "Serenity 评分",
            "sort_evidence_coverage": "证据覆盖",
            "sort_primary_coverage": "Primary source 覆盖",
            "sort_risk_coverage": "风险覆盖",
            "sort_explanation": "排序解释会根据当前选择的维度更新。",
            "sort_explanation_prefix": "排序解释",
            "interactive_candidate_ranking": "交互式候选排序",
            "report_quality_eyebrow": "发布门禁",
            "report_quality_gate": "报告质量门禁",
            "report_quality_empty": "暂无候选报告可评估质量。请先生成分析报告。",
            "report_quality_description": "用评分、证据深度、primary source、风险覆盖和关键缺口判断报告是否适合对外发布。",
            "publish_status": "发布状态",
            "quality_status_publishable": "可发布",
            "quality_status_needs_evidence": "需补证据",
            "quality_status_not_publishable": "不可发布",
            "quality_score": "质量评分",
            "quality_score_basis": "基于 Serenity 评分、证据、primary source 和风险覆盖。",
            "quality_candidate_prefix": "当前候选：",
            "evidence_depth": "证据深度",
            "primary_source_depth": "Primary source 深度",
            "risk_coverage_label": "风险覆盖",
            "quality_gaps": "质量缺口",
            "quality_gap_basis": "来自当前 scorecard gaps。",
            "quality_checklist": "质量检查清单",
            "quality_check_evidence_ok": "证据深度达到最低阅读门槛。",
            "quality_check_evidence_gap": "证据深度不足，需要补充更多可追溯来源。",
            "quality_check_primary_ok": "Primary source 深度达到最低门槛。",
            "quality_check_primary_gap": "Primary source 深度不足，需要补充公司公告、监管文件或官方材料。",
            "quality_check_risk_ok": "风险覆盖达到最低门槛。",
            "quality_check_risk_gap": "风险覆盖不足，需要补充反证、失效条件或下行情景证据。",
            "quality_check_gap_ok": "暂无关键 scorecard 缺口。",
            "quality_check_gap_review": "仍需复核这些关键缺口：{gaps}。",
            "saved_workspace_eyebrow": "本地研究状态",
            "saved_research_workspace": "研究工作区",
            "saved_workspace_description": "保存当前报告、候选标记、排序偏好和质量门禁快照，方便下次继续复核。",
            "saved_reports": "已保存报告",
            "candidate_marks": "候选标记",
            "saved_sort_preference": "已保存排序偏好",
            "quality_gate_snapshot": "质量门禁快照",
            "save_workspace": "保存工作区",
            "clear_workspace": "清空工作区",
            "workspace_not_saved": "尚未保存此页面的研究状态。",
            "workspace_last_saved": "最近保存：",
            "workspace_no_saved_reports": "暂无已保存报告。点击保存工作区后会记录当前报告入口。",
            "workspace_no_candidate_marks": "暂无候选标记。点击保存工作区后会记录当前候选排序。",
            "workspace_mark_tracking": "跟踪中",
            "saved_sort_description": "跟随决策工作台当前排序维度，并在保存后自动更新。",
            "quality_snapshot_description": "记录当前发布状态与质量评分，便于下次继续补证据。",
            "project_library_eyebrow": "项目跟踪",
            "research_project_library": "研究项目库",
            "project_library_description": "把当前行业、主题、板块或个股分析保存为可跟踪项目，并在本地维护复核状态。",
            "save_as_project": "保存为项目",
            "clear_projects": "清空项目",
            "project_library_count": "已保存项目",
            "project_library_empty": "暂无已保存项目。生成分析后点击保存为项目，即可在这里跟踪后续复核状态。",
            "project_filter_label": "按状态筛选项目",
            "all_project_statuses": "全部项目状态",
            "project_comparison_summary": "项目对比摘要",
            "project_total_projects": "项目总数",
            "project_average_quality": "平均质量评分",
            "project_evidence_backlog": "证据待办",
            "project_delivered_projects": "已交付项目",
            "project_search_label": "搜索已保存项目",
            "project_search_placeholder": "按主题、候选、状态、缺口搜索",
            "project_sort_label": "排序已保存项目",
            "project_sort_recent": "最近保存",
            "project_sort_activity": "最活跃",
            "project_sort_quality": "质量评分最高",
            "project_sort_topic": "主题 A-Z",
            "project_tags": "项目标签",
            "all_project_tags": "全部项目标签",
            "project_tag_needs_evidence": "标签：待补证据",
            "project_tag_high_quality": "标签：高质量",
            "project_tag_delivered": "标签：已交付",
            "project_next_action_filter_label": "项目下一步动作",
            "all_project_next_actions": "全部下一步动作",
            "project_next_action_collect_evidence_projects": "补齐证据项目",
            "project_next_action_review_report_projects": "复核报告项目",
            "project_next_action_rerun_analysis_projects": "重跑分析项目",
            "project_next_action_archive_projects": "归档项目",
            "next_action_queue": "下一步动作队列",
            "queue_by_workflow_step": "按工作流步骤统计队列",
            "filter_to_collect_evidence": "筛选补齐证据",
            "filter_to_review_reports": "筛选复核报告",
            "filter_to_rerun_analysis": "筛选重跑分析",
            "filter_to_archive_projects": "筛选归档项目",
            "project_queue_handoff": "项目队列交接",
            "copy_project_queue_handoff": "复制队列交接",
            "project_queue_handoff_copied": "队列交接已复制",
            "filtered_project_handoff": "筛选项目交接",
            "copy_filtered_handoff": "复制筛选交接",
            "filtered_handoff_copied": "筛选交接已复制",
            "filtered_handoff_preview": "筛选交接预览",
            "filtered_item_count": "筛选条目数",
            "research_only_queue_handoff": "仅供研究的队列交接",
            "queue_handoff_action": "队列交接动作",
            "queue_handoff_preview": "队列交接预览",
            "review_handoff_before_copying": "复制前复核交接内容",
            "handoff_item_count": "交接条目数",
            "project_owner_queue": "项目负责人队列",
            "project_owner_queue_description": "按负责人角色查看待处理项目",
            "project_owner_filter_label": "按负责人筛选",
            "all_project_owners": "全部负责人",
            "project_owner_unassigned": "未分配负责人",
        "project_owner_evidence": "证据负责人",
        "project_owner_reviewer": "报告复核人",
        "project_owner_rerun": "重跑负责人",
            "project_owner_archive": "归档负责人",
            "assign_project_owner": "分配项目负责人",
            "review_event_owner_changed": "负责人已更新",
            "project_activity_filter": "项目活动筛选",
            "all_activity_states": "全部活动状态",
            "has_activity": "有活动",
            "no_activity": "无活动",
            "project_library_no_matches": "没有匹配的项目。请调整搜索、状态或标签筛选。",
            "historical_comparison_matrix": "历史对比矩阵",
            "historical_comparison_description": "选择多个已保存项目，横向比较主题、首选候选、质量、证据缺口、状态与报告入口。",
            "select_for_comparison": "选择对比",
            "compare_selected_projects": "对比已选项目",
            "copy_comparison_brief": "复制对比简报",
            "comparison_brief_copied": "已复制对比简报",
            "research_only_comparison_brief": "仅供研究的对比简报",
            "comparison_brief_boundary": "仅汇总研究元数据，不包含买入、卖出、持有、目标价或仓位建议。",
            "project_comparison_empty": "请选择项目进行对比。",
            "comparison_topic": "对比主题",
            "comparison_top_candidate": "首选候选",
            "comparison_quality": "质量评分",
            "comparison_gap": "证据缺口",
            "comparison_status": "项目状态",
            "comparison_report": "报告入口",
            "project_status": "项目状态",
            "project_status_pending_evidence": "待补证据",
            "project_status_reviewable": "可复核",
            "project_status_delivered": "已交付",
            "project_status_needs_rerun": "需重跑",
            "project_quality_label": "质量",
            "project_gap_label": "缺口",
            "open_project_report": "打开项目报告",
            "project_detail_drawer": "项目详情抽屉",
            "review_project": "复核项目",
            "project_review_panel": "项目复核面板",
            "project_detail_description": "在不离开当前页面的情况下复核项目质量、缺口、状态和下一步动作。",
            "project_detail_quality": "项目详情质量",
            "project_detail_gap": "项目详情缺口",
            "project_detail_status": "项目详情状态",
            "next_review_action": "下一步复核动作",
            "open_report_from_detail": "从详情打开报告",
            "project_detail_empty": "请选择一个已保存项目查看详情。",
            "project_detail_boundary": "仅用于研究复核，不包含交易建议。",
            "project_review_action_delivered": "确认交付状态并归档复核记录。",
            "project_review_action_rerun": "重新生成分析并复核失败原因。",
            "project_review_action_gap": "优先关闭证据缺口后再复核报告。",
            "project_review_action_report": "打开报告并复核论点、风险和失效条件。",
            "project_review_action_panel": "项目复核操作面板",
            "recommended_review_actions": "建议复核动作",
            "close_evidence_gap": "关闭证据缺口",
            "rerun_analysis": "重新生成分析",
            "mark_delivered": "标记已交付",
            "open_report_from_action_panel": "从操作面板打开报告",
            "action_logged": "动作已记录",
            "evidence_gap_linked_task": "证据缺口关联任务",
            "jump_to_evidence_task": "跳转到证据任务",
            "rerun_with_project_context": "带项目上下文重跑",
            "quality_after_rerun": "重跑后质量",
            "project_review_loop_idle": "选择一个复核动作以查看证据任务或重跑质量上下文。",
            "evidence_verification_rerun_loop": "证据验证重跑闭环",
            "auto_rerun_after_verification": "验证后自动重跑",
            "rerun_verified_task": "重跑已验证任务",
            "quality_delta_after_rerun": "重跑后质量变化",
            "project_evidence_audit_log": "项目证据审计日志",
            "evidence_contribution_history": "证据贡献历史",
            "verified_task_audit_trail": "已验证任务审计轨迹",
            "quality_contribution": "质量贡献",
            "latest_quality_delta": "最新质量变化",
            "latest_evidence_impact": "最新证据影响",
            "evidence_progress": "证据进度",
            "evidence_progress_empty": "暂无证据任务进度。",
            "workflow_next_step": "工作流下一步",
            "project_next_action_review_report": "复核报告",
            "project_next_action_review_reason": "证据任务已完成；复核论点、风险和失效条件",
            "quality_delta_summary_empty": "暂无可展示质量变化。",
            "project_evidence_audit_empty": "暂无证据贡献记录。验证任务或重跑分析后会在这里显示。",
            "project_review_timeline": "项目复核时间线",
            "review_event_history": "复核事件历史",
            "collaboration_event_view": "协作事件视图",
            "filter_review_events": "筛选复核事件",
            "all_review_events": "全部复核事件",
            "status_events": "状态事件",
            "owner_events": "负责人事件",
            "detail_events": "详情事件",
            "comparison_events": "对比事件",
            "queue_handoff_events": "队列交接事件",
            "latest_project_activity": "最新项目活动",
            "project_activity_summary": "项目活动摘要",
            "activity_count": "活动次数",
            "latest_activity": "最新活动",
            "no_activity_yet": "暂无活动",
            "project_review_timeline_empty": "暂无复核事件。",
            "log_review_event": "记录复核事件",
            "server_backed_review_event_log": "服务端复核事件日志",
            "review_event_status_changed": "状态已更新",
            "review_event_detail_opened": "已打开详情",
            "review_event_comparison_copied": "已复制对比简报",
            "review_event_queue_handoff_copied": "已复制队列交接",
            "deliverable_report_eyebrow": "交付物",
            "deliverable_research_report": "可交付研究报告",
            "deliverable_report_description": "把当前分析压缩成可打开、可打印、可保存 PDF 的中文研究简报，便于对外复核或内部流转。",
            "export_ready_brief": "交付版摘要",
            "open_deliverable_report": "打开交付版报告",
            "print_save_pdf": "打印 / 保存 PDF",
            "share_handoff": "分享交接",
            "copy_report_link": "复制报告链接",
            "copy_manifest_link": "复制清单链接",
            "copied_link": "已复制链接",
            "reader_toolbar": "阅读器工具栏",
            "reader_outline": "报告目录",
            "report_highlights": "报告重点",
            "jump_to_section": "跳转章节",
            "current_report_link": "当前报告链接",
            "copy_current_link": "复制当前链接",
            "copy_handoff_bundle": "复制交接清单",
            "handoff_bundle_copied": "已复制交接清单",
            "delivery_package_eyebrow": "交付包",
            "delivery_package": "报告交付包",
            "delivery_package_description": "在一个面板中打开或复制交付报告、分析清单、覆盖矩阵和证据采集队列。",
            "delivery_quality_summary": "交付质量摘要",
            "research_only_package": "仅供研究",
            "remaining_gaps": "剩余缺口",
            "delivery_quality_no_remaining_gaps": "暂无剩余缺口",
            "delivery_package_deliverable_description": "适合对外流转或内部复核的中文研究摘要。",
            "delivery_package_manifest_description": "机器可读的输入解析、候选标的、质量快照和报告链接。",
            "delivery_package_coverage_description": "核对维护股票池中仍缺哪些 primary/fact、风险或 ticker 证据。",
            "delivery_package_queue_description": "继续补齐 primary source、风险和失效证据的执行队列。",
            "deliverable_report_type": "交付版报告",
            "deliverable_brief_description": "包含研究主题、候选排序、质量门禁、证据缺口和下一步动作。",
            "deliverable_contents": "报告内容",
            "deliverable_contents_summary": "摘要、排序、门禁、缺口",
            "deliverable_contents_description": "Markdown 文件可在右侧阅读器打开，也可用浏览器打印为 PDF。",
            "report_library_eyebrow": "报告库",
            "recent_reports": "最近报告",
            "recent_reports_description": "最近生成的行业、主题和个股分析会保存在这里，方便用户回看和继续比较。",
            "report_workbench": "报告工作台",
            "report_workbench_description": "按报告类型筛选，先在阅读器打开生成分析或运营报告，也可按需打开完整页面。",
            "report_type_label": "按报告类型筛选",
            "all_report_types": "全部报告类型",
            "generated_analysis_reports": "生成的分析",
            "operational_report_type": "运营报告",
            "open_in_reader": "在阅读器打开",
            "open_full_page": "打开完整页面",
            "operational_reports": "运营报告",
            "coverage_matrix_title": "覆盖矩阵",
            "coverage_matrix_description": "查看维护股票池中哪些行业候选标的缺少 primary/fact、风险或直接 ticker 证据。",
            "open_coverage_matrix": "打开覆盖矩阵",
            "acquisition_queue_title": "证据采集队列",
            "acquisition_queue_description": "查看当前分析还需要补采哪些 primary source、风险证据和失效证据。",
            "open_acquisition_queue": "打开采集队列",
            "analysis_manifest_title": "分析清单",
            "analysis_manifest_description": "查看本次分析的输入解析、候选标的、质量快照、报告链接和研究边界。",
            "open_analysis_manifest": "打开分析清单",
            "evidence_tasks_eyebrow": "下一步研究动作",
            "evidence_tasks": "证据任务",
            "evidence_tasks_description": "把采集队列中的高优先级任务直接放在页面上，方便用户补齐 primary source、风险和失效证据。",
            "no_evidence_tasks": "暂无待处理证据任务。可打开采集队列复核覆盖矩阵，或继续阅读候选报告。",
            "evidence_tasks_priority": "优先级",
            "source_target": "来源目标",
            "task_rationale": "补证原因",
            "task_acceptance_criteria": "验收标准",
            "task_after_import": "导入后动作",
            "copy_search_prompt": "复制搜索提示",
            "copied_prompt": "已复制",
            "task_status": "任务状态",
            "task_to_collect": "待采集",
            "task_collected": "已采集",
            "task_verified": "已验证",
            "add_evidence": "补充证据",
            "source_title_label": "来源标题",
            "source_url_label": "来源链接",
            "source_excerpt_label": "来源摘录",
            "submit_evidence": "提交并重新分析",
            "evidence_imported": "补充证据已纳入",
            "import_helper": "请粘贴一段能直接支撑该任务的来源摘录。",
            "import_required": "必填：来源标题、来源链接和可追溯摘录。",
            "import_loading": "正在提交证据...",
            "imported_evidence": "已导入证据",
            "no_imported_evidence": "尚未从此任务导入证据。",
            "resolved": "已解决",
            "resolved_by_imported_evidence": "已由导入证据解决",
            "import_impact": "导入影响",
            "closed_gap_label": "已关闭缺口",
            "quality_gate_impact": "质量门禁影响：已重新生成分析；请复核更新后的发布状态和质量评分。",
            "remaining_evidence_work": "剩余补证工作：发布前请继续复核下一个可见证据任务。",
            "quality_before_import": "导入前质量评分",
            "quality_after_import": "导入后质量评分",
            "quality_score_change": "质量评分变化",
            "quality_delta_unavailable": "待对比",
            "quality_delta_points": "{delta:+d} 分",
            "import_failed_title": "证据导入失败",
            "import_failed_recovery": "请返回上一页修正来源标题、来源链接和来源摘录后重试。",
            "resolved_gap_prefix": "已解决缺口：",
            "open_report": "打开报告",
            "canonical_theme": "标准主题",
            "candidate_tickers": "候选标的",
            "no_recent_reports": "还没有生成历史报告。输入行业、主题或个股并点击启动分析后，会在这里出现。",
            "search_label": "搜索股票代码、标记、备忘录文本或来源声明",
            "search_placeholder": "试试 SIVE、risk、primary source、NVDA...",
            "status": "状态",
            "all_statuses": "全部状态",
            "reset_filters": "重置筛选",
            "showing_all": "显示全部仪表盘项目。",
            "showing": "显示",
            "of": "/",
            "dashboard_items": "个仪表盘项目。",
            "readiness_description": "状态基于证据深度、primary source 覆盖、风险覆盖和集中度检查。",
            "generated_research": "已生成研究",
            "memo_description": "打开单个备忘录查看完整评分卡、投资论点、怀疑者复核和失效条件。",
            "comparison_eyebrow": "横向复核",
            "candidate_comparison": "候选对比",
            "candidate_comparison_description": "按评分、评级、置信层级、关键短板和证据覆盖横向比较候选标的。",
            "score": "评分",
            "rating": "评级",
            "confidence": "置信层级",
            "key_gaps": "关键短板",
            "revenue_growth": "收入增速",
            "gross_margin": "毛利率",
            "valuation": "估值",
            "momentum": "价格动量",
            "cycle_position": "周期位置",
            "analyst_preview": "分析师预览",
            "featured_preview": "精选备忘录预览",
            "preview_description": "短预览帮助用户在打开完整备忘录前快速筛选研究包。",
            "traceability": "可追溯性",
            "evidence_provenance": "证据溯源",
            "provenance_description": "Primary evidence 会展示声明文本和摘录，方便用户审计备忘录为何使用该来源。",
            "research_only": "仅供研究。",
            "disclaimer": "本仪表盘不是投资建议，不推荐任何交易；任何资金决策前都需要独立验证。",
            "no_readiness": "没有找到就绪状态数据。",
            "ticker": "股票代码",
            "evidence_count": "证据",
            "risk": "风险",
            "flags": "标记",
            "no_memos": "没有找到备忘录包数据。",
            "open_memo": "打开备忘录",
            "view_report": "查看报告",
            "report_reader": "报告阅读器",
            "select_report": "选择一份报告",
            "close_report": "关闭报告",
            "drawer_empty": "点击任一报告按钮后，会在这里展开完整备忘录。",
            "loading_report": "正在载入报告...",
            "report_load_failed": "报告载入失败。请检查本地服务是否能访问该备忘录文件。",
            "not_generated": "未生成",
            "primary": "Primary",
            "serenity_rating": "Serenity 评级",
            "no_previews": "没有找到备忘录预览。",
            "open_full_memo": "打开完整备忘录",
            "no_thesis": "没有找到论点摘要。",
            "source_coverage": "来源覆盖",
            "no_coverage": "没有找到覆盖摘要。",
            "risks": "风险",
            "invalidation_conditions": "失效条件",
            "no_sources": "没有找到 primary evidence 溯源。",
            "used_in": "用于",
            "no_claim": "没有找到声明文本。",
            "no_excerpt": "没有提供来源摘录。",
        }

    return {
        "language": "en",
        "title_suffix": "Local Research Dashboard",
        "skip": "Skip to main content",
        "eyebrow": "Local research dashboard",
        "readiness": "Readiness",
        "memo_pack": "Memo Pack",
        "evidence": "Evidence",
        "alternate_language": "中文",
        "overview": "CPO pack overview",
        "hero_title": "Investment research pack, cleaned into one product view.",
        "hero_subtitle": "Review candidate readiness, memo coverage, risk checks, and source provenance before reading the detailed Markdown memos.",
        "research_question": "Research question",
        "pack_status": "Pack status",
        "ready_memos_lower": "ready memos",
        "skipped_summary": "skipped or needs-review candidate(s).",
        "primary_summary": "primary/fact item(s) and",
        "risk_summary": "risk item(s) are represented.",
        "total_evidence": "Total Evidence",
        "ready_memos": "Ready Memos",
        "primary_fact": "Primary / Fact",
        "risk_items": "Risk Items",
        "launch_aria": "Launch a new industry theme analysis",
        "launch_label": "Enter a new industry theme",
        "launch_placeholder": "For example: memory chips, HBM, semiconductor equipment",
        "launch_button": "Start analysis",
        "launch_loading": "Generating analysis...",
        "launch_help": "This generates a new theme research pack from the current local evidence base. The search box only filters the current page.",
        "preview_scope": "Preview analysis scope",
        "confirm_generate": "Confirm and generate",
        "input_preview_eyebrow": "Pre-analysis confirmation",
        "input_preview": "Input Preview",
        "detected_input_type": "Detected input type",
        "evidence_coverage": "Evidence coverage",
        "candidate_coverage_detail": "Candidate coverage details",
        "candidate_coverage_empty": "No candidate coverage details yet",
        "preflight_evidence_tasks": "Preflight evidence actions",
        "preflight_evidence_tasks_empty": "No preflight evidence actions yet",
        "copy_evidence_gap_prompt": "Copy evidence prompt",
        "open_evidence_import_handoff": "Open evidence import",
        "expected_outputs": "Expected outputs",
        "expected_outputs_value": "Report, comparison table, evidence tasks, and operational reports",
        "preview_waiting": "Waiting for input",
        "preview_ready": "Analysis scope preview is ready. Confirm to generate the report.",
        "preview_resolving": "Resolving analysis scope with the backend resolver...",
        "preview_fallback": "Preview unavailable; using local fallback.",
        "preview_source": "Resolver source",
        "preview_source_backend": "Backend-backed resolver",
        "preview_source_local": "Local fallback resolver",
        "intent_theme": "Theme",
        "intent_industry": "Industry",
        "intent_sector": "Sector",
        "intent_ticker": "Ticker",
        "coverage_evidence_items": "evidence items",
        "coverage_primary_items": "primary/fact items",
        "coverage_risk_items": "risk items",
        "semiconductor_equipment_theme": "semiconductor equipment",
        "workbench_eyebrow": "Product workbench",
        "research_workflow": "Research Workflow",
        "workbench_description": "Start with an industry, sector, theme, or ticker, then move through Serenity candidate comparison, report reading, evidence collection, and review.",
        "workflow_scope": "Define scope",
        "workflow_scope_description": "Enter an industry, theme, sector, or ticker so the system can resolve candidates and evidence.",
        "workflow_compare": "Compare candidates",
        "workflow_compare_description": "Use score, rating, confidence, key gaps, and coverage to triage the candidate set.",
        "workflow_reports": "Read reports",
        "workflow_reports_description": "Open memos, coverage matrices, and acquisition queues in the right-side report reader.",
        "workflow_evidence": "Close evidence gaps",
        "workflow_evidence_description": "Add primary-source, risk, and invalidation evidence, then rerun the analysis.",
        "quick_examples_eyebrow": "Quick start",
        "quick_examples": "Example launches",
        "quick_examples_description": "If you are not sure where to start, run a complete industry analysis from an example topic.",
        "example_primary": "Try HBM",
        "example_secondary": "Try memory chips",
        "example_query_primary": "HBM",
        "example_query_secondary": "memory chips",
        "run_center_eyebrow": "Run status",
        "run_center": "Run Center",
        "current_run": "Current run",
        "run_waiting": "Waiting for an analysis request.",
        "run_queued": "Queued analysis:",
        "run_queued_generic": "Analysis queued...",
        "run_running": "Running analysis:",
        "run_running_generic": "Running analysis...",
        "run_complete": "Recently completed:",
        "run_complete_generic": "Recent run completed.",
        "run_failed": "Recent run failed:",
        "run_failed_generic": "Recent run failed.",
        "run_history": "Run History",
        "run_history_empty": "No run history yet.",
        "run_status_completed": "Completed",
        "run_status_failed": "Failed",
        "run_status_running": "Running",
        "run_status_queued": "Queued",
        "run_status_cancelled": "Cancelled",
        "run_status_unknown": "Unknown status",
        "open_run_report": "Open report",
        "job_detail": "Job detail",
        "cancel_job": "Cancel job",
        "rerun_run": "Rerun",
        "run_history_quality": "Quality in run history",
        "run_history_candidates": "Candidate tickers in run history",
        "open_run_manifest": "Open analysis manifest",
        "failure_details": "Failure details",
        "unknown_run": "Untitled run",
        "run_polling": "Polling run status...",
        "run_report_ready": "Report ready.",
        "open_latest_report": "Open latest report",
        "analysis_failed_title": "Analysis generation failed",
        "analysis_failed_recovery": "This analysis did not complete. Review the failure details or rerun the analysis.",
        "retry_analysis": "Rerun analysis",
        "back_home": "Back to home",
        "run_steps_aria": "Analysis run steps",
        "run_step_resolve": "Resolve universe",
        "run_step_resolve_detail": "Map the industry, theme, sector, or ticker to candidate companies.",
        "run_step_pack": "Build memo pack",
        "run_step_pack_detail": "Retrieve evidence, score candidates, and generate report drafts.",
        "run_step_publish": "Publish dashboard",
        "run_step_publish_detail": "Write the bilingual analysis page and report assets.",
        "run_step_open": "Open report",
        "run_step_open_detail": "Navigate to the generated analysis page for review.",
        "retry_last_run": "Retry last run",
        "analysis_briefing_eyebrow": "Report summary",
        "analysis_briefing": "Analysis Briefing",
        "analysis_briefing_description": "Use candidate rank, coverage state, and evidence gaps to decide where to start reading.",
        "analysis_briefing_empty": "No candidate data is available yet. Generate an analysis report first.",
        "top_candidate": "Top candidate",
        "coverage_state": "Coverage state",
        "primary_gap": "Primary gap",
        "next_actions": "Next actions",
        "open_top_report": "Open top report",
        "review_evidence_tasks": "Review evidence tasks",
        "briefing_reviewable": "Ready for human review",
        "briefing_needs_evidence": "Needs evidence collection",
        "briefing_needs_primary": "Needs primary/fact source",
        "briefing_needs_risk": "Needs risk evidence",
        "primary_gap_present": "Primary evidence still needs work",
        "primary_gap_closed": "Primary evidence meets the minimum gate",
        "briefing_action_compare": "Compare candidate score, rating, confidence, and key gaps first.",
        "briefing_action_evidence": "Resolve high-priority evidence tasks, then rerun the analysis.",
        "briefing_action_monitor": "Monitor the report library and run history while waiting for new evidence.",
        "briefing_action_verify": "Open the top report and review thesis, risks, and invalidation conditions.",
        "research_action_eyebrow": "Research loop",
        "research_action_workbench": "Research Action Workbench",
        "research_action_description": "Group the next evidence, report-review, queue, and copy-prompt actions in one compact place.",
        "research_action_empty": "No research actions are available yet. Generate an analysis report first.",
        "action_queue": "Action queue",
        "quality_gap_to_close": "Quality gap to close",
        "open_evidence_tasks": "Open evidence tasks",
        "open_acquisition_queue_action": "Open acquisition queue",
        "copy_next_research_prompt": "Copy next research prompt",
        "research_action_sequence": "Collect evidence → read deliverable → open acquisition queue → rerun",
        "research_action_sequence_description": "Close the quality-gate gap first, then review the deliverable and acquisition queue.",
        "research_prompt_description": "Copy this prompt to continue searching for primary sources, risks, and invalidation evidence.",
        "decision_workbench_eyebrow": "Research triage",
        "decision_workbench": "Decision Workbench",
        "decision_workbench_description": "Break candidate ranking into auditable rationale, drivers, counter-thesis risks, and runner-up context before reading deeper.",
        "decision_workbench_empty": "No candidate data is available for decision triage yet. Generate an analysis report first.",
        "research_triage_only": "Research triage only",
        "ranking_rationale": "Ranking rationale",
        "key_drivers": "Key drivers",
        "counter_thesis_risks": "Counter-thesis risks",
        "why_not_other_candidates": "Why not other candidates",
        "decision_rationale_body": "{ticker} ranks first based on {score}, {rating}, {confidence}, with {evidence} evidence items, {primary} primary/fact items, and {risk} risk items.",
        "decision_driver_evidence": "Evidence coverage: {evidence} evidence items, {primary} primary/fact items, {risk} risk items.",
        "decision_driver_revenue": "Revenue growth: {value}.",
        "decision_driver_margin": "Gross margin: {value}.",
        "decision_driver_valuation": "Valuation: {value}.",
        "decision_driver_momentum": "Price momentum: {value}.",
        "decision_driver_cycle": "Cycle position: {value}.",
        "decision_driver_fallback": "Current drivers are thin; collect more sources before raising confidence.",
        "decision_risk_primary_gap": "Primary/fact sourcing still needs work before confidence can be raised.",
        "decision_risk_fallback": "Counter-evidence is thin; collect more risk and invalidation evidence.",
        "decision_no_runner_up": "Only one candidate is available, so there is no runner-up comparison yet. Expand the universe or add more candidates.",
        "decision_runner_up_body": "The next candidate is {ticker} at {score}, but these gaps still need work: {gaps}.",
        "sort_candidates_by": "Sort candidates by",
        "sort_serenity_score": "Serenity score",
        "sort_evidence_coverage": "Evidence coverage",
        "sort_primary_coverage": "Primary source coverage",
        "sort_risk_coverage": "Risk coverage",
        "sort_explanation": "Sort explanation updates when you choose a ranking dimension.",
        "sort_explanation_prefix": "Sort explanation",
        "interactive_candidate_ranking": "Interactive candidate ranking",
        "report_quality_eyebrow": "Publishing gate",
        "report_quality_gate": "Report Quality Gate",
        "report_quality_empty": "No candidate report is available for quality review yet. Generate an analysis report first.",
        "report_quality_description": "Use score, evidence depth, primary sources, risk coverage, and key gaps to decide whether the report is ready to publish.",
        "publish_status": "Publish status",
        "quality_status_publishable": "Publishable",
        "quality_status_needs_evidence": "Needs evidence",
        "quality_status_not_publishable": "Not publishable",
        "quality_score": "Quality score",
        "quality_score_basis": "Based on Serenity score, evidence, primary sources, and risk coverage.",
        "quality_candidate_prefix": "Current candidate:",
        "evidence_depth": "Evidence depth",
        "primary_source_depth": "Primary source depth",
        "risk_coverage_label": "Risk coverage",
        "quality_gaps": "Quality gaps",
        "quality_gap_basis": "From current scorecard gaps.",
        "quality_checklist": "Quality checklist",
        "quality_check_evidence_ok": "Evidence depth meets the minimum reading gate.",
        "quality_check_evidence_gap": "Evidence depth is thin; add more traceable sources.",
        "quality_check_primary_ok": "Primary source depth meets the minimum gate.",
        "quality_check_primary_gap": "Primary source depth is thin; add company releases, filings, or official materials.",
        "quality_check_risk_ok": "Risk coverage meets the minimum gate.",
        "quality_check_risk_gap": "Risk coverage is thin; add counter-evidence, invalidation conditions, or downside evidence.",
        "quality_check_gap_ok": "No key scorecard gaps are currently flagged.",
        "quality_check_gap_review": "Review these key gaps before publishing: {gaps}.",
        "saved_workspace_eyebrow": "Local research state",
        "saved_research_workspace": "Saved Research Workspace",
        "saved_workspace_description": "Save the current report links, candidate marks, sort preference, and quality gate snapshot so users can resume review later.",
        "saved_reports": "Saved reports",
        "candidate_marks": "Candidate marks",
        "saved_sort_preference": "Saved sort preference",
        "quality_gate_snapshot": "Quality gate snapshot",
        "save_workspace": "Save workspace",
        "clear_workspace": "Clear workspace",
        "workspace_not_saved": "This page research state has not been saved yet.",
        "workspace_last_saved": "Last saved:",
        "workspace_no_saved_reports": "No saved reports yet. Save workspace to capture the current report links.",
        "workspace_no_candidate_marks": "No candidate marks yet. Save workspace to capture the current candidate order.",
        "workspace_mark_tracking": "Tracking",
        "saved_sort_description": "Follows the current Decision Workbench sort dimension and updates after saving.",
        "quality_snapshot_description": "Captures the current publish status and quality score for follow-up evidence work.",
        "project_library_eyebrow": "Project tracking",
        "research_project_library": "Research Project Library",
        "project_library_description": "Server-backed project library for saving the current industry, theme, sector, or ticker analysis as a trackable research project.",
        "save_as_project": "Save as project",
        "clear_projects": "Clear projects",
        "project_library_count": "Saved projects",
        "project_library_empty": "No saved projects yet. Generate an analysis, then save it as a project to track review status here.",
        "project_filter_label": "Filter projects by status",
        "all_project_statuses": "All project statuses",
        "project_comparison_summary": "Project comparison summary",
        "project_total_projects": "Total projects",
        "project_average_quality": "Average quality score",
        "project_evidence_backlog": "Evidence backlog",
        "project_delivered_projects": "Delivered projects",
        "project_search_label": "Search saved projects",
        "project_search_placeholder": "Search by topic, candidate, status, or gap",
        "project_sort_label": "Sort saved projects",
        "project_sort_recent": "Most recent",
        "project_sort_activity": "Most active",
        "project_sort_quality": "Highest quality",
        "project_sort_topic": "Topic A-Z",
        "project_tags": "Project tags",
        "all_project_tags": "All project tags",
        "project_tag_needs_evidence": "Tag: needs evidence",
        "project_tag_high_quality": "Tag: high quality",
        "project_tag_delivered": "Tag: delivered",
        "project_next_action_filter_label": "Project next action",
        "all_project_next_actions": "All next actions",
        "project_next_action_collect_evidence_projects": "Collect evidence projects",
        "project_next_action_review_report_projects": "Review report projects",
        "project_next_action_rerun_analysis_projects": "Rerun analysis projects",
        "project_next_action_archive_projects": "Archive projects",
        "next_action_queue": "Next-action queue",
        "queue_by_workflow_step": "Queue by workflow step",
        "filter_to_collect_evidence": "Filter to collect evidence",
        "filter_to_review_reports": "Filter to review reports",
        "filter_to_rerun_analysis": "Filter to rerun analysis",
        "filter_to_archive_projects": "Filter to archive projects",
        "project_queue_handoff": "Project queue handoff",
        "copy_project_queue_handoff": "Copy queue handoff",
        "project_queue_handoff_copied": "Queue handoff copied",
        "filtered_project_handoff": "Filtered project handoff",
        "copy_filtered_handoff": "Copy filtered handoff",
        "filtered_handoff_copied": "Filtered handoff copied",
        "filtered_handoff_preview": "Filtered handoff preview",
        "filtered_item_count": "Filtered item count",
        "research_only_queue_handoff": "Research-only queue handoff",
        "queue_handoff_action": "Queue handoff action",
        "queue_handoff_preview": "Queue handoff preview",
        "review_handoff_before_copying": "Review handoff before copying",
        "handoff_item_count": "Handoff item count",
        "project_owner_queue": "Project owner queue",
        "project_owner_queue_description": "View pending projects by workflow owner role",
        "project_owner_filter_label": "Filter by owner",
        "all_project_owners": "All owners",
        "project_owner_unassigned": "Unassigned owner",
        "project_owner_evidence": "Evidence owner",
        "project_owner_reviewer": "Report reviewer",
        "project_owner_rerun": "Rerun owner",
        "project_owner_archive": "Archive owner",
        "assign_project_owner": "Assign project owner",
        "review_event_owner_changed": "Owner changed",
        "project_activity_filter": "Project activity filter",
        "all_activity_states": "All activity states",
        "has_activity": "Has activity",
        "no_activity": "No activity",
        "project_library_no_matches": "No matching projects. Adjust search, status, or tag filters.",
        "historical_comparison_matrix": "Historical comparison matrix",
        "historical_comparison_description": "Select saved projects to compare topic, top candidate, quality, evidence gap, status, and report access side by side.",
        "select_for_comparison": "Select for comparison",
        "compare_selected_projects": "Compare selected projects",
        "copy_comparison_brief": "Copy comparison brief",
        "comparison_brief_copied": "Comparison brief copied",
        "research_only_comparison_brief": "Research-only comparison brief",
        "comparison_brief_boundary": "Summarizes research metadata only; no buy, sell, hold, target price, or position-sizing guidance.",
        "project_comparison_empty": "Select projects to compare.",
        "comparison_topic": "Comparison topic",
        "comparison_top_candidate": "Comparison top candidate",
        "comparison_quality": "Comparison quality",
        "comparison_gap": "Comparison gap",
        "comparison_status": "Comparison status",
        "comparison_report": "Comparison report",
        "project_status": "Project status",
        "project_status_pending_evidence": "Pending evidence",
        "project_status_reviewable": "Reviewable",
        "project_status_delivered": "Delivered",
        "project_status_needs_rerun": "Needs rerun",
        "project_quality_label": "Quality",
        "project_gap_label": "Gap",
        "open_project_report": "Open project report",
        "project_detail_drawer": "Project detail drawer",
        "review_project": "Review project",
        "project_review_panel": "Project review panel",
        "project_detail_description": "Review project quality, gap, status, and next action without leaving the current page.",
        "project_detail_quality": "Project detail quality",
        "project_detail_gap": "Project detail gap",
        "project_detail_status": "Project detail status",
        "next_review_action": "Next review action",
        "open_report_from_detail": "Open report from detail",
        "project_detail_empty": "Select a saved project to review details.",
        "project_detail_boundary": "Research review only; no trade recommendation is included.",
        "project_review_action_delivered": "Confirm delivery state and archive the review trail.",
        "project_review_action_rerun": "Rerun the analysis and review the failure reason.",
        "project_review_action_gap": "Close the evidence gap before reviewing the report again.",
        "project_review_action_report": "Open the report and review thesis, risks, and invalidation conditions.",
        "project_review_action_panel": "Project review action panel",
        "recommended_review_actions": "Recommended review actions",
        "close_evidence_gap": "Close evidence gap",
        "rerun_analysis": "Rerun analysis",
        "mark_delivered": "Mark delivered",
        "open_report_from_action_panel": "Open report from action panel",
        "action_logged": "Action logged",
        "evidence_gap_linked_task": "Evidence gap linked task",
        "jump_to_evidence_task": "Jump to evidence task",
        "rerun_with_project_context": "Rerun with project context",
        "quality_after_rerun": "Quality after rerun",
        "project_review_loop_idle": "Choose a review action to see the evidence task or rerun quality context.",
        "evidence_verification_rerun_loop": "Evidence verification rerun loop",
        "auto_rerun_after_verification": "Auto-rerun after verification",
        "rerun_verified_task": "Rerun verified task",
        "quality_delta_after_rerun": "Quality delta after rerun",
        "project_evidence_audit_log": "Project evidence audit log",
        "evidence_contribution_history": "Evidence contribution history",
        "verified_task_audit_trail": "Verified task audit trail",
        "quality_contribution": "Quality contribution",
        "latest_quality_delta": "Latest quality delta",
        "latest_evidence_impact": "Latest evidence impact",
        "evidence_progress": "Evidence progress",
        "evidence_progress_empty": "No evidence task progress yet.",
        "workflow_next_step": "Workflow next step",
        "project_next_action_review_report": "Review report",
        "project_next_action_review_reason": "Evidence tasks are complete; review thesis, risks, and invalidation conditions",
        "quality_delta_summary_empty": "No quality delta available yet.",
        "project_evidence_audit_empty": "No evidence contribution records yet. Verified tasks and reruns will appear here.",
        "project_review_timeline": "Project review timeline",
        "review_event_history": "Review event history",
        "collaboration_event_view": "Collaboration event view",
        "filter_review_events": "Filter review events",
        "all_review_events": "All review events",
        "status_events": "Status events",
        "owner_events": "Owner events",
        "detail_events": "Detail events",
        "comparison_events": "Comparison events",
        "queue_handoff_events": "Queue handoff events",
        "latest_project_activity": "Latest project activity",
        "project_activity_summary": "Project activity summary",
        "activity_count": "Activity count",
        "latest_activity": "Latest activity",
        "no_activity_yet": "No activity yet",
        "project_review_timeline_empty": "No review events yet.",
        "log_review_event": "Log review event",
        "server_backed_review_event_log": "Server-backed review event log",
        "review_event_status_changed": "Status changed",
        "review_event_detail_opened": "Detail opened",
        "review_event_comparison_copied": "Comparison brief copied",
        "review_event_queue_handoff_copied": "Queue handoff copied",
        "deliverable_report_eyebrow": "Deliverable",
        "deliverable_research_report": "Deliverable Research Report",
        "deliverable_report_description": "Condense the current analysis into an export-ready Chinese research brief that can be opened, printed, or saved as PDF.",
        "export_ready_brief": "Export-ready brief",
        "open_deliverable_report": "Open deliverable report",
        "print_save_pdf": "Print / Save PDF",
        "share_handoff": "Share handoff",
        "copy_report_link": "Copy report link",
        "copy_manifest_link": "Copy manifest link",
        "copied_link": "Link copied",
        "reader_toolbar": "Reader toolbar",
        "reader_outline": "Reader outline",
        "report_highlights": "Report highlights",
        "jump_to_section": "Jump to section",
        "current_report_link": "Current report link",
        "copy_current_link": "Copy current link",
        "copy_handoff_bundle": "Copy handoff bundle",
        "handoff_bundle_copied": "Handoff bundle copied",
        "delivery_package_eyebrow": "Delivery package",
        "delivery_package": "Report Delivery Package",
        "delivery_package_description": "Open or copy the deliverable, manifest, coverage matrix, and evidence queue from one compact panel.",
        "delivery_quality_summary": "Delivery quality summary",
        "research_only_package": "Research-only package",
        "remaining_gaps": "Remaining gaps",
        "delivery_quality_no_remaining_gaps": "No remaining gaps",
        "delivery_package_deliverable_description": "Chinese research summary for external handoff or internal review.",
        "delivery_package_manifest_description": "Machine-readable input resolution, candidates, quality snapshot, and report links.",
        "delivery_package_coverage_description": "Check which maintained-universe candidates still lack primary/fact, risk, or ticker evidence.",
        "delivery_package_queue_description": "Execution queue for closing primary-source, risk, and invalidation evidence gaps.",
        "deliverable_report_type": "Deliverable report",
        "deliverable_brief_description": "Includes research topic, candidate ranking, quality gate, evidence gaps, and next actions.",
        "deliverable_contents": "Report contents",
        "deliverable_contents_summary": "Summary, ranking, gate, gaps",
        "deliverable_contents_description": "The Markdown file opens in the report reader and can be printed to PDF from the browser.",
        "report_library_eyebrow": "Report library",
        "recent_reports": "Recent Reports",
        "recent_reports_description": "Recently generated industry, theme, and ticker analyses are saved here for review and comparison.",
        "report_workbench": "Report Workbench",
        "report_workbench_description": "Filter by report type, Open in reader for generated analyses or operational reports, then Open full page when needed.",
        "report_type_label": "Filter by report type",
        "all_report_types": "All report types",
        "generated_analysis_reports": "Generated analyses",
        "operational_report_type": "Operational reports",
        "open_in_reader": "Open in reader",
        "open_full_page": "Open full page",
        "operational_reports": "Operational Reports",
        "coverage_matrix_title": "Universe Coverage Matrix",
        "coverage_matrix_description": "Review which maintained universe candidates still lack primary/fact, risk, or direct ticker evidence.",
        "open_coverage_matrix": "Open Coverage Matrix",
        "acquisition_queue_title": "Evidence Acquisition Queue",
        "acquisition_queue_description": "Review the next primary-source, risk, and invalidation evidence tasks for this analysis.",
        "open_acquisition_queue": "Open Acquisition Queue",
        "analysis_manifest_title": "Analysis Manifest",
        "analysis_manifest_description": "Review this run's input resolution, candidate tickers, quality snapshot, report links, and research boundary.",
        "open_analysis_manifest": "Open Analysis Manifest",
        "evidence_tasks_eyebrow": "Next research actions",
        "evidence_tasks": "Evidence Tasks",
        "evidence_tasks_description": "Act on the highest-priority acquisition queue items before promoting the research confidence of this analysis.",
        "no_evidence_tasks": "No pending evidence tasks. Open the acquisition queue to review coverage, or continue reading candidate reports.",
        "evidence_tasks_priority": "Priority",
        "source_target": "Source Target",
        "task_rationale": "Why it matters",
        "task_acceptance_criteria": "Acceptance criteria",
        "task_after_import": "After import",
        "copy_search_prompt": "Copy search prompt",
        "copied_prompt": "Copied",
        "task_status": "Task Status",
        "task_to_collect": "To collect",
        "task_collected": "Collected",
        "task_verified": "Verified",
        "add_evidence": "Add Evidence",
        "source_title_label": "Source title",
        "source_url_label": "Source URL",
        "source_excerpt_label": "Source excerpt",
        "submit_evidence": "Submit and rerun analysis",
        "evidence_imported": "Evidence added to analysis",
        "import_helper": "Paste a short primary-source excerpt that directly supports this task.",
        "import_required": "Required: source title, source URL, and a traceable excerpt.",
        "import_loading": "Submitting evidence...",
        "imported_evidence": "Imported Evidence",
        "no_imported_evidence": "No evidence has been imported from this task yet.",
        "resolved": "Resolved",
        "resolved_by_imported_evidence": "Resolved by imported evidence",
        "import_impact": "Import Impact",
        "closed_gap_label": "Closed gap",
        "quality_gate_impact": "Quality gate impact: rerun complete; review the updated publish status and quality score.",
        "remaining_evidence_work": "Remaining evidence work: review the next visible task cards before publishing.",
        "quality_before_import": "Quality before import",
        "quality_after_import": "Quality after import",
        "quality_score_change": "Quality score change",
        "quality_delta_unavailable": "not available",
        "quality_delta_points": "{delta:+d} pts",
        "import_failed_title": "Evidence import failed",
        "import_failed_recovery": "Go back and correct the source title, source URL, and source excerpt, then try again.",
        "resolved_gap_prefix": "Resolved gap: ",
        "open_report": "Open report",
        "canonical_theme": "Canonical theme",
        "candidate_tickers": "Candidate tickers",
        "no_recent_reports": "No generated reports yet. Enter an industry, theme, or ticker and start an analysis to populate this library.",
        "search_label": "Search tickers, flags, memo text, or source claims",
        "search_placeholder": "Try SIVE, risk, primary source, NVDA...",
        "status": "Status",
        "all_statuses": "All Statuses",
        "reset_filters": "Reset filters",
        "showing_all": "Showing all dashboard items.",
        "showing": "Showing",
        "of": "of",
        "dashboard_items": "dashboard items.",
        "readiness_description": "Status is based on evidence depth, primary-source coverage, risk coverage, and concentration checks.",
        "generated_research": "Generated research",
        "memo_description": "Open individual memos for the full scorecard, thesis, skeptic review, and invalidation work.",
        "comparison_eyebrow": "Cross-candidate review",
        "candidate_comparison": "Candidate Comparison",
        "candidate_comparison_description": "Compare candidates side by side by score, rating, confidence, key gaps, and evidence coverage.",
        "score": "Score",
        "rating": "Rating",
        "confidence": "Confidence",
        "key_gaps": "Key Gaps",
        "revenue_growth": "Revenue Growth",
        "gross_margin": "Gross Margin",
        "valuation": "Valuation",
        "momentum": "Momentum",
        "cycle_position": "Cycle Position",
        "analyst_preview": "Analyst preview",
        "featured_preview": "Featured Memo Preview",
        "preview_description": "Short previews make it easier to triage the pack before opening the full memo files.",
        "traceability": "Traceability",
        "evidence_provenance": "Evidence Provenance",
        "provenance_description": "Primary evidence is shown with claim text and excerpts so users can audit why a memo uses a source.",
        "research_only": "Research only.",
        "disclaimer": "This dashboard is not investment advice, does not recommend any trade, and requires independent verification before any capital decision.",
        "no_readiness": "No readiness rows were found.",
        "ticker": "Ticker",
        "evidence_count": "Evidence",
        "risk": "Risk",
        "flags": "Flags",
        "no_memos": "No memo pack rows were found.",
        "open_memo": "Open memo",
        "view_report": "View Report",
        "report_reader": "Report Reader",
        "select_report": "Select a report",
        "close_report": "Close report",
        "drawer_empty": "Choose any report button to open the full memo here.",
        "loading_report": "Loading report...",
        "report_load_failed": "Report failed to load. Check that the local server can access the memo file.",
        "not_generated": "Not generated",
        "primary": "Primary",
        "serenity_rating": "Serenity Rating",
        "no_previews": "No memo previews were found.",
        "open_full_memo": "Open full memo",
        "no_thesis": "No thesis summary found.",
        "source_coverage": "Source coverage",
        "no_coverage": "No coverage summary found.",
        "risks": "Risks",
        "invalidation_conditions": "Invalidation Conditions",
        "no_sources": "No primary evidence provenance was found.",
        "used_in": "Used in",
        "no_claim": "No claim text found.",
        "no_excerpt": "No excerpt provided.",
    }


def _render_status_options(rows: Sequence[Mapping[str, str]]) -> str:
    statuses = sorted({row.get("status", "").strip() for row in rows if row.get("status", "").strip()})
    return "".join(
        f'<option value="{escape(status)}">{escape(status.replace("_", " ").title())}</option>'
        for status in statuses
    )


def _render_analysis_history(rows: Sequence[Mapping[str, object]], copy: Mapping[str, str], language: str) -> str:
    if not rows:
        return (
            '<div class="report-grid">'
            '<article class="report-card" data-dashboard-item data-report-workbench-item '
            'data-report-type="generated" data-status="generated">'
            f'<div class="eyebrow">{escape(copy["generated_analysis_reports"])}</div>'
            f'<h3>{escape(copy["recent_reports"])}</h3>'
            f'<p>{escape(copy["no_recent_reports"])}</p>'
            "</article>"
            "</div>"
        )

    cards = []
    for row in rows[:12]:
        href = str(row.get("href_zh" if language == "zh" else "href_en") or row.get("href") or "")
        query = str(row.get("query") or "Report")
        intent = str(row.get("intent") or "")
        canonical = str(row.get("canonical_theme") or "")
        candidate_tickers = row.get("candidate_tickers") or ""
        if isinstance(candidate_tickers, list):
            candidate_text = ", ".join(str(ticker) for ticker in candidate_tickers)
        else:
            candidate_text = str(candidate_tickers)
        link = (
            '<div class="report-actions">'
            f'<button type="button" class="memo-link" data-memo-href="{escape(href)}" '
            f'data-memo-title="{escape(query)}" onclick="openMemoDrawer(this)">{escape(copy["open_in_reader"])}</button>'
            f'<a class="memo-link" href="{escape(href)}">{escape(copy["open_full_page"])}</a>'
            "</div>"
            if href
            else f'<span class="memo-link" aria-disabled="true">{escape(copy["not_generated"])}</span>'
        )
        cards.append(
            f"<article class=\"report-card\" data-dashboard-item data-report-workbench-item data-report-type=\"generated\" data-status=\"generated\" data-search=\"{escape(_search_blob(row))}\">"
            f"<div class=\"eyebrow\">{escape(copy['generated_analysis_reports'])}{' · ' + escape(intent) if intent else ''}</div>"
            f"<h3>{escape(query)}</h3>"
            f"<p class=\"source-meta\">{escape(copy['canonical_theme'])}: {escape(canonical or 'n/a')}</p>"
            f"<p class=\"source-meta\">{escape(copy['candidate_tickers'])}: {escape(candidate_text or 'n/a')}</p>"
            f"{link}"
            "</article>"
        )
    return f'<div class="report-grid">{"".join(cards)}</div>'


def _render_operational_reports(rows: Sequence[Mapping[str, str]], copy: Mapping[str, str]) -> str:
    if not rows:
        return ""

    cards = []
    for row in rows:
        href = row.get("href", "")
        title = row.get("title", copy["operational_reports"])
        description = row.get("description", "")
        report_type = "deliverable" if row.get("title_key") == "deliverable_report_title" else "operational"
        eyebrow = copy["deliverable_report_type"] if report_type == "deliverable" else copy["operational_reports"]
        if href:
            copy_label = copy["copy_manifest_link"] if row.get("title_key") == "analysis_manifest_title" else copy["copy_report_link"]
            button = (
                '<div class="report-actions">'
                f'<button type="button" class="memo-link" data-memo-href="{escape(href)}" '
                f'data-memo-title="{escape(title)}" onclick="openMemoDrawer(this)">{escape(row.get("button", copy["open_report"]))}</button>'
                f'<button type="button" class="memo-link" data-share-href="{escape(href)}" '
                f'data-copied-text="{escape(copy["copied_link"])}" onclick="copyShareLink(this)">{escape(copy_label)}</button>'
                '</div>'
            )
        else:
            button = f'<span class="memo-link" aria-disabled="true">{escape(copy["not_generated"])}</span>'
        cards.append(
            f'<article class="report-card" data-dashboard-item data-report-workbench-item data-report-type="{escape(report_type)}" data-status="{escape(report_type)}" data-search="{escape(_search_blob(row))}">'
            f'<div class="eyebrow">{escape(eyebrow)}</div>'
            f"<h3>{escape(title)}</h3>"
            f"<p>{escape(description)}</p>"
            f"{button}"
            "</article>"
        )
    return f'<div class="report-grid operational-report-grid">{"".join(cards)}</div>'


def _write_deliverable_report(
    output_dir: Path,
    query: str,
    memo_rows: Sequence[Mapping[str, str]],
    memo_previews: Sequence[Mapping[str, object]],
    primary_sources: Sequence[Mapping[str, str]] | None = None,
) -> Path:
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / "deliverable-research-report.md"
    output.write_text(
        _render_deliverable_report_markdown(query, memo_rows, memo_previews, primary_sources or []),
        encoding="utf-8",
    )
    return output


def _render_deliverable_report_markdown(
    query: str,
    memo_rows: Sequence[Mapping[str, str]],
    memo_previews: Sequence[Mapping[str, object]],
    primary_sources: Sequence[Mapping[str, str]] | None = None,
) -> str:
    preview_by_ticker = {
        str(preview.get("ticker", "")).upper(): preview
        for preview in memo_previews
        if str(preview.get("ticker", "")).strip()
    }
    top_row = _select_top_candidate(memo_rows, preview_by_ticker) if memo_rows else {}
    top_ticker = str(top_row.get("ticker") or "n/a").upper()
    top_preview = preview_by_ticker.get(top_ticker, {})
    score_text = str(top_preview.get("score") or top_row.get("score") or "0")
    score_match = re.search(r"\d+", score_text)
    score_value = int(score_match.group(0)) if score_match else 0
    evidence_value = _to_int(str(top_row.get("evidence", "0")))
    primary_value = _to_int(str(top_row.get("primary", "0")))
    risk_value = _to_int(str(top_row.get("risk", "0")))
    gaps = str(top_preview.get("gaps") or top_row.get("gaps") or "none")
    quality_score = _report_quality_score(score_value, evidence_value, primary_value, risk_value)
    status_key = _report_quality_status(quality_score, primary_value, risk_value, gaps, top_row)
    zh = _copy("zh")
    status_copy = zh[f"quality_status_{status_key.replace('-', '_')}"]
    ranked_rows = sorted(memo_rows, key=lambda row: _candidate_rank_tuple(row, preview_by_ticker), reverse=True)
    ranking_lines = [
        "| 排名 | 候选 | 评分 | 评级 | 置信层级 | 证据 | Primary | 风险 | 关键缺口 |",
        "|---:|---|---|---|---|---:|---:|---:|---|",
    ]
    for index, row in enumerate(ranked_rows, start=1):
        ticker = str(row.get("ticker") or "n/a").upper()
        preview = preview_by_ticker.get(ticker, {})
        ranking_lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    ticker,
                    str(preview.get("score") or row.get("score") or "n/a"),
                    str(preview.get("rating") or row.get("rating") or "n/a"),
                    str(preview.get("confidence") or row.get("confidence") or "n/a"),
                    str(row.get("evidence", "0")),
                    str(row.get("primary", "0")),
                    str(row.get("risk", "0")),
                    str(preview.get("gaps") or row.get("gaps") or "none"),
                ]
            )
            + " |"
        )
    evidence_lines = _render_deliverable_primary_source_lines(primary_sources or [])
    gap_lines = "\n".join(f"- {item}" for item in _deliverable_gap_actions(gaps, primary_value, risk_value))
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return "\n".join(
        [
            "# 可交付研究报告",
            "",
            f"**研究主题:** {query}",
            f"**生成时间:** {generated_at}",
            "**报告性质:** 仅供研究，不构成投资建议。",
            "",
            "## 交付版摘要",
            "",
            f"- 首选候选：{top_ticker}（{score_text}，{top_preview.get('rating') or top_row.get('rating') or 'n/a'}，{top_preview.get('confidence') or top_row.get('confidence') or 'n/a'}）。",
            f"- 覆盖情况：{evidence_value} 条证据、{primary_value} 条 primary/fact、{risk_value} 条风险证据。",
            f"- 质量门禁：{status_copy}，质量评分 {quality_score}/100。",
            "",
            "## 候选排序",
            "",
            *ranking_lines,
            "",
            "## 质量门禁",
            "",
            f"- 发布状态：{status_copy}",
            f"- 质量评分：{quality_score}/100",
            f"- Primary source 深度：{primary_value}",
            f"- 风险覆盖：{risk_value}",
            f"- 当前缺口：{gaps}",
            "",
            "## 关键来源与证据",
            "",
            *evidence_lines,
            "",
            "## 证据缺口与下一步",
            "",
            gap_lines,
            "",
            "## 研究边界",
            "",
            "仅供研究。本报告用于整理 Serenity Alpha Lab 的候选排序、证据覆盖和后续研究动作，不提供买入、卖出、持有、目标价或仓位建议。",
            "",
        ]
    )


def _render_deliverable_primary_source_lines(primary_sources: Sequence[Mapping[str, str]]) -> list[str]:
    if not primary_sources:
        return ["- 暂无可展示 primary source；请先补充可追溯来源。"]

    lines: list[str] = []
    for source in list(primary_sources)[:5]:
        source_id = str(source.get("id") or "n/a").strip() or "n/a"
        title = str(source.get("title") or source_id).strip() or source_id
        memos = str(source.get("memos") or "n/a").strip() or "n/a"
        claim = str(source.get("claim") or "n/a").strip() or "n/a"
        excerpt = str(source.get("excerpt") or "n/a").strip() or "n/a"
        lines.extend(
            [
                f"- **来源:** {title} ({source_id})",
                f"  - **用于:** {memos}",
                f"  - **声明:** {claim}",
                f"  - **来源摘录:** {excerpt}",
            ]
        )
    return lines


def _deliverable_gap_actions(gaps: str, primary: int, risk: int) -> list[str]:
    actions = []
    normalized = gaps.lower()
    if primary < 2 or "primary" in normalized:
        actions.append("补充公司公告、监管文件、业绩会或官方投资者材料，提升 primary source 深度。")
    if risk < 2 or "risk" in normalized or "invalidation" in normalized:
        actions.append("补充反证、失效条件和下行情景证据，避免只保留正向论点。")
    if "low_score" in normalized:
        actions.append("复核低评分来源，优先寻找能直接支撑需求、供给瓶颈或公司兑现的数据。")
    if not actions:
        actions.append("暂无关键证据缺口；继续监控新增来源并定期重新生成报告。")
    return actions


def _render_evidence_tasks(
    rows: Sequence[Mapping[str, object]],
    copy: Mapping[str, str],
    imported_evidence: Sequence[Mapping[str, object]] = (),
    *,
    quality_snapshot: Mapping[str, object] | None = None,
) -> str:
    acquisition = next((row for row in rows if row.get("title_key") == "acquisition_queue_title"), None)
    if not acquisition:
        return _render_evidence_tasks_section([], copy, "")

    tasks = acquisition.get("tasks")
    queue_href = str(acquisition.get("href") or "")
    if not isinstance(tasks, list) or not tasks:
        return _render_evidence_tasks_section([], copy, queue_href)

    rendered = []
    rendered_task_keys: set[tuple[str, str]] = set()
    for task in tasks[:8]:
        if not isinstance(task, Mapping):
            continue
        priority = _localize_priority_label(str(task.get("priority", "")), copy)
        ticker = str(task.get("ticker", "") or "n/a")
        raw_gap = str(task.get("gap", ""))
        gap = _localize_gap_label(raw_gap, copy)
        source_target = _localize_source_target_label(str(task.get("source_target", "")), copy)
        search_prompt = str(task.get("search_prompt", "") or "")
        rationale = _localize_task_playbook_text(
            str(task.get("rationale") or _default_task_rationale(raw_gap)),
            copy,
        )
        acceptance_criteria = _localize_task_playbook_text(
            str(task.get("acceptance_criteria") or _default_task_acceptance_criteria(raw_gap)),
            copy,
        )
        after_import = _localize_task_playbook_text(
            str(task.get("after_import") or _default_task_after_import(raw_gap)),
            copy,
        )
        task_id = _task_id(ticker=ticker, gap=raw_gap, search_prompt=search_prompt)
        default_claim = _default_import_claim(ticker=ticker, gap=gap)
        default_summary = _default_import_summary(ticker=ticker, gap=gap)
        default_id = f"manual:{ticker}:{task_id}"
        quality_before_score = str((quality_snapshot or {}).get("score") or "")
        quality_before_status = str((quality_snapshot or {}).get("status") or "")
        task_history = _matching_imported_evidence(imported_evidence, ticker=ticker, gap=raw_gap)
        is_resolved = bool(task_history)
        rendered_task_keys.add((_normalize_ticker(ticker), _canonical_gap(raw_gap)))
        task_status = "verified" if is_resolved else "to_collect"
        status_label = copy["resolved"] if is_resolved else priority
        resolved_note = ""
        if is_resolved:
            resolved_note = f'<p class="resolved-note">{escape(copy["resolved_by_imported_evidence"])}</p>'
        rerun_context = escape(
            json.dumps(
                {
                    "taskId": task_id,
                    "ticker": ticker,
                    "query": copy.get("query", ""),
                    "qualityBefore": quality_before_score or "n/a",
                },
                ensure_ascii=False,
            )
        )
        rendered.append(
            f'<article class="task-card" data-dashboard-item data-status="operational" data-ticker="{escape(ticker)}" data-task-id="{escape(task_id)}" data-task-status="{escape(task_status)}" data-quality-before-rerun="{escape(quality_before_score)}" data-search="{escape(_search_blob(task))}">'
            "<header>"
            f"<div><div class=\"eyebrow\">{escape(copy['evidence_tasks_priority'])}: {escape(priority)}</div><h3>{escape(ticker)} · {escape(gap)}</h3></div>"
            f"{_status_pill(status_label)}"
            "</header>"
            f"{resolved_note}"
            f"<p><strong>{escape(copy['source_target'])}:</strong> {escape(source_target)}</p>"
            f"<div class=\"task-prompt\">{escape(search_prompt)}</div>"
            "<div class=\"task-playbook\">"
            f"<p><strong>{escape(copy['task_rationale'])}:</strong> {escape(rationale)}</p>"
            f"<p><strong>{escape(copy['task_acceptance_criteria'])}:</strong> {escape(acceptance_criteria)}</p>"
            f"<p><strong>{escape(copy['task_after_import'])}:</strong> {escape(after_import)}</p>"
            "</div>"
            f"<label class=\"task-status-control\">{escape(copy['task_status'])}"
            f"<select data-task-status-select onchange=\"updateTaskStatus(this)\" aria-label=\"{escape(copy['task_status'])}\">"
            f"<option value=\"to_collect\">{escape(copy['task_to_collect'])}</option>"
            f"<option value=\"collected\">{escape(copy['task_collected'])}</option>"
            f"<option value=\"verified\">{escape(copy['task_verified'])}</option>"
            "</select></label>"
            f"<div class=\"verified-task-rerun-loop\" data-verified-task-rerun data-verified-task-rerun-context=\"{rerun_context}\" data-quality-delta-after-rerun=\"n/a\">"
            f"<strong>{escape(copy['evidence_verification_rerun_loop'])}</strong>"
            f"<small>{escape(copy['auto_rerun_after_verification'])}</small>"
            f"<p data-verified-task-rerun-status aria-live=\"polite\">{escape(copy['quality_delta_after_rerun'])}: n/a</p>"
            f"<button type=\"button\" data-verified-task-rerun-button onclick=\"return handleVerifiedTaskRerun(this);\" disabled>{escape(copy['rerun_verified_task'])}</button>"
            "</div>"
            f"<button type=\"button\" class=\"memo-link\" data-copy-text=\"{escape(search_prompt)}\" data-copied-text=\"{escape(copy['copied_prompt'])}\" onclick=\"copyTaskPrompt(this)\">{escape(copy['copy_search_prompt'])}</button>"
            f"<form class=\"evidence-import\" action=\"/ingest-evidence\" method=\"post\" onsubmit=\"return handleEvidenceImportSubmit(this);\">"
            f"<strong>{escape(copy['add_evidence'])}</strong>"
            f"<p class=\"evidence-import-help\">{escape(copy['import_helper'])}</p>"
            f"<input type=\"hidden\" name=\"query\" value=\"{escape(copy.get('query', ''))}\">"
            f"<input type=\"hidden\" name=\"language\" value=\"{escape(copy['language'])}\">"
            f"<input type=\"hidden\" name=\"ticker\" value=\"{escape(ticker)}\">"
            f"<input type=\"hidden\" name=\"id\" value=\"{escape(default_id)}\">"
            f"<input type=\"hidden\" name=\"task_id\" value=\"{escape(task_id)}\">"
            f"<input type=\"hidden\" name=\"claim\" value=\"{escape(default_claim)}\">"
            f"<input type=\"hidden\" name=\"summary\" value=\"{escape(default_summary)}\">"
            f"<input type=\"hidden\" name=\"quality_before_score\" value=\"{escape(quality_before_score)}\">"
            f"<input type=\"hidden\" name=\"quality_before_status\" value=\"{escape(quality_before_status)}\">"
            f"<div class=\"field\"><label>{escape(copy['source_title_label'])}<input name=\"source_title\" required></label></div>"
            f"<div class=\"field\"><label>{escape(copy['source_url_label'])}<input name=\"source_url\" type=\"url\" required></label></div>"
            f"<div class=\"field\"><label>{escape(copy['source_excerpt_label'])}<textarea name=\"source_excerpt\" required></textarea></label></div>"
            f"<p class=\"evidence-import-help\">{escape(copy['import_required'])}</p>"
            f"<p class=\"import-status\" data-import-status aria-live=\"polite\" hidden>{escape(copy['import_loading'])}</p>"
            f"<button type=\"submit\" data-loading-text=\"{escape(copy['import_loading'])}\">{escape(copy['submit_evidence'])}</button>"
            f"{_render_import_history(task_history, copy)}"
            "</form>"
            "</article>"
        )
    for item in imported_evidence:
        ticker = _first_ticker(item)
        gap_key = _canonical_gap_from_evidence(item)
        if not ticker or (ticker, gap_key) in rendered_task_keys:
            continue
        title = str(item.get("source_title") or item.get("id") or "Imported evidence")
        gap = _localize_gap_label(gap_key, copy)
        task_id = _task_id(ticker=ticker, gap=gap_key, search_prompt=title)
        rendered_task_keys.add((ticker, gap_key))
        rendered.append(
            f'<article class="task-card" data-dashboard-item data-status="operational" data-ticker="{escape(ticker)}" data-task-id="{escape(task_id)}" data-task-status="verified" data-search="{escape(_search_blob(item))}">'
            "<header>"
            f"<div><div class=\"eyebrow\">{escape(copy['imported_evidence'])}</div><h3>{escape(ticker)} · {escape(gap)}</h3></div>"
            f"{_status_pill(copy['resolved'])}"
            "</header>"
            f"<p class=\"resolved-note\">{escape(copy['resolved_by_imported_evidence'])}</p>"
            f"{_render_import_history([item], copy)}"
            "</article>"
        )
    if not rendered:
        return _render_evidence_tasks_section([], copy, queue_href)

    return _render_evidence_tasks_section(rendered, copy, queue_href)


def _render_evidence_tasks_section(rendered: Sequence[str], copy: Mapping[str, str], queue_href: str = "") -> str:
    empty_rerun_loop = (
        '<div class="verified-task-rerun-loop" data-verified-task-rerun '
        'data-verified-task-rerun-context="{}" data-quality-delta-after-rerun="n/a">'
        f'<strong>{escape(copy["evidence_verification_rerun_loop"])}</strong>'
        f'<small>{escape(copy["auto_rerun_after_verification"])}</small>'
        f'<p data-verified-task-rerun-status aria-live="polite">{escape(copy["quality_delta_after_rerun"])}: n/a</p>'
        f'<button type="button" data-verified-task-rerun-button disabled>{escape(copy["rerun_verified_task"])}</button>'
        "</div>"
    )
    body = (
        f'<div class="task-grid">{"".join(rendered)}</div>'
        if rendered
        else (
            '<div class="note" data-dashboard-item data-status="operational">'
            f'<p>{escape(copy["no_evidence_tasks"])}</p>'
            f"{empty_rerun_loop}"
            f'<button type="button" class="memo-link" data-memo-href="{escape(queue_href)}" '
            f'data-memo-title="{escape(copy["acquisition_queue_title"])}" onclick="openMemoDrawer(this)">{escape(copy["open_acquisition_queue"])}</button>'
            "</div>"
            if queue_href
            else f'<div class="note" data-dashboard-item data-status="operational"><p>{escape(copy["no_evidence_tasks"])}</p>{empty_rerun_loop}</div>'
        )
    )
    return (
        '<section id="evidence-tasks" aria-labelledby="evidence-tasks-title">'
        '<div class="section-head"><div>'
        f'<div class="eyebrow">{escape(copy["evidence_tasks_eyebrow"])}</div>'
        f'<h2 id="evidence-tasks-title">{escape(copy["evidence_tasks"])}</h2>'
        f'<p>{escape(copy["evidence_tasks_description"])}</p>'
        '</div></div>'
        f"{body}"
        '</section>'
    )


def _render_import_history(items: Sequence[Mapping[str, object]], copy: Mapping[str, str]) -> str:
    if not items:
        return f"<div class=\"import-history\" aria-live=\"polite\"><strong>{escape(copy['imported_evidence'])}</strong><br>{escape(copy['no_imported_evidence'])}</div>"

    rendered = []
    for item in items[:5]:
        title = str(item.get("source_title") or item.get("id") or "Imported evidence")
        url = str(item.get("source_url") or "")
        item_id = str(item.get("id") or "")
        published_at = str(item.get("published_at") or "")
        claim = str(item.get("claim") or "")
        title_html = f'<a href="{escape(url)}">{escape(title)}</a>' if url else f"<strong>{escape(title)}</strong>"
        meta = " | ".join(value for value in [item_id, published_at] if value)
        meta_html = f'<div class="source-meta">{escape(meta)}</div>' if meta else ""
        claim_html = f"<p>{escape(claim)}</p>" if claim else ""
        impact_html = _render_import_impact(item, copy)
        rendered.append(
            "<article class=\"import-history-item\">"
            f"{title_html}"
            f"{meta_html}"
            f"{claim_html}"
            f"{impact_html}"
            "</article>"
        )
    return f"<div class=\"import-history\" aria-live=\"polite\"><strong>{escape(copy['imported_evidence'])}</strong>{''.join(rendered)}</div>"


def _render_import_impact(
    item: Mapping[str, object],
    copy: Mapping[str, str],
    *,
    quality_before_score: str = "",
    quality_after_score: str = "",
) -> str:
    gap_key = _canonical_gap_from_evidence(item)
    gap = _localize_gap_label(gap_key, copy)
    separator = "：" if copy.get("language") == "zh" else ": "
    before_value = _format_quality_score(quality_before_score, copy)
    after_value = _format_quality_score(quality_after_score, copy)
    delta_value = _format_quality_delta(quality_before_score, quality_after_score, copy)
    return (
        '<div class="import-impact">'
        f'<strong>{escape(copy["import_impact"])}</strong>'
        f'<p>{escape(copy["closed_gap_label"])}{separator}{escape(gap)}</p>'
        f'<p>{escape(copy["quality_gate_impact"])}</p>'
        f'<p>{escape(copy["remaining_evidence_work"])}</p>'
        f'<p>{escape(copy["quality_before_import"])}{separator}{escape(before_value)}</p>'
        f'<p>{escape(copy["quality_after_import"])}{separator}{escape(after_value)}</p>'
        f'<p>{escape(copy["quality_score_change"])}{separator}{escape(delta_value)}</p>'
        '</div>'
    )


def _format_quality_score(value: object, copy: Mapping[str, str]) -> str:
    score = _parse_quality_score(value)
    if score is None:
        return copy["quality_delta_unavailable"]
    return f"{score}/100"


def _format_quality_delta(before: object, after: object, copy: Mapping[str, str]) -> str:
    before_score = _parse_quality_score(before)
    after_score = _parse_quality_score(after)
    if before_score is None or after_score is None:
        return copy["quality_delta_unavailable"]
    return copy["quality_delta_points"].format(delta=after_score - before_score)


def _parse_quality_score(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"\d+", text)
    if not match:
        return None
    return max(0, min(100, int(match.group(0))))


def _extract_quality_score_from_html(html: str, copy: Mapping[str, str]) -> str:
    label = re.escape(copy["quality_score"])
    match = re.search(
        rf"<span>{label}</span>\s*<strong>(\d{{1,3}})/100</strong>",
        html,
    )
    if match:
        return match.group(1)
    fallback = re.search(r">\s*(\d{1,3})/100\s*</strong>", html)
    return fallback.group(1) if fallback else ""


def _load_imported_evidence_for_output(output_path: Path) -> list[dict[str, object]]:
    candidates = [
        output_path.parent / "manual_intake_guarded.jsonl",
        output_path.parent.parent / "manual_intake_guarded.jsonl",
        output_path.parent.parent.parent / "manual_intake_guarded.jsonl",
        Path("data/enriched/manual_intake_guarded.jsonl"),
    ]
    for path in candidates:
        if path.exists():
            return _load_manual_evidence_jsonl(path)
    return []


def _load_manual_evidence_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and str(item.get("id", "")).startswith("manual:"):
            rows.append(item)
    return rows


def _matching_imported_evidence(
    imported_evidence: Sequence[Mapping[str, object]],
    *,
    ticker: str,
    gap: str,
) -> list[Mapping[str, object]]:
    normalized_ticker = _normalize_ticker(ticker)
    gap_key = _canonical_gap(gap)
    return [
        item
        for item in imported_evidence
        if _first_ticker(item) == normalized_ticker and _canonical_gap_from_evidence(item) == gap_key
    ]


def _first_ticker(item: Mapping[str, object]) -> str:
    tickers = item.get("tickers")
    if isinstance(tickers, Sequence) and not isinstance(tickers, (str, bytes)):
        for ticker in tickers:
            normalized = _normalize_ticker(str(ticker))
            if normalized:
                return normalized
    return _normalize_ticker(str(item.get("ticker", "")))


def _normalize_ticker(value: str) -> str:
    return value.strip().upper().lstrip("$")


def _canonical_gap(value: str) -> str:
    normalized = value.lower()
    if "primary" in normalized or "source" in normalized or "fact" in normalized:
        return "missing_primary_source"
    if "risk" in normalized or "invalidation" in normalized:
        return "missing_risk_evidence"
    if "direct" in normalized or "ticker" in normalized:
        return "missing_direct_ticker_evidence"
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_") or "missing_direct_ticker_evidence"


def _canonical_gap_from_evidence(item: Mapping[str, object]) -> str:
    text = " ".join(
        str(value)
        for value in [
            item.get("claim", ""),
            item.get("summary", ""),
            item.get("claim_type", ""),
            item.get("strength", ""),
            item.get("id", ""),
        ]
    ).lower()
    if "primary" in text or "source" in text or "fact" in text:
        return "missing_primary_source"
    if "risk" in text or "invalidation" in text:
        return "missing_risk_evidence"
    return "missing_direct_ticker_evidence"


def _load_operational_reports(output_dir: Path) -> list[TableRow]:
    reports_dir = output_dir / "reports"
    report_specs = [
        ("deliverable-research-report.md", "deliverable_report_title"),
        ("universe-coverage-matrix.md", "coverage_matrix_title"),
        ("evidence-acquisition-queue.md", "acquisition_queue_title"),
    ]
    reports: list[TableRow] = []
    manifest_path = output_dir / "analysis-manifest.json"
    if manifest_path.exists():
        reports.append({"title_key": "analysis_manifest_title", "href": _relative_href(output_dir, manifest_path)})
    for filename, title_key in report_specs:
        path = reports_dir / filename
        if path.exists():
            row = {"title_key": title_key, "href": _relative_href(output_dir, path)}
            if title_key == "acquisition_queue_title":
                row["tasks"] = _parse_acquisition_queue_tasks(path.read_text(encoding="utf-8"))  # type: ignore[assignment]
            reports.append(row)
    return reports


def _localize_operational_reports(rows: Sequence[Mapping[str, object]], copy: Mapping[str, str]) -> list[dict[str, object]]:
    localized: list[dict[str, object]] = []
    for row in rows:
        tasks = row.get("tasks", [])
        if row.get("title_key") == "deliverable_report_title":
            localized.append(
                {
                    "title_key": "deliverable_report_title",
                    "title": copy["deliverable_research_report"],
                    "description": copy["deliverable_report_description"],
                    "button": copy["open_deliverable_report"],
                    "href": row.get("href", ""),
                    "tasks": tasks,
                }
            )
            continue
        if row.get("title_key") == "coverage_matrix_title":
            localized.append(
                {
                    "title_key": "coverage_matrix_title",
                    "title": copy["coverage_matrix_title"],
                    "description": copy["coverage_matrix_description"],
                    "button": copy["open_coverage_matrix"],
                    "href": row.get("href", ""),
                    "tasks": tasks,
                }
            )
            continue
        if row.get("title_key") == "analysis_manifest_title":
            localized.append(
                {
                    "title_key": "analysis_manifest_title",
                    "title": copy["analysis_manifest_title"],
                    "description": copy["analysis_manifest_description"],
                    "button": copy["open_analysis_manifest"],
                    "href": row.get("href", ""),
                    "tasks": tasks,
                }
            )
            continue
        if row.get("title_key") == "acquisition_queue_title":
            localized.append(
                {
                    "title_key": "acquisition_queue_title",
                    "title": copy["acquisition_queue_title"],
                    "description": copy["acquisition_queue_description"],
                    "button": copy["open_acquisition_queue"],
                    "href": row.get("href", ""),
                    "tasks": tasks,
                }
            )
            continue
        localized.append(dict(row))
    return localized


def _parse_acquisition_queue_tasks(markdown: str) -> list[TableRow]:
    rows = _parse_first_table(markdown, expected_first_header="Priority")
    if not rows:
        rows = _parse_first_table(markdown, expected_first_header="优先级")

    tasks: list[TableRow] = []
    for row in rows:
        ticker = row.get("Ticker", "") or row.get("股票代码", "")
        if not ticker or ticker.lower() == "none":
            continue
        tasks.append(
            {
                "priority": row.get("Priority", "") or row.get("优先级", ""),
                "ticker": ticker,
                "gap": row.get("Gap", "") or row.get("缺口", ""),
                "source_target": row.get("Source Target", "") or row.get("来源目标", ""),
                "search_prompt": row.get("Search Prompt", "") or row.get("搜索提示", ""),
                "rationale": row.get("Why It Matters", "") or row.get("补证原因", ""),
                "acceptance_criteria": row.get("Acceptance Criteria", "") or row.get("验收标准", ""),
                "after_import": row.get("After Import", "") or row.get("导入后动作", ""),
            }
        )
    return tasks


def _task_id(*, ticker: str, gap: str, search_prompt: str) -> str:
    raw = f"{ticker}|{gap}|{search_prompt}".lower()
    return re.sub(r"[^a-z0-9]+", "-", raw).strip("-") or "task"


def _default_import_claim(*, ticker: str, gap: str) -> str:
    return f"Manual intake adds source-backed evidence for {ticker}: {gap}."


def _default_import_summary(*, ticker: str, gap: str) -> str:
    return f"User-collected evidence is being added to close the {gap} gap for {ticker}."


def _load_analysis_history(path: Path) -> list[TableRow]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    rows: list[TableRow] = []
    for entry in payload:
        if isinstance(entry, dict):
            rows.append(entry)
    return rows


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_run_records(path: Path) -> list[dict[str, object]]:
    with RUN_RECORD_LOCK:
        return _read_run_records_unlocked(path)


def _read_run_records_unlocked(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        payload = payload.get("runs", [])
    if not isinstance(payload, list):
        return []
    return [entry for entry in payload if isinstance(entry, dict)]


def _write_run_records_unlocked(path: Path, records: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps({"runs": list(records)}, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _load_project_records(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        payload = payload.get("projects", [])
    if not isinstance(payload, list):
        return []
    return [_normalize_project_record(entry) for entry in payload if isinstance(entry, dict)]


def _project_records_with_evidence_quality_summary(
    projects: Sequence[Mapping[str, object]],
    audits_path: Path,
    task_statuses_path: Path | None = None,
) -> list[dict[str, object]]:
    audits = _load_project_evidence_audits(audits_path)
    task_statuses = _load_task_status_records(task_statuses_path) if task_statuses_path is not None else []
    enriched: list[dict[str, object]] = []
    for project in projects:
        item = dict(project)
        identifiers = {
            str(item.get("id") or ""),
            str(item.get("href") or ""),
        }
        project_audits = [
            audit
            for audit in audits
            if str(audit.get("projectId") or "") in identifiers
        ]
        summary = _project_evidence_audit_summary(project_audits)
        if summary:
            item["evidenceQualitySummary"] = summary
        elif "evidenceQualitySummary" in item:
            item["evidenceQualitySummary"] = {}
        project_statuses = [
            status
            for status in task_statuses
            if str(status.get("projectId") or "") in identifiers
        ]
        progress = _project_evidence_progress_summary(project_statuses)
        if progress:
            item["evidenceProgressSummary"] = progress
        elif "evidenceProgressSummary" in item:
            item["evidenceProgressSummary"] = {}
        item["nextActionSummary"] = _project_next_action_summary(item)
        enriched.append(item)
    return enriched


def _project_next_action_summary(project: Mapping[str, object]) -> dict[str, object]:
    status = str(project.get("status") or "pending-evidence")
    progress = project.get("evidenceProgressSummary")
    if not isinstance(progress, Mapping):
        progress = {}
    to_collect = _safe_int(progress.get("toCollect"))
    collected = _safe_int(progress.get("collected"))
    total = _safe_int(progress.get("total"))
    verified = _safe_int(progress.get("verified"))
    gap = str(project.get("gap") or "").strip()
    href = str(project.get("href") or "").strip()
    if status == "delivered":
        return {
            "type": "archive-project",
            "priority": "low",
            "label": "Archive delivered project",
            "reason": "Project is marked delivered; preserve the review trail",
        }
    if status == "needs-rerun":
        return {
            "type": "rerun-analysis",
            "priority": "high",
            "label": "Rerun analysis",
            "reason": "Project is marked as needing a rerun",
        }
    if to_collect > 0:
        noun = "task" if to_collect == 1 else "tasks"
        return {
            "type": "collect-evidence",
            "priority": "high",
            "label": "Collect missing evidence",
            "reason": f"{to_collect} evidence {noun} still needs collection",
        }
    if total > 0:
        return {
            "type": "review-report",
            "priority": "medium",
            "label": "Review report",
            "reason": "Evidence tasks are complete; review thesis, risks, and invalidation conditions",
        }
    if gap:
        return {
            "type": "collect-evidence",
            "priority": "high",
            "label": "Collect missing evidence",
            "reason": f"Open evidence task for {gap}",
        }
    if href:
        return {
            "type": "review-report",
            "priority": "medium",
            "label": "Review report",
            "reason": "Review thesis, risks, and invalidation conditions before delivery",
        }
    return {
        "type": "open-report",
        "priority": "medium",
        "label": "Open project report",
        "reason": "Open the generated report to continue review",
    }


def _project_evidence_progress_summary(statuses: Sequence[Mapping[str, object]]) -> dict[str, object]:
    if not statuses:
        return {}
    total = len(statuses)
    verified = sum(1 for status in statuses if str(status.get("status") or "") == "verified")
    collected = sum(1 for status in statuses if str(status.get("status") or "") == "collected")
    to_collect = sum(1 for status in statuses if str(status.get("status") or "") == "to_collect")
    return {
        "total": total,
        "verified": verified,
        "collected": collected,
        "toCollect": to_collect,
        "label": f"{verified}/{total} verified",
    }


def _normalize_project_record(project: Mapping[str, object]) -> dict[str, object]:
    quality = project.get("quality")
    if not isinstance(quality, dict):
        quality = {}
    record = {
        "id": str(project.get("id") or project.get("href") or project.get("query") or ""),
        "query": str(project.get("query") or ""),
        "href": str(project.get("href") or ""),
        "status": str(project.get("status") or "pending-evidence"),
        "quality": dict(quality),
        "topTicker": str(project.get("topTicker") or project.get("top_ticker") or "n/a"),
        "gap": str(project.get("gap") or ""),
        "owner": str(project.get("owner") or ""),
        "savedAt": str(project.get("savedAt") or project.get("saved_at") or _utc_timestamp()),
    }
    evidence_quality_summary = project.get("evidenceQualitySummary")
    if isinstance(evidence_quality_summary, dict):
        record["evidenceQualitySummary"] = dict(evidence_quality_summary)
    evidence_progress_summary = project.get("evidenceProgressSummary")
    if isinstance(evidence_progress_summary, dict):
        record["evidenceProgressSummary"] = dict(evidence_progress_summary)
    next_action_summary = project.get("nextActionSummary")
    if isinstance(next_action_summary, dict):
        record["nextActionSummary"] = dict(next_action_summary)
    return record


def _write_project_record(*, path: Path, project: Mapping[str, object]) -> list[dict[str, object]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_project_record(project)
    project_id = str(normalized.get("id") or "")
    existing = [entry for entry in _load_project_records(path) if str(entry.get("id") or "") != project_id]
    projects = [normalized, *existing][:100]
    path.write_text(json.dumps({"projects": projects}, ensure_ascii=False, indent=2), encoding="utf-8")
    return projects


def _clear_project_records(path: Path) -> list[dict[str, object]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"projects": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    return []


def _load_project_review_events(path: Path, *, project_id: str = "") -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        payload = payload.get("events", [])
    if not isinstance(payload, list):
        return []
    events = [_normalize_project_review_event(entry) for entry in payload if isinstance(entry, dict)]
    if project_id:
        events = [entry for entry in events if str(entry.get("projectId") or "") in {project_id, "comparison"}]
    return events


def _normalize_project_review_event(event: Mapping[str, object]) -> dict[str, object]:
    return {
        "id": str(event.get("id") or f"event-{_utc_timestamp()}"),
        "projectId": str(event.get("projectId") or event.get("project_id") or ""),
        "projectQuery": str(event.get("projectQuery") or event.get("project_query") or ""),
        "type": str(event.get("type") or "review-event"),
        "label": str(event.get("label") or ""),
        "at": str(event.get("at") or _utc_timestamp()),
    }


def _write_project_review_event(*, path: Path, event: Mapping[str, object]) -> list[dict[str, object]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_project_review_event(event)
    event_id = str(normalized.get("id") or "")
    existing = [entry for entry in _load_project_review_events(path) if str(entry.get("id") or "") != event_id]
    events = [normalized, *existing][:500]
    path.write_text(json.dumps({"events": events}, ensure_ascii=False, indent=2), encoding="utf-8")
    return events


def _clear_project_review_events(path: Path) -> list[dict[str, object]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"events": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    return []


def _load_project_evidence_audits(path: Path, *, project_id: str = "") -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        payload = payload.get("audits", [])
    if not isinstance(payload, list):
        return []
    audits = [_normalize_project_evidence_audit(entry) for entry in payload if isinstance(entry, dict)]
    if project_id:
        audits = [entry for entry in audits if str(entry.get("projectId") or "") == project_id]
    return audits


def _project_evidence_audit_summary(audits: Sequence[Mapping[str, object]]) -> dict[str, object]:
    for audit in audits:
        delta = str(audit.get("qualityDelta") or "").strip()
        if not delta or delta == "n/a":
            continue
        return {
            "projectId": str(audit.get("projectId") or ""),
            "projectQuery": str(audit.get("projectQuery") or ""),
            "taskId": str(audit.get("taskId") or ""),
            "ticker": str(audit.get("ticker") or ""),
            "qualityBefore": str(audit.get("qualityBefore") or "n/a"),
            "qualityAfter": str(audit.get("qualityAfter") or "n/a"),
            "qualityDelta": delta,
            "at": str(audit.get("at") or ""),
        }
    return {}


def _normalize_project_evidence_audit(audit: Mapping[str, object]) -> dict[str, object]:
    return {
        "id": str(audit.get("id") or f"audit-{_utc_timestamp()}"),
        "projectId": str(audit.get("projectId") or audit.get("project_id") or ""),
        "projectQuery": str(audit.get("projectQuery") or audit.get("project_query") or ""),
        "taskId": str(audit.get("taskId") or audit.get("task_id") or ""),
        "ticker": str(audit.get("ticker") or ""),
        "type": str(audit.get("type") or "verified-task"),
        "label": str(audit.get("label") or ""),
        "qualityBefore": str(audit.get("qualityBefore") or audit.get("quality_before") or "n/a"),
        "qualityAfter": str(audit.get("qualityAfter") or audit.get("quality_after") or "n/a"),
        "qualityDelta": str(audit.get("qualityDelta") or audit.get("quality_delta") or "n/a"),
        "at": str(audit.get("at") or _utc_timestamp()),
    }


def _write_project_evidence_audit(*, path: Path, audit: Mapping[str, object]) -> list[dict[str, object]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_project_evidence_audit(audit)
    audit_id = str(normalized.get("id") or "")
    existing = [entry for entry in _load_project_evidence_audits(path) if str(entry.get("id") or "") != audit_id]
    audits = [normalized, *existing][:500]
    path.write_text(json.dumps({"audits": audits}, ensure_ascii=False, indent=2), encoding="utf-8")
    return audits


def _clear_project_evidence_audits(path: Path) -> list[dict[str, object]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"audits": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    return []


VALID_TASK_STATUS_VALUES = {"to_collect", "collected", "verified"}


def _load_task_status_records(path: Path, *, project_id: str = "") -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        payload = payload.get("statuses", [])
    if not isinstance(payload, list):
        return []
    statuses = [_normalize_task_status_record(entry) for entry in payload if isinstance(entry, dict)]
    if project_id:
        statuses = [entry for entry in statuses if str(entry.get("projectId") or "") == project_id]
    return statuses


def _normalize_task_status_record(record: Mapping[str, object]) -> dict[str, object]:
    task_id = str(record.get("taskId") or record.get("task_id") or record.get("id") or "")
    status_value = str(record.get("status") or "to_collect")
    if status_value not in VALID_TASK_STATUS_VALUES:
        raise ValueError("Invalid task status value.")
    return {
        "id": str(record.get("id") or task_id),
        "projectId": str(record.get("projectId") or record.get("project_id") or ""),
        "taskId": task_id,
        "ticker": str(record.get("ticker") or ""),
        "status": status_value,
        "updatedAt": str(record.get("updatedAt") or record.get("updated_at") or _utc_timestamp()),
    }


def _write_task_status_record(*, path: Path, record: Mapping[str, object]) -> list[dict[str, object]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_task_status_record(record)
    record_id = str(normalized.get("id") or normalized.get("taskId") or "")
    existing = [entry for entry in _load_task_status_records(path) if str(entry.get("id") or "") != record_id]
    statuses = [normalized, *existing][:500]
    path.write_text(json.dumps({"statuses": statuses}, ensure_ascii=False, indent=2), encoding="utf-8")
    return statuses


def _clear_task_status_records(path: Path) -> list[dict[str, object]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"statuses": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    return []


def _write_run_record(
    *,
    path: Path,
    query: str,
    language: str,
    status: str,
    href: str = "",
    error: str = "",
    job_id: str = "",
    retry_of_job_id: str = "",
    attempt: int = 1,
    cancelled_at: str = "",
    queued_at: str = "",
    started_at: str = "",
    manifest_href: str = "",
    canonical_theme: str = "",
    candidate_tickers: Sequence[str] | None = None,
    candidate_coverage: Sequence[Mapping[str, object]] | None = None,
    evidence_gap_tasks: Sequence[Mapping[str, object]] | None = None,
    coverage_label: str = "",
    preflight_source: str = "",
    quality_score: int | None = None,
    quality_status: str = "",
) -> dict[str, object]:
    normalized_language = "zh" if language == "zh" else "en"
    queued_value = queued_at or _utc_timestamp()
    started_value = started_at or _utc_timestamp()
    completed_value = "" if status in {"queued", "running"} else _utc_timestamp()
    record: dict[str, object] = {
        "query": query,
        "language": normalized_language,
        "status": status,
        "href": href,
        "error": error,
        "job_id": job_id,
        "retry_of_job_id": retry_of_job_id,
        "attempt": attempt,
        "cancelled_at": cancelled_at,
        "queued_at": queued_value,
        "started_at": started_value,
        "completed_at": completed_value,
    }
    if manifest_href:
        record["manifest_href"] = manifest_href
    if canonical_theme:
        record["canonical_theme"] = canonical_theme
    if candidate_tickers is not None:
        record["candidate_tickers"] = list(candidate_tickers)
    if candidate_coverage is not None:
        record["candidate_coverage"] = [dict(item) for item in candidate_coverage]
    if evidence_gap_tasks is not None:
        record["evidence_gap_tasks"] = _evidence_gap_tasks_with_handoff(evidence_gap_tasks, href=href)
    if coverage_label:
        record["coverage_label"] = coverage_label
    if preflight_source:
        record["preflight_source"] = preflight_source
    if quality_score is not None:
        record["quality_score"] = quality_score
    if quality_status:
        record["quality_status"] = quality_status
    with RUN_RECORD_LOCK:
        existing = _read_run_records_unlocked(path)
        existing = [
            entry
            for entry in existing
            if not (
                entry.get("query") == query
                and entry.get("language") == normalized_language
                and entry.get("started_at") == started_value
            )
        ]
        _write_run_records_unlocked(path, [record, *existing][:50])
    return record


def _find_run_record(path: Path, *, job_id: str) -> dict[str, object] | None:
    for run in _load_run_records(path):
        if str(run.get("job_id") or "") == job_id:
            return run
    return None


def _cancel_run_record(path: Path, *, job_id: str) -> dict[str, object] | None:
    cancelled_value = _utc_timestamp()
    with RUN_RECORD_LOCK:
        runs = _read_run_records_unlocked(path)
        updated: list[dict[str, object]] = []
        cancelled: dict[str, object] | None = None
        for run in runs:
            if str(run.get("job_id") or "") == job_id:
                status = str(run.get("status") or "")
                if status in {"completed", "failed", "cancelled"}:
                    cancelled = dict(run)
                else:
                    cancelled = {
                        **run,
                        "status": "cancelled",
                        "href": "",
                        "error": "Job cancelled by user.",
                        "cancelled_at": cancelled_value,
                        "completed_at": cancelled_value,
                    }
                updated.append(cancelled)
            else:
                updated.append(run)
        if cancelled is None:
            return None
        _write_run_records_unlocked(path, updated[:50])
        return cancelled


def _run_manifest_summary(*, output_path: Path, directory: Path) -> dict[str, object]:
    manifest_path = output_path.parent / "analysis-manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(manifest, dict):
        return {}
    quality = manifest.get("quality")
    if not isinstance(quality, dict):
        quality = {}
    candidate_tickers = manifest.get("candidate_tickers")
    if not isinstance(candidate_tickers, list):
        candidate_tickers = []
    relative = os.path.relpath(manifest_path, start=directory).replace(os.sep, "/")
    return {
        "manifest_href": "/" + quote(relative, safe="/.-_"),
        "canonical_theme": str(manifest.get("canonical_theme") or ""),
        "candidate_tickers": [str(ticker) for ticker in candidate_tickers],
        "quality_score": _parse_quality_score(quality.get("score")),
        "quality_status": str(quality.get("status") or ""),
    }


def _preflight_run_metadata(payload: Mapping[str, object] | None) -> dict[str, object]:
    if not payload:
        return {}
    candidate_tickers = payload.get("candidate_tickers")
    if not isinstance(candidate_tickers, list):
        candidate_tickers = []
    candidate_coverage = payload.get("candidate_coverage")
    if not isinstance(candidate_coverage, list):
        candidate_coverage = []
    evidence_gap_tasks = payload.get("evidence_gap_tasks")
    if not isinstance(evidence_gap_tasks, list):
        evidence_gap_tasks = []
    metadata: dict[str, object] = {}
    canonical_theme = str(payload.get("canonical_theme") or "")
    coverage_label = str(payload.get("coverage_label") or "")
    preflight_source = str(payload.get("source") or "")
    if canonical_theme:
        metadata["canonical_theme"] = canonical_theme
    metadata["candidate_tickers"] = [str(ticker) for ticker in candidate_tickers]
    metadata["candidate_coverage"] = [
        dict(item) for item in candidate_coverage if isinstance(item, Mapping)
    ]
    metadata["evidence_gap_tasks"] = [
        dict(item) for item in evidence_gap_tasks if isinstance(item, Mapping)
    ]
    if coverage_label:
        metadata["coverage_label"] = coverage_label
    if preflight_source:
        metadata["preflight_source"] = preflight_source
    return metadata


def _merge_run_metadata(*metadata: Mapping[str, object]) -> dict[str, object]:
    merged: dict[str, object] = {}
    for item in metadata:
        for key, value in item.items():
            if key == "candidate_tickers":
                if value is not None:
                    merged[key] = list(value) if isinstance(value, list) else []
            elif key == "candidate_coverage":
                if value is not None:
                    merged[key] = [dict(item) for item in value] if isinstance(value, list) else []
            elif key == "evidence_gap_tasks":
                if value is not None:
                    merged[key] = [dict(item) for item in value] if isinstance(value, list) else []
            elif value not in ("", None):
                merged[key] = value
    return merged


def _evidence_gap_tasks_with_handoff(
    tasks: Sequence[Mapping[str, object]],
    *,
    href: str = "",
) -> list[dict[str, object]]:
    handoff_href = _evidence_import_handoff_href(href)
    enriched: list[dict[str, object]] = []
    for task in tasks:
        item = dict(task)
        if handoff_href and not item.get("import_handoff_href"):
            item["import_handoff_href"] = handoff_href
        enriched.append(item)
    return enriched


def _evidence_import_handoff_href(href: str) -> str:
    value = str(href or "").strip()
    if not value:
        return ""
    return value.split("#", 1)[0] + "#evidence-tasks"


def build_topic_resolution_preview(
    *,
    query: str,
    language: str,
    evidence: Sequence[EvidenceItem],
    fallback_tickers: Sequence[str],
    stock_universe: Sequence[StockUniverseEntry] | None = None,
) -> dict[str, object]:
    copy = _copy("zh" if language == "zh" else "en")
    resolved = resolve_topic(
        query,
        evidence,
        fallback_tickers=fallback_tickers,
        stock_universe=stock_universe or [],
        max_candidates=max(len(fallback_tickers), 12),
    )
    matched_evidence = _match_resolution_evidence(evidence, resolved)
    primary_count = sum(1 for item in matched_evidence if item.strength == "primary" or item.claim_type == "fact")
    risk_count = sum(1 for item in matched_evidence if item.direction == "negative" or item.claim_type in {"risk", "invalidation"})
    evidence_count = len(matched_evidence)
    candidate_coverage = _candidate_coverage_summary(evidence, resolved.candidate_tickers, copy)
    evidence_gap_tasks = _candidate_evidence_gap_tasks(candidate_coverage, query=resolved.original_query, copy=copy)
    return {
        "original_query": resolved.original_query,
        "intent": resolved.intent,
        "intent_label": _localized_intent_label(resolved.intent, copy),
        "canonical_theme": resolved.canonical_theme,
        "aliases": resolved.aliases,
        "expanded_query": resolved.expanded_query,
        "candidate_tickers": resolved.candidate_tickers,
        "candidate_coverage": candidate_coverage,
        "evidence_gap_tasks": evidence_gap_tasks,
        "coverage": {
            "evidence_count": evidence_count,
            "primary_count": primary_count,
            "risk_count": risk_count,
        },
        "coverage_label": f"{evidence_count} {copy['coverage_evidence_items']}",
        "expected_outputs": copy["expected_outputs_value"],
        "source": "backend",
    }


def _candidate_coverage_summary(
    evidence: Sequence[EvidenceItem],
    candidate_tickers: Sequence[str],
    copy: Mapping[str, str],
) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    for ticker in candidate_tickers:
        normalized = ticker.upper().lstrip("$")
        matched = [
            item
            for item in evidence
            if normalized in {item_ticker.upper().lstrip("$") for item_ticker in item.tickers}
        ]
        primary_count = sum(1 for item in matched if item.strength == "primary" or item.claim_type == "fact")
        risk_count = sum(1 for item in matched if item.direction == "negative" or item.claim_type in {"risk", "invalidation"})
        evidence_count = len(matched)
        summaries.append(
            {
                "ticker": normalized,
                "evidence_count": evidence_count,
                "primary_count": primary_count,
                "risk_count": risk_count,
                "coverage_label": f"{evidence_count} {copy['coverage_evidence_items']}",
            }
        )
    return summaries


def _candidate_evidence_gap_tasks(
    candidate_coverage: Sequence[Mapping[str, object]],
    *,
    query: str,
    copy: Mapping[str, str],
    limit: int = 6,
) -> list[dict[str, object]]:
    compact_query = " ".join(str(query or "").split())
    first_query_term = compact_query.split()[0] if compact_query else "evidence"
    tasks: list[dict[str, object]] = []
    for item in candidate_coverage:
        ticker = str(item.get("ticker") or "").strip().upper().lstrip("$")
        if not ticker:
            continue
        primary_count = _safe_int(item.get("primary_count"))
        risk_count = _safe_int(item.get("risk_count"))
        if primary_count <= 0:
            tasks.append(
                {
                    "ticker": ticker,
                    "gap": "missing_primary_source",
                    "priority": "high",
                    "source_target": "Primary filing, company release, audited fact, or official investor material",
                    "search_prompt": f"{ticker} primary filing {first_query_term}",
                    "copy_label": copy["copy_evidence_gap_prompt"],
                }
            )
        if len(tasks) >= limit:
            break
        if risk_count <= 0:
            tasks.append(
                {
                    "ticker": ticker,
                    "gap": "missing_risk_coverage",
                    "priority": "medium",
                    "source_target": "Risk, negative, or invalidation evidence from filings, earnings calls, or credible third-party sources",
                    "search_prompt": f"{ticker} risk {compact_query or first_query_term}",
                    "copy_label": copy["copy_evidence_gap_prompt"],
                }
            )
        if len(tasks) >= limit:
            break
    return tasks[:limit]


def _safe_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _match_resolution_evidence(evidence: Sequence[EvidenceItem], resolved) -> list[EvidenceItem]:
    query_tokens = set(tokenize(" ".join([resolved.expanded_query, resolved.canonical_theme, *resolved.aliases])))
    candidate_tickers = {ticker.upper().lstrip("$") for ticker in resolved.candidate_tickers}
    matched: list[EvidenceItem] = []
    for item in evidence:
        item_tickers = {ticker.upper().lstrip("$") for ticker in item.tickers}
        if candidate_tickers and item_tickers & candidate_tickers:
            matched.append(item)
            continue
        item_tokens = set(tokenize(" ".join([item.search_text, " ".join(item.themes)])))
        if query_tokens and query_tokens & item_tokens:
            matched.append(item)
    return matched


def _localized_intent_label(intent: str, copy: Mapping[str, str]) -> str:
    return {
        "industry": copy["intent_industry"],
        "sector": copy["intent_sector"],
        "ticker": copy["intent_ticker"],
        "theme": copy["intent_theme"],
    }.get(intent, intent or copy["intent_theme"])


def _build_dashboard_handler(
    directory: Path,
    analyze_callback: AnalyzeCallback | None,
    *,
    ingest_callback: IngestCallback | None = None,
    resolve_callback: ResolveCallback | None = None,
):
    class DashboardRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/runs":
                self._handle_runs_api()
                return
            if parsed.path == "/api/analyze-jobs":
                self._handle_analyze_jobs_api(parsed.query)
                return
            if parsed.path == "/api/projects":
                self._handle_projects_api()
                return
            if parsed.path == "/api/project-events":
                self._handle_project_events_api(parsed.query)
                return
            if parsed.path == "/api/project-evidence-audits":
                self._handle_project_evidence_audits_api(parsed.query)
                return
            if parsed.path == "/api/task-statuses":
                self._handle_task_statuses_api(parsed.query)
                return
            if parsed.path == "/api/resolve-topic":
                self._handle_resolve_topic_api(parsed.query)
                return
            if parsed.path == "/analyze":
                self._handle_analyze(parsed.query)
                return
            super().do_GET()

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/projects":
                self._handle_projects_api()
                return
            if parsed.path == "/api/project-events":
                self._handle_project_events_api("")
                return
            if parsed.path == "/api/project-evidence-audits":
                self._handle_project_evidence_audits_api("")
                return
            if parsed.path == "/api/task-statuses":
                self._handle_task_statuses_api("")
                return
            if parsed.path == "/api/analyze-jobs":
                self._handle_analyze_jobs_api("")
                return
            if parsed.path == "/ingest-evidence":
                self._handle_ingest_evidence()
                return
            self.send_error(404, "Unknown POST endpoint.")

        def _run_analysis_job(
            self,
            *,
            query: str,
            language: str,
            job_id: str,
            retry_of_job_id: str = "",
            attempt: int = 1,
            queued_at: str,
            started_at: str,
            preflight_metadata: Mapping[str, object] | None = None,
        ) -> None:
            if analyze_callback is None:
                return
            run_records_path = directory / "runs.json"
            preflight = dict(preflight_metadata or {})
            running_record = _write_run_record(
                path=run_records_path,
                query=query,
                language=language,
                status="running",
                job_id=job_id,
                retry_of_job_id=retry_of_job_id,
                attempt=attempt,
                queued_at=queued_at,
                started_at=started_at,
                **preflight,
            )
            try:
                output = analyze_callback(query=query, language=language)
            except Exception as exc:
                if (_find_run_record(run_records_path, job_id=job_id) or {}).get("status") == "cancelled":
                    return
                _write_run_record(
                    path=run_records_path,
                    query=query,
                    language=language,
                    status="failed",
                    error=str(exc),
                    job_id=job_id,
                    retry_of_job_id=retry_of_job_id,
                    attempt=attempt,
                    queued_at=str(running_record.get("queued_at", "")),
                    started_at=str(running_record.get("started_at", "")),
                    **preflight,
                )
                return

            if (_find_run_record(run_records_path, job_id=job_id) or {}).get("status") == "cancelled":
                return

            relative = os.path.relpath(output, start=directory).replace(os.sep, "/")
            href = "/" + quote(relative, safe="/.-_")
            manifest_summary = _run_manifest_summary(output_path=output, directory=directory)
            completed_metadata = _merge_run_metadata(preflight, manifest_summary)
            _write_run_record(
                path=run_records_path,
                query=query,
                language=language,
                status="completed",
                href=href,
                job_id=job_id,
                retry_of_job_id=retry_of_job_id,
                attempt=attempt,
                queued_at=str(running_record.get("queued_at", "")),
                started_at=str(running_record.get("started_at", "")),
                **completed_metadata,
            )

        def _handle_analyze_jobs_api(self, query_string: str) -> None:
            if analyze_callback is None:
                self._send_json({"error": "Theme analysis is not configured for this server."}, status=501)
                return
            if self.command == "GET":
                params = parse_qs(query_string)
                requested_job_id = params.get("jobId", [""])[0].strip() or params.get("job_id", [""])[0].strip()
                runs = _load_run_records(directory / "runs.json")
                if requested_job_id:
                    for run in runs:
                        if str(run.get("job_id") or "") == requested_job_id:
                            self._send_json({"job": run})
                            return
                    self._send_json({"error": "Job not found."}, status=404)
                    return
                self._send_json({"runs": runs})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                payload = json.loads(raw_body or "{}")
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON payload."}, status=400)
                return
            if not isinstance(payload, dict):
                self._send_json({"error": "Invalid JSON payload."}, status=400)
                return
            if payload.get("cancel") is True:
                cancel_job_id = str(payload.get("job_id") or payload.get("jobId") or "").strip()
                if not cancel_job_id:
                    self._send_json({"error": "Missing required job_id."}, status=400)
                    return
                cancelled = _cancel_run_record(directory / "runs.json", job_id=cancel_job_id)
                if cancelled is None:
                    self._send_json({"error": "Job not found."}, status=404)
                    return
                self._send_json({"job": cancelled})
                return
            retry_job_id = str(payload.get("retry_job_id") or payload.get("retryJobId") or "").strip()
            retry_source: dict[str, object] | None = None
            if retry_job_id:
                for run in _load_run_records(directory / "runs.json"):
                    if str(run.get("job_id") or "") == retry_job_id:
                        retry_source = run
                        break
                if retry_source is None:
                    self._send_json({"error": "Job not found."}, status=404)
                    return

            query = str(payload.get("query") or (retry_source or {}).get("query") or "").strip()
            language = str(payload.get("language") or (retry_source or {}).get("language") or "en").strip() or "en"
            normalized_language = "zh" if language == "zh" else "en"
            if not query:
                self._send_json({"error": "Missing required query."}, status=400)
                return

            preflight_payload: Mapping[str, object] | None = None
            if retry_source is not None:
                preflight_payload = retry_source
            elif resolve_callback is not None:
                try:
                    preflight_payload = dict(resolve_callback(query=query, language=normalized_language))
                except Exception:
                    preflight_payload = None
            preflight_metadata = _preflight_run_metadata(preflight_payload)
            job_id = "job-" + uuid4().hex[:12]
            attempt = int((retry_source or {}).get("attempt") or 1) + 1 if retry_source else 1
            queued_record = _write_run_record(
                path=directory / "runs.json",
                query=query,
                language=normalized_language,
                status="queued",
                job_id=job_id,
                retry_of_job_id=retry_job_id,
                attempt=attempt,
                **preflight_metadata,
            )
            worker = threading.Thread(
                target=self._run_analysis_job,
                kwargs={
                    "query": query,
                    "language": normalized_language,
                    "job_id": job_id,
                    "retry_of_job_id": retry_job_id,
                    "attempt": attempt,
                    "queued_at": str(queued_record.get("queued_at", "")),
                    "started_at": str(queued_record.get("started_at", "")),
                    "preflight_metadata": preflight_metadata,
                },
                daemon=True,
            )
            worker.start()
            job = dict(queued_record)
            job["poll_href"] = "/api/runs"
            self._send_json({"job": job}, status=202)

        def _handle_analyze(self, query_string: str) -> None:
            if analyze_callback is None:
                self.send_error(501, "Theme analysis is not configured for this server.")
                return

            params = parse_qs(query_string)
            query = params.get("query", [""])[0].strip()
            language = params.get("language", ["en"])[0].strip() or "en"
            if not query:
                self.send_error(400, "Missing required query parameter.")
                return

            run_records_path = directory / "runs.json"
            queued_record = _write_run_record(
                path=run_records_path,
                query=query,
                language=language,
                status="queued",
                job_id="sync-" + uuid4().hex[:12],
            )
            running_record = _write_run_record(
                path=run_records_path,
                query=query,
                language=language,
                status="running",
                job_id=str(queued_record.get("job_id", "")),
                queued_at=str(queued_record.get("queued_at", "")),
                started_at=str(queued_record.get("started_at", "")),
            )
            try:
                output = analyze_callback(query=query, language=language)
            except Exception as exc:
                _write_run_record(
                    path=run_records_path,
                    query=query,
                    language=language,
                    status="failed",
                    error=str(exc),
                    job_id=str(running_record.get("job_id", "")),
                    queued_at=str(running_record.get("queued_at", "")),
                    started_at=str(running_record.get("started_at", "")),
                )
                copy = _copy("zh" if language == "zh" else "en")
                retry_href = "/analyze?" + urlencode({"query": query, "language": "zh" if language == "zh" else "en"})
                home_href = "/index.zh.html" if language == "zh" else "/index.html"
                body = _render_analysis_error_page(
                    title=copy["analysis_failed_title"],
                    message=copy["analysis_failed_recovery"],
                    detail=f"Theme analysis failed: {exc}",
                    retry_label=copy["retry_analysis"],
                    retry_href=retry_href,
                    home_label=copy["back_home"],
                    home_href=home_href,
                    language="zh" if language == "zh" else "en",
                )
                encoded = body.encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                return

            relative = os.path.relpath(output, start=directory).replace(os.sep, "/")
            href = "/" + quote(relative, safe="/.-_")
            manifest_summary = _run_manifest_summary(output_path=output, directory=directory)
            _write_run_record(
                path=run_records_path,
                query=query,
                language=language,
                status="completed",
                href=href,
                job_id=str(running_record.get("job_id", "")),
                queued_at=str(running_record.get("queued_at", "")),
                started_at=str(running_record.get("started_at", "")),
                **manifest_summary,
            )
            self.send_response(303)
            self.send_header("Location", href)
            self.end_headers()

        def _handle_runs_api(self) -> None:
            payload = json.dumps({"runs": _load_run_records(directory / "runs.json")}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _handle_projects_api(self) -> None:
            path = directory / "projects.json"
            audits_path = directory / "project_evidence_audits.json"
            task_statuses_path = directory / "task_statuses.json"
            if self.command == "GET":
                projects = _project_records_with_evidence_quality_summary(
                    _load_project_records(path),
                    audits_path,
                    task_statuses_path,
                )
                self._send_json({"projects": projects})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                payload = json.loads(raw_body or "{}")
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON payload."}, status=400)
                return
            if not isinstance(payload, dict):
                self._send_json({"error": "Invalid JSON payload."}, status=400)
                return
            if payload.get("clear") is True:
                self._send_json({"projects": _clear_project_records(path)})
                return
            project = payload.get("project")
            if not isinstance(project, dict):
                self._send_json({"error": "Missing project payload."}, status=400)
                return
            projects = _project_records_with_evidence_quality_summary(
                _write_project_record(path=path, project=project),
                audits_path,
                task_statuses_path,
            )
            self._send_json({"projects": projects})

        def _handle_project_events_api(self, query_string: str) -> None:
            path = directory / "project_review_events.json"
            if self.command == "GET":
                params = parse_qs(query_string)
                project_id = params.get("projectId", [""])[0].strip()
                self._send_json({"events": _load_project_review_events(path, project_id=project_id)})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                payload = json.loads(raw_body or "{}")
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON payload."}, status=400)
                return
            if not isinstance(payload, dict):
                self._send_json({"error": "Invalid JSON payload."}, status=400)
                return
            if payload.get("clear") is True:
                self._send_json({"events": _clear_project_review_events(path)})
                return
            event = payload.get("event")
            if not isinstance(event, dict):
                self._send_json({"error": "Missing project review event payload."}, status=400)
                return
            self._send_json({"events": _write_project_review_event(path=path, event=event)})

        def _handle_project_evidence_audits_api(self, query_string: str) -> None:
            path = directory / "project_evidence_audits.json"
            if self.command == "GET":
                params = parse_qs(query_string)
                project_id = params.get("projectId", [""])[0].strip()
                audits = _load_project_evidence_audits(path, project_id=project_id)
                self._send_json({"audits": audits, "summary": _project_evidence_audit_summary(audits)})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                payload = json.loads(raw_body or "{}")
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON payload."}, status=400)
                return
            if not isinstance(payload, dict):
                self._send_json({"error": "Invalid JSON payload."}, status=400)
                return
            if payload.get("clear") is True:
                audits = _clear_project_evidence_audits(path)
                self._send_json({"audits": audits, "summary": _project_evidence_audit_summary(audits)})
                return
            audit = payload.get("audit")
            if not isinstance(audit, dict):
                self._send_json({"error": "Missing project evidence audit payload."}, status=400)
                return
            audits = _write_project_evidence_audit(path=path, audit=audit)
            self._send_json({"audits": audits, "summary": _project_evidence_audit_summary(audits)})

        def _handle_task_statuses_api(self, query_string: str) -> None:
            path = directory / "task_statuses.json"
            if self.command == "GET":
                params = parse_qs(query_string)
                project_id = params.get("projectId", [""])[0].strip()
                self._send_json({"statuses": _load_task_status_records(path, project_id=project_id)})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                payload = json.loads(raw_body or "{}")
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON payload."}, status=400)
                return
            if not isinstance(payload, dict):
                self._send_json({"error": "Invalid JSON payload."}, status=400)
                return
            if payload.get("clear") is True:
                self._send_json({"statuses": _clear_task_status_records(path)})
                return
            record = payload.get("status")
            if not isinstance(record, dict):
                self._send_json({"error": "Missing task status payload."}, status=400)
                return
            try:
                statuses = _write_task_status_record(path=path, record=record)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json({"statuses": statuses})

        def _handle_resolve_topic_api(self, query_string: str) -> None:
            params = parse_qs(query_string)
            query = params.get("query", [""])[0].strip()
            language = params.get("language", ["en"])[0].strip() or "en"
            if not query:
                self._send_json({"error": "Missing required query parameter."}, status=400)
                return
            try:
                if resolve_callback is not None:
                    payload = dict(resolve_callback(query=query, language=language))
                else:
                    payload = build_topic_resolution_preview(
                        query=query,
                        language=language,
                        evidence=[],
                        fallback_tickers=[],
                        stock_universe=[],
                    )
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
                return
            self._send_json(payload)

        def _send_json(self, payload: Mapping[str, object], *, status: int = 200) -> None:
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _handle_ingest_evidence(self) -> None:
            if ingest_callback is None:
                self.send_error(501, "Evidence import is not configured for this server.")
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            raw_body = self.rfile.read(length).decode("utf-8") if length else ""
            form = {
                key: values[0].strip()
                for key, values in parse_qs(raw_body, keep_blank_values=True).items()
                if values
            }
            try:
                output = ingest_callback(form)
            except Exception as exc:
                language = form.get("language", "en")
                copy = _copy("zh" if language == "zh" else "en")
                body = _render_error_page(
                    title=copy["import_failed_title"],
                    message=copy["import_failed_recovery"],
                    detail=str(exc),
                    language="zh" if language == "zh" else "en",
                )
                encoded = body.encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                return

            relative = os.path.relpath(output, start=directory).replace(os.sep, "/")
            project_href = "/" + quote(relative, safe="/.-_")
            body = output.read_text(encoding="utf-8")
            language = form.get("language", "en")
            copy = _copy("zh" if language == "zh" else "en")
            notice = copy["evidence_imported"]
            source_title = form.get("source_title", "")
            ticker = form.get("ticker", "").upper()
            raw_gap = form.get("task_gap", "") or _infer_gap_key_from_claim(form.get("claim", ""))
            task_id = form.get("task_id", "") or form.get("id", "") or _task_id(
                ticker=ticker,
                gap=raw_gap,
                search_prompt=f"{ticker} {raw_gap} {form.get('query', '')}",
            )
            resolved_gap = _infer_resolved_gap_from_claim(form.get("claim", ""), copy)
            quality_after_score = _extract_quality_score_from_html(body, copy)
            impact = _render_import_impact(
                {
                    "id": form.get("id", ""),
                    "claim": form.get("claim", ""),
                    "summary": form.get("summary", ""),
                    "ticker": form.get("ticker", ""),
                },
                copy,
                quality_before_score=form.get("quality_before_score", ""),
                quality_after_score=quality_after_score,
            )
            _write_task_status_record(
                path=directory / "task_statuses.json",
                record={
                    "id": task_id,
                    "projectId": project_href,
                    "taskId": task_id,
                    "ticker": ticker,
                    "status": "verified",
                    "updatedAt": _utc_timestamp(),
                },
            )
            _write_project_evidence_audit(
                path=directory / "project_evidence_audits.json",
                audit={
                    "id": f"import-{task_id}",
                    "projectId": project_href,
                    "projectQuery": form.get("query", ""),
                    "taskId": task_id,
                    "ticker": ticker,
                    "type": "import-verified-task",
                    "label": copy["verified_task_audit_trail"],
                    "qualityBefore": _format_quality_score(form.get("quality_before_score", ""), copy),
                    "qualityAfter": _format_quality_score(quality_after_score, copy),
                    "qualityDelta": _format_quality_delta(form.get("quality_before_score", ""), quality_after_score, copy),
                    "at": _utc_timestamp(),
                },
            )
            banner = (
                f'<div class="note" role="status"><strong>{escape(notice)}</strong>'
                f'<p><strong>{escape(copy["imported_evidence"])}:</strong> {escape(source_title or "n/a")}</p>'
                f'<p>{escape(resolved_gap)}</p>{impact}</div>'
            )
            body = body.replace('<main id="main">', f'<main id="main">\n      {banner}', 1)
            output.write_text(body, encoding="utf-8")
            self.send_response(303)
            self.send_header("Location", project_href)
            self.end_headers()

    return DashboardRequestHandler


def _render_analysis_error_page(
    *,
    title: str,
    message: str,
    detail: str,
    retry_label: str,
    retry_href: str,
    home_label: str,
    home_href: str,
    language: str,
) -> str:
    html_lang = "zh-CN" if language == "zh" else "en"
    return f"""<!doctype html>
<html lang="{html_lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{ margin: 0; background: #f5f2eb; color: #18212b; font: 16px/1.55 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ width: min(760px, calc(100vw - 32px)); margin: 48px auto; background: #fffdf8; border: 1px solid #d9ded9; border-radius: 8px; padding: 24px; box-shadow: 0 16px 45px rgba(24, 33, 43, 0.08); }}
    .detail {{ padding: 12px; border-radius: 8px; background: #fff1d6; color: #7c3d12; word-break: break-word; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }}
    a {{ display: inline-flex; align-items: center; min-height: 44px; border-radius: 8px; padding: 0 0.9rem; font-weight: 760; text-decoration: none; }}
    .primary {{ background: #163f3b; color: #fff; }}
    .secondary {{ background: #ffffff; color: #18212b; border: 1px solid #d9ded9; }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(title)}</h1>
    <p>{escape(message)}</p>
    <p class="detail">{escape(detail)}</p>
    <div class="actions">
      <a class="primary" href="{escape(retry_href)}">{escape(retry_label)}</a>
      <a class="secondary" href="{escape(home_href)}">{escape(home_label)}</a>
    </div>
  </main>
</body>
</html>
"""


def _render_error_page(*, title: str, message: str, detail: str, language: str) -> str:
    html_lang = "zh-CN" if language == "zh" else "en"
    back = "返回上一页" if language == "zh" else "Go back"
    return f"""<!doctype html>
<html lang="{html_lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{ margin: 0; background: #f5f2eb; color: #18212b; font: 16px/1.55 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ width: min(760px, calc(100vw - 32px)); margin: 48px auto; background: #fffdf8; border: 1px solid #d9ded9; border-radius: 8px; padding: 24px; }}
    .detail {{ padding: 12px; border-radius: 8px; background: #fff1d6; color: #7c3d12; word-break: break-word; }}
    button {{ min-height: 44px; border: 0; border-radius: 8px; background: #163f3b; color: white; padding: 0.65rem 0.9rem; font-weight: 760; cursor: pointer; }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(title)}</h1>
    <p>{escape(message)}</p>
    <p class="detail">{escape(detail)}</p>
    <button type="button" onclick="history.back()">{escape(back)}</button>
  </main>
</body>
</html>
"""


def _infer_gap_key_from_claim(claim: str) -> str:
    normalized = claim.lower()
    if "primary" in normalized or "source" in normalized:
        return "missing_primary_source"
    elif "risk" in normalized or "invalidation" in normalized:
        return "missing_risk_evidence"
    return "missing_direct_ticker_evidence"


def _infer_resolved_gap_from_claim(claim: str, copy: Mapping[str, str]) -> str:
    gap = _localize_gap_label(_infer_gap_key_from_claim(claim), copy)
    return f"{copy['resolved_gap_prefix']}{gap}"


def _search_blob(row: Mapping[str, object]) -> str:
    parts: list[str] = []
    for value in row.values():
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        else:
            parts.append(str(value))
    return " ".join(parts)


def _render_list(values: object) -> str:
    items = [str(value) for value in values if str(value).strip()] if isinstance(values, list) else []
    if not items:
        return "<p>No items found.</p>"
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items[:4]) + "</ul>"


def _parse_readiness_rows(markdown: str) -> list[TableRow]:
    rows = _parse_first_table(markdown, expected_first_header="Rank")
    parsed = []
    for row in rows:
        parsed.append(
            {
                "ticker": row.get("Ticker", ""),
                "status": row.get("Status", ""),
                "evidence": row.get("Evidence", ""),
                "primary": row.get("Primary/Fact", ""),
                "risk": row.get("Risk", ""),
                "flags": row.get("Flags", ""),
            }
        )
    return parsed


def _parse_pack_rows(markdown: str) -> list[TableRow]:
    rows = _parse_first_table(markdown, expected_first_header="Ticker")
    parsed = []
    for row in rows:
        parsed.append(
            {
                "ticker": row.get("Ticker", ""),
                "status": row.get("Status", ""),
                "rating": row.get("Serenity Rating", ""),
                "confidence": row.get("Confidence", ""),
                "gaps": row.get("Key Gaps", ""),
                "memo_file": row.get("Memo File", ""),
                "evidence": row.get("Evidence", ""),
                "primary": row.get("Primary/Fact", ""),
                "risk": row.get("Risk", ""),
                "flags": row.get("Flags", ""),
            }
        )
    return parsed


def _parse_first_table(markdown: str, *, expected_first_header: str) -> list[TableRow]:
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        headers = _split_table_row(line)
        if not headers or headers[0] != expected_first_header:
            continue
        if index + 1 >= len(lines) or not lines[index + 1].startswith("|"):
            continue
        rows = []
        for data_line in lines[index + 2 :]:
            if not data_line.startswith("|"):
                break
            values = _split_table_row(data_line)
            if len(values) != len(headers):
                continue
            rows.append(dict(zip(headers, values)))
        return rows
    return []


def _split_table_row(line: str) -> list[str]:
    return [cell.strip().replace("`", "") for cell in line.strip().strip("|").split("|")]


def _copy_pack_for_serving(source_dir: Path, destination_dir: Path) -> Path:
    source = source_dir.resolve()
    destination = destination_dir.resolve()
    if source == destination:
        return destination_dir

    destination_dir.parent.mkdir(parents=True, exist_ok=True)
    if destination_dir.exists():
        try:
            shutil.rmtree(destination_dir)
        except FileNotFoundError:
            if destination_dir.exists():
                shutil.rmtree(destination_dir)
    shutil.copytree(source_dir, destination_dir)
    return destination_dir


def _copy_reports_for_serving(output_dir: Path) -> None:
    local_reports_dir = output_dir / "reports"
    source_dir = local_reports_dir if local_reports_dir.exists() else Path("output") / "reports"
    source = source_dir.resolve()
    destination_dir = local_reports_dir
    destination = destination_dir.resolve()
    if not source_dir.exists() or source == destination:
        return

    report_names = ["deliverable-research-report.md", "universe-coverage-matrix.md", "evidence-acquisition-queue.md"]
    for report_name in report_names:
        source_path = source_dir / report_name
        if not source_path.exists():
            continue
        destination_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_dir / report_name)


def _attach_memo_hrefs(memo_rows: Sequence[Mapping[str, str]], pack_dir: Path, output_dir: Path) -> list[TableRow]:
    rows: list[TableRow] = []
    for row in memo_rows:
        copied = dict(row)
        memo_file = copied.get("memo_file", "")
        if memo_file and memo_file != "not generated":
            copied["memo_href"] = _relative_href(output_dir, pack_dir / memo_file)
        rows.append(copied)
    return rows


def _load_memo_previews(
    memo_rows: Sequence[Mapping[str, str]],
    pack_dir: Path,
    output_dir: Path,
) -> list[TableRow]:
    previews: list[TableRow] = []
    for row in memo_rows:
        memo_file = row.get("memo_file", "")
        if not memo_file or memo_file == "not generated":
            continue
        memo_path = pack_dir / memo_file
        if not memo_path.exists():
            continue
        markdown = memo_path.read_text(encoding="utf-8")
        preview = {
            "ticker": row.get("ticker", ""),
            "memo_file": memo_file,
            "memo_href": _relative_href(output_dir, memo_path),
            "score": _extract_first_bold_value(markdown, ["Composite research score", "综合研究评分"]) or "n/a",
            "rating": _extract_first_bold_value(markdown, ["Serenity rating", "Serenity 评级"]) or row.get("rating", ""),
            "confidence": _extract_first_bold_value(markdown, ["Research confidence", "研究置信层级"]) or row.get("confidence", ""),
            "gaps": _extract_first_bold_value(markdown, ["Key gaps", "关键短板"]) or row.get("gaps", ""),
            "thesis": _extract_first_section_text(markdown, ["Thesis Summary", "论点摘要"]),
            "coverage": _extract_coverage_summary(markdown),
            "risks": _extract_first_bullets(markdown, ["Skeptic Review", "怀疑者复核"]),
            "invalidations": _extract_first_bullets(markdown, ["Invalidation Conditions", "失效条件"]),
        }
        previews.append(preview)
    return previews


def _parse_primary_sources(markdown: str) -> list[TableRow]:
    sources: list[TableRow] = []
    current: TableRow | None = None
    source_pattern = re.compile(r"^- \*\*(?P<id>[^*]+)\*\* \[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\)")
    detail_pattern = re.compile(r"^  - \*\*(?P<label>[^:]+):\*\* (?P<value>.*)$")
    for line in markdown.splitlines():
        source_match = source_pattern.match(line)
        if source_match:
            if current:
                sources.append(current)
            current = {
                "id": source_match.group("id").strip(),
                "title": source_match.group("title").strip(),
                "url": source_match.group("url").strip(),
                "tickers": "",
                "memos": "",
                "claim": "",
                "excerpt": "",
            }
            continue
        detail_match = detail_pattern.match(line)
        if detail_match and current is not None:
            label = detail_match.group("label").strip().lower()
            value = detail_match.group("value").strip()
            if label == "tickers":
                current["tickers"] = value
            elif label == "used in memos":
                current["memos"] = value
            elif label == "claim":
                current["claim"] = value
            elif label == "source excerpt":
                current["excerpt"] = value
    if current:
        sources.append(current)
    return sources


def _extract_bold_value(markdown: str, label: str) -> str:
    match = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", markdown)
    return match.group(1).strip() if match else ""


def _extract_first_bold_value(markdown: str, labels: Sequence[str]) -> str:
    for label in labels:
        value = _extract_bold_value(markdown, label)
        if value:
            return value
    return ""


def _extract_section_text(markdown: str, heading: str) -> str:
    lines = _extract_section_lines(markdown, heading)
    paragraphs = [line.strip() for line in lines if line.strip() and not line.strip().startswith("|")]
    return " ".join(paragraphs).strip()


def _extract_first_section_text(markdown: str, headings: Sequence[str]) -> str:
    for heading in headings:
        value = _extract_section_text(markdown, heading)
        if value:
            return value
    return ""


def _extract_coverage_summary(markdown: str) -> str:
    section = "\n".join(
        _extract_first_section_lines(markdown, ["Source Coverage", "来源覆盖"])
    )
    return _extract_first_bold_value(section, ["Coverage counts", "覆盖统计"]) or _extract_first_section_text(
        markdown,
        ["Source Coverage", "来源覆盖"],
    )


def _extract_bullets(markdown: str, heading: str) -> list[str]:
    lines = _extract_section_lines(markdown, heading)
    return [line.strip()[2:].strip() for line in lines if line.strip().startswith("- ")]


def _extract_first_bullets(markdown: str, headings: Sequence[str]) -> list[str]:
    for heading in headings:
        bullets = _extract_bullets(markdown, heading)
        if bullets:
            return bullets
    return []


def _extract_first_section_lines(markdown: str, headings: Sequence[str]) -> list[str]:
    for heading in headings:
        lines = _extract_section_lines(markdown, heading)
        if lines:
            return lines
    return []


def _extract_section_lines(markdown: str, heading: str) -> list[str]:
    lines = markdown.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == f"## {heading}":
            start = index + 1
            break
    if start is None:
        return []
    section = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        section.append(line)
    return section


def _relative_href(output_dir: Path, target: Path) -> str:
    return os.path.relpath(target, start=output_dir).replace(os.sep, "/")


def _to_int(value: str) -> int:
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return 0
