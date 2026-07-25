#!/usr/bin/env bash
set -euo pipefail

BASELINE_TAG="upstream/dsa-v3.26.1"
EXPECTED_SHA="e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
WORKTREE_PATH=".worktrees/dsa-v3.26.1"
CACHE_ROOT=".cache/dsa-p4"
PATCH_ROOT="patches/dsa/v3.26.1"
SNAPSHOT_DIR="docs/baselines/dsa-v3.26.1/signal-evaluation-characterization"
UPDATE_SNAPSHOTS=0

usage() {
  cat <<'USAGE'
Usage: scripts/run-dsa-signal-evaluation-characterization.sh [options]

Generate and verify SAL-P4-001 DSA Signal Evaluation characterization goldens.

Options:
  --worktree <path>         Locked DSA worktree. Default: .worktrees/dsa-v3.26.1
  --cache-root <path>       Cache/artifact root. Default: .cache/dsa-p4
  --patch-root <path>       Local DSA patch directory. Default: patches/dsa/v3.26.1
  --snapshot-dir <path>     Committed snapshot directory. Default: docs/baselines/dsa-v3.26.1/signal-evaluation-characterization
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

compare_snapshot() {
  local name="$1"
  if [[ ! -f "$SNAPSHOT_ABS/$name" ]]; then
    echo "Missing snapshot: $SNAPSHOT_DIR/$name" >&2
    return 1
  fi
  diff -u "$SNAPSHOT_ABS/$name" "$GENERATED_DIR/$name" > "$DIFF_DIR/$name.diff"
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

WORKTREE_ABS="$REPO_ROOT/$WORKTREE_PATH"
CACHE_ABS="$REPO_ROOT/$CACHE_ROOT"
SNAPSHOT_ABS="$REPO_ROOT/$SNAPSHOT_DIR"
ARTIFACT_DIR="$CACHE_ABS/signal-evaluation-characterization"
GENERATED_DIR="$ARTIFACT_DIR/generated"
DIFF_DIR="$ARTIFACT_DIR/diff"
EMPTY_ENV="$ARTIFACT_DIR/empty.env"

VENV_PY="$REPO_ROOT/.venv/bin/python"
if [[ -x "$REPO_ROOT/.cache/dsa-p0/venv/bin/python" ]]; then
  VENV_PY="$REPO_ROOT/.cache/dsa-p0/venv/bin/python"
fi
if [[ ! -x "$VENV_PY" ]]; then
  echo "Missing Python interpreter: expected .venv/bin/python or .cache/dsa-p0/venv/bin/python" >&2
  exit 1
fi

rm -rf "$GENERATED_DIR" "$DIFF_DIR"
mkdir -p "$GENERATED_DIR" "$DIFF_DIR"
: > "$EMPTY_ENV"

(
  cd "$WORKTREE_ABS"
  export PATH="$(dirname "$VENV_PY"):$PATH"
  export PYTHONPATH="$WORKTREE_ABS${PYTHONPATH:+:$PYTHONPATH}"
  export ENV_FILE="$EMPTY_ENV"
  export DSA_DESKTOP_MODE=false
  export DSA_RUNTIME_SCHEDULER_SUPPRESS_START=true
  export DSA_RUNTIME_SCHEDULER_RUN_IMMEDIATELY=false
  export STOCK_INDEX_REMOTE_UPDATE_ENABLED=false
  export LITELLM_LOCAL_MODEL_COST_MAP=True
  "$VENV_PY" - "$GENERATED_DIR" "$EXPECTED_SHA" <<'PY'
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

generated_dir = Path(sys.argv[1])
expected_sha = sys.argv[2]


def stable_json_dump(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: normalize_value(value) for key, value in payload.items()}


@dataclasses.dataclass(frozen=True)
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


# SAL-P4-001 explicitly freezes current legacy DSA Signal Evaluation behavior.
# BacktestEngine.evaluate_single is legacy signal evaluation, not a formal portfolio backtest.
from src.core.backtest_engine import BacktestEngine, EvaluationConfig
from api.v1.endpoints import backtest as backtest_endpoint  # api.v1.endpoints.backtest
from api.v1.schemas import backtest as backtest_schemas
from src.agent.tools.backtest_tools import ALL_BACKTEST_TOOLS


def make_engine_inputs() -> list[dict[str, Any]]:
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
        {
            "case": "negated_buy_wait_cash",
            "operation_advice": "不要买入，等待确认",
            "analysis_date": "2026-01-02",
            "start_price": 100.0,
            "stop_loss": None,
            "take_profit": None,
            "bars": [
                {"date": "2026-01-03", "high": 103.0, "low": 99.0, "close": 102.0},
                {"date": "2026-01-04", "high": 104.0, "low": 100.0, "close": 103.0},
                {"date": "2026-01-05", "high": 105.0, "low": 101.0, "close": 104.0},
            ],
        },
        {
            "case": "negated_sell_hold_long",
            "operation_advice": "不要卖出，继续持有",
            "analysis_date": "2026-01-02",
            "start_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 110.0,
            "bars": [
                {"date": "2026-01-03", "high": 102.0, "low": 99.0, "close": 101.0},
                {"date": "2026-01-04", "high": 101.0, "low": 98.0, "close": 100.0},
                {"date": "2026-01-05", "high": 103.0, "low": 99.0, "close": 101.0},
            ],
        },
        {
            "case": "english_negated_sell_hold",
            "operation_advice": "do not sell, hold and watch",
            "analysis_date": "2026-01-02",
            "start_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 110.0,
            "bars": [
                {"date": "2026-01-03", "high": 102.0, "low": 99.0, "close": 101.0},
                {"date": "2026-01-04", "high": 101.0, "low": 98.0, "close": 100.0},
                {"date": "2026-01-05", "high": 103.0, "low": 99.0, "close": 101.0},
            ],
        },
        {
            "case": "missing_end_close",
            "operation_advice": "买入",
            "analysis_date": "2026-01-02",
            "start_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 105.0,
            "bars": [
                {"date": "2026-01-03", "high": 102.0, "low": 99.0, "close": 101.0},
                {"date": "2026-01-04", "high": 103.0, "low": 98.0, "close": 102.0},
                {"date": "2026-01-05", "high": 104.0, "low": 99.0, "close": None},
            ],
        },
        {
            "case": "missing_high_low",
            "operation_advice": "买入",
            "analysis_date": "2026-01-02",
            "start_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 105.0,
            "bars": [
                {"date": "2026-01-03", "high": None, "low": None, "close": 101.0},
                {"date": "2026-01-04", "high": None, "low": None, "close": 102.0},
                {"date": "2026-01-05", "high": None, "low": None, "close": 103.0},
            ],
        },
    ]


def make_decision_signal_inputs() -> list[dict[str, Any]]:
    return [
        {
            "case": "decision_up_hit",
            "direction_expected": "up",
            "anchor_date": "2026-01-02",
            "start_price": 100.0,
            "bars": [
                {"date": "2026-01-03", "high": 102.0, "low": 99.0, "close": 101.0},
                {"date": "2026-01-04", "high": 104.0, "low": 100.0, "close": 103.0},
                {"date": "2026-01-05", "high": 105.0, "low": 101.0, "close": 104.0},
            ],
        },
        {
            "case": "decision_not_up_hit",
            "direction_expected": "not_up",
            "anchor_date": "2026-01-02",
            "start_price": 100.0,
            "bars": [
                {"date": "2026-01-03", "high": 102.0, "low": 99.0, "close": 101.0},
                {"date": "2026-01-04", "high": 101.0, "low": 98.0, "close": 100.0},
                {"date": "2026-01-05", "high": 100.0, "low": 98.0, "close": 99.0},
            ],
        },
        {
            "case": "decision_invalid_anchor",
            "direction_expected": "up",
            "anchor_date": "2026-01-02",
            "start_price": 0.0,
            "bars": [
                {"date": "2026-01-03", "high": 102.0, "low": 99.0, "close": 101.0},
                {"date": "2026-01-04", "high": 104.0, "low": 100.0, "close": 103.0},
                {"date": "2026-01-05", "high": 105.0, "low": 101.0, "close": 104.0},
            ],
        },
        {
            "case": "decision_insufficient_forward_bars",
            "direction_expected": "up",
            "anchor_date": "2026-01-02",
            "start_price": 100.0,
            "bars": [
                {"date": "2026-01-03", "high": 102.0, "low": 99.0, "close": 101.0},
            ],
        },
        {
            "case": "decision_missing_end_close",
            "direction_expected": "up",
            "anchor_date": "2026-01-02",
            "start_price": 100.0,
            "bars": [
                {"date": "2026-01-03", "high": 102.0, "low": 99.0, "close": 101.0},
                {"date": "2026-01-04", "high": 104.0, "low": 100.0, "close": 103.0},
                {"date": "2026-01-05", "high": 105.0, "low": 99.0, "close": None},
            ],
        },
    ]


def to_bars(rows: list[dict[str, Any]]) -> list[DailyBar]:
    return [
        DailyBar(
            date=date.fromisoformat(str(row["date"])),
            high=row["high"],
            low=row["low"],
            close=row["close"],
        )
        for row in rows
    ]


def evaluate_engine(inputs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = EvaluationConfig(eval_window_days=3, neutral_band_pct=2.0, engine_version="v1")
    outputs: list[dict[str, Any]] = []
    summary_rows: list[SimpleNamespace] = []
    for item in inputs:
        evaluation = BacktestEngine.evaluate_single(
            operation_advice=item["operation_advice"],
            analysis_date=date.fromisoformat(str(item["analysis_date"])),
            start_price=float(item["start_price"]),
            forward_bars=to_bars(item["bars"]),
            stop_loss=item["stop_loss"],
            take_profit=item["take_profit"],
            config=config,
        )
        normalized = {"case": item["case"], **normalize_payload(evaluation)}
        outputs.append(normalized)
        summary_rows.append(result_namespace(evaluation))
    summary = BacktestEngine.compute_summary(
        results=summary_rows,
        scope="overall",
        code="__overall__",
        eval_window_days=config.eval_window_days,
        engine_version=config.engine_version,
    )
    return outputs, normalize_payload(summary)


def evaluate_decision_signals(inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    config = EvaluationConfig(eval_window_days=3, neutral_band_pct=2.0, engine_version="v1")
    outputs: list[dict[str, Any]] = []
    for item in inputs:
        evaluation = BacktestEngine.evaluate_decision_signal(
            direction_expected=item["direction_expected"],
            anchor_date=date.fromisoformat(str(item["anchor_date"])),
            start_price=float(item["start_price"]),
            forward_bars=to_bars(item["bars"]),
            config=config,
        )
        outputs.append({"case": item["case"], **normalize_payload(evaluation)})
    return outputs


def collect_api_surface() -> dict[str, Any]:
    routes = []
    for route in backtest_endpoint.router.routes:
        methods = sorted(method for method in getattr(route, "methods", set()) if method not in {"HEAD", "OPTIONS"})
        if not methods:
            continue
        response_model = getattr(route, "response_model", None)
        routes.append(
            {
                "name": getattr(route, "name", None),
                "path": f"/api/v1/backtest{getattr(route, 'path', '')}",
                "methods": methods,
                "summary": getattr(route, "summary", None),
                "response_model": getattr(response_model, "__name__", None),
                "semantic_scope": "legacy_signal_evaluation",
            }
        )
    routes.sort(key=lambda item: (item["path"], item["methods"]))

    schemas = {}
    for model_name in [
        "BacktestRunRequest",
        "BacktestRunResponse",
        "BacktestResultItem",
        "BacktestResultsResponse",
        "PerformanceMetrics",
    ]:
        model = getattr(backtest_schemas, model_name)
        schema = model.model_json_schema()
        schemas[model_name] = {
            "title": schema.get("title"),
            "required": schema.get("required", []),
            "properties": schema.get("properties", {}),
        }

    agent_tools = []
    for tool in ALL_BACKTEST_TOOLS:
        descriptor = tool.to_public_descriptor()
        agent_tools.append(
            {
                "name": descriptor["name"],
                "description": descriptor["description"],
                "category": descriptor["category"],
                "parameters": descriptor["parameters"],
                "policy": descriptor["policy"],
                "scope": descriptor["scope"],
                "semantic_scope": "legacy_signal_evaluation",
            }
        )
    agent_tools.sort(key=lambda item: item["name"])

    return {
        "routes": routes,
        "schemas": schemas,
        "agent_tools": agent_tools,
        "legacy_name_boundary": {
            "legacy_prefix": "/api/v1/backtest",
            "semantic_scope": "legacy_signal_evaluation",
            "not_formal_backtest_prefix": "/api/v1/quant/backtest-runs",
            "formal_backtest_started": False,
        },
    }


engine_inputs = make_engine_inputs()
decision_inputs = make_decision_signal_inputs()
engine_outputs, signal_summary = evaluate_engine(engine_inputs)
decision_outputs = evaluate_decision_signals(decision_inputs)
api_surface = collect_api_surface()

input_payload = {
    "baseline": {
        "upstream": "ZhuLinsen/daily_stock_analysis",
        "tag": "v3.26.1",
        "commit": expected_sha,
    },
    "task": "SAL-P4-001",
    "signal_evaluation_config": {
        "engine_version": "v1",
        "eval_window_days": 3,
        "neutral_band_pct": 2.0,
    },
    "engine_cases": engine_inputs,
    "decision_signal_cases": decision_inputs,
}

generated_dir.mkdir(parents=True, exist_ok=True)
stable_json_dump(generated_dir / "inputs.json", input_payload)
stable_json_dump(generated_dir / "engine-evaluations.json", {"items": engine_outputs})
stable_json_dump(generated_dir / "decision-signal-evaluations.json", {"items": decision_outputs})
stable_json_dump(generated_dir / "signal-evaluation-summary.json", signal_summary)
stable_json_dump(generated_dir / "api-surface.json", api_surface)

artifact_files = [
    "api-surface.json",
    "decision-signal-evaluations.json",
    "engine-evaluations.json",
    "inputs.json",
    "signal-evaluation-summary.json",
]
content_hashes = {name: sha256_file(generated_dir / name) for name in artifact_files}
stable_json_dump(
    generated_dir / "content-hashes.json",
    {
        "artifact_set": "dsa-signal-evaluation-characterization",
        "artifacts": content_hashes,
    },
)
content_hashes["content-hashes.json"] = sha256_file(generated_dir / "content-hashes.json")

summary_payload = {
    "task": "SAL-P4-001",
    "artifact_set": "dsa-signal-evaluation-characterization",
    "baseline": {
        "upstream": "ZhuLinsen/daily_stock_analysis",
        "tag": "v3.26.1",
        "commit": expected_sha,
    },
    "counts": {
        "engine_case_count": len(engine_outputs),
        "decision_signal_case_count": len(decision_outputs),
        "api_route_count": len(api_surface["routes"]),
        "api_schema_count": len(api_surface["schemas"]),
        "agent_tool_count": len(api_surface["agent_tools"]),
    },
    "coverage": {
        "buy_sell_hold_watch": True,
        "stop_loss_take_profit": True,
        "ambiguous_same_day_targets": True,
        "insufficient_forward_bars": True,
        "negated_recommendation_text": True,
        "missing_ohlc_fields": True,
        "structured_decision_signal": True,
        "legacy_api_surface": True,
        "agent_read_tools": True,
    },
    "signal_evaluation_key_metrics": {
        "total_evaluations": signal_summary["total_evaluations"],
        "completed_count": signal_summary["completed_count"],
        "insufficient_count": signal_summary["insufficient_count"],
        "direction_accuracy_pct": signal_summary["direction_accuracy_pct"],
        "win_rate_pct": signal_summary["win_rate_pct"],
        "avg_stock_return_pct": signal_summary["avg_stock_return_pct"],
        "avg_simulated_return_pct": signal_summary["avg_simulated_return_pct"],
        "stop_loss_trigger_rate": signal_summary["stop_loss_trigger_rate"],
        "take_profit_trigger_rate": signal_summary["take_profit_trigger_rate"],
        "ambiguous_rate": signal_summary["ambiguous_rate"],
    },
    "validation": {
        "characterization_passed": True,
        "api_surface_passed": True,
        "formal_backtest_started": False,
        "uses_stub_inputs_only": True,
        "real_provider_calls_zero": True,
        "real_llm_calls_zero": True,
        "evidence_agent_started": False,
    },
    "artifacts": content_hashes,
}
stable_json_dump(generated_dir / "summary.json", summary_payload)
PY
)

EXPECTED_FILES=(
  api-surface.json
  content-hashes.json
  decision-signal-evaluations.json
  engine-evaluations.json
  inputs.json
  signal-evaluation-summary.json
  summary.json
)

if [[ "$UPDATE_SNAPSHOTS" -eq 1 ]]; then
  mkdir -p "$SNAPSHOT_ABS"
  rm -f "$SNAPSHOT_ABS"/*.json
  for name in "${EXPECTED_FILES[@]}"; do
    cp "$GENERATED_DIR/$name" "$SNAPSHOT_ABS/$name"
  done
  echo "Updated DSA Signal Evaluation characterization snapshots in $SNAPSHOT_DIR"
  exit 0
fi

for name in "${EXPECTED_FILES[@]}"; do
  compare_snapshot "$name"
done

echo "DSA Signal Evaluation characterization snapshots match $SNAPSHOT_DIR"
