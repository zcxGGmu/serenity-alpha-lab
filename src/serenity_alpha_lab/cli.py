from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Sequence

from .acquisition_queue import build_acquisition_queue, render_acquisition_queue_markdown
from .coverage_matrix import build_coverage_matrix, render_coverage_matrix_markdown
from .evidence_audit import audit_evidence, render_audit_markdown
from .evidence import dedupe_evidence, load_evidence_files, write_evidence_jsonl
from .evidence_intake import append_intake_evidence, build_intake_evidence, parse_factor_impacts
from .financial_metrics import build_metrics_catalog, render_metrics_catalog_json
from .github_importer import fetch_repo_documents, import_github_repos, load_repo_specs
from .memo import generate_memo
from .memo_pack import build_memo_pack, write_memo_pack
from .official_report import load_official_report_specs, official_report_specs_to_evidence
from .readiness import assess_batch_readiness, render_readiness_markdown
from .report_safety import render_report_safety_markdown, scan_report_safety
from .retrieval import retrieve
from .scoring import score_research_question
from .sec_companyfacts import companyfacts_to_evidence, load_companyfacts_json, load_companyfact_specs
from .source_coverage import assess_source_coverage, render_source_coverage_markdown
from .stock_universe import load_stock_universe
from .summary_enrichment import enrich_evidence_summaries
from .ticker_resolution import load_ticker_resolution_rules, resolve_evidence_tickers
from .topic_resolver import resolve_topic
from .ui import build_dashboard, build_topic_resolution_preview, serve_dashboard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a Serenity Alpha Lab research memo.")
    parser.add_argument("--data", required=True, nargs="+", help="Path(s) to evidence JSONL.")
    parser.add_argument("--query", required=True, help="Research query, theme, or question.")
    parser.add_argument("--ticker", default=None, help="Optional ticker focus.")
    parser.add_argument("--out", required=True, help="Markdown memo output path.")
    parser.add_argument("--limit", type=int, default=12, help="Maximum evidence items to include.")
    return parser


def build_import_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import Serenity-related GitHub repositories as evidence JSONL.")
    parser.add_argument("import-github")
    parser.add_argument("--repos", required=True, help="Path to GitHub repo manifest JSON.")
    parser.add_argument("--out", required=True, help="Output evidence JSONL path.")
    return parser


def build_import_sec_companyfacts_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import local SEC companyfacts JSON as primary evidence.")
    parser.add_argument("import-sec-companyfacts")
    parser.add_argument("--sources", required=True, help="Path to SEC companyfacts source manifest JSON.")
    parser.add_argument("--out", required=True, help="Output primary evidence JSONL path.")
    return parser


def build_import_official_report_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import official report excerpts as primary evidence.")
    parser.add_argument("import-official-report")
    parser.add_argument("--sources", required=True, help="Path to official report source manifest JSON.")
    parser.add_argument("--out", required=True, help="Output primary evidence JSONL path.")
    return parser


def build_financial_metrics_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a source-backed financial metrics catalog for the UI.")
    parser.add_argument("build-financial-metrics")
    parser.add_argument("--data", required=True, nargs="+", help="Path(s) to evidence JSONL.")
    parser.add_argument(
        "--out",
        default="config/financial_metrics.json",
        help="Output metrics catalog JSON path.",
    )
    return parser


def build_scan_report_safety_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan generated reports for investment-advice guardrail violations.")
    parser.add_argument("scan-report-safety")
    parser.add_argument("--reports", required=True, nargs="+", help="Generated Markdown report path(s) to scan.")
    parser.add_argument("--out", required=True, help="Markdown safety scan output path.")
    return parser


def build_audit_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit evidence JSONL quality and coverage.")
    parser.add_argument("audit-evidence")
    parser.add_argument("--data", required=True, nargs="+", help="Path(s) to evidence JSONL.")
    parser.add_argument("--ticker", default=None, help="Optional ticker focus.")
    parser.add_argument("--out", required=True, help="Markdown audit report output path.")
    return parser


def build_resolve_tickers_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve placeholder evidence to concrete tickers.")
    parser.add_argument("resolve-tickers")
    parser.add_argument("--data", required=True, nargs="+", help="Path(s) to evidence JSONL.")
    parser.add_argument("--rules", required=True, help="Ticker resolution rules JSON path.")
    parser.add_argument("--out", required=True, help="Output enriched evidence JSONL path.")
    return parser


def build_enrich_summaries_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Enrich weak evidence summaries deterministically.")
    parser.add_argument("enrich-summaries")
    parser.add_argument("--data", required=True, nargs="+", help="Path(s) to evidence JSONL.")
    parser.add_argument("--out", required=True, help="Output summary-enriched evidence JSONL path.")
    return parser


def build_check_coverage_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check retrieved source coverage for a query/ticker pair.")
    parser.add_argument("check-coverage")
    parser.add_argument("--data", required=True, nargs="+", help="Path(s) to evidence JSONL.")
    parser.add_argument("--query", required=True, help="Research query, theme, or question.")
    parser.add_argument("--ticker", default=None, help="Optional ticker focus.")
    parser.add_argument("--out", required=True, help="Markdown coverage report output path.")
    parser.add_argument("--limit", type=int, default=12, help="Maximum evidence items to retrieve.")
    return parser


def build_scan_readiness_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan source readiness across multiple ticker candidates.")
    parser.add_argument("scan-readiness")
    parser.add_argument("--data", required=True, nargs="+", help="Path(s) to evidence JSONL.")
    parser.add_argument("--query", required=True, help="Research query, theme, or question.")
    parser.add_argument("--tickers", required=True, nargs="+", help="Ticker candidates to scan.")
    parser.add_argument("--out", required=True, help="Markdown readiness report output path.")
    parser.add_argument("--limit", type=int, default=12, help="Maximum evidence items to retrieve per ticker.")
    return parser


def build_generate_pack_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate memos for ready tickers and index skipped gaps.")
    parser.add_argument("generate-pack")
    parser.add_argument("--data", required=True, nargs="+", help="Path(s) to evidence JSONL.")
    parser.add_argument("--query", required=True, help="Research query, theme, or question.")
    parser.add_argument("--tickers", required=True, nargs="+", help="Ticker candidates to evaluate.")
    parser.add_argument("--out-dir", required=True, help="Output directory for memo pack files.")
    parser.add_argument("--limit", type=int, default=12, help="Maximum evidence items to retrieve per ticker.")
    return parser


def build_run_cpo_pack_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the default CPO memo-pack pipeline.")
    parser.add_argument("run-cpo-pack")
    parser.add_argument(
        "--base-data",
        nargs="+",
        default=["data/enriched/github_evidence_resolved_summaries.jsonl"],
        help="Base evidence JSONL path(s) before primary-source imports.",
    )
    parser.add_argument(
        "--sec-sources",
        default="config/sec_companyfacts_sources.json",
        help="SEC companyfacts source manifest JSON.",
    )
    parser.add_argument(
        "--official-sources",
        default="config/official_report_sources.json",
        help="Official report source manifest JSON.",
    )
    parser.add_argument(
        "--manual-data",
        nargs="*",
        default=["data/enriched/manual_intake_guarded.jsonl"],
        help="Optional manual intake JSONL path(s) to include in readiness and pack outputs when present.",
    )
    parser.add_argument(
        "--combined-out",
        default="data/enriched/github_plus_primary.jsonl",
        help="Output combined evidence JSONL path.",
    )
    parser.add_argument(
        "--readiness-out",
        default="output/reports/cpo-readiness-guarded.md",
        help="Output readiness report path.",
    )
    parser.add_argument(
        "--pack-out-dir",
        default="output/packs/cpo-guarded",
        help="Output directory for generated memo pack.",
    )
    parser.add_argument(
        "--query",
        default="CPO laser bottleneck revenue profitability",
        help="Research query for readiness and memo pack generation.",
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=["AAOI", "LITE", "COHR", "AXTI", "SIVE", "NVDA"],
        help="Ticker candidates to evaluate.",
    )
    parser.add_argument("--limit", type=int, default=16, help="Maximum evidence items to retrieve per ticker.")
    parser.add_argument(
        "--allow-skipped",
        action="store_true",
        help="Return success even when one or more ticker candidates are skipped.",
    )
    return parser


def build_doctor_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check local Serenity Alpha Lab product inputs.")
    parser.add_argument("doctor")
    parser.add_argument(
        "--base-data",
        nargs="+",
        default=["data/enriched/github_evidence_resolved_summaries.jsonl"],
        help="Base evidence JSONL path(s) before primary-source imports.",
    )
    parser.add_argument(
        "--sec-sources",
        default="config/sec_companyfacts_sources.json",
        help="SEC companyfacts source manifest JSON.",
    )
    parser.add_argument(
        "--official-sources",
        default="config/official_report_sources.json",
        help="Official report source manifest JSON.",
    )
    parser.add_argument(
        "--manual-data",
        nargs="*",
        default=["data/enriched/manual_intake_guarded.jsonl"],
        help="Optional manual intake JSONL path(s) to check.",
    )
    return parser


def build_ui_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local static dashboard for generated research outputs.")
    parser.add_argument("build-ui")
    parser.add_argument(
        "--readiness",
        default="output/reports/cpo-readiness-guarded.md",
        help="Readiness Markdown report path.",
    )
    parser.add_argument(
        "--pack-dir",
        default="output/packs/cpo-guarded",
        help="Memo pack directory containing index.md, sources.md, and memo files.",
    )
    parser.add_argument(
        "--out",
        default="output/ui/index.html",
        help="Output dashboard HTML path.",
    )
    parser.add_argument(
        "--language",
        choices=["en", "zh", "both"],
        default="both",
        help="Dashboard language output to generate.",
    )
    return parser


def build_serve_ui_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and serve the local dashboard UI.")
    parser.add_argument("serve-ui")
    parser.add_argument(
        "--readiness",
        default="output/reports/cpo-readiness-guarded.md",
        help="Readiness Markdown report path.",
    )
    parser.add_argument(
        "--pack-dir",
        default="output/packs/cpo-guarded",
        help="Memo pack directory containing index.md, sources.md, and memo files.",
    )
    parser.add_argument(
        "--out",
        default="output/ui/index.html",
        help="Output dashboard HTML path.",
    )
    parser.add_argument(
        "--language",
        choices=["en", "zh", "both"],
        default="both",
        help="Dashboard language output to generate before serving.",
    )
    parser.add_argument(
        "--analysis-data",
        nargs="+",
        default=["data/enriched/github_plus_primary.jsonl"],
        help="Evidence JSONL path(s) used when the UI launches a new industry theme analysis.",
    )
    parser.add_argument(
        "--analysis-tickers",
        nargs="+",
        default=["AAOI", "LITE", "COHR", "AXTI", "SIVE", "NVDA"],
        help="Ticker candidates evaluated when the UI launches a new industry theme analysis.",
    )
    parser.add_argument(
        "--analysis-out-dir",
        default="output/ui/analyses",
        help="Output directory for UI-launched theme analysis dashboards.",
    )
    parser.add_argument(
        "--analysis-limit",
        type=int,
        default=16,
        help="Maximum evidence items to retrieve per ticker for UI-launched analysis.",
    )
    parser.add_argument(
        "--analysis-stock-universe",
        default="config/stock_universe.json",
        help="Optional stock universe JSON used to expand UI-launched industry and sector candidates.",
    )
    parser.add_argument(
        "--manual-intake-out",
        default="data/enriched/manual_intake_guarded.jsonl",
        help="Manual evidence JSONL path written by analysis-page evidence import forms.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface for the local preview server.")
    parser.add_argument("--port", default=8000, type=int, help="Port for the local preview server.")
    return parser


def build_acquisition_queue_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build evidence acquisition tasks from readiness gaps.")
    parser.add_argument("build-acquisition-queue")
    parser.add_argument("--data", required=True, nargs="+", help="Path(s) to evidence JSONL.")
    parser.add_argument("--query", required=True, help="Research query, theme, or question.")
    parser.add_argument("--tickers", required=True, nargs="+", help="Ticker candidates to evaluate.")
    parser.add_argument("--out", required=True, help="Markdown acquisition queue output path.")
    parser.add_argument("--limit", type=int, default=12, help="Maximum evidence items to retrieve per ticker.")
    return parser


def build_coverage_matrix_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a stock-universe evidence coverage matrix for a theme query.")
    parser.add_argument("build-coverage-matrix")
    parser.add_argument("--data", required=True, nargs="+", help="Path(s) to evidence JSONL.")
    parser.add_argument("--stock-universe", required=True, help="Maintained stock universe JSON path.")
    parser.add_argument("--query", required=True, help="Industry, sector, theme, or ticker query to match.")
    parser.add_argument("--out", required=True, help="Markdown coverage matrix output path.")
    return parser


def build_ingest_task_evidence_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append manually collected evidence and optionally refresh outputs.")
    parser.add_argument("ingest-task-evidence")
    parser.add_argument("--out", required=True, help="Output intake evidence JSONL path.")
    parser.add_argument("--id", required=True, help="Evidence item id.")
    parser.add_argument("--source-title", required=True, help="Source title.")
    parser.add_argument("--source-url", required=True, help="Source URL.")
    parser.add_argument("--published-at", required=True, help="Publication date in YYYY-MM-DD format.")
    parser.add_argument("--claim", required=True, help="Evidence claim.")
    parser.add_argument("--summary", required=True, help="Evidence summary.")
    parser.add_argument("--source-excerpt", default="", help="Traceable excerpt or note linking source to claim.")
    parser.add_argument("--tickers", required=True, nargs="+", help="Ticker symbols.")
    parser.add_argument("--themes", required=True, nargs="+", help="Evidence themes.")
    parser.add_argument("--supply-chain-layer", required=True, help="Supply-chain layer.")
    parser.add_argument("--direction", required=True, choices=["positive", "negative", "neutral"], help="Evidence direction.")
    parser.add_argument("--strength", required=True, choices=["primary", "derived", "speculative"], help="Evidence strength.")
    parser.add_argument("--claim-type", required=True, help="Claim type.")
    parser.add_argument("--confidence", required=True, type=float, help="Confidence from 0 to 1.")
    parser.add_argument("--factor-impact", required=True, action="append", default=[], help="Factor impact as key=value.")
    parser.add_argument("--refresh-data", nargs="+", default=None, help="Evidence JSONL paths to use for refresh.")
    parser.add_argument("--refresh-query", default=None, help="Query for refreshed readiness and memo pack outputs.")
    parser.add_argument("--refresh-tickers", nargs="+", default=None, help="Tickers for refreshed outputs.")
    parser.add_argument("--readiness-out", default=None, help="Optional refreshed readiness report output path.")
    parser.add_argument("--pack-out-dir", default=None, help="Optional refreshed memo pack output directory.")
    parser.add_argument("--limit", type=int, default=12, help="Maximum evidence items to retrieve per ticker.")
    return parser


def _missing_paths(paths: Sequence[str | Path]) -> list[Path]:
    return [Path(path) for path in paths if not Path(path).exists()]


def _preflight_required_paths(paths: Sequence[str | Path]) -> int:
    missing = _missing_paths(paths)
    if not missing:
        return 0

    print("Missing required input file(s):", file=sys.stderr)
    for path in missing:
        print(f"- {path}", file=sys.stderr)
    return 2


def _print_doctor_status(required_paths: Sequence[str | Path], optional_paths: Sequence[str | Path]) -> None:
    optional_missing = _missing_paths(optional_paths)
    print("Serenity Alpha Lab doctor")
    print("required inputs: ok")
    if optional_missing:
        print("optional manual intake: missing")
        for path in optional_missing:
            print(f"- {path}")
    else:
        print("optional manual intake: ok")


def _analysis_slug(query: str) -> str:
    digest = hashlib.sha1(query.encode("utf-8")).hexdigest()[:10]
    base = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
    if not base:
        base = "topic"
    return f"{base[:48]}-{digest}"


def _build_theme_analysis_dashboard(
    *,
    query: str,
    language: str,
    data_paths: Sequence[str | Path],
    tickers: Sequence[str],
    out_dir: str | Path,
    limit: int,
    stock_universe_path: str | Path | None = None,
) -> Path:
    available_data_paths = [path for path in data_paths if Path(path).exists()]
    if not available_data_paths:
        raise FileNotFoundError("No evidence JSONL input files exist for theme analysis.")
    evidence = load_evidence_files(available_data_paths)
    stock_universe = load_stock_universe(stock_universe_path) if stock_universe_path else []
    resolved = resolve_topic(
        query,
        evidence,
        fallback_tickers=tickers,
        stock_universe=stock_universe,
        max_candidates=max(len(tickers), 12),
    )
    analysis_query = resolved.expanded_query or query
    analysis_tickers = _scoped_analysis_tickers(resolved.candidate_tickers, tickers)
    analysis_dir = Path(out_dir) / _analysis_slug(query)
    readiness_path = analysis_dir / "readiness.md"
    pack_dir = analysis_dir / "pack"
    reports_dir = analysis_dir / "reports"
    dashboard_path = analysis_dir / "index.html"

    readiness = assess_batch_readiness(evidence, query=analysis_query, tickers=analysis_tickers, limit=limit)
    readiness_path.parent.mkdir(parents=True, exist_ok=True)
    readiness_path.write_text(_render_resolved_topic_header(resolved) + "\n\n" + render_readiness_markdown(readiness), encoding="utf-8")

    memo_language = "zh" if language == "zh" else "en"
    pack = build_memo_pack(
        evidence,
        query=query,
        tickers=analysis_tickers,
        limit=limit,
        language=memo_language,
        include_gap_memos=True,
    )
    write_memo_pack(pack, pack_dir)
    report_language = "zh" if language == "zh" else "en"
    if stock_universe:
        coverage_matrix = build_coverage_matrix(evidence, universe=stock_universe, query=query)
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "universe-coverage-matrix.md").write_text(
            render_coverage_matrix_markdown(coverage_matrix, language=report_language),
            encoding="utf-8",
        )
    acquisition_queue = build_acquisition_queue(evidence, query=query, tickers=analysis_tickers, limit=limit)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "evidence-acquisition-queue.md").write_text(
        render_acquisition_queue_markdown(acquisition_queue, language=report_language),
        encoding="utf-8",
    )
    build_dashboard(readiness_path=readiness_path, pack_dir=pack_dir, output_path=dashboard_path, language="both")
    _write_analysis_manifest(
        analysis_dir=analysis_dir,
        query=query,
        language="zh" if language == "zh" else "en",
        resolved=resolved,
    )
    build_dashboard(readiness_path=readiness_path, pack_dir=pack_dir, output_path=dashboard_path, language="both")
    _update_analysis_manifest(
        out_dir=Path(out_dir),
        query=query,
        resolved=resolved,
        analysis_dir=analysis_dir,
    )

    if language == "zh":
        return dashboard_path.with_name(f"{dashboard_path.stem}.zh{dashboard_path.suffix}")
    return dashboard_path


def _write_analysis_manifest(*, analysis_dir: Path, query: str, language: str, resolved) -> Path:
    manifest = {
        "query": query,
        "language": language,
        "intent": resolved.intent,
        "canonical_theme": resolved.canonical_theme,
        "expanded_query": resolved.expanded_query,
        "candidate_tickers": resolved.candidate_tickers,
        "quality": _extract_analysis_quality_snapshot(analysis_dir / ("index.zh.html" if language == "zh" else "index.html")),
        "reports": {
            "dashboard_en": "index.html",
            "dashboard_zh": "index.zh.html",
            "deliverable": "reports/deliverable-research-report.md",
            "coverage_matrix": "reports/universe-coverage-matrix.md",
            "evidence_queue": "reports/evidence-acquisition-queue.md",
        },
        "research_only": True,
    }
    output = analysis_dir / "analysis-manifest.json"
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _extract_analysis_quality_snapshot(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"score": 0, "status": "not-publishable"}
    html = path.read_text(encoding="utf-8")
    status_match = re.search(r'<section id="report-quality-gate"[^>]*data-quality-status="([^"]+)"', html)
    score_match = re.search(r"<span>(?:Quality score|质量评分)</span>\s*<strong>(\d{1,3})/100</strong>", html)
    return {
        "score": int(score_match.group(1)) if score_match else 0,
        "status": status_match.group(1) if status_match else "not-publishable",
    }


def _scoped_analysis_tickers(resolved_tickers: Sequence[str], configured_tickers: Sequence[str]) -> list[str]:
    configured = [ticker.upper().lstrip("$") for ticker in configured_tickers]
    if not configured:
        return [ticker.upper().lstrip("$") for ticker in resolved_tickers]

    configured_set = set(configured)
    scoped = [ticker.upper().lstrip("$") for ticker in resolved_tickers if ticker.upper().lstrip("$") in configured_set]
    return scoped or configured


def _update_analysis_manifest(*, out_dir: Path, query: str, resolved, analysis_dir: Path) -> None:
    manifest_path = out_dir / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_analysis_manifest(manifest_path)
    relative_dir = analysis_dir.relative_to(out_dir.parent).as_posix()
    entry = {
        "query": query,
        "intent": resolved.intent,
        "canonical_theme": resolved.canonical_theme,
        "expanded_query": resolved.expanded_query,
        "candidate_tickers": resolved.candidate_tickers,
        "href_en": f"{relative_dir}/index.html",
        "href_zh": f"{relative_dir}/index.zh.html",
    }
    deduped = [item for item in existing if item.get("query") != query]
    manifest_path.write_text(json.dumps([entry, *deduped][:50], ensure_ascii=False, indent=2), encoding="utf-8")


def _read_analysis_manifest(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [entry for entry in payload if isinstance(entry, dict)]


def _render_resolved_topic_header(resolved) -> str:
    aliases = ", ".join(resolved.aliases) if resolved.aliases else "none"
    tickers = ", ".join(resolved.candidate_tickers) if resolved.candidate_tickers else "none"
    return "\n".join(
        [
            "# Resolved Topic",
            "",
            f"**Original query:** {resolved.original_query}",
            f"**Intent:** {resolved.intent}",
            f"**Canonical theme:** {resolved.canonical_theme}",
            f"**Expanded query:** {resolved.expanded_query}",
            f"**Candidate tickers:** {tickers}",
            f"**Aliases:** {aliases}",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(argv) if argv is not None else sys.argv[1:]
    if args_list and args_list[0] == "import-github":
        args = build_import_parser().parse_args(args_list)
        repos = load_repo_specs(args.repos)
        items = import_github_repos(repos, args.out, fetcher=fetch_repo_documents)
        print(f"Imported {len(items)} evidence items to {args.out}")
        return 0

    if args_list and args_list[0] == "import-sec-companyfacts":
        args = build_import_sec_companyfacts_parser().parse_args(args_list)
        items = []
        for spec in load_companyfact_specs(args.sources):
            payload = load_companyfacts_json(spec.path)
            source_url = spec.source_url or f"https://data.sec.gov/api/xbrl/companyfacts/CIK{spec.cik}.json"
            items.extend(companyfacts_to_evidence(payload, ticker=spec.ticker, cik=spec.cik, source_url=source_url))
        deduped = dedupe_evidence(items)
        write_evidence_jsonl(deduped, args.out)
        print(f"Imported {len(deduped)} SEC companyfacts evidence items to {args.out}")
        return 0

    if args_list and args_list[0] == "import-official-report":
        args = build_import_official_report_parser().parse_args(args_list)
        specs = load_official_report_specs(args.sources)
        items = dedupe_evidence(official_report_specs_to_evidence(specs))
        write_evidence_jsonl(items, args.out)
        print(f"Imported {len(items)} official report evidence items to {args.out}")
        return 0

    if args_list and args_list[0] == "build-financial-metrics":
        args = build_financial_metrics_parser().parse_args(args_list)
        evidence = load_evidence_files(args.data)
        catalog = build_metrics_catalog(evidence)
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_metrics_catalog_json(catalog), encoding="utf-8")
        print(f"Wrote {len(catalog)} financial metric rows to {output}")
        return 0

    if args_list and args_list[0] == "scan-report-safety":
        args = build_scan_report_safety_parser().parse_args(args_list)
        result = scan_report_safety(args.reports)
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_report_safety_markdown(result), encoding="utf-8")
        print(f"Wrote report safety scan to {output}")
        return 0 if result.passed else 4

    if args_list and args_list[0] == "audit-evidence":
        args = build_audit_parser().parse_args(args_list)
        evidence = load_evidence_files(args.data)
        report = audit_evidence(evidence, focus_ticker=args.ticker)
        markdown = render_audit_markdown(report)
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
        print(f"Wrote evidence audit to {output}")
        return 0

    if args_list and args_list[0] == "resolve-tickers":
        args = build_resolve_tickers_parser().parse_args(args_list)
        evidence = load_evidence_files(args.data)
        rules = load_ticker_resolution_rules(args.rules)
        resolved = resolve_evidence_tickers(evidence, rules)
        write_evidence_jsonl(resolved, args.out)
        print(f"Wrote {len(resolved)} resolved evidence items to {args.out}")
        return 0

    if args_list and args_list[0] == "enrich-summaries":
        args = build_enrich_summaries_parser().parse_args(args_list)
        evidence = load_evidence_files(args.data)
        enriched = enrich_evidence_summaries(evidence)
        write_evidence_jsonl(enriched, args.out)
        print(f"Wrote {len(enriched)} summary-enriched evidence items to {args.out}")
        return 0

    if args_list and args_list[0] == "check-coverage":
        args = build_check_coverage_parser().parse_args(args_list)
        evidence = load_evidence_files(args.data)
        matched = retrieve(evidence, query=args.query, ticker=args.ticker, limit=args.limit)
        report = assess_source_coverage(matched, focus_ticker=args.ticker)
        markdown = "\n".join(
            [
                "# Source Coverage Report",
                "",
                f"**Research question:** {args.query}",
                f"**Ticker focus:** {args.ticker or 'not specified'}",
                f"**Retrieved evidence count:** {len(matched)}",
                "",
                render_source_coverage_markdown(report),
                "",
            ]
        )
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
        print(f"Wrote source coverage report to {output}")
        return 0

    if args_list and args_list[0] == "scan-readiness":
        args = build_scan_readiness_parser().parse_args(args_list)
        evidence = load_evidence_files(args.data)
        report = assess_batch_readiness(evidence, query=args.query, tickers=args.tickers, limit=args.limit)
        markdown = render_readiness_markdown(report)
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
        print(f"Wrote batch readiness report to {output}")
        return 0

    if args_list and args_list[0] == "generate-pack":
        args = build_generate_pack_parser().parse_args(args_list)
        evidence = load_evidence_files(args.data)
        pack = build_memo_pack(evidence, query=args.query, tickers=args.tickers, limit=args.limit)
        write_memo_pack(pack, args.out_dir)
        print(f"Wrote memo pack to {args.out_dir}")
        return 0

    if args_list and args_list[0] == "doctor":
        args = build_doctor_parser().parse_args(args_list)
        required_paths = [*args.base_data, args.sec_sources, args.official_sources]
        preflight_exit = _preflight_required_paths(required_paths)
        if preflight_exit:
            return preflight_exit
        _print_doctor_status(required_paths, args.manual_data)
        return 0

    if args_list and args_list[0] == "build-ui":
        args = build_ui_parser().parse_args(args_list)
        preflight_exit = _preflight_required_paths([args.readiness, Path(args.pack_dir) / "index.md", Path(args.pack_dir) / "sources.md"])
        if preflight_exit:
            return preflight_exit
        output = build_dashboard(readiness_path=args.readiness, pack_dir=args.pack_dir, output_path=args.out, language=args.language)
        print(f"Wrote dashboard UI to {output}")
        if args.language == "both":
            print(f"Wrote Chinese dashboard UI to {output.with_name(output.stem + '.zh' + output.suffix)}")
        return 0

    if args_list and args_list[0] == "serve-ui":
        args = build_serve_ui_parser().parse_args(args_list)
        preflight_exit = _preflight_required_paths(
            [
                args.readiness,
                Path(args.pack_dir) / "index.md",
                Path(args.pack_dir) / "sources.md",
                *args.analysis_data,
            ]
        )
        if preflight_exit:
            return preflight_exit
        output = build_dashboard(readiness_path=args.readiness, pack_dir=args.pack_dir, output_path=args.out, language=args.language)

        def analysis_data_paths() -> list[str | Path]:
            manual_intake = Path(args.manual_intake_out)
            if manual_intake.exists():
                return [*args.analysis_data, manual_intake]
            return list(args.analysis_data)

        def analyze_theme(*, query: str, language: str = "en") -> Path:
            return _build_theme_analysis_dashboard(
                query=query,
                language=language,
                data_paths=analysis_data_paths(),
                tickers=args.analysis_tickers,
                out_dir=args.analysis_out_dir,
                limit=args.analysis_limit,
                stock_universe_path=args.analysis_stock_universe,
            )

        def resolve_theme(*, query: str, language: str = "en") -> dict[str, object]:
            stock_universe = load_stock_universe(args.analysis_stock_universe) if args.analysis_stock_universe else []
            return build_topic_resolution_preview(
                query=query,
                language=language,
                evidence=load_evidence_files(analysis_data_paths()),
                fallback_tickers=args.analysis_tickers,
                stock_universe=stock_universe,
            )

        def ingest_evidence(form: dict[str, str]) -> Path:
            ticker = str(form.get("ticker") or "").upper().lstrip("$")
            query = str(form.get("query") or "").strip()
            language = str(form.get("language") or "en").strip() or "en"
            item = build_intake_evidence(
                item_id=str(form.get("id") or f"manual:{ticker}:{hashlib.sha1(json.dumps(form, sort_keys=True).encode('utf-8')).hexdigest()[:10]}"),
                source_title=str(form.get("source_title") or ""),
                source_url=str(form.get("source_url") or ""),
                published_at=str(form.get("published_at") or date.today().isoformat()),
                claim=str(form.get("claim") or f"Manual evidence collected for {ticker or 'candidate'} in {query or 'the analysis'}."),
                summary=str(form.get("summary") or f"Manual intake evidence for {ticker or 'candidate'} in {query or 'the analysis'}."),
                source_excerpt=str(form.get("source_excerpt") or ""),
                tickers=[ticker] if ticker else [],
                themes=[value for value in [query, "manual-intake"] if value],
                supply_chain_layer="manual evidence",
                direction="neutral",
                strength="primary",
                confidence=0.8,
                factor_impacts={"evidence_quality": 12},
                claim_type="fact",
            )
            append_intake_evidence(item, args.manual_intake_out)
            return analyze_theme(query=query or ticker or "manual evidence", language=language)

        serve_dashboard(
            output_path=output,
            host=args.host,
            port=args.port,
            analyze_callback=analyze_theme,
            ingest_callback=ingest_evidence,
            resolve_callback=resolve_theme,
        )
        return 0

    if args_list and args_list[0] == "run-cpo-pack":
        args = build_run_cpo_pack_parser().parse_args(args_list)
        preflight_exit = _preflight_required_paths([*args.base_data, args.sec_sources, args.official_sources])
        if preflight_exit:
            return preflight_exit

        base_items = load_evidence_files(args.base_data)

        sec_items = []
        sec_sources = Path(args.sec_sources)
        if sec_sources.exists():
            for spec in load_companyfact_specs(sec_sources):
                payload = load_companyfacts_json(spec.path)
                source_url = spec.source_url or f"https://data.sec.gov/api/xbrl/companyfacts/CIK{spec.cik}.json"
                sec_items.extend(companyfacts_to_evidence(payload, ticker=spec.ticker, cik=spec.cik, source_url=source_url))

        official_items = []
        official_sources = Path(args.official_sources)
        if official_sources.exists():
            official_items = official_report_specs_to_evidence(load_official_report_specs(official_sources))

        combined = dedupe_evidence([*base_items, *sec_items, *official_items])
        write_evidence_jsonl(combined, args.combined_out)

        manual_paths = [path for path in args.manual_data if Path(path).exists()]
        product_evidence = load_evidence_files([args.combined_out, *manual_paths])

        readiness = assess_batch_readiness(
            product_evidence,
            query=args.query,
            tickers=args.tickers,
            limit=args.limit,
        )
        readiness_output = Path(args.readiness_out)
        readiness_output.parent.mkdir(parents=True, exist_ok=True)
        readiness_output.write_text(render_readiness_markdown(readiness), encoding="utf-8")

        pack = build_memo_pack(product_evidence, query=args.query, tickers=args.tickers, limit=args.limit)
        write_memo_pack(pack, args.pack_out_dir)

        print(
            "Run complete: "
            f"combined {len(combined)} evidence items; "
            f"ready memos {len(pack.memos)}; skipped {len(pack.skipped)}; "
            f"readiness {args.readiness_out}; pack {args.pack_out_dir}"
        )
        if pack.skipped and not args.allow_skipped:
            print("Skipped memo candidate(s):", file=sys.stderr)
            for candidate in pack.skipped:
                flags = ", ".join(flag.code for flag in candidate.report.flags) or "none"
                print(f"- {candidate.ticker}: {candidate.status} ({flags})", file=sys.stderr)
            return 3
        return 0

    if args_list and args_list[0] == "build-acquisition-queue":
        args = build_acquisition_queue_parser().parse_args(args_list)
        evidence = load_evidence_files(args.data)
        queue = build_acquisition_queue(evidence, query=args.query, tickers=args.tickers, limit=args.limit)
        markdown = render_acquisition_queue_markdown(queue)
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
        print(f"Wrote acquisition queue to {output}")
        return 0

    if args_list and args_list[0] == "build-coverage-matrix":
        args = build_coverage_matrix_parser().parse_args(args_list)
        evidence = load_evidence_files(args.data)
        universe = load_stock_universe(args.stock_universe)
        matrix = build_coverage_matrix(evidence, universe=universe, query=args.query)
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_coverage_matrix_markdown(matrix), encoding="utf-8")
        print(f"Wrote coverage matrix to {output}")
        return 0

    if args_list and args_list[0] == "ingest-task-evidence":
        args = build_ingest_task_evidence_parser().parse_args(args_list)
        item = build_intake_evidence(
            item_id=args.id,
            source_title=args.source_title,
            source_url=args.source_url,
            published_at=args.published_at,
            claim=args.claim,
            summary=args.summary,
            source_excerpt=args.source_excerpt,
            tickers=args.tickers,
            themes=args.themes,
            supply_chain_layer=args.supply_chain_layer,
            direction=args.direction,
            strength=args.strength,
            confidence=args.confidence,
            factor_impacts=parse_factor_impacts(args.factor_impact),
            claim_type=args.claim_type,
        )
        append_intake_evidence(item, args.out)
        if args.refresh_data and args.refresh_query and args.refresh_tickers:
            evidence = load_evidence_files(args.refresh_data)
            if args.readiness_out:
                report = assess_batch_readiness(
                    evidence,
                    query=args.refresh_query,
                    tickers=args.refresh_tickers,
                    limit=args.limit,
                )
                output = Path(args.readiness_out)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(render_readiness_markdown(report), encoding="utf-8")
            if args.pack_out_dir:
                pack = build_memo_pack(
                    evidence,
                    query=args.refresh_query,
                    tickers=args.refresh_tickers,
                    limit=args.limit,
                )
                write_memo_pack(pack, args.pack_out_dir)
        print(f"Appended intake evidence to {args.out}")
        return 0

    args = build_parser().parse_args(args_list)
    evidence = load_evidence_files(args.data)
    matched = retrieve(evidence, query=args.query, ticker=args.ticker, limit=args.limit)
    score = score_research_question(matched)
    memo = generate_memo(query=args.query, ticker=args.ticker, evidence=matched, score=score)

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(memo, encoding="utf-8")
    print(f"Wrote memo to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
