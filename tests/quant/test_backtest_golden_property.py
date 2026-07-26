from __future__ import annotations

import ast
import json
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

import pytest

from serenity_alpha_lab.quant.backtest.golden import (
    BACKTEST_GOLDEN_FIXTURE_CONTRACT_VERSION,
    BacktestGoldenFixtureError,
    BacktestGoldenRunner,
    default_backtest_golden_fixture,
)


def test_backtest_golden_fixture_covers_required_rules_and_expected_results() -> None:
    fixture = default_backtest_golden_fixture()
    result = BacktestGoldenRunner(fixture).run()

    assert result.contract_version == BACKTEST_GOLDEN_FIXTURE_CONTRACT_VERSION
    assert result.fixture_summary == {
        "fixture_id": "btg_cn_a_share_hand_computable_v1",
        "instrument_count": 3,
        "trading_day_count": 20,
        "bar_count": 60,
        "chunked_read_supported": True,
        "production_backtest_promoted": False,
    }
    assert set(result.covered_rules) == {
        "fees",
        "t_plus_one",
        "suspension",
        "limit_up_down",
        "cash_dividend",
        "rebalance",
        "chunked_vs_full_read",
    }
    assert result.order_statuses == {
        "ord-golden-buy-600519": "filled",
        "ord-golden-tplus-one-sell-600519": "expired",
        "ord-golden-suspended-buy-000001": "rejected",
        "ord-golden-limit-up-buy-300750": "expired",
        "ord-golden-sell-600519": "filled",
    }
    assert result.execution_count == 2
    assert result.corporate_action_count == 1
    assert result.final_cash == Decimal("10246.600")
    assert result.final_equity == Decimal("10246.600")
    assert result.total_transaction_cost == Decimal("3.400")
    assert result.realized_pnl == Decimal("196.600")
    assert result.metrics_report.returns["cumulative_return"] == Decimal("0.024660")
    assert result.metrics_report.costs["total_cost"] == Decimal("3.400000")
    assert result.metrics_report.trading["closed_trade_count"] == 1

    record = result.to_record()
    assert record["scope"] == "formal_portfolio_backtest_golden_fixture"
    assert record["production_backtest_promoted"] is False
    assert record["metrics"]["returns"]["cumulative_return"] == "0.024660"
    json.dumps(record, sort_keys=True)


def test_chunked_and_full_fixture_reads_are_identical_and_hash_stable() -> None:
    fixture = default_backtest_golden_fixture()

    full = BacktestGoldenRunner(fixture).run()
    chunked_by_1 = BacktestGoldenRunner(fixture).run(chunk_size=1)
    chunked_by_7 = BacktestGoldenRunner(fixture).run(chunk_size=7)

    assert chunked_by_1.to_record() == full.to_record()
    assert chunked_by_7.to_record() == full.to_record()
    assert chunked_by_1.result_hash == full.result_hash
    assert chunked_by_7.result_hash == full.result_hash
    assert len(tuple(fixture.iter_bar_chunks(chunk_size=7))) == 9

    with pytest.raises(BacktestGoldenFixtureError, match="chunk_size must be positive"):
        tuple(fixture.iter_bar_chunks(chunk_size=0))


def test_golden_property_invariants_hold_for_every_equity_point_and_event() -> None:
    result = BacktestGoldenRunner(default_backtest_golden_fixture()).run()

    assert result.equity_curve[0].equity == Decimal("10000.000")
    assert result.equity_curve[-1].equity == result.final_equity
    assert all(point.equity > 0 for point in result.equity_curve)
    assert len({point.valuation_date for point in result.equity_curve}) == len(result.equity_curve)
    assert all(left.valuation_date < right.valuation_date for left, right in pairwise(result.equity_curve))
    assert result.ledger.equity == result.final_equity
    assert result.ledger.reconciliation_record()["equity_formula"] == (
        "cash + position_market_value + receivables - payables"
    )
    assert result.ledger.position_quantity("600519.XSHG") == Decimal("0")
    assert result.ledger.receivables == Decimal("0")
    assert result.ledger.payables == Decimal("0")
    assert all(order_record["intent"]["source"].startswith("golden_") for order_record in result.order_records)


def test_backtest_golden_fixture_stays_inside_offline_validation_boundary() -> None:
    source = Path("src/serenity_alpha_lab/quant/backtest/golden.py").read_text()
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
            imported_modules.add(node.module)

    assert not {"qlib", "pyqlib", "fastapi", "celery", "redis", "sqlalchemy", "litellm"}.intersection(imported_roots)
    assert all(
        not module.startswith(("api.", "bot.", "data_provider", "src.services.llm", "src.services.stock"))
        for module in imported_modules
    )
