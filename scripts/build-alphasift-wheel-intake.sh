#!/usr/bin/env bash
set -euo pipefail

# SAL-P3-002: reproducible AlphaSift wheel intake.

LOCKED_COMMIT="9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf"
SOURCE_ARCHIVE_SHA256="4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a"
SOURCE_DATE_EPOCH_VALUE=1783081838
PACKAGE_NAME="alphasift"
PACKAGE_VERSION="0.2.0"
WHEEL_FILENAME="alphasift-0.2.0-py3-none-any.whl"
SOURCE_ARCHIVE_URL="https://codeload.github.com/ZhuLinsen/alphasift/tar.gz/${LOCKED_COMMIT}"
INTERNAL_ARTIFACT_URI="internal://serenity-alpha-lab/python-wheels/alphasift/${LOCKED_COMMIT}/${WHEEL_FILENAME}"

CACHE_ROOT=".cache/alphasift-wheel-intake"
ARTIFACT_DIR="docs/baselines/alphasift-wheel-intake"
SOURCE_ARCHIVE=""
PYTHON_VERSION="3.11"
SKIP_DOWNLOAD=0

usage() {
  cat <<'USAGE'
Usage: scripts/build-alphasift-wheel-intake.sh [options]

Build the locked AlphaSift source archive into a reproducible wheel and write
SAL-P3-002 intake evidence.

Options:
  --cache-root <path>       Cache root for source, wheelhouse, and install check.
                            Default: .cache/alphasift-wheel-intake
  --artifact-dir <path>     Committed evidence directory.
                            Default: docs/baselines/alphasift-wheel-intake
  --source-archive <path>   Use an existing source archive instead of downloading.
  --skip-download           Require the default source archive to already exist.
  --python <version>        Python version used by uv build. Default: 3.11
  -h, --help                Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cache-root)
      CACHE_ROOT="$2"
      shift 2
      ;;
    --artifact-dir)
      ARTIFACT_DIR="$2"
      shift 2
      ;;
    --source-archive)
      SOURCE_ARCHIVE="$2"
      shift 2
      ;;
    --skip-download)
      SKIP_DOWNLOAD=1
      shift
      ;;
    --python)
      PYTHON_VERSION="$2"
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

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

step() {
  echo "==> $1"
}

require_cmd git
require_cmd uv
require_cmd curl
require_cmd python3

REPO_ROOT="$(repo_root)"
cd "$REPO_ROOT"

SOURCE_DIR="$CACHE_ROOT/source"
WHEELHOUSE="$CACHE_ROOT/wheelhouse"
INSTALL_TARGET="$CACHE_ROOT/offline-install-check"
mkdir -p "$SOURCE_DIR" "$WHEELHOUSE" "$INSTALL_TARGET" "$ARTIFACT_DIR"

if [[ -z "$SOURCE_ARCHIVE" ]]; then
  SOURCE_ARCHIVE="$SOURCE_DIR/${PACKAGE_NAME}-${LOCKED_COMMIT}.tar.gz"
fi

if [[ ! -f "$SOURCE_ARCHIVE" ]]; then
  if [[ "$SKIP_DOWNLOAD" -eq 1 ]]; then
    echo "Missing source archive: $SOURCE_ARCHIVE" >&2
    exit 1
  fi
  step "download locked AlphaSift source archive"
  curl -L --fail --silent --show-error --connect-timeout 20 --max-time 120 \
    "$SOURCE_ARCHIVE_URL" \
    -o "$SOURCE_ARCHIVE"
fi

ACTUAL_SOURCE_SHA="$(sha256_file "$SOURCE_ARCHIVE")"
if [[ "$ACTUAL_SOURCE_SHA" != "$SOURCE_ARCHIVE_SHA256" ]]; then
  echo "Source archive SHA-256 mismatch: got $ACTUAL_SOURCE_SHA expected $SOURCE_ARCHIVE_SHA256" >&2
  exit 1
fi

step "build reproducible wheel"
SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH_VALUE" uv build \
  --wheel \
  --python "$PYTHON_VERSION" \
  --out-dir "$WHEELHOUSE" \
  --clear \
  "$SOURCE_ARCHIVE"

WHEEL_PATH="$WHEELHOUSE/$WHEEL_FILENAME"
if [[ ! -f "$WHEEL_PATH" ]]; then
  echo "Expected wheel not found: $WHEEL_PATH" >&2
  exit 1
fi

WHEEL_SHA="$(sha256_file "$WHEEL_PATH")"

step "verify offline no-deps install from wheelhouse"
uv pip install \
  --target "$INSTALL_TARGET" \
  --reinstall \
  --no-index \
  --find-links "$WHEELHOUSE" \
  --no-deps \
  "${PACKAGE_NAME}==${PACKAGE_VERSION}" >/dev/null

step "write intake manifest, SBOM, and license inventory"
uv run --extra core --extra providers --extra desktop --extra dev python - \
  "$SOURCE_ARCHIVE" \
  "$WHEEL_PATH" \
  "$ARTIFACT_DIR" \
  "$CACHE_ROOT" \
  "$ACTUAL_SOURCE_SHA" \
  "$WHEEL_SHA" \
  "$INTERNAL_ARTIFACT_URI" <<'PY'
from __future__ import annotations

import csv
import email
import hashlib
import json
import os
import sys
import uuid
import zipfile
from collections import Counter
from importlib import metadata
from pathlib import Path


SOURCE_ARCHIVE = Path(sys.argv[1])
WHEEL_PATH = Path(sys.argv[2])
ARTIFACT_DIR = Path(sys.argv[3])
CACHE_ROOT = Path(sys.argv[4])
SOURCE_SHA = sys.argv[5]
WHEEL_SHA = sys.argv[6]
INTERNAL_ARTIFACT_URI = sys.argv[7]

LOCKED_COMMIT = "9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf"
SOURCE_ARCHIVE_SHA256 = "4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a"
SOURCE_DATE_EPOCH_VALUE = 1783081838
PACKAGE_NAME = "alphasift"
PACKAGE_VERSION = "0.2.0"
WHEEL_FILENAME = "alphasift-0.2.0-py3-none-any.whl"
SOURCE_ARCHIVE_URL = f"https://codeload.github.com/ZhuLinsen/alphasift/tar.gz/{LOCKED_COMMIT}"

ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_name(name: str) -> str:
    return name.replace("_", "-").lower()


def license_from_dist(distribution_name: str) -> tuple[str, str, str]:
    fallback = {
        "pandas": "BSD-3-Clause",
        "pyyaml": "MIT",
        "litellm": "MIT",
        "efinance": "MIT",
        "akshare": "MIT",
        "baostock": "BSD",
        "tushare": "BSD",
        "yfinance": "Apache-2.0",
        "requests": "Apache-2.0",
    }
    dist = metadata.distribution(distribution_name)
    meta = dist.metadata
    project_name = meta.get("Name", distribution_name)
    version = dist.version
    license_expression = meta.get("License-Expression")
    if license_expression:
        return project_name, version, license_expression
    license_text = (meta.get("License") or "").strip()
    if license_text and "\n" not in license_text and len(license_text) <= 80:
        normalized = {
            "Apache": "Apache-2.0",
            "BSD License": "BSD",
            "BSD": "BSD",
        }.get(license_text, license_text)
        return project_name, version, normalized
    classifiers = meta.get_all("Classifier") or []
    license_classifiers = [item.rsplit(" :: ", 1)[-1] for item in classifiers if item.startswith("License ::")]
    if license_classifiers:
        return project_name, version, " OR ".join(sorted(set(license_classifiers)))
    return project_name, version, fallback.get(normalize_name(distribution_name), "UNKNOWN")


with zipfile.ZipFile(WHEEL_PATH) as wheel:
    metadata_text = wheel.read("alphasift-0.2.0.dist-info/METADATA").decode("utf-8")
    wheel_text = wheel.read("alphasift-0.2.0.dist-info/WHEEL").decode("utf-8")
    record_text = wheel.read("alphasift-0.2.0.dist-info/RECORD").decode("utf-8")
    license_paths = [
        item.filename
        for item in wheel.infolist()
        if item.filename.endswith("LICENSE") or "/licenses/" in item.filename
    ]
    license_hashes = {path: sha256_bytes(wheel.read(path)) for path in license_paths}
    file_count = len(wheel.infolist())

message = email.message_from_string(metadata_text)
runtime_requirements = [
    value
    for value in message.get_all("Requires-Dist", [])
    if "extra ==" not in value
]

wheel_lines = dict(
    line.split(": ", 1)
    for line in wheel_text.splitlines()
    if ": " in line
)

direct_dependency_names = []
for requirement in runtime_requirements:
    name = requirement.split(" ", 1)[0].split(">", 1)[0].split("<", 1)[0].split("=", 1)[0].strip()
    direct_dependency_names.append(name)

license_rows = [
    {
        "name": PACKAGE_NAME,
        "version": PACKAGE_VERSION,
        "scope": "wheel",
        "requirement": "",
        "license": "Apache-2.0",
        "source": "alphasift-0.2.0.dist-info/METADATA License-Expression",
        "notes": "Wheel includes alphasift-0.2.0.dist-info/licenses/LICENSE and package data LICENSE.",
    }
]

for requirement, dependency_name in zip(runtime_requirements, direct_dependency_names):
    project_name, version, license_name = license_from_dist(dependency_name)
    license_rows.append(
        {
            "name": project_name,
            "version": version,
            "scope": "declared-runtime-dependency",
            "requirement": requirement,
            "license": license_name,
            "source": "current root uv environment metadata; dependency is not vendored in AlphaSift wheel",
            "notes": "Resolved for intake review only; production resolution remains controlled by root uv.lock or later wheelhouse mirror.",
        }
    )

license_path = ARTIFACT_DIR / "license-inventory.csv"
with license_path.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=["name", "version", "scope", "requirement", "license", "source", "notes"],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(license_rows)

license_counts = Counter(row["license"] for row in license_rows)
unknown_count = license_counts.get("UNKNOWN", 0)
summary_path = ARTIFACT_DIR / "license-summary.md"
summary_lines = [
    "# AlphaSift Wheel License Summary",
    "",
    f"package_count={len(license_rows)}",
    "",
    f"unknown_license_count={unknown_count}",
    "",
    "| License | Count |",
    "|---|---:|",
]
for license_name, count in sorted(license_counts.items()):
    summary_lines.append(f"| {license_name} | {count} |")
summary_lines.extend(
    [
        "",
        "AlphaSift itself is Apache-2.0. Direct runtime dependencies are not vendored in the wheel;",
        "their current metadata is recorded here for intake review and remains subject to the root lock and release gate.",
    ]
)
summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

checksum_path = ARTIFACT_DIR / "alphasift-wheel.sha256"
checksum_path.write_text(f"{WHEEL_SHA}  {INTERNAL_ARTIFACT_URI}\n", encoding="utf-8")

component_hash = [{"alg": "SHA-256", "content": WHEEL_SHA}]
components = [
    {
        "type": "library",
        "name": PACKAGE_NAME,
        "version": PACKAGE_VERSION,
        "purl": f"pkg:pypi/{PACKAGE_NAME}@{PACKAGE_VERSION}",
        "licenses": [{"license": {"id": "Apache-2.0"}}],
        "hashes": component_hash,
        "properties": [
            {"name": "serenity:task", "value": "SAL-P3-002"},
            {"name": "serenity:source_commit", "value": LOCKED_COMMIT},
            {"name": "serenity:source_archive_sha256", "value": SOURCE_ARCHIVE_SHA256},
            {"name": "serenity:internal_artifact_uri", "value": INTERNAL_ARTIFACT_URI},
        ],
    }
]
for row in license_rows[1:]:
    components.append(
        {
            "type": "library",
            "name": row["name"],
            "version": row["version"],
            "scope": "required",
            "licenses": [{"license": {"name": row["license"]}}],
            "properties": [
                {"name": "serenity:declared_requirement", "value": row["requirement"]},
                {"name": "serenity:not_vendored_in_alphasift_wheel", "value": "true"},
            ],
        }
    )

sbom = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, INTERNAL_ARTIFACT_URI + WHEEL_SHA)}",
    "version": 1,
    "metadata": {
        "timestamp": "2026-07-23T00:00:00Z",
        "tools": [
            {
                "vendor": "Serenity Alpha Lab",
                "name": "build-alphasift-wheel-intake",
                "version": "SAL-P3-002",
            }
        ],
        "component": {
            "type": "library",
            "name": PACKAGE_NAME,
            "version": PACKAGE_VERSION,
            "purl": f"pkg:pypi/{PACKAGE_NAME}@{PACKAGE_VERSION}",
            "licenses": [{"license": {"id": "Apache-2.0"}}],
            "hashes": component_hash,
        },
    },
    "components": components,
    "dependencies": [
        {
            "ref": f"pkg:pypi/{PACKAGE_NAME}@{PACKAGE_VERSION}",
            "dependsOn": [f"pkg:pypi/{normalize_name(row['name'])}@{row['version']}" for row in license_rows[1:]],
        }
    ],
}
(ARTIFACT_DIR / "sbom-cyclonedx.json").write_text(
    json.dumps(sbom, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

manifest = {
    "task": "SAL-P3-002",
    "status": "APPROVED_FOR_INTERNAL_WHEELHOUSE",
    "package": {
        "name": PACKAGE_NAME,
        "version": PACKAGE_VERSION,
        "requires_python": message.get("Requires-Python"),
        "license_spdx": message.get("License-Expression"),
        "runtime_dependencies": runtime_requirements,
    },
    "source": {
        "repository": "https://github.com/ZhuLinsen/alphasift",
        "locked_commit": LOCKED_COMMIT,
        "archive_url": SOURCE_ARCHIVE_URL,
        "archive_sha256": SOURCE_SHA,
        "archive_size_bytes": SOURCE_ARCHIVE.stat().st_size,
    },
    "build": {
        "backend": "setuptools.build_meta via uv build",
        "command": "SOURCE_DATE_EPOCH=1783081838 uv build --wheel --python 3.11 --out-dir .cache/alphasift-wheel-intake/wheelhouse --clear <source-archive>",
        "source_date_epoch": SOURCE_DATE_EPOCH_VALUE,
        "reproducibility": "SOURCE_DATE_EPOCH pinned to locked commit time",
        "wheel_generator": wheel_lines.get("Generator"),
    },
    "wheel": {
        "filename": WHEEL_FILENAME,
        "sha256": WHEEL_SHA,
        "size_bytes": WHEEL_PATH.stat().st_size,
        "root_is_purelib": wheel_lines.get("Root-Is-Purelib") == "true",
        "tag": wheel_lines.get("Tag"),
        "file_count": file_count,
        "license_files": [{"path": path, "sha256": digest} for path, digest in sorted(license_hashes.items())],
    },
    "internal_artifact": {
        "uri": f"{INTERNAL_ARTIFACT_URI}#sha256={WHEEL_SHA}",
        "local_wheelhouse_path": str(WHEEL_PATH),
        "checksum_file": "docs/baselines/alphasift-wheel-intake/alphasift-wheel.sha256",
        "binary_committed_to_git": False,
    },
    "evidence": {
        "manifest": "docs/baselines/alphasift-wheel-intake/intake-manifest.json",
        "sbom": "docs/baselines/alphasift-wheel-intake/sbom-cyclonedx.json",
        "license_inventory": "docs/baselines/alphasift-wheel-intake/license-inventory.csv",
        "license_summary": "docs/baselines/alphasift-wheel-intake/license-summary.md",
        "checksum": "docs/baselines/alphasift-wheel-intake/alphasift-wheel.sha256",
    },
    "production_install_policy": {
        "git_dependencies_allowed": False,
        "offline_install_mode": "uv pip install --no-index --find-links <internal-wheelhouse> --no-deps alphasift==0.2.0",
        "root_pyproject_modified": False,
        "production_requirements_modified": False,
        "root_uv_lock_modified": False,
    },
    "offline_install_check": {
        "status": "PASS",
        "command": "uv pip install --target .cache/alphasift-wheel-intake/offline-install-check --reinstall --no-index --find-links .cache/alphasift-wheel-intake/wheelhouse --no-deps alphasift==0.2.0",
        "target": str(CACHE_ROOT / "offline-install-check"),
    },
    "prohibited_scope": [
        "No ScreeningProvider Adapter implementation in SAL-P3-002.",
        "No CandidateBatch, Factor Engine, Quant Core, formal backtest, or Evidence Agent.",
        "No real Provider or real LLM calls.",
        "No DSA runtime source migration and no upstream tag movement.",
    ],
}
(ARTIFACT_DIR / "intake-manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

step "AlphaSift wheel intake complete"
echo "source_sha256=$ACTUAL_SOURCE_SHA"
echo "wheel_sha256=$WHEEL_SHA"
echo "wheel=$WHEEL_PATH"
echo "evidence=$ARTIFACT_DIR"
