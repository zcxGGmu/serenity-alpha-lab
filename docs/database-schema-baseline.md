# DSA 数据库 Schema 与迁移样本基线记录

> 任务：`SAL-P0-009` 冻结数据库 Schema 与迁移样本<br>
> 日期：2026-07-19<br>
> 上游基线：`ZhuLinsen/daily_stock_analysis v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 运行入口：`scripts/run-dsa-database-baseline.sh`

## 1. 结论

`SAL-P0-009` 已完成。当前已冻结锁定 DSA 基线的 SQLite Schema、表/索引/外键元数据、可重建的脱敏历史库 SQL fixture、内容哈希与摘要文件。

本任务不修改 DSA 上游源码，不引入 Alembic，也不把 DSA 源码合入本项目工作树。数据库基线仍来自隔离 worktree `.worktrees/dsa-v3.26.1` 的 `src.storage.Base.metadata.create_all()` 与 `DatabaseManager` 启动时的兼容迁移逻辑。

脚本会把 `fixture.sql` 恢复到临时 SQLite 数据库，重新开启外键后执行 `PRAGMA foreign_key_check`，并比较恢复前后的表行数与内容哈希；该验证结果写入 `summary.json`。

## 2. 产物

提交产物位于 `docs/baselines/dsa-v3.26.1/database/`：

| 文件 | 作用 |
|---|---|
| `schema.sql` | 稳定排序后的 SQLite table/index DDL dump |
| `schema-metadata.json` | 表、字段、索引、外键、行数、建表 SQL 与表内容哈希 |
| `fixture.sql` | 可重建脱敏历史库的稳定 SQL fixture |
| `fixture-summary.json` | fixture 覆盖范围、行数与脱敏声明 |
| `content-hashes.json` | 已提交文件与每张表内容哈希 |
| `summary.json` | Gate/CI 使用的摘要和 PASS 条件 |

运行时还会生成 SQLite 文件：

```text
.cache/dsa-p0/database-baseline-artifacts/generated/fixture.sqlite
```

该二进制文件不提交。原因是相同表内容下 SQLite 文件页/header 字节仍可能因内部写入顺序产生不同 SHA；CI 使用稳定 SQL/JSON 快照和表内容哈希做漂移检测，运行时 SQLite 只作为可复查 fixture。

## 3. Fixture 覆盖

脱敏 fixture 使用固定时钟 `2026-01-05T09:30:00`，仅包含合成数据，无密钥、Cookie、真实 Token、个人数据或本机路径。

| 覆盖项 | 表 | 结果 |
|---|---|---|
| 分析历史 | `analysis_history`、`news_intel`、`fundamental_snapshot` | 覆盖，含单股报告与市场复盘历史行 |
| 信号评价 | `backtest_results`、`backtest_summaries`、`decision_signals`、`decision_signal_outcomes`、`decision_signal_feedback` | 覆盖 |
| 持仓/组合 | `portfolio_accounts`、`portfolio_trades`、`portfolio_cash_ledger`、`portfolio_positions`、`portfolio_daily_snapshots` | 覆盖 |
| 会话 | `conversation_messages`、`conversation_summaries`、`agent_provider_turns` | 覆盖 Agent 对话/Provider trace 会话 |
| LLM usage | `llm_usage` | 覆盖 |
| Schema 版本 | `schema_migrations` | 覆盖，版本为 `2026-06-05-create-all-baseline` |

说明：DSA `v3.26.1` 的管理员认证密码、盐和 signed-cookie session 不是 SQLite 表，而是文件/内存状态；本数据库 fixture 不包含认证 secret。本任务用 Agent conversation/session 表覆盖持久化会话数据口径，并在 `summary.json` 中显式记录 auth session 不落库。

## 4. 摘要

| 指标 | 值 |
|---|---:|
| 表数量 | 28 |
| 索引数量 | 177 |
| fixture 总行数 | 31 |
| `fixture.sql` SHA-256 | `382f4719d813f20b233786d90b0b5de66637a40d7ae35de61c69c4b0f57fa931` |
| `schema.sql` SHA-256 | `8d39743b05e5f6b6b7417805ced0fc27d5e5323d2ac04f791ac22c50038a5a51` |
| `schema-metadata.json` SHA-256 | `c17c0038814e27bebced45be9d5edc2deb1f28b6b5036639b730323b6aa7f7ae` |

权威摘要见 [database summary](./baselines/dsa-v3.26.1/database/summary.json)。

## 5. 复跑命令

首次生成或有意更新快照：

```bash
scripts/run-dsa-database-baseline.sh --update-snapshots
```

CI/本地验证：

```bash
scripts/run-dsa-database-baseline.sh
```

每次验证会检查：

- 锁定 tag 与隔离 worktree 都解析到 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。
- DSA worktree 的 tracked diff 只来自已登记 patch，untracked 只允许缓存/构建生成物。
- `fixture.sql` 可恢复、`PRAGMA foreign_key_check` 无违规，恢复前后行数与内容哈希一致。
- SQL/JSON 快照与 `docs/baselines/dsa-v3.26.1/database/` 中的提交文件一致。

本次验证已连续运行：

```text
scripts/run-dsa-database-baseline.sh --update-snapshots
scripts/run-dsa-database-baseline.sh
scripts/run-dsa-database-baseline.sh
```

结果：两次非更新复跑均输出 `Database baseline snapshots match docs/baselines/dsa-v3.26.1/database`；`summary.json` 中 `fixture_sql_round_trip_passed`、`foreign_key_check_passed`、`restored_row_counts_match`、`restored_content_hashes_match` 均为 `true`。

## 6. 限制与后续

- 本任务冻结 DSA 当前 `create_all` + 兼容迁移后的实际 SQLite 形状，不把 Alembic 引入 P0；Alembic baseline 属于 `SAL-P1-012`。
- fixture 是合成脱敏样本，不代表真实生产历史库规模、Provider 数据质量或正式 PIT 数据。
- `fixture.sql` 可重建小型历史库；`.cache` 中运行时 `fixture.sqlite` 仅用于本机/CI 复查，不提交。
- 后续 `SAL-P1-013` 需要基于本 fixture 执行 expand/backfill/verify 迁移演练。
