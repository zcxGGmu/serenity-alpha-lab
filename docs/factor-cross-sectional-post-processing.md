# 横截面因子后处理记录

> 任务：`SAL-P3-008` 实现横截面后处理<br>
> 日期：2026-07-24<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-009 FACTOR EVALUATION`

## 1. 交付结论

`SAL-P3-008` 已建立平台侧横截面因子后处理契约和确定性处理器。该层消费显式传入的同一交易日股票池快照，不读取 Provider、Dataset Catalog latest alias、历史窗口或外部运行时；输出 winsorize、缺失处理、中性化、标准化后的值、丢弃记录和 warning。

新增模块：

```text
src/serenity_alpha_lab/quant/factors/post_processing.py
```

新增测试：

```text
tests/quant/test_factor_post_processing.py
```

## 2. 契约对象

核心对象：

- `CrossSectionPostProcessingSpec`：冻结 `quant.factor_cross_section_post_processing@1.0.0` 参数 Schema，记录具体 Dataset Version、缺失策略、winsorize、中性化和标准化配置。
- `CrossSectionFactorValue`：单个候选证券在某交易日的原始因子值、行业、市值和附加 metadata；证券 ID 复用 canonical `InstrumentId`。
- `ProcessedCrossSectionFactorValue`：输出 raw、filled、step values、exposures 和最终 processed value。
- `CrossSectionPostProcessingResult`：批次输出，包含处理后值、被丢弃的原始行、warning 和原始 spec。
- `process_cross_sectional_factor_values()`：按 `trade_date` 分组处理，保证每个交易日只使用当日输入行。

`CrossSectionPostProcessingSpec.dataset_versions` 必须是具体 `dsv_*` Dataset Version id；`latest` alias 被拒绝。当前典型输入包括 `factor_values` 和 `instrument_master`，后续 Factor Engine/ScreenDefinition 可以扩展更多具体版本引用。

## 3. 执行顺序

处理器固定顺序：

```text
per trade_date explicit universe snapshot
  -> missing policy
  -> winsorization
  -> industry / log_market_cap neutralization
  -> z-score standardization
```

支持策略：

- 缺失值：`drop`、`fill_median`、`fill_constant`、`zero`。
- Winsorize：MAD clip（默认 `n_mad=3.0`）和 quantile clip。
- 中性化：行业哑变量和 `log_market_cap` OLS residual；缺行业进入 `__missing_industry__` bucket，缺市值可 `drop`、`fill_median` 或 `zero`（以市值 1.0 表达）。
- 标准化：横截面 z-score。

## 4. 边界行为

- 常量列：z-score 返回 0.0 并记录 `standardize_zero_variance`。
- 小样本：单证券分组返回 0.0 并记录 `standardize_small_sample` 或 `neutralize_small_sample`。
- 缺行业：不会静默丢弃，默认进入 `__missing_industry__` 并记录 `missing_industry_bucketed`。
- 缺市值：按配置填充或丢弃，并记录 `missing_market_cap_filled` / `missing_market_cap_dropped`。
- 极值：MAD/quantile winsorize 会在标准化前裁剪，并把中间值写入 `step_values["winsorized"]`。
- 矩阵秩不足：仍返回 least-squares residual，并记录 `neutralize_rank_deficient`。

## 5. 明确未做事项

- 未执行原始因子公式、未发布 factor values Dataset、未建立 Factor Engine 或 DAG/cache。
- 未实现 Factor Evaluation、IC/ICIR、分组收益、暴露报告、ScreenDefinition、ScreenSnapshot、Quant Screening API 或 Screen Lab。
- 未启动 Quant Core、Qlib Adapter、正式组合回测、Portfolio Ledger、Risk Engine 或 Evidence Agent。
- 未调用真实 Provider、真实 LLM 或 Worker execution loop。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 6. 本地验证

| 验证 | 结果 |
|---|---|
| `uv run --extra core --extra dev python -m pytest tests/quant/test_factor_post_processing.py -q` | Red：`1 error`，缺少 `serenity_alpha_lab.quant.factors.post_processing`；Green：`4 passed` |
| `uv run --extra core --extra dev python -m pytest tests/quant/test_factor_post_processing.py tests/quant/test_base_factor_definitions.py tests/quant/test_factor_dsl_contract.py tests/quant/test_factor_definition_contract.py -q` | PASS：`25 passed` |
| `uv run --extra core --extra dev python -m pytest tests/quant/test_factor_post_processing.py tests/quant/test_base_factor_definitions.py tests/quant/test_factor_dsl_contract.py tests/quant/test_factor_definition_contract.py tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`50 passed` |
| `uv run --extra core --extra dev python -m pytest -q` | PASS：`280 passed, 3 skipped` |
| `uv run --extra core --extra dev python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | PASS：`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

最终完整验证结果同步记录在 `AEV-057`。
