from __future__ import annotations

import pytest

from serenity_alpha_lab.application.research_orchestrator import (
    ResearchChatRequest,
    ResearchMode,
    ResearchOrchestrator,
    ResearchOrchestratorError,
    ResearchRequest,
    ResearchResult,
)


class MinimalResearchOrchestrator:
    def run(self, request: ResearchRequest) -> ResearchResult:
        return ResearchResult(run_id=request.run_id, success=True, content="dashboard")

    def chat(self, request: ResearchChatRequest, progress_callback=None) -> ResearchResult:
        return ResearchResult(run_id=request.run_id, success=True, content="chat")


def test_research_orchestrator_protocol_is_runtime_checkable() -> None:
    assert isinstance(MinimalResearchOrchestrator(), ResearchOrchestrator)


def test_research_request_validates_and_copies_context() -> None:
    context = {"stock_code": "600519", "report_language": "zh"}

    request = ResearchRequest(
        run_id="run-research-001",
        query="Analyze 600519",
        context=context,
        mode=ResearchMode.DASHBOARD,
        idempotency_key="research:600519:2026-07-20",
    )
    context["stock_code"] = "000001"

    assert request.run_id == "run-research-001"
    assert request.query == "Analyze 600519"
    assert request.context == {"stock_code": "600519", "report_language": "zh"}
    assert request.mode is ResearchMode.DASHBOARD
    assert request.idempotency_key == "research:600519:2026-07-20"


def test_research_request_rejects_missing_required_fields() -> None:
    with pytest.raises(ResearchOrchestratorError, match="run_id is required"):
        ResearchRequest(run_id="", query="Analyze")

    with pytest.raises(ResearchOrchestratorError, match="query is required"):
        ResearchRequest(run_id="run-001", query="   ")


def test_research_chat_request_normalizes_skills_without_mutating_context() -> None:
    context = {"stock_code": "600519", "skills": ["old_skill"]}

    request = ResearchChatRequest(
        run_id="run-chat-001",
        message="换成缠论看一下",
        session_id="session-001",
        context=context,
        skills=["chan_theory", "risk_review"],
    )
    context["skills"].append("mutated")

    assert request.context == {"stock_code": "600519", "skills": ["old_skill"]}
    assert request.skills == ("chan_theory", "risk_review")


def test_research_chat_request_rejects_missing_message_or_session() -> None:
    with pytest.raises(ResearchOrchestratorError, match="message is required"):
        ResearchChatRequest(run_id="run-chat-001", message="", session_id="session-001")

    with pytest.raises(ResearchOrchestratorError, match="session_id is required"):
        ResearchChatRequest(run_id="run-chat-001", message="hello", session_id=" ")


def test_research_result_preserves_agent_result_compatible_fields() -> None:
    dashboard = {"decision_type": "hold"}
    tool_calls_log = [{"tool": "get_realtime_quote", "success": True}]

    result = ResearchResult(
        run_id="run-result-001",
        success=True,
        content="{\"decision_type\":\"hold\"}",
        dashboard=dashboard,
        tool_calls_log=tool_calls_log,
        total_steps=3,
        total_tokens=500,
        provider="gemini",
        model="gemini/test-model",
    )
    dashboard["decision_type"] = "buy"
    tool_calls_log.append({"tool": "mutated"})

    assert result.run_id == "run-result-001"
    assert result.success is True
    assert result.dashboard == {"decision_type": "hold"}
    assert result.tool_calls_log == [{"tool": "get_realtime_quote", "success": True}]
    assert result.total_steps == 3
    assert result.total_tokens == 500
    assert result.provider == "gemini"
    assert result.model == "gemini/test-model"
