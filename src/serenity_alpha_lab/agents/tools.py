from __future__ import annotations

from typing import Any, Iterable, Mapping

from .contracts import ResearchToolContext, ResearchToolResult


SUMMARY_TOOL_NAME = "serenity_research_summary"
EVIDENCE_GAPS_TOOL_NAME = "serenity_evidence_gaps"

_GAP_PRIORITY = (
    "missing_primary_source",
    "missing_risk_coverage",
)


def serenity_research_summary(context: ResearchToolContext) -> ResearchToolResult:
    analysis = context.analysis
    readiness = _mapping_value(analysis, "readiness")
    report_gate = _mapping_value(analysis, "report_gate")
    signals = _mapping_value(analysis, "signals")
    source_coverage = _source_coverage(analysis, readiness)

    payload: dict[str, Any] = {
        "subject": _subject(analysis),
        "readiness": readiness,
        "source_coverage": source_coverage,
        "report_gate": report_gate,
        "signals": signals,
        "evidence_ids": _evidence_ids(analysis, signals),
    }

    return ResearchToolResult(
        tool=SUMMARY_TOOL_NAME,
        status=_research_status(analysis, readiness),
        payload=payload,
    )


def serenity_evidence_gaps(context: ResearchToolContext) -> ResearchToolResult:
    analysis = context.analysis
    readiness = _mapping_value(analysis, "readiness")
    report_gate = _mapping_value(analysis, "report_gate")
    signals = _mapping_value(analysis, "signals")
    source_coverage = _source_coverage(analysis, readiness)

    gap_values = [
        *_string_items(readiness.get("flag_codes")),
        *_string_items(readiness.get("gaps")),
        *_string_items(signals.get("gaps")),
    ]
    unique_gaps = set(gap_values)
    ordered_gaps = [
        gap
        for gap in _GAP_PRIORITY
        if gap in unique_gaps
    ]
    ordered_gaps.extend(sorted(unique_gaps.difference(_GAP_PRIORITY)))

    return ResearchToolResult(
        tool=EVIDENCE_GAPS_TOOL_NAME,
        status=_research_status(analysis, readiness),
        payload={
            "gaps": [
                {
                    "gap_code": gap,
                    "priority": index + 1,
                    "status": "open",
                    "research_only": True,
                }
                for index, gap in enumerate(ordered_gaps)
            ],
            "readiness": readiness,
            "source_coverage": source_coverage,
            "report_gate": report_gate,
            "evidence_ids": _evidence_ids(analysis, signals),
        },
    )


def _mapping_value(source: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = source.get(key)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _source_coverage(
    analysis: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    direct = analysis.get("source_coverage")
    if isinstance(direct, Mapping):
        return dict(direct)

    nested = readiness.get("source_coverage")
    if isinstance(nested, Mapping):
        return dict(nested)
    return {}


def _subject(analysis: Mapping[str, Any]) -> dict[str, Any]:
    subject = analysis.get("subject")
    if isinstance(subject, Mapping):
        return dict(subject)
    return {
        "code": analysis.get("symbol", ""),
        "stock_name": analysis.get("stock_name", ""),
        "market": analysis.get("market", ""),
    }


def _evidence_ids(
    analysis: Mapping[str, Any],
    signals: Mapping[str, Any],
) -> list[str]:
    signal_ids = list(_string_items(signals.get("evidence_ids")))
    if signal_ids:
        return signal_ids

    evidence = analysis.get("evidence")
    if not isinstance(evidence, (list, tuple)):
        return []
    return [
        item["id"]
        for item in evidence
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    ]


def _research_status(
    analysis: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> str:
    readiness_status = readiness.get("status")
    if readiness_status in {"ready", "needs_work", "blocked"}:
        return str(readiness_status)

    analysis_status = analysis.get("status")
    if analysis_status in {"ready", "needs_work", "blocked"}:
        return str(analysis_status)
    return "blocked"


def _string_items(value: Any) -> Iterable[str]:
    if not isinstance(value, (list, tuple)):
        return ()
    return (item for item in value if isinstance(item, str))
