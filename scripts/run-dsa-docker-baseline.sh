#!/usr/bin/env bash
set -euo pipefail

BASELINE_TAG="upstream/dsa-v3.26.1"
EXPECTED_SHA="e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
WORKTREE_PATH=".worktrees/dsa-v3.26.1"
CACHE_ROOT=".cache/dsa-p0"
BUILD_CONTEXT=""
ARTIFACT_DIR=""
IMAGE_TAG="serenity-dsa-p0:sal-p0-007"
HOST_PORT="18000"
BUILD_ONLY=0
KEEP_CONTAINERS=0

usage() {
  cat <<'USAGE'
Usage: scripts/run-dsa-docker-baseline.sh [options]

Build and smoke-test the locked DSA Docker baseline.

Options:
  --worktree <path>        Locked DSA worktree. Default: .worktrees/dsa-v3.26.1
  --cache-root <path>      Cache/artifact root. Default: .cache/dsa-p0
  --image-tag <tag>        Docker image tag. Default: serenity-dsa-p0:sal-p0-007
  --host-port <port>       Host port for server smoke. Default: 18000
  --alphasift-wheel <path> Explicit AlphaSift wheel path
  --build-only             Build image and skip container smoke
  --keep-containers        Leave smoke containers running after the script exits
  -h, --help               Show this help
USAGE
}

ALPHASIFT_WHEEL="${ALPHASIFT_WHEEL:-}"

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
    --image-tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --host-port)
      HOST_PORT="$2"
      shift 2
      ;;
    --alphasift-wheel)
      ALPHASIFT_WHEEL="$2"
      shift 2
      ;;
    --build-only)
      BUILD_ONLY=1
      shift
      ;;
    --keep-containers)
      KEEP_CONTAINERS=1
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

repo_root() {
  git rev-parse --show-toplevel
}

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

find_alphasift_wheel() {
  if [[ -n "$ALPHASIFT_WHEEL" ]]; then
    printf '%s\n' "$ALPHASIFT_WHEEL"
    return
  fi

  find "$CACHE_ROOT/pip/wheels" -name 'alphasift-*.whl' -type f 2>/dev/null \
    | sort \
    | tail -n 1
}

cleanup_containers() {
  if [[ "$KEEP_CONTAINERS" -eq 1 ]]; then
    return
  fi
  docker rm -f dsa-p0-server dsa-p0-analyzer >/dev/null 2>&1 || true
}

require_cmd git
require_cmd docker
require_cmd rsync
require_cmd python3

REPO_ROOT="$(repo_root)"
cd "$REPO_ROOT"

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

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not available. Start Docker Desktop/OrbStack and retry." >&2
  exit 1
fi

ALPHASIFT_WHEEL="$(find_alphasift_wheel)"
if [[ -z "$ALPHASIFT_WHEEL" || ! -f "$ALPHASIFT_WHEEL" ]]; then
  echo "AlphaSift wheel not found under $CACHE_ROOT/pip/wheels." >&2
  echo "Run scripts/bootstrap-dsa-baseline.sh --python <python3.11> --install-ci-tools first, or pass --alphasift-wheel." >&2
  exit 1
fi

BUILD_CONTEXT="$CACHE_ROOT/docker-build-context"
ARTIFACT_DIR="$CACHE_ROOT/docker-baseline-artifacts"
RUNTIME_DIR="$CACHE_ROOT/docker-runtime"
WHEEL_BASENAME="$(basename "$ALPHASIFT_WHEEL")"
WHEEL_SHA="$(sha256_file "$ALPHASIFT_WHEEL")"

step "prepare Docker build context"
rm -rf "$BUILD_CONTEXT"
mkdir -p "$BUILD_CONTEXT" "$ARTIFACT_DIR" "$RUNTIME_DIR/data" "$RUNTIME_DIR/logs" "$RUNTIME_DIR/reports" "$RUNTIME_DIR/longbridge_tokens"

rsync -a --delete \
  --exclude '.git' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude '**/node_modules' \
  --exclude '**/__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.venv' \
  --exclude 'venv' \
  --exclude 'dist' \
  --exclude 'build' \
  "$WORKTREE_PATH"/ "$BUILD_CONTEXT"/

mkdir -p "$BUILD_CONTEXT/vendor"
cp "$ALPHASIFT_WHEEL" "$BUILD_CONTEXT/vendor/$WHEEL_BASENAME"
printf '%s  %s\n' "$WHEEL_SHA" "vendor/$WHEEL_BASENAME" > "$ARTIFACT_DIR/alphasift-wheel.sha256"

python3 - "$BUILD_CONTEXT/requirements.txt" "vendor/$WHEEL_BASENAME" <<'PY'
from pathlib import Path
import sys

requirements = Path(sys.argv[1])
wheel_path = sys.argv[2]
lines = requirements.read_text(encoding="utf-8").splitlines()
replaced = False
out = []
for line in lines:
    if line.startswith("git+https://github.com/ZhuLinsen/alphasift.git@") and "#egg=alphasift" in line:
        out.append(wheel_path)
        replaced = True
    else:
        out.append(line)

if not replaced:
    raise SystemExit("requirements.txt did not contain the expected AlphaSift git dependency")

requirements.write_text("\n".join(out) + "\n", encoding="utf-8")
PY

python3 - "$BUILD_CONTEXT/docker/Dockerfile" <<'PY'
from pathlib import Path
import sys

dockerfile = Path(sys.argv[1])
text = dockerfile.read_text(encoding="utf-8")
needle = "COPY requirements.txt .\n"
replacement = "COPY requirements.txt .\nCOPY vendor/ ./vendor/\n"
if replacement not in text:
    if needle not in text:
        raise SystemExit("Dockerfile did not contain expected requirements COPY line")
    text = text.replace(needle, replacement, 1)
dockerfile.write_text(text, encoding="utf-8")
PY

if [[ -f "$WORKTREE_PATH/.env" ]]; then
  cp "$WORKTREE_PATH/.env" "$BUILD_CONTEXT/.env"
elif [[ -f "$WORKTREE_PATH/.env.example" ]]; then
  cp "$WORKTREE_PATH/.env.example" "$BUILD_CONTEXT/.env"
else
  : > "$BUILD_CONTEXT/.env"
fi

step "validate compose config"
(cd "$BUILD_CONTEXT" && docker compose -f docker/docker-compose.yml config >/dev/null)

step "build Docker image $IMAGE_TAG"
docker build --progress=plain -t "$IMAGE_TAG" -f "$BUILD_CONTEXT/docker/Dockerfile" "$BUILD_CONTEXT" \
  2>&1 | tee "$ARTIFACT_DIR/docker-build.log"

docker image inspect "$IMAGE_TAG" > "$ARTIFACT_DIR/image-inspect.json"
docker image inspect "$IMAGE_TAG" --format 'image_id={{.Id}} repo_digests={{join .RepoDigests ","}}' \
  | tee "$ARTIFACT_DIR/image-summary.txt"

if [[ "$BUILD_ONLY" -eq 1 ]]; then
  step "build-only requested; skipping container smoke"
  exit 0
fi

trap cleanup_containers EXIT
cleanup_containers

step "run server profile smoke"
docker run -d \
  --name dsa-p0-server \
  --env-file "$BUILD_CONTEXT/.env" \
  -e WEBUI_HOST=0.0.0.0 \
  -e API_PORT=8000 \
  -p "$HOST_PORT:8000" \
  -v "$REPO_ROOT/$RUNTIME_DIR/data:/app/data" \
  -v "$REPO_ROOT/$RUNTIME_DIR/logs:/app/logs" \
  -v "$REPO_ROOT/$RUNTIME_DIR/reports:/app/reports" \
  -v "$REPO_ROOT/$RUNTIME_DIR/longbridge_tokens:/home/dsa/.longbridge" \
  "$IMAGE_TAG" \
  python main.py --serve-only --host 0.0.0.0 --port 8000 >/dev/null

SERVER_HEALTH_URL="http://127.0.0.1:$HOST_PORT/api/health"
for _ in $(seq 1 60); do
  if curl -fsS "$SERVER_HEALTH_URL" > "$ARTIFACT_DIR/server-health.json"; then
    cat "$ARTIFACT_DIR/server-health.json"
    printf '\n'
    break
  fi
  sleep 2
done

if [[ ! -s "$ARTIFACT_DIR/server-health.json" ]]; then
  docker logs dsa-p0-server > "$ARTIFACT_DIR/server.log" 2>&1 || true
  echo "Server health check failed; see $ARTIFACT_DIR/server.log" >&2
  exit 1
fi

docker ps --filter name=dsa-p0-server --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' \
  | tee "$ARTIFACT_DIR/server-ps.txt"
docker logs --tail 200 dsa-p0-server > "$ARTIFACT_DIR/server.log" 2>&1 || true

step "run analyzer import smoke"
docker run --rm \
  --name dsa-p0-analyzer \
  --env-file "$BUILD_CONTEXT/.env" \
  -e SCHEDULE_ENABLED=false \
  -v "$REPO_ROOT/$RUNTIME_DIR/data:/app/data" \
  -v "$REPO_ROOT/$RUNTIME_DIR/logs:/app/logs" \
  -v "$REPO_ROOT/$RUNTIME_DIR/reports:/app/reports" \
  -v "$REPO_ROOT/$RUNTIME_DIR/longbridge_tokens:/home/dsa/.longbridge" \
  "$IMAGE_TAG" \
  python -c "from src.analyzer import GeminiAnalyzer; print('ok-analyzer')" \
  | tee "$ARTIFACT_DIR/analyzer-smoke.log"

step "Docker baseline smoke complete"
echo "Artifacts: $REPO_ROOT/$ARTIFACT_DIR"
