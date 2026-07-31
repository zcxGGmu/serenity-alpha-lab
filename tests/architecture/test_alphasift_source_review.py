from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = ROOT / "docs" / "alphasift-source-review.md"

LOCKED_COMMIT = "9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf"
SOURCE_ARCHIVE_SHA256 = "4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a"


def test_alphasift_source_review_locks_source_license_and_dependencies() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    required_terms = [
        "SAL-P3-001",
        f"locked_source_commit: {LOCKED_COMMIT}",
        "source_repository: https://github.com/ZhuLinsen/alphasift",
        f"source_archive_sha256: {SOURCE_ARCHIVE_SHA256}",
        "license_spdx: Apache-2.0",
        "version: 0.2.0",
        "requires_python: >=3.10",
        "pandas>=2.0",
        "pyyaml>=6.0",
        "litellm>=1.0",
        "efinance>=0.4",
        "akshare>=1.10",
        "baostock>=0.8.9",
        "tushare>=1.4",
        "yfinance>=0.2",
        "requests>=2.28",
    ]

    missing = [term for term in required_terms if term not in text]
    assert missing == []

def test_alphasift_source_review_documents_security_limitations_and_stop_conditions() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    required_terms = [
        "pip_audit_current_resolution: 0 known vulnerabilities",
        "AlphaSift itself is not PyPI-auditable",
        "range dependencies are not a release lock",
        "Known limitations",
        "Upgrade conditions",
        "Replacement conditions",
        "Stop-use conditions",
        "must not replace Dataset Catalog",
        "must not replace PIT Dataset",
        "must not replace Provider Policy",
        "must not start Quant Core",
        "must not start formal backtesting",
        "must not start Evidence Agent",
        "SAL-P3-002",
    ]

    missing = [term for term in required_terms if term not in text]
    assert missing == []
