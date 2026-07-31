#!/usr/bin/env bash
set -euo pipefail

WORKTREE_PATH=".worktrees/dsa-v3.26.1"
PYTHON_PATH=".cache/dsa-p0/venv/bin/python"
ENV_FILE_PATH=".cache/dsa-p0/web-smoke/.env"
DATABASE_PATH=".cache/dsa-p0/web-smoke/stock_analysis.db"
SMOKE_PASSWORD="${DSA_WEB_SMOKE_PASSWORD:-p0-smoke-password}"

usage() {
  cat <<'USAGE'
Usage: scripts/seed-dsa-web-smoke-fixture.sh [options]

Prepare a local DSA Web smoke fixture database and auth password.

Options:
  --worktree <path>       Locked DSA worktree. Default: .worktrees/dsa-v3.26.1
  --python <path>         Python interpreter with DSA deps. Default: .cache/dsa-p0/venv/bin/python
  --env-file <path>       Env file consumed through ENV_FILE. Default: .cache/dsa-p0/web-smoke/.env
  --database <path>       SQLite database path. Default: .cache/dsa-p0/web-smoke/stock_analysis.db
  --password <password>   Local smoke password. Default: DSA_WEB_SMOKE_PASSWORD or p0-smoke-password
  -h, --help              Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --worktree)
      WORKTREE_PATH="$2"
      shift 2
      ;;
    --python)
      PYTHON_PATH="$2"
      shift 2
      ;;
    --env-file)
      ENV_FILE_PATH="$2"
      shift 2
      ;;
    --database)
      DATABASE_PATH="$2"
      shift 2
      ;;
    --password)
      SMOKE_PASSWORD="$2"
      shift 2
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

repo_root() {
  git rev-parse --show-toplevel
}

abs_path() {
  local path="$1"
  if [[ "$path" = /* ]]; then
    printf '%s\n' "$path"
  else
    printf '%s/%s\n' "$REPO_ROOT" "$path"
  fi
}

REPO_ROOT="$(repo_root)"
WORKTREE_ABS="$(abs_path "$WORKTREE_PATH")"
PYTHON_ABS="$(abs_path "$PYTHON_PATH")"
ENV_FILE_ABS="$(abs_path "$ENV_FILE_PATH")"
DATABASE_ABS="$(abs_path "$DATABASE_PATH")"

if [[ ! -d "$WORKTREE_ABS" ]]; then
  echo "Missing DSA worktree: $WORKTREE_ABS" >&2
  exit 1
fi

if [[ ! -x "$PYTHON_ABS" ]]; then
  echo "Missing executable Python interpreter: $PYTHON_ABS" >&2
  exit 1
fi

if [[ -z "${SMOKE_PASSWORD// }" ]]; then
  echo "Smoke password cannot be blank." >&2
  exit 1
fi

mkdir -p "$(dirname "$ENV_FILE_ABS")" "$(dirname "$DATABASE_ABS")"
umask 077
cat > "$ENV_FILE_ABS" <<ENV
ADMIN_AUTH_ENABLED=true
DATABASE_PATH=$DATABASE_ABS
WEBUI_AUTO_BUILD=false
ENV

(
  cd "$WORKTREE_ABS"
  ENV_FILE="$ENV_FILE_ABS" \
  DATABASE_PATH="$DATABASE_ABS" \
  ADMIN_AUTH_ENABLED=true \
  DSA_WEB_SMOKE_PASSWORD="$SMOKE_PASSWORD" \
  "$PYTHON_ABS" - <<'PY'
import os

from src.analyzer import AnalysisResult
from src.auth import overwrite_password
from src.storage import DatabaseManager

password = os.environ["DSA_WEB_SMOKE_PASSWORD"]
error = overwrite_password(password)
if error:
    raise SystemExit(error)

db = DatabaseManager()
query_id = "p0-web-smoke-fixture"
existing = db.get_analysis_history(query_id=query_id, code="600519", limit=1)
if existing:
    print(f"web-smoke-fixture-existing id={existing[0].id}")
    raise SystemExit(0)

result = AnalysisResult(
    code="600519",
    name="贵州茅台",
    sentiment_score=78,
    trend_prediction="看多",
    operation_advice="持有",
    analysis_summary="P0 Web smoke fixture: 基本面稳健，短期震荡。",
    technical_analysis="均线结构平稳。",
    fundamental_analysis="现金流稳健。",
    risk_warning="仅用于本地 smoke，不构成投资建议。",
    current_price=1800.0,
    change_pct=1.2,
    model_used="p0-smoke-fixture",
)
record_id = db.save_analysis_history(
    result=result,
    query_id=query_id,
    report_type="simple",
    news_content="P0 smoke 新闻摘要",
    context_snapshot={"source": "p0-web-smoke"},
    save_snapshot=True,
)
if record_id <= 0:
    raise SystemExit("Failed to seed analysis history fixture")
print(f"web-smoke-fixture-seeded id={record_id}")
PY
)

cat <<EOF
Web smoke fixture ready.
ENV_FILE=$ENV_FILE_ABS
DATABASE_PATH=$DATABASE_ABS
DSA_WEB_SMOKE_PASSWORD=$SMOKE_PASSWORD
EOF
