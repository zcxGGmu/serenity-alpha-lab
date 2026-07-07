from pathlib import Path

from serenity_alpha_lab.report_safety import (
    render_report_safety_markdown,
    scan_report_safety,
)


def test_scan_report_safety_flags_generated_recommendations(tmp_path):
    report = tmp_path / "unsafe-memo.md"
    report.write_text(
        "\n".join(
            [
                "# Serenity Alpha Lab Memo",
                "",
                "## Thesis Summary",
                "",
                "You should buy AAOI now because the setup is improving.",
                "",
                "This memo is research only.",
            ]
        ),
        encoding="utf-8",
    )

    result = scan_report_safety([report])

    assert result.files_scanned == 1
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.path == report
    assert finding.line_number == 5
    assert finding.phrase == "you should buy"


def test_scan_report_safety_ignores_quoted_source_evidence(tmp_path):
    report = tmp_path / "quoted-evidence-memo.md"
    report.write_text(
        "\n".join(
            [
                "# Serenity Alpha Lab Memo",
                "",
                "## Supporting Evidence",
                "",
                '- **github:example:1** [source](https://example.com) (2026-01-01, speculative, inference, confidence 0.56): '
                'The source says "buy / sell / hold / size" when describing an external framework.',
                "",
                "## Disclaimer",
                "",
                "This memo is research only and does not provide investment advice.",
            ]
        ),
        encoding="utf-8",
    )

    result = scan_report_safety([report])

    assert result.files_scanned == 1
    assert result.findings == []


def test_render_report_safety_markdown_summarizes_clean_and_blocked_files(tmp_path):
    clean = tmp_path / "clean.md"
    unsafe = tmp_path / "unsafe.md"
    clean.write_text("# Memo\n\nThis memo is research only.\n", encoding="utf-8")
    unsafe.write_text("# Memo\n\nTarget price is $100.\n", encoding="utf-8")

    result = scan_report_safety([clean, unsafe])
    markdown = render_report_safety_markdown(result)

    assert "# Report Safety Scan" in markdown
    assert "**Files scanned:** 2" in markdown
    assert "**Findings:** 1" in markdown
    assert "| unsafe.md | 3 | target price |" in markdown
    assert "quoted source evidence lines are ignored" in markdown
