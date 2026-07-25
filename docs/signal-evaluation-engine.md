# SignalEvaluationEngine 迁移记录

> 任务：`SAL-P4-002` 迁移为 `SignalEvaluationEngine`<br>
> 日期：2026-07-25<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 前置金标：[`DSA Signal Evaluation Characterization`](./dsa-signal-evaluation-characterization.md)<br>
> 结论：`SAL-P4-001` 快照保持完全一致；`SAL-P4-003` 可在本任务后单独启动正式 `BacktestSpec`

## 1. 交付结论

`SAL-P4-002` 已把当前 DSA legacy `BacktestEngine` 的真实语义迁移为 `SignalEvaluationEngine`。该引擎只负责历史 AI 建议的 T+N 后验信号评价，公开语义为：

```text
evaluation_type = signal
semantic_scope = legacy_signal_evaluation
engine_version = v1
```

Serenity root 新增纯 quant 模块 `src/serenity_alpha_lab/quant/signal_evaluation.py`，用 `SignalEvaluationConfig` 与 `SignalEvaluationEngine` 复刻 `SAL-P4-001` 冻结的文本信号、结构化 DecisionSignal 和汇总指标行为。模块保留 `EvaluationConfig`、`BacktestEngine`、`BacktestResultLike` 作为兼容别名，但文档和常量不再把该逻辑描述为正式组合回测。

DSA 隔离 worktree 通过 `DSA-PATCH-005` 新增 `src/core/signal_evaluation_engine.py`，并把 `backtest_service.py`、`decision_signal_outcome_service.py` 内部调用迁移到 `SignalEvaluationEngine` / `SignalEvaluationConfig`。Legacy `/api/v1/backtest/*` route、Pydantic `Backtest*` schema、数据库表和 Agent `get_*_backtest_summary` 只保留为兼容面。

## 2. 保持兼容

| 表面 | 本任务处理 | 兼容性 |
|---|---|---|
| `SAL-P4-001` JSON 快照 | 不改动 | `scripts/run-dsa-signal-evaluation-characterization.sh` 输出 match |
| Root quant API | 新增 `SignalEvaluationEngine`，导出兼容别名 | 新代码使用 signal 命名；旧命名只作桥接 |
| DSA backend | 新增 `src.core.signal_evaluation_engine`，服务内部改用 signal 命名 | legacy route/schema/table 不变 |
| DSA Web | 可见文案改为“信号评价 / Signal Evaluation” | legacy `/backtest` route 和 `/api/v1/backtest/*` client 保留 |
| Patch workflow | 新增 `0005-migrate-signal-evaluation-engine.patch` | `scripts/apply-dsa-baseline-patches.sh --check-only` 识别 `0001..0005` already applied |

## 3. 非目标

本任务没有定义 `BacktestSpec`，没有执行正式组合回测，没有接入 Qlib、Ledger、Order/Execution、Portfolio Risk、Quant Lab、Evidence Agent、Worker loop、真实 Provider 或真实 LLM。`SAL-P4-003` 必须在本任务之后单独处理正式组合回测输入、交易时间、费用、滑点、现金、持仓、组合账本、风险和偏差审计。

## 4. 验证记录

| 验证 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/quant/test_signal_evaluation_engine.py -q` | `3 passed` |
| `.venv/bin/python -m pytest tests/architecture/test_dsa_signal_evaluation_engine_migration.py -q` | `4 passed` |
| `.venv/bin/python -m pytest tests/quant/test_signal_evaluation_engine.py tests/architecture/test_dsa_signal_evaluation_engine_migration.py tests/architecture/test_dsa_signal_evaluation_characterization.py -q` | `11 passed` |
| `scripts/run-dsa-signal-evaluation-characterization.sh` | `DSA Signal Evaluation characterization snapshots match ...` |
| `scripts/apply-dsa-baseline-patches.sh --check-only` | `0001..0005` already applied |
| DSA Web focused Vitest | `3 passed files / 26 passed tests` |
| DSA Python focused suite | `95 passed, 1 warning` |

## 5. 后续入口

`SAL-P4-003` 现在可以进入 `READY`，但必须从正式 `BacktestSpec` 开始，不得复用 legacy Signal Evaluation 作为组合回测实现。所有正式回测结果必须与 legacy `/api/v1/backtest/*` 信号评价兼容面隔离。
