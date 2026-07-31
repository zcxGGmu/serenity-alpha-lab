# Factor Evaluation 记录

> 任务：`SAL-P3-009` 实现 Factor Evaluation<br>
> 日期：2026-07-24<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-010 DAG/CACHE AND SAL-P3-011 HISTORICAL UNIVERSE`

## 1. 交付结论

`SAL-P3-009` 已建立平台侧 Factor Evaluation 契约和离线确定性评价器。该层只消费已经产出的因子值、前瞻收益、显式 universe 成员和暴露字段，不计算原始因子、不读取 Provider、不解析 `latest` Dataset alias、不启动 Qlib/Quant Core，也不执行组合回测。

新增模块：

```text
src/serenity_alpha_lab/quant/factors/evaluation.py
```

新增测试：

```text
tests/quant/test_factor_evaluation.py
```

## 2. 契约对象

核心对象：

- `FutureReturnWindow`：版本化前瞻收益窗口，包含 horizon、unit、return field、窗口版本和 ICIR 年化周期。
- `FactorEvaluationSpec`：冻结 `quant.factor_evaluation@1.0.0` 评价参数，绑定 `run_id`、`stage_id`、`fdv_*` 因子版本、具体 Dataset Version、因子方向、分组数量、IC 样本下限、相关系数方法和暴露字段。
- `FactorEvaluationObservation`：单个 `instrument_id + trade_date` 的因子值、前瞻收益、PIT 时间、universe 状态和暴露字段。
- `FactorEvaluationReport`：覆盖率、IC/ICIR、分组收益、单调性、换手、暴露和 warning 的 JSON-friendly 结果。
- `publish_factor_evaluation_report()`：复用 P1 `ArtifactStore`，把报告按 deterministic JSON 发布为内容寻址 Artifact。

`FactorEvaluationSpec.dataset_versions` 必须全部是具体 `dsv_*` Dataset Version id；`latest` alias 被拒绝。`factor_version_id` 必须是 `fdv_*`，用于绑定已发布或审查过的因子定义版本。

## 3. 指标口径

覆盖率：

- `total_universe_count`：输入中 `in_universe=True` 的观察总数。
- `factor_observation_count`：有有限因子值的观察数。
- `return_observation_count`：有有限前瞻收益的观察数。
- `overlap_observation_count`：因子值和前瞻收益同时存在的交集样本。
- `coverage_ratio`：`factor_observation_count / total_universe_count`。
- `sample_overlap_ratio`：`overlap_observation_count / total_universe_count`。

IC/ICIR：

- 默认按交易日计算 Spearman IC，也支持 Pearson。
- 每日样本低于 `minimum_ic_observations` 时跳过并记录 warning。
- `mean_ic` 为有效日期 IC 均值；`ic_std` 为日期间样本标准差；`icir = mean_ic / ic_std * sqrt(annualization_periods)`，零方差时返回 `None` 并记录 warning。

分组收益与单调性：

- 每个交易日按因子值排序并切分为 `quantile_count` 组，组号从 1 到 N。
- `long_short_mean_return` 对 `higher_is_better` 使用 Top 组减 Bottom 组；对 `lower_is_better` 反向。
- 单调性使用分组号与组均收益的 Spearman 相关，并按因子方向给出 `direction_adjusted_score`。

换手：

- 默认比较相邻交易日的目标组成员。`higher_is_better` 使用 Top 组，`lower_is_better` 使用 Bottom 组。
- `turnover = 1 - retained_count / previous_count`；previous 为空时返回 `None` 并记录 warning。

暴露：

- 对 `spec.exposure_fields` 中每个暴露字段计算可用样本数、均值和与因子值的 Pearson 相关。
- 缺失暴露不会静默失败，会记录 `exposure_missing_values`。

## 4. PIT 与样本重叠保护

正式评价 `formal=True` 时，任何观察只要 `factor_available_at > decision_time` 就拒绝整次评价，错误消息包含 `PIT`。前瞻收益允许在未来才可用，因为它是评价标签，不参与决策。

Factor Evaluation 只在因子值与前瞻收益的交集样本上计算 IC、分组收益、单调性、换手和暴露。若存在 factor-only 或 return-only 样本，报告仍生成，但记录 `sample_non_overlap` warning，并在 coverage 中写明缺口。

## 5. Artifact 输出

`publish_factor_evaluation_report()` 使用：

- `schema_name = quant.factor_evaluation`
- `schema_version = 1.0.0`
- `content_type = application/json`
- `produced_by_run_id = spec.run_id`
- `produced_by_stage_id = spec.stage_id`

JSON payload 使用 `sort_keys=True` 和稳定缩进，同一报告重复发布会得到同一内容哈希和同一 Artifact manifest。

## 6. 明确未做事项

- 未执行原始因子公式，未发布 factor values Dataset。
- 未实现因子计算 DAG/cache、Historical Universe、ScreenDefinition、ScreenSnapshot、Quant Screening API 或 Screen Lab。
- 未启动 Quant Core、Qlib Adapter、Portfolio Backtest、Portfolio Ledger、Risk Engine 或 Evidence Agent。
- 未调用真实 Provider、真实 LLM 或 Worker execution loop。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 7. 本地验证

| 验证 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/quant/test_factor_evaluation.py -q` | Red：`1 error`，缺少 `serenity_alpha_lab.quant.factors.evaluation`；Green：`4 passed` |
| `.venv/bin/python -m pytest tests/quant/test_factor_evaluation.py tests/quant/test_factor_post_processing.py tests/quant/test_base_factor_definitions.py tests/quant/test_factor_dsl_contract.py tests/quant/test_factor_definition_contract.py -q` | PASS：`29 passed` |
| `.venv/bin/python -m pytest tests/quant/test_factor_evaluation.py tests/quant/test_factor_post_processing.py tests/quant/test_base_factor_definitions.py tests/quant/test_factor_dsl_contract.py tests/quant/test_factor_definition_contract.py tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`54 passed` |
| `.venv/bin/python -m pytest -q` | PASS：`284 passed, 3 skipped` |
| `.venv/bin/python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | PASS：`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

最终完整验证结果同步记录在 `AEV-058`。
