# Provider 领域契约记录

> 任务：`SAL-P2-001` 定义 Provider 领域契约<br>
> 日期：2026-07-21<br>
> Phase：P2 数据与持久任务<br>
> Gate：G2 未通过<br>
> 范围：纯领域 Provider Capability、DataBatch、Provenance、warning、六类错误和同步 MarketDataProvider Protocol；不实现 DSA Adapter、真实 Provider 调用、Dataset/PIT、Quant Core 或持久任务。

## 1. 目标

本任务冻结 Provider 与 Serenity 领域之间的最小稳定边界，使后续 DSA Provider Compatibility Adapter、Bronze 原始层、Dataset Catalog 和 fallback policy 可以共享同一数据来源与失败语义。契约保持同步、通用和框架无关，以兼容 DSA 当前同步 Provider，同时避免把 Pandas、Provider SDK 或上游 `DataFetcherManager` 具体实现带入 domain。

## 2. 领域契约

| 类型 | 作用 |
|---|---|
| `ProviderCapability` | 稳定能力标识：`instruments`、`trading_calendar`、`daily_bars`、`fundamentals`。 |
| `Capability` | 声明能力对应的 schema、版本、市场、频率和字段。 |
| `ProviderCapabilities` | 收集不可变能力声明，支持按能力和市场查询。 |
| `ProviderWarning` | 表达部分字段、质量或来源警告，不把 warning 伪装为成功数据质量结论。 |
| `Provenance` | 记录 provider/version、operation、已脱敏请求参数、请求/抓取/源时间、原始响应 SHA-256、字段 lineage 和 trace/run/stage 标量关联。 |
| `DataBatch[T]` | 泛型不可变批次，携带记录、schema 名称/版本、Provenance、`fresh_until` 和 warnings。允许合法空批次。 |
| `ProviderErrorCategory` | 统一失败分类：`retryable`、`rate_limited`、`auth`、`schema_drift`、`data_invalid`、`permanent`。 |
| `ProviderError` | 结构化 Provider 运行错误，带 category、provider、operation、脱敏 message 和可选限流等待时间。 |
| `MarketDataProvider` | 同步 Protocol，定义 capabilities、证券主数据、交易日历、日线和基本面读取入口。 |

具体 `Instrument`、`TradingDay`、`DailyBar` 和 `FundamentalRecord` 仍属于后续 P2 Dataset 任务；当前 Protocol 使用带 schema 标识的泛型记录，避免提前冻结错误的 DTO。

## 3. Provenance 与批次不变量

- 所有 provider、operation、schema 名称/版本和必要字符串必须非空。
- `request_parameters` 和 `field_lineage` 在进入领域值对象时深拷贝并递归冻结；调用方后续修改不会改变已记录 provenance。
- `raw_response_sha256` 复用 `ArtifactUri.for_sha256()` 的 64 位小写 SHA-256 校验口径。
- `requested_at`、`fetched_at`、可选 `source_timestamp`、`fresh_until` 和 `is_stale(at=...)` 的输入时间必须带时区；领域对象不隐式读取当前时间。
- `DataBatch` 的 records 规范化为 tuple；映射、列表、集合记录递归冻结为只读结构，避免以 frozen dataclass 伪装可变内容。
- warning 规范化为不可变 tuple；空 batch 合法，空数据是否为质量失败由后续 Adapter/质量门禁决定。
- `trace_id`、`run_id`、`stage_id` 只作为标量关联字段，避免 domain 反向依赖 `application.tracing`；调用方负责在既有 `TraceContext` 和 `Run/Stage/Event` 生命周期内填充它们。
- Provider 入口接收 `InstrumentId`，不接收跨市场裸 symbol；具体供应商 symbol 映射留给 `SAL-P2-002`。

## 4. 错误分类与 API 边界

| 分类 | 领域语义 | 默认重试 |
|---|---|---:|
| `retryable` | 暂时性网络/服务失败 | 是 |
| `rate_limited` | Provider 限流，可带 `retry_after_seconds` | 是 |
| `auth` | 凭据无效、过期或权限不足 | 否 |
| `schema_drift` | 返回字段或结构不符合已声明 schema | 否 |
| `data_invalid` | 返回成功但数据违反基本质量/完整性约束 | 否 |
| `permanent` | 当前请求或能力不可恢复失败 | 否 |

六类内部分类供后续 retry/fallback policy 使用；应用层不扩展 P1 已冻结的公共错误码。`application/api_errors.py` 将任意 `ProviderError` 映射为现有 `ProviderProblem`（HTTP 502、`provider_error`），继续复用既有 trace_id 传播与自由文本脱敏，避免把 Provider token、绝对路径或私有正文返回给客户端。

## 5. P1 契约复用与边界

- `InstrumentId` 是 Provider Protocol 的跨市场身份输入；Provider symbol mapping 不在本任务扩展。
- `RuntimeProfile` 的 CI 禁网、无真实 key 和无 Provider/LLM 调用边界由 application/integration 调用方执行；本领域对象不导入配置模块。
- `TraceContext` 负责请求到 Worker/Provider 的传播；Provenance 只保存已脱敏的标量关联与请求元数据。
- Bronze、Dataset Version 和报告输出必须在后续任务复用既有 `ArtifactStore`，本任务不创建新的 URI、manifest 或物理存储。
- Provider 调用由 application/worker 绑定既有 `Run`、`Stage`、`RunEvent`；本任务不创建第二套生命周期。
- 新 Schema 仍必须经过既有 Alembic revision/preflight；本任务不新增数据库表或迁移。
- `ProviderCompatibilityFacade` 属于 `SAL-P2-002`；fallback trace 和来源选择属于 `SAL-P2-015`。

## 6. 范围限制

- 不导入或复制 DSA runtime source，不移动 `upstream/dsa-v3.26.1` tag。
- 不调用 AKShare、efinance、Tushare、BaoStock、YFinance 或任何真实 Provider。
- 不启动真实 LLM、Evidence Agent、Quant Core、正式组合回测、PIT Dataset、Bronze 落盘、Dataset Catalog 或 PersistentTaskBackend。
- 不改变 DSA API/OpenAPI、Web/Desktop、旧 `DataFetcherManager` 或 `normalize_stock_code` 调用点。
- 本任务不关闭 `RSK-004` 免费 Provider 不稳定风险；契约分类、Provenance 和离线 Contract Test 只提供后续缓解基础。

## 7. 验证证据

| 验证 | 结果 |
|---|---|
| Red：domain contract | 新增目标测试后首次收集因缺少 `serenity_alpha_lab.domain.providers` 失败，`1 collection error`。 |
| Red：Problem Details mapping | ProviderError 尚未映射时断言得到 `500 != 502`，其余 API 测试 `12 passed`。 |
| Red：审查回归 | 独立审查发现 bytearray 可变性绕过、非有限 retry delay、自定义可变标量子类、quoted Provider secret、可变契约对象引用和非字符串 lineage/schema 绕过；本地复核继续发现 mapping key 未冻结，均已新增回归测试覆盖。 |
| Green：目标与相关套件 | Provider contract `23 passed`；domain/application/architecture 组合 `109 passed`。 |
| Green：全量 pytest | `uv run --python /Users/zq/.local/bin/python3.11 --with pytest --with pydantic-settings --with alembic pytest -q`，`128 passed`。 |
| 语法 | `py_compile` 覆盖 Provider、domain exports、Problem Details、Provider tests、API tests 和 architecture tests，PASS。 |
| 依赖/基线保护 | `scripts/verify-python-dependency-lock.sh`、`git diff --check` PASS；`upstream/dsa-v3.26.1` 仍为 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。 |
| 静态检查 | 本轮未声明 Ruff 通过：下载后的本地 Ruff 首先被既有 `W503` selector 配置阻断；临时移除该 selector 后又暴露既有 lint 债务，未纳入 `SAL-P2-001` 通过项。 |

## 8. 后续衔接与回滚

下一步是 `SAL-P2-002`：通过显式 Provider Compatibility Facade 把 DSA `DataFetcherManager`/Pandas 输出转换为本契约，并为旧接口补 characterization/contract tests。之后依次由 `SAL-P2-004` 复用 ArtifactStore 保存 Bronze、`SAL-P2-006` 补交易日历 DTO、`SAL-P2-009` 补 PIT 基本面时间字段、`SAL-P2-015` 实现 fallback policy。

若后续 Adapter 发现能力字段、错误分类或 provenance 不足，应先新增契约测试并通过兼容扩展；不得绕过 Facade 直接在 domain 引入 Provider SDK。若本契约回归既有行为，回滚本 checkpoint，保留 Red/Contract Test，并复跑 P1 兼容基线和 domain/application/architecture 套件。
