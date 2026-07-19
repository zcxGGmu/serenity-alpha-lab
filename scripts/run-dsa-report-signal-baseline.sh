#!/usr/bin/env bash
set -euo pipefail

BASELINE_TAG="upstream/dsa-v3.26.1"
EXPECTED_SHA="e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
WORKTREE_PATH=".worktrees/dsa-v3.26.1"
CACHE_ROOT=".cache/dsa-p0"
PATCH_ROOT="patches/dsa/v3.26.1"
SNAPSHOT_DIR="docs/baselines/dsa-v3.26.1/report-signal"
UPDATE_SNAPSHOTS=0

usage() {
  cat <<'USAGE'
Usage: scripts/run-dsa-report-signal-baseline.sh [options]

Generate and verify locked DSA report and Signal Evaluation golden baselines.

Options:
  --worktree <path>         Locked DSA worktree. Default: .worktrees/dsa-v3.26.1
  --cache-root <path>       Cache/artifact root. Default: .cache/dsa-p0
  --patch-root <path>       Local DSA patch directory. Default: patches/dsa/v3.26.1
  --snapshot-dir <path>     Committed snapshot directory. Default: docs/baselines/dsa-v3.26.1/report-signal
  --update-snapshots        Replace committed snapshots with freshly generated output
  -h, --help                Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --worktree)
      WORKTREE_PATH="$2"
      shift 2
      ;;
    --cache-root)
      CACHE_ROOT="$2"
      shift 2
      ;;
    --patch-root)
      PATCH_ROOT="$2"
      shift 2
      ;;
    --snapshot-dir)
      SNAPSHOT_DIR="$2"
      shift 2
      ;;
    --update-snapshots)
      UPDATE_SNAPSHOTS=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found on PATH: $1" >&2
    exit 1
  fi
}

repo_root() {
  git rev-parse --show-toplevel
}

normalize_repo_relative_path() {
  local label="$1"
  local rel="$2"
  local required_prefix="$3"

  rel="${rel#./}"
  rel="${rel%/}"
  if [[ -z "$rel" || "$rel" == /* ]]; then
    echo "Unsafe $label path: $rel" >&2
    exit 2
  fi
  IFS='/' read -r -a parts <<< "$rel"
  for part in "${parts[@]}"; do
    if [[ -z "$part" || "$part" == "." || "$part" == ".." ]]; then
      echo "Unsafe $label path: $rel" >&2
      exit 2
    fi
  done
  if [[ "$rel" != "$required_prefix" && "$rel" != "$required_prefix"/* ]]; then
    echo "$label path must stay under $required_prefix: $rel" >&2
    exit 2
  fi
  printf '%s\n' "$rel"
}

compare_snapshot() {
  local name="$1"
  if [[ ! -f "$SNAPSHOT_ABS/$name" ]]; then
    echo "Missing snapshot: $SNAPSHOT_DIR/$name" >&2
    return 1
  fi
  diff -u "$SNAPSHOT_ABS/$name" "$GENERATED_DIR/$name" > "$DIFF_DIR/$name.diff"
}

allow_generated_worktree_untracked_path() {
  local path="$1"
  case "$path" in
    apps/dsa-desktop/.cache/*|\
    apps/dsa-desktop/node_modules/*|\
    apps/dsa-web/node_modules/*|\
    static/*|\
    .pytest_cache/*|\
    */.pytest_cache/*|\
    __pycache__/*|\
    */__pycache__/*|\
    *.pyc)
      return 0
      ;;
  esac
  return 1
}

load_allowed_patch_paths() {
  ALLOWED_PATCH_PATHS=()
  if [[ ! -d "$PATCH_ROOT" ]]; then
    return
  fi
  while IFS= read -r patch_path; do
    while IFS= read -r line; do
      path="$(printf '%s\n' "$line" | awk -F '\t' '{print $3}')"
      if [[ -n "$path" ]]; then
        ALLOWED_PATCH_PATHS+=("$path")
      fi
    done < <(git -C "$WORKTREE_PATH" apply --numstat "$REPO_ROOT/$patch_path")
  done < <(find "$PATCH_ROOT" -maxdepth 1 -type f -name '*.patch' | sort)
}

is_allowed_patch_path() {
  local path="$1"
  local allowed
  for allowed in "${ALLOWED_PATCH_PATHS[@]:-}"; do
    if [[ "$path" == "$allowed" ]]; then
      return 0
    fi
  done
  return 1
}

verify_worktree_diff_is_registered() {
  load_allowed_patch_paths

  unexpected=()
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    status="${line:0:2}"
    path="${line:3}"
    if [[ "$status" == "??" ]]; then
      if ! allow_generated_worktree_untracked_path "$path"; then
        unexpected+=("$line")
      fi
      continue
    fi
    if ! is_allowed_patch_path "$path"; then
      unexpected+=("$line")
    fi
  done < <(git -C "$WORKTREE_PATH" status --porcelain=v1 --untracked-files=all)

  if [[ "${#unexpected[@]}" -gt 0 ]]; then
    echo "DSA worktree contains changes outside registered baseline patches/generated caches:" >&2
    printf '  %s\n' "${unexpected[@]}" >&2
    exit 1
  fi
}

require_cmd git
require_cmd diff

REPO_ROOT="$(repo_root)"
cd "$REPO_ROOT"

WORKTREE_PATH="$(normalize_repo_relative_path "worktree" "$WORKTREE_PATH" ".worktrees")"
CACHE_ROOT="$(normalize_repo_relative_path "cache root" "$CACHE_ROOT" ".cache")"
PATCH_ROOT="$(normalize_repo_relative_path "patch root" "$PATCH_ROOT" "patches")"
SNAPSHOT_DIR="$(normalize_repo_relative_path "snapshot dir" "$SNAPSHOT_DIR" "docs/baselines")"

BASELINE_SHA="$(git rev-parse "$BASELINE_TAG")"
if [[ "$BASELINE_SHA" != "$EXPECTED_SHA" ]]; then
  echo "Baseline tag $BASELINE_TAG resolves to $BASELINE_SHA, expected $EXPECTED_SHA" >&2
  exit 1
fi

if [[ ! -d "$WORKTREE_PATH" ]]; then
  echo "Missing DSA worktree: $WORKTREE_PATH" >&2
  echo "Run scripts/bootstrap-dsa-baseline.sh first." >&2
  exit 1
fi

WORKTREE_SHA="$(git -C "$WORKTREE_PATH" rev-parse HEAD)"
if [[ "$WORKTREE_SHA" != "$EXPECTED_SHA" ]]; then
  echo "Worktree $WORKTREE_PATH is at $WORKTREE_SHA, expected $EXPECTED_SHA" >&2
  exit 1
fi

scripts/apply-dsa-baseline-patches.sh --worktree "$WORKTREE_PATH" --patch-root "$PATCH_ROOT"
verify_worktree_diff_is_registered

VENV_PATH="$CACHE_ROOT/venv"
if [[ ! -x "$VENV_PATH/bin/python" ]]; then
  echo "Missing Python venv: $VENV_PATH" >&2
  echo "Run scripts/bootstrap-dsa-baseline.sh --python <python3.11> --install-ci-tools first." >&2
  exit 1
fi

WORKTREE_ABS="$REPO_ROOT/$WORKTREE_PATH"
CACHE_ABS="$REPO_ROOT/$CACHE_ROOT"
VENV_ABS="$REPO_ROOT/$VENV_PATH"
SNAPSHOT_ABS="$REPO_ROOT/$SNAPSHOT_DIR"
ARTIFACT_DIR="$CACHE_ABS/report-signal-baseline-artifacts"
GENERATED_DIR="$ARTIFACT_DIR/generated"
DIFF_DIR="$ARTIFACT_DIR/diff"
EMPTY_ENV="$ARTIFACT_DIR/empty.env"

rm -rf "$GENERATED_DIR" "$DIFF_DIR"
mkdir -p "$GENERATED_DIR" "$DIFF_DIR"
: > "$EMPTY_ENV"

(
  cd "$WORKTREE_ABS"
  export PATH="$VENV_ABS/bin:$PATH"
  export PYTHONPATH="$WORKTREE_ABS${PYTHONPATH:+:$PYTHONPATH}"
  export ENV_FILE="$EMPTY_ENV"
  export DSA_DESKTOP_MODE=false
  export DSA_RUNTIME_SCHEDULER_SUPPRESS_START=true
  export DSA_RUNTIME_SCHEDULER_RUN_IMMEDIATELY=false
  export STOCK_INDEX_REMOTE_UPDATE_ENABLED=false
  export LITELLM_LOCAL_MODEL_COST_MAP=True
  "$VENV_ABS/bin/python" - "$GENERATED_DIR" "$WORKTREE_ABS" "$EXPECTED_SHA" <<'PY'
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

generated_dir = Path(sys.argv[1])
worktree = Path(sys.argv[2])
expected_sha = sys.argv[3]
fixed_now = datetime(2026, 1, 5, 9, 30, 0)


def stable_json_dump(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assert_no_forbidden_content(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    forbidden_patterns = [
        r"/Users/",
        r"BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY",
        r"sk-[A-Za-z0-9_-]{12,}",
        r"AIza[0-9A-Za-z_-]{20,}",
        r"(?i)bearer\s+[A-Za-z0-9._-]{10,}",
        r"(?i)(password|token|secret|webhook)\s*=\s*[^\s\]\}),;]+",
        r"https://hooks\\.slack\\.com/services/",
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, text):
            raise AssertionError(f"forbidden fixture content matched {pattern!r} in {path.name}")


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        if tz is not None:
            return fixed_now.replace(tzinfo=tz)
        return fixed_now


@dataclasses.dataclass
class DailyBar:
    date: date
    high: float | None
    low: float | None
    close: float | None


BACKTEST_RESULT_FIELDS = (
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
)


def result_namespace(payload: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(**{field: payload.get(field) for field in BACKTEST_RESULT_FIELDS})


def normalize_eval_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    for key, value in list(normalized.items()):
        if isinstance(value, date):
            normalized[key] = value.isoformat()
    return normalized


from src.analyzer import AnalysisResult, GeminiAnalyzer, check_content_integrity
from src.config import Config
from src.core.backtest_engine import BacktestEngine, EvaluationConfig
from src.core.market_review import _render_market_review_payload_markdown
from src.notification import NotificationService
from src.schemas.report_schema import AnalysisReportSchema
from src.services.decision_signal_summary import (
    format_decision_signal_excerpt,
    summarize_decision_signal,
)


def make_config(**overrides: Any) -> Config:
    base = {
        "stock_list": [],
        "report_language": "zh",
        "report_renderer_enabled": False,
        "report_show_llm_model": True,
        "report_summary_only": False,
        "report_history_compare_n": 0,
        "markdown_to_image_channels": [],
    }
    base.update(overrides)
    return Config(**base)


def stub_llm_payloads() -> list[dict[str, Any]]:
    return [
        {
            "code": "600519",
            "name": "贵州茅台",
            "raw_response": {
                "stock_name": "贵州茅台",
                "sentiment_score": 74,
                "trend_prediction": "看多",
                "operation_advice": "买入",
                "decision_type": "buy",
                "action": "buy",
                "confidence_level": "中",
                "analysis_summary": "量价结构改善，适合等待回踩后分批关注。",
                "key_points": "均线走稳；量能温和；估值仍需观察。",
                "risk_warning": "若放量跌破支撑位，需要降低仓位。",
                "dashboard": {
                    "core_conclusion": {
                        "one_sentence": "回踩不破支撑时可分批买入。",
                        "signal_type": "🟢买入信号",
                        "time_sensitivity": "本周内",
                        "position_advice": {
                            "no_position": "等待回踩 1660 附近试探性建仓。",
                            "has_position": "保留底仓，跌破 1600 执行止损。",
                        },
                    },
                    "data_perspective": {
                        "trend_status": {
                            "ma_alignment": "多头排列",
                            "is_bullish": True,
                            "trend_score": 76,
                        },
                        "price_position": {
                            "current_price": 1688.0,
                            "ma5": 1668.0,
                            "ma10": 1642.0,
                            "ma20": 1608.0,
                            "bias_ma5": 1.2,
                            "bias_status": "安全",
                            "support_level": 1600.0,
                            "resistance_level": 1740.0,
                        },
                        "volume_analysis": {
                            "volume_ratio": 1.18,
                            "volume_status": "温和放量",
                            "turnover_rate": 0.8,
                            "volume_meaning": "缩量回踩后买盘回补。",
                        },
                        "chip_structure": {
                            "profit_ratio": "62%",
                            "avg_cost": 1580,
                            "concentration": "中等",
                            "chip_health": "健康",
                        },
                    },
                    "intelligence": {
                        "latest_news": "公司渠道库存维持正常。",
                        "risk_alerts": ["消费复苏斜率低于预期", "高端白酒估值仍受利率影响"],
                        "positive_catalysts": ["春节备货预期改善", "现金流质量稳定"],
                        "earnings_outlook": "利润率保持韧性。",
                        "sentiment_summary": "机构观点偏中性乐观。",
                    },
                    "battle_plan": {
                        "sniper_points": {
                            "ideal_buy": "1660-1680",
                            "secondary_buy": "1620",
                            "stop_loss": "1600",
                            "take_profit": "1740",
                        },
                        "position_strategy": {
                            "suggested_position": "20%-30%",
                            "entry_plan": "分两笔买入，等待回踩确认。",
                            "risk_control": "跌破 1600 后停止加仓。",
                        },
                        "action_checklist": ["✅ 趋势保持向上", "⚠️ 量能仍需确认", "❌ 不追高"],
                    },
                    "phase_decision": {
                        "phase_context": {"market": "cn", "phase": "postmarket"},
                        "action_window": "盘后复盘",
                        "immediate_action": "设置提醒",
                        "watch_conditions": ["1660 支撑有效", "量能不低于 5 日均量"],
                        "next_check_time": "下一交易日 10:00",
                        "confidence_reason": "日线数据完整但缺少盘中确认。",
                        "data_limitations": ["未使用真实 Provider，仅为离线金标"],
                    },
                    "signal_attribution": {
                        "technical_indicators": "45%",
                        "news_sentiment": "15%",
                        "fundamentals": "25%",
                        "market_conditions": "15%",
                        "strongest_bullish_signal": "均线多头排列",
                        "strongest_bearish_signal": "估值弹性有限",
                    },
                },
            },
        },
        {
            "code": "AAPL",
            "name": "Apple",
            "raw_response": {
                "stock_name": "Apple",
                "sentiment_score": 54,
                "trend_prediction": "震荡",
                "operation_advice": "观望",
                "decision_type": "hold",
                "action": "watch",
                "confidence_level": "中",
                "analysis_summary": "短期等待放量突破后再提高仓位。",
                "key_points": "趋势未坏；成交量不足；等待业绩确认。",
                "risk_warning": "若科技权重回调，股价可能测试下方支撑。",
                "dashboard": {
                    "core_conclusion": {
                        "one_sentence": "等待放量突破后再行动。",
                        "signal_type": "🟡持有观望",
                        "time_sensitivity": "不急",
                        "position_advice": {
                            "no_position": "等待 190 上方放量确认。",
                            "has_position": "维持底仓，跌破 182 减仓。",
                        },
                    },
                    "intelligence": {
                        "risk_alerts": ["新品周期预期已有部分反映"],
                        "positive_catalysts": ["服务收入保持稳健"],
                        "sentiment_summary": "市场预期分歧扩大。",
                    },
                    "battle_plan": {
                        "sniper_points": {
                            "ideal_buy": "190",
                            "stop_loss": "182",
                            "take_profit": "205",
                        }
                    },
                    "signal_attribution": {
                        "technical_indicators": 30,
                        "news_sentiment": 20,
                        "fundamentals": 30,
                        "market_conditions": 20,
                        "strongest_bullish_signal": "服务业务韧性",
                        "strongest_bearish_signal": "短线量能不足",
                    },
                },
            },
        },
    ]


def parse_structured_reports(stubs: list[dict[str, Any]]) -> tuple[list[AnalysisResult], dict[str, Any]]:
    analyzer = GeminiAnalyzer.__new__(GeminiAnalyzer)
    reports: list[AnalysisResult] = []
    output: dict[str, Any] = {"items": [], "validation": {}}
    for stub in stubs:
        raw_text = json.dumps(stub["raw_response"], ensure_ascii=False, sort_keys=True)
        result = analyzer._parse_response(raw_text, stub["code"], stub["name"])
        result.model_used = "stub/offline-golden"
        reports.append(result)
        ok, missing = check_content_integrity(result, require_phase_decision=stub["code"] == "600519")
        AnalysisReportSchema.model_validate(stub["raw_response"])
        output["items"].append(
            {
                "code": result.code,
                "name": result.name,
                "raw_response_sha256": sha256_text(raw_text),
                "parsed": result.to_dict(),
                "content_integrity": {"passed": ok, "missing": missing},
            }
        )
    output["validation"] = {
        "schema_validation_passed": True,
        "content_integrity_passed": all(item["content_integrity"]["passed"] for item in output["items"]),
        "phase_decision_required_for": ["600519"],
        "uses_stub_llm_only": True,
    }
    return reports, output


def make_market_review_payload() -> dict[str, Any]:
    return {
        "version": 1,
        "kind": "market_review",
        "region": "cn",
        "language": "zh",
        "title": "2026-01-05 大盘复盘",
        "sections": [
            {
                "key": "overview",
                "title": "2026-01-05 大盘复盘",
                "markdown": "> 指数震荡收高，成交额温和放大。\n\n### 一、盘面总览\n权重与成长风格均有修复，但追高意愿仍有限。",
            },
            {
                "key": "fund_flow",
                "title": "资金方向",
                "markdown": "- 北向资金小幅净流入。\n- 高股息、AI 算力和消费电子轮动活跃。",
            },
            {
                "key": "watchlist",
                "title": "明日观察",
                "markdown": "关注成交额能否维持在万亿附近，以及权重板块是否继续承接。",
            },
        ],
        "sectors": {
            "top": [{"name": "AI算力", "change_pct": 3.25}, {"name": "消费电子", "change_pct": 2.18}],
            "bottom": [{"name": "煤炭", "change_pct": -1.12}],
        },
    }


def make_signal_inputs() -> list[dict[str, Any]]:
    return [
        {
            "case": "buy_take_profit",
            "operation_advice": "买入",
            "analysis_date": "2026-01-02",
            "start_price": 100.0,
            "stop_loss": 94.0,
            "take_profit": 105.0,
            "bars": [
                {"date": "2026-01-03", "high": 106.0, "low": 99.0, "close": 104.0},
                {"date": "2026-01-04", "high": 108.0, "low": 102.0, "close": 107.0},
                {"date": "2026-01-05", "high": 109.0, "low": 106.0, "close": 108.0},
            ],
        },
        {
            "case": "sell_direction_win",
            "operation_advice": "卖出",
            "analysis_date": "2026-01-02",
            "start_price": 50.0,
            "stop_loss": None,
            "take_profit": None,
            "bars": [
                {"date": "2026-01-03", "high": 50.5, "low": 48.0, "close": 49.0},
                {"date": "2026-01-04", "high": 49.2, "low": 46.8, "close": 47.2},
                {"date": "2026-01-05", "high": 48.0, "low": 46.5, "close": 47.0},
            ],
        },
        {
            "case": "hold_loss",
            "operation_advice": "持有",
            "analysis_date": "2026-01-02",
            "start_price": 20.0,
            "stop_loss": 18.0,
            "take_profit": 23.0,
            "bars": [
                {"date": "2026-01-03", "high": 20.2, "low": 19.2, "close": 19.5},
                {"date": "2026-01-04", "high": 19.6, "low": 18.7, "close": 19.0},
                {"date": "2026-01-05", "high": 19.1, "low": 18.8, "close": 19.0},
            ],
        },
        {
            "case": "watch_flat_win",
            "operation_advice": "观望",
            "analysis_date": "2026-01-02",
            "start_price": 30.0,
            "stop_loss": None,
            "take_profit": None,
            "bars": [
                {"date": "2026-01-03", "high": 30.5, "low": 29.7, "close": 30.1},
                {"date": "2026-01-04", "high": 30.4, "low": 29.8, "close": 30.0},
                {"date": "2026-01-05", "high": 30.6, "low": 29.9, "close": 30.3},
            ],
        },
        {
            "case": "buy_ambiguous_stop_first",
            "operation_advice": "买入",
            "analysis_date": "2026-01-02",
            "start_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 105.0,
            "bars": [
                {"date": "2026-01-03", "high": 110.0, "low": 90.0, "close": 100.0},
                {"date": "2026-01-04", "high": 101.0, "low": 98.0, "close": 99.0},
                {"date": "2026-01-05", "high": 100.0, "low": 97.0, "close": 98.0},
            ],
        },
        {
            "case": "buy_insufficient_data",
            "operation_advice": "买入",
            "analysis_date": "2026-01-02",
            "start_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 105.0,
            "bars": [
                {"date": "2026-01-03", "high": 102.0, "low": 99.0, "close": 101.0},
            ],
        },
    ]


def evaluate_signals(inputs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = EvaluationConfig(eval_window_days=3, neutral_band_pct=2.0, engine_version="v1")
    outputs: list[dict[str, Any]] = []
    rows: list[SimpleNamespace] = []
    for item in inputs:
        bars = [
            DailyBar(
                date=date.fromisoformat(str(bar["date"])),
                high=bar["high"],
                low=bar["low"],
                close=bar["close"],
            )
            for bar in item["bars"]
        ]
        evaluation = BacktestEngine.evaluate_single(
            operation_advice=item["operation_advice"],
            analysis_date=date.fromisoformat(str(item["analysis_date"])),
            start_price=float(item["start_price"]),
            forward_bars=bars,
            stop_loss=item["stop_loss"],
            take_profit=item["take_profit"],
            config=config,
        )
        normalized = {"case": item["case"], **normalize_eval_payload(evaluation)}
        outputs.append(normalized)
        rows.append(result_namespace(evaluation))
    summary = BacktestEngine.compute_summary(
        results=rows,
        scope="overall",
        code="__overall__",
        eval_window_days=config.eval_window_days,
        engine_version=config.engine_version,
    )
    return outputs, summary


def make_decision_signal_summary() -> dict[str, Any]:
    payload = {
        "id": 1001,
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "market": "cn",
        "action": "buy",
        "action_label": "买入",
        "horizon": "3d",
        "status": "active",
        "source_type": "report",
        "source_report_id": 501,
        "reason": "回踩支撑后量能修复",
        "watch_conditions": ["1660 支撑有效", "量能不低于 5 日均量"],
        "risk_summary": {"drawdown": "跌破 1600 后止损"},
        "created_at": "2026-01-05T09:30:00+08:00",
        "expires_at": "2026-01-08T09:30:00+08:00",
        "metadata": {"ignored": True},
    }
    summary = summarize_decision_signal(payload)
    excerpt = format_decision_signal_excerpt(summary, report_language="zh")
    return {"input": payload, "summary": summary, "excerpt": excerpt}


generated_dir.mkdir(parents=True, exist_ok=True)

stubs = stub_llm_payloads()
reports, structured_reports = parse_structured_reports(stubs)
signal_inputs = make_signal_inputs()
signal_outputs, signal_summary = evaluate_signals(signal_inputs)
market_review_payload = make_market_review_payload()
decision_signal_summary = make_decision_signal_summary()

input_payload = {
    "baseline": {
        "upstream": "ZhuLinsen/daily_stock_analysis",
        "tag": "v3.26.1",
        "commit": expected_sha,
    },
    "fixed_clock": fixed_now.isoformat(),
    "report_date": "2026-01-05",
    "stub_llm_codes": [item["code"] for item in stubs],
    "market_review_region": "cn",
    "signal_evaluation_config": {
        "eval_window_days": 3,
        "neutral_band_pct": 2.0,
        "engine_version": "v1",
    },
    "signal_evaluation_cases": signal_inputs,
}
stable_json_dump(generated_dir / "inputs.json", input_payload)
stable_json_dump(generated_dir / "stub-llm-responses.json", stubs)
stable_json_dump(generated_dir / "structured-reports.json", structured_reports)
stable_json_dump(generated_dir / "signal-evaluations.json", {"items": signal_outputs})
stable_json_dump(generated_dir / "signal-evaluation-summary.json", signal_summary)
stable_json_dump(generated_dir / "decision-signal-summary.json", decision_signal_summary)
stable_json_dump(generated_dir / "market-review-payload.json", market_review_payload)

config = make_config()
with patch("src.notification.get_config", return_value=config), patch("src.notification.datetime", FixedDateTime):
    notification_service = NotificationService()
    single_stock_report = notification_service.generate_single_stock_report(reports[0])
    aggregate_report = notification_service.generate_aggregate_report(
        reports,
        "full",
        report_date="2026-01-05",
    )

market_review_report = _render_market_review_payload_markdown(
    market_review_payload,
    wrapper_title="🎯 大盘复盘",
)

(generated_dir / "single-stock-report.md").write_text(single_stock_report + "\n", encoding="utf-8")
(generated_dir / "aggregate-report.md").write_text(aggregate_report + "\n", encoding="utf-8")
(generated_dir / "market-review-report.md").write_text(market_review_report + "\n", encoding="utf-8")

for generated_file in sorted(generated_dir.iterdir()):
    if generated_file.is_file():
        assert_no_forbidden_content(generated_file)

content_hashes = {
    "files": {
        path.name: sha256_file(path)
        for path in sorted(generated_dir.iterdir())
        if path.is_file() and path.name != "content-hashes.json"
    },
    "logical": {
        "structured_report_codes": [item["code"] for item in structured_reports["items"]],
        "signal_evaluation_cases": [item["case"] for item in signal_outputs],
        "market_review_payload_sha256": sha256_file(generated_dir / "market-review-payload.json"),
    },
}
stable_json_dump(generated_dir / "content-hashes.json", content_hashes)

coverage = {
    "single_stock_report": {
        "covered": "贵州茅台" in single_stock_report and "信号归因" in single_stock_report,
        "artifact": "single-stock-report.md",
    },
    "aggregate_report": {
        "covered": "AAPL" in aggregate_report and "2026-01-05" in aggregate_report,
        "artifact": "aggregate-report.md",
    },
    "market_review_report": {
        "covered": "大盘复盘" in market_review_report and "板块主线" in market_review_report,
        "artifact": "market-review-report.md",
    },
    "signal_evaluation_metrics": {
        "covered": signal_summary.get("total_evaluations") == len(signal_outputs)
        and signal_summary.get("completed_count") == 5
        and signal_summary.get("insufficient_count") == 1,
        "artifact": "signal-evaluation-summary.json",
    },
    "decision_signal_summary": {
        "covered": bool(decision_signal_summary.get("summary")) and "AI 决策信号" in decision_signal_summary["excerpt"],
        "artifact": "decision-signal-summary.json",
    },
}

validation = {
    "required_coverage_passed": all(item["covered"] for item in coverage.values()),
    "schema_validation_passed": structured_reports["validation"]["schema_validation_passed"],
    "content_integrity_passed": structured_reports["validation"]["content_integrity_passed"],
    "secret_scan_passed": True,
    "uses_stub_llm_only": True,
    "real_provider_calls_zero": True,
    "real_notification_sends_zero": True,
}
if not all(validation.values()):
    raise AssertionError(f"report/signal baseline validation failed: {validation}")

summary = {
    "baseline": input_payload["baseline"],
    "generated_at": "2026-07-19T00:00:00Z",
    "artifact_set": "report-signal-golden-fixtures",
    "artifacts": {
        **content_hashes["files"],
        "content-hashes.json": sha256_file(generated_dir / "content-hashes.json"),
    },
    "coverage": coverage,
    "counts": {
        "structured_report_count": len(structured_reports["items"]),
        "stub_llm_response_count": len(stubs),
        "signal_evaluation_case_count": len(signal_outputs),
        "markdown_report_count": 3,
    },
    "signal_evaluation_key_metrics": {
        key: signal_summary.get(key)
        for key in (
            "total_evaluations",
            "completed_count",
            "insufficient_count",
            "direction_accuracy_pct",
            "win_rate_pct",
            "neutral_rate_pct",
            "avg_stock_return_pct",
            "avg_simulated_return_pct",
            "stop_loss_trigger_rate",
            "take_profit_trigger_rate",
            "ambiguous_rate",
            "avg_days_to_first_hit",
        )
    },
    "validation": validation,
}
stable_json_dump(generated_dir / "summary.json", summary)
PY
)

SNAPSHOT_NAMES=(
  inputs.json
  stub-llm-responses.json
  structured-reports.json
  single-stock-report.md
  aggregate-report.md
  market-review-payload.json
  market-review-report.md
  signal-evaluations.json
  signal-evaluation-summary.json
  decision-signal-summary.json
  content-hashes.json
  summary.json
)

if [[ "$UPDATE_SNAPSHOTS" -eq 1 ]]; then
  mkdir -p "$SNAPSHOT_ABS"
  for snapshot_name in "${SNAPSHOT_NAMES[@]}"; do
    cp "$GENERATED_DIR/$snapshot_name" "$SNAPSHOT_ABS/$snapshot_name"
  done
  echo "Updated report/signal baseline snapshots in $SNAPSHOT_DIR"
else
  for snapshot_name in "${SNAPSHOT_NAMES[@]}"; do
    if ! compare_snapshot "$snapshot_name"; then
      echo "Report/signal baseline snapshot changed: $snapshot_name" >&2
      echo "Inspect $DIFF_DIR and rerun with --update-snapshots if intentional." >&2
      exit 1
    fi
  done
  echo "Report/signal baseline snapshots match $SNAPSHOT_DIR"
fi

echo "Generated artifacts: $GENERATED_DIR"
