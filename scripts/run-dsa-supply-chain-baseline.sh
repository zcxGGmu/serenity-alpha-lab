#!/usr/bin/env bash
set -euo pipefail

BASELINE_TAG="upstream/dsa-v3.26.1"
EXPECTED_SHA="e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
WORKTREE_PATH=".worktrees/dsa-v3.26.1"
CACHE_ROOT=".cache/dsa-p0"
IMAGE_TAG="serenity-dsa-p0:sal-p0-007"

usage() {
  cat <<'USAGE'
Usage: scripts/run-dsa-supply-chain-baseline.sh [options]

Generate the locked DSA supply-chain baseline artifacts.

Options:
  --worktree <path>      Locked DSA worktree. Default: .worktrees/dsa-v3.26.1
  --cache-root <path>    Cache/artifact root. Default: .cache/dsa-p0
  --image-tag <tag>      Docker image tag. Default: serenity-dsa-p0:sal-p0-007
  -h, --help             Show this help
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
    --image-tag)
      IMAGE_TAG="$2"
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

require_cmd git
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
  exit 1
fi

WORKTREE_SHA="$(git -C "$WORKTREE_PATH" rev-parse HEAD)"
if [[ "$WORKTREE_SHA" != "$EXPECTED_SHA" ]]; then
  echo "Worktree $WORKTREE_PATH is at $WORKTREE_SHA, expected $EXPECTED_SHA" >&2
  exit 1
fi

VENV_PATH="$CACHE_ROOT/venv"
if [[ ! -x "$VENV_PATH/bin/python" ]]; then
  echo "Missing Python venv: $VENV_PATH" >&2
  exit 1
fi

ARTIFACT_DIR="$CACHE_ROOT/supply-chain-artifacts"
mkdir -p "$ARTIFACT_DIR"

TARGET_PYTHON="$REPO_ROOT/$VENV_PATH/bin/python"
WORKTREE_ABS="$REPO_ROOT/$WORKTREE_PATH"
ARTIFACT_ABS="$REPO_ROOT/$ARTIFACT_DIR"
PIP_AUDIT_BIN=""
if [[ -x "$REPO_ROOT/$CACHE_ROOT/supply-chain-tools-venv/bin/pip-audit" ]]; then
  PIP_AUDIT_BIN="$REPO_ROOT/$CACHE_ROOT/supply-chain-tools-venv/bin/pip-audit"
elif command -v pip-audit >/dev/null 2>&1; then
  PIP_AUDIT_BIN="$(command -v pip-audit)"
fi

{
  echo "# DSA supply-chain baseline environment"
  echo
  echo "baseline_tag=$BASELINE_TAG"
  echo "expected_sha=$EXPECTED_SHA"
  echo "worktree=$WORKTREE_ABS"
  echo "cache_root=$REPO_ROOT/$CACHE_ROOT"
  echo "artifact_dir=$ARTIFACT_ABS"
  echo "image_tag=$IMAGE_TAG"
  echo
  "$TARGET_PYTHON" --version
  "$TARGET_PYTHON" -m pip --version
  if command -v docker >/dev/null 2>&1; then
    docker --version
    docker info --format 'docker_server={{.ServerVersion}}' 2>/dev/null || echo "docker_server=UNAVAILABLE"
  else
    echo "docker=NOT_INSTALLED"
  fi
  for scanner in syft grype trivy; do
    if command -v "$scanner" >/dev/null 2>&1; then
      "$scanner" version 2>/dev/null | head -20 || true
    else
      echo "$scanner=NOT_INSTALLED"
    fi
  done
  if [[ -n "$PIP_AUDIT_BIN" ]]; then
    "$PIP_AUDIT_BIN" --version
  else
    echo "pip-audit=NOT_INSTALLED"
  fi
} > "$ARTIFACT_DIR/environment.txt"

"$TARGET_PYTHON" -m pip inspect --local > "$ARTIFACT_DIR/python-pip-inspect.json"
"$TARGET_PYTHON" -m pip list --format=json > "$ARTIFACT_DIR/python-pip-list.json"

python3 - "$ARTIFACT_DIR/python-pip-inspect.json" "$ARTIFACT_DIR/python-sbom-cyclonedx.json" "$ARTIFACT_DIR/python-license-inventory.csv" "$ARTIFACT_DIR/python-license-summary.md" <<'PY'
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone

def normalize_license(value, classifier_licenses):
    value = (value or "").strip()
    if "\n" in value or len(value) > 120:
        return classifier_licenses[0] if classifier_licenses else "CUSTOM/SEE-METADATA"
    value = re.sub(r"\s+", " ", value)
    return value or (classifier_licenses[0] if classifier_licenses else "UNKNOWN")

inspect_path, sbom_path, license_csv_path, summary_path = sys.argv[1:5]
data = json.load(open(inspect_path, encoding="utf-8"))
components = []
licenses = []
for item in sorted(data.get("installed", []), key=lambda x: (x.get("metadata", {}).get("name") or "").lower()):
    metadata = item.get("metadata", {})
    name = metadata.get("name") or "UNKNOWN"
    version = metadata.get("version") or "UNKNOWN"
    license_value = (metadata.get("license") or "").strip()
    classifiers = metadata.get("classifier") or []
    classifier_licenses = [
        classifier.split(" :: ")[-1]
        for classifier in classifiers
        if classifier.startswith("License ::")
    ]
    license_name = normalize_license(license_value, classifier_licenses)
    component = {
        "type": "library",
        "bom-ref": f"pkg:pypi/{name.lower()}@{version}",
        "name": name,
        "version": version,
        "purl": f"pkg:pypi/{name.lower()}@{version}",
    }
    if license_name != "UNKNOWN":
        component["licenses"] = [{"license": {"name": license_name}}]
    components.append(component)
    licenses.append((name, version, license_name))

sbom = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "version": 1,
    "metadata": {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tools": [{"vendor": "Serenity Alpha Lab", "name": "pip-inspect-to-cyclonedx", "version": "p0"}],
    },
    "components": components,
}
json.dump(sbom, open(sbom_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

with open(license_csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["name", "version", "license"])
    writer.writerows(licenses)

counts = Counter(license_name for _, _, license_name in licenses)
unknown = counts.get("UNKNOWN", 0)
with open(summary_path, "w", encoding="utf-8") as f:
    f.write("# Python license summary\n\n")
    f.write(f"package_count={len(licenses)}\n\n")
    f.write(f"unknown_license_count={unknown}\n\n")
    f.write("| License | Count |\n|---|---:|\n")
    for license_name, count in counts.most_common():
        f.write(f"| {license_name} | {count} |\n")
PY

python3 - "$WORKTREE_PATH/requirements.txt" "$WORKTREE_PATH/.github/requirements-ci.txt" "$ARTIFACT_DIR/python-requirements-summary.md" <<'PY'
import sys
from pathlib import Path

runtime_path, ci_path, output_path = map(Path, sys.argv[1:4])
lines = []
for raw in runtime_path.read_text(encoding="utf-8").splitlines():
    clean = raw.split("#", 1)[0].strip()
    if clean:
        lines.append(clean)

dynamic_git = [line for line in lines if line.startswith("git+")]
exact_pins = [line for line in lines if "==" in line and not line.startswith("git+")]
ranges = [line for line in lines if line not in dynamic_git and line not in exact_pins]

with output_path.open("w", encoding="utf-8") as f:
    f.write("# Python requirements summary\n\n")
    f.write(f"runtime_requirement_count={len(lines)}\n")
    f.write(f"dynamic_git_count={len(dynamic_git)}\n")
    f.write(f"exact_pin_count={len(exact_pins)}\n")
    f.write(f"range_or_unpinned_count={len(ranges)}\n")
    f.write(f"ci_requirements={ci_path.as_posix()}\n\n")
    f.write("## Dynamic Git dependencies\n\n")
    for line in dynamic_git:
        f.write(f"- `{line}`\n")
    f.write("\n## Exact pins\n\n")
    for line in exact_pins:
        f.write(f"- `{line}`\n")
PY

if command -v npm >/dev/null 2>&1 && [[ -d "$WORKTREE_PATH/apps/dsa-web" ]]; then
  (
    cd "$WORKTREE_PATH/apps/dsa-web"
    npm audit --json > "$ARTIFACT_ABS/node-web-npm-audit.json" 2>"$ARTIFACT_ABS/node-web-npm-audit.stderr" || true
  )
fi

python3 - "$WORKTREE_PATH/apps/dsa-web/node_modules" "$WORKTREE_PATH/apps/dsa-web/package-lock.json" "$ARTIFACT_DIR/node-web-license-inventory.csv" "$ARTIFACT_DIR/node-web-license-summary.md" <<'PY'
import csv
import json
import sys
from collections import Counter
from pathlib import Path

node_modules, lockfile_path, csv_path, summary_path = map(Path, sys.argv[1:5])
rows = []
if node_modules.exists():
    for package_json in node_modules.rglob("package.json"):
        rel = package_json.relative_to(node_modules)
        if len(rel.parts) > 3:
            continue
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = data.get("name") or package_json.parent.name
        version = data.get("version") or "UNKNOWN"
        license_value = data.get("license") or "UNKNOWN"
        if isinstance(license_value, dict):
            license_value = license_value.get("type") or "UNKNOWN"
        rows.append((name, version, str(license_value)))
elif lockfile_path.exists():
    lockfile = json.loads(lockfile_path.read_text(encoding="utf-8"))
    for package_path, data in lockfile.get("packages", {}).items():
        if not package_path.startswith("node_modules/"):
            continue
        name = data.get("name")
        if not name:
            name = package_path.split("node_modules/")[-1]
        version = data.get("version") or "UNKNOWN"
        license_value = data.get("license") or "UNKNOWN"
        if isinstance(license_value, dict):
            license_value = license_value.get("type") or "UNKNOWN"
        rows.append((name, version, str(license_value)))

rows = sorted(set(rows), key=lambda row: (row[0].lower(), row[1]))
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["name", "version", "license"])
    writer.writerows(rows)

counts = Counter(license_value for _, _, license_value in rows)
with summary_path.open("w", encoding="utf-8") as f:
    f.write("# Node web license summary\n\n")
    f.write(f"package_count={len(rows)}\n\n")
    f.write(f"unknown_license_count={counts.get('UNKNOWN', 0)}\n\n")
    f.write("| License | Count |\n|---|---:|\n")
    for license_value, count in counts.most_common():
        f.write(f"| {license_value} | {count} |\n")
PY

DOCKER_AVAILABLE=0
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  DOCKER_AVAILABLE=1
fi

if [[ "$DOCKER_AVAILABLE" -eq 1 ]] && docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
  docker image inspect "$IMAGE_TAG" > "$ARTIFACT_DIR/image-inspect.json"
  docker history --no-trunc "$IMAGE_TAG" > "$ARTIFACT_DIR/image-history.txt"
  docker run --rm --entrypoint sh "$IMAGE_TAG" -lc 'cat /etc/os-release' > "$ARTIFACT_DIR/image-os-release.txt"
  docker run --rm --entrypoint sh "$IMAGE_TAG" -lc 'dpkg-query -W -f="\${Package}\t\${Version}\t\${Architecture}\n"' > "$ARTIFACT_DIR/image-dpkg.tsv"
  docker run --rm --entrypoint sh "$IMAGE_TAG" -lc 'python -m pip list --format=json' > "$ARTIFACT_DIR/image-python-pip-list.json"
  python3 - "$ARTIFACT_DIR/image-dpkg.tsv" "$ARTIFACT_DIR/image-python-pip-list.json" "$ARTIFACT_DIR/image-sbom-lite-cyclonedx.json" <<'PY'
import csv
import json
import sys
from datetime import datetime, timezone

dpkg_path, pip_path, output_path = sys.argv[1:4]
components = []
with open(dpkg_path, encoding="utf-8") as f:
    for row in csv.reader(f, delimiter="\t"):
        if len(row) != 3:
            continue
        name, version, arch = row
        components.append({
            "type": "library",
            "bom-ref": f"pkg:deb/debian/{name}@{version}?arch={arch}",
            "name": name,
            "version": version,
            "purl": f"pkg:deb/debian/{name}@{version}?arch={arch}",
        })
for item in json.load(open(pip_path, encoding="utf-8")):
    name = item.get("name") or "UNKNOWN"
    version = item.get("version") or "UNKNOWN"
    components.append({
        "type": "library",
        "bom-ref": f"pkg:pypi/{name.lower()}@{version}",
        "name": name,
        "version": version,
        "purl": f"pkg:pypi/{name.lower()}@{version}",
    })
sbom = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "version": 1,
    "metadata": {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tools": [{"vendor": "Serenity Alpha Lab", "name": "docker-inventory-to-cyclonedx", "version": "p0"}],
    },
    "components": components,
}
json.dump(sbom, open(output_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
PY
else
  echo "Docker unavailable or image missing: $IMAGE_TAG" > "$ARTIFACT_DIR/image-blocker.txt"
fi

SCANNER_STATUS="$ARTIFACT_DIR/scanner-status.md"
{
  echo "# Scanner status"
  echo
  echo "| Scanner | Status | Output |"
  echo "|---|---|---|"
} > "$SCANNER_STATUS"

if command -v syft >/dev/null 2>&1 && [[ "$DOCKER_AVAILABLE" -eq 1 ]]; then
  set +e
  syft "$IMAGE_TAG" -o cyclonedx-json > "$ARTIFACT_DIR/image-syft-cyclonedx.json" 2>"$ARTIFACT_DIR/image-syft.stderr"
  syft_rc=$?
  set -e
  if [[ "$syft_rc" -eq 0 && -s "$ARTIFACT_DIR/image-syft-cyclonedx.json" ]]; then
    echo "| syft | success | image-syft-cyclonedx.json |" >> "$SCANNER_STATUS"
  else
    echo "| syft | failed exit=$syft_rc | image-syft.stderr |" >> "$SCANNER_STATUS"
  fi
else
  echo "| syft | not installed | image-sbom-lite-cyclonedx.json generated from dpkg + pip inventory |" >> "$SCANNER_STATUS"
fi

if command -v trivy >/dev/null 2>&1 && [[ "$DOCKER_AVAILABLE" -eq 1 ]]; then
  set +e
  trivy image --skip-db-update --timeout 2m --format json --output "$ARTIFACT_DIR/image-trivy-vulnerabilities.json" "$IMAGE_TAG" 2>"$ARTIFACT_DIR/image-trivy.stderr"
  trivy_rc=$?
  set -e
  if [[ "$trivy_rc" -eq 0 && -s "$ARTIFACT_DIR/image-trivy-vulnerabilities.json" ]]; then
    echo "| trivy | success | image-trivy-vulnerabilities.json |" >> "$SCANNER_STATUS"
  else
    echo "| trivy | failed exit=$trivy_rc | image-trivy.stderr |" >> "$SCANNER_STATUS"
  fi
else
  echo "| trivy | not installed | vulnerability scanner unavailable |" >> "$SCANNER_STATUS"
fi

if command -v grype >/dev/null 2>&1 && [[ "$DOCKER_AVAILABLE" -eq 1 ]]; then
  set +e
  grype "$IMAGE_TAG" -o json > "$ARTIFACT_DIR/image-grype-vulnerabilities.json" 2>"$ARTIFACT_DIR/image-grype.stderr"
  grype_rc=$?
  set -e
  if [[ "$grype_rc" -eq 0 && -s "$ARTIFACT_DIR/image-grype-vulnerabilities.json" ]]; then
    echo "| grype | success | image-grype-vulnerabilities.json |" >> "$SCANNER_STATUS"
  else
    echo "| grype | failed exit=$grype_rc | image-grype.stderr |" >> "$SCANNER_STATUS"
  fi
else
  echo "| grype | not installed | vulnerability scanner unavailable |" >> "$SCANNER_STATUS"
fi

if [[ -n "$PIP_AUDIT_BIN" ]]; then
  SITE_PACKAGES="$($TARGET_PYTHON - <<'PY_SITE'
import site
print(site.getsitepackages()[0])
PY_SITE
)"
  set +e
  "$PIP_AUDIT_BIN" --path "$SITE_PACKAGES" --format json --output "$ARTIFACT_DIR/python-pip-audit.json" --progress-spinner off
  pip_audit_rc=$?
  set -e
  if [[ -s "$ARTIFACT_DIR/python-pip-audit.json" ]]; then
    echo "| pip-audit | completed exit=$pip_audit_rc | python-pip-audit.json |" >> "$SCANNER_STATUS"
  else
    echo "| pip-audit | failed exit=$pip_audit_rc | Python vulnerability scanner unavailable |" >> "$SCANNER_STATUS"
  fi
else
  echo "| pip-audit | not installed | Python vulnerability scanner unavailable |" >> "$SCANNER_STATUS"
fi

python3 - "$ARTIFACT_DIR" "$IMAGE_TAG" <<'PY'
import json
import sys
from pathlib import Path

artifact_dir = Path(sys.argv[1])
image_tag = sys.argv[2]
summary_path = artifact_dir / "summary.md"

def count_json_array(path):
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return len(data) if isinstance(data, list) else None

python_packages = count_json_array(artifact_dir / "python-pip-list.json")
image_python_packages = count_json_array(artifact_dir / "image-python-pip-list.json")
dpkg_count = 0
dpkg_path = artifact_dir / "image-dpkg.tsv"
if dpkg_path.exists():
    dpkg_count = sum(1 for line in dpkg_path.read_text(encoding="utf-8").splitlines() if line.strip())

node_audit = artifact_dir / "node-web-npm-audit.json"
node_vulns = {}
if node_audit.exists():
    try:
        audit = json.loads(node_audit.read_text(encoding="utf-8"))
        node_vulns = audit.get("metadata", {}).get("vulnerabilities", {})
    except Exception:
        node_vulns = {}

python_audit_path = artifact_dir / "python-pip-audit.json"
python_audit_vulns = 0
python_audit_packages = 0
python_audit_skipped = 0
if python_audit_path.exists() and python_audit_path.stat().st_size > 0:
    try:
        audit = json.loads(python_audit_path.read_text(encoding="utf-8"))
        for dep in audit.get("dependencies", []):
            if dep.get("skip_reason"):
                python_audit_skipped += 1
            else:
                python_audit_packages += 1
            python_audit_vulns += len(dep.get("vulns") or [])
    except Exception:
        python_audit_path = None

trivy_path = artifact_dir / "image-trivy-vulnerabilities.json"
trivy_counts = {}
if trivy_path.exists() and trivy_path.stat().st_size > 0:
    try:
        trivy = json.loads(trivy_path.read_text(encoding="utf-8"))
        for result_item in trivy.get("Results", []) or []:
            for vuln in result_item.get("Vulnerabilities", []) or []:
                severity = vuln.get("Severity", "UNKNOWN").lower()
                trivy_counts[severity] = trivy_counts.get(severity, 0) + 1
    except Exception:
        trivy_path = None

grype_path = artifact_dir / "image-grype-vulnerabilities.json"
grype_count = None
grype_counts = {}
if grype_path.exists() and grype_path.stat().st_size > 0:
    try:
        grype = json.loads(grype_path.read_text(encoding="utf-8"))
        matches = grype.get("matches", []) or []
        grype_count = len(matches)
        for match in matches:
            severity = ((match.get("vulnerability") or {}).get("severity") or "unknown").lower()
            grype_counts[severity] = grype_counts.get(severity, 0) + 1
    except Exception:
        grype_count = None
        grype_counts = {}

scanner_status = (artifact_dir / "scanner-status.md").read_text(encoding="utf-8")
image_vuln_available = bool(trivy_counts) or grype_count is not None
python_vuln_available = python_audit_path is not None
blocked = not image_vuln_available or not python_vuln_available
result = "BLOCKED" if blocked else "PASS"

with summary_path.open("w", encoding="utf-8") as f:
    f.write("# DSA supply-chain baseline summary\n\n")
    f.write(f"Result: {result}\n\n")
    f.write(f"image_tag={image_tag}\n\n")
    f.write("| Area | Count / Status |\n|---|---:|\n")
    f.write(f"| Python installed packages | {python_packages if python_packages is not None else 'missing'} |\n")
    f.write(f"| Python audit packages checked | {python_audit_packages if python_vuln_available else 'missing'} |\n")
    f.write(f"| Python audit skipped packages | {python_audit_skipped if python_vuln_available else 'missing'} |\n")
    f.write(f"| Python audit vulnerabilities | {python_audit_vulns if python_vuln_available else 'missing'} |\n")
    f.write(f"| Image Debian packages | {dpkg_count or 'missing'} |\n")
    f.write(f"| Image Python packages | {image_python_packages if image_python_packages is not None else 'missing'} |\n")
    if trivy_counts:
        f.write(f"| Image Trivy critical | {trivy_counts.get('critical', 0)} |\n")
        f.write(f"| Image Trivy high | {trivy_counts.get('high', 0)} |\n")
        f.write(f"| Image Trivy total | {sum(trivy_counts.values())} |\n")
    if grype_count is not None:
        f.write(f"| Image Grype critical | {grype_counts.get('critical', 0)} |\n")
        f.write(f"| Image Grype high | {grype_counts.get('high', 0)} |\n")
        f.write(f"| Image Grype medium | {grype_counts.get('medium', 0)} |\n")
        f.write(f"| Image Grype matches | {grype_count} |\n")
    if node_vulns:
        total = node_vulns.get("total", sum(v for k, v in node_vulns.items() if isinstance(v, int)))
        f.write(f"| Node audit total vulnerabilities | {total} |\n")
        f.write(f"| Node audit high | {node_vulns.get('high', 0)} |\n")
        f.write(f"| Node audit critical | {node_vulns.get('critical', 0)} |\n")
    f.write("\n")
    f.write(scanner_status)
PY

cat "$ARTIFACT_DIR/summary.md"
