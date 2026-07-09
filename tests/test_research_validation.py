from __future__ import annotations

from datetime import date

from serenity_alpha_lab.research_validation import (
    BacktestObservation,
    PortfolioObservation,
    build_portfolio_research_snapshot,
    summarize_backtest_validation,
)


def test_portfolio_snapshot_is_research_validation_not_trade_automation():
    snapshot = build_portfolio_research_snapshot(
        portfolio_id="watchlist-alpha",
        as_of=date(2026, 7, 9),
        observations=[
            PortfolioObservation(
                symbol="SIVE",
                research_weight=0.42,
                evidence_ids=["evidence:sive:primary:2025-10k"],
                thesis="Primary-source margin expansion thesis needs validation.",
                risk_flags=["primary_source_gap_closed"],
            )
        ],
    )

    payload = snapshot.to_dict()

    assert payload["research_only"] is True
    assert payload["validation_scope"] == "portfolio_research_snapshot"
    assert payload["items"][0]["symbol"] == "SIVE"
    assert payload["items"][0]["evidence_ids"] == ["evidence:sive:primary:2025-10k"]
    assert payload["diagnostics"]["automation_enabled"] is False
    rendered = str(payload).lower()
    assert "position_size" not in rendered
    assert "broker" not in rendered
    assert "trade" not in rendered


def test_backtest_summary_is_historical_validation_not_future_promise():
    summary = summarize_backtest_validation(
        hypothesis_id="hypothesis:sive:margin-expansion",
        observations=[
            BacktestObservation(
                symbol="SIVE",
                analysis_date=date(2026, 6, 1),
                evaluation_window_days=20,
                start_value=10.0,
                end_value=11.5,
                evidence_ids=["evidence:sive:primary:2025-10k"],
            ),
            BacktestObservation(
                symbol="SIVE",
                analysis_date=date(2026, 6, 2),
                evaluation_window_days=20,
                start_value=12.0,
                end_value=11.4,
                evidence_ids=["evidence:sive:market-data:daily-bars"],
            ),
        ],
    )

    payload = summary.to_dict()

    assert payload["research_only"] is True
    assert payload["validation_scope"] == "historical_research_validation"
    assert payload["completed_count"] == 2
    assert payload["positive_count"] == 1
    assert payload["negative_count"] == 1
    assert payload["diagnostics"]["future_performance_disclaimer"] == "historical_validation_only"
    rendered = str(payload).lower()
    assert "guarantee" not in rendered
    assert "take_profit" not in rendered
    assert "stop_loss" not in rendered
