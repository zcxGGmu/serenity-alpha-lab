#!/usr/bin/env bash
set -euo pipefail

BASELINE_TAG="upstream/dsa-v3.26.1"
EXPECTED_SHA="e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
WORKTREE_PATH=".worktrees/dsa-v3.26.1"
CACHE_ROOT=".cache/dsa-p0"
PATCH_ROOT="patches/dsa/v3.26.1"
SNAPSHOT_DIR="docs/baselines/dsa-v3.26.1/api-config"
UPDATE_SNAPSHOTS=0

usage() {
  cat <<'USAGE'
Usage: scripts/run-dsa-api-config-baseline.sh [options]

Generate and verify the locked DSA API/config contract baseline.

Options:
  --worktree <path>         Locked DSA worktree. Default: .worktrees/dsa-v3.26.1
  --cache-root <path>       Cache/artifact root. Default: .cache/dsa-p0
  --patch-root <path>       Local DSA patch directory. Default: patches/dsa/v3.26.1
  --snapshot-dir <path>     Committed snapshot directory. Default: docs/baselines/dsa-v3.26.1/api-config
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

write_summary_markdown() {
  local result="$1"
  {
    echo "# DSA API/config contract baseline summary"
    echo
    echo "| Snapshot | Status |"
    echo "|---|---|"
    for snapshot_name in openapi.json config-schema.json config-env-inventory.json summary.json; do
      if [[ -f "$SNAPSHOT_ABS/$snapshot_name" ]]; then
        if cmp -s "$GENERATED_DIR/$snapshot_name" "$SNAPSHOT_ABS/$snapshot_name"; then
          echo "| $snapshot_name | matched |"
        else
          echo "| $snapshot_name | changed |"
        fi
      else
        echo "| $snapshot_name | missing |"
      fi
    done
    echo
    echo "Result: $result"
  } > "$ARTIFACT_DIR/summary.md"
}

require_cmd git
require_cmd date
require_cmd diff

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
SNAPSHOT_ABS="$REPO_ROOT/$SNAPSHOT_DIR"
ARTIFACT_DIR="$CACHE_ABS/api-config-contract-artifacts"
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
  "$VENV_ABS/bin/python" - "$GENERATED_DIR" "$WORKTREE_ABS" "$EXPECTED_SHA" <<'PY'
from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

generated_dir = Path(sys.argv[1])
worktree = Path(sys.argv[2])
expected_sha = sys.argv[3]

from api.app import create_app
from src.config import Config
from src.core.config_registry import (
    WEB_SETTINGS_HIDDEN_FROM_UI,
    build_schema_response,
)
from src.services.system_config_service import SystemConfigService


def stable_json_dump(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(worktree).as_posix()


def const_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def is_os_getenv_call(node: ast.Call) -> str | None:
    func = node.func
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "getenv"
        and isinstance(func.value, ast.Name)
        and func.value.id == "os"
        and node.args
    ):
        return const_string(node.args[0])
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "get"
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == "environ"
        and isinstance(func.value.value, ast.Name)
        and func.value.value.id == "os"
        and node.args
    ):
        return const_string(node.args[0])
    if (
        isinstance(func, ast.Attribute)
        and func.attr in {"pop", "setdefault"}
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == "environ"
        and isinstance(func.value.value, ast.Name)
        and func.value.value.id == "os"
        and node.args
    ):
        return const_string(node.args[0])
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "_resolve_env_value"
        and node.args
    ):
        return const_string(node.args[0])
    return None


def collect_code_env_sources() -> dict[str, list[dict[str, Any]]]:
    sources: dict[str, list[dict[str, Any]]] = defaultdict(list)
    scan_roots = [worktree / "api", worktree / "src", worktree / "data_provider", worktree / "main.py", worktree / "server.py", worktree / "webui.py"]
    python_files: list[Path] = []
    for root in scan_roots:
        if root.is_file():
            python_files.append(root)
        elif root.is_dir():
            python_files.extend(
                path
                for path in root.rglob("*.py")
                if "__pycache__" not in path.parts
            )
    for path in sorted(python_files):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            key: str | None = None
            if isinstance(node, ast.Call):
                key = is_os_getenv_call(node)
            elif isinstance(node, ast.Subscript):
                if (
                    isinstance(node.value, ast.Attribute)
                    and node.value.attr == "environ"
                    and isinstance(node.value.value, ast.Name)
                    and node.value.value.id == "os"
                ):
                    key = const_string(node.slice)
            if not key:
                continue
            sources[key.upper()].append(
                {
                    "path": rel(path),
                    "line": getattr(node, "lineno", None),
                }
            )
    return sources


def collect_env_example_sources() -> dict[str, dict[str, Any]]:
    env_example = worktree / ".env.example"
    result: dict[str, dict[str, Any]] = {}
    assignment_pattern = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]+)\s*=")
    if not env_example.is_file():
        return result
    for lineno, line in enumerate(env_example.read_text(encoding="utf-8").splitlines(), start=1):
        match = assignment_pattern.match(line)
        if not match:
            continue
        key = match.group(1).upper()
        commented = line.lstrip().startswith("#")
        result.setdefault(
            key,
            {
                "path": rel(env_example),
                "line": lineno,
                "commented": commented,
            },
        )
    return result


def source_files(locations: list[dict[str, Any]]) -> list[str]:
    return sorted({str(location["path"]) for location in locations})


def truncate_locations(locations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return locations[:12]


def normalize_default(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [normalize_default(item) for item in value]
    if isinstance(value, dict):
        return {str(key): normalize_default(item) for key, item in value.items()}
    return repr(value)


def dataclass_defaults() -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    for field_name, field in Config.__dataclass_fields__.items():
        if field_name.startswith("_"):
            continue
        if field.default is not dataclasses.MISSING:
            defaults[field_name] = normalize_default(field.default)
        elif field.default_factory is not dataclasses.MISSING:  # type: ignore[attr-defined]
            defaults[field_name] = normalize_default(field.default_factory())  # type: ignore[misc]
    return defaults


def infer_dataclass_field(key: str, defaults: dict[str, Any]) -> str | None:
    candidate = key.lower()
    if candidate in defaults:
        return candidate
    aliases = {
        "DISCORD_CHANNEL_ID": "discord_main_channel_id",
        "AGENT_STRATEGY_DIR": "agent_skill_dir",
        "AGENT_STRATEGY_AUTOWEIGHT": "agent_skill_autoweight",
        "AGENT_STRATEGY_ROUTING": "agent_skill_routing",
        "OPENAI_VISION_MODEL": "openai_vision_model",
        "RUN_IMMEDIATELY": "run_immediately",
    }
    return aliases.get(key)


def is_sensitive_key(key: str, registry_sensitive: bool) -> bool:
    if registry_sensitive:
        return True
    markers = (
        "API_KEY",
        "API_KEYS",
        "APP_KEY",
        "APP_SECRET",
        "BEARER_TOKEN",
        "BOT_TOKEN",
        "CLIENT_SECRET",
        "ENCODING_AES_KEY",
        "ENCRYPT_KEY",
        "HMAC_SECRET",
        "OAUTH_TOKEN_CACHE",
        "OAUTH_TOKEN",
        "PASSWORD",
        "SECRET",
        "SENDKEY",
        "TOKEN_CACHE",
        "WEBHOOK_URL",
        "WEBHOOK_URLS",
        "USER_KEY",
    )
    additional_sensitive = {
        "ALPHASIFT_INSTALL_SPEC",
        "CUSTOM_WEBHOOK_BODY_TEMPLATE",
        "LLM_HERMES_EXTRA_HEADERS",
    }
    if key in additional_sensitive or any(marker in key for marker in markers):
        return True
    return bool(re.search(r"(^|_)TOKEN($|_)", key))


def build_inventory() -> dict[str, Any]:
    schema = build_schema_response()
    registry_fields: dict[str, dict[str, Any]] = {}
    for category in schema["categories"]:
        for field in category["fields"]:
            registry_fields[field["key"].upper()] = field

    code_sources = collect_code_env_sources()
    env_example_sources = collect_env_example_sources()
    defaults = dataclass_defaults()
    hidden = {key.upper() for key in WEB_SETTINGS_HIDDEN_FROM_UI}
    server_masked = {key.upper() for key in SystemConfigService._SERVER_MASKED_CONFIG_KEYS}
    deprecated = {
        "OPENAI_VISION_MODEL": "Deprecated alias; use VISION_MODEL.",
        "AGENT_STRATEGY_DIR": "Deprecated alias; use AGENT_SKILL_DIR.",
        "AGENT_STRATEGY_AUTOWEIGHT": "Deprecated alias; use AGENT_SKILL_AUTOWEIGHT.",
        "AGENT_STRATEGY_ROUTING": "Deprecated alias; use AGENT_SKILL_ROUTING.",
    }
    compatibility_aliases = {
        "DISCORD_CHANNEL_ID": "Compatibility alias for DISCORD_MAIN_CHANNEL_ID.",
        "RUN_IMMEDIATELY": "Legacy startup flag still used by schedule compatibility logic.",
    }
    dynamic_patterns = {
        "EMAIL_GROUP_<N>": {
            "category": "notification",
            "description": "Dynamic stock-to-email routing group recipient list.",
            "data_type": "array",
            "is_sensitive": False,
        },
        "STOCK_GROUP_<N>": {
            "category": "base",
            "description": "Dynamic stock-to-email routing group stock list.",
            "data_type": "array",
            "is_sensitive": False,
        },
        "LLM_<CHANNEL>_API_KEY": {
            "category": "ai_model",
            "description": "Dynamic single API key for one LLM channel.",
            "data_type": "string",
            "is_sensitive": True,
        },
        "LLM_<CHANNEL>_API_KEYS": {
            "category": "ai_model",
            "description": "Dynamic comma-separated API keys for one LLM channel.",
            "data_type": "array",
            "is_sensitive": True,
        },
        "LLM_<CHANNEL>_BASE_URL": {
            "category": "ai_model",
            "description": "Dynamic base URL for one LLM channel.",
            "data_type": "string",
            "is_sensitive": False,
        },
        "LLM_<CHANNEL>_ENABLED": {
            "category": "ai_model",
            "description": "Dynamic enable switch for one LLM channel.",
            "data_type": "boolean",
            "is_sensitive": False,
        },
        "LLM_<CHANNEL>_EXTRA_HEADERS": {
            "category": "ai_model",
            "description": "Dynamic extra headers for one LLM channel; may contain credentials.",
            "data_type": "json",
            "is_sensitive": True,
        },
        "LLM_<CHANNEL>_MODELS": {
            "category": "ai_model",
            "description": "Dynamic comma-separated model list for one LLM channel.",
            "data_type": "array",
            "is_sensitive": False,
        },
        "LLM_<CHANNEL>_PROTOCOL": {
            "category": "ai_model",
            "description": "Dynamic protocol selector for one LLM channel.",
            "data_type": "string",
            "is_sensitive": False,
        },
    }
    keys = set(registry_fields) | set(code_sources) | set(env_example_sources) | set(deprecated) | set(compatibility_aliases) | set(server_masked)
    fields: list[dict[str, Any]] = []

    for key in sorted(keys):
        registry = registry_fields.get(key)
        dataclass_field = infer_dataclass_field(key, defaults)
        classes: list[str] = []
        registry_sensitive = bool(registry.get("is_sensitive")) if registry else False
        sensitive = is_sensitive_key(key, registry_sensitive)
        if sensitive:
            classes.append("secret")
        if registry:
            classes.append("config_schema")
            if bool(registry.get("is_editable")) and key not in hidden:
                classes.append("runtime_mutable")
        if key in hidden:
            classes.append("runtime_hidden")
        if key in server_masked:
            classes.append("server_masked")
        if key in deprecated:
            classes.append("deprecated")
        if key in compatibility_aliases:
            classes.append("compatibility_alias")
        if code_sources.get(key) and not registry:
            classes.append("runtime_only")
        if env_example_sources.get(key):
            classes.append("env_example")
        if dataclass_field:
            classes.append("config_dataclass")

        code_locations = sorted(code_sources.get(key, []), key=lambda item: (item["path"], item["line"] or 0))
        field_payload = {
            "key": key,
            "classes": sorted(set(classes)),
            "category": registry.get("category") if registry else None,
            "data_type": registry.get("data_type") if registry else None,
            "ui_control": registry.get("ui_control") if registry else None,
            "is_sensitive": sensitive,
            "is_required": bool(registry.get("is_required")) if registry else False,
            "is_editable": bool(registry.get("is_editable")) if registry else False,
            "web_settings_visible": bool(registry and key not in hidden),
            "default_value": registry.get("default_value") if registry else None,
            "dataclass_field": dataclass_field,
            "dataclass_default": defaults.get(dataclass_field) if dataclass_field else None,
            "deprecated_note": deprecated.get(key),
            "compatibility_alias_note": compatibility_aliases.get(key),
            "source_files": source_files(code_locations),
            "source_count": len(code_locations),
            "source_locations": truncate_locations(code_locations),
            "env_example": env_example_sources.get(key),
        }
        fields.append(field_payload)

    for key, pattern in sorted(dynamic_patterns.items()):
        classes = ["dynamic_pattern", "runtime_mutable"]
        if pattern["is_sensitive"]:
            classes.append("secret")
        fields.append(
            {
                "key": key,
                "classes": classes,
                "category": pattern["category"],
                "data_type": pattern["data_type"],
                "ui_control": None,
                "is_sensitive": bool(pattern["is_sensitive"]),
                "is_required": False,
                "is_editable": True,
                "web_settings_visible": False,
                "default_value": None,
                "dataclass_field": None,
                "dataclass_default": None,
                "deprecated_note": None,
                "compatibility_alias_note": None,
                "source_files": [],
                "source_count": 0,
                "source_locations": [],
                "env_example": None,
                "pattern_description": pattern["description"],
            }
        )

    class_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    for field in fields:
        for class_name in field["classes"]:
            class_counts[class_name] += 1
        category_counts[field["category"] or "uncategorized"] += 1

    return {
        "baseline": {
            "upstream": "ZhuLinsen/daily_stock_analysis",
            "version": "v3.26.1",
            "commit": expected_sha,
        },
        "schema_version": schema["schema_version"],
        "field_count": len(fields),
        "class_counts": dict(sorted(class_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "fields": fields,
    }


app = create_app(static_dir=Path("/__serenity_no_static_bundle__"))
openapi = app.openapi()
config_schema = build_schema_response()
config_inventory = build_inventory()
operation_count = sum(
    1
    for path_item in openapi.get("paths", {}).values()
    for method in path_item
    if method.lower() in {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
)

stable_json_dump(generated_dir / "openapi.json", openapi)
stable_json_dump(generated_dir / "config-schema.json", config_schema)
stable_json_dump(generated_dir / "config-env-inventory.json", config_inventory)

summary = {
    "baseline": {
        "upstream": "ZhuLinsen/daily_stock_analysis",
        "version": "v3.26.1",
        "commit": expected_sha,
    },
    "openapi": {
        "version": openapi.get("openapi"),
        "title": openapi.get("info", {}).get("title"),
        "api_version": openapi.get("info", {}).get("version"),
        "path_count": len(openapi.get("paths", {})),
        "operation_count": operation_count,
        "component_schema_count": len(openapi.get("components", {}).get("schemas", {})),
        "security_scheme_count": len(openapi.get("components", {}).get("securitySchemes", {})),
    },
    "config_schema": {
        "schema_version": config_schema.get("schema_version"),
        "category_count": len(config_schema.get("categories", [])),
        "registered_field_count": sum(len(category["fields"]) for category in config_schema.get("categories", [])),
    },
    "config_inventory": {
        "field_count": config_inventory["field_count"],
        "class_counts": config_inventory["class_counts"],
        "category_counts": config_inventory["category_counts"],
    },
    "files": {
        name: sha256_file(generated_dir / name)
        for name in ("openapi.json", "config-schema.json", "config-env-inventory.json")
    },
}
stable_json_dump(generated_dir / "summary.json", summary)
PY
)

if [[ "$UPDATE_SNAPSHOTS" -eq 1 ]]; then
  mkdir -p "$SNAPSHOT_ABS"
  cp "$GENERATED_DIR/openapi.json" "$SNAPSHOT_ABS/openapi.json"
  cp "$GENERATED_DIR/config-schema.json" "$SNAPSHOT_ABS/config-schema.json"
  cp "$GENERATED_DIR/config-env-inventory.json" "$SNAPSHOT_ABS/config-env-inventory.json"
  cp "$GENERATED_DIR/summary.json" "$SNAPSHOT_ABS/summary.json"
fi

if [[ ! -d "$SNAPSHOT_ABS" ]]; then
  echo "Missing committed snapshot dir: $SNAPSHOT_DIR" >&2
  echo "Run with --update-snapshots after reviewing generated artifacts." >&2
  exit 1
fi

FAILED=0
for snapshot_name in openapi.json config-schema.json config-env-inventory.json summary.json; do
  if [[ ! -f "$SNAPSHOT_ABS/$snapshot_name" ]]; then
    echo "Missing committed snapshot: $SNAPSHOT_DIR/$snapshot_name" >&2
    FAILED=1
    continue
  fi
  if ! cmp -s "$GENERATED_DIR/$snapshot_name" "$SNAPSHOT_ABS/$snapshot_name"; then
    diff -u "$SNAPSHOT_ABS/$snapshot_name" "$GENERATED_DIR/$snapshot_name" > "$DIFF_DIR/$snapshot_name.diff" || true
    echo "Snapshot changed: $SNAPSHOT_DIR/$snapshot_name" >&2
    echo "Diff artifact: ${DIFF_DIR#$REPO_ROOT/}/$snapshot_name.diff" >&2
    FAILED=1
  fi
done

if [[ "$FAILED" -eq 0 ]]; then
  write_summary_markdown "PASS"
else
  write_summary_markdown "FAIL"
fi

cat "$ARTIFACT_DIR/summary.md"
exit "$FAILED"
