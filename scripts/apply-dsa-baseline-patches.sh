#!/usr/bin/env bash
set -euo pipefail

EXPECTED_SHA="e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
WORKTREE_PATH=".worktrees/dsa-v3.26.1"
PATCH_ROOT="patches/dsa/v3.26.1"
CHECK_ONLY=0

usage() {
  cat <<'USAGE'
Usage: scripts/apply-dsa-baseline-patches.sh [options]

Apply registered local compatibility patches to the locked DSA baseline worktree.

Options:
  --worktree <path>     Locked DSA worktree. Default: .worktrees/dsa-v3.26.1
  --patch-root <path>   Patch directory. Default: patches/dsa/v3.26.1
  --check-only          Validate whether patches can be applied; do not mutate.
  -h, --help            Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --worktree)
      WORKTREE_PATH="$2"
      shift 2
      ;;
    --patch-root)
      PATCH_ROOT="$2"
      shift 2
      ;;
    --check-only)
      CHECK_ONLY=1
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

require_cmd git

REPO_ROOT="$(repo_root)"
cd "$REPO_ROOT"

if [[ ! -d "$WORKTREE_PATH" ]]; then
  echo "Missing DSA worktree: $WORKTREE_PATH" >&2
  exit 1
fi

WORKTREE_SHA="$(git -C "$WORKTREE_PATH" rev-parse HEAD)"
if [[ "$WORKTREE_SHA" != "$EXPECTED_SHA" ]]; then
  echo "Worktree $WORKTREE_PATH is at $WORKTREE_SHA, expected $EXPECTED_SHA" >&2
  exit 1
fi

if [[ ! -d "$PATCH_ROOT" ]]; then
  echo "No DSA baseline patches found at $PATCH_ROOT."
  exit 0
fi

PATCHES=()
while IFS= read -r patch_path; do
  PATCHES+=("$patch_path")
done < <(find "$PATCH_ROOT" -maxdepth 1 -type f -name '*.patch' | sort)
if [[ "${#PATCHES[@]}" -eq 0 ]]; then
  echo "No DSA baseline patches found at $PATCH_ROOT."
  exit 0
fi

for patch_path in "${PATCHES[@]}"; do
  patch_abs="$REPO_ROOT/$patch_path"
  patch_name="$(basename "$patch_path")"
  if git -C "$WORKTREE_PATH" apply --check --reverse "$patch_abs" >/dev/null 2>&1; then
    echo "Patch already applied: $patch_name"
    continue
  fi
  if ! git -C "$WORKTREE_PATH" apply --check "$patch_abs"; then
    echo "Patch cannot be applied cleanly: $patch_name" >&2
    exit 1
  fi
  if [[ "$CHECK_ONLY" -eq 1 ]]; then
    echo "Patch can be applied: $patch_name"
  else
    git -C "$WORKTREE_PATH" apply "$patch_abs"
    echo "Applied patch: $patch_name"
  fi
done
