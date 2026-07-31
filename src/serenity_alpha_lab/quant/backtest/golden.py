from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.datasets.corporate_actions import CorporateAction, CorporateActionType
from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.corporate_actions import CorporateActionLedgerProcessor
from serenity_alpha_lab.quant.backtest.costs import CostBreakdown, CostModel
from serenity_alpha_lab.quant.backtest.execution import (
    AShareExecutionModel,
    AShareExecutionResult,
    AShareMarketSnapshot,
    ASharePositionAvailability,
)
from serenity_alpha_lab.quant.backtest.ledger import PortfolioLedger
from serenity_alpha_lab.quant.backtest.metrics import (
    BacktestEquityPoint,
    BacktestMetricFrequency,
    BacktestPerformanceMetricCalculator,
    BacktestPerformanceMetricPolicy,
    BacktestPerformanceMetricReport,
    BacktestTradeOutcome,
    BacktestTurnoverObservation,
)
from serenity_alpha_lab.quant.backtest.orders import (
    Order,
    OrderIntent,
    OrderSide,
    OrderType,
    TimeInForce,
)
from serenity_alpha_lab.quant.backtest.spec import (
    BacktestCostSpec,
    BacktestDatasetSpec,
    BacktestExecutionSpec,
    BacktestRiskSpec,
    BacktestSpec,
    BacktestStrategySpec,
    BacktestUniverseSpec,
)


BACKTEST_GOLDEN_FIXTURE_CONTRACT_VERSION = "quant.backtest_golden_fixture@1.0.0"
BACKTEST_GOLDEN_FIXTURE_SCHEMA_NAME = "quant.backtest.golden_fixture"
BACKTEST_GOLDEN_FIXTURE_SCHEMA_VERSION = "1.0.0"
BACKTEST_GOLDEN_RUNNER_VERSION = "cn_a_share_backtest_golden_runner@1.0.0"
BACKTEST_GOLDEN_SCOPE = "formal_portfolio_backtest_golden_fixture"

_FIXTURE_ID = "btg_cn_a_share_hand_computable_v1"
_RUN_ID = "run-backtest-golden-fixture"
_STAGE_ID = "stage-backtest-golden-fixture"
_TRACE_ID = "trace-backtest-golden-fixture"
_SPEC_ID = "formal_cn_backtest_golden_v1"
_SCREEN_DEFINITION_VERSION = "sdv_" + "1" * 32
_SCREEN_SNAPSHOT_ID = "ssn_" + "2" * 32
_FACTOR_VERSION = "fdv_" + "3" * 32
_CODE_HASH = "sha256:" + "8" * 64
_DATASET_VERSION_RE = re.compile(r"^dsv_[0-9a-f]{32,64}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_MONEY_QUANT = Decimal("0.001")


class BacktestGoldenFixtureError(ValueError):
    """Raised when a backtest golden fixture or run violates the validation contract."""


class BacktestGoldenOrderRole(StrEnum):
    INITIAL_BUY = "initial_buy"
    T_PLUS_ONE_PROBE = "t_plus_one_probe"
    SUSPENDED_BUY = "suspended_buy"
    LIMIT_UP_BUY = "limit_up_buy"
    FINAL_SELL = "final_sell"


@dataclass(frozen=True, slots=True)
class BacktestGoldenBar:
    instrument_id: InstrumentId
    trade_date: date
    open: Decimal | int | str
    high: Decimal | int | str
    low: Decimal | int | str
    close: Decimal | int | str
    volume: Decimal | int | str
    is_trading: bool
    is_suspended: bool
    limit_up_price: Decimal | int | str
    limit_down_price: Decimal | int | str
    source_dataset_version: str

    def __post_init__(self) -> None:
        if type(self.instrument_id) is not InstrumentId:
            raise BacktestGoldenFixtureError("instrument_id must be an InstrumentId")
        _require_date("trade_date", self.trade_date)
        object.__setattr__(self, "open", _decimal_min("open", self.open, Decimal("0"), exclusive=True))
        object.__setattr__(self, "high", _decimal_min("high", self.high, Decimal("0"), exclusive=True))
        object.__setattr__(self, "low", _decimal_min("low", self.low, Decimal("0"), exclusive=True))
        object.__setattr__(self, "close", _decimal_min("close", self.close, Decimal("0"), exclusive=True))
        object.__setattr__(self, "volume", _decimal_min("volume", self.volume, Decimal("0"), exclusive=True))
        if type(self.is_trading) is not bool:
            raise BacktestGoldenFixtureError("is_trading must be a bool")
        if type(self.is_suspended) is not bool:
            raise BacktestGoldenFixtureError("is_suspended must be a bool")
        object.__setattr__(
            self,
            "limit_up_price",
            _decimal_min("limit_up_price", self.limit_up_price, Decimal("0"), exclusive=True),
        )
        object.__setattr__(
            self,
            "limit_down_price",
            _decimal_min("limit_down_price", self.limit_down_price, Decimal("0"), exclusive=True),
        )
        if self.limit_down_price > self.limit_up_price:
            raise BacktestGoldenFixtureError("limit_down_price cannot exceed limit_up_price")
        object.__setattr__(
            self,
            "source_dataset_version",
            _validate_dataset_version("source_dataset_version", self.source_dataset_version),
        )

    def to_market_snapshot(self) -> AShareMarketSnapshot:
        return AShareMarketSnapshot(
            instrument_id=self.instrument_id,
            trade_date=self.trade_date,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            is_trading=self.is_trading,
            is_suspended=self.is_suspended,
            limit_up_price=self.limit_up_price,
            limit_down_price=self.limit_down_price,
            source_dataset_version=self.source_dataset_version,
            metadata={"fixture_id": _FIXTURE_ID},
        )

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id.canonical,
            "trade_date": self.trade_date.isoformat(),
            "open": _decimal_to_string(self.open),
            "high": _decimal_to_string(self.high),
            "low": _decimal_to_string(self.low),
            "close": _decimal_to_string(self.close),
            "volume": _decimal_to_string(self.volume),
            "is_trading": self.is_trading,
            "is_suspended": self.is_suspended,
            "limit_up_price": _decimal_to_string(self.limit_up_price),
            "limit_down_price": _decimal_to_string(self.limit_down_price),
            "source_dataset_version": self.source_dataset_version,
        }


@dataclass(frozen=True, slots=True)
class BacktestGoldenFixture:
    fixture_id: str
    spec: BacktestSpec
    instruments: tuple[InstrumentId, ...]
    trading_days: tuple[date, ...]
    bars: tuple[BacktestGoldenBar, ...]
    covered_rules: tuple[str, ...]
    contract_version: str = BACKTEST_GOLDEN_FIXTURE_CONTRACT_VERSION
    schema_name: str = BACKTEST_GOLDEN_FIXTURE_SCHEMA_NAME
    schema_version: str = BACKTEST_GOLDEN_FIXTURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "fixture_id", _required_string("fixture_id", self.fixture_id))
        if type(self.spec) is not BacktestSpec:
            raise BacktestGoldenFixtureError("spec must be a BacktestSpec")
        instruments = tuple(self.instruments)
        if len(instruments) != 3:
            raise BacktestGoldenFixtureError("golden fixture must contain exactly 3 instruments")
        if len({instrument.canonical for instrument in instruments}) != len(instruments):
            raise BacktestGoldenFixtureError("golden fixture instruments must be unique")
        object.__setattr__(self, "instruments", instruments)
        trading_days = tuple(self.trading_days)
        if len(trading_days) != 20:
            raise BacktestGoldenFixtureError("golden fixture must contain exactly 20 trading days")
        if tuple(sorted(trading_days)) != trading_days or len(set(trading_days)) != len(trading_days):
            raise BacktestGoldenFixtureError("golden fixture trading days must be unique and sorted")
        object.__setattr__(self, "trading_days", trading_days)
        bars = tuple(self.bars)
        if len(bars) != len(instruments) * len(trading_days):
            raise BacktestGoldenFixtureError("golden fixture must contain one bar per instrument per trading day")
        if len({(bar.instrument_id.canonical, bar.trade_date) for bar in bars}) != len(bars):
            raise BacktestGoldenFixtureError("golden fixture bars must be unique by instrument/date")
        object.__setattr__(self, "bars", tuple(sorted(bars, key=lambda bar: (bar.trade_date, bar.instrument_id.canonical))))
        object.__setattr__(self, "covered_rules", tuple(_required_string("covered_rule", rule) for rule in self.covered_rules))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    @property
    def summary(self) -> dict[str, object]:
        return {
            "fixture_id": self.fixture_id,
            "instrument_count": len(self.instruments),
            "trading_day_count": len(self.trading_days),
            "bar_count": len(self.bars),
            "chunked_read_supported": True,
            "production_backtest_promoted": False,
        }

    def read_bars(self, *, chunk_size: int | None = None) -> tuple[BacktestGoldenBar, ...]:
        if chunk_size is None:
            return self.bars
        return tuple(bar for chunk in self.iter_bar_chunks(chunk_size=chunk_size) for bar in chunk)

    def iter_bar_chunks(self, *, chunk_size: int) -> Iterable[tuple[BacktestGoldenBar, ...]]:
        if type(chunk_size) is not int or chunk_size <= 0:
            raise BacktestGoldenFixtureError("chunk_size must be positive")
        for start in range(0, len(self.bars), chunk_size):
            yield self.bars[start : start + chunk_size]

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "summary": self.summary,
            "covered_rules": list(self.covered_rules),
            "spec": self.spec.to_record(),
            "instruments": [instrument.canonical for instrument in self.instruments],
            "trading_days": [day.isoformat() for day in self.trading_days],
            "bars": [bar.to_record() for bar in self.bars],
        }


@dataclass(frozen=True, slots=True)
class BacktestGoldenResult:
    fixture: BacktestGoldenFixture
    ledger: PortfolioLedger
    orders: tuple[Order, ...]
    execution_results: tuple[AShareExecutionResult, ...]
    equity_curve: tuple[BacktestEquityPoint, ...]
    metrics_report: BacktestPerformanceMetricReport
    cost_breakdowns: tuple[CostBreakdown, ...]
    contract_version: str = BACKTEST_GOLDEN_FIXTURE_CONTRACT_VERSION
    schema_name: str = BACKTEST_GOLDEN_FIXTURE_SCHEMA_NAME
    schema_version: str = BACKTEST_GOLDEN_FIXTURE_SCHEMA_VERSION
    runner_version: str = BACKTEST_GOLDEN_RUNNER_VERSION
    scope: str = BACKTEST_GOLDEN_SCOPE

    def __post_init__(self) -> None:
        if type(self.fixture) is not BacktestGoldenFixture:
            raise BacktestGoldenFixtureError("fixture must be a BacktestGoldenFixture")
        if type(self.ledger) is not PortfolioLedger:
            raise BacktestGoldenFixtureError("ledger must be a PortfolioLedger")
        object.__setattr__(self, "orders", tuple(self.orders))
        object.__setattr__(self, "execution_results", tuple(self.execution_results))
        object.__setattr__(self, "equity_curve", tuple(self.equity_curve))
        object.__setattr__(self, "cost_breakdowns", tuple(self.cost_breakdowns))
        if type(self.metrics_report) is not BacktestPerformanceMetricReport:
            raise BacktestGoldenFixtureError("metrics_report must be a BacktestPerformanceMetricReport")
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "runner_version", _required_string("runner_version", self.runner_version))
        object.__setattr__(self, "scope", _required_string("scope", self.scope))

    @property
    def fixture_summary(self) -> dict[str, object]:
        return self.fixture.summary

    @property
    def covered_rules(self) -> tuple[str, ...]:
        return self.fixture.covered_rules

    @property
    def order_statuses(self) -> dict[str, str]:
        return {order.order_id: order.status.value for order in self.orders}

    @property
    def order_records(self) -> tuple[dict[str, object], ...]:
        return tuple(order.to_record() for order in self.orders)

    @property
    def execution_count(self) -> int:
        return len([result for result in self.execution_results if result.fill_event is not None])

    @property
    def corporate_action_count(self) -> int:
        return len(self.ledger.corporate_actions)

    @property
    def final_cash(self) -> Decimal:
        return _money(self.ledger.cash_balance)

    @property
    def final_equity(self) -> Decimal:
        return _money(self.ledger.equity)

    @property
    def total_transaction_cost(self) -> Decimal:
        return _money(sum((cost.total_cost for cost in self.cost_breakdowns), Decimal("0")))

    @property
    def realized_pnl(self) -> Decimal:
        return _money(
            sum((execution.realized_pnl or Decimal("0") for execution in self.ledger.executions), Decimal("0"))
        )

    @property
    def result_hash(self) -> str:
        return f"sha256:{hashlib.sha256(_canonical_json(self._hash_payload()).encode('utf-8')).hexdigest()}"

    def to_record(self) -> dict[str, object]:
        record = self._hash_payload()
        record["result_hash"] = self.result_hash
        return record

    def _hash_payload(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "runner_version": self.runner_version,
            "scope": self.scope,
            "production_backtest_promoted": False,
            "fixture_summary": self.fixture_summary,
            "covered_rules": list(self.covered_rules),
            "order_statuses": self.order_statuses,
            "orders": list(self.order_records),
            "execution_results": [result.to_record() for result in self.execution_results],
            "execution_count": self.execution_count,
            "corporate_action_count": self.corporate_action_count,
            "ledger": self.ledger.to_record(),
            "equity_curve": [point.to_record() for point in self.equity_curve],
            "metrics": self.metrics_report.to_record(),
            "final_cash": _decimal_to_string(self.final_cash),
            "final_equity": _decimal_to_string(self.final_equity),
            "total_transaction_cost": _decimal_to_string(self.total_transaction_cost),
            "realized_pnl": _decimal_to_string(self.realized_pnl),
        }


class BacktestGoldenRunner:
    def __init__(self, fixture: BacktestGoldenFixture) -> None:
        if type(fixture) is not BacktestGoldenFixture:
            raise BacktestGoldenFixtureError("fixture must be a BacktestGoldenFixture")
        self.fixture = fixture

    def run(self, *, chunk_size: int | None = None) -> BacktestGoldenResult:
        bars = self.fixture.read_bars(chunk_size=chunk_size)
        if bars != self.fixture.bars:
            raise BacktestGoldenFixtureError("chunked fixture read changed bar ordering or contents")
        bar_by_key = {(bar.instrument_id.canonical, bar.trade_date): bar for bar in bars}
        spec = self.fixture.spec
        ledger = PortfolioLedger.open(
            run_id=_RUN_ID,
            stage_id=_STAGE_ID,
            spec_id=spec.spec_id,
            spec_hash=spec.spec_hash,
            base_currency=spec.currency,
            initial_cash=spec.initial_capital,
            event_id="golden-ledger-initial-cash",
            occurred_at=_at_open(self.fixture.trading_days[0]),
        )
        execution_model = AShareExecutionModel(
            spec_hash=spec.spec_hash,
            execution_spec=spec.execution,
            cost_model=CostModel(spec_hash=spec.spec_hash, cost_spec=spec.costs),
        )
        corporate_action_processor = CorporateActionLedgerProcessor()
        execution_results: list[AShareExecutionResult] = []
        orders: list[Order] = []
        cost_breakdowns: list[CostBreakdown] = []
        equity_curve: list[BacktestEquityPoint] = []

        for trade_day in self.fixture.trading_days:
            if trade_day == date(2026, 1, 6):
                buy_result = self._execute_order(
                    execution_model=execution_model,
                    bar=bar_by_key[("600519.XSHG", trade_day)],
                    order_id="ord-golden-buy-600519",
                    side=OrderSide.BUY,
                    quantity=Decimal("100"),
                    signal_day=date(2026, 1, 5),
                    event_id_prefix="golden-buy-600519",
                    source="golden_initial_rebalance",
                )
                execution_results.append(buy_result)
                orders.append(buy_result.order)
                assert buy_result.fill_event is not None
                assert buy_result.cost_breakdown is not None
                cost_breakdowns.append(buy_result.cost_breakdown)
                ledger = ledger.record_execution(
                    order=buy_result.order,
                    fill_event=buy_result.fill_event,
                    event_id="golden-ledger-buy-600519",
                    occurred_at=_at_open(trade_day),
                    trade_date=trade_day,
                    settlement_date=date(2026, 1, 7),
                    transaction_cost=buy_result.cost_breakdown.total_cost,
                )

                t_plus_one_result = self._execute_order(
                    execution_model=execution_model,
                    bar=bar_by_key[("600519.XSHG", trade_day)],
                    order_id="ord-golden-tplus-one-sell-600519",
                    side=OrderSide.SELL,
                    quantity=Decimal("100"),
                    signal_day=date(2026, 1, 5),
                    event_id_prefix="golden-tplus-one-sell-600519",
                    source="golden_t_plus_one_probe",
                    position_availability=ASharePositionAvailability(
                        instrument_id=InstrumentId.parse("600519.XSHG"),
                        trade_date=trade_day,
                        total_quantity=Decimal("100"),
                        sellable_quantity=Decimal("0"),
                        locked_t_plus_one_quantity=Decimal("100"),
                    ),
                )
                execution_results.append(t_plus_one_result)
                orders.append(t_plus_one_result.order)

            if trade_day == date(2026, 1, 7):
                ledger = ledger.settle_payable(
                    event_id="golden-settle-buy-600519",
                    occurred_at=_at_open(trade_day),
                    settlement_date=trade_day,
                    amount=ledger.payables,
                    source_execution_id="golden-buy-600519-fill",
                )

            if trade_day == date(2026, 1, 8):
                suspended_result = self._execute_order(
                    execution_model=execution_model,
                    bar=bar_by_key[("000001.XSHE", trade_day)],
                    order_id="ord-golden-suspended-buy-000001",
                    side=OrderSide.BUY,
                    quantity=Decimal("100"),
                    signal_day=date(2026, 1, 7),
                    event_id_prefix="golden-suspended-buy-000001",
                    source="golden_suspension_probe",
                )
                execution_results.append(suspended_result)
                orders.append(suspended_result.order)

            if trade_day == date(2026, 1, 9):
                limit_result = self._execute_order(
                    execution_model=execution_model,
                    bar=bar_by_key[("300750.XSHE", trade_day)],
                    order_id="ord-golden-limit-up-buy-300750",
                    side=OrderSide.BUY,
                    quantity=Decimal("100"),
                    signal_day=date(2026, 1, 8),
                    event_id_prefix="golden-limit-up-buy-300750",
                    source="golden_limit_up_probe",
                )
                execution_results.append(limit_result)
                orders.append(limit_result.order)

            if trade_day == date(2026, 1, 12):
                ledger = corporate_action_processor.apply(
                    ledger,
                    _cash_dividend_action(),
                    event_id="golden-cash-dividend-600519",
                    occurred_at=_at_open(trade_day),
                    settlement_date=date(2026, 1, 13),
                )

            if trade_day == date(2026, 1, 13):
                ledger = ledger.settle_receivable(
                    event_id="golden-settle-cash-dividend-600519",
                    occurred_at=_at_open(trade_day),
                    settlement_date=trade_day,
                    amount=ledger.receivables,
                    source_execution_id=ledger.corporate_actions[-1].corporate_action_id,
                )

            if trade_day == date(2026, 1, 16):
                sell_result = self._execute_order(
                    execution_model=execution_model,
                    bar=bar_by_key[("600519.XSHG", trade_day)],
                    order_id="ord-golden-sell-600519",
                    side=OrderSide.SELL,
                    quantity=Decimal("100"),
                    signal_day=date(2026, 1, 15),
                    event_id_prefix="golden-sell-600519",
                    source="golden_final_rebalance",
                    position_availability=ASharePositionAvailability(
                        instrument_id=InstrumentId.parse("600519.XSHG"),
                        trade_date=trade_day,
                        total_quantity=Decimal("100"),
                        sellable_quantity=Decimal("100"),
                        locked_t_plus_one_quantity=Decimal("0"),
                    ),
                )
                execution_results.append(sell_result)
                orders.append(sell_result.order)
                assert sell_result.fill_event is not None
                assert sell_result.cost_breakdown is not None
                cost_breakdowns.append(sell_result.cost_breakdown)
                ledger = ledger.record_execution(
                    order=sell_result.order,
                    fill_event=sell_result.fill_event,
                    event_id="golden-ledger-sell-600519",
                    occurred_at=_at_open(trade_day),
                    trade_date=trade_day,
                    settlement_date=date(2026, 1, 19),
                    transaction_cost=sell_result.cost_breakdown.total_cost,
                )

            if trade_day == date(2026, 1, 19):
                ledger = ledger.settle_receivable(
                    event_id="golden-settle-sell-600519",
                    occurred_at=_at_open(trade_day),
                    settlement_date=trade_day,
                    amount=ledger.receivables,
                    source_execution_id="golden-sell-600519-fill",
                )

            prices = _position_prices(ledger=ledger, trade_day=trade_day, bar_by_key=bar_by_key)
            if prices:
                ledger = ledger.mark_to_market(
                    event_id=f"golden-mark-to-market-{trade_day.isoformat()}",
                    occurred_at=_at_close(trade_day),
                    valuation_date=trade_day,
                    prices=prices,
                )
            equity_curve.append(BacktestEquityPoint(trade_day, _money(ledger.equity)))

        metrics_report = BacktestPerformanceMetricCalculator(
            spec=spec,
            policy=BacktestPerformanceMetricPolicy(
                policy_id="cn_a_share_backtest_golden_metrics",
                policy_version="1.0.0",
                frequency=BacktestMetricFrequency.DAILY,
                annualization_days=252,
                risk_free_rate=Decimal("0.0000"),
            ),
        ).calculate(
            run_id=_RUN_ID,
            stage_id="stage-backtest-golden-metrics",
            equity_curve=tuple(equity_curve),
            turnover_observations=(
                BacktestTurnoverObservation(date(2026, 1, 6), Decimal("1000"), Decimal("0"), Decimal("10000")),
                BacktestTurnoverObservation(date(2026, 1, 16), Decimal("0"), Decimal("1200"), Decimal("10246.600")),
            ),
            trade_outcomes=(
                BacktestTradeOutcome(
                    trade_id="trade-golden-600519",
                    instrument_id=InstrumentId.parse("600519.XSHG"),
                    realized_pnl=_money(
                        sum(
                            (execution.realized_pnl or Decimal("0") for execution in ledger.executions),
                            Decimal("0"),
                        )
                    ),
                ),
            ),
            cost_breakdowns=tuple(cost_breakdowns),
        )
        return BacktestGoldenResult(
            fixture=self.fixture,
            ledger=ledger,
            orders=tuple(orders),
            execution_results=tuple(execution_results),
            equity_curve=tuple(equity_curve),
            metrics_report=metrics_report,
            cost_breakdowns=tuple(cost_breakdowns),
        )

    def _execute_order(
        self,
        *,
        execution_model: AShareExecutionModel,
        bar: BacktestGoldenBar,
        order_id: str,
        side: OrderSide,
        quantity: Decimal,
        signal_day: date,
        event_id_prefix: str,
        source: str,
        position_availability: ASharePositionAvailability | None = None,
    ) -> AShareExecutionResult:
        order = Order.create(
            intent=OrderIntent(
                order_id=order_id,
                run_id=_RUN_ID,
                stage_id=_STAGE_ID,
                spec_id=self.fixture.spec.spec_id,
                spec_hash=self.fixture.spec.spec_hash,
                instrument_id=bar.instrument_id,
                side=side,
                order_type=OrderType.MARKET,
                target_quantity=quantity,
                trade_date=bar.trade_date,
                signal_time=_at_close(signal_day),
                created_at=_at_open(bar.trade_date),
                time_in_force=TimeInForce.DAY,
                source=source,
            ),
            event_id=f"evt-created-{order_id}",
            occurred_at=_at_open(bar.trade_date),
        )
        return execution_model.execute(
            order=order,
            market_snapshot=bar.to_market_snapshot(),
            occurred_at=_at_open(bar.trade_date),
            event_id_prefix=event_id_prefix,
            position_availability=position_availability,
        )


def default_backtest_golden_fixture() -> BacktestGoldenFixture:
    instruments = (
        InstrumentId.parse("600519.XSHG"),
        InstrumentId.parse("000001.XSHE"),
        InstrumentId.parse("300750.XSHE"),
    )
    trading_days = _trading_days()
    bars = tuple(
        _bar(instrument=instrument, trade_day=trade_day)
        for trade_day in trading_days
        for instrument in instruments
    )
    return BacktestGoldenFixture(
        fixture_id=_FIXTURE_ID,
        spec=_formal_backtest_spec(start_date=trading_days[0], end_date=trading_days[-1]),
        instruments=instruments,
        trading_days=trading_days,
        bars=bars,
        covered_rules=(
            "fees",
            "t_plus_one",
            "suspension",
            "limit_up_down",
            "cash_dividend",
            "rebalance",
            "chunked_vs_full_read",
        ),
    )


def _formal_backtest_spec(*, start_date: date, end_date: date) -> BacktestSpec:
    dataset_versions = {
        "adjusted_daily_bars": "dsv_" + "a" * 32,
        "raw_daily_bars": "dsv_" + "b" * 32,
        "trading_calendar": "dsv_" + "c" * 32,
        "corporate_actions": "dsv_" + "d" * 32,
        "instrument_master": "dsv_" + "e" * 32,
    }
    dataset_hashes = {name: f"sha256:{index:064x}" for index, name in enumerate(sorted(dataset_versions), start=1)}
    return BacktestSpec(
        spec_id=_SPEC_ID,
        created_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
        created_by_run_id=_RUN_ID,
        dataset=BacktestDatasetSpec(dataset_versions=dataset_versions, dataset_hashes=dataset_hashes),
        universe=BacktestUniverseSpec(
            universe_version_id="dsv_" + "f" * 32,
            universe_name="cn_a_share_golden_three_name",
            as_of=start_date,
            membership_policy="pit_membership_as_of_decision_time",
        ),
        strategy=BacktestStrategySpec(
            strategy_id="cn_a_share_golden_rebalance",
            strategy_version="1.0.0",
            strategy_kind="screen_snapshot_rebalance",
            source_commit="sal-p4-019-golden",
            code_hash=_CODE_HASH,
            screen_definition_version_id=_SCREEN_DEFINITION_VERSION,
            screen_snapshot_id=_SCREEN_SNAPSHOT_ID,
            factor_version_ids=(_FACTOR_VERSION,),
        ),
        start_date=start_date,
        end_date=end_date,
        benchmark="000300.XSHG",
        currency="CNY",
        initial_capital=Decimal("10000.000"),
        cash_rate_bps=Decimal("0"),
        execution=BacktestExecutionSpec(
            signal_timing="after_close",
            execution_timing="next_open",
            signal_price_field="close",
            execution_price_field="open",
            rebalance_calendar="cn_a_share_trading_calendar",
            valuation_calendar="cn_a_share_trading_calendar",
            rebalance_frequency="daily",
            settlement_lag_days=1,
            lot_size=100,
            random_seed=20260726,
        ),
        costs=BacktestCostSpec(
            commission_bps=Decimal("10.0"),
            min_commission=Decimal("0"),
            stamp_tax_bps=Decimal("10.0"),
            transfer_fee_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
            impact_bps=Decimal("0"),
            max_participation_rate=Decimal("0.1000"),
        ),
        risk=BacktestRiskSpec(
            risk_policy_version="risk_policy.cn_a_share_golden@1.0.0",
            max_weight_per_instrument=Decimal("0.5000"),
            max_weight_per_industry=Decimal("0.8000"),
            max_turnover_per_rebalance=Decimal("1.0000"),
            cash_buffer_pct=Decimal("0.0000"),
            liquidity_floor_amount=Decimal("0"),
        ),
        artifact_output_level="full_audit",
    )


def _trading_days() -> tuple[date, ...]:
    days: list[date] = []
    current = date(2026, 1, 5)
    while len(days) < 20:
        if current.weekday() < 5:
            days.append(current)
        current = current + timedelta(days=1)
    return tuple(days)


def _bar(*, instrument: InstrumentId, trade_day: date) -> BacktestGoldenBar:
    if instrument.canonical == "600519.XSHG":
        price = Decimal("10")
        if trade_day == date(2026, 1, 12):
            price = Decimal("9.5")
        elif trade_day >= date(2026, 1, 16):
            price = Decimal("12")
        return _make_bar(instrument=instrument, trade_day=trade_day, price=price)
    if instrument.canonical == "000001.XSHE":
        return _make_bar(
            instrument=instrument,
            trade_day=trade_day,
            price=Decimal("20"),
            is_trading=trade_day != date(2026, 1, 8),
            is_suspended=trade_day == date(2026, 1, 8),
        )
    if instrument.canonical == "300750.XSHE" and trade_day == date(2026, 1, 9):
        return _make_bar(instrument=instrument, trade_day=trade_day, price=Decimal("11"), limit_up_price=Decimal("11"))
    return _make_bar(instrument=instrument, trade_day=trade_day, price=Decimal("10"))


def _make_bar(
    *,
    instrument: InstrumentId,
    trade_day: date,
    price: Decimal,
    is_trading: bool = True,
    is_suspended: bool = False,
    limit_up_price: Decimal | None = None,
) -> BacktestGoldenBar:
    return BacktestGoldenBar(
        instrument_id=instrument,
        trade_date=trade_day,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Decimal("2000"),
        is_trading=is_trading,
        is_suspended=is_suspended,
        limit_up_price=limit_up_price or price * Decimal("1.10"),
        limit_down_price=price * Decimal("0.90"),
        source_dataset_version="dsv_" + "a" * 32,
    )


def _cash_dividend_action() -> CorporateAction:
    return CorporateAction(
        instrument_id=InstrumentId.parse("600519.XSHG"),
        ex_date=date(2026, 1, 12),
        action_type=CorporateActionType.CASH_DIVIDEND,
        provider_id="golden_fixture_provider",
        provider_source="hand_computable_backtest_golden",
        provider_source_timestamp=_at_open(date(2026, 1, 12)),
        provider_raw_response_sha256="a" * 64,
        field_lineage={"cash_dividend_per_share": "golden_fixture.cash_dividend_per_share"},
        source_bronze_artifact_id="bronze://golden-fixture/corporate-actions",
        cash_dividend_per_share=0.5,
        currency="CNY",
    )


def _position_prices(
    *,
    ledger: PortfolioLedger,
    trade_day: date,
    bar_by_key: Mapping[tuple[str, date], BacktestGoldenBar],
) -> Mapping[InstrumentId, Decimal]:
    prices: dict[InstrumentId, Decimal] = {}
    for lot in ledger.position_lots:
        bar = bar_by_key[(lot.instrument_id.canonical, trade_day)]
        prices[lot.instrument_id] = bar.close
    return prices


def _at_open(trade_day: date) -> datetime:
    return datetime(trade_day.year, trade_day.month, trade_day.day, 9, 30, tzinfo=UTC)


def _at_close(trade_day: date) -> datetime:
    return datetime(trade_day.year, trade_day.month, trade_day.day, 15, 0, tzinfo=UTC)


def _money(value: Decimal) -> Decimal:
    return value.quantize(_MONEY_QUANT)


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise BacktestGoldenFixtureError(f"{field_name} is required")
    return value


def _validate_dataset_version(field_name: str, value: object) -> str:
    version = _required_string(field_name, value)
    if version.lower() == "latest" or not _DATASET_VERSION_RE.fullmatch(version):
        raise BacktestGoldenFixtureError(f"{field_name} must be a concrete Dataset Version id")
    return version


def _validate_sha256(field_name: str, value: object) -> str:
    digest = _required_string(field_name, value)
    if not _SHA256_RE.fullmatch(digest):
        raise BacktestGoldenFixtureError(f"{field_name} must match sha256:<64 lowercase hex chars>")
    return digest


def _decimal_value(field_name: str, value: object) -> Decimal:
    if isinstance(value, bool):
        raise BacktestGoldenFixtureError(f"{field_name} must be a decimal value")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BacktestGoldenFixtureError(f"{field_name} must be a decimal value") from exc
    if not decimal.is_finite():
        raise BacktestGoldenFixtureError(f"{field_name} must be finite")
    return decimal


def _decimal_min(
    field_name: str,
    value: object,
    minimum: Decimal,
    *,
    exclusive: bool = False,
) -> Decimal:
    decimal = _decimal_value(field_name, value)
    if exclusive:
        if decimal <= minimum:
            raise BacktestGoldenFixtureError(f"{field_name} must be greater than {minimum}")
    elif decimal < minimum:
        raise BacktestGoldenFixtureError(f"{field_name} cannot be less than {minimum}")
    return decimal


def _decimal_to_string(value: Decimal) -> str:
    return format(value, "f")


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise BacktestGoldenFixtureError(f"{field_name} must be a date")
