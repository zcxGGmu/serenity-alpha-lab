# Corporate Actions and Adjustments Dataset 记录

> 任务：`SAL-P2-008` 实现公司行动与复权<br>
> 日期：2026-07-22<br>
> Gate：G2 未通过，本任务仅完成公司行动 Dataset、前/后复权因子和复权日线 Dataset<br>
> 代码：`src/serenity_alpha_lab/datasets/corporate_actions.py`<br>
> 测试：`tests/datasets/test_corporate_actions_adjustments.py`

## 1. 范围

本任务新增公司行动与复权 Dataset，覆盖：

- 公司行动：支持 `cash_dividend`、`bonus_share`、`rights_issue` 和 `share_split`，每条记录携带 canonical `InstrumentId`、`ex_date`、Provider/source timestamp、raw response SHA-256、field lineage 和 Bronze source artifact id。
- 证券与交易日校验：公司行动必须能在 `InstrumentMasterDataset` 中按 `ex_date` 查到有效证券，且 `ex_date` 必须是 `TradingCalendarDataset` 中的交易日。
- 复权因子：以已有未复权 `RawDailyBarsDataset` 为输入，按公司行动除权日和前一交易日 raw close 计算事件系数。
- 复权口径：`forward` 表示前复权/最新锚定，历史价格乘以后续事件系数；`backward` 表示后复权/起点锚定，事件日起及之后价格乘以事件系数倒数。
- 复权日线：`AdjustedDailyBarsDataset` 以 `instrument_id + trade_date + provider_id + adjustment` 为主键，记录复权 OHLC、raw OHLC、factor、volume/amount 原值、raw Bronze lineage 和公司行动 lineage。
- Provider 口径：复权派生按 raw bar 的 `provider_id` 只使用同一 Provider 的公司行动记录，避免不同 Provider 的重复公司行动源被叠加。
- 原始数据保护：复权 Dataset 从 raw bars 派生，不改写 `RawDailyBarsDataset` 原始价格。
- 查询能力：支持按公司行动证券/日期、市场除权日、复权日线单条主键、证券日期区间和复权口径查询。
- 增量合并：`AdjustedDailyBarsDataset.merge_incremental()` 以复权主键替换记录，并返回新的不可变 Dataset。
- Artifact 发布：公司行动与复权日线均复用 P1 `ArtifactStore`，输出 deterministic JSON Artifact，携带 schema、record_count、Bronze lineage、trace/run/stage 和 manifest-last 发布语义。
- 错误边界：Dataset 校验错误继承 `ValueError`，在既有 `ProblemDetails` 边界映射为稳定 `validation_error`。

## 2. 复权口径

同一除权日的公司行动按证券聚合后计算理论除权价：

```text
theoretical_ex_price =
  (previous_close - cash_dividend + rights_issue_ratio * rights_issue_price)
  / (split_ratio_product * (1 + bonus_share_ratio) + rights_issue_ratio)

event_coefficient = theoretical_ex_price / previous_close
```

因子定义：

- `forward`：`trade_date` 之后所有 `ex_date` 的 `event_coefficient` 连乘。
- `backward`：`trade_date` 当日及之前所有 `ex_date` 的 `1 / event_coefficient` 连乘。
- 无公司行动时，两种口径因子均为 `1.0`。

本口径覆盖现金分红、送转/拆股和配股的价格连续性，不处理组合账本中的现金入账、股份入账或配股认购决策；这些属于 `SAL-P4-012`。

## 3. Schema

新增常量：

- `CORPORATE_ACTIONS_SCHEMA_NAME = "dataset.corporate_actions"`
- `CORPORATE_ACTIONS_SCHEMA_VERSION = "1.0.0"`
- `CORPORATE_ACTIONS_CONTENT_TYPE = "application/vnd.serenity.dataset.corporate-actions+json"`
- `CORPORATE_ACTIONS_PARTITION_KEYS = ("market", "year")`
- `ADJUSTED_DAILY_BARS_SCHEMA_NAME = "dataset.bars_1d_adjusted"`
- `ADJUSTED_DAILY_BARS_SCHEMA_VERSION = "1.0.0"`
- `ADJUSTED_DAILY_BARS_CONTENT_TYPE = "application/vnd.serenity.dataset.adjusted-daily-bars+json"`
- `ADJUSTED_DAILY_BARS_PARTITION_KEYS = ("market", "year", "month")`
- `*_FIELD_SCHEMA`：冻结 Arrow-compatible 字段名与类型字符串，但不建立 Arrow Schema Registry。

核心记录：

- `CorporateAction`：一个证券在一个除权日、一个 Provider 下的一类公司行动。
- `CorporateActionsDataset`：不可变公司行动集合、离线索引、校验和 Artifact 发布入口。
- `AdjustedDailyBar`：一个证券在一个交易日、一个 Provider、一个复权口径下的复权价格记录。
- `AdjustedDailyBarsDataset`：复权日线集合、raw bars 派生、查询 API、增量合并和 Artifact 发布入口。

## 4. 校验规则

- 公司行动主键 `(instrument_id.canonical, ex_date, action_type, provider_id)` 必须唯一。
- 复权日线主键 `(instrument_id.canonical, trade_date, provider_id, adjustment)` 必须唯一。
- `created_at`、Provider source timestamp 必须是 timezone-aware datetime。
- `provider_raw_response_sha256` 必须是合法 SHA-256。
- 每条公司行动与复权日线必须携带 Bronze/source artifact lineage。
- 现金分红金额、送转比例、拆股比例、配股比例和配股价必须有限且满足对应行动类型约束。
- 现金分红不能大于或等于前一交易日 raw close，理论除权价和复权因子必须为正。
- 复权 OHLC 和 raw OHLC 都必须满足 `low <= open/close <= high`，volume/amount 保持非负。
- 发布时必须提供 `produced_by_run_id` 或 Dataset 自带 `run_id`。

## 5. 验证

本任务使用 TDD：

- Red：`uv run --extra core --extra dev python -m pytest tests/datasets/test_corporate_actions_adjustments.py -q` 先以缺少 `serenity_alpha_lab.datasets.corporate_actions` 失败。
- Green target：`uv run --extra core --extra dev python -m pytest tests/datasets/test_corporate_actions_adjustments.py -q`，`3 passed`；覆盖不同 Provider 公司行动不被叠加到 raw bar Provider 的回归断言。
- Related suite：`uv run --extra core --extra dev python -m pytest tests/datasets tests/domain/test_provider_contract.py tests/domain/test_artifacts.py tests/repositories/test_local_artifact_store.py tests/repositories/test_bronze_raw_store.py tests/application/test_api_errors.py tests/application/test_trace_context.py tests/architecture/test_architecture_boundaries.py -q`，`68 passed`。
- Full suite：`uv run --extra core --extra dev python -m pytest -q`，`175 passed`。
- Compile：`uv run --extra core --extra dev python -m py_compile src/serenity_alpha_lab/datasets/corporate_actions.py src/serenity_alpha_lab/datasets/__init__.py tests/datasets/test_corporate_actions_adjustments.py` 通过。
- Lock：`scripts/verify-python-dependency-lock.sh` 通过。
- Diff/tag：`git diff --check` 通过；`git rev-parse upstream/dsa-v3.26.1` 仍为 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。

最终提交前验证命令和结果记录在 `tasks/todo.md` 的 `SAL-P2-008` review 与任务清单证据登记中。

## 6. 范围限制

本任务明确未实现：

- PIT 基本面 Dataset、fallback policy、Provider 质量门禁、Dataset Catalog/latest alias、Arrow Schema Registry、PersistentTaskBackend、Worker runtime、Quant Core、正式回测、Evidence Agent。
- Portfolio Ledger 中的现金分红、送转、配股入账或退市清算。
- 真实 Provider/LLM 调用、联网探针或 DSA runtime source 迁移。

Gate G2 仍未通过。
