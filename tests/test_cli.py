import json
from pathlib import Path

from serenity_alpha_lab.cli import main


FIXTURE = Path(__file__).parent / "fixtures" / "evidence.jsonl"
GITHUB_MANIFEST = Path(__file__).parent / "fixtures" / "github_repo_manifest.json"
SEC_COMPANYFACTS_SOURCES = Path(__file__).parent / "fixtures" / "sec_companyfacts_sources.json"
OFFICIAL_REPORT_SOURCES = Path(__file__).parent / "fixtures" / "official_report_sources.json"


def test_cli_writes_memo(tmp_path):
    out = tmp_path / "memo.md"

    exit_code = main(["--data", str(FIXTURE), "--query", "CPO", "--ticker", "SIVE", "--out", str(out)])

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "SIVE" in text
    assert "## Scorecard" in text
    assert "## Skeptic Review" in text


def test_cli_accepts_multiple_data_files(tmp_path):
    out = tmp_path / "memo.md"

    exit_code = main(
        [
            "--data",
            str(FIXTURE),
            str(FIXTURE),
            "--query",
            "CPO",
            "--ticker",
            "SIVE",
            "--out",
            str(out),
        ]
    )

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "**Evidence count:** 4" in text


def test_cli_import_github_writes_jsonl(tmp_path, monkeypatch):
    from serenity_alpha_lab import cli
    from serenity_alpha_lab.github_importer import GitHubDocument, load_repo_specs

    repo = load_repo_specs(GITHUB_MANIFEST)[0]
    content = (Path(__file__).parent / "fixtures" / "github_readme.md").read_text(encoding="utf-8")

    def fake_fetch_repo_documents(spec):
        assert spec.full_name == repo.full_name
        return [
            GitHubDocument(
                repo=repo,
                path="README.md",
                source_url="https://github.com/example/serenity-skill/blob/main/README.md",
                content=content,
            )
        ]

    monkeypatch.setattr(cli, "fetch_repo_documents", fake_fetch_repo_documents)
    out = tmp_path / "github_evidence.jsonl"

    exit_code = main(["import-github", "--repos", str(GITHUB_MANIFEST), "--out", str(out)])

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "github:example/serenity-skill" in text
    assert "CPO" in text


def test_cli_import_github_reads_sys_argv_when_called_as_module(tmp_path, monkeypatch):
    from serenity_alpha_lab import cli
    from serenity_alpha_lab.github_importer import GitHubDocument, load_repo_specs

    repo = load_repo_specs(GITHUB_MANIFEST)[0]
    content = (Path(__file__).parent / "fixtures" / "github_readme.md").read_text(encoding="utf-8")

    def fake_fetch_repo_documents(_spec):
        return [
            GitHubDocument(
                repo=repo,
                path="README.md",
                source_url="https://github.com/example/serenity-skill/blob/main/README.md",
                content=content,
            )
        ]

    out = tmp_path / "github_evidence.jsonl"
    monkeypatch.setattr(cli, "fetch_repo_documents", fake_fetch_repo_documents)
    monkeypatch.setattr(
        "sys.argv",
        ["serenity_alpha_lab.cli", "import-github", "--repos", str(GITHUB_MANIFEST), "--out", str(out)],
    )

    exit_code = main()

    assert exit_code == 0
    assert out.exists()


def test_cli_audit_evidence_writes_report(tmp_path):
    out = tmp_path / "evidence-audit.md"

    exit_code = main(["audit-evidence", "--data", str(FIXTURE), "--ticker", "SIVE", "--out", str(out)])

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "# Evidence Audit Report" in text
    assert "## Quality Flags" in text
    assert "## Next Fixes" in text


def test_cli_resolve_tickers_writes_enriched_jsonl(tmp_path):
    out = tmp_path / "resolved.jsonl"
    rules = Path(__file__).parent / "fixtures" / "ticker_rules.json"

    exit_code = main(["resolve-tickers", "--data", str(FIXTURE), "--rules", str(rules), "--out", str(out)])

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert '"ticker-resolution:SIVE"' in text
    assert '"SIVE"' in text


def test_cli_enrich_summaries_writes_jsonl(tmp_path):
    source = tmp_path / "short.jsonl"
    source.write_text(
        '{"id":"short","source_title":"Repo README.md","source_url":"https://example.com",'
        '"published_at":"2026-01-01","claim":"Install path: use the project skills directory.",'
        '"summary":"```","tickers":["SERENITY"],"themes":["Serenity"],'
        '"supply_chain_layer":"methodology","direction":"neutral","strength":"derived",'
        '"confidence":0.6,"factor_impacts":{"evidence_quality":1},"claim_type":"methodology"}\n',
        encoding="utf-8",
    )
    out = tmp_path / "summary-enriched.jsonl"

    exit_code = main(["enrich-summaries", "--data", str(source), "--out", str(out)])

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert '"summary-enriched"' in text
    assert "Install path" in text


def test_cli_import_sec_companyfacts_writes_jsonl(tmp_path):
    out = tmp_path / "sec_companyfacts.jsonl"

    exit_code = main(["import-sec-companyfacts", "--sources", str(SEC_COMPANYFACTS_SOURCES), "--out", str(out)])

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "SEC companyfacts reports Revenue for SIVE FY2025" in text
    assert '"claim_type": "fact"' in text
    assert '"strength": "primary"' in text


def test_cli_import_official_report_writes_primary_evidence_jsonl(tmp_path):
    out = tmp_path / "official_report.jsonl"
    sources = Path(__file__).parent / "fixtures" / "official_report_sources.json"

    exit_code = main(["import-official-report", "--sources", str(sources), "--out", str(out)])

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "official-report:SIVE:net-sales-2025" in text
    assert "co-packaged optics" in text
    assert '"claim_type": "fact"' in text
    assert '"strength": "primary"' in text
    assert '"source_excerpt"' in text


def test_cli_build_financial_metrics_writes_source_backed_catalog(tmp_path):
    evidence = tmp_path / "evidence.jsonl"
    evidence.write_text(
        "\n".join(
            [
                '{"id":"sec-companyfacts:SIVE:revenue","source_title":"SEC companyfacts SIVE Revenue","source_url":"https://example.com/sec","published_at":"2026-02-28","claim":"SEC companyfacts reports Revenue for SIVE FY2025: $420,000,000.","summary":"Primary SEC companyfacts data shows SIVE FY2025 Revenue of $420,000,000.","tickers":["SIVE"],"themes":["SEC companyfacts","primary-source","revenue"],"supply_chain_layer":"company financials","direction":"neutral","strength":"primary","confidence":0.9,"factor_impacts":{"evidence_quality":20},"claim_type":"fact"}',
                '{"id":"sec-companyfacts:SIVE:income","source_title":"SEC companyfacts SIVE Net Income","source_url":"https://example.com/sec","published_at":"2026-02-28","claim":"SEC companyfacts reports Net Income (Loss) for SIVE FY2025: $-15,000,000.","summary":"Primary SEC companyfacts data shows SIVE FY2025 Net Income (Loss) of $-15,000,000. The value is a reported loss.","tickers":["SIVE"],"themes":["SEC companyfacts","primary-source","profitability"],"supply_chain_layer":"company financials","direction":"negative","strength":"primary","confidence":0.9,"factor_impacts":{"evidence_quality":20},"claim_type":"fact"}',
                '{"id":"official-report:SIVE:net-sales-2025","source_title":"Sivers Annual Report","source_url":"https://example.com/report","published_at":"2026-05-01","claim":"Sivers Semiconductors reported 2025 net sales of SEK 306.6 million, up 40% year over year.","summary":"Official annual-report evidence shows SIVE 2025 net sales increased to SEK 306.6 million from SEK 219.2 million.","tickers":["SIVE"],"themes":["annual-report","primary-source","revenue","CPO"],"supply_chain_layer":"company financials","direction":"positive","strength":"primary","confidence":0.9,"factor_impacts":{"evidence_quality":24},"claim_type":"fact"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "financial_metrics.json"

    exit_code = main(["build-financial-metrics", "--data", str(evidence), "--out", str(out)])

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert '"ticker": "SIVE"' in text
    assert '"revenue_growth": "40% YoY official report"' in text
    assert '"momentum": "reported loss"' in text
    assert '"cycle_position": "revenue ramp / loss-making"' in text


def test_cli_scan_report_safety_writes_report_and_returns_failure_for_findings(tmp_path):
    memo = tmp_path / "unsafe-memo.md"
    memo.write_text("# Memo\n\nYou should sell AAOI now.\n", encoding="utf-8")
    out = tmp_path / "safety.md"

    exit_code = main(["scan-report-safety", "--reports", str(memo), "--out", str(out)])

    assert exit_code == 4
    text = out.read_text(encoding="utf-8")
    assert "# Report Safety Scan" in text
    assert "**Findings:** 1" in text
    assert "| unsafe-memo.md | 3 | you should sell |" in text


def test_cli_scan_report_safety_allows_quoted_source_evidence(tmp_path):
    memo = tmp_path / "quoted-memo.md"
    memo.write_text(
        "\n".join(
            [
                "# Memo",
                "",
                "## Supporting Evidence",
                "",
                '- **github:example:1** [source](https://example.com): External source mentions "buy / sell / hold / size".',
                "",
                "This memo is research only.",
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "safety.md"

    exit_code = main(["scan-report-safety", "--reports", str(memo), "--out", str(out)])

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "**Findings:** 0" in text


def test_cli_analyze_stock_stub_writes_report_artifacts(tmp_path):
    out_dir = tmp_path / "stock-analysis"

    exit_code = main(
        [
            "analyze-stock",
            "--stock-code",
            "AAPL",
            "--stock-name",
            "Apple Inc.",
            "--query",
            "AAPL market data research",
            "--out-dir",
            str(out_dir),
            "--stub",
        ]
    )

    assert exit_code == 0
    report = (out_dir / "reports" / "stock-analysis-report.md").read_text(encoding="utf-8")
    manifest = json.loads((out_dir / "analysis-report-manifest.json").read_text(encoding="utf-8"))
    html = (out_dir / "index.html").read_text(encoding="utf-8")

    assert "# Serenity Stock Analysis Report" in report
    assert "## Key Claims And Provenance" in report
    assert "serenity:market-data:AAPL:quote:2026-07-09" in report
    assert manifest["reports"]["stock_analysis"] == "reports/stock-analysis-report.md"
    assert manifest["safety"]["passed"] is True
    assert 'data-report-href="reports/stock-analysis-report.md"' in html
    assert "research only" in html.lower()


def test_cli_build_coverage_matrix_writes_theme_universe_report(tmp_path):
    evidence = tmp_path / "evidence.jsonl"
    evidence.write_text(
        "\n".join(
            [
                '{"id":"github:MU:hbm","source_title":"MU HBM source","source_url":"https://example.com/mu","published_at":"2026-01-01","claim":"MU has HBM exposure.","summary":"Derived evidence links MU to HBM.","tickers":["MU"],"themes":["memory","HBM"],"supply_chain_layer":"semiconductors","direction":"positive","strength":"derived","confidence":0.75,"factor_impacts":{"evidence_quality":10},"claim_type":"inference"}',
                '{"id":"sec:AAOI:revenue","source_title":"AAOI revenue source","source_url":"https://example.com/aaoi","published_at":"2026-01-01","claim":"AAOI revenue fact.","summary":"Primary AAOI evidence.","tickers":["AAOI"],"themes":["primary-source","CPO"],"supply_chain_layer":"optical components","direction":"neutral","strength":"primary","confidence":0.9,"factor_impacts":{"evidence_quality":20},"claim_type":"fact"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    universe = tmp_path / "stock_universe.json"
    universe.write_text(
        """[
  {"ticker":"AAOI","name":"Applied Optoelectronics","market":"US","sector":"Optical Components","themes":["CPO"],"aliases":["CPO"]},
  {"ticker":"MU","name":"Micron Technology","market":"US","sector":"Semiconductors","themes":["memory","HBM"],"aliases":["存储芯片","HBM"]},
  {"ticker":"GIGADEVICE","name":"兆易创新","market":"CN","sector":"Semiconductors","themes":["memory","NOR flash"],"aliases":["存储芯片","NOR"]}
]""",
        encoding="utf-8",
    )
    out = tmp_path / "coverage-matrix.md"

    exit_code = main(
        [
            "build-coverage-matrix",
            "--data",
            str(evidence),
            "--stock-universe",
            str(universe),
            "--query",
            "存储芯片",
            "--out",
            str(out),
        ]
    )

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "# Universe Coverage Matrix" in text
    assert "GIGADEVICE" in text
    assert "MU primary filing 存储芯片" in text


def test_cli_check_coverage_writes_report(tmp_path):
    out = tmp_path / "coverage.md"

    exit_code = main(
        [
            "check-coverage",
            "--data",
            str(FIXTURE),
            "--query",
            "CPO laser bottleneck",
            "--ticker",
            "SIVE",
            "--out",
            str(out),
            "--limit",
            "4",
        ]
    )

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "# Source Coverage Report" in text
    assert "**Research question:** CPO laser bottleneck" in text
    assert "**Focus ticker:** SIVE" in text
    assert "**Retrieved evidence count:** 4" in text
    assert "missing_primary_source" in text


def test_cli_scan_readiness_writes_report(tmp_path):
    out = tmp_path / "readiness.md"

    exit_code = main(
        [
            "scan-readiness",
            "--data",
            str(FIXTURE),
            "--query",
            "CPO laser bottleneck",
            "--tickers",
            "SIVE",
            "AAOI",
            "--out",
            str(out),
            "--limit",
            "4",
        ]
    )

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "# Batch Readiness Report" in text
    assert "**Research question:** CPO laser bottleneck" in text
    assert "| Rank | Ticker | Status | Evidence | Primary/Fact | Risk | Methodology | SERENITY Placeholder | Flags |" in text
    assert "SIVE" in text
    assert "AAOI" in text


def test_cli_generate_pack_writes_ready_memos_and_index(tmp_path):
    out_dir = tmp_path / "pack"

    exit_code = main(
        [
            "generate-pack",
            "--data",
            str(FIXTURE),
            "--query",
            "CPO laser bottleneck",
            "--tickers",
            "SIVE",
            "AAOI",
            "--out-dir",
            str(out_dir),
            "--limit",
            "4",
        ]
    )

    assert exit_code == 0
    index = (out_dir / "index.md").read_text(encoding="utf-8")
    assert "# Serenity Alpha Lab Memo Pack" in index
    assert "not generated" in index
    assert "missing_primary_source" in index
    assert (out_dir / "sources.md").exists()
    assert not (out_dir / "sive-memo.md").exists()


def test_cli_build_ui_writes_dashboard(tmp_path):
    readiness = tmp_path / "readiness.md"
    readiness.write_text(
        "\n".join(
            [
                "# Batch Readiness Report",
                "",
                "**Research question:** CPO laser bottleneck",
                "",
                "| Rank | Ticker | Status | Evidence | Primary/Fact | Risk | Methodology | SERENITY Placeholder | Flags |",
                "|---:|---|---|---:|---:|---:|---:|---:|---|",
                "| 1 | SIVE | ready | 16 | 3 | 6 | 6% | 0% | none |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "index.md").write_text(
        "\n".join(
            [
                "# Serenity Alpha Lab Memo Pack",
                "",
                "| Ticker | Status | Memo File | Evidence | Primary/Fact | Risk | Flags |",
                "|---|---|---|---:|---:|---:|---|",
                "| SIVE | ready | sive-memo.md | 16 | 3 | 6 | none |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "sources.md").write_text("# Evidence Provenance Index\n", encoding="utf-8")
    (pack_dir / "sive-memo.md").write_text(
        "# Serenity Alpha Lab Memo\n\n**Ticker focus:** SIVE\n\n## Thesis Summary\n\nSIVE dashboard preview.\n",
        encoding="utf-8",
    )
    out = tmp_path / "ui" / "index.html"

    exit_code = main(
        [
            "build-ui",
            "--readiness",
            str(readiness),
            "--pack-dir",
            str(pack_dir),
            "--out",
            str(out),
        ]
    )

    assert exit_code == 0
    html = out.read_text(encoding="utf-8")
    assert "Serenity Alpha Lab" in html
    assert "Readiness" in html
    assert "SIVE" in html
    assert "Research only" in html


def test_cli_build_ui_writes_bilingual_dashboards(tmp_path):
    readiness = tmp_path / "readiness.md"
    readiness.write_text(
        "\n".join(
            [
                "# Batch Readiness Report",
                "",
                "**Research question:** CPO laser bottleneck",
                "",
                "| Rank | Ticker | Status | Evidence | Primary/Fact | Risk | Methodology | SERENITY Placeholder | Flags |",
                "|---:|---|---|---:|---:|---:|---:|---:|---|",
                "| 1 | SIVE | ready | 16 | 3 | 6 | 6% | 0% | none |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "index.md").write_text(
        "\n".join(
            [
                "# Serenity Alpha Lab Memo Pack",
                "",
                "| Ticker | Status | Memo File | Evidence | Primary/Fact | Risk | Flags |",
                "|---|---|---|---:|---:|---:|---|",
                "| SIVE | ready | sive-memo.md | 16 | 3 | 6 | none |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "sources.md").write_text("# Evidence Provenance Index\n", encoding="utf-8")
    (pack_dir / "sive-memo.md").write_text(
        "# Serenity Alpha Lab Memo\n\n**Ticker focus:** SIVE\n\n## Thesis Summary\n\nSIVE dashboard preview.\n",
        encoding="utf-8",
    )
    out = tmp_path / "ui" / "index.html"

    exit_code = main(
        [
            "build-ui",
            "--readiness",
            str(readiness),
            "--pack-dir",
            str(pack_dir),
            "--out",
            str(out),
            "--language",
            "both",
        ]
    )

    assert exit_code == 0
    en_html = out.read_text(encoding="utf-8")
    zh_html = (out.parent / "index.zh.html").read_text(encoding="utf-8")
    assert "Research only" in en_html
    assert "本地研究仪表盘" in zh_html
    assert "仅供研究" in zh_html
    assert 'href="index.zh.html"' in en_html
    assert 'href="index.html"' in zh_html


def test_cli_serve_ui_builds_dashboard_and_invokes_server(tmp_path, monkeypatch):
    from serenity_alpha_lab import cli

    readiness = tmp_path / "readiness.md"
    readiness.write_text(
        "\n".join(
            [
                "# Batch Readiness Report",
                "",
                "**Research question:** CPO laser bottleneck",
                "",
                "| Rank | Ticker | Status | Evidence | Primary/Fact | Risk | Methodology | SERENITY Placeholder | Flags |",
                "|---:|---|---|---:|---:|---:|---:|---:|---|",
                "| 1 | SIVE | ready | 16 | 3 | 6 | 6% | 0% | none |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "index.md").write_text(
        "\n".join(
            [
                "# Serenity Alpha Lab Memo Pack",
                "",
                "| Ticker | Status | Memo File | Evidence | Primary/Fact | Risk | Flags |",
                "|---|---|---|---:|---:|---:|---|",
                "| SIVE | ready | sive-memo.md | 16 | 3 | 6 | none |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "sources.md").write_text("# Evidence Provenance Index\n", encoding="utf-8")
    (pack_dir / "sive-memo.md").write_text(
        "# Serenity Alpha Lab Memo\n\n**Ticker focus:** SIVE\n\n## Thesis Summary\n\nSIVE preview.\n",
        encoding="utf-8",
    )
    out = tmp_path / "ui" / "index.html"
    analysis_out_dir = tmp_path / "analyses"
    calls = []

    def fake_serve_dashboard(*, output_path, host, port, analyze_callback, ingest_callback=None, resolve_callback=None):
        generated = analyze_callback(query="存储芯片", language="zh")
        resolved = resolve_callback(query="存储芯片", language="zh") if resolve_callback else {}
        calls.append((output_path, host, port, generated, ingest_callback, resolved))

    monkeypatch.setattr(cli, "serve_dashboard", fake_serve_dashboard)

    exit_code = main(
        [
            "serve-ui",
            "--readiness",
            str(readiness),
            "--pack-dir",
            str(pack_dir),
            "--out",
            str(out),
            "--analysis-data",
            str(FIXTURE),
            "--analysis-tickers",
            "SIVE",
            "--analysis-out-dir",
            str(analysis_out_dir),
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
        ]
    )

    assert exit_code == 0
    assert out.exists()
    assert calls[0][:3] == (out, "127.0.0.1", 8765)
    assert callable(calls[0][4])
    generated = calls[0][3]
    assert generated.name == "index.zh.html"
    assert generated.exists()
    assert "存储芯片" in generated.read_text(encoding="utf-8")
    manifest = analysis_out_dir / "manifest.json"
    assert manifest.exists()
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "存储芯片" in manifest_text
    resolved = calls[0][5]
    assert resolved["intent"] == "industry"
    assert resolved["canonical_theme"] == "memory"
    assert resolved["candidate_tickers"]
    assert "index.zh.html" in manifest_text
    analysis_manifest = generated.parent / "analysis-manifest.json"
    assert analysis_manifest.exists()
    analysis_payload = json.loads(analysis_manifest.read_text(encoding="utf-8"))
    assert analysis_payload["query"] == "存储芯片"
    assert analysis_payload["language"] == "zh"
    assert analysis_payload["intent"] == "industry"
    assert analysis_payload["canonical_theme"] == "memory"
    assert analysis_payload["candidate_tickers"]
    assert analysis_payload["quality"]["score"] >= 0
    assert analysis_payload["quality"]["status"] in {"publishable", "needs-evidence", "not-publishable"}
    assert analysis_payload["reports"]["dashboard_zh"] == "index.zh.html"
    assert analysis_payload["reports"]["deliverable"] == "reports/deliverable-research-report.md"
    assert analysis_payload["reports"]["evidence_queue"] == "reports/evidence-acquisition-queue.md"
    assert analysis_payload["research_only"] is True
    memo = (generated.parent / "pack" / "sive-memo.md").read_text(encoding="utf-8")
    assert "# Serenity Alpha Lab 研究备忘录" in memo
    assert "**研究问题:** 存储芯片" in memo


def test_cli_serve_app_invokes_serenity_api_without_building_static_dashboard(tmp_path, monkeypatch):
    from serenity_alpha_lab import cli

    calls = []

    def fail_build_dashboard(**_kwargs):
        raise AssertionError("serve-app should not rebuild the static dashboard")

    def fake_serve_app(config):
        calls.append(config)

    monkeypatch.setattr(cli, "build_dashboard", fail_build_dashboard)
    monkeypatch.setattr(cli, "serve_app", fake_serve_app)

    runs_path = tmp_path / "runs.json"
    dashboard_path = tmp_path / "index.html"

    exit_code = main(
        [
            "serve-app",
            "--host",
            "0.0.0.0",
            "--port",
            "8123",
            "--runs-path",
            str(runs_path),
            "--dashboard-path",
            str(dashboard_path),
        ]
    )

    assert exit_code == 0
    assert len(calls) == 1
    config = calls[0]
    assert config.host == "0.0.0.0"
    assert config.port == 8123
    assert config.runs_path == runs_path
    assert config.dashboard_path == dashboard_path
    assert config.require_market_data_credentials is False
    assert config.research_only is True


def test_cli_run_cpo_pack_fails_fast_when_required_inputs_are_missing(tmp_path, capsys):
    missing_base = tmp_path / "missing-base.jsonl"
    missing_sec = tmp_path / "missing-sec.json"
    missing_official = tmp_path / "missing-official.json"
    combined_out = tmp_path / "combined.jsonl"
    readiness_out = tmp_path / "readiness.md"
    pack_out_dir = tmp_path / "pack"

    exit_code = main(
        [
            "run-cpo-pack",
            "--base-data",
            str(missing_base),
            "--sec-sources",
            str(missing_sec),
            "--official-sources",
            str(missing_official),
            "--combined-out",
            str(combined_out),
            "--readiness-out",
            str(readiness_out),
            "--pack-out-dir",
            str(pack_out_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Missing required input file" in captured.err
    assert str(missing_base) in captured.err
    assert str(missing_sec) in captured.err
    assert str(missing_official) in captured.err
    assert not combined_out.exists()
    assert not readiness_out.exists()
    assert not pack_out_dir.exists()


def test_cli_doctor_reports_ok_when_required_inputs_exist(tmp_path, capsys):
    missing_manual = tmp_path / "missing-optional-manual.jsonl"

    exit_code = main(
        [
            "doctor",
            "--base-data",
            str(FIXTURE),
            "--sec-sources",
            str(SEC_COMPANYFACTS_SOURCES),
            "--official-sources",
            str(OFFICIAL_REPORT_SOURCES),
            "--manual-data",
            str(missing_manual),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Serenity Alpha Lab doctor" in captured.out
    assert "required inputs: ok" in captured.out
    assert "optional manual intake: missing" in captured.out
    assert str(missing_manual) in captured.out


def test_cli_doctor_reports_missing_required_inputs(tmp_path, capsys):
    missing_base = tmp_path / "missing-base.jsonl"
    missing_sec = tmp_path / "missing-sec.json"
    missing_official = tmp_path / "missing-official.json"

    exit_code = main(
        [
            "doctor",
            "--base-data",
            str(missing_base),
            "--sec-sources",
            str(missing_sec),
            "--official-sources",
            str(missing_official),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Missing required input file" in captured.err
    assert str(missing_base) in captured.err
    assert str(missing_sec) in captured.err
    assert str(missing_official) in captured.err


def test_cli_run_cpo_pack_regenerates_product_outputs(tmp_path):
    combined = tmp_path / "github_plus_primary.jsonl"
    readiness = tmp_path / "readiness.md"
    pack_dir = tmp_path / "pack"

    exit_code = main(
        [
            "run-cpo-pack",
            "--base-data",
            str(FIXTURE),
            "--sec-sources",
            str(SEC_COMPANYFACTS_SOURCES),
            "--official-sources",
            str(OFFICIAL_REPORT_SOURCES),
            "--combined-out",
            str(combined),
            "--readiness-out",
            str(readiness),
            "--pack-out-dir",
            str(pack_dir),
            "--query",
            "CPO laser bottleneck",
            "--tickers",
            "SIVE",
            "AAOI",
            "--allow-skipped",
            "--limit",
            "8",
        ]
    )

    assert exit_code == 0
    assert combined.exists()
    assert "official-report:SIVE:net-sales-2025" in combined.read_text(encoding="utf-8")
    readiness_text = readiness.read_text(encoding="utf-8")
    assert "# Batch Readiness Report" in readiness_text
    assert "| SIVE | ready |" in readiness_text
    assert "missing_primary_source" not in [
        cell.strip()
        for row in readiness_text.splitlines()
        if "| SIVE |" in row
        for cell in row.split("|")
    ]
    assert (pack_dir / "index.md").exists()
    assert (pack_dir / "sources.md").exists()
    assert (pack_dir / "sive-memo.md").exists()
    assert "official-report:SIVE:net-sales-2025" in (pack_dir / "sources.md").read_text(encoding="utf-8")


def test_cli_run_cpo_pack_fails_when_candidates_are_skipped_without_override(tmp_path, capsys):
    combined = tmp_path / "github_plus_primary.jsonl"
    readiness = tmp_path / "readiness.md"
    pack_dir = tmp_path / "pack"

    exit_code = main(
        [
            "run-cpo-pack",
            "--base-data",
            str(FIXTURE),
            "--sec-sources",
            str(SEC_COMPANYFACTS_SOURCES),
            "--official-sources",
            str(OFFICIAL_REPORT_SOURCES),
            "--combined-out",
            str(combined),
            "--readiness-out",
            str(readiness),
            "--pack-out-dir",
            str(pack_dir),
            "--query",
            "CPO laser bottleneck",
            "--tickers",
            "SIVE",
            "AAOI",
            "--limit",
            "8",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "Skipped memo candidate(s)" in captured.err
    assert "AAOI" in captured.err
    assert combined.exists()
    assert readiness.exists()
    assert (pack_dir / "index.md").exists()


def test_cli_build_acquisition_queue_writes_report(tmp_path):
    out = tmp_path / "acquisition-queue.md"

    exit_code = main(
        [
            "build-acquisition-queue",
            "--data",
            str(FIXTURE),
            "--query",
            "CPO laser bottleneck",
            "--tickers",
            "SIVE",
            "AAOI",
            "--out",
            str(out),
            "--limit",
            "4",
        ]
    )

    assert exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "# Evidence Acquisition Queue" in text
    assert "missing_primary_source" in text
    assert "| Priority | Ticker | Gap | Source Target | Search Prompt | Why It Matters | Acceptance Criteria | After Import |" in text
    assert "Source title, URL, and source excerpt must directly support the task claim." in text


def test_cli_ingest_task_evidence_writes_intake_and_refreshes_outputs(tmp_path):
    intake = tmp_path / "manual_intake.jsonl"
    readiness = tmp_path / "readiness.md"
    pack_dir = tmp_path / "pack"

    exit_code = main(
        [
            "ingest-task-evidence",
            "--out",
            str(intake),
            "--id",
            "manual:NVDA:risk:cpo-sourcing",
            "--source-title",
            "Manual NVDA risk note",
            "--source-url",
            "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
            "--published-at",
            "2026-07-04",
            "--claim",
            "NVDA faces CPO sourcing risk if optical component supply tightens.",
            "--summary",
            "Manual intake captures a negative/risk item for NVDA CPO sourcing.",
            "--source-excerpt",
            "SEC companyfacts URL validates the issuer identity; analyst note ties the filing to CPO sourcing risk.",
            "--tickers",
            "NVDA",
            "--themes",
            "CPO",
            "risk",
            "manual-intake",
            "--supply-chain-layer",
            "AI accelerator customer",
            "--direction",
            "negative",
            "--strength",
            "derived",
            "--claim-type",
            "risk",
            "--confidence",
            "0.72",
            "--factor-impact",
            "evidence_quality=8",
            "--factor-impact",
            "supply_elasticity=-5",
            "--refresh-data",
            str(FIXTURE),
            str(intake),
            "--refresh-query",
            "CPO laser bottleneck",
            "--refresh-tickers",
            "NVDA",
            "--readiness-out",
            str(readiness),
            "--pack-out-dir",
            str(pack_dir),
            "--limit",
            "4",
        ]
    )

    assert exit_code == 0
    assert "manual:NVDA:risk:cpo-sourcing" in intake.read_text(encoding="utf-8")
    assert "source_excerpt" in intake.read_text(encoding="utf-8")
    assert "# Batch Readiness Report" in readiness.read_text(encoding="utf-8")
    assert "# Serenity Alpha Lab Memo Pack" in (pack_dir / "index.md").read_text(encoding="utf-8")


def test_cli_ingest_task_evidence_rejects_missing_source_excerpt_before_refresh(tmp_path):
    intake = tmp_path / "manual_intake.jsonl"
    readiness = tmp_path / "readiness.md"
    pack_dir = tmp_path / "pack"

    try:
        main(
            [
                "ingest-task-evidence",
                "--out",
                str(intake),
                "--id",
                "manual:NVDA:risk:cpo-sourcing",
                "--source-title",
                "Manual NVDA risk note",
                "--source-url",
                "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
                "--published-at",
                "2026-07-04",
                "--claim",
                "NVDA faces CPO sourcing risk if optical component supply tightens.",
                "--summary",
                "Manual intake captures a negative/risk item for NVDA CPO sourcing.",
                "--tickers",
                "NVDA",
                "--themes",
                "CPO",
                "risk",
                "manual-intake",
                "--supply-chain-layer",
                "AI accelerator customer",
                "--direction",
                "negative",
                "--strength",
                "derived",
                "--claim-type",
                "risk",
                "--confidence",
                "0.72",
                "--factor-impact",
                "evidence_quality=8",
                "--refresh-data",
                str(FIXTURE),
                str(intake),
                "--refresh-query",
                "CPO laser bottleneck",
                "--refresh-tickers",
                "NVDA",
                "--readiness-out",
                str(readiness),
                "--pack-out-dir",
                str(pack_dir),
                "--limit",
                "4",
            ]
        )
    except ValueError as exc:
        assert "source excerpt" in str(exc).lower()
    else:
        raise AssertionError("missing source excerpt should be rejected")

    assert not intake.exists()
    assert not readiness.exists()
    assert not (pack_dir / "index.md").exists()


def test_cli_ingest_task_evidence_rejects_placeholder_source_before_refresh(tmp_path):
    intake = tmp_path / "manual_intake.jsonl"
    readiness = tmp_path / "readiness.md"
    pack_dir = tmp_path / "pack"

    try:
        main(
            [
                "ingest-task-evidence",
                "--out",
                str(intake),
                "--id",
                "manual:NVDA:risk:cpo-sourcing",
                "--source-title",
                "Manual NVDA risk note",
                "--source-url",
                "https://example.com/nvda-risk",
                "--published-at",
                "2026-07-04",
                "--claim",
                "NVDA faces CPO sourcing risk if optical component supply tightens.",
                "--summary",
                "Manual intake captures a negative/risk item for NVDA CPO sourcing.",
                "--source-excerpt",
                "SEC companyfacts URL validates the issuer identity; analyst note ties the filing to CPO sourcing risk.",
                "--tickers",
                "NVDA",
                "--themes",
                "CPO",
                "risk",
                "manual-intake",
                "--supply-chain-layer",
                "AI accelerator customer",
                "--direction",
                "negative",
                "--strength",
                "derived",
                "--claim-type",
                "risk",
                "--confidence",
                "0.72",
                "--factor-impact",
                "evidence_quality=8",
                "--refresh-data",
                str(FIXTURE),
                str(intake),
                "--refresh-query",
                "CPO laser bottleneck",
                "--refresh-tickers",
                "NVDA",
                "--readiness-out",
                str(readiness),
                "--pack-out-dir",
                str(pack_dir),
                "--limit",
                "4",
            ]
        )
    except ValueError as exc:
        assert "placeholder" in str(exc).lower()
    else:
        raise AssertionError("placeholder source URL should be rejected")

    assert not intake.exists()
    assert not readiness.exists()
    assert not (pack_dir / "index.md").exists()
