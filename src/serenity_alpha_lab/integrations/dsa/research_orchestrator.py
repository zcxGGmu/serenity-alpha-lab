from __future__ import annotations

from typing import Any, Mapping

from serenity_alpha_lab.application.research_orchestrator import (
    ProgressCallback,
    ResearchChatRequest,
    ResearchOrchestratorError,
    ResearchRequest,
    ResearchResult,
)


class DsaResearchOrchestratorFacade:
    """ResearchOrchestrator facade for an injected DSA AgentOrchestrator-like object."""

    def __init__(self, orchestrator: Any) -> None:
        self._orchestrator = orchestrator

    def run(self, request: ResearchRequest) -> ResearchResult:
        try:
            result = self._orchestrator.run(request.query, context=dict(request.context))
        except Exception as exc:
            raise ResearchOrchestratorError("DSA research orchestrator run failed") from exc
        return research_result_from_legacy_agent_result(request.run_id, result)

    def chat(
        self,
        request: ResearchChatRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> ResearchResult:
        context = dict(request.context)
        if request.skills is not None:
            skills = list(request.skills)
            context["skills"] = skills
            context["strategies"] = list(skills)

        try:
            result = self._orchestrator.chat(
                message=request.message,
                session_id=request.session_id,
                progress_callback=progress_callback,
                context=context,
            )
        except Exception as exc:
            raise ResearchOrchestratorError("DSA research orchestrator chat failed") from exc
        return research_result_from_legacy_agent_result(request.run_id, result)


def research_result_from_legacy_agent_result(run_id: str, result: Any) -> ResearchResult:
    record = _legacy_result_record(result)
    dashboard = record.get("dashboard")
    if dashboard is not None and not isinstance(dashboard, Mapping):
        dashboard = None

    return ResearchResult(
        run_id=run_id,
        success=bool(record.get("success", False)),
        content=str(record.get("content") or ""),
        dashboard=dashboard,
        tool_calls_log=_tool_calls_log(record.get("tool_calls_log")),
        total_steps=_coerce_int(record.get("total_steps")),
        total_tokens=_coerce_int(record.get("total_tokens")),
        provider=str(record.get("provider") or ""),
        model=str(record.get("model") or ""),
        error=None if record.get("error") is None else str(record.get("error")),
    )


def _legacy_result_record(result: Any) -> dict[str, Any]:
    if isinstance(result, Mapping):
        return dict(result)
    if hasattr(result, "to_dict"):
        return dict(result.to_dict())
    return {
        "success": getattr(result, "success", False),
        "content": getattr(result, "content", ""),
        "dashboard": getattr(result, "dashboard", None),
        "tool_calls_log": getattr(result, "tool_calls_log", []),
        "total_steps": getattr(result, "total_steps", 0),
        "total_tokens": getattr(result, "total_tokens", 0),
        "provider": getattr(result, "provider", ""),
        "model": getattr(result, "model", ""),
        "error": getattr(result, "error", None),
    }


def _tool_calls_log(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    log: list[dict[str, Any]] = []
    for item in list(value):
        log.append(dict(item) if isinstance(item, Mapping) else {"value": item})
    return log


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
