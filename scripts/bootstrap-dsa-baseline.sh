#!/usr/bin/env bash
set -euo pipefail

BASELINE_TAG="upstream/dsa-v3.26.1"
EXPECTED_SHA="e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
WORKTREE_PATH=".worktrees/dsa-v3.26.1"
CACHE_ROOT=".cache/dsa-p0"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_PYTHON=0
INSTALL_CI_TOOLS=0
INSTALL_WEB=0
INSTALL_DESKTOP=0
VALIDATE_ONLY=0

usage() {
  cat <<'USAGE'
Usage: scripts/bootstrap-dsa-baseline.sh [options]

Options:
  --tag <ref>             Baseline tag/ref to materialize.
  --worktree <path>       Worktree destination. Default: .worktrees/dsa-v3.26.1
  --cache-root <path>     Dependency cache root. Default: .cache/dsa-p0
  --python <command>      Python executable. Default: $PYTHON_BIN or python3
  --install-python        Install runtime Python dependencies into local venv.
  --install-ci-tools      Install CI test/lint tooling into local venv.
  --install-web           Run npm ci for apps/dsa-web using local npm cache.
  --install-desktop       Run npm ci for apps/dsa-desktop using local npm cache.
  --validate-only         Verify baseline tag/worktree only; do not mutate.
  -h, --help              Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)
      BASELINE_TAG="$2"
      shift 2
      ;;
    --worktree)
      WORKTREE_PATH="$2"
      shift 2
      ;;
    --cache-root)
      CACHE_ROOT="$2"
      shift 2
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --install-python)
      INSTALL_PYTHON=1
      shift
      ;;
    --install-ci-tools)
      INSTALL_CI_TOOLS=1
      shift
      ;;
    --install-web)
      INSTALL_WEB=1
      shift
      ;;
    --install-desktop)
      INSTALL_DESKTOP=1
      shift
      ;;
    --validate-only)
      VALIDATE_ONLY=1
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

step() {
  echo "==> $1"
}

require_cmd git

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

BASELINE_SHA="$(git rev-parse "$BASELINE_TAG")"
if [[ "$BASELINE_SHA" != "$EXPECTED_SHA" ]]; then
  echo "Baseline tag $BASELINE_TAG resolves to $BASELINE_SHA, expected $EXPECTED_SHA" >&2
  exit 1
fi

if [[ "$VALIDATE_ONLY" -eq 1 ]]; then
  echo "Baseline tag OK: $BASELINE_TAG -> $BASELINE_SHA"
  if [[ -e "$WORKTREE_PATH" ]]; then
    echo "Existing worktree HEAD: $(git -C "$WORKTREE_PATH" rev-parse HEAD)"
  fi
  exit 0
fi

step "materialize baseline worktree"
if [[ -e "$WORKTREE_PATH" ]]; then
  WORKTREE_SHA="$(git -C "$WORKTREE_PATH" rev-parse HEAD)"
  if [[ "$WORKTREE_SHA" != "$EXPECTED_SHA" ]]; then
    echo "Worktree $WORKTREE_PATH is at $WORKTREE_SHA, expected $EXPECTED_SHA" >&2
    exit 1
  fi
  echo "Worktree already present at expected SHA."
else
  mkdir -p "$(dirname "$WORKTREE_PATH")"
  git worktree add --detach "$WORKTREE_PATH" "$BASELINE_TAG"
fi

step "prepare local env file"
if [[ ! -f "$WORKTREE_PATH/.env" && -f "$WORKTREE_PATH/.env.example" ]]; then
  cp "$WORKTREE_PATH/.env.example" "$WORKTREE_PATH/.env"
  echo "Created $WORKTREE_PATH/.env from .env.example. Fill secrets manually before real provider runs."
else
  echo "No env file change needed."
fi

if [[ "$INSTALL_PYTHON" -eq 1 || "$INSTALL_CI_TOOLS" -eq 1 ]]; then
  require_cmd "$PYTHON_BIN"
  step "create Python virtualenv"
  mkdir -p "$CACHE_ROOT"
  VENV_PATH="$CACHE_ROOT/venv"
  if [[ ! -d "$VENV_PATH" ]]; then
    "$PYTHON_BIN" -m venv "$VENV_PATH"
  fi
  PYTHON_IN_VENV="$VENV_PATH/bin/python"
  export PIP_CACHE_DIR="$CACHE_ROOT/pip"
  "$PYTHON_IN_VENV" -m pip install --upgrade pip
  if [[ "$INSTALL_PYTHON" -eq 1 ]]; then
    "$PYTHON_IN_VENV" -m pip install -r "$WORKTREE_PATH/requirements.txt"
  fi
  if [[ "$INSTALL_CI_TOOLS" -eq 1 ]]; then
    "$PYTHON_IN_VENV" -m pip install -r "$WORKTREE_PATH/.github/requirements-ci.txt"
  fi
fi

if [[ "$INSTALL_WEB" -eq 1 ]]; then
  require_cmd npm
  step "install DSA web dependencies"
  export npm_config_cache="$CACHE_ROOT/npm-web"
  (cd "$WORKTREE_PATH/apps/dsa-web" && npm ci)
fi

if [[ "$INSTALL_DESKTOP" -eq 1 ]]; then
  require_cmd npm
  step "install DSA desktop dependencies"
  export npm_config_cache="$CACHE_ROOT/npm-desktop"
  (cd "$WORKTREE_PATH/apps/dsa-desktop" && npm ci)
fi

echo "DSA baseline bootstrap complete."
echo "Worktree: $REPO_ROOT/$WORKTREE_PATH"
echo "Cache: $REPO_ROOT/$CACHE_ROOT"
