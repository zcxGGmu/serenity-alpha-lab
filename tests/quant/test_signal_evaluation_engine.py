from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from serenity_alpha_lab.quant.signal_evaluation import (
    SIGNAL_EVALUATION_ENGINE_VERSION,
    SIGNAL_EVALUATION_TYPE,
    SignalEvaluationConfig,
    SignalEvaluationEngine,
)


ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = ROOT / "docs" / "baselines" / "dsa-v3.26.1" / "signal-evaluation-characterization"


@dataclass(frozen=True, slots=True)
class DailyBar:
    date: date
    high: float | None
    low: float | None
    close: float | None


def test_signal_evaluation_engine_matches_p4_001_text_signal_goldens() -> None:
    inputs = _load_json("inputs.json")["engine_cases"]
    expected_items = _load_json("engine-evaluations.json")["items"]
    config = _config()

    actual_items: list[dict[str, Any]] = []
    summary_rows: list[SimpleNamespace] = []
    for item in inputs:
        evaluation = SignalEvaluationEngine.evaluate_single(
            operation_advice=item["operation_advice"],
            analysis_date=date.fromisoformat(item["analysis_date"]),
            start_price=float(item["start_price"]),
            forward_bars=_bars(item["bars"]),
            stop_loss=item["stop_loss"],
            take_profit=item["take_profit"],
            config=config,
        )
        actual_items.append({"case": item["case"], **_normalize(evaluation)})
        summary_rows.append(_result_namespace(evaluation))

    assert actual_items == expected_items

    summary = SignalEvaluationEngine.compute_summary(
        results=summary_rows,
        scope="overall",
        code="__overall__",
        eval_window_days=config.eval_window_days,
        engine_version=config.engine_version,
    )
    assert _normalize(summary) == _load_json("signal-evaluation-summary.json")


def test_signal_evaluation_engine_matches_p4_001_structured_signal_goldens() -> None:
    inputs = _load_json("inputs.json")["decision_signal_cases"]
    expected_items = _load_json("decision-signal-evaluations.json")["items"]
    config = _config()

    actual_items = [
        {
            "case": item["case"],
            **_normalize(
                SignalEvaluationEngine.evaluate_decision_signal(
                    direction_expected=item["direction_expected"],
                    anchor_date=date.fromisoformat(item["anchor_date"]),
                    start_price=float(item["start_price"]),
                    forward_bars=_bars(item["bars"]),
                    config=config,
                )
            ),
        }
        for item in inputs
    ]

    assert actual_items == expected_items


def test_signal_evaluation_engine_declares_signal_semantics_not_formal_backtest() -> None:
    config = _config()

    assert config.evaluation_type == SIGNAL_EVALUATION_TYPE == "signal"
    assert config.engine_version == SIGNAL_EVALUATION_ENGINE_VERSION
    assert SignalEvaluationEngine.semantic_scope == "legacy_signal_evaluation"
    assert SignalEvaluationEngine.evaluation_type == "signal"
    assert "portfolio" not in (SignalEvaluationEngine.__doc__ or "").lower()


def _config() -> SignalEvaluationConfig:
    return SignalEvaluationConfig(eval_window_days=3, neutral_band_pct=2.0)


def _load_json(name: str) -> Any:
    return json.loads((BASELINE_DIR / name).read_text(encoding="utf-8"))


def _bars(rows: list[dict[str, Any]]) -> list[DailyBar]:
    return [
        DailyBar(
            date=date.fromisoformat(row["date"]),
            high=row["high"],
            low=row["low"],
            close=row["close"],
        )
        for row in rows
    ]


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    return value


def _result_namespace(payload: dict[str, Any]) -> SimpleNamespace:
    fields = [
        "eval_status",
        "position_recommendation",
        "outcome",
        "direction_correct",
        "stock_return_pct",
        "simulated_return_pct",
        "hit_stop_loss",
        "hit_take_profit",
        "first_hit",
        "first_hit_trading_days",
        "operation_advice",
    ]
    return SimpleNamespace(**{field: payload.get(field) for field in fields})
