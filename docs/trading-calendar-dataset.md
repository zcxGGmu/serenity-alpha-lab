# Trading Calendar Dataset 记录

> 任务：`SAL-P2-006` 实现交易日历<br>
> 日期：2026-07-21<br>
> Gate：G2 未通过，本任务仅完成交易日历 Dataset<br>
> 代码：`src/serenity_alpha_lab/datasets/trading_calendar.py`<br>
> 测试：`tests/datasets/test_trading_calendar.py`

## 1. 范围

本任务新增交易日历 Dataset，覆盖：

- 市场主键：复用 P1 `Market`，内部主键为 `market + trade_date`。
- 市场时区：内置 `cn -> Asia/Shanghai`、`hk -> Asia/Hong_Kong`、`us -> America/New_York`、`jp -> Asia/Tokyo`、`kr -> Asia/Seoul`、`tw -> Asia/Taipei`。
- 交易 session：记录交易日、闭市日、半日交易、异常休市和停牌日状态。
- 开闭市时间：交易 session 必须携带 market-local aware datetime；闭市/异常休市/停牌不得携带开闭市时间。
- 午间休市：支持可选 `break_start_at` / `break_end_at`，并在 `is_open_at()` 中排除午休窗口。
- UTC 金标：`open_at_utc`、`close_at_utc` 和午休 UTC 字段由 market-local 时间确定性转换。
- 查询缓存：Dataset 初始化时按 `(market, trade_date)` 与 `market` 构建不可变索引，支持 session、交易日、前后交易日和 timestamp 开市状态查询。
- Artifact 发布：复用 P1 `ArtifactStore`，输出 deterministic JSON Artifact，携带 schema、record_count、Bronze lineage、trace/run/stage 和 manifest-last 发布语义。
- 错误边界：Dataset 校验错误继承 `ValueError`，在既有 `ProblemDetails` 边界映射为稳定 `validation_error`。

## 2. Schema

新增常量：

- `TRADING_CALENDAR_SCHEMA_NAME = "dataset.trading_calendar"`
- `TRADING_CALENDAR_SCHEMA_VERSION = "1.0.0"`
- `TRADING_CALENDAR_CONTENT_TYPE = "application/vnd.serenity.dataset.trading-calendar+json"`

核心记录：

- `TradingSessionStatus`：`open`、`half_day`、`closed`、`ad_hoc_closed`、`suspended`。
- `MarketSession`：一个市场在一个 `trade_date` 的 session 状态、时区、开闭市、午休、Bronze lineage 和说明。
- `TradingCalendarDataset`：不可变 session 集合、查询 API、内存索引和 Artifact 发布入口。

## 3. A 股日历策略

本任务采用显式记录策略：

- A 股节假日用 `closed` session 记录，且不携带 `open_at` / `close_at`。
- A 股半日交易若发生，用 `half_day` session 记录缩短后的开闭市时间；本任务不默认推断半日规则。
- 异常休市用 `ad_hoc_closed` session 记录，并通过 `note` 说明来源或原因。
- 午间休市通过显式 break window 表达；`is_open_at()` 在 break window 内返回 `False`。
- Dataset 不从当前日期、网络、真实 Provider 或外部 mutable 服务推断假期；后续 Provider/Worker 只能发布显式 calendar records。

## 4. 校验规则

- Dataset 不能为空。
- `(market, trade_date)` 必须唯一。
- `created_at` 必须是 timezone-aware datetime。
- `timezone` 必须匹配 `Market` 的已冻结市场时区。
- `open_at`、`close_at` 和 break endpoints 必须是 market-local timezone-aware datetime，且 local date 等于 `trade_date`。
- `open` / `half_day` 必须携带 `open_at` 与 `close_at`，且 `close_at > open_at`。
- `closed` / `ad_hoc_closed` / `suspended` 不得携带开闭市或午休时间。
- break window 若存在，必须同时提供起止，并满足 `open_at < break_start_at < break_end_at < close_at`。
- 每条 session 必须携带 `source_bronze_artifact_id`，保持从 Bronze 原始响应到 Dataset 的审计链路。
- 发布时必须提供 `produced_by_run_id` 或 Dataset 自带 `run_id`。

## 5. 验证

本任务使用 TDD：

- Red：`uv run --extra core --extra dev python -m pytest tests/datasets/test_trading_calendar.py -q` 先以缺少 `serenity_alpha_lab.datasets.trading_calendar` 失败。
- Green target：`uv run --extra core --extra dev python -m pytest tests/datasets/test_trading_calendar.py -q`，`3 passed`。
- Related suite：`uv run --extra core --extra dev python -m pytest tests/datasets tests/domain/test_provider_contract.py tests/repositories/test_bronze_raw_store.py tests/application/test_api_errors.py tests/application/test_trace_context.py tests/architecture/test_architecture_boundaries.py -q`，`56 passed`。

最终全量验证命令和结果记录在 `tasks/todo.md` 的 `SAL-P2-006` review 与任务清单证据登记中。

## 6. 范围限制

本任务明确未实现：

- 原始日线 Dataset `SAL-P2-007`。
- PIT 基本面 Dataset、fallback policy、Provider 质量门禁、Dataset Catalog/latest alias、Arrow Schema Registry、PersistentTaskBackend、Worker runtime、Quant Core、正式回测、Evidence Agent。
- 真实 Provider/LLM 调用、联网探针或 DSA runtime source 迁移。

Gate G2 仍未通过。
