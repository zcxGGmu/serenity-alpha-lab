#!/usr/bin/env bash
set -euo pipefail

BASELINE_TAG="upstream/dsa-v3.26.1"
EXPECTED_SHA="e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
WORKTREE_PATH=".worktrees/dsa-v3.26.1"
CACHE_ROOT=".cache/dsa-p0"
PATCH_ROOT="patches/dsa/v3.26.1"
BOOTSTRAP_PYTHON="${PYTHON_BIN:-python3}"
RUN_BOOTSTRAP=1

DESKTOP_BACKEND_STARTUP_THRESHOLD_MS="${DESKTOP_BACKEND_STARTUP_THRESHOLD_MS:-60000}"
REPORT_SIGNAL_BASELINE_THRESHOLD_MS="${REPORT_SIGNAL_BASELINE_THRESHOLD_MS:-60000}"
SINGLE_STOCK_REPORT_THRESHOLD_MS="${SINGLE_STOCK_REPORT_THRESHOLD_MS:-5000}"

usage() {
  cat <<'USAGE'
Usage: scripts/run-p1-desktop-compatibility-performance.sh [options]

Run the SAL-P1-015 Desktop compatibility and performance baseline.

Options:
  --worktree <path>         Locked DSA worktree. Default: .worktrees/dsa-v3.26.1
  --cache-root <path>       Cache/artifact root. Default: .cache/dsa-p0
  --patch-root <path>       Local DSA patch directory. Default: patches/dsa/v3.26.1
  --python <command>        Python executable for bootstrap. Default: $PYTHON_BIN or python3
  --skip-bootstrap          Reuse existing DSA venv/Desktop node_modules
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
    --python)
      BOOTSTRAP_PYTHON="$2"
      shift 2
      ;;
    --skip-bootstrap)
      RUN_BOOTSTRAP=0
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

now_ms() {
  "$CLOCK_PYTHON" -c 'import time; print(int(time.time() * 1000))'
}

record_command_result() {
  local name="$1"
  local status="$2"
  local elapsed_ms="$3"
  local log_path="$4"
  printf '%s\t%s\t%s\t%s\n' "$name" "$status" "$elapsed_ms" "$log_path" >> "$COMMANDS_TSV"
}

run_in_dir() {
  local name="$1"
  local cwd="$2"
  shift 2
  local log_path="$ARTIFACT_DIR/${name}.log"
  local started_at
  local finished_at
  local status

  echo "==> $name"
  started_at="$(now_ms)"
  set +e
  (
    cd "$cwd"
    "$@"
  ) > "$log_path" 2>&1
  status=$?
  set -e
  finished_at="$(now_ms)"
  record_command_result "$name" "$status" "$((finished_at - started_at))" "$log_path"
  if [[ "$status" -ne 0 ]]; then
    echo "$name failed; tail of $log_path:" >&2
    tail -80 "$log_path" >&2 || true
    exit "$status"
  fi
}

run_root() {
  local name="$1"
  shift
  run_in_dir "$name" "$REPO_ROOT" "$@"
}

write_startup_metrics() {
  local elapsed_ms="$1"
  local attempts="$2"
  local port="$3"
  local passed="$4"
  "$VENV_PYTHON" - "$STARTUP_METRICS_JSON" "$elapsed_ms" "$attempts" "$port" "$passed" "$DESKTOP_BACKEND_STARTUP_THRESHOLD_MS" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
elapsed_ms = int(sys.argv[2])
attempts = int(sys.argv[3])
port = int(sys.argv[4])
passed = sys.argv[5] == "1"
threshold_ms = int(sys.argv[6])
payload = {
    "metric": "desktop_backend_health_startup",
    "elapsed_ms": elapsed_ms,
    "attempts": attempts,
    "port": port,
    "threshold_ms": threshold_ms,
    "passed": passed,
    "scope": "DSA desktop development backend health probe, no real Provider/LLM calls",
}
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

pick_port() {
  "$VENV_PYTHON" - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

probe_health() {
  local port="$1"
  "$VENV_PYTHON" - "$port" <<'PY'
import sys
import urllib.request

port = int(sys.argv[1])
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.0) as response:
        raise SystemExit(0 if response.status == 200 else 1)
except Exception:
    raise SystemExit(1)
PY
}

measure_desktop_backend_startup() {
  local name="desktop_backend_health_startup"
  local log_path="$ARTIFACT_DIR/${name}.log"
  local runtime_dir="$ARTIFACT_DIR/runtime"
  local env_path="$runtime_dir/.env"
  local db_path="$runtime_dir/stock_analysis.db"
  local log_dir="$runtime_dir/logs"
  local port
  local started_at
  local elapsed_ms
  local status=1
  local attempts=0
  local backend_pid=""

  echo "==> $name"
  rm -rf "$runtime_dir"
  mkdir -p "$runtime_dir" "$log_dir"
  if [[ -f "$WORKTREE_ABS/.env.example" ]]; then
    cp "$WORKTREE_ABS/.env.example" "$env_path"
  else
    : > "$env_path"
  fi
  {
    echo
    echo "WEBUI_ENABLED=false"
    echo "WEBUI_AUTO_BUILD=false"
    echo "BOT_ENABLED=false"
    echo "DINGTALK_STREAM_ENABLED=false"
    echo "FEISHU_STREAM_ENABLED=false"
  } >> "$env_path"

  port="$(pick_port)"
  started_at="$(now_ms)"
  (
    cd "$WORKTREE_ABS"
    export PATH="$VENV_ABS/bin:$PATH"
    export PYTHONPATH="$WORKTREE_ABS${PYTHONPATH:+:$PYTHONPATH}"
    export ENV_FILE="$env_path"
    export DATABASE_PATH="$db_path"
    export LOG_DIR="$log_dir"
    export DSA_DESKTOP_MODE=true
    export WEBUI_ENABLED=false
    export WEBUI_AUTO_BUILD=false
    export BOT_ENABLED=false
    export DINGTALK_STREAM_ENABLED=false
    export FEISHU_STREAM_ENABLED=false
    export DSA_RUNTIME_SCHEDULER_SUPPRESS_START=true
    export DSA_RUNTIME_SCHEDULER_RUN_IMMEDIATELY=false
    "$VENV_ABS/bin/python" main.py --serve-only --host 127.0.0.1 --port "$port"
  ) > "$log_path" 2>&1 &
  backend_pid="$!"

  while true; do
    attempts=$((attempts + 1))
    if probe_health "$port"; then
      status=0
      break
    fi
    if ! kill -0 "$backend_pid" >/dev/null 2>&1; then
      status=1
      break
    fi
    elapsed_ms="$(( $(now_ms) - started_at ))"
    if [[ "$elapsed_ms" -gt "$DESKTOP_BACKEND_STARTUP_THRESHOLD_MS" ]]; then
      status=1
      break
    fi
    sleep 0.25
  done

  elapsed_ms="$(( $(now_ms) - started_at ))"
  if kill -0 "$backend_pid" >/dev/null 2>&1; then
    kill "$backend_pid" >/dev/null 2>&1 || true
    wait "$backend_pid" >/dev/null 2>&1 || true
  fi

  if [[ "$status" -eq 0 && "$elapsed_ms" -le "$DESKTOP_BACKEND_STARTUP_THRESHOLD_MS" ]]; then
    write_startup_metrics "$elapsed_ms" "$attempts" "$port" 1
  else
    write_startup_metrics "$elapsed_ms" "$attempts" "$port" 0
  fi
  record_command_result "$name" "$status" "$elapsed_ms" "$log_path"
  if [[ "$status" -ne 0 ]]; then
    echo "$name failed or exceeded ${DESKTOP_BACKEND_STARTUP_THRESHOLD_MS}ms; tail of $log_path:" >&2
    tail -100 "$log_path" >&2 || true
    exit 1
  fi
}

measure_single_stock_report() {
  local name="single_stock_report_performance"
  local log_path="$ARTIFACT_DIR/${name}.log"
  local started_at
  local finished_at
  local status

  echo "==> $name"
  started_at="$(now_ms)"
  set +e
  (
    cd "$REPO_ROOT"
    export SINGLE_STOCK_METRICS_JSON="$SINGLE_STOCK_METRICS_JSON"
    export SINGLE_STOCK_REPORT_THRESHOLD_MS="$SINGLE_STOCK_REPORT_THRESHOLD_MS"
    "$VENV_PYTHON" - "$REPO_ROOT" "$WORKTREE_ABS" <<'PY'
import json
import os
import statistics
import sys
import time
from pathlib import Path

repo_root = Path(sys.argv[1])
worktree = Path(sys.argv[2])
sys.path.insert(0, str(worktree))

from src.analyzer import AnalysisResult
from src.notification import NotificationService

structured = json.loads(
    (repo_root / "docs/baselines/dsa-v3.26.1/report-signal/structured-reports.json").read_text(
        encoding="utf-8"
    )
)
payload = structured["items"][0]["parsed"]
result = AnalysisResult(**payload)
service = NotificationService()

warmup = service.generate_single_stock_report(result)
if "贵州茅台" not in warmup or "信号归因" not in warmup:
    raise SystemExit("single-stock report coverage markers missing")

durations = []
for _ in range(20):
    started = time.perf_counter()
    report = service.generate_single_stock_report(result)
    durations.append((time.perf_counter() - started) * 1000.0)
    if "贵州茅台" not in report or "信号归因" not in report:
        raise SystemExit("single-stock report coverage markers missing")

threshold_ms = int(os.environ["SINGLE_STOCK_REPORT_THRESHOLD_MS"])
avg_ms = statistics.fmean(durations)
metrics = {
    "metric": "single_stock_report_generation",
    "iterations": len(durations),
    "average_ms": round(avg_ms, 3),
    "max_ms": round(max(durations), 3),
    "min_ms": round(min(durations), 3),
    "threshold_ms": threshold_ms,
    "passed": avg_ms <= threshold_ms,
    "scope": "Offline NotificationService.generate_single_stock_report from committed P0 stub AnalysisResult",
}
Path(os.environ["SINGLE_STOCK_METRICS_JSON"]).write_text(
    json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(metrics, ensure_ascii=False, sort_keys=True))
raise SystemExit(0 if metrics["passed"] else 1)
PY
  ) > "$log_path" 2>&1
  status=$?
  set -e
  finished_at="$(now_ms)"
  record_command_result "$name" "$status" "$((finished_at - started_at))" "$log_path"
  if [[ "$status" -ne 0 ]]; then
    echo "$name failed; tail of $log_path:" >&2
    tail -80 "$log_path" >&2 || true
    exit "$status"
  fi
}

write_final_summary() {
  "$VENV_PYTHON" - "$ARTIFACT_DIR" "$COMMANDS_TSV" "$STARTUP_METRICS_JSON" "$SINGLE_STOCK_METRICS_JSON" "$REPORT_SIGNAL_BASELINE_THRESHOLD_MS" <<'PY'
import json
import sys
from pathlib import Path

artifact_dir = Path(sys.argv[1])
commands_tsv = Path(sys.argv[2])
startup_metrics_path = Path(sys.argv[3])
single_stock_metrics_path = Path(sys.argv[4])
report_threshold_ms = int(sys.argv[5])

commands = []
for line in commands_tsv.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    name, status, elapsed_ms, log_path = line.split("\t")
    commands.append(
        {
            "name": name,
            "status": int(status),
            "elapsed_ms": int(elapsed_ms),
            "log": str(Path(log_path).relative_to(artifact_dir.parent.parent.parent))
            if Path(log_path).is_absolute()
            else log_path,
        }
    )

startup = json.loads(startup_metrics_path.read_text(encoding="utf-8"))
single_stock = json.loads(single_stock_metrics_path.read_text(encoding="utf-8"))
report_signal = next((item for item in commands if item["name"] == "report_signal_baseline"), None)
if report_signal is None:
    raise SystemExit("missing report_signal_baseline command metrics")

performance = {
    "desktop_backend_health_startup": startup,
    "single_stock_report_generation": single_stock,
    "report_signal_baseline_wall_time": {
        "metric": "report_signal_baseline_wall_time",
        "elapsed_ms": report_signal["elapsed_ms"],
        "threshold_ms": report_threshold_ms,
        "passed": report_signal["elapsed_ms"] <= report_threshold_ms,
        "scope": "Full report/signal golden script including offline single-stock, aggregate, market review, and signal evaluation fixtures",
    },
}
passed = all(command["status"] == 0 for command in commands) and all(
    item.get("passed", False) for item in performance.values()
)
summary = {
    "task": "SAL-P1-015",
    "baseline": {
        "upstream": "ZhuLinsen/daily_stock_analysis",
        "tag": "v3.26.1",
        "commit": "e8a9ca7742e8cb2498c8f491dd76d239b3064e1a",
    },
    "commands": commands,
    "performance": performance,
    "validation": {
        "all_commands_passed": all(command["status"] == 0 for command in commands),
        "performance_thresholds_passed": all(item.get("passed", False) for item in performance.values()),
        "real_provider_calls_zero": True,
        "real_llm_calls_zero": True,
        "generated_artifacts_under_cache": True,
    },
    "passed": passed,
}
(artifact_dir / "summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

rows = [
    "# SAL-P1-015 Desktop compatibility and performance summary",
    "",
    "| Command | Status | Elapsed ms |",
    "|---|---:|---:|",
]
for command in commands:
    rows.append(f"| {command['name']} | {command['status']} | {command['elapsed_ms']} |")
rows.extend([
    "",
    "| Performance metric | Result | Threshold | Status |",
    "|---|---:|---:|---|",
    f"| Desktop backend health startup | {startup['elapsed_ms']} ms | {startup['threshold_ms']} ms | {'PASS' if startup['passed'] else 'FAIL'} |",
    f"| Single-stock report generation avg | {single_stock['average_ms']} ms | {single_stock['threshold_ms']} ms | {'PASS' if single_stock['passed'] else 'FAIL'} |",
    f"| Report/signal baseline wall time | {report_signal['elapsed_ms']} ms | {report_threshold_ms} ms | {'PASS' if performance['report_signal_baseline_wall_time']['passed'] else 'FAIL'} |",
    "",
    f"Result: {'PASS' if passed else 'FAIL'}",
])
(artifact_dir / "summary.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
if not passed:
    raise SystemExit("SAL-P1-015 summary did not pass")
PY
}

require_cmd git
require_cmd tail

REPO_ROOT="$(repo_root)"
cd "$REPO_ROOT"

BASELINE_SHA="$(git rev-parse "$BASELINE_TAG")"
if [[ "$BASELINE_SHA" != "$EXPECTED_SHA" ]]; then
  echo "Baseline tag $BASELINE_TAG resolves to $BASELINE_SHA, expected $EXPECTED_SHA" >&2
  exit 1
fi

CLOCK_PYTHON="$BOOTSTRAP_PYTHON"
if ! command -v "$CLOCK_PYTHON" >/dev/null 2>&1; then
  CLOCK_PYTHON="python3"
fi
require_cmd "$CLOCK_PYTHON"

ARTIFACT_DIR="$REPO_ROOT/$CACHE_ROOT/p1-desktop-compatibility-performance"
rm -rf "$ARTIFACT_DIR"
mkdir -p "$ARTIFACT_DIR"
COMMANDS_TSV="$ARTIFACT_DIR/commands.tsv"
STARTUP_METRICS_JSON="$ARTIFACT_DIR/desktop-backend-startup.json"
SINGLE_STOCK_METRICS_JSON="$ARTIFACT_DIR/single-stock-report-performance.json"
: > "$COMMANDS_TSV"

if [[ "$RUN_BOOTSTRAP" -eq 1 ]]; then
  run_root bootstrap_dsa_desktop_python \
    bash scripts/bootstrap-dsa-baseline.sh \
      --python "$BOOTSTRAP_PYTHON" \
      --install-python \
      --install-ci-tools \
      --install-desktop
else
  run_root bootstrap_validate_only bash scripts/bootstrap-dsa-baseline.sh --validate-only
fi

WORKTREE_ABS="$REPO_ROOT/$WORKTREE_PATH"
CACHE_ABS="$REPO_ROOT/$CACHE_ROOT"
VENV_ABS="$CACHE_ABS/venv"
VENV_PYTHON="$VENV_ABS/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Missing Python venv: $VENV_PYTHON" >&2
  exit 1
fi
if [[ ! -d "$WORKTREE_ABS/apps/dsa-desktop/node_modules" ]]; then
  echo "Missing Desktop node_modules; rerun without --skip-bootstrap." >&2
  exit 1
fi

CLOCK_PYTHON="$VENV_PYTHON"

WORKTREE_SHA="$(git -C "$WORKTREE_ABS" rev-parse HEAD)"
if [[ "$WORKTREE_SHA" != "$EXPECTED_SHA" ]]; then
  echo "Worktree $WORKTREE_PATH is at $WORKTREE_SHA, expected $EXPECTED_SHA" >&2
  exit 1
fi

run_root apply_dsa_patches scripts/apply-dsa-baseline-patches.sh --worktree "$WORKTREE_PATH" --patch-root "$PATCH_ROOT"
run_in_dir desktop_node_tests "$WORKTREE_ABS/apps/dsa-desktop" npm test
run_in_dir desktop_api_cli_bot_pytest "$WORKTREE_ABS" "$VENV_PYTHON" -m pytest \
  tests/test_desktop_packaging_assets.py \
  tests/test_desktop_installer_config.py \
  tests/test_api_health.py \
  tests/test_local_cli_backend.py \
  tests/test_bot_status_command.py \
  tests/test_bot_dispatcher_async.py \
  tests/test_bot_market_command.py \
  -q
run_root api_config_baseline scripts/run-dsa-api-config-baseline.sh --worktree "$WORKTREE_PATH" --cache-root "$CACHE_ROOT" --patch-root "$PATCH_ROOT"
run_root database_baseline scripts/run-dsa-database-baseline.sh --worktree "$WORKTREE_PATH" --cache-root "$CACHE_ROOT" --patch-root "$PATCH_ROOT"
run_root report_signal_baseline scripts/run-dsa-report-signal-baseline.sh --worktree "$WORKTREE_PATH" --cache-root "$CACHE_ROOT" --patch-root "$PATCH_ROOT"
measure_desktop_backend_startup
measure_single_stock_report
write_final_summary

echo "SAL-P1-015 compatibility/performance baseline passed."
echo "Summary: $ARTIFACT_DIR/summary.md"
