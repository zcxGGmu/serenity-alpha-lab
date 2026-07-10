from __future__ import annotations

from serenity_alpha_lab.agents import (
    ResearchToolContext,
    ResearchToolDefinition,
    ResearchToolRegistry,
    ResearchToolResult,
    build_research_tool_registry,
)


def _analysis_payload() -> dict:
    return {
        "symbol": "SIVE",
        "stock_name": "Sivers Semiconductors",
        "market": "us",
        "status": "completed",
        "research_only": True,
        "readiness": {
            "status": "needs_work",
            "flag_codes": ["missing_risk_coverage", "missing_primary_source"],
            "source_coverage": {
                "focus_ticker": "SIVE",
                "focus_evidence_count": 1,
                "primary_count": 0,
                "risk_count": 0,
            },
        },
        "report_gate": {
            "status": "blocked",
            "reason": "readiness_not_ready",
            "research_only": True,
        },
        "signals": {
            "rating": "Watchlist Candidate",
            "confidence": "low",
            "gaps": ["missing_primary_source", "missing_risk_coverage"],
            "evidence_ids": ["serenity:market-data:SIVE:quote:2026-07-10"],
        },
        "evidence": [
            {
                "id": "serenity:market-data:SIVE:quote:2026-07-10",
                "source_url": "serenity://market-data/SIVE/quote/2026-07-10",
                "claim_type": "fact",
            }
        ],
        "diagnostics": {"provider_status": "ok"},
    }


def test_agent_tools_are_hidden_by_default_and_require_explicit_context() -> None:
    disabled = build_research_tool_registry(enabled=False)
    assert disabled.list_names() == []

    enabled = build_research_tool_registry(
        enabled=True,
        allowlist=["serenity_research_summary"],
    )
    result = enabled.execute("serenity_research_summary", context=None)
    payload = result.to_dict()

    assert payload["status"] == "blocked"
    assert payload["diagnostics"]["reason"] == "analysis_context_required"
    assert payload["research_only"] is True


def test_agent_summary_preserves_real_analysis_readiness_and_provenance() -> None:
    registry = build_research_tool_registry(
        enabled=True,
        allowlist=["serenity_research_summary", "serenity_evidence_gaps"],
    )
    context = ResearchToolContext(analysis=_analysis_payload(), requested_by="test")

    summary = registry.execute("serenity_research_summary", context=context).to_dict()
    gaps = registry.execute("serenity_evidence_gaps", context=context).to_dict()

    assert summary["status"] == "needs_work"
    assert summary["readiness"]["status"] == "needs_work"
    assert summary["readiness"]["source_coverage"]["primary_count"] == 0
    assert summary["report_gate"]["status"] == "blocked"
    assert summary["evidence_ids"] == [
        "serenity:market-data:SIVE:quote:2026-07-10"
    ]
    assert summary["subject"] == {
        "code": "SIVE",
        "stock_name": "Sivers Semiconductors",
        "market": "us",
    }
    assert [item["gap_code"] for item in gaps["gaps"]] == [
        "missing_primary_source",
        "missing_risk_coverage",
    ]


def test_agent_summary_accepts_compatible_subject_and_report_gate_shape() -> None:
    payload = _analysis_payload()
    payload.pop("symbol")
    payload.pop("stock_name")
    payload.pop("market")
    payload["subject"] = {
        "code": "SIVE",
        "stock_name": "Sivers Semiconductors",
        "market": "us",
    }
    payload["readiness"] = {
        "status": "needs_work",
        "gaps": ["missing_primary_source"],
    }
    payload["report_gate"] = {
        "available": False,
        "reason": "readiness_not_ready",
    }

    registry = build_research_tool_registry(
        enabled=True,
        allowlist=["serenity_research_summary"],
    )
    result = registry.execute(
        "serenity_research_summary",
        context=ResearchToolContext(analysis=payload, requested_by="test"),
    ).to_dict()

    assert result["status"] == "needs_work"
    assert result["subject"]["code"] == "SIVE"
    assert result["report_gate"]["available"] is False


def test_agent_summary_fails_closed_for_unknown_readiness_status() -> None:
    payload = _analysis_payload()
    payload["readiness"]["status"] = "you should buy"
    registry = build_research_tool_registry(
        enabled=True,
        allowlist=["serenity_research_summary"],
    )

    result = registry.execute(
        "serenity_research_summary",
        context=ResearchToolContext(analysis=payload, requested_by="test"),
    ).to_dict()

    assert result["status"] == "blocked"


def test_agent_runtime_blocks_recursive_trading_fields_in_input() -> None:
    registry = build_research_tool_registry(
        enabled=True,
        allowlist=["serenity_research_summary"],
    )
    context = ResearchToolContext(
        analysis={**_analysis_payload(), "nested": {"operation_advice": "buy"}},
        requested_by="test",
    )

    payload = registry.execute(
        "serenity_research_summary",
        context=context,
    ).to_dict()

    assert payload["status"] == "blocked"
    assert payload["diagnostics"]["reason"] == "forbidden_output_field"
    assert payload["diagnostics"]["field"] == "operation_advice"


def test_agent_runtime_blocks_recursive_trading_fields_in_output() -> None:
    definition = ResearchToolDefinition(
        name="unsafe_test_tool",
        description="Test-only unsafe tool.",
    )

    def unsafe_handler(context: ResearchToolContext) -> ResearchToolResult:
        return ResearchToolResult(
            tool="unsafe_test_tool",
            status="ok",
            payload={"nested": [{"target_price": 100}]},
            diagnostics={},
        )

    registry = ResearchToolRegistry(
        enabled=True,
        allowlist=["unsafe_test_tool"],
        definitions=[definition],
        handlers={"unsafe_test_tool": unsafe_handler},
    )

    payload = registry.execute(
        "unsafe_test_tool",
        context=ResearchToolContext(analysis=_analysis_payload(), requested_by="test"),
    ).to_dict()

    assert payload["status"] == "blocked"
    assert payload["diagnostics"] == {
        "reason": "forbidden_output_field",
        "field": "target_price",
    }


def test_agent_runtime_does_not_call_unavailable_handlers() -> None:
    calls: list[str] = []
    definition = ResearchToolDefinition(
        name="hidden_test_tool",
        description="Test-only hidden tool.",
    )

    def handler(context: ResearchToolContext) -> ResearchToolResult:
        calls.append(context.requested_by)
        return ResearchToolResult(
            tool="hidden_test_tool",
            status="ok",
            payload={},
            diagnostics={},
        )

    registry = ResearchToolRegistry(
        enabled=True,
        allowlist=[],
        definitions=[definition],
        handlers={"hidden_test_tool": handler},
    )
    payload = registry.execute(
        "hidden_test_tool",
        context=ResearchToolContext(analysis=_analysis_payload(), requested_by="test"),
    ).to_dict()

    assert payload["status"] == "blocked"
    assert payload["diagnostics"]["reason"] == "tool_not_available"
    assert calls == []


def test_agent_runtime_sanitizes_handler_failures() -> None:
    definition = ResearchToolDefinition(
        name="failing_test_tool",
        description="Test-only failing tool.",
    )

    def failing_handler(context: ResearchToolContext) -> ResearchToolResult:
        raise RuntimeError(
            f"do not expose /Users/example/private or {context.analysis['symbol']}"
        )

    registry = ResearchToolRegistry(
        enabled=True,
        allowlist=["failing_test_tool"],
        definitions=[definition],
        handlers={"failing_test_tool": failing_handler},
    )
    payload = registry.execute(
        "failing_test_tool",
        context=ResearchToolContext(analysis=_analysis_payload(), requested_by="test"),
    ).to_dict()

    assert payload["status"] == "failed_open"
    assert payload["diagnostics"] == {"error_type": "RuntimeError"}
    rendered = str(payload)
    assert "/Users/example/private" not in rendered
    assert "SIVE" not in rendered
