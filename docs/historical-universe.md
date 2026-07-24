# Historical Universe 记录

> 任务：`SAL-P3-011` 实现 Historical Universe<br>
> 日期：2026-07-24<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-012 SCREENDEFINITION`

## 1. 交付结论

`SAL-P3-011` 已建立平台侧 L0 Historical Universe 契约和确定性快照构建器。该层只构建历史股票池和可交易性硬过滤，使用 Instrument Master、Trading Calendar、Raw Daily Bars 和显式 Instrument Trade Status 输入，不执行 AlphaSift、因子值计算、ScreenDefinition、组合回测、Evidence Agent、真实 Provider/LLM 调用或 Worker runtime。

新增模块：

```text
src/serenity_alpha_lab/quant/screening/universe.py
```

新增测试：

```text
tests/quant/test_historical_universe.py
```

## 2. 契约对象

核心对象：

- `UniverseDefinition`：冻结 `quant.historical_universe@1.0.0` 定义，绑定市场、具体 Dataset Version、最小上市交易日、ST/停牌/日线可用性硬过滤开关和创建审计信息。
- `UniverseInstrumentTradeStatus`：表达单证券单交易日的显式可交易状态，支持 `tradable`、`suspended` 和 `unknown`，并保留 Bronze 来源证据。
- `UniverseDataEvidence`：每条纳入或排除证据的标准记录，包含 dataset name、具体 `dsv_*` version、Bronze source、字段名和观测值。
- `UniverseMember` / `UniverseExclusion`：分别表达入池证券和硬过滤淘汰记录；每条 exclusion 必须包含 `rule_id`、`rule_version`、severity 和 evidence。
- `UniverseSnapshot`：表达某个 `as_of` 决策日的确定性 L0 股票池、排除轨迹、Dataset Version map 和派生 `universe_version_id`。

## 3. PIT 与版本约束

`UniverseDefinition.dataset_versions` 必须包含并绑定具体版本：

- `instrument_master`
- `trading_calendar`
- `raw_daily_bars`
- `instrument_trade_status`

所有版本必须是 `dsv_*`，`latest` 被拒绝。`build_historical_universe_snapshot()` 使用 `InstrumentMasterDataset.query_as_of(as_of, include_inactive=True)` 读取历史状态，不使用当前成分、当前上市状态或当前 ST 状态；`as_of` 必须是对应市场 Trading Calendar 中的交易日。

## 4. 硬过滤规则

当前 L0 规则按固定顺序执行：

| Rule ID | 语义 | 证据来源 |
|---|---|---|
| `listing_status_active` | 只允许 as-of active 且未在决策日前退市的证券 | Instrument Master `listing_status` / `delisted_on` |
| `min_listing_trading_days` | 按 Trading Calendar 计算上市以来交易日数量，低于阈值排除 | Instrument Master `listed_on` + Trading Calendar |
| `not_st` | `exclude_st=True` 时排除 as-of ST 标记证券 | Instrument Master `is_st` |
| `not_suspended` | `exclude_suspended=True` 时排除显式 suspended 状态 | Instrument Trade Status `status` |
| `daily_bar_available` | `require_daily_bar=True` 时要求决策日 Raw Daily Bar 存在 | Raw Daily Bars `instrument_id + trade_date` |

排除记录是权威结构化轨迹，后续 ScreenSnapshot 可以直接引用；人类说明不得覆盖 `rule_id` 和 evidence。

## 5. 快照与发布

`UniverseSnapshot.universe_version_id` 从快照有效载荷稳定哈希派生，格式为 `dsv_<32 hex>`。`publish_historical_universe_snapshot()` 使用既有 `ArtifactStore` 发布 deterministic JSON：

- schema name：`quant.historical_universe_snapshot`
- schema version：`1.0.0`
- content type：`application/vnd.serenity.quant.historical-universe+json`

同一快照重复发布得到相同 Artifact ID 和 SHA-256。

## 6. 明确未做事项

- 未实现 `ScreenDefinition`、L0~L4 pipeline、ScreenSnapshot、Quant Screening API 或 Screen Lab。
- 未执行 AlphaSift、因子值计算、因子缓存执行、组合约束、Portfolio Backtest、Qlib Adapter 或 Risk Engine。
- 未启动 Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用或 Worker execution loop。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 7. 本地验证

| 验证 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/quant/test_historical_universe.py -q` | Red：初始缺少 `serenity_alpha_lab.quant.screening.universe` 时 `1 error`；Green：`4 passed` |
| `.venv/bin/python -m pytest tests/quant/test_historical_universe.py tests/datasets/test_instrument_master.py tests/datasets/test_trading_calendar.py tests/datasets/test_raw_daily_bars.py tests/quant/test_factor_dag_cache.py tests/quant/test_factor_post_processing.py tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`45 passed` |
| `.venv/bin/python -m pytest -q` | PASS：`296 passed, 3 skipped` |
| `.venv/bin/python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | PASS：`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

最终完整验证结果同步记录在 `AEV-060`。
