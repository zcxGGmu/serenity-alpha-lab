from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = ROOT / "docs" / "baselines" / "dsa-v3.26.1" / "signal-evaluation-characterization"
DOC = ROOT / "docs" / "dsa-signal-evaluation-characterization.md"
SCRIPT = ROOT / "scripts" / "run-dsa-signal-evaluation-characterization.sh"


def _load_json(name: str) -> dict:
    return json.loads((BASELINE_DIR / name).read_text(encoding="utf-8"))


def test_signal_evaluation_characterization_baseline_files_are_committed() -> None:
    expected_files = {
        "api-surface.json",
        "content-hashes.json",
        "decision-signal-evaluations.json",
        "engine-evaluations.json",
        "inputs.json",
        "signal-evaluation-summary.json",
        "summary.json",
    }

    assert BASELINE_DIR.exists()
    assert {path.name for path in BASELINE_DIR.iterdir() if path.is_file()} == expected_files

    summary = _load_json("summary.json")
    assert summary["task"] == "SAL-P4-001"
    assert summary["baseline"]["commit"] == "e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
    assert summary["validation"]["characterization_passed"] is True
    assert summary["validation"]["api_surface_passed"] is True
    assert summary["validation"]["formal_backtest_started"] is False
    assert summary["validation"]["real_provider_calls_zero"] is True
    assert summary["validation"]["real_llm_calls_zero"] is True


def test_signal_evaluation_engine_goldens_cover_negation_missing_data_and_summary() -> None:
    engine_items = _load_json("engine-evaluations.json")["items"]
    by_case = {item["case"]: item for item in engine_items}

    assert len(engine_items) >= 11
    for case in [
        "buy_take_profit",
        "sell_direction_win",
        "hold_loss",
        "watch_flat_win",
        "buy_ambiguous_stop_first",
        "buy_insufficient_data",
        "negated_buy_wait_cash",
        "negated_sell_hold_long",
        "english_negated_sell_hold",
        "missing_end_close",
        "missing_high_low",
    ]:
        assert case in by_case

    assert by_case["negated_buy_wait_cash"]["position_recommendation"] == "cash"
    assert by_case["negated_buy_wait_cash"]["direction_expected"] == "flat"
    assert by_case["negated_buy_wait_cash"]["outcome"] == "loss"

    assert by_case["negated_sell_hold_long"]["position_recommendation"] == "long"
    assert by_case["negated_sell_hold_long"]["direction_expected"] == "not_down"
    assert by_case["negated_sell_hold_long"]["outcome"] == "win"
    assert by_case["english_negated_sell_hold"]["direction_expected"] == "not_down"

    assert by_case["missing_end_close"]["eval_status"] == "completed"
    assert by_case["missing_end_close"]["stock_return_pct"] is None
    assert by_case["missing_end_close"]["simulated_return_pct"] is None
    assert by_case["missing_high_low"]["max_high"] is None
    assert by_case["missing_high_low"]["min_low"] is None
    assert by_case["missing_high_low"]["outcome"] == "win"

    summary = _load_json("signal-evaluation-summary.json")
    assert summary["total_evaluations"] == len(engine_items)
    assert summary["completed_count"] == len(engine_items) - 1
    assert summary["insufficient_count"] == 1
    assert "不要买入，等待确认" in summary["advice_breakdown"]
    assert "do not sell, hold and watch" in summary["advice_breakdown"]


def test_decision_signal_goldens_lock_structured_signal_outcomes() -> None:
    decision_items = _load_json("decision-signal-evaluations.json")["items"]
    by_case = {item["case"]: item for item in decision_items}

    assert by_case["decision_up_hit"]["eval_status"] == "completed"
    assert by_case["decision_up_hit"]["outcome"] == "hit"
    assert by_case["decision_not_up_hit"]["direction_expected"] == "not_up"
    assert by_case["decision_not_up_hit"]["direction_correct"] is True
    assert by_case["decision_invalid_anchor"]["unable_reason"] == "invalid_anchor_price"
    assert by_case["decision_insufficient_forward_bars"]["unable_reason"] == "insufficient_forward_bars"
    assert by_case["decision_missing_end_close"]["unable_reason"] == "missing_end_close"


def test_legacy_api_surface_is_frozen_as_signal_evaluation_not_formal_backtest() -> None:
    api_surface = _load_json("api-surface.json")

    route_paths = {route["path"] for route in api_surface["routes"]}
    assert {
        "/api/v1/backtest/run",
        "/api/v1/backtest/results",
        "/api/v1/backtest/performance",
        "/api/v1/backtest/performance/{code}",
    } <= route_paths
    assert "/api/v1/quant/backtest-runs" not in route_paths

    schema_fields = api_surface["schemas"]
    assert "BacktestRunRequest" in schema_fields
    assert "BacktestResultItem" in schema_fields
    assert "PerformanceMetrics" in schema_fields
    assert "eval_window_days" in schema_fields["BacktestRunRequest"]["properties"]
    assert "simulated_return_pct" in schema_fields["BacktestResultItem"]["properties"]

    agent_tools = {tool["name"]: tool for tool in api_surface["agent_tools"]}
    assert set(agent_tools) == {
        "get_skill_backtest_summary",
        "get_stock_backtest_summary",
        "get_strategy_backtest_summary",
    }
    assert all(tool["policy"]["read_only"] is True for tool in agent_tools.values())
    assert all(tool["semantic_scope"] == "legacy_signal_evaluation" for tool in agent_tools.values())


def test_characterization_script_and_review_document_preserve_p4_boundaries() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    for term in [
        "SAL-P4-001",
        "BacktestEngine.evaluate_single",
        "BacktestEngine.evaluate_decision_signal",
        "api.v1.endpoints.backtest",
        "ALL_BACKTEST_TOOLS",
        "--update-snapshots",
    ]:
        assert term in script

    required_doc_terms = [
        "SAL-P4-001",
        "DSA Signal Evaluation",
        "legacy `/api/v1/backtest/*`",
        "not a formal portfolio backtest",
        "不得把 DSA Signal Evaluation 直接命名为正式组合回测",
        "SAL-P4-002",
        "SAL-P4-003",
        "未调用真实 Provider",
        "未调用真实 LLM",
        "未启动 Evidence Agent",
    ]
    missing = [term for term in required_doc_terms if term not in doc]
    assert missing == []
