from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Sequence


FORBIDDEN_PHRASES = (
    "you should buy",
    "you should sell",
    "you should hold",
    "target price",
    "price target",
    "position size",
    "position sizing",
)


@dataclass(frozen=True)
class ReportSafetyFinding:
    path: Path
    line_number: int
    phrase: str
    line: str


@dataclass(frozen=True)
class ReportSafetyResult:
    files_scanned: int
    findings: list[ReportSafetyFinding]

    @property
    def passed(self) -> bool:
        return not self.findings


def scan_report_safety(paths: Sequence[str | Path]) -> ReportSafetyResult:
    findings: list[ReportSafetyFinding] = []
    files_scanned = 0

    for path in paths:
        report_path = Path(path)
        files_scanned += 1
        findings.extend(_scan_text(report_path.read_text(encoding="utf-8"), report_path))

    return ReportSafetyResult(files_scanned=files_scanned, findings=findings)


def scan_report_text(markdown: str, *, path: str | Path = "<generated-report>") -> ReportSafetyResult:
    report_path = Path(path)
    return ReportSafetyResult(files_scanned=1, findings=_scan_text(markdown, report_path))


def render_report_safety_markdown(result: ReportSafetyResult) -> str:
    lines = [
        "# Report Safety Scan",
        "",
        f"**Files scanned:** {result.files_scanned}",
        f"**Findings:** {len(result.findings)}",
        "",
        "Policy: generated report text must remain research only; quoted source evidence lines are ignored.",
        "",
    ]

    if not result.findings:
        lines.extend(["## Findings", "", "- No generated-report safety findings detected.", ""])
        return "\n".join(lines)

    lines.extend(
        [
            "## Findings",
            "",
            "| File | Line | Phrase | Text |",
            "|---|---:|---|---|",
        ]
    )
    for finding in result.findings:
        lines.append(
            f"| {finding.path.name} | {finding.line_number} | {finding.phrase} | {_escape_table_cell(finding.line)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _forbidden_phrases(line: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", line.lower())
    return [phrase for phrase in FORBIDDEN_PHRASES if phrase in normalized]


def _scan_text(markdown: str, path: Path) -> list[ReportSafetyFinding]:
    findings: list[ReportSafetyFinding] = []
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        if _is_quoted_source_evidence_line(line):
            continue
        for phrase in _forbidden_phrases(line):
            findings.append(
                ReportSafetyFinding(
                    path=path,
                    line_number=line_number,
                    phrase=phrase,
                    line=line.strip(),
                )
            )
    return findings


def _is_quoted_source_evidence_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("- **"):
        return False
    if re.match(r"^- \*\*[^*]+:[^*]+\*\*", stripped):
        return True
    if re.match(r"^- \*\*(github|sec-companyfacts|official-report|manual):", stripped, flags=re.IGNORECASE):
        return True
    return False


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
