from __future__ import annotations

from serenity_alpha_lab.bot import BotMessage, ResearchBotDispatcher


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


def test_research_bot_is_disabled_by_default_and_does_not_call_services() -> None:
    calls: list[str] = []
    dispatcher = ResearchBotDispatcher(analyze=lambda symbol: calls.append(symbol))

    response = dispatcher.dispatch(
        BotMessage(user_id="u1", content="/analyze SIVE"),
    )

    assert response.status == "disabled"
    assert calls == []
    assert response.research_only is True
    assert response.diagnostics["reason"] == "research_bot_default_off"


def test_research_bot_parses_aliases_and_unknown_commands() -> None:
    dispatcher = ResearchBotDispatcher(enabled=True, analyze=lambda symbol: {})

    assert dispatcher.parse_command("分析 SIVE") == ("analyze", ["SIVE"])
    assert dispatcher.parse_command("/gaps SIVE") == ("evidence-gaps", ["SIVE"])
    assert dispatcher.parse_command("状态") == ("status", [])

    response = dispatcher.dispatch(BotMessage(user_id="u1", content="/unknown"))
    assert response.status == "error"
    assert "help" in response.text.lower()
    assert response.diagnostics["reason"] == "unknown_command"


def test_bot_analyze_and_evidence_gap_commands_preserve_research_states() -> None:
    analysis = _analysis_payload()
    calls: list[str] = []

    def analyze(symbol: str) -> dict:
        calls.append(symbol)
        return analysis

    dispatcher = ResearchBotDispatcher(enabled=True, analyze=analyze)

    analyze_response = dispatcher.dispatch(
        BotMessage(user_id="u1", content="/analyze SIVE"),
    )
    gap_response = dispatcher.dispatch(
        BotMessage(user_id="u2", content="/evidence-gaps SIVE"),
    )

    assert calls == ["SIVE", "SIVE"]
    assert analyze_response.status == "needs_work"
    assert analyze_response.evidence_ids == [
        "serenity:market-data:SIVE:quote:2026-07-10"
    ]
    assert "Readiness: needs_work" in analyze_response.text
    assert "Report gate: blocked" in analyze_response.text
    assert "research-only" in analyze_response.text.lower()
    assert gap_response.status == "needs_work"
    assert "missing_primary_source" in gap_response.text
    assert "missing_risk_coverage" in gap_response.text


def test_bot_accepts_analysis_objects_with_to_dict() -> None:
    class AnalysisObject:
        def to_dict(self) -> dict:
            return _analysis_payload()

    dispatcher = ResearchBotDispatcher(
        enabled=True,
        analyze=lambda symbol: AnalysisObject(),
    )

    response = dispatcher.dispatch(
        BotMessage(user_id="u1", content="/analyze SIVE"),
    )

    assert response.status == "needs_work"
    assert response.evidence_ids


def test_bot_rate_limit_uses_injected_monotonic_clock() -> None:
    now = [10.0]
    dispatcher = ResearchBotDispatcher(
        enabled=True,
        analyze=lambda symbol: _analysis_payload(),
        max_requests=1,
        window_seconds=60,
        clock=lambda: now[0],
    )

    first = dispatcher.dispatch(BotMessage(user_id="u1", content="/status"))
    second = dispatcher.dispatch(BotMessage(user_id="u1", content="/status"))
    now[0] = 71.0
    third = dispatcher.dispatch(BotMessage(user_id="u1", content="/status"))

    assert first.status == "ok"
    assert second.status == "rate_limited"
    assert third.status == "ok"
    assert second.diagnostics == {
        "reason": "rate_limit_exceeded",
        "window_seconds": 60,
    }


def test_bot_validates_arguments_before_calling_analysis() -> None:
    calls: list[str] = []
    dispatcher = ResearchBotDispatcher(
        enabled=True,
        analyze=lambda symbol: calls.append(symbol),
    )

    missing = dispatcher.dispatch(BotMessage(user_id="u1", content="/analyze"))
    too_many = dispatcher.dispatch(
        BotMessage(user_id="u2", content="/evidence-gaps SIVE EXTRA"),
    )
    invalid = dispatcher.dispatch(
        BotMessage(user_id="u3", content="/analyze ../../secret"),
    )

    assert missing.status == "error"
    assert too_many.status == "error"
    assert invalid.status == "error"
    assert calls == []


def test_bot_sanitizes_service_failures_and_forbidden_analysis_fields() -> None:
    def failing_analyze(symbol: str) -> dict:
        raise RuntimeError(f"do not expose /Users/example/private/{symbol}")

    failed = ResearchBotDispatcher(
        enabled=True,
        analyze=failing_analyze,
    ).dispatch(BotMessage(user_id="u1", content="/analyze SIVE"))

    unsafe_payload = {
        **_analysis_payload(),
        "nested": {"operation_advice": "buy"},
    }
    blocked = ResearchBotDispatcher(
        enabled=True,
        analyze=lambda symbol: unsafe_payload,
    ).dispatch(BotMessage(user_id="u1", content="/analyze SIVE"))

    assert failed.status == "failed_open"
    assert failed.diagnostics == {"error_type": "RuntimeError"}
    assert "/Users/example/private" not in str(failed.to_dict())
    assert "SIVE" not in failed.text
    assert blocked.status == "blocked"
    assert blocked.diagnostics["reason"] == "forbidden_output_field"
    rendered = str(blocked.to_dict()).lower()
    assert "operation_advice" not in rendered
    assert "target_price" not in rendered


def test_bot_report_safety_blocks_unsafe_signal_text() -> None:
    unsafe_payload = _analysis_payload()
    unsafe_payload["signals"] = {
        **unsafe_payload["signals"],
        "rating": "you should buy",
    }
    response = ResearchBotDispatcher(
        enabled=True,
        analyze=lambda symbol: unsafe_payload,
    ).dispatch(BotMessage(user_id="u1", content="/analyze SIVE"))

    assert response.status == "blocked"
    assert response.diagnostics["reason"] == "report_safety_violation"
    assert "you should buy" not in response.text.lower()
