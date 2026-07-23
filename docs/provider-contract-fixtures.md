# Provider 契约 Fixture 记录

> 任务：`SAL-P2-014` 建立 Provider 契约 Fixture<br>
> 日期：2026-07-23<br>
> Phase：P2 数据与持久任务<br>
> Gate：G2 未通过<br>
> 代码：`src/serenity_alpha_lab/integrations/data/provider_contract_fixtures.py`<br>
> 测试：`tests/integrations/test_provider_contract_fixtures.py`<br>
> 快照：`docs/baselines/provider-contract-fixtures/`

## 1. 范围

本任务新增全离线 Provider contract fixture corpus，用固定、脱敏、可提交的 Provider 响应样本约束后续 Adapter、Bronze、Dataset、质量门禁和 fallback policy 的输入边界。

覆盖范围：

- Provider：AKShare、efinance、Tushare、BaoStock、YFinance。
- 市场：A 股主路径覆盖 AKShare、efinance、Tushare、BaoStock；YFinance 覆盖美股 `AAPL.XNAS` 和港股 `0700.XHKG` 基本路径。
- 能力：当前冻结为 `daily_bars`，与既有 DSA Provider Compatibility Adapter 的已实现能力保持一致。
- 成功样本：每个 Provider 至少一个日线成功响应，转换为不可变 `DataBatch`。
- 异常样本：`timeout`、`empty`、`schema_drift` 分别映射到 `retryable`、`data_invalid`、`schema_drift`。
- Schema：每个 fixture case 记录 Provider-facing schema、required/optional fields，并绑定 `dataset.bars_1d_raw@1.0.0` 的 Arrow Schema hash。
- 追踪：`to_data_batch()` 接收 trace/run/stage 标量，写入既有 Provider `Provenance`。

## 2. 实现口径

| 类型 / 函数 | 作用 |
|---|---|
| `ProviderFixtureStatus` | 稳定状态：`success`、`timeout`、`empty`、`schema_drift`。 |
| `ProviderFixtureSchema` | 记录 capability、schema name/version、required/optional fields 和 Dataset schema hash，并校验成功记录字段。 |
| `ProviderContractFixtureCase` | 单个脱敏 Provider 响应样本；成功样本可转为 `DataBatch`，异常样本可转为 `ProviderError`。 |
| `ProviderContractFixtureCatalog` | 不可变 fixture catalog，提供 provider 覆盖、成功/异常样本筛选和 case lookup。 |
| `default_provider_contract_fixture_catalog()` | 构建默认 corpus；不导入 AKShare、efinance、Tushare、BaoStock 或 YFinance SDK。 |
| `write_provider_fixture_snapshots()` | 输出 deterministic JSON 快照，包括 `index.json` 和每个 case 的响应/Schema/预期结果。 |

`integrations/data` 被 `.gitignore` 中的通用 `data/` 规则误伤，本任务新增精确例外，只允许跟踪 `src/serenity_alpha_lab/integrations/data/*.py`，不放开运行时 `data/` 目录。

## 3. Fixture 覆盖

| Case | Provider | Market | Status | 预期 |
|---|---|---|---|---|
| `akshare_daily_bars_cn_success_600519` | AKShare | CN | success | 生成 `DataBatch`，含 OHLCV/amount/CNY/source。 |
| `efinance_daily_bars_cn_success_600519` | efinance | CN | success | 生成 `DataBatch`，含 OHLCV/CNY/source。 |
| `tushare_daily_bars_cn_success_600519_sh` | Tushare | CN | success | 生成 `DataBatch`，将 `vol` 口径固定为规范化 `volume`。 |
| `baostock_daily_bars_cn_success_sh_600519` | BaoStock | CN | success | 生成 `DataBatch`，固定字符串数值脱敏样本。 |
| `yfinance_daily_bars_us_success_aapl` | YFinance | US | success | 覆盖美股基本路径。 |
| `yfinance_daily_bars_hk_success_0700_hk` | YFinance | HK | success | 覆盖港股基本路径。 |
| `akshare_daily_bars_timeout` | AKShare | CN | timeout | 映射为 `ProviderErrorCategory.RETRYABLE`。 |
| `baostock_daily_bars_empty` | BaoStock | CN | empty | 映射为 `ProviderErrorCategory.DATA_INVALID`。 |
| `tushare_daily_bars_schema_drift` | Tushare | CN | schema_drift | 映射为 `ProviderErrorCategory.SCHEMA_DRIFT`。 |

## 4. 安全与边界

- 所有样本为合成脱敏数据，不包含真实 key、cookie、授权头、prompt、用户数据或本地绝对路径。
- 测试断言 fixture 模块不会导入 AKShare、efinance、Tushare、BaoStock 或 YFinance SDK。
- Snapshot writer 只写调用方显式传入目录，不访问网络、不读取用户数据、不实例化 DSA `DataFetcherManager`。
- Provider fixture 只冻结输入契约，不实现 Provider 选择、fallback 顺序、cross-check、质量门禁发布、增量调度、Worker runtime、Quant Core、正式回测或 Evidence Agent。

## 5. 验证证据

| 验证 | 结果 |
|---|---|
| Red：fixture module | `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_contract_fixtures.py -q` 先以 `ModuleNotFoundError: No module named 'serenity_alpha_lab.integrations.data.provider_contract_fixtures'` 失败。 |
| Green：target | `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_contract_fixtures.py -q`，`4 passed`。 |
| Green：related | `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_contract_fixtures.py tests/integrations/test_dsa_provider_adapter.py tests/domain/test_provider_contract.py tests/datasets/test_arrow_schema_registry.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q`，`58 passed`。 |

完整 `pytest`、`compileall`、lock、diff 和 immutable tag 验证在 checkpoint 前执行，并记录到任务清单和进度清单。

## 6. 后续衔接

`SAL-P2-015` 可以在本 corpus 上实现 Provider Policy 与 fallback trace：策略层只消费 fixture case 的 capability、schema、error category、raw-response hash 和 normalized records，不应修改这些样本来表达选择逻辑。真实 Provider 探针、定时小样本 CI、跨源差异阈值和 quarantine 行为仍属于后续任务。
