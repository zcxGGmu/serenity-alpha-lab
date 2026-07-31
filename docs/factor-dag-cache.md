# Factor DAG/cache 记录

> 任务：`SAL-P3-010` 实现因子计算 DAG 与缓存<br>
> 日期：2026-07-24<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-011 HISTORICAL UNIVERSE`

## 1. 交付结论

`SAL-P3-010` 已建立平台侧 Factor Engine DAG/cache 计划层。该层只编译因子依赖、公共子表达式、因子级数据依赖、缓存键、分区计划、增量重算计划和质量门控缓存 manifest，不执行真实因子数值、不读取 Provider、不解析 `latest` Dataset alias、不启动 Qlib/Quant Core，也不运行 ScreenDefinition 或正式回测。

新增模块：

```text
src/serenity_alpha_lab/quant/factors/engine.py
```

新增测试：

```text
tests/quant/test_factor_dag_cache.py
```

## 2. 契约对象

核心对象：

- `FactorDagBuildSpec`：冻结 `quant.factor_engine_dag@1.0.0` 构建参数，绑定 run/stage、具体 Dataset Version、`fdv_*` factor version、具体 universe version、date range 和 engine version。
- `FactorDagNode` / `FactorDag`：保存 DSL expression plan 展开的平台 DAG，按稳定节点身份去重公共子表达式，并保留 factor root、operator set、lookback metadata 和每个 factor 实际依赖的 Dataset Version 子集。
- `FactorCacheKey`：每个缓存分区的权威键，包含该 factor 实际依赖的 Dataset Version、factor version、universe version、date range、engine version、partition kind、trade date、instrument 和 partition id。
- `FactorCachePartition` / `FactorPartitionPlan`：表达时间序列与横截面分区计划，并记录 expected scan rows、partition count 和 max lookback periods。
- `FactorIncrementalChangeSet` / `FactorIncrementalRecomputePlan`：表达数据、factor version 或交易日变化触发的重算分区。
- `FactorCacheQualityGate` / `FactorCacheManifest`：表达缓存发布前质量门和 deterministic manifest 输出。

## 3. DAG 与公共子表达式

`build_factor_dag()` 复用 `compile_factor_definition()` 编译 `FactorDefinition` 的 DSL plan。DAG 节点身份由 operation、value type、value、parameters、source 和 child dependency ids 的稳定 JSON 哈希派生，多个因子共享相同子树时只保留一个节点，并把共享节点的 `factor_definition_ids` 扩展为所有使用方。

该层会校验：

- `FactorDagBuildSpec.dataset_versions` 全部为具体 `dsv_*`。
- `FactorDagBuildSpec.factor_versions` 全部为具体 `fdv_*`。
- `universe_version_id` 必须是具体 `dsv_*`，不得使用 `latest`。
- 已发布 `FactorDefinition.version_id` 必须与 `FactorDagBuildSpec.factor_versions[definition_id]` 完全一致。
- 每个 compiled plan 的 `dataset_versions` 必须能在 build spec 中找到完全一致的版本，并作为 `FactorDag.factor_dataset_versions` 写入 DAG。

## 4. 缓存键与分区

缓存键字段固定为：

- `dataset_versions`（该 factor 实际依赖的 Dataset Version 子集）
- `factor_definition_id`
- `factor_version_id`
- `universe_version_id`
- `date_range`
- `engine_version`
- `partition_id`
- `partition_kind`
- `trade_date`
- `instrument_id`（仅时间序列分区）

分区规则：

- 含 `delay` 或 `rolling_*` 的因子生成 `time_series` 分区，按 `instrument_id + trade_date` 切分，并记录 `start_date/end_date` 回看窗口。
- 含 `rank` 的因子生成 `cross_section` 分区，按 `trade_date` 切分。
- 无时间序列算子的简单因子默认生成横截面分区，避免全表 Python 循环。
- `plan_factor_cache_partitions()` 会去重重复 instrument/date 输入，拒绝超出 DAG `date_range` 的交易日，并要求 `FactorPartitionPlan.partition_id` 唯一。
- `FactorCacheKey` 与 `FactorCachePartition` 强制匹配 factor、version、partition kind、trade date、instrument 和 partition id；`time_series` 必须有 `instrument_id`，`cross_section` 不允许携带 `instrument_id`。
- `performance_budget` 当前记录 expected scan rows、partition count 和 max lookback periods，为后续 Polars/DuckDB 或真实执行器优化留证据。

## 5. 增量重算与质量门

`plan_incremental_factor_recompute()` 使用分区自身的 `start_date <= changed_trade_date <= end_date` 判断受影响窗口。新交易日只影响该交易日分区；历史日期变化会带动包含该日期的回看窗口分区。factor version 变化只重算对应 factor 的分区；dataset version 变化只重算 cache key 中声明依赖该 dataset 的 factor 分区，避免无关 Dataset 改版触发全量因子重算。

`publish_factor_cache_manifest()` 只允许 `FactorCacheQualityGate.status == passed` 时发布 deterministic JSON manifest。失败质量门直接拒绝发布，避免失败 run 污染共享缓存。

## 6. 明确未做事项

- 未执行因子公式，未计算或发布 factor values Dataset。
- 未实现 Historical Universe、ScreenDefinition、ScreenSnapshot、Quant Screening API 或 Screen Lab。
- 未启动 Quant Core、Qlib Adapter、Portfolio Backtest、Portfolio Ledger、Risk Engine 或 Evidence Agent。
- 未调用真实 Provider、真实 LLM 或 Worker execution loop。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 7. 本地验证

| 验证 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/quant/test_factor_dag_cache.py -q` | Red：初始缺少 `serenity_alpha_lab.quant.factors.engine` 时 `1 error`；评审回归 Red：`5 failed, 3 passed`；Green：`8 passed` |
| `.venv/bin/python -m pytest tests/quant/test_factor_dag_cache.py tests/quant/test_factor_evaluation.py tests/quant/test_factor_post_processing.py tests/quant/test_base_factor_definitions.py tests/quant/test_factor_dsl_contract.py tests/quant/test_factor_definition_contract.py -q` | PASS：`37 passed` |
| `.venv/bin/python -m pytest tests/quant/test_factor_dag_cache.py tests/quant/test_factor_evaluation.py tests/quant/test_factor_post_processing.py tests/quant/test_base_factor_definitions.py tests/quant/test_factor_dsl_contract.py tests/quant/test_factor_definition_contract.py tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`62 passed` |
| `.venv/bin/python -m pytest -q` | PASS：`292 passed, 3 skipped` |
| `.venv/bin/python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | PASS：`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

最终完整验证结果同步记录在 `AEV-059`。
