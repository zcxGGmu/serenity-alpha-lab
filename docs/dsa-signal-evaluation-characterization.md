# DSA Signal Evaluation Characterization

> 任务：`SAL-P4-001` 锁定 DSA Signal Evaluation 行为<br>
> 日期：2026-07-25<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 运行入口：`scripts/run-dsa-signal-evaluation-characterization.sh`<br>
> 结论：`APPROVED FOR SAL-P4-002`

## 1. 交付结论

`SAL-P4-001` 已冻结当前 DSA Signal Evaluation 行为和 legacy `/api/v1/backtest/*` API 金标。这里的 DSA `BacktestEngine` 只把历史报告或结构化 DecisionSignal 映射为 T+N 后验信号评价：用分析日后的日线窗口判断方向、止盈止损触达、模拟 long/cash 收益和汇总统计。

This is not a formal portfolio backtest. 当前 legacy `/api/v1/backtest/*` 名称只作为 DSA 兼容面保留；不得把 DSA Signal Evaluation 直接命名为正式组合回测。正式组合回测必须等待 `SAL-P4-003` BacktestSpec 定义交易时间、费用、滑点、现金、持仓、组合账本、风险和偏差审计。

新增产物：

```text
scripts/run-dsa-signal-evaluation-characterization.sh
docs/baselines/dsa-v3.26.1/signal-evaluation-characterization/
tests/architecture/test_dsa_signal_evaluation_characterization.py
```

本任务未调用真实 Provider，未调用真实 LLM，未启动 Evidence Agent，未启动 Worker execution loop，未定义 BacktestSpec，未执行正式组合回测，未迁移 DSA runtime source。

## 2. 冻结语义

### 2.1 `BacktestEngine.evaluate_single`

当前文本型报告评价流程：

- 从 `operation_advice` 推断 `direction_expected`：买入/加仓为 `up`，卖出/减仓为 `down`，持有为 `not_down`，观望/等待为 `flat`。
- 从 `operation_advice` 推断 `position_recommendation`：看多/持有为 `long`，卖出/观望为 `cash`。
- 使用固定 `eval_window_days=3` 和 `neutral_band_pct=2.0` 评价 T+N 收益。
- 只模拟 long/cash：`cash` 的 `simulated_return_pct=0.0`；`long` 用 start price 入场，并用止损、止盈或窗口末 close 退出。
- 同一日 stop-loss 和 take-profit 同时触发时，记录 `first_hit=ambiguous`，并按 `ambiguous_stop_loss` 退出。
- 缺少 forward bars 时返回 `eval_status=insufficient_data`；末日 close 缺失仍返回 `completed`，但收益、方向和模拟收益为 `null`。

### 2.2 `BacktestEngine.evaluate_decision_signal`

结构化 DecisionSignal 评价不走文本推断，直接使用 `direction_expected`：

- `up`：收益超过中性带为 `hit`，低于负中性带为 `miss`。
- `not_down`：收益非负为 `hit`，低于负中性带为 `miss`。
- `not_up`：收益不高于中性带为 `hit`。
- 无效 anchor price、forward bars 不足或末日 close 缺失返回 `eval_status=unable` 和 `unable_reason`。

## 3. Baseline 快照

提交目录：`docs/baselines/dsa-v3.26.1/signal-evaluation-characterization/`

| 文件 | 作用 | SHA-256 |
|---|---|---|
| `inputs.json` | 固定输入、配置、文本信号和结构化 DecisionSignal cases | `4c7acf3b7b32b88934922e866a7902ec53cde61d5b82eae25e2be8b6bd46e880` |
| `engine-evaluations.json` | `BacktestEngine.evaluate_single()` 11 个行为金标 | `b0c44de279becea790ed06b3e162975dd66eda06ee17fd65831b95866012029f` |
| `decision-signal-evaluations.json` | `BacktestEngine.evaluate_decision_signal()` 5 个结构化信号金标 | `f519a7dcfaed2664a1ed124357230b6edc949224132a0c9632120765118533e1` |
| `signal-evaluation-summary.json` | `BacktestEngine.compute_summary()` 汇总指标金标 | `107707e41fb8bb1012b83eebeb8486ba005677225de9264504a4bcae4b48b2b2` |
| `api-surface.json` | legacy `/api/v1/backtest/*` route、schema 和 Agent read-tool 金标 | `7b1870253ab079f5416c584fca941e3e1f4419bf75c893e7956d25600e3f56d7` |
| `content-hashes.json` | 快照内容哈希清单 | `1efa1ffb6f07cd2ea8db8383090879dcf1e0ec85f1723094102fc926f18191ef` |
| `summary.json` | P4 Gate/CI 使用摘要 | 由 `scripts/run-dsa-signal-evaluation-characterization.sh` 生成并比较 |

## 4. 覆盖范围

| 覆盖项 | 金标 case | 锁定行为 |
|---|---|---|
| 买入止盈 | `buy_take_profit` | `long`，首日 take-profit，模拟收益 `5.0%` |
| 卖出方向正确 | `sell_direction_win` | `cash`，下跌为 `win`，模拟收益 `0.0%` |
| 持有下跌 | `hold_loss` | `not_down`，下跌超过中性带为 `loss` |
| 观望横盘 | `watch_flat_win` | `flat`，中性带内为 `win` |
| 止盈止损同日歧义 | `buy_ambiguous_stop_first` | `first_hit=ambiguous`，退出原因为 `ambiguous_stop_loss` |
| 数据不足 | `buy_insufficient_data` | `eval_status=insufficient_data` |
| 否定买入文本 | `negated_buy_wait_cash` | `不要买入` 识别为 `cash/flat` |
| 否定卖出文本 | `negated_sell_hold_long`、`english_negated_sell_hold` | 否定 sell 后继续持有识别为 `long/not_down` |
| 末日 close 缺失 | `missing_end_close` | `completed`，收益与方向结果为 `null` |
| high/low 缺失 | `missing_high_low` | 不触发止盈止损，但按 close 计算收益 |
| 结构化信号 | `decision_*` | 锁定 `hit/miss/unable` 与 `unable_reason` |

## 5. 汇总指标

当前 11 个文本型 Signal Evaluation cases 的汇总指标：

| 指标 | 值 |
|---|---:|
| `total_evaluations` | 11 |
| `completed_count` | 10 |
| `insufficient_count` | 1 |
| `direction_accuracy_pct` | 66.67 |
| `win_rate_pct` | 66.67 |
| `avg_stock_return_pct` | 0.5556 |
| `avg_simulated_return_pct` | 0.0 |
| `stop_loss_trigger_rate` | 14.29 |
| `take_profit_trigger_rate` | 28.57 |
| `ambiguous_rate` | 14.29 |

这些指标是信号评价统计，不代表组合收益、净值曲线、资金曲线、交易成本后收益或可投资组合绩效。

## 6. API 金标

`api-surface.json` 冻结 4 个 legacy route：

| Route | Method | Response model | 当前语义 |
|---|---|---|---|
| `/api/v1/backtest/run` | `POST` | `BacktestRunResponse` | 触发历史报告 Signal Evaluation 并写入 legacy DSA 表 |
| `/api/v1/backtest/results` | `GET` | `BacktestResultsResponse` | 查询 Signal Evaluation 明细 |
| `/api/v1/backtest/performance` | `GET` | `PerformanceMetrics` | 查询整体 Signal Evaluation 汇总 |
| `/api/v1/backtest/performance/{code}` | `GET` | `PerformanceMetrics` | 查询单股 Signal Evaluation 汇总 |

同时冻结 5 个 Pydantic schema：

```text
BacktestRunRequest
BacktestRunResponse
BacktestResultItem
BacktestResultsResponse
PerformanceMetrics
```

Agent read tools 仅为只读 Signal Evaluation 查询面：

```text
get_skill_backtest_summary
get_strategy_backtest_summary
get_stock_backtest_summary
```

这些工具的 `semantic_scope` 在金标中标注为 `legacy_signal_evaluation`；`get_skill_backtest_summary` 在缺少真实 skill-scoped rollups 时不能伪造指标。

## 7. 复跑方式

首次生成或有意更新快照：

```bash
scripts/run-dsa-signal-evaluation-characterization.sh --update-snapshots
```

CI/PR 默认检查：

```bash
scripts/run-dsa-signal-evaluation-characterization.sh
```

脚本流程：

1. 校验 `upstream/dsa-v3.26.1` 和 `.worktrees/dsa-v3.26.1` 均指向 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。
2. 幂等应用 `DSA-PATCH-001` 至 `DSA-PATCH-004`。
3. 验证 DSA worktree 只包含登记 patch 或允许的生成缓存。
4. 使用固定离线输入调用 `BacktestEngine.evaluate_single`、`BacktestEngine.evaluate_decision_signal`、API schema introspection 和 `ALL_BACKTEST_TOOLS` metadata。
5. 默认模式与提交快照做 byte-for-byte diff。

## 8. 本地验证

| 验证 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/architecture/test_dsa_signal_evaluation_characterization.py -q` | Red：初始 `5 failed`，缺少 P4 characterization baseline、脚本和证据文档；Green 结果见本任务最终 review |
| `bash -n scripts/run-dsa-signal-evaluation-characterization.sh` | PASS |
| `scripts/run-dsa-signal-evaluation-characterization.sh --update-snapshots` | PASS，生成 7 个 committed snapshot |
| `scripts/run-dsa-signal-evaluation-characterization.sh` | PASS，输出 `DSA Signal Evaluation characterization snapshots match ...` |

## 9. 后续约束

- `SAL-P4-002` 可以在本金标基础上迁移为 `SignalEvaluationEngine`，并必须保持 P4-001 快照完全一致。
- `SAL-P4-002` 完成后才能启动 `SAL-P4-003` 定义正式 `BacktestSpec`；正式组合回测 API 必须与 legacy `/api/v1/backtest/*` 分离。
- P4 后续不得将 AlphaSift T+N evaluation、DSA Signal Evaluation 或 Screen result 直接命名为正式组合回测。
- 真实 Provider/LLM 仍只能在后续 Worker/调度任务中通过 profile guard、离线契约、fallback trace、ProblemDetails、Trace、Artifact 和 Run/Stage/Event 接入。
