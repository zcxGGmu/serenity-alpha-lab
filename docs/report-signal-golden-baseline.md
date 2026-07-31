# DSA 报告与信号评价金标基线记录

> 任务：`SAL-P0-010` 冻结报告与信号评价金标<br>
> 执行日期：2026-07-20<br>
> 上游基线：`upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 运行入口：`scripts/run-dsa-report-signal-baseline.sh`<br>
> 当前状态：`DONE`

## 1. 执行结论

`SAL-P0-010` 已完成。当前已冻结锁定 DSA 基线的结构化报告解析、单股 Markdown、聚合 Markdown、市场复盘 Markdown、DecisionSignal 摘要和 Signal Evaluation 指标金标。

本任务只使用离线 fixture 和 Stub LLM JSON，不触发真实 Provider、真实 LLM、Scheduler、Bot/Webhook 或通知发送。脚本在隔离 worktree `.worktrees/dsa-v3.26.1` 上应用已登记补丁 `DSA-PATCH-001` 至 `DSA-PATCH-003` 后生成 `.cache` 产物，并默认与已提交快照做 byte-for-byte diff。

脚本固定通知渲染时间为 `2026-01-05T09:30:00`，并把 `summary.json.generated_at` 固定为 `2026-07-19T00:00:00Z`，用于稳定快照；本记录的实际执行日期为 `2026-07-20`。

## 2. 快照产物

提交产物位于 `docs/baselines/dsa-v3.26.1/report-signal/`：

| 文件 | 作用 |
|---|---|
| `inputs.json` | 固定股票、市场复盘 payload、Signal Evaluation bars 和评价配置 |
| `stub-llm-responses.json` | 离线 Stub LLM 原始 JSON 响应 |
| `structured-reports.json` | `GeminiAnalyzer._parse_response()` 解析输出、Schema 和完整性校验 |
| `single-stock-report.md` | `NotificationService.generate_single_stock_report()` 单股 Markdown 金标 |
| `aggregate-report.md` | `NotificationService.generate_aggregate_report()` 聚合 Markdown 金标 |
| `market-review-payload.json` | 市场复盘结构化输入 |
| `market-review-report.md` | `_render_market_review_payload_markdown()` 市场复盘 Markdown 金标 |
| `signal-evaluations.json` | 6 个 Signal Evaluation 明细金标 |
| `signal-evaluation-summary.json` | `BacktestEngine.compute_summary()` 指标汇总金标 |
| `decision-signal-summary.json` | DecisionSignal summary 与报告 excerpt 金标 |
| `content-hashes.json` | 文件 SHA-256 与逻辑内容哈希 |
| `summary.json` | Gate/CI 使用的摘要、覆盖范围和 PASS 条件 |

## 3. 覆盖范围

| 覆盖项 | 来源 | 结果 |
|---|---|---|
| 结构化报告 | 2 个 Stub LLM 响应，股票 `600519` 与 `AAPL` | 覆盖；通过 `AnalysisReportSchema.model_validate()` 与 `check_content_integrity()` |
| 单股报告 | `NotificationService.generate_single_stock_report()` | 覆盖；包含贵州茅台、核心结论、战术计划和信号归因 |
| 聚合报告 | `NotificationService.generate_aggregate_report()` | 覆盖；包含 2 只股票和固定报告日期 `2026-01-05` |
| 市场复盘 | `_render_market_review_payload_markdown()` | 覆盖；包含大盘复盘、资金方向和板块主线 |
| Signal Evaluation | `BacktestEngine.evaluate_single()` 与 `BacktestEngine.compute_summary()` | 覆盖买入止盈、卖出方向正确、持有亏损、观望、止损/止盈同日歧义和数据不足 |
| DecisionSignal 摘要 | `summarize_decision_signal()` 与 `format_decision_signal_excerpt()` | 覆盖结构化摘要和中文报告 excerpt |

## 4. 摘要指标

| 指标 | 值 |
|---|---:|
| 结构化报告数量 | 2 |
| Markdown 报告数量 | 3 |
| Signal Evaluation cases | 6 |
| `total_evaluations` | 6 |
| `completed_count` | 5 |
| `insufficient_count` | 1 |
| `direction_accuracy_pct` | 60.0 |
| `win_rate_pct` | 60.0 |
| `stop_loss_trigger_rate` | 33.33 |
| `take_profit_trigger_rate` | 66.67 |
| `ambiguous_rate` | 33.33 |

权威摘要见 [report/signal summary](./baselines/dsa-v3.26.1/report-signal/summary.json)。

## 5. 内容哈希

| Artifact | SHA-256 |
|---|---|
| `inputs.json` | `22798d946c647640bc643819664d6faa2b64c3c11b197cf21ab3f8ff5a8430ad` |
| `stub-llm-responses.json` | `18deb63a8ca6afb63a8d705402f12f5cb4b2acea33500d8d25db15335ed91c70` |
| `structured-reports.json` | `6eb167abbaf546a1f7318bbc62eeab023d32ce58e4ace8896cd1c5f9c86b0fd0` |
| `single-stock-report.md` | `a103811b18bd7caf20e18e491e348995928932d17eede6c3440319caeb4ec86a` |
| `aggregate-report.md` | `29286358099a31a69a9992b4fe1b5fccc392e348b7d9eea53b127b4d9ba7e50d` |
| `market-review-payload.json` | `9204a045d68192ed5193b8360ffdb639be8ee3939dafc7931ca06eaf94481fd4` |
| `market-review-report.md` | `bfc9164b19553db5f58f1dad105ff8aef37234765bab77ef37e40bf19995d5d5` |
| `signal-evaluations.json` | `7f0d5eec142b8cf9b3e415be2c88df60a4e71a4ad71a50058572f1101ee8804c` |
| `signal-evaluation-summary.json` | `54f1bc63cf3aabadede28d7f09012833386dcc414f8797f77ac5cde301a80940` |
| `decision-signal-summary.json` | `63e8dc93d7a2ee762844bd9c9099ef8888cb6161d54c9c302e3d8679df8bbf64` |
| `content-hashes.json` | `19ba57a789ff1fafdbac737706206129d8a2d7f3281a4aac3d264c1af45e1042` |
| `summary.json` | `01e7c0ec1a7070f5e7923414e7ef57f1ef5eb40d9c3bbf26da4ce3529bed0adb` |

## 6. 复跑与 CI 用法

首次生成或有意更新快照：

```bash
scripts/run-dsa-report-signal-baseline.sh --update-snapshots
```

CI/PR 默认检查：

```bash
scripts/run-dsa-report-signal-baseline.sh
```

脚本执行步骤：

1. 校验本地 tag `upstream/dsa-v3.26.1` 和隔离 worktree HEAD 都指向 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。
2. 通过 `scripts/apply-dsa-baseline-patches.sh` 幂等应用 `DSA-PATCH-001` 至 `DSA-PATCH-003`。
3. 校验 DSA worktree diff 只包含登记补丁或允许的生成缓存。
4. 使用空 env、固定时钟、Stub LLM JSON 和 `.cache/dsa-p0/venv` 生成报告与 Signal Evaluation 产物。
5. 默认模式与 `docs/baselines/dsa-v3.26.1/report-signal/` 做 byte-for-byte diff；差异写入 `.cache/dsa-p0/report-signal-baseline-artifacts/diff/`。

为避免 CI 因 LiteLLM 远程模型价格表拉取而变慢，脚本显式设置 `LITELLM_LOCAL_MODEL_COST_MAP=True`。

## 7. 验证结果

| 命令 | 结果 |
|---|---|
| `bash -n scripts/run-dsa-report-signal-baseline.sh` | 通过 |
| `scripts/run-dsa-report-signal-baseline.sh --update-snapshots` | 通过；12 个 committed snapshot 更新到 `docs/baselines/dsa-v3.26.1/report-signal/` |
| `scripts/run-dsa-report-signal-baseline.sh` | 通过；输出 `Report/signal baseline snapshots match docs/baselines/dsa-v3.26.1/report-signal`，未触发 LiteLLM 远程 cost map warning |
| `PYTHONPATH="$PWD" LITELLM_LOCAL_MODEL_COST_MAP=True ../../.cache/dsa-p0/venv/bin/python -m pytest tests/test_report_schema.py tests/test_report_renderer.py tests/test_notification_report_fixtures.py tests/test_decision_signal_summary.py tests/test_backtest_summary.py tests/test_signal_attribution.py tests/test_signal_attribution_e2e.py tests/test_backtest_service.py -q` | 通过；137 passed，6 warnings |

`summary.json` 中以下 PASS 条件均为 `true`：

- `required_coverage_passed`
- `schema_validation_passed`
- `content_integrity_passed`
- `secret_scan_passed`
- `uses_stub_llm_only`
- `real_provider_calls_zero`
- `real_notification_sends_zero`

## 8. 不做事项与限制

- 不调用真实 LLM，不读取真实 Provider，不启动 Scheduler，不发送真实通知。
- 不把 `.cache/dsa-p0` 中的生成目录、diff、空 env 或运行日志提交到仓库。
- 不把 `.worktrees/dsa-v3.26.1` 中的 DSA 源码复制进本项目工作树。
- 不将当前 Signal Evaluation 金标解释为正式组合回测；真实组合回测、PIT 数据、交易成本、Ledger 和风控仍属于 P4。
- 不将 Gate G0 标记为完成；`SAL-P0-012` 和 `SAL-P0-013` 仍需完成。
