from __future__ import annotations

import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol


OVERALL_SENTINEL_CODE = "__overall__"
SIGNAL_EVALUATION_ENGINE_VERSION = "v1"
SIGNAL_EVALUATION_TYPE = "signal"
SIGNAL_EVALUATION_SEMANTIC_SCOPE = "legacy_signal_evaluation"
SIGNAL_EVALUATION_CONTRACT_VERSION = "signal_evaluation@1.0.0"


class DailyBarLike(Protocol):
    date: date
    high: float | None
    low: float | None
    close: float | None


class SignalResultLike(Protocol):
    eval_status: str
    position_recommendation: str | None
    outcome: str | None
    direction_correct: bool | None
    stock_return_pct: float | None
    simulated_return_pct: float | None
    hit_stop_loss: bool | None
    hit_take_profit: bool | None
    first_hit: str | None
    first_hit_trading_days: int | None
    operation_advice: str | None


@dataclass(frozen=True, slots=True)
class SignalEvaluationConfig:
    eval_window_days: int
    neutral_band_pct: float = 2.0
    engine_version: str = SIGNAL_EVALUATION_ENGINE_VERSION
    evaluation_type: str = SIGNAL_EVALUATION_TYPE

    def __post_init__(self) -> None:
        if type(self.eval_window_days) is not int or self.eval_window_days <= 0:
            raise ValueError("eval_window_days must be positive")
        object.__setattr__(self, "neutral_band_pct", float(self.neutral_band_pct))
        object.__setattr__(self, "engine_version", str(self.engine_version))
        object.__setattr__(self, "evaluation_type", str(self.evaluation_type))
        if self.evaluation_type != SIGNAL_EVALUATION_TYPE:
            raise ValueError("evaluation_type must be signal")


class SignalEvaluationEngine:
    """T+N signal evaluation engine for legacy DSA recommendation outcomes."""

    evaluation_type = SIGNAL_EVALUATION_TYPE
    semantic_scope = SIGNAL_EVALUATION_SEMANTIC_SCOPE
    contract_version = SIGNAL_EVALUATION_CONTRACT_VERSION

    _BULLISH_KEYWORDS = (
        "买入",
        "加仓",
        "强烈买入",
        "增持",
        "建仓",
        "strong buy",
        "buy",
        "add",
    )
    _BEARISH_KEYWORDS = (
        "卖出",
        "减仓",
        "强烈卖出",
        "清仓",
        "strong sell",
        "sell",
        "reduce",
    )
    _HOLD_KEYWORDS = (
        "持有",
        "震荡观望",
        "洗盘观察",
        "持有观察",
        "hold",
        "range-bound watch",
        "shakeout watch",
        "hold and watch",
    )
    _WAIT_KEYWORDS = (
        "观望",
        "等待",
        "wait",
    )
    _NEGATION_PATTERNS = (
        "not",
        "don't",
        "do not",
        "no",
        "never",
        "avoid",
        "不要",
        "不",
        "别",
        "勿",
        "没有",
    )
    _NEGATION_CONNECTOR_WORDS = (
        "建议",
        "应",
        "应当",
        "宜",
        "先",
        "再",
        "暂",
        "不必",
        "必须",
        "无需",
    )

    @classmethod
    def infer_direction_expected(cls, operation_advice: str | None) -> str:
        text = cls._normalize_text(operation_advice)
        if cls._matches_intent(text, cls._BEARISH_KEYWORDS):
            return "down"
        if cls._first_intent_position(text, cls._WAIT_KEYWORDS) is not None:
            wait_pos = cls._first_intent_position(text, cls._WAIT_KEYWORDS)
            bullish_pos = cls._first_intent_position(text, cls._BULLISH_KEYWORDS)
            hold_pos = cls._first_intent_position(text, cls._HOLD_KEYWORDS)
            if (bullish_pos is None or wait_pos < bullish_pos) and (
                hold_pos is None or wait_pos < hold_pos
            ):
                return "flat"
        if cls._matches_intent(text, cls._BULLISH_KEYWORDS):
            return "up"
        if cls._matches_intent(text, cls._HOLD_KEYWORDS):
            return "not_down"
        if cls._matches_intent(text, cls._WAIT_KEYWORDS):
            return "flat"
        return "flat"

    @classmethod
    def infer_position_recommendation(cls, operation_advice: str | None) -> str:
        text = cls._normalize_text(operation_advice)
        if cls._matches_intent(text, cls._BEARISH_KEYWORDS):
            return "cash"
        wait_pos = cls._first_intent_position(text, cls._WAIT_KEYWORDS)
        if wait_pos is not None:
            bullish_pos = cls._first_intent_position(text, cls._BULLISH_KEYWORDS)
            hold_pos = cls._first_intent_position(text, cls._HOLD_KEYWORDS)
            if (bullish_pos is None or wait_pos < bullish_pos) and (
                hold_pos is None or wait_pos < hold_pos
            ):
                return "cash"
        if cls._matches_intent(text, cls._BULLISH_KEYWORDS) or cls._matches_intent(text, cls._HOLD_KEYWORDS):
            return "long"
        if cls._matches_intent(text, cls._WAIT_KEYWORDS):
            return "cash"
        return "cash"

    @classmethod
    def evaluate_single(
        cls,
        *,
        operation_advice: str | None,
        analysis_date: date,
        start_price: float,
        forward_bars: Sequence[DailyBarLike],
        stop_loss: float | None,
        take_profit: float | None,
        config: SignalEvaluationConfig,
    ) -> dict[str, Any]:
        if start_price is None or start_price <= 0:
            return {
                "analysis_date": analysis_date,
                "operation_advice": operation_advice,
                "position_recommendation": cls.infer_position_recommendation(operation_advice),
                "direction_expected": cls.infer_direction_expected(operation_advice),
                "eval_status": "error",
            }

        eval_days = int(config.eval_window_days)
        if eval_days <= 0:
            raise ValueError("eval_window_days must be positive")

        if len(forward_bars) < eval_days:
            return {
                "analysis_date": analysis_date,
                "operation_advice": operation_advice,
                "position_recommendation": cls.infer_position_recommendation(operation_advice),
                "direction_expected": cls.infer_direction_expected(operation_advice),
                "eval_status": "insufficient_data",
                "eval_window_days": eval_days,
            }

        window_bars = list(forward_bars[:eval_days])
        end_close = window_bars[-1].close
        highs = [bar.high for bar in window_bars if bar.high is not None]
        lows = [bar.low for bar in window_bars if bar.low is not None]
        max_high = max(highs) if highs else None
        min_low = min(lows) if lows else None
        stock_return_pct = None if end_close is None else (end_close - start_price) / start_price * 100

        direction_expected = cls.infer_direction_expected(operation_advice)
        position = cls.infer_position_recommendation(operation_advice)
        outcome, direction_correct = cls._classify_outcome(
            stock_return_pct=stock_return_pct,
            direction_expected=direction_expected,
            neutral_band_pct=config.neutral_band_pct,
        )
        (
            hit_stop_loss,
            hit_take_profit,
            first_hit,
            first_hit_date,
            first_hit_days,
            simulated_exit_price,
            simulated_exit_reason,
        ) = cls._evaluate_targets(
            position=position,
            stop_loss=stop_loss,
            take_profit=take_profit,
            window_bars=window_bars,
            end_close=end_close,
        )

        simulated_entry_price = start_price if position == "long" else None
        if position != "long":
            simulated_return_pct = 0.0
        elif simulated_exit_price is None:
            simulated_return_pct = None
        else:
            simulated_return_pct = (simulated_exit_price - start_price) / start_price * 100

        return {
            "analysis_date": analysis_date,
            "eval_window_days": eval_days,
            "engine_version": config.engine_version,
            "eval_status": "completed",
            "operation_advice": operation_advice,
            "position_recommendation": position,
            "start_price": start_price,
            "end_close": end_close,
            "max_high": max_high,
            "min_low": min_low,
            "stock_return_pct": stock_return_pct,
            "direction_expected": direction_expected,
            "direction_correct": direction_correct,
            "outcome": outcome,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "hit_stop_loss": hit_stop_loss,
            "hit_take_profit": hit_take_profit,
            "first_hit": first_hit,
            "first_hit_date": first_hit_date,
            "first_hit_trading_days": first_hit_days,
            "simulated_entry_price": simulated_entry_price,
            "simulated_exit_price": simulated_exit_price,
            "simulated_exit_reason": simulated_exit_reason,
            "simulated_return_pct": simulated_return_pct,
        }

    @classmethod
    def evaluate_decision_signal(
        cls,
        *,
        direction_expected: str,
        anchor_date: date,
        start_price: float,
        forward_bars: Sequence[DailyBarLike],
        config: SignalEvaluationConfig,
    ) -> dict[str, Any]:
        start_price_value = cls._finite_optional_float(start_price)
        if start_price_value is None or start_price_value <= 0:
            return {
                "anchor_date": anchor_date,
                "direction_expected": direction_expected,
                "eval_status": "unable",
                "unable_reason": "invalid_anchor_price",
            }

        eval_days = int(config.eval_window_days)
        if eval_days <= 0:
            raise ValueError("eval_window_days must be positive")

        if len(forward_bars) < eval_days:
            return {
                "anchor_date": anchor_date,
                "eval_window_days": eval_days,
                "engine_version": config.engine_version,
                "direction_expected": direction_expected,
                "eval_status": "unable",
                "unable_reason": "insufficient_forward_bars",
            }

        window_bars = list(forward_bars[:eval_days])
        raw_end_close = window_bars[-1].close
        end_close = cls._finite_optional_float(raw_end_close)
        highs: list[float] = []
        lows: list[float] = []
        for bar in window_bars:
            high = cls._finite_optional_float(bar.high)
            low = cls._finite_optional_float(bar.low)
            if high is not None:
                highs.append(high)
            if low is not None:
                lows.append(low)
        max_high = max(highs) if highs else None
        min_low = min(lows) if lows else None
        stock_return_pct = (
            None if end_close is None else (end_close - start_price_value) / start_price_value * 100
        )
        outcome, direction_correct = cls._classify_signal_outcome(
            stock_return_pct=stock_return_pct,
            direction_expected=direction_expected,
            neutral_band_pct=config.neutral_band_pct,
        )

        if stock_return_pct is None:
            return {
                "anchor_date": anchor_date,
                "eval_window_days": eval_days,
                "engine_version": config.engine_version,
                "direction_expected": direction_expected,
                "eval_status": "unable",
                "unable_reason": "missing_end_close" if raw_end_close is None else "invalid_end_close",
                "start_price": start_price_value,
                "end_close": end_close,
                "max_high": max_high,
                "min_low": min_low,
            }

        return {
            "anchor_date": anchor_date,
            "eval_window_days": eval_days,
            "engine_version": config.engine_version,
            "eval_status": "completed",
            "direction_expected": direction_expected,
            "direction_correct": direction_correct,
            "outcome": outcome,
            "start_price": start_price_value,
            "end_close": end_close,
            "max_high": max_high,
            "min_low": min_low,
            "stock_return_pct": stock_return_pct,
        }

    @classmethod
    def compute_summary(
        cls,
        *,
        results: Iterable[SignalResultLike],
        scope: str,
        code: str | None,
        eval_window_days: int,
        engine_version: str,
    ) -> dict[str, Any]:
        results_list = list(results)
        total = len(results_list)
        completed = [row for row in results_list if (row.eval_status or "") == "completed"]
        insufficient_count = sum(1 for row in results_list if (row.eval_status or "") == "insufficient_data")
        long_count = sum(1 for row in completed if (row.position_recommendation or "") == "long")
        cash_count = sum(1 for row in completed if (row.position_recommendation or "") == "cash")
        win_count = sum(1 for row in completed if (row.outcome or "") == "win")
        loss_count = sum(1 for row in completed if (row.outcome or "") == "loss")
        neutral_count = sum(1 for row in completed if (row.outcome or "") == "neutral")
        direction_denominator = sum(1 for row in completed if row.direction_correct is not None)
        direction_numerator = sum(1 for row in completed if row.direction_correct is True)
        direction_accuracy_pct = (
            round(direction_numerator / direction_denominator * 100, 2) if direction_denominator else None
        )
        win_loss_denominator = win_count + loss_count
        win_rate_pct = round(win_count / win_loss_denominator * 100, 2) if win_loss_denominator else None
        neutral_rate_pct = round(neutral_count / len(completed) * 100, 2) if completed else None
        avg_stock_return_pct = cls._average([row.stock_return_pct for row in completed])
        avg_simulated_return_pct = cls._average([row.simulated_return_pct for row in completed])
        stop_applicable = [
            row
            for row in completed
            if (row.position_recommendation or "") == "long" and row.hit_stop_loss is not None
        ]
        stop_loss_trigger_rate = (
            round(sum(1 for row in stop_applicable if row.hit_stop_loss is True) / len(stop_applicable) * 100, 2)
            if stop_applicable
            else None
        )
        take_profit_applicable = [
            row
            for row in completed
            if (row.position_recommendation or "") == "long" and row.hit_take_profit is not None
        ]
        take_profit_trigger_rate = (
            round(
                sum(1 for row in take_profit_applicable if row.hit_take_profit is True)
                / len(take_profit_applicable)
                * 100,
                2,
            )
            if take_profit_applicable
            else None
        )
        any_target_applicable = [
            row
            for row in completed
            if (row.position_recommendation or "") == "long"
            and (row.hit_stop_loss is not None or row.hit_take_profit is not None)
        ]
        ambiguous_rate = (
            round(
                sum(1 for row in any_target_applicable if (row.first_hit or "") == "ambiguous")
                / len(any_target_applicable)
                * 100,
                2,
            )
            if any_target_applicable
            else None
        )
        avg_days_to_first_hit = cls._average(
            [
                float(row.first_hit_trading_days)
                for row in any_target_applicable
                if row.first_hit_trading_days is not None
                and (row.first_hit or "") in ("stop_loss", "take_profit", "ambiguous")
            ]
        )
        return {
            "scope": scope,
            "code": code,
            "eval_window_days": int(eval_window_days),
            "engine_version": engine_version,
            "total_evaluations": total,
            "completed_count": len(completed),
            "insufficient_count": insufficient_count,
            "long_count": long_count,
            "cash_count": cash_count,
            "win_count": win_count,
            "loss_count": loss_count,
            "neutral_count": neutral_count,
            "direction_accuracy_pct": direction_accuracy_pct,
            "win_rate_pct": win_rate_pct,
            "neutral_rate_pct": neutral_rate_pct,
            "avg_stock_return_pct": avg_stock_return_pct,
            "avg_simulated_return_pct": avg_simulated_return_pct,
            "stop_loss_trigger_rate": stop_loss_trigger_rate,
            "take_profit_trigger_rate": take_profit_trigger_rate,
            "ambiguous_rate": ambiguous_rate,
            "avg_days_to_first_hit": avg_days_to_first_hit,
            "advice_breakdown": cls._compute_advice_breakdown(completed),
            "diagnostics": cls._compute_diagnostics(results_list),
        }

    @staticmethod
    def _normalize_text(value: str | None) -> str:
        return str(value or "").strip().lower()

    @classmethod
    def _matches_intent(cls, text: str, keywords: Sequence[str]) -> bool:
        return cls._first_intent_position(text, keywords) is not None

    @classmethod
    def _first_intent_position(cls, text: str, keywords: Sequence[str]) -> int | None:
        if not text:
            return None
        best_pos: int | None = None
        for keyword_value in keywords:
            if not keyword_value:
                continue
            if text == keyword_value:
                return 0
            keyword = keyword_value.lower().strip()
            if not keyword:
                continue
            if bool(re.search(r"[a-z]", keyword)):
                for match in re.finditer(
                    rf"(?<![a-zA-Z0-9_]){re.escape(keyword)}(?![a-zA-Z0-9_])",
                    text,
                ):
                    if not cls._is_negated(text[: match.start()], keyword):
                        position = match.start()
                        if best_pos is None or position < best_pos:
                            best_pos = position
                            break
                    continue
            if re.search(r"[\u4e00-\u9fff]", keyword):
                start = 0
                while True:
                    match_idx = text.find(keyword, start)
                    if match_idx < 0:
                        break
                    if not cls._is_negated(text[:match_idx], keyword):
                        if best_pos is None or match_idx < best_pos:
                            best_pos = match_idx
                        break
                    start = match_idx + len(keyword)
                continue
        return best_pos

    @classmethod
    def _is_negated(cls, prefix: str, keyword: str) -> bool:
        stripped = prefix.rstrip()
        target = (keyword or "").lower().strip()
        if not target:
            return False
        if any(stripped.endswith(negation) for negation in cls._NEGATION_PATTERNS):
            return True
        lookback = stripped[-12:]
        for negation in cls._NEGATION_PATTERNS:
            if not negation:
                continue
            negation_index = lookback.rfind(negation)
            if negation_index < 0:
                continue
            suffix_gap = lookback[negation_index + len(negation):].strip()
            if not suffix_gap:
                return True
            if any(char in suffix_gap for char in "，,。；;:!?！？"):
                continue
            if cls._contains_keyword(suffix_gap, target):
                return True
            if not any("\u4e00" <= char <= "\u9fff" for char in suffix_gap):
                if len(suffix_gap) <= 6:
                    return True
                continue
            if cls._is_negation_connector_gap(suffix_gap):
                return True
        return False

    @classmethod
    def _contains_keyword(cls, text: str, keyword: str) -> bool:
        if not text or not keyword:
            return False
        if bool(re.search(r"[a-z]", keyword)):
            return bool(re.search(rf"(?<![a-zA-Z0-9_]){re.escape(keyword)}(?![a-zA-Z0-9_])", text))
        return keyword in text

    @classmethod
    def _is_negation_connector_gap(cls, gap: str) -> bool:
        compact = re.sub(r"[\s,，。；;:!?！？]", "", gap).strip()
        if not compact:
            return True
        return compact in cls._NEGATION_CONNECTOR_WORDS

    @classmethod
    def _classify_outcome(
        cls,
        *,
        stock_return_pct: float | None,
        direction_expected: str,
        neutral_band_pct: float,
    ) -> tuple[str | None, bool | None]:
        if stock_return_pct is None:
            return None, None
        band = abs(float(neutral_band_pct))
        stock_return = float(stock_return_pct)
        if direction_expected == "up":
            if stock_return >= band:
                return "win", True
            if stock_return <= -band:
                return "loss", False
            return "neutral", None
        if direction_expected == "down":
            if stock_return <= -band:
                return "win", True
            if stock_return >= band:
                return "loss", False
            return "neutral", None
        if direction_expected == "not_down":
            if stock_return >= 0:
                return "win", True
            if stock_return <= -band:
                return "loss", False
            return "neutral", None
        if abs(stock_return) <= band:
            return "win", True
        return "loss", False

    @classmethod
    def _classify_signal_outcome(
        cls,
        *,
        stock_return_pct: float | None,
        direction_expected: str,
        neutral_band_pct: float,
    ) -> tuple[str | None, bool | None]:
        if stock_return_pct is None:
            return None, None
        band = abs(float(neutral_band_pct))
        stock_return = float(stock_return_pct)
        if direction_expected == "up":
            if stock_return >= band:
                return "hit", True
            if stock_return <= -band:
                return "miss", False
            return "neutral", None
        if direction_expected == "not_down":
            if stock_return >= 0:
                return "hit", True
            if stock_return <= -band:
                return "miss", False
            return "neutral", None
        if direction_expected == "not_up":
            if stock_return <= band:
                return "hit", True
            return "miss", False
        return None, None

    @staticmethod
    def _finite_optional_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @classmethod
    def _evaluate_targets(
        cls,
        *,
        position: str,
        stop_loss: float | None,
        take_profit: float | None,
        window_bars: list[DailyBarLike],
        end_close: float | None,
    ) -> tuple[bool | None, bool | None, str, date | None, int | None, float | None, str]:
        if position != "long":
            return None, None, "not_applicable", None, None, None, "cash"
        has_any_target = stop_loss is not None or take_profit is not None
        if not has_any_target:
            return None, None, "neither", None, None, end_close, "window_end"

        hit_stop_loss = None if stop_loss is None else False
        hit_take_profit = None if take_profit is None else False
        first_hit = "neither"
        first_hit_date = None
        first_hit_days = None
        exit_price = end_close
        exit_reason = "window_end"

        for index, bar in enumerate(window_bars, start=1):
            stop_hit = stop_loss is not None and bar.low is not None and bar.low <= stop_loss
            take_profit_hit = take_profit is not None and bar.high is not None and bar.high >= take_profit
            if stop_hit:
                hit_stop_loss = True
            if take_profit_hit:
                hit_take_profit = True
            if not stop_hit and not take_profit_hit:
                continue

            first_hit_date = bar.date
            first_hit_days = index
            if stop_hit and take_profit_hit:
                first_hit = "ambiguous"
                exit_price = stop_loss
                exit_reason = "ambiguous_stop_loss"
                break
            if stop_hit:
                first_hit = "stop_loss"
                exit_price = stop_loss
                exit_reason = "stop_loss"
                break
            first_hit = "take_profit"
            exit_price = take_profit
            exit_reason = "take_profit"
            break

        return hit_stop_loss, hit_take_profit, first_hit, first_hit_date, first_hit_days, exit_price, exit_reason

    @staticmethod
    def _average(values: Iterable[float | None]) -> float | None:
        items = [float(value) for value in values if value is not None]
        if not items:
            return None
        return round(sum(items) / len(items), 4)

    @staticmethod
    def _compute_advice_breakdown(results: list[SignalResultLike]) -> dict[str, Any]:
        breakdown: dict[str, dict[str, int]] = {}
        for row in results:
            raw_advice = row.operation_advice
            advice = (raw_advice if isinstance(raw_advice, str) else str(raw_advice or "")).strip() or "(unknown)"
            bucket = breakdown.setdefault(advice, {"total": 0, "win": 0, "loss": 0, "neutral": 0})
            bucket["total"] += 1
            outcome = (row.outcome or "").strip()
            if outcome in ("win", "loss", "neutral"):
                bucket[outcome] += 1

        enriched: dict[str, Any] = {}
        for advice, bucket in breakdown.items():
            win_count = bucket["win"]
            loss_count = bucket["loss"]
            denominator = win_count + loss_count
            win_rate = round(win_count / denominator * 100, 2) if denominator else None
            enriched[advice] = {**bucket, "win_rate_pct": win_rate}
        return enriched

    @staticmethod
    def _compute_diagnostics(results: list[SignalResultLike]) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        first_hit_counts: dict[str, int] = {}
        for row in results:
            status = (row.eval_status or "").strip() or "(unknown)"
            status_counts[status] = status_counts.get(status, 0) + 1
            first_hit = (row.first_hit or "").strip() or "(none)"
            first_hit_counts[first_hit] = first_hit_counts.get(first_hit, 0) + 1
        return {
            "eval_status": status_counts,
            "first_hit": first_hit_counts,
        }


EvaluationConfig = SignalEvaluationConfig
BacktestEngine = SignalEvaluationEngine
BacktestResultLike = SignalResultLike
