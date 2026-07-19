#!/usr/bin/env bash
set -euo pipefail

BASELINE_TAG="upstream/dsa-v3.26.1"
EXPECTED_SHA="e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
WORKTREE_PATH=".worktrees/dsa-v3.26.1"
CACHE_ROOT=".cache/dsa-p0"
PATCH_ROOT="patches/dsa/v3.26.1"
SNAPSHOT_DIR="docs/baselines/dsa-v3.26.1/database"
UPDATE_SNAPSHOTS=0

usage() {
  cat <<'USAGE'
Usage: scripts/run-dsa-database-baseline.sh [options]

Generate and verify the locked DSA SQLite schema and sanitized fixture baseline.

Options:
  --worktree <path>         Locked DSA worktree. Default: .worktrees/dsa-v3.26.1
  --cache-root <path>       Cache/artifact root. Default: .cache/dsa-p0
  --patch-root <path>       Local DSA patch directory. Default: patches/dsa/v3.26.1
  --snapshot-dir <path>     Committed snapshot directory. Default: docs/baselines/dsa-v3.26.1/database
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
ARTIFACT_DIR="$CACHE_ABS/database-baseline-artifacts"
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
  export SQLITE_WAL_ENABLED=false
  export DSA_DESKTOP_MODE=false
  export DSA_RUNTIME_SCHEDULER_SUPPRESS_START=true
  export DSA_RUNTIME_SCHEDULER_RUN_IMMEDIATELY=false
  export STOCK_INDEX_REMOTE_UPDATE_ENABLED=false
  "$VENV_ABS/bin/python" - "$GENERATED_DIR" "$WORKTREE_ABS" "$EXPECTED_SHA" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

generated_dir = Path(sys.argv[1])
worktree = Path(sys.argv[2])
expected_sha = sys.argv[3]
fixture_path = generated_dir / "fixture.sqlite"

if fixture_path.exists():
    fixture_path.unlink()

from src.config import Config
from src.storage import (
    AgentProviderTurn,
    AlertCooldownRecord,
    AlertNotificationRecord,
    AlertRuleRecord,
    AlertTriggerRecord,
    AnalysisHistory,
    BacktestResult,
    BacktestSummary,
    Base,
    ConversationMessage,
    ConversationSummary,
    CURRENT_SCHEMA_VERSION,
    DatabaseManager,
    DatabaseSchemaMigration,
    DecisionSignalFeedbackRecord,
    DecisionSignalOutcomeRecord,
    DecisionSignalRecord,
    FundamentalSnapshot,
    IntelligenceItem,
    IntelligenceSource,
    LLMUsage,
    NewsIntel,
    PortfolioAccount,
    PortfolioCashLedger,
    PortfolioCorporateAction,
    PortfolioDailySnapshot,
    PortfolioFxRate,
    PortfolioPosition,
    PortfolioPositionLot,
    PortfolioTrade,
    StockDaily,
)


FIXED_DT = datetime(2026, 1, 5, 9, 30, 0)
FIXED_DT_2 = datetime(2026, 1, 5, 15, 5, 0)
FIXED_DATE = date(2026, 1, 5)


def stable_json_dump(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def strip_trailing_whitespace(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines())


def sqlite_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    return value


def table_rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    columns = [row[1] for row in conn.execute(f'PRAGMA table_xinfo("{table}")').fetchall()]
    order_column = "id" if "id" in columns else columns[0]
    rows = conn.execute(f'SELECT * FROM "{table}" ORDER BY "{order_column}"').fetchall()
    return [
        {columns[index]: sqlite_value(value) for index, value in enumerate(row)}
        for row in rows
    ]


def table_content_hash(conn: sqlite3.Connection, table: str) -> str:
    payload = json.dumps(table_rows(conn, table), ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def redact_sqlite_dump_line(line: str) -> str:
    # The fixture is synthetic, but keep a defensive pass for future edits.
    secret_key_re = re.compile(
        r"(?i)(api[_-]?key|token|secret|password|sendkey|webhook|cookie)(['\"]?\s*[,=:]\s*)[^,'\"\s)]+"
    )
    return secret_key_re.sub(r"\1\2[REDACTED]", line)


def assert_no_forbidden_fixture_content(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    forbidden_patterns = [
        r"sk-[A-Za-z0-9_-]{8,}",
        r"AIza[0-9A-Za-z_-]{20,}",
        r"ghp_[0-9A-Za-z_]{20,}",
        r"AKIA[0-9A-Z]{12,}",
        re.escape(str(Path.home())),
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, text):
            raise AssertionError(f"forbidden fixture content matched: {pattern}")


def reset_dsa_singletons() -> None:
    try:
        DatabaseManager.reset_instance()
    finally:
        if hasattr(Config, "reset_instance"):
            Config.reset_instance()


def create_fixture() -> None:
    reset_dsa_singletons()
    os.environ["DATABASE_PATH"] = str(fixture_path)
    db = DatabaseManager(db_url=f"sqlite:///{fixture_path}")

    with db.session_scope() as session:
        migration = session.get(DatabaseSchemaMigration, CURRENT_SCHEMA_VERSION)
        if migration is not None:
            migration.applied_at = FIXED_DT

        session.add_all(
            [
                StockDaily(
                    code="600519",
                    date=FIXED_DATE,
                    open=1680.0,
                    high=1701.0,
                    low=1668.0,
                    close=1695.0,
                    volume=1000000.0,
                    amount=1695000000.0,
                    pct_chg=1.2,
                    ma5=1688.0,
                    ma10=1675.0,
                    ma20=1650.0,
                    volume_ratio=1.1,
                    data_source="fixture-provider",
                    created_at=FIXED_DT,
                    updated_at=FIXED_DT,
                ),
                StockDaily(
                    code="000001",
                    date=FIXED_DATE,
                    open=10.1,
                    high=10.5,
                    low=10.0,
                    close=10.4,
                    volume=2000000.0,
                    amount=20800000.0,
                    pct_chg=0.8,
                    ma5=10.2,
                    ma10=10.0,
                    ma20=9.8,
                    volume_ratio=0.9,
                    data_source="fixture-provider",
                    created_at=FIXED_DT,
                    updated_at=FIXED_DT,
                ),
            ]
        )

        source = IntelligenceSource(
            name="fixture-rss",
            source_type="rss",
            url="https://example.invalid/finance/rss.xml",
            enabled=True,
            scope_type="market",
            scope_value="cn",
            market="cn",
            description="Synthetic source for P0 database baseline.",
            last_status="ok",
            last_fetched_at=FIXED_DT,
            created_at=FIXED_DT,
            updated_at=FIXED_DT,
        )
        session.add(source)
        session.flush()
        session.add(
            IntelligenceItem(
                source_id=source.id,
                source_name="fixture-rss",
                source_type="rss",
                title="Synthetic fixture market headline",
                summary="Synthetic non-personal market context.",
                url="https://example.invalid/news/fixture-market-headline",
                source="fixture",
                published_at=FIXED_DT,
                fetched_at=FIXED_DT_2,
                scope_type="market",
                scope_value="cn",
                market="cn",
                raw_payload=json_dumps({"fixture": True, "symbols": ["600519", "000001"]}),
            )
        )
        session.add(
            NewsIntel(
                query_id="fixture-query-analysis",
                code="600519",
                name="Fixture Moutai",
                dimension="latest_news",
                query="fixture 600519 latest news",
                provider="fixture",
                title="Synthetic single stock fixture news",
                snippet="Synthetic snippet with no personal data.",
                url="https://example.invalid/news/600519",
                source="fixture",
                published_date=FIXED_DT,
                fetched_at=FIXED_DT_2,
                query_source="ci",
                requester_platform="fixture",
                requester_user_id="fixture-user",
                requester_user_name="fixture",
                requester_chat_id="fixture-chat",
                requester_message_id="fixture-message",
                requester_query="synthetic query",
            )
        )
        session.add(
            FundamentalSnapshot(
                query_id="fixture-query-analysis",
                code="600519",
                payload=json_dumps({"pe_ttm": 24.5, "roe": 0.28, "as_of": "2026-01-05"}),
                source_chain=json_dumps(["fixture-provider"]),
                coverage=json_dumps({"fundamental": "synthetic"}),
                created_at=FIXED_DT,
            )
        )

        analysis = AnalysisHistory(
            query_id="fixture-query-analysis",
            code="600519",
            name="Fixture Moutai",
            report_type="single_stock",
            sentiment_score=72,
            operation_advice="hold",
            trend_prediction="neutral_up",
            analysis_summary="Synthetic single stock analysis summary.",
            raw_result=json_dumps(
                {
                    "code": "600519",
                    "name": "Fixture Moutai",
                    "report_markdown": "# Fixture Single Stock Report\n\nSynthetic baseline report.",
                    "decision": {"action": "hold", "confidence": 0.72},
                }
            ),
            news_content="Synthetic sanitized news content.",
            context_snapshot=json_dumps({"market": "cn", "fixture": True, "source": "sanitized"}),
            ideal_buy=1660.0,
            secondary_buy=1620.0,
            stop_loss=1580.0,
            take_profit=1780.0,
            created_at=FIXED_DT,
        )
        market_review = AnalysisHistory(
            query_id="fixture-query-market-review",
            code="MARKET",
            name="Fixture Market",
            report_type="market_review",
            sentiment_score=55,
            operation_advice="observe",
            trend_prediction="range_bound",
            analysis_summary="Synthetic market review summary.",
            raw_result=json_dumps({"report_markdown": "# Fixture Market Review\n\nSynthetic baseline report."}),
            news_content="Synthetic market news.",
            context_snapshot=json_dumps({"market": "cn", "fixture": True}),
            created_at=FIXED_DT_2,
        )
        session.add_all([analysis, market_review])
        session.flush()

        signal = DecisionSignalRecord(
            stock_code="600519",
            stock_name="Fixture Moutai",
            market="cn",
            source_type="analysis",
            source_agent="fixture-agent",
            source_report_id=analysis.id,
            trace_id="fixture-trace-001",
            decision_profile="balanced",
            market_phase="range",
            trigger_source="fixture",
            action="hold",
            action_label="Hold",
            confidence=0.72,
            score=72,
            horizon="swing",
            entry_low=1660.0,
            entry_high=1700.0,
            stop_loss=1580.0,
            target_price=1780.0,
            invalidation="Synthetic invalidation condition.",
            watch_conditions="Synthetic watch conditions.",
            reason="Synthetic signal reason.",
            risk_summary="Synthetic risk summary.",
            catalyst_summary="Synthetic catalyst summary.",
            evidence_json=json_dumps([{"kind": "fixture", "ref": "analysis_history"}]),
            data_quality_summary_json=json_dumps({"level": "fixture"}),
            plan_quality="complete",
            status="active",
            expires_at=datetime(2026, 2, 5, 0, 0, 0),
            created_at=FIXED_DT,
            updated_at=FIXED_DT,
            metadata_json=json_dumps({"decision_profile": "balanced", "fixture": True}),
        )
        session.add(signal)
        session.flush()

        session.add_all(
            [
                BacktestResult(
                    analysis_history_id=analysis.id,
                    code="600519",
                    analysis_date=FIXED_DATE,
                    eval_window_days=10,
                    engine_version="fixture-v1",
                    eval_status="completed",
                    evaluated_at=FIXED_DT_2,
                    operation_advice="hold",
                    position_recommendation="long",
                    start_price=1695.0,
                    end_close=1710.0,
                    max_high=1782.0,
                    min_low=1660.0,
                    stock_return_pct=0.885,
                    direction_expected="not_down",
                    direction_correct=True,
                    outcome="win",
                    stop_loss=1580.0,
                    take_profit=1780.0,
                    hit_stop_loss=False,
                    hit_take_profit=True,
                    first_hit="take_profit",
                    first_hit_date=date(2026, 1, 12),
                    first_hit_trading_days=5,
                    simulated_entry_price=1695.0,
                    simulated_exit_price=1780.0,
                    simulated_exit_reason="take_profit",
                    simulated_return_pct=5.015,
                ),
                BacktestSummary(
                    scope="stock",
                    code="600519",
                    eval_window_days=10,
                    engine_version="fixture-v1",
                    computed_at=FIXED_DT_2,
                    total_evaluations=1,
                    completed_count=1,
                    insufficient_count=0,
                    long_count=1,
                    cash_count=0,
                    win_count=1,
                    loss_count=0,
                    neutral_count=0,
                    direction_accuracy_pct=100.0,
                    win_rate_pct=100.0,
                    neutral_rate_pct=0.0,
                    avg_stock_return_pct=0.885,
                    avg_simulated_return_pct=5.015,
                    stop_loss_trigger_rate=0.0,
                    take_profit_trigger_rate=100.0,
                    ambiguous_rate=0.0,
                    avg_days_to_first_hit=5.0,
                    advice_breakdown_json=json_dumps({"hold": 1}),
                    diagnostics_json=json_dumps({"fixture": True}),
                ),
            ]
        )
        session.add(
            DecisionSignalOutcomeRecord(
                signal_id=signal.id,
                horizon="swing",
                engine_version="fixture-v1",
                eval_status="completed",
                outcome="win",
                direction_expected="not_down",
                direction_correct=True,
                unable_reason=None,
                anchor_date=FIXED_DATE,
                eval_window_days=10,
                start_price=1695.0,
                end_close=1710.0,
                max_high=1782.0,
                min_low=1660.0,
                stock_return_pct=0.885,
                action="hold",
                market="cn",
                market_phase="range",
                source_type="analysis",
                source_agent="fixture-agent",
                plan_quality="complete",
                data_quality_level="fixture",
                holding_state="held",
                created_at=FIXED_DT_2,
                updated_at=FIXED_DT_2,
            )
        )
        session.add(
            DecisionSignalFeedbackRecord(
                signal_id=signal.id,
                feedback_value="useful",
                reason_code="fixture",
                note="Synthetic reviewer feedback.",
                source="fixture",
                created_at=FIXED_DT_2,
                updated_at=FIXED_DT_2,
            )
        )

        account = PortfolioAccount(
            owner_id="fixture-owner",
            name="Fixture Account",
            broker="fixture-broker",
            market="cn",
            base_currency="CNY",
            is_active=True,
            created_at=FIXED_DT,
            updated_at=FIXED_DT,
        )
        session.add(account)
        session.flush()
        trade = PortfolioTrade(
            account_id=account.id,
            trade_uid="fixture-trade-001",
            symbol="600519",
            market="cn",
            currency="CNY",
            trade_date=FIXED_DATE,
            side="buy",
            quantity=100.0,
            price=1695.0,
            fee=5.0,
            tax=0.0,
            note="Synthetic buy event.",
            dedup_hash="fixture-dedup-001",
            created_at=FIXED_DT,
        )
        session.add(trade)
        session.flush()
        session.add_all(
            [
                PortfolioCashLedger(
                    account_id=account.id,
                    event_date=FIXED_DATE,
                    direction="in",
                    amount=200000.0,
                    currency="CNY",
                    note="Synthetic deposit.",
                    created_at=FIXED_DT,
                ),
                PortfolioCorporateAction(
                    account_id=account.id,
                    symbol="600519",
                    market="cn",
                    currency="CNY",
                    effective_date=date(2026, 1, 20),
                    action_type="cash_dividend",
                    cash_dividend_per_share=1.0,
                    note="Synthetic corporate action.",
                    created_at=FIXED_DT,
                ),
                PortfolioPosition(
                    account_id=account.id,
                    cost_method="fifo",
                    symbol="600519",
                    market="cn",
                    currency="CNY",
                    quantity=100.0,
                    avg_cost=1695.0,
                    total_cost=169500.0,
                    last_price=1710.0,
                    market_value_base=171000.0,
                    unrealized_pnl_base=1500.0,
                    valuation_currency="CNY",
                    updated_at=FIXED_DT_2,
                ),
                PortfolioPositionLot(
                    account_id=account.id,
                    cost_method="fifo",
                    symbol="600519",
                    market="cn",
                    currency="CNY",
                    open_date=FIXED_DATE,
                    remaining_quantity=100.0,
                    unit_cost=1695.0,
                    source_trade_id=trade.id,
                    updated_at=FIXED_DT_2,
                ),
                PortfolioDailySnapshot(
                    account_id=account.id,
                    snapshot_date=FIXED_DATE,
                    cost_method="fifo",
                    base_currency="CNY",
                    total_cash=30500.0,
                    total_market_value=171000.0,
                    total_equity=201500.0,
                    unrealized_pnl=1500.0,
                    realized_pnl=0.0,
                    fee_total=5.0,
                    tax_total=0.0,
                    fx_stale=False,
                    payload=json_dumps({"fixture": True, "positions": 1}),
                    created_at=FIXED_DT_2,
                    updated_at=FIXED_DT_2,
                ),
                PortfolioFxRate(
                    from_currency="CNY",
                    to_currency="CNY",
                    rate_date=FIXED_DATE,
                    rate=1.0,
                    source="fixture",
                    is_stale=False,
                    updated_at=FIXED_DT,
                ),
            ]
        )

        user_message = ConversationMessage(
            session_id="fixture-session-001",
            role="user",
            content="Synthetic user asks for a fixture analysis.",
            created_at=FIXED_DT,
        )
        assistant_message = ConversationMessage(
            session_id="fixture-session-001",
            role="assistant",
            content="Synthetic assistant response for fixture analysis.",
            created_at=FIXED_DT_2,
        )
        session.add_all([user_message, assistant_message])
        session.flush()
        session.add_all(
            [
                ConversationSummary(
                    session_id="fixture-session-001",
                    summary="Synthetic conversation summary.",
                    covered_message_id=user_message.id,
                    source_message_count=1,
                    estimated_tokens=42,
                    created_at=FIXED_DT_2,
                    updated_at=FIXED_DT_2,
                ),
                AgentProviderTurn(
                    session_id="fixture-session-001",
                    run_id="fixture-run-001",
                    provider="fixture-provider",
                    model="fixture-model",
                    anchor_user_message_id=user_message.id,
                    anchor_assistant_message_id=assistant_message.id,
                    messages_json=json_dumps(
                        [
                            {"role": "user", "content_hmac": "fixture-user-hmac"},
                            {"role": "assistant", "content_hmac": "fixture-assistant-hmac"},
                        ]
                    ),
                    contains_reasoning=False,
                    contains_tool_calls=True,
                    contains_thinking_blocks=False,
                    must_roundtrip=True,
                    estimated_tokens=84,
                    created_at=FIXED_DT_2,
                ),
            ]
        )

        session.add(
            LLMUsage(
                call_type="analysis",
                model="fixture-model",
                stock_code="600519",
                provider="fixture-provider",
                prompt_tokens=120,
                completion_tokens=80,
                total_tokens=200,
                provider_usage_json=json_dumps({"prompt_tokens": 120, "completion_tokens": 80}),
                provider_usage_schema_name="fixture_usage",
                provider_usage_schema_version="1",
                provider_usage_observed_at="2026-01-05T09:30:00Z",
                normalized_prompt_tokens=120,
                normalized_completion_tokens=80,
                normalized_total_tokens=200,
                normalized_cache_read_tokens=0,
                normalized_cache_write_tokens=0,
                normalized_cache_miss_tokens=120,
                normalized_uncached_input_tokens=120,
                normalized_cache_eligible_input_tokens=0,
                normalized_cache_hit_ratio=0.0,
                normalized_cache_write_ratio=0.0,
                cache_capability="none",
                cache_eligibility="not_eligible",
                cache_observation="fixture",
                estimated_prefix_tokens=0,
                provider_reported_prompt_tokens=120,
                provider_reported_cached_tokens=0,
                provider_min_cache_tokens=0,
                eligibility_confidence="high",
                messages_hmac="fixture-messages-hmac",
                system_message_hmac="fixture-system-hmac",
                user_message_hmac="fixture-user-hmac",
                hmac_key_version="fixture-v1",
                hmac_domain="fixture",
                hash_scope="message_shape",
                language="zh",
                market_group="cn",
                analysis_mode="single_stock",
                legacy_prompt_mode="fixture",
                skill_config_hmac="fixture-skill-hmac",
                transport="offline",
                message_count=2,
                estimated_total_prompt_tokens=120,
                approx_common_prefix_chars=0,
                approx_common_prefix_tokens=0,
                known_dynamic_marker_positions=json_dumps([]),
                called_at=FIXED_DT_2,
            )
        )

        alert_rule = AlertRuleRecord(
            name="fixture-price-alert",
            target_scope="single_symbol",
            target="600519",
            alert_type="price_above",
            parameters=json_dumps({"threshold": 1780.0}),
            severity="warning",
            enabled=True,
            source="fixture",
            cooldown_policy=json_dumps({"minutes": 30}),
            notification_policy=json_dumps({"channels": ["fixture"]}),
            created_at=FIXED_DT,
            updated_at=FIXED_DT,
        )
        session.add(alert_rule)
        session.flush()
        trigger = AlertTriggerRecord(
            rule_id=alert_rule.id,
            target="600519",
            observed_value=1781.0,
            threshold=1780.0,
            reason="Synthetic alert trigger.",
            data_source="fixture-provider",
            data_timestamp=FIXED_DT_2,
            triggered_at=FIXED_DT_2,
            status="triggered",
            diagnostics=json_dumps({"fixture": True}),
        )
        session.add(trigger)
        session.flush()
        session.add_all(
            [
                AlertNotificationRecord(
                    trigger_id=trigger.id,
                    channel="fixture",
                    attempt=1,
                    success=True,
                    retryable=False,
                    latency_ms=12,
                    diagnostics=json_dumps({"fixture": True}),
                    created_at=FIXED_DT_2,
                ),
                AlertCooldownRecord(
                    rule_id=alert_rule.id,
                    rule_key="fixture-price-alert",
                    target="600519",
                    severity="warning",
                    last_triggered_at=FIXED_DT_2,
                    cooldown_until=datetime(2026, 1, 5, 15, 35, 0),
                    reason="Synthetic cooldown.",
                    state="active",
                    updated_at=FIXED_DT_2,
                ),
            ]
        )

    reset_dsa_singletons()


def collect_metadata() -> dict[str, Any]:
    with sqlite3.connect(fixture_path) as conn:
        conn.row_factory = sqlite3.Row
        table_names = [
            row["name"]
            for row in conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        index_names = [
            row["name"]
            for row in conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        tables: dict[str, Any] = {}
        for table in table_names:
            columns = [
                {
                    "cid": row["cid"],
                    "name": row["name"],
                    "type": row["type"],
                    "notnull": bool(row["notnull"]),
                    "default": row["dflt_value"],
                    "pk": row["pk"],
                    "hidden": row["hidden"],
                }
                for row in conn.execute(f'PRAGMA table_xinfo("{table}")')
            ]
            indexes = []
            for index in conn.execute(f'PRAGMA index_list("{table}")'):
                index_name = index["name"]
                indexes.append(
                    {
                        "name": index_name,
                        "unique": bool(index["unique"]),
                        "origin": index["origin"],
                        "partial": bool(index["partial"]),
                        "columns": [
                            row["name"]
                            for row in conn.execute(f'PRAGMA index_xinfo("{index_name}")')
                            if row["name"] is not None and row["key"]
                        ],
                    }
                )
            foreign_keys = [
                {
                    "id": row["id"],
                    "seq": row["seq"],
                    "table": row["table"],
                    "from": row["from"],
                    "to": row["to"],
                    "on_update": row["on_update"],
                    "on_delete": row["on_delete"],
                    "match": row["match"],
                }
                for row in conn.execute(f'PRAGMA foreign_key_list("{table}")')
            ]
            create_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()["sql"]
            tables[table] = {
                "columns": columns,
                "indexes": sorted(indexes, key=lambda item: item["name"]),
                "foreign_keys": foreign_keys,
                "row_count": conn.execute(f'SELECT COUNT(*) AS n FROM "{table}"').fetchone()["n"],
                "create_sql": create_sql,
                "content_sha256": table_content_hash(conn, table),
            }
        return {
            "baseline": {
                "upstream": "ZhuLinsen/daily_stock_analysis",
                "tag": "v3.26.1",
                "commit": expected_sha,
                "schema_version": CURRENT_SCHEMA_VERSION,
            },
            "sqlite": {
                "user_version": conn.execute("PRAGMA user_version").fetchone()[0],
                "journal_mode": conn.execute("PRAGMA journal_mode").fetchone()[0],
                "foreign_keys": conn.execute("PRAGMA foreign_keys").fetchone()[0],
                "page_count": conn.execute("PRAGMA page_count").fetchone()[0],
                "page_size": conn.execute("PRAGMA page_size").fetchone()[0],
            },
            "table_count": len(table_names),
            "index_count": len(index_names),
            "tables": tables,
        }


def write_schema_sql() -> None:
    with sqlite3.connect(fixture_path) as conn:
        rows = conn.execute(
            """
            SELECT type, name, sql FROM sqlite_master
            WHERE sql IS NOT NULL
              AND name NOT LIKE 'sqlite_%'
              AND type IN ('table', 'index', 'view', 'trigger')
            ORDER BY
              CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 WHEN 'view' THEN 2 ELSE 3 END,
              name
            """
        ).fetchall()
    statements = []
    for object_type, name, sql in rows:
        statements.append(f"-- {object_type}: {name}\n{strip_trailing_whitespace(sql)};")
    (generated_dir / "schema.sql").write_text("\n\n".join(statements) + "\n", encoding="utf-8")


def write_fixture_sql_dump() -> None:
    with sqlite3.connect(fixture_path) as conn:
        conn.row_factory = sqlite3.Row
        table_names = [
            row["name"]
            for row in conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        table_sql = [
            row["sql"]
            for row in conn.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type='table' AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        index_sql = [
            row["sql"]
            for row in conn.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type='index' AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        lines = ["PRAGMA foreign_keys=OFF;", "BEGIN TRANSACTION;"]
        for sql in table_sql:
            lines.append(f"{strip_trailing_whitespace(sql)};")
        for table in table_names:
            columns = [
                row["name"]
                for row in conn.execute(f'PRAGMA table_xinfo("{table}")')
                if row["hidden"] == 0
            ]
            if not columns:
                continue
            order_column = "id" if "id" in columns else columns[0]
            rows = conn.execute(f'SELECT * FROM "{table}" ORDER BY "{order_column}"').fetchall()
            quoted_columns = ", ".join(f'"{column}"' for column in columns)
            for row in rows:
                values = ", ".join(
                    conn.execute("SELECT quote(?)", (row[column],)).fetchone()[0]
                    for column in columns
                )
                lines.append(f'INSERT INTO "{table}" ({quoted_columns}) VALUES({values});')
        for sql in index_sql:
            lines.append(f"{strip_trailing_whitespace(sql)};")
        lines.extend(["COMMIT;", "PRAGMA foreign_keys=ON;"])
        dump_text = "\n".join(lines)
        dump_text = "\n".join(
            redact_sqlite_dump_line(line).rstrip()
            for line in dump_text.splitlines()
        )
    (generated_dir / "fixture.sql").write_text(dump_text + "\n", encoding="utf-8")


def verify_fixture_sql_round_trip() -> dict[str, bool]:
    restored_path = generated_dir / "fixture-restored.sqlite"
    if restored_path.exists():
        restored_path.unlink()
    fixture_sql = (generated_dir / "fixture.sql").read_text(encoding="utf-8")
    source_metadata = collect_metadata()
    source_counts = {
        table: info["row_count"]
        for table, info in source_metadata["tables"].items()
    }
    source_hashes = {
        table: info["content_sha256"]
        for table, info in source_metadata["tables"].items()
    }
    with sqlite3.connect(restored_path) as conn:
        conn.executescript(fixture_sql)
        conn.execute("PRAGMA foreign_keys=ON")
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise AssertionError(f"fixture SQL foreign key violations: {violations}")
        restored_counts = {}
        restored_hashes = {}
        table_names = [
            row[0]
            for row in conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        for table in table_names:
            restored_counts[table] = conn.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            restored_hashes[table] = table_content_hash(conn, table)
        if restored_counts != source_counts:
            raise AssertionError(
                "fixture SQL restore row counts differ: "
                f"source={source_counts} restored={restored_counts}"
            )
        if restored_hashes != source_hashes:
            raise AssertionError(
                "fixture SQL restore content hashes differ: "
                f"source={source_hashes} restored={restored_hashes}"
            )
    restored_path.unlink()
    return {
        "fixture_sql_round_trip_passed": True,
        "foreign_key_check_passed": True,
        "restored_row_counts_match": True,
        "restored_content_hashes_match": True,
    }


def write_fixture_summary(metadata: dict[str, Any]) -> dict[str, Any]:
    required_coverage = {
        "analysis": ["analysis_history", "news_intel", "fundamental_snapshot"],
        "signal_evaluation": ["backtest_results", "backtest_summaries", "decision_signals", "decision_signal_outcomes", "decision_signal_feedback"],
        "portfolio": ["portfolio_accounts", "portfolio_trades", "portfolio_cash_ledger", "portfolio_positions", "portfolio_daily_snapshots"],
        "sessions": ["conversation_messages", "conversation_summaries", "agent_provider_turns"],
        "llm_usage": ["llm_usage"],
        "schema_migration": ["schema_migrations"],
    }
    table_row_counts = {
        table: info["row_count"]
        for table, info in metadata["tables"].items()
    }
    coverage = {}
    for category, tables in required_coverage.items():
        coverage[category] = {
            "tables": tables,
            "row_counts": {table: table_row_counts.get(table, 0) for table in tables},
            "covered": all(table_row_counts.get(table, 0) > 0 for table in tables),
        }
    auth_note = {
        "covered": False,
        "reason": "DSA v3.26.1 auth password/session state is file-backed or signed-cookie based, not a SQLite table; no auth secrets are included in this database fixture.",
    }
    summary = {
        "baseline": metadata["baseline"],
        "fixture": {
            "kind": "sanitized-synthetic-sqlite-history-db",
            "database_file": "fixture.sqlite",
            "sql_dump": "fixture.sql",
            "contains_real_user_data": False,
            "contains_secrets": False,
            "fixed_clock": "2026-01-05T09:30:00",
        },
        "coverage": coverage,
        "auth_session_persistence": auth_note,
        "table_count": metadata["table_count"],
        "index_count": metadata["index_count"],
        "row_counts": table_row_counts,
        "total_rows": sum(table_row_counts.values()),
    }
    stable_json_dump(generated_dir / "fixture-summary.json", summary)
    return summary


def write_content_hashes(metadata: dict[str, Any]) -> dict[str, Any]:
    hashes = {
        "files": {},
        "tables": {
            table: info["content_sha256"]
            for table, info in metadata["tables"].items()
        },
    }
    for path in sorted(generated_dir.iterdir()):
        if path.is_file() and path.name != "content-hashes.json":
            if path.name == "fixture.sqlite" or path.name.endswith("-wal") or path.name.endswith("-shm"):
                continue
            hashes["files"][path.name] = sha256_file(path)
    stable_json_dump(generated_dir / "content-hashes.json", hashes)
    return hashes


def write_summary(
    metadata: dict[str, Any],
    fixture_summary: dict[str, Any],
    hashes: dict[str, Any],
    round_trip_validation: dict[str, bool],
) -> None:
    summary = {
        "baseline": metadata["baseline"],
        "generated_at": "2026-07-19T00:00:00Z",
        "artifact_set": "database-schema-fixture",
        "artifacts": {
            "fixture.sql": hashes["files"]["fixture.sql"],
            "schema.sql": hashes["files"]["schema.sql"],
            "schema-metadata.json": hashes["files"]["schema-metadata.json"],
            "fixture-summary.json": hashes["files"]["fixture-summary.json"],
            "content-hashes.json": sha256_file(generated_dir / "content-hashes.json"),
        },
        "runtime_artifacts": {
            "fixture.sqlite": "Generated under .cache/dsa-p0/database-baseline-artifacts/generated/fixture.sqlite; omitted from committed snapshots because SQLite page/header bytes are not stable across identical content rebuilds.",
        },
        "table_count": metadata["table_count"],
        "index_count": metadata["index_count"],
        "total_fixture_rows": fixture_summary["total_rows"],
        "coverage": fixture_summary["coverage"],
        "auth_session_persistence": fixture_summary["auth_session_persistence"],
        "validation": {
            "required_coverage_passed": all(item["covered"] for item in fixture_summary["coverage"].values()),
            "secret_scan_passed": True,
            "schema_migration_version": CURRENT_SCHEMA_VERSION,
            **round_trip_validation,
        },
    }
    stable_json_dump(generated_dir / "summary.json", summary)


def validate(
    metadata: dict[str, Any],
    fixture_summary: dict[str, Any],
    round_trip_validation: dict[str, bool],
) -> None:
    expected_tables = set(Base.metadata.tables)
    actual_tables = set(metadata["tables"])
    missing_tables = sorted(expected_tables - actual_tables)
    if missing_tables:
        raise AssertionError(f"missing metadata tables: {missing_tables}")
    uncovered = [
        category
        for category, info in fixture_summary["coverage"].items()
        if not info["covered"]
    ]
    if uncovered:
        raise AssertionError(f"fixture coverage gaps: {uncovered}")
    schema_rows = metadata["tables"].get("schema_migrations", {}).get("row_count", 0)
    if schema_rows < 1:
        raise AssertionError("schema_migrations table has no baseline row")
    if not all(round_trip_validation.values()):
        raise AssertionError(f"fixture SQL round-trip validation failed: {round_trip_validation}")
    assert_no_forbidden_fixture_content(generated_dir / "fixture.sql")


generated_dir.mkdir(parents=True, exist_ok=True)
create_fixture()
write_schema_sql()
write_fixture_sql_dump()
round_trip_validation = verify_fixture_sql_round_trip()
metadata = collect_metadata()
stable_json_dump(generated_dir / "schema-metadata.json", metadata)
fixture_summary = write_fixture_summary(metadata)
hashes = write_content_hashes(metadata)
write_summary(metadata, fixture_summary, hashes, round_trip_validation)
validate(metadata, fixture_summary, round_trip_validation)
PY
)

SNAPSHOT_NAMES=(
  fixture.sql
  schema.sql
  schema-metadata.json
  fixture-summary.json
  content-hashes.json
  summary.json
)

if [[ "$UPDATE_SNAPSHOTS" -eq 1 ]]; then
  mkdir -p "$SNAPSHOT_ABS"
  for snapshot_name in "${SNAPSHOT_NAMES[@]}"; do
    cp "$GENERATED_DIR/$snapshot_name" "$SNAPSHOT_ABS/$snapshot_name"
  done
  echo "Updated database baseline snapshots in $SNAPSHOT_DIR"
else
  for snapshot_name in "${SNAPSHOT_NAMES[@]}"; do
    if ! compare_snapshot "$snapshot_name"; then
      echo "Database baseline snapshot changed: $snapshot_name" >&2
      echo "Inspect $DIFF_DIR and rerun with --update-snapshots if intentional." >&2
      exit 1
    fi
  done
  echo "Database baseline snapshots match $SNAPSHOT_DIR"
fi

echo "Generated artifacts: $GENERATED_DIR"
