from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "patches" / "dsa" / "v3.26.1" / "0005-migrate-signal-evaluation-engine.patch"
PLAN = ROOT / "docs" / "superpowers" / "plans" / "2026-07-25-signal-evaluation-engine.md"
CHARACTERIZATION_SCRIPT = ROOT / "scripts" / "run-dsa-signal-evaluation-characterization.sh"


def test_dsa_signal_evaluation_engine_patch_introduces_new_semantic_name() -> None:
    assert PATCH.exists()
    patch = PATCH.read_text(encoding="utf-8")

    required_terms = [
        "src/core/signal_evaluation_engine.py",
        "class SignalEvaluationEngine",
        "SignalEvaluationConfig",
        "evaluation_type",
        "legacy_signal_evaluation",
        "src/services/backtest_service.py",
        "src/services/decision_signal_outcome_service.py",
    ]
    missing = [term for term in required_terms if term not in patch]
    assert missing == []


def test_dsa_web_copy_migrates_visible_backtest_page_to_signal_evaluation_language() -> None:
    assert PATCH.exists()
    patch = PATCH.read_text(encoding="utf-8")

    required_terms = [
        "信号评价",
        "Signal Evaluation",
        "运行信号评价",
        "Run signal evaluation",
        "legacy `/api/v1/backtest/*`",
    ]
    missing = [term for term in required_terms if term not in patch]
    assert missing == []

    forbidden_terms = [
        "/api/v1/quant/backtest-runs",
        "BacktestSpec",
        "formal_backtest_started=true",
    ]
    forbidden = [term for term in forbidden_terms if term in patch]
    assert forbidden == []


def test_signal_evaluation_engine_plan_preserves_p4_002_boundaries() -> None:
    plan = PLAN.read_text(encoding="utf-8")

    required_terms = [
        "SAL-P4-002",
        "SAL-P4-001` snapshots byte-for-byte identical",
        "SignalEvaluationEngine",
        "evaluation_type=signal",
        "portfolio backtests",
        "BacktestSpec",
        "Provider, LLM",
    ]
    missing = [term for term in required_terms if term not in plan]
    assert missing == []


def test_signal_evaluation_characterization_guard_allows_new_registered_patch_files() -> None:
    script = CHARACTERIZATION_SCRIPT.read_text(encoding="utf-8")

    required_terms = [
        'if is_allowed_patch_path "$path"; then',
        'allow_generated_worktree_untracked_path "$path"',
        "unexpected+=(\"$line\")",
    ]
    missing = [term for term in required_terms if term not in script]
    assert missing == []
