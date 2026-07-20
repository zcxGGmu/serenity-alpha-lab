from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from serenity_alpha_lab.application.research_orchestrator import (
    ResearchChatRequest,
    ResearchOrchestratorError,
    ResearchRequest,
)
from serenity_alpha_lab.integrations.dsa.research_orchestrator import (
    DsaResearchOrchestratorFacade,
)


@dataclass
class FakeAgentResult:
    success: bool = True
    content: str = ""
    dashboard: dict[str, Any] | None = field(default_factory=dict)
    tool_calls_log: list[dict[str, Any]] = field(default_factory=list)
    total_steps: int = 0
    total_tokens: int = 0
    provider: str = ""
    model: str = ""
    error: str | None = None


class FakeDsaOrchestrator:
    def __init__(self, result: FakeAgentResult | None = None) -> None:
        self.result = result or FakeAgentResult(
            success=True,
            content="{\"decision_type\":\"hold\"}",
            dashboard={"decision_type": "hold"},
            tool_calls_log=[{"tool": "get_realtime_quote", "success": True}],
            total_steps=3,
            total_tokens=500,
            provider="gemini",
            model="gemini/test-model",
        )
        self.run_calls: list[dict[str, Any]] = []
        self.chat_calls: list[dict[str, Any]] = []

    def run(self, task: str, context=None):
        self.run_calls.append({"task": task, "context": context})
        return self.result

    def chat(self, message: str, session_id: str, progress_callback=None, context=None):
        self.chat_calls.append(
            {
                "message": message,
                "session_id": session_id,
                "progress_callback": progress_callback,
                "context": context,
            }
        )
        if progress_callback is not None:
            progress_callback({"type": "stage_start", "stage": "technical"})
        return self.result


def test_dsa_research_orchestrator_facade_maps_run_result_fields() -> None:
    dsa = FakeDsaOrchestrator()
    facade = DsaResearchOrchestratorFacade(dsa)
    context = {"stock_code": "600519", "stock_name": "贵州茅台", "report_language": "zh"}

    result = facade.run(
        ResearchRequest(
            run_id="run-research-001",
            query="Analyze 600519",
            context=context,
        )
    )
    context["stock_code"] = "000001"

    assert dsa.run_calls == [
        {
            "task": "Analyze 600519",
            "context": {"stock_code": "600519", "stock_name": "贵州茅台", "report_language": "zh"},
        }
    ]
    assert result.run_id == "run-research-001"
    assert result.success is True
    assert result.content == "{\"decision_type\":\"hold\"}"
    assert result.dashboard == {"decision_type": "hold"}
    assert result.tool_calls_log == [{"tool": "get_realtime_quote", "success": True}]
    assert result.total_steps == 3
    assert result.total_tokens == 500
    assert result.provider == "gemini"
    assert result.model == "gemini/test-model"
    assert result.error is None


def test_dsa_research_orchestrator_facade_maps_failed_run_without_reinterpreting_error() -> None:
    dsa = FakeDsaOrchestrator(
        FakeAgentResult(
            success=False,
            content="LLM returned text but no dashboard JSON",
            dashboard=None,
            provider="ollama",
            error="Failed to parse dashboard JSON from agent response",
        )
    )
    facade = DsaResearchOrchestratorFacade(dsa)

    result = facade.run(ResearchRequest(run_id="run-failed-001", query="Analyze 600519"))

    assert result.success is False
    assert result.content == "LLM returned text but no dashboard JSON"
    assert result.dashboard is None
    assert result.provider == "ollama"
    assert result.error == "Failed to parse dashboard JSON from agent response"


def test_dsa_research_orchestrator_facade_chat_passes_session_progress_and_explicit_skills() -> None:
    dsa = FakeDsaOrchestrator(FakeAgentResult(success=True, content="assistant reply"))
    facade = DsaResearchOrchestratorFacade(dsa)
    events: list[dict[str, Any]] = []
    request = ResearchChatRequest(
        run_id="run-chat-001",
        message="换成缠论看一下",
        session_id="session-001",
        context={"stock_code": "600519", "skills": ["old_skill"]},
        skills=["chan_theory"],
    )

    result = facade.chat(request, progress_callback=events.append)

    assert result.run_id == "run-chat-001"
    assert result.content == "assistant reply"
    assert events == [{"type": "stage_start", "stage": "technical"}]
    assert dsa.chat_calls == [
        {
            "message": "换成缠论看一下",
            "session_id": "session-001",
            "progress_callback": events.append,
            "context": {
                "stock_code": "600519",
                "skills": ["chan_theory"],
                "strategies": ["chan_theory"],
            },
        }
    ]
    assert request.context == {"stock_code": "600519", "skills": ["old_skill"]}


def test_dsa_research_orchestrator_facade_wraps_unexpected_legacy_exceptions() -> None:
    class ExplodingDsaOrchestrator:
        def run(self, task: str, context=None):
            raise RuntimeError("provider exploded")

    facade = DsaResearchOrchestratorFacade(ExplodingDsaOrchestrator())

    with pytest.raises(ResearchOrchestratorError, match="DSA research orchestrator run failed"):
        facade.run(ResearchRequest(run_id="run-error-001", query="Analyze 600519"))
