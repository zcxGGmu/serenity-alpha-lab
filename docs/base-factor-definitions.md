# 基础因子定义记录

> 任务：`SAL-P3-007` 交付首批 15 个基础因子<br>
> 日期：2026-07-24<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-008 CROSS-SECTIONAL POST-PROCESSING`

## 1. 交付结论

`SAL-P3-007` 已发布平台首批基础因子 catalog。该 catalog 位于 Quant 因子层，只输出 `FactorDefinition` draft 和 DSL 编译计划金标，供后续横截面后处理、Factor Engine、DAG/cache、ScreenDefinition 和 Factor Evaluation 消费。

新增模块：

```text
src/serenity_alpha_lab/quant/factors/base_factors.py
```

新增测试：

```text
tests/quant/test_base_factor_definitions.py
```

## 2. Catalog 契约

核心对象：

- `BaseFactorCatalog`：冻结 `base_factor_catalog@1.0.0`，包含 15 个基础因子定义和分类计数。
- `BaseFactorSpec` / `BaseFactorInputSpec`：声明公式、输入、窗口、方向、类别、数据需求和手工 DSL plan reference。
- `base_factor_definitions()`：生成 15 个 `FactorDefinition` draft，默认绑定具体 `dsv_*` Dataset Version，并支持后续通过显式 `dataset_versions` 覆盖重新生成。
- `compile_base_factor_plans()`：复用 `SAL-P3-006` 的 `compile_factor_definition()`，并把编译结果与手工 reference plan 对齐校验。

默认 Dataset Version 引用：

| Dataset | 默认版本 | 用途 |
|---|---|---|
| `fundamentals_pit` | `dsv_77777777777777777777777777777777` | PIT 财务、估值、成长和质量指标 |
| `adjusted_daily_bars` | `dsv_88888888888888888888888888888888` | 前/后复权日线的 close、volume、amount |

这些默认值是 catalog-level concrete references，不是 `latest` alias；正式运行可在创建 Screen/Factor Run 前传入已发布 Dataset Catalog 版本覆盖。

## 3. 因子清单

| 因子 ID | 类别 | 方向 | 公式 | 窗口 | 数据需求 |
|---|---|---|---|---|---|
| `roe_ttm` | quality | higher | `roe_ttm` | 0 | PIT `roe_ttm` |
| `gross_margin_ttm` | quality | higher | `gross_margin_ttm` | 0 | PIT `gross_margin_ttm` |
| `cash_flow_to_assets_ttm` | quality | higher | `operating_cash_flow_ttm / total_assets` | 0 | PIT `operating_cash_flow_ttm`, `total_assets` |
| `earnings_yield_ttm` | valuation | higher | `net_profit_ttm / market_cap` | 0 | PIT `net_profit_ttm`, `market_cap` |
| `book_to_market` | valuation | higher | `book_value / market_cap` | 0 | PIT `book_value`, `market_cap` |
| `sales_yield_ttm` | valuation | higher | `revenue_ttm / market_cap` | 0 | PIT `revenue_ttm`, `market_cap` |
| `revenue_growth_yoy` | growth | higher | `revenue_ttm / delay(revenue_ttm, 252) - 1` | 252d | PIT `revenue_ttm` |
| `net_profit_growth_yoy` | growth | higher | `net_profit_ttm / delay(net_profit_ttm, 252) - 1` | 252d | PIT `net_profit_ttm` |
| `roe_change_yoy` | growth | higher | `roe_ttm - delay(roe_ttm, 252)` | 252d | PIT `roe_ttm` |
| `momentum_20d` | momentum | higher | `close / delay(close, 20) - 1` | 20d | adjusted close |
| `momentum_60d` | momentum | higher | `close / delay(close, 60) - 1` | 60d | adjusted close |
| `volatility_20d` | volatility | lower | `rolling_std(close / delay(close, 1) - 1, 20)` | 21d | adjusted close |
| `downside_volatility_20d` | volatility | lower | `rolling_std(where(close / delay(close, 1) - 1 < 0, close / delay(close, 1) - 1, 0), 20)` | 21d | adjusted close |
| `amount_liquidity_20d` | liquidity | higher | `rolling_mean(amount, 20)` | 20d | adjusted amount |
| `volume_liquidity_20d` | liquidity | higher | `rolling_mean(volume, 20)` | 20d | adjusted volume |

## 4. 关键校验

- Catalog 必须正好包含 15 个因子，且 ID 顺序稳定。
- 分类覆盖 `quality`、`valuation`、`growth`、`momentum`、`volatility` 和 `liquidity`。
- 每个因子都是 `FactorDefinitionStatus.DRAFT`、`semantic_version=1.0.0`、`formula.language=serenity_factor_dsl`。
- 每个 `FactorInput.dataset_version` 必须是具体 `dsv_*`，拒绝 `latest`。
- 每个因子声明 `direction`、`category`、`applicable_markets`、`data_requirements` 和 `reference_plan`。
- `compile_base_factor_plans()` 对每个定义执行 DSL compile，并校验 required inputs、operators、lookback 和 Dataset Version 与手工 reference 一致。

## 5. 明确未做事项

- 未执行因子值、未发布 factor values Dataset、未实现横截面后处理执行。
- 未实现 Factor Evaluation、IC/ICIR、分组收益、暴露、换手或后验评价。
- 未实现 DAG/cache、增量重算、Historical Universe、ScreenDefinition、ScreenSnapshot、Quant Screening API 或 Screen Lab。
- 未启动 Quant Core、Qlib Adapter、正式组合回测、Portfolio Ledger、Risk Engine 或 Evidence Agent。
- 未调用真实 Provider、真实 LLM 或 Worker execution loop。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 6. 本地验证

| 验证 | 结果 |
|---|---|
| `uv run --extra core --extra dev python -m pytest tests/quant/test_base_factor_definitions.py -q` | Red：`1 error`，缺少 `BASE_FACTOR_CATALOG_VERSION` / `quant.factors.base_factors` 导出；Green：`4 passed` |
| `uv run --extra core --extra dev python -m pytest tests/quant/test_base_factor_definitions.py tests/quant/test_factor_dsl_contract.py tests/quant/test_factor_definition_contract.py -q` | PASS：`21 passed` |
| `uv run --extra core --extra dev python -m pytest tests/quant/test_base_factor_definitions.py tests/quant/test_factor_dsl_contract.py tests/quant/test_factor_definition_contract.py tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`46 passed` |
| `uv run --extra core --extra dev python -m pytest -q` | PASS：`276 passed, 3 skipped` |
| `uv run --extra core --extra dev python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | PASS：`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

最终完整验证结果同步记录在 `AEV-056`。
