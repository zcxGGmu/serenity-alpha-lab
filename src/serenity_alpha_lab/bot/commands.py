from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from serenity_alpha_lab.agents import (
    ResearchToolContext,
    ResearchToolResult,
    build_research_tool_registry,
)
from serenity_alpha_lab.report_safety import scan_report_text

from .contracts import BotResponse


def run_status_command() -> BotResponse:
    return BotResponse(
        status="ok",
        text=(
            "Serenity research Bot is enabled for local research-only commands. "
            "Platform delivery remains disabled."
        ),
        diagnostics={"platform_delivery": "disabled"},
    )


def run_analysis_command(
    analysis: Mapping[str, Any],
    *,
    requested_by: str,
) -> BotResponse:
    result = _execute_agent_tool(
        "serenity_research_summary",
        analysis=analysis,
        requested_by=requested_by,
    )
    payload = result.to_dict()
    diagnostics = _public_diagnostics(result)
    if result.status in {"blocked", "failed_open"}:
        return BotResponse(
            status=result.status,
            text=_blocked_text(result.status),
            diagnostics=diagnostics,
        )

    subject = _mapping(payload.get("subject"))
    readiness = _mapping(payload.get("readiness"))
    report_gate = _mapping(payload.get("report_gate"))
    signals = _mapping(payload.get("signals"))
    evidence_ids = _string_list(payload.get("evidence_ids"))
    report_gate_status = report_gate.get("status")
    if not report_gate_status and "available" in report_gate:
        report_gate_status = "available" if report_gate["available"] else "blocked"

    lines = [
        "Serenity research-only analysis",
        f"Symbol: {subject.get('code') or 'unknown'}",
        f"Readiness: {readiness.get('status') or result.status}",
        f"Report gate: {report_gate_status or 'unknown'}",
        f"Signal: {signals.get('rating') or 'unavailable'}",
        f"Confidence: {signals.get('confidence') or 'unavailable'}",
    ]
    if evidence_ids:
        lines.extend(["Evidence IDs:", *[f"- {item}" for item in evidence_ids]])
    else:
        lines.append("Evidence IDs: unavailable")

    return _safe_text_response(
        status=result.status,
        text="\n".join(lines),
        evidence_ids=evidence_ids,
        diagnostics=diagnostics,
    )


def run_evidence_gaps_command(
    analysis: Mapping[str, Any],
    *,
    requested_by: str,
) -> BotResponse:
    result = _execute_agent_tool(
        "serenity_evidence_gaps",
        analysis=analysis,
        requested_by=requested_by,
    )
    payload = result.to_dict()
    diagnostics = _public_diagnostics(result)
    if result.status in {"blocked", "failed_open"}:
        return BotResponse(
            status=result.status,
            text=_blocked_text(result.status),
            diagnostics=diagnostics,
        )

    gaps = payload.get("gaps")
    gap_codes = [
        str(item["gap_code"])
        for item in gaps
        if isinstance(gaps, list)
        and isinstance(item, Mapping)
        and isinstance(item.get("gap_code"), str)
    ] if isinstance(gaps, list) else []
    evidence_ids = _string_list(payload.get("evidence_ids"))
    readiness = _mapping(payload.get("readiness"))

    lines = [
        "Serenity research-only evidence gaps",
        f"Readiness: {readiness.get('status') or result.status}",
    ]
    if gap_codes:
        lines.extend(f"- {gap_code}" for gap_code in gap_codes)
    else:
        lines.append("- No evidence gaps were reported.")

    return _safe_text_response(
        status=result.status,
        text="\n".join(lines),
        evidence_ids=evidence_ids,
        diagnostics=diagnostics,
    )


def _execute_agent_tool(
    tool_name: str,
    *,
    analysis: Mapping[str, Any],
    requested_by: str,
) -> ResearchToolResult:
    registry = build_research_tool_registry(
        enabled=True,
        allowlist=[tool_name],
    )
    return registry.execute(
        tool_name,
        context=ResearchToolContext(
            analysis=analysis,
            requested_by=requested_by,
        ),
    )


def _public_diagnostics(result: ResearchToolResult) -> dict[str, Any]:
    diagnostics = dict(result.diagnostics)
    reason = diagnostics.get("reason")
    if reason == "forbidden_output_field":
        return {"reason": reason}
    if result.status == "failed_open":
        error_type = diagnostics.get("error_type")
        return {"error_type": error_type} if isinstance(error_type, str) else {}
    return diagnostics


def _blocked_text(status: str) -> str:
    if status == "failed_open":
        return "The local research command failed open without exposing internal details."
    return "The analysis context was blocked by the research-only boundary."


def _safe_text_response(
    *,
    status: str,
    text: str,
    evidence_ids: list[str],
    diagnostics: dict[str, Any],
) -> BotResponse:
    safety = scan_report_text(text, path="<research-bot-response>")
    if not safety.passed:
        return BotResponse(
            status="blocked",
            text="The research response was blocked by the report safety boundary.",
            diagnostics={"reason": "report_safety_violation"},
        )
    return BotResponse(
        status=status,
        text=text,
        evidence_ids=evidence_ids,
        diagnostics=diagnostics,
    )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [item for item in value if isinstance(item, str)]
