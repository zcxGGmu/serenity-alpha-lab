from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build-alphasift-wheel-intake.sh"
DOC = ROOT / "docs" / "alphasift-wheel-intake.md"
BASELINE_DIR = ROOT / "docs" / "baselines" / "alphasift-wheel-intake"
MANIFEST = BASELINE_DIR / "intake-manifest.json"
SBOM = BASELINE_DIR / "sbom-cyclonedx.json"
LICENSE_INVENTORY = BASELINE_DIR / "license-inventory.csv"
LICENSE_SUMMARY = BASELINE_DIR / "license-summary.md"
WHEEL_SHA = BASELINE_DIR / "alphasift-wheel.sha256"

LOCKED_COMMIT = "9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf"
SOURCE_ARCHIVE_SHA256 = "4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a"
WHEEL_SHA256 = "b71fe6f4b11c9655b2190f91217fee66361f9852ae344c53fe501455a4823ed2"


def test_alphasift_wheel_intake_script_is_reproducible_and_offline_safe() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    required_terms = [
        "SAL-P3-002",
        LOCKED_COMMIT,
        SOURCE_ARCHIVE_SHA256,
        "https://codeload.github.com/ZhuLinsen/alphasift/tar.gz/",
        "SOURCE_DATE_EPOCH_VALUE=1783081838",
        "uv build --wheel",
        "--no-index",
        "--find-links",
        "--no-deps",
        "git_dependencies_allowed",
    ]

    missing = [term for term in required_terms if term not in script]
    assert missing == []
    assert "git clone" not in script
    assert "git+https://github.com/ZhuLinsen/alphasift" not in script


def test_alphasift_wheel_intake_manifest_locks_hashes_and_boundaries() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["task"] == "SAL-P3-002"
    assert manifest["package"]["name"] == "alphasift"
    assert manifest["package"]["version"] == "0.2.0"
    assert manifest["source"]["locked_commit"] == LOCKED_COMMIT
    assert manifest["source"]["archive_sha256"] == SOURCE_ARCHIVE_SHA256
    assert manifest["wheel"]["filename"] == "alphasift-0.2.0-py3-none-any.whl"
    assert manifest["wheel"]["sha256"] == WHEEL_SHA256
    assert manifest["build"]["source_date_epoch"] == 1783081838
    assert manifest["build"]["reproducibility"] == "SOURCE_DATE_EPOCH pinned to locked commit time"
    assert manifest["internal_artifact"]["uri"].endswith(f"#sha256={WHEEL_SHA256}")
    assert manifest["production_install_policy"]["git_dependencies_allowed"] is False
    assert manifest["production_install_policy"]["root_pyproject_modified"] is False
    assert manifest["production_install_policy"]["production_requirements_modified"] is False
    assert manifest["offline_install_check"]["status"] == "PASS"

    prohibited = "\n".join(manifest["prohibited_scope"])
    for term in [
        "ScreeningProvider",
        "Quant Core",
        "formal backtest",
        "Evidence Agent",
        "real Provider",
        "real LLM",
    ]:
        assert term in prohibited


def test_alphasift_wheel_intake_sbom_and_license_inventory_are_committed() -> None:
    sbom = json.loads(SBOM.read_text(encoding="utf-8"))

    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert sbom["metadata"]["component"]["name"] == "alphasift"
    assert sbom["metadata"]["component"]["version"] == "0.2.0"
    assert sbom["metadata"]["component"]["hashes"] == [{"alg": "SHA-256", "content": WHEEL_SHA256}]
    assert any(component["name"] == "alphasift" for component in sbom["components"])

    rows = list(csv.DictReader(LICENSE_INVENTORY.read_text(encoding="utf-8").splitlines()))
    by_name = {row["name"]: row for row in rows}
    assert by_name["alphasift"]["license"] == "Apache-2.0"
    for dependency in ["pandas", "PyYAML", "litellm", "efinance", "akshare", "baostock", "tushare", "yfinance", "requests"]:
        assert dependency in by_name

    summary = LICENSE_SUMMARY.read_text(encoding="utf-8")
    assert "AlphaSift Wheel License Summary" in summary
    assert "unknown_license_count=0" in summary
    assert "Apache-2.0" in summary

    checksum = WHEEL_SHA.read_text(encoding="utf-8").strip()
    assert checksum == f"{WHEEL_SHA256}  internal://serenity-alpha-lab/python-wheels/alphasift/{LOCKED_COMMIT}/alphasift-0.2.0-py3-none-any.whl"


def test_alphasift_wheel_intake_review_documents_non_goals() -> None:
    text = DOC.read_text(encoding="utf-8")

    required_terms = [
        "SAL-P3-002",
        LOCKED_COMMIT,
        SOURCE_ARCHIVE_SHA256,
        WHEEL_SHA256,
        "internal://serenity-alpha-lab/python-wheels/alphasift/",
        "sbom-cyclonedx.json",
        "license-inventory.csv",
        "uv pip install --no-index --find-links",
        "不提交 Wheel 二进制",
        "未实现 ScreeningProvider",
        "未启动 Quant Core",
        "未启动正式回测",
        "未启动 Evidence Agent",
        "未调用真实 Provider",
        "未调用真实 LLM",
    ]

    missing = [term for term in required_terms if term not in text]
    assert missing == []
