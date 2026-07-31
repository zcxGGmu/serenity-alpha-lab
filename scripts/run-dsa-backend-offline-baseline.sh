#!/usr/bin/env bash
set -uo pipefail

BASELINE_TAG="upstream/dsa-v3.26.1"
EXPECTED_SHA="e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
WORKTREE_PATH=".worktrees/dsa-v3.26.1"
CACHE_ROOT=".cache/dsa-p0"
PATCH_ROOT="patches/dsa/v3.26.1"
PHASE="all"

usage() {
  cat <<'USAGE'
Usage: scripts/run-dsa-backend-offline-baseline.sh [options]

Run and record the locked DSA backend offline gate baseline.

Options:
  --worktree <path>     Locked DSA worktree. Default: .worktrees/dsa-v3.26.1
  --cache-root <path>   Cache/artifact root. Default: .cache/dsa-p0
  --patch-root <path>   Local DSA patch directory. Default: patches/dsa/v3.26.1
  --phase <phase>       all, syntax, flake8, deterministic, collect, offline-tests
  -h, --help            Show this help
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
    --phase)
      PHASE="$2"
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

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found on PATH: $1" >&2
    exit 1
  fi
}

repo_root() {
  git rev-parse --show-toplevel
}

phase_enabled() {
  local target="$1"
  [[ "$PHASE" == "all" || "$PHASE" == "$target" ]]
}

run_phase() {
  local name="$1"
  shift
  local log_path="$ARTIFACT_DIR/$name.log"
  local start_ts
  local end_ts
  local duration
  local status

  start_ts="$(date +%s)"
  {
    echo "==> $name"
    echo "command: $*"
    echo "started_at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  } | tee "$log_path"

  (
    cd "$WORKTREE_ABS" || exit 1
    export PATH="$VENV_ABS/bin:$PATH"
    export PYTHONPATH="$WORKTREE_ABS${PYTHONPATH:+:$PYTHONPATH}"
    "$@"
  ) >>"$log_path" 2>&1
  status=$?

  end_ts="$(date +%s)"
  duration=$((end_ts - start_ts))
  {
    echo "finished_at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "exit_code: $status"
    echo "duration_seconds: $duration"
  } | tee -a "$log_path"

  printf '%s\t%s\t%s\t%s\n' "$name" "$status" "$duration" "$log_path" >> "$SUMMARY_TSV"
  if [[ "$status" -ne 0 ]]; then
    FAILED_PHASES+=("$name")
  fi
}

write_environment() {
  {
    echo "# DSA backend offline gate environment"
    echo
    echo "baseline_tag=$BASELINE_TAG"
    echo "expected_sha=$EXPECTED_SHA"
    echo "worktree=$WORKTREE_ABS"
    echo "cache_root=$CACHE_ABS"
    echo "artifact_dir=$ARTIFACT_DIR"
    echo
    "$VENV_ABS/bin/python" --version
    "$VENV_ABS/bin/python" -m pip --version
    "$VENV_ABS/bin/python" - <<'PY'
import importlib.metadata

packages = ["pytest", "flake8", "alphasift"]
for package in packages:
    try:
        print(f"{package}={importlib.metadata.version(package)}")
    except importlib.metadata.PackageNotFoundError:
        print(f"{package}=NOT_INSTALLED")
PY
  } > "$ARTIFACT_DIR/environment.txt"

  (
    cd "$WORKTREE_ABS" || exit 1
    {
      echo "python_test_files=$(find tests -path '*/__pycache__/*' -prune -o -name '*.py' -type f -print | wc -l | tr -d ' ')"
      echo "pytest_markers=$(sed -n '/^markers =/,$p' setup.cfg | sed -n '1,12p' | tr '\n' ';')"
    }
  ) > "$ARTIFACT_DIR/test-inventory.txt"
}

write_summary_markdown() {
  {
    echo "# DSA backend offline gate summary"
    echo
    echo "| Phase | Exit | Duration seconds | Log |"
    echo "|---|---:|---:|---|"
    while IFS=$'\t' read -r name status duration log_path; do
      echo "| $name | $status | $duration | ${log_path#$REPO_ROOT/} |"
    done < "$SUMMARY_TSV"
    echo
    if [[ "${#FAILED_PHASES[@]}" -eq 0 ]]; then
      echo "Result: PASS"
    else
      echo "Result: FAIL"
      echo
      echo "Failed phases: ${FAILED_PHASES[*]}"
    fi
  } > "$ARTIFACT_DIR/summary.md"
}

case "$PHASE" in
  all|syntax|flake8|deterministic|collect|offline-tests)
    ;;
  *)
    echo "Unknown phase: $PHASE" >&2
    usage >&2
    exit 2
    ;;
esac

require_cmd git
require_cmd date

REPO_ROOT="$(repo_root)"
cd "$REPO_ROOT" || exit 1

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

VENV_PATH="$CACHE_ROOT/venv"
if [[ ! -x "$VENV_PATH/bin/python" ]]; then
  echo "Missing Python venv: $VENV_PATH" >&2
  echo "Run scripts/bootstrap-dsa-baseline.sh --python <python3.11> --install-ci-tools first." >&2
  exit 1
fi

WORKTREE_ABS="$REPO_ROOT/$WORKTREE_PATH"
CACHE_ABS="$REPO_ROOT/$CACHE_ROOT"
VENV_ABS="$REPO_ROOT/$VENV_PATH"
ARTIFACT_DIR="$CACHE_ABS/backend-offline-artifacts"
SUMMARY_TSV="$ARTIFACT_DIR/summary.tsv"
FAILED_PHASES=()

mkdir -p "$ARTIFACT_DIR"
rm -f "$ARTIFACT_DIR"/*.log "$ARTIFACT_DIR"/summary.tsv "$ARTIFACT_DIR"/summary.md
write_environment
: > "$SUMMARY_TSV"

if phase_enabled "syntax"; then
  run_phase syntax bash scripts/ci_gate.sh syntax
fi

if phase_enabled "flake8"; then
  run_phase flake8 bash scripts/ci_gate.sh flake8
fi

if phase_enabled "deterministic"; then
  run_phase deterministic bash scripts/ci_gate.sh deterministic
fi

if phase_enabled "collect"; then
  run_phase collect "$VENV_ABS/bin/python" -m pytest -m "not network" --collect-only -q
fi

if phase_enabled "offline-tests"; then
  run_phase offline-tests bash scripts/ci_gate.sh offline-tests
fi

write_summary_markdown
cat "$ARTIFACT_DIR/summary.md"

if [[ "${#FAILED_PHASES[@]}" -ne 0 ]]; then
  exit 1
fi
