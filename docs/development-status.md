# Serenity Alpha Lab 当前开发状态

> 最后更新：2026-07-25<br>
> 最近阶段性任务：`SAL-P4-004` 定义 `BacktestArtifact`<br>
> 工作区要求：从 `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab` 恢复，并重新执行 `git status`，以实际工作区为准<br>
> 当前 Phase：P4 真实组合回测与确定性风控<br>
> 当前 Gate：G4 未通过；G0、G1、G2、G3 已通过（均为 `GO with accepted risks`）<br>
> 任务完成度：70/129<br>
> 当前可执行任务：`SAL-P4-005` 锁定 Qlib 版本与隔离方案，状态为 `READY`；不得启动正式组合回测运行<br>
> 最近可评审交付 checkpoint：本次 `feat(P4): 定义正式 BacktestArtifact` 提交后以最终回复和 `git log -1 --oneline` 为准；上一 checkpoint 为 `1ecfaa2d feat(P4): 定义正式 BacktestSpec`<br>
> 最新状态同步 checkpoint：本次 `docs: 同步 SAL-P4-004 checkpoint hash` 提交后以最终回复和 `git log -1 --oneline` 为准；上一状态同步 checkpoint 为 `d23d5883 docs: 同步 SAL-P4-003 checkpoint hash`<br>
> 本次实现 checkpoint：本次 `feat(P4): 定义正式 BacktestArtifact` 提交后以最终回复和 `git log -1 --oneline` 为准；已完成任务范围推进至 `SAL-P4-004`<br>
> 最新状态复核 checkpoint：`cec881a6 docs: 复核 SAL-P3-016 最新开发状态`；上一状态复核 checkpoint 为 `eb476ff0 docs: 复核 SAL-P3-015 恢复状态与习惯`<br>
> 权威清单：[开发进度跟踪清单](./development-progress-checklist.md)

## 已完成

### 规划与协作

- 完成 GitHub 项目调研与选型，确定以 `daily_stock_analysis` 作为产品与 AI 分析主干。
- 完成 DSA 主干融合开发方案，明确 AlphaSift、Qlib、PIT 数据、真实回测、Evidence Agent 和发布边界。
- 完成 129 项原子任务、依赖、验收条件、Gate、风险和证据登记清单。
- 将 4 人团队排期按 268.5 理想人日修正为 16~18 周，并预留 10 个交易日稳定观察。
- 新增 `AGENTS.md`，要求后续会话读取状态/清单、阶段性任务完成后自动同步恢复状态，并在阶段 Gate 后主动提交。

### P0 上游接管

- 完成 `SAL-P0-001` 至 `SAL-P0-003`：锁定 DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`，导入上游历史/tag，并固化 Windows、Linux/CI、Docker、Desktop 运行环境矩阵。
- 完成 `SAL-P0-004`：后端离线 gate 通过，`4455 passed, 4 deselected, 48 warnings, 416 subtests passed`；登记 `DSA-PATCH-001`。
- 完成 `SAL-P0-005`：Web `npm ci`、lint、build、Vitest `965 passed, 2 skipped`、Playwright smoke `13 passed`；登记 `DSA-PATCH-002` 与 `DSA-PATCH-003`。
- 完成 `SAL-P0-006`：Desktop `47/47`、packaging/API `13/13`、CLI local backend `77/77`、Bot status/dispatcher/market `31/31` 离线 smoke。
- 完成 `SAL-P0-007`：Docker 镜像 `serenity-dsa-p0@sha256:7de0eca96fa8622e8b4b7292890f413e1a8fc52417f02c9c9a2829a364918076`，server `/api/health` 与 analyzer import smoke 通过。
- 完成 `SAL-P0-008`：冻结运行时 OpenAPI `3.1.0`、105 paths、119 operations、186 component schemas，以及 386 个配置 inventory 字段。
- 完成 `SAL-P0-009`：冻结 SQLite Schema、表/索引/外键元数据和脱敏 fixture；基线含 28 张业务表、177 个索引、31 行 fixture 数据。
- 完成 `SAL-P0-010`：冻结报告与信号评价金标；基线含 2 个结构化报告、3 个 Markdown 报告、6 个 Signal Evaluation cases，`direction_accuracy_pct=60.0`、`win_rate_pct=60.0`。
- 完成 `SAL-P0-011`：生成供应链 baseline；Python SBOM 146 components，Web npm audit 16 vulnerabilities / 10 high，Syft image SBOM 7865 components，Grype 39 critical / 84 high。
- 完成 `SAL-P0-012`：新增 `UPSTREAM_BASE.md`、补丁分类和 `.github/workflows/p0-required-baselines.yml` 四个 P0 required check 候选。
- 完成 `SAL-P0-013`：Gate G0 评审结论为 `GO with accepted risks`；证据见 [Gate G0 基线接管评审](./gate-g0-baseline-review.md)。

### P1 工程加固

- 完成 `SAL-P1-001`：批准 [ADR-001](./adr/ADR-001-upstream-takeover-sync-and-patch-policy.md) 与 [ADR-002](./adr/ADR-002-progressive-modularization-and-compatibility-facade.md)，明确不可变上游 tag、受控 sync 分支、补丁分类、候选 commit 处理、Compatibility Facade、模块边界、服务拆分条件、旧路径删除条件、回滚和复审日期。
- 上游候选处理已定：`55946536` macOS Gatekeeper 文档修复不 cherry-pick 到当前 P1 基线；`487e49e5` DecisionSignal reassessment persistence 延期至 `sync/dsa-487e49e5` 分支评审。
- 完成 `SAL-P1-002`：新增根 [pyproject.toml](../pyproject.toml)，标准化 PEP 621 项目元数据、Python `>=3.11,<3.13`、构建后端、DSA runtime 依赖声明、console entry points 和工具配置；依赖差异审查见 [Python 项目元数据审查](./python-project-metadata.md)。
- 完成 `SAL-P1-003`：拆分 `core`、`providers`、`desktop`、`quant`、`dev` extras，生成 [uv.lock](../uv.lock) 和由 lock 导出的 [requirements.txt](../requirements.txt)，新增 drift guard [verify-python-dependency-lock.sh](../scripts/verify-python-dependency-lock.sh)；生产/桌面 requirements 不包含 `pyqlib`、`dev` 工具或动态 Git 依赖，证据见 [Python 依赖 Extras 与锁文件记录](./python-dependency-lock.md)。
- 完成 `SAL-P1-004`：新增 `src/serenity_alpha_lab/` 目标包骨架和 `tests/architecture/` 架构测试，建立 domain/application/quant/datasets/evidence/integrations/repositories/services 边界；未启动 Quant Core、PIT Dataset、正式回测或 DSA runtime source 迁移。
- 完成 `SAL-P1-005`：新增纯领域 [instruments.py](../src/serenity_alpha_lab/domain/instruments.py)，定义 `InstrumentId`、市场、交易所、资产类型、Provider Symbol Mapping 和旧 symbol 兼容适配；A/港/美/日/韩/台典型代码可 canonical round-trip，裸 6 位代码无市场上下文时拒绝，证据见 [InstrumentId 统一证券 ID 领域模型记录](./instrument-id-domain-model.md)。
- 完成 `SAL-P1-006`：新增纯领域 [run_lifecycle.py](../src/serenity_alpha_lab/domain/run_lifecycle.py)，定义 `Run`、`Stage`、`RunEvent`、状态枚举、追加事件、retry attempt、终态拒绝回退和 idempotency conflict；证据见 [Run / Stage / Event 领域模型记录](./run-stage-event-domain-model.md)。
- 完成 `SAL-P1-007`：新增纯领域 [artifacts.py](../src/serenity_alpha_lab/domain/artifacts.py) 和本地 [local_artifact_store.py](../src/serenity_alpha_lab/repositories/local_artifact_store.py)，定义内容寻址 URI、Artifact Manifest、`ArtifactStore` Protocol、保留等级、manifest-last 原子发布和哈希完整性校验；证据见 [Artifact 模型与本地存储记录](./artifact-store-domain-model.md)。
- 完成 `SAL-P1-008`：新增应用层 [task_backend.py](../src/serenity_alpha_lab/application/task_backend.py) 和 DSA 兼容 [task_backend.py](../src/serenity_alpha_lab/integrations/dsa/task_backend.py)，定义 `TaskBackend` Protocol、`InMemoryTaskBackend`、任务命令/快照/事件、状态映射和注入式 DSA `AnalysisTaskQueue` facade；证据见 [TaskBackend 协议与 DSA 兼容 Facade 记录](./task-backend-facade.md)。
- 完成 `SAL-P1-009`：新增应用层 [research_orchestrator.py](../src/serenity_alpha_lab/application/research_orchestrator.py) 和 DSA 兼容 [research_orchestrator.py](../src/serenity_alpha_lab/integrations/dsa/research_orchestrator.py)，定义 `ResearchOrchestrator` Protocol、run/chat DTO、进度回调、错误类型和注入式 DSA `AgentOrchestrator` facade；证据见 [ResearchOrchestrator 协议与 DSA 兼容 Facade 记录](./research-orchestrator-facade.md)。
- 完成 `SAL-P1-010`：新增应用层 [api_errors.py](../src/serenity_alpha_lab/application/api_errors.py)，定义 `ApiErrorCode`、`ProblemDetail`、常用 problem error、异常映射、自由文本脱敏和框架无关 `ProblemDetailsMiddleware`；证据见 [API 错误协议记录](./api-error-protocol.md)。
- 完成 `SAL-P1-011`：新增应用层 [tracing.py](../src/serenity_alpha_lab/application/tracing.py)，定义 `TraceContext`、ContextVar 传播、结构化 JSON formatter、logging filter、递归脱敏和框架无关 ASGI middleware；证据见 [结构化日志与 Trace 记录](./structured-trace-logging.md)。
- 完成 `SAL-P1-012`：新增根 [alembic.ini](../alembic.ini)、[migrations](../migrations) baseline revision 和 [storage_migrations.py](../src/serenity_alpha_lab/repositories/storage_migrations.py)，让 Serenity root 通过 Alembic 创建 DSA `v3.26.1` baseline schema，并提供启动前 revision preflight；证据见 [Alembic 存储迁移接入记录](./storage-migration-alembic.md)。
- 完成 `SAL-P1-013`：新增 [sqlite_upgrade.py](../src/serenity_alpha_lab/repositories/sqlite_upgrade.py)，从 P0 脱敏 fixture 演练 backup、Alembic stamp、业务表行数/内容哈希校验和失败恢复；证据见 [SQLite 历史库升级验证记录](./sqlite-upgrade-verification.md)。
- 完成 `SAL-P1-014`：新增应用层 [config_profiles.py](../src/serenity_alpha_lab/application/config_profiles.py)，定义 `RuntimeSettings`、desktop/standalone/ci profile policy、CI 真实 key/网络拒绝、脱敏诊断、配置来源追踪和无副作用更新预览；证据见 [配置 Profile 与密钥边界记录](./config-profile-facade.md)。
- 完成 `SAL-P1-015`：新增 [run-p1-desktop-compatibility-performance.sh](../scripts/run-p1-desktop-compatibility-performance.sh)，重跑 DSA Desktop/API/CLI/Bot/契约金标离线矩阵并记录 Desktop 后端启动与离线单股报告性能；证据见 [Desktop 兼容和性能基线记录](./desktop-compatibility-performance-baseline.md)。
- 完成 `SAL-P1-016`：Gate G1 评审结论为 `GO with accepted risks`，P1 工程加固完成 `16/16`，允许进入 P2；证据见 [Gate G1 工程地基评审](./gate-g1-engineering-foundation-review.md)。

### P2 数据与持久任务

- 完成 `SAL-P2-001`：新增纯领域 [providers.py](../src/serenity_alpha_lab/domain/providers.py)，定义 Provider capabilities、不可变 `DataBatch`/`Provenance`、warning、同步 `MarketDataProvider` Protocol 和六类错误；Provider 错误复用 P1 `ProviderProblem`/trace/脱敏边界，证据见 [Provider 领域契约记录](./provider-domain-contract.md)。
- 完成 `SAL-P2-002`：新增 [provider_adapter.py](../src/serenity_alpha_lab/integrations/dsa/provider_adapter.py)，通过注入式 DSA-like manager 将 `DataFetcherManager.get_daily_data()` / Pandas daily-bar 输出映射为不可变 `DataBatch`，并新增 `DsaStockHistoryCompatibilityFacade` feature flag 在 legacy 与 Provider contract 路径之间切换；证据见 [DSA Provider Compatibility Adapter 记录](./dsa-provider-compatibility-adapter.md)。
- 完成 `SAL-P2-003`：新增 [symbol_compatibility.py](../src/serenity_alpha_lab/integrations/dsa/symbol_compatibility.py)，用 `DsaStockCodeCompatibilityMapper` 和不可变 `DsaStockCodeMapping` 包裹 DSA `normalize_stock_code` 兼容语义，覆盖 P0 转换样例、Provider Symbol Mapping、有效期和歧义错误；证据见 [DSA Symbol Compatibility Migration 记录](./dsa-symbol-compatibility-migration.md)。
- 完成 `SAL-P2-004`：新增 [bronze_raw_store.py](../src/serenity_alpha_lab/repositories/bronze_raw_store.py)，通过既有 `ArtifactStore` 发布 deterministic JSON + gzip Bronze envelope，保存脱敏后的 Provider 原始响应、请求元数据、source/sanitized hash、trace/run/stage 和 archive retention；证据见 [Bronze 原始数据层记录](./bronze-raw-data-layer.md)。
- 完成 `SAL-P2-005`：新增 [instrument_master.py](../src/serenity_alpha_lab/datasets/instrument_master.py)，构建历史有效期 instrument master，复用 canonical `InstrumentId`、`ProviderSymbolMapping`、Bronze lineage 和 `ArtifactStore` deterministic JSON 发布；证据见 [Instrument Master Dataset 记录](./instrument-master-dataset.md)。
- 完成 `SAL-P2-006`：新增 [trading_calendar.py](../src/serenity_alpha_lab/datasets/trading_calendar.py)，构建 `market + trade_date` 交易日历 Dataset，冻结市场时区、交易 session、午休、半日/异常休市语义、UTC 转换、查询缓存和 `ArtifactStore` deterministic JSON 发布；证据见 [Trading Calendar Dataset 记录](./trading-calendar-dataset.md)。
- 完成 `SAL-P2-007`：新增 [raw_daily_bars.py](../src/serenity_alpha_lab/datasets/raw_daily_bars.py)，构建未复权 OHLCV/amount 原始日线 Dataset，复用 Provider `DataBatch`/`Provenance`、Instrument Master as-of、Trading Calendar trading-day、Bronze lineage 和 `ArtifactStore` deterministic JSON 发布；证据见 [Raw Daily Bars Dataset 记录](./raw-daily-bars-dataset.md)。
- 完成 `SAL-P2-008`：新增 [corporate_actions.py](../src/serenity_alpha_lab/datasets/corporate_actions.py)，构建公司行动 Dataset、前/后复权因子和复权日线 Dataset，支持现金分红、送转/拆股、配股、provider-scoped action filtering、raw price immutability、Bronze lineage 和 `ArtifactStore` deterministic JSON 发布；证据见 [Corporate Actions and Adjustments Dataset 记录](./corporate-actions-adjustments-dataset.md)。
- 完成 `SAL-P2-009`：新增 [fundamentals.py](../src/serenity_alpha_lab/datasets/fundamentals.py)，构建 PIT 基本面 Dataset，显式区分 period、announced、available、ingested 和 revision，支持 `available_at <= decision_time` 查询、latest revision 选择、unknown temporal confidence research-only/formal-backtest 拒绝、Bronze lineage 和 `ArtifactStore` deterministic JSON 发布；证据见 [PIT Fundamental Dataset 记录](./fundamentals-pit-dataset.md)。
- 完成 `SAL-P2-010`：新增 [schema_registry.py](../src/serenity_alpha_lab/datasets/schema_registry.py)，建立 Arrow Schema Registry，默认注册证券主数据、原始日线、公司行动、复权日线和 PIT 基本面 Dataset Schema，支持 lazy PyArrow conversion、schema metadata、canonical hash 和 semantic-version compatibility；证据见 [Arrow Schema Registry 记录](./arrow-schema-registry.md)。
- 完成 `SAL-P2-011`：新增 [catalog.py](../src/serenity_alpha_lab/datasets/catalog.py)，实现 Dataset Catalog 与 Manifest，管理不可变版本、Artifact 文件哈希、schema hash、previous/input lineage 和 latest alias；正式实验解析拒绝 latest，必须使用具体 dataset version；证据见 [Dataset Catalog 与 Manifest 记录](./dataset-catalog-manifest.md)。
- 完成 `SAL-P2-012`：新增 [quality.py](../src/serenity_alpha_lab/datasets/quality.py)，实现数据质量规则引擎、warning/quarantine/blocking 报告、issue 精确定位、deterministic quality report Artifact 和 Dataset Manifest metadata helper；证据见 [Data Quality Rule Engine 记录](./data-quality-rule-engine.md)。
- 完成 `SAL-P2-013`：新增 [publication.py](../src/serenity_alpha_lab/datasets/publication.py)，实现质量门禁发布、passed-only latest promotion、warning/quarantine/blocking 隔离记录、旧 latest 保持和显式 tmp 清理；证据见 [Dataset 隔离区与原子发布记录](./dataset-atomic-publication.md)。
- 完成 `SAL-P2-014`：新增 [provider_contract_fixtures.py](../src/serenity_alpha_lab/integrations/data/provider_contract_fixtures.py) 和 [Provider fixture 快照](./baselines/provider-contract-fixtures/index.json)，建立 AKShare、efinance、Tushare、BaoStock、YFinance 的全离线脱敏响应、Schema、timeout/empty/schema_drift 案例、`DataBatch` 转换和 deterministic snapshot writer；证据见 [Provider 契约 Fixture 记录](./provider-contract-fixtures.md)。
- 完成 `SAL-P2-015`：新增 [provider_policy.py](../src/serenity_alpha_lab/integrations/data/provider_policy.py)，实现 YAML-compatible Provider Policy、fallback trace、质量状态拒绝、Provider error exhaustion 和跨源 close 冲突 quarantine；证据见 [Provider Policy 与 Fallback Trace 记录](./provider-policy-fallback-trace.md)。
- 完成 `SAL-P2-016`：新增 [data_sync.py](../src/serenity_alpha_lab/services/data_sync.py)，实现增量同步计划、交易日调度、checkpoint、lookback window、scope lock、失败重试语义和历史补数命令；证据见 [增量同步与交易日调度记录](./data-sync-scheduler.md)。
- 完成 `SAL-P2-017`：新增 [database.py](../src/serenity_alpha_lab/repositories/database.py)，建立 PostgreSQL standalone Profile、SQLAlchemy 连接池、SQLite PRAGMA、readiness/Alembic preflight 和 Repository Contract probe；`core` extra 增加 `psycopg[binary]` 并刷新锁文件，证据见 [PostgreSQL Standalone Profile 记录](./postgresql-standalone-profile.md)。
- 完成 `SAL-P2-018`：新增 [persistent_task_backend.py](../src/serenity_alpha_lab/repositories/persistent_task_backend.py)，实现数据库权威 `PersistentTaskBackend`、追加 task events、注入式 `CeleryTaskQueueRouter`、队列路由、取消请求、Worker lease/heartbeat/complete/fail 和 expired lease requeue primitives；证据见 [PersistentTaskBackend 记录](./persistent-task-backend.md)。
- 完成 `SAL-P2-019`：新增 [task_event_stream.py](../src/serenity_alpha_lab/services/task_event_stream.py)，实现可恢复 task/run 事件流、SSE `Last-Event-ID` replay、RunEvent 持久化、queued orphan redispatch、stalled lease requeue 和临时 Artifact cleanup；证据见 [可恢复任务事件流记录](./recoverable-task-event-stream.md)。
- 完成 `SAL-P2-020`：Gate G2 评审结论为 `GO with accepted risks`，新增 [Gate G2 数据与任务评审](./gate-g2-data-task-review.md) 和 [Gate G2 integration test](../tests/gates/test_gate_g2_data_task_review.py)，验证 versioned A-share Dataset publication、Provider conflict quarantine、PersistentTaskBackend restart/SSE replay 和 DSA 单股兼容路径；P2 完成 `20/20`，允许进入 P3。

### P3 AlphaSift、因子与股票筛选

- 完成 `SAL-P3-001`：新增 [AlphaSift 源码审查与锁定记录](./alphasift-source-review.md) 和 [AlphaSift source review test](../tests/architecture/test_alphasift_source_review.py)，锁定 `ZhuLinsen/alphasift@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`、source archive SHA-256 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a`、Apache-2.0 attribution、runtime dependency list、current-resolution SCA、维护风险、已知限制、升级/替换/停止使用条件；P3 进度 `1/17`。
- 完成 `SAL-P3-002`：新增 [AlphaSift 离线 Wheel Intake 记录](./alphasift-wheel-intake.md)、[intake manifest](./baselines/alphasift-wheel-intake/intake-manifest.json)、CycloneDX [SBOM](./baselines/alphasift-wheel-intake/sbom-cyclonedx.json)、[许可证清单](./baselines/alphasift-wheel-intake/license-inventory.csv)、[AlphaSift Wheel intake test](../tests/architecture/test_alphasift_wheel_intake.py) 和 [build-alphasift-wheel-intake.sh](../scripts/build-alphasift-wheel-intake.sh)，固定 source archive SHA-256 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a`、reproducible wheel SHA-256 `b71fe6f4b11c9655b2190f91217fee66361f9852ae344c53fe501455a4823ed2`、internal artifact URI、SBOM、许可证清单和 offline no-deps install evidence；P3 进度 `2/17`。
- 完成 `SAL-P3-003`：新增 [ScreeningProvider 契约与 AlphaSift Adapter 记录](./screening-provider-contract.md)、应用层 [screening_provider.py](../src/serenity_alpha_lab/application/screening_provider.py)、AlphaSift 集成 [provider_adapter.py](../src/serenity_alpha_lab/integrations/alphasift/provider_adapter.py)、Fake provider、ProblemDetails 映射和架构边界测试；`ScreeningRequest` 强制具体 `dsv_*` Dataset Version 并拒绝 `latest`，CI profile 禁止未注入 client 的真实 AlphaSift 调用，LLM overlay 默认关闭并受 model-call policy 保护；P3 进度 `3/17`。
- 完成 `SAL-P3-004`：新增 [CandidateBatch 候选契约记录](./candidate-batch-contract.md)、应用层 [candidate_batch.py](../src/serenity_alpha_lab/application/candidate_batch.py) 和 CandidateBatch contract test，冻结 `screening.candidate_batch@1.0.0`、标准候选、L1/L2/L3 层级分数、原因码、来源血缘、rank、`to_record()` 序列化和 `ScreeningResult` metadata bridge；P3 进度 `4/17`。
- 完成 `SAL-P3-005`：新增 [FactorDefinition 版本模型记录](./factor-definition-version-model.md)、Quant 层 [definitions.py](../src/serenity_alpha_lab/quant/factors/definitions.py) 和 FactorDefinition contract test，冻结 `quant.factor_definition@1.0.0`、公式/输入/窗口/缺失/后处理/实现哈希、draft/published/retired 生命周期、不可变发布、独立 retirement record 和 audit events；P3 进度 `5/17`。
- 完成 `SAL-P3-006`：新增 [Factor DSL 与算子白名单记录](./factor-dsl-operator-whitelist.md)、Quant 层 [dsl.py](../src/serenity_alpha_lab/quant/factors/dsl.py) 和 Factor DSL contract test，冻结 `serenity_factor_dsl@1.0.0`、白名单 parser/AST/validator/compiler、`FactorExpressionPlan`、`FactorExpressionNode`、`compile_factor_expression()` 和 `compile_factor_definition()`；支持 delay/rolling/rank/算术/条件等基础表达式并拒绝任意 Python/module path；P3 进度 `6/17`。
- 完成 `SAL-P3-007`：新增 [基础因子定义记录](./base-factor-definitions.md)、Quant 层 [base_factors.py](../src/serenity_alpha_lab/quant/factors/base_factors.py) 和 Base factor contract test，冻结 `base_factor_catalog@1.0.0`、15 个 `FactorDefinition` draft、默认具体 `dsv_*` Dataset Version 引用、分类计数、适用市场、数据需求和手工 DSL plan reference；P3 进度 `7/17`。
- 完成 `SAL-P3-008`：新增 [横截面因子后处理记录](./factor-cross-sectional-post-processing.md)、Quant 层 [post_processing.py](../src/serenity_alpha_lab/quant/factors/post_processing.py) 和 Factor post-processing contract test，冻结 `quant.factor_cross_section_post_processing@1.0.0`、具体 `dsv_*` Dataset Version guard、按交易日分组的显式股票池处理、缺失策略、winsorize、行业/市值中性化、z-score 标准化和 edge-case warnings；P3 进度 `8/17`。
- 完成 `SAL-P3-009`：新增 [Factor Evaluation 记录](./factor-evaluation.md)、Quant 层 [evaluation.py](../src/serenity_alpha_lab/quant/factors/evaluation.py) 和 Factor evaluation contract test，冻结 `quant.factor_evaluation@1.0.0`、`FutureReturnWindow`、覆盖率、IC/ICIR、分组收益、单调性、换手、暴露 summary 和 deterministic Artifact 发布；P3 进度 `9/17`。
- 完成 `SAL-P3-010`：新增 [Factor DAG/cache 记录](./factor-dag-cache.md)、Quant 层 [engine.py](../src/serenity_alpha_lab/quant/factors/engine.py) 和 Factor DAG/cache contract test，冻结 `factor_engine@1.0.0`、DAG node CSE、factor-specific dataset dependency map、cache key、分区计划、增量重算计划、质量门和 deterministic cache manifest Artifact 发布；P3 进度 `10/17`。
- 完成 `SAL-P3-011`：新增 [Historical Universe 记录](./historical-universe.md)、Quant Screening 层 [universe.py](../src/serenity_alpha_lab/quant/screening/universe.py) 和 Historical Universe contract test，冻结 `quant.historical_universe@1.0.0`、`UniverseDefinition`、`UniverseSnapshot`、显式 Instrument Trade Status、规则证据、派生 `dsv_*` universe version 和 deterministic Artifact 发布；P3 进度 `11/17`。
- 完成 `SAL-P3-012`：新增 [ScreenDefinition 与 L0-L4 Pipeline 记录](./screen-definition-pipeline.md)、Quant Screening 层 [pipeline.py](../src/serenity_alpha_lab/quant/screening/pipeline.py) 和 ScreenDefinition pipeline contract test，冻结 `quant.screen_pipeline@1.0.0`、`ScreenDefinition`、L1 Provider、L2 Factor、L3 LLM overlay、L4 deterministic risk gate、stage trace、pipeline candidate/exclusion 和 deterministic Artifact 发布；P3 进度 `12/17`。
- 完成 `SAL-P3-013`：新增 [ScreenSnapshot 与解释轨迹记录](./screen-snapshot-explanation-trace.md)、Quant Screening 层 [snapshot.py](../src/serenity_alpha_lab/quant/screening/snapshot.py) 和 ScreenSnapshot contract test，冻结 `quant.screen_snapshot@1.0.0`、`ScreenSnapshot`、`ScreenSnapshotResult`、结构化 `ScreenExplanationStep`、本地 `ScreenSnapshotComparison` 和 deterministic Artifact 发布；P3 进度 `13/17`。
- 完成 `SAL-P3-014`：新增 [Quant Screening API 记录](./quant-screening-api.md)、应用层 [quant_screening_api.py](../src/serenity_alpha_lab/application/quant_screening_api.py) 和 Quant Screening API contract test，冻结 `application.quant_screening_api@1.0.0`、`/api/v1/quant` route metadata、FactorDefinition/ScreenDefinition create response、screen run `202 Accepted`、Idempotency-Key replay、stable cursor pagination、single-result lookup 和 ScreenSnapshot comparison API 语义；P3 进度 `14/17`。
- 完成 `SAL-P3-015`：新增 [Screen Lab 记录](./screen-lab.md)、`DSA-PATCH-004`、DSA Web `quantScreeningApi` client、`ScreenLabPage`、`/screen-lab` route、SidebarNav item、zh/en labels 和 API/page/route/nav tests；Screen Lab 只通过 `/api/v1/quant` 复用 Quant Screening API、ScreenSnapshot、ScreenDefinition Pipeline、Dataset/Trace/Artifact lineage，不调用 legacy AlphaSift endpoint 作为页面数据源；P3 进度 `15/17`。
- 完成 `SAL-P3-016`：新增 [筛选性能与复现验收记录](./screen-performance-reproducibility.md)、Quant Screening 层 [performance.py](../src/serenity_alpha_lab/quant/screening/performance.py) 和 Screen performance reproducibility contract test，冻结 `quant.screen_performance@1.0.0`、A 股筛选 SLO/内存/结果行/增量预算、stage timing/memory samples、canonical result hash、fixed Run Bundle、reproducibility check 和 deterministic performance report Artifact 发布；P3 进度 `16/17`。
- 完成 `SAL-P3-017`：新增 [Gate G3 筛选与因子评审](./gate-g3-screen-factor-review.md) 和 Gate G3 integration test，结论为 `GO with accepted risks`；复核 `SAL-P3-001..016` 全部证据，批准 Screen/Factor 契约作为 P4 输入，但不批准 Quant Core、正式回测、Evidence Agent、真实 Provider/LLM、Worker loop 或 DSA runtime source migration；P3 完成 `17/17`，总进度 `66/129`。

### P4 真实组合回测与确定性风控

- 完成 `SAL-P4-001`：新增 [DSA Signal Evaluation Characterization](./dsa-signal-evaluation-characterization.md)、[P4 characterization script](../scripts/run-dsa-signal-evaluation-characterization.sh)、[P4 characterization test](../tests/architecture/test_dsa_signal_evaluation_characterization.py) 和 [P4 baseline snapshots](./baselines/dsa-v3.26.1/signal-evaluation-characterization/)，冻结 DSA `BacktestEngine.evaluate_single()` / `evaluate_decision_signal()`、legacy `/api/v1/backtest/*` route/schema 与 Agent backtest read tools 当前行为；这些表面只标注为 `legacy_signal_evaluation`，不是正式组合回测；P4 进度 `1/22`，总进度 `67/129`。
- 完成 `SAL-P4-002`：新增 [SignalEvaluationEngine 迁移记录](./signal-evaluation-engine.md)、root [SignalEvaluationEngine](../src/serenity_alpha_lab/quant/signal_evaluation.py)、[root parity tests](../tests/quant/test_signal_evaluation_engine.py)、[DSA migration tests](../tests/architecture/test_dsa_signal_evaluation_engine_migration.py) 和 `DSA-PATCH-005`；内部语义迁移为 `evaluation_type=signal` / `semantic_scope=legacy_signal_evaluation`，legacy `/api/v1/backtest/*`、`Backtest*` schema、数据库表、Agent read tools 和 `/backtest` route 保留兼容；P4-001 快照完全一致；P4 进度 `2/22`，总进度 `68/129`。
- 完成 `SAL-P4-003`：新增 [BacktestSpec Contract](./backtest-spec.md)、Quant Backtest [BacktestSpec](../src/serenity_alpha_lab/quant/backtest/spec.py) 和 [BacktestSpec contract test](../tests/quant/test_backtest_spec.py)，冻结正式组合回测 Dataset/Universe/Strategy/Execution/Cost/Risk 输入、canonical JSON、`spec_hash`、具体版本/hash guard、legacy Signal Evaluation 拒绝和 same-bar close 执行拒绝；本任务不执行正式组合回测；P4 进度 `3/22`，总进度 `69/129`。
- 完成 `SAL-P4-004`：新增 [BacktestArtifact Contract](./backtest-artifact.md)、Quant Backtest [BacktestArtifact](../src/serenity_alpha_lab/quant/backtest/artifacts.py) 和 [BacktestArtifact contract test](../tests/quant/test_backtest_artifact.py)，冻结正式组合回测订单、成交、持仓、现金、净值、指标和审计输出描述符、compact bundle summary Artifact、`preview/formal/partial/invalid` 状态、URI-only 大结果边界、具体 Dataset Version guard 和 legacy Signal Evaluation scope 拒绝；本任务不执行正式组合回测；P4 进度 `4/22`，总进度 `70/129`。

## 未完成

### 当前可执行 P4 任务

- `SAL-P4-005` 当前为 `READY`：锁定 Qlib 版本与隔离方案；不得启动正式组合回测运行、Qlib runtime、Ledger/Risk/Quant Lab、Evidence Agent、真实 Provider/LLM 或 Worker loop。

### 全局未完成

- 当前仓库已导入 DSA 上游 Git 历史和基线 tag，但尚未把 DSA 源码合入本项目工作树。
- P4 至 P6 仍有 59 项工程任务未完成。
- 已完成 P2 Dataset、Provider、Data Sync、PostgreSQL standalone Profile、PersistentTaskBackend 和可恢复任务事件流，并通过 Gate G2；已完成 P3 AlphaSift、Factor、ScreenDefinition、ScreenSnapshot、Quant Screening API、Screen Lab、性能/复现验收和 Gate G3；已完成 P4 DSA Signal Evaluation 行为/API 金标冻结、`SignalEvaluationEngine` 迁移、正式 `BacktestSpec` 与 `BacktestArtifact`。但尚未完成 Qlib 隔离、完整 Worker runtime、Quant Core、正式回测、Evidence Agent 或部署环境。
- 供应链 Critical/High、Web registry 混用和 Docker 镜像漏洞是已接受的 G0 风险，但继续阻断发布或未评审依赖漂移；Serenity root Python 动态 Git 生产依赖风险已由 `SAL-P1-003` 关闭。

## 当前决策与约束

- 2026-07-25 完成 `SAL-P3-015` Screen Lab：新增 DSA Web extension patch `DSA-PATCH-004`、Screen Lab evidence 和状态登记；完成范围推进至 `SAL-P3-015`，当前唯一 `READY` 阶段任务为 `SAL-P3-016` 筛选性能与复现验收。`cd0d6c6f docs: 同步 SAL-P3-014 checkpoint hash` 是本次实现前最新已落地状态同步锚点。
- 2026-07-25 完成 `SAL-P3-016` 筛选性能与复现验收，implementation checkpoint `e7569c83 feat(P3): 实现筛选性能与复现验收`；本次补齐筛选性能、内存、增量和结果哈希复现验收，完成范围推进至 `SAL-P3-016`，当前唯一 `READY` 阶段任务为 `SAL-P3-017` Gate G3：筛选与因子评审。
- 2026-07-25 完成 `SAL-P3-017` Gate G3 筛选与因子评审；结论为 `GO with accepted risks`，P3 完成 `17/17`，当前唯一 `READY` 阶段任务为 `SAL-P4-001` 锁定 DSA Signal Evaluation 行为。本次 Gate 只批准 Screen/Factor 契约作为 P4 输入，不批准直接执行正式回测。
- 2026-07-25 完成 `SAL-P4-001` DSA Signal Evaluation 行为锁定；本次冻结 DSA `BacktestEngine` 文本信号与结构化 DecisionSignal 评价、legacy `/api/v1/backtest/*` API schema、Agent read tools 和 7 个 committed snapshot，明确它们是 `legacy_signal_evaluation` 而非正式组合回测；当前唯一 `READY` 阶段任务为 `SAL-P4-002` 迁移为 `SignalEvaluationEngine`，`SAL-P4-003` 正式 `BacktestSpec` 等待 `SAL-P4-002`。
- 2026-07-25 完成 `SAL-P4-002` SignalEvaluationEngine 迁移；root quant parity、DSA compatibility patch、Web Signal Evaluation 文案和 P4-001 snapshot guard 均通过验证，legacy Backtest API/schema/table/Agent tool 仅作兼容面；当前唯一 `READY` 阶段任务为 `SAL-P4-003` 定义正式 `BacktestSpec`。
- 2026-07-25 完成 `SAL-P4-003` 正式 `BacktestSpec` 定义；BacktestSpec contract、canonical hash、具体 Dataset/Universe/Screen/Factor/code hash guard、legacy Signal Evaluation 拒绝和 same-bar close 执行拒绝均通过验证；当前唯一 `READY` 阶段任务为 `SAL-P4-004` 定义 `BacktestArtifact`。
- 2026-07-25 完成 `SAL-P4-004` 正式 `BacktestArtifact` 定义；BacktestArtifact contract、订单/成交/持仓/现金/净值/指标/审计 required output descriptors、URI-only 大结果边界、compact bundle summary Artifact、状态语义、具体 Dataset Version guard、manifest/hash guard 和 legacy Signal Evaluation scope 拒绝均通过验证；当前唯一 `READY` 阶段任务为 `SAL-P4-005` 锁定 Qlib 版本与隔离方案。
- Gate G0、Gate G1、Gate G2 与 Gate G3 已通过（均为 `GO with accepted risks`）；Gate G4 尚未通过。DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` 仍是当前上游产品基线。
- `upstream/dsa-v3.26.1` 是本地不可变基线标签；后续升级必须新建 `sync/dsa-<version>` 分支和新基线 tag，不得移动该标签。
- ADR-001 已批准受控同步策略：所有上游吸收必须经 `sync/dsa-*` 分支、补丁结果登记、相关基线刷新和 Gate/ADR 记录。
- ADR-002 已批准渐进式模块化策略：旧 DSA 路径只能经显式 Compatibility Facade 迁移，P1 不拆微服务。
- DSA 源码通过 `.worktrees/dsa-v3.26.1` 隔离物化；依赖缓存放在 `.cache/dsa-p0`，两者均不提交。
- 当前本地偏离均为 `compatible` 或 `extension`，无 `divergence`；已登记补丁为 `DSA-PATCH-001` 至 `DSA-PATCH-005`。
- Artifact 本地存储已采用 SHA-256 blob + JSON manifest 分离存储，manifest 最后发布；后续 Evidence、Dataset 和任务输出必须复用或显式适配该契约。
- TaskBackend 已建立应用层协议和 DSA 兼容 facade；后续 API、Worker 或持久队列不得直接依赖 DSA `ThreadPoolExecutor` 假设。
- ResearchOrchestrator 已建立应用层协议和 DSA 兼容 facade；后续 API、Worker、Bot 或 Agent checkpoint 不得直接依赖 DSA `AgentOrchestrator` / `AgentExecutor` 具体类。
- API Problem Details 错误协议已建立；后续 API/Worker 失败响应应使用稳定 `ApiErrorCode` 与 `application/problem+json`，不得泄露 stack trace、绝对路径、secret、prompt 或 request body/content。
- Trace context、结构化 JSON 日志和脱敏基础已建立；后续 API、Worker、Provider、Agent 和报告链路应复用 `TraceContext` 并避免记录 secret、token、完整 prompt 或私有正文。
- Alembic baseline 已建立：Serenity root 的新增 Schema 创建入口为 `migrations`，baseline revision `20260720_dsa_v3261_baseline` 对应 DSA `v3.26.1` P0 SQLite snapshot；应用启动前应检查 revision，不得静默 `create_all`。
- SQLite 历史升级演练已建立：已有 DSA SQLite 库通过 backup -> Alembic stamp -> row/content hash verify 接入 baseline head，失败时恢复备份；正式生产规模迁移和 runbook 留给后续发布任务。
- 配置 Profile facade 已建立：CI profile 默认禁止真实网络/模型/Provider 调用并拒绝真实 key；standalone/service profile 只允许无副作用预览，不通过 profile API 改写部署 `.env`。
- Desktop 兼容和性能基线已建立：`scripts/run-p1-desktop-compatibility-performance.sh` 离线复跑 Desktop/API/CLI/Bot、API/config、database、report/signal，并记录启动和单股报告性能；运行产物只落 `.cache/dsa-p0`。
- Gate G1 已批准进入 P2：Provider、Dataset、Persistent TaskBackend 和 Worker 必须复用 P1 `RuntimeProfile`、`ProblemDetail`、`TraceContext`、`ArtifactStore`、`Run/Stage/Event`、Alembic preflight 和 Compatibility Facade。
- Provider 领域契约已冻结：Adapter 通过同步 `MarketDataProvider` 返回带 schema、来源、已脱敏请求、时间、SHA-256、field lineage、freshness 和 warning 的不可变 `DataBatch`；`retryable/rate_limited/auth/schema_drift/data_invalid/permanent` 供内部策略使用，对外继续映射为稳定 `provider_error`。
- DSA Provider Adapter 已通过窄兼容层收口：真实 DSA `DataFetcherManager` 只在 profile guard 允许时 lazy 构造；CI/测试使用注入式 manager；旧单股历史调用必须继续通过显式 Compatibility Facade 和 `use_provider_contract` feature flag 迁移，不得直接扩散具体 Fetcher 依赖。
- DSA 证券代码兼容迁移已完成：`DsaStockCodeCompatibilityMapper` 在 DSA integration 边界包裹 `normalize_stock_code` 兼容语义；新领域路径携带 canonical `InstrumentId`，Provider 调用显式生成 `dsa` / `yahoo` symbol mapping，裸 6 位只在 legacy facade 带 CN 上下文时兼容。
- Bronze 原始数据层已完成：`BronzeRawStore` 复用 P1 `ArtifactStore` 内容寻址和 manifest-last 语义，原始响应落盘前递归脱敏并压缩，记录 provider/operation/request time/source hash/sanitized hash/field lineage/trace/run/stage；本层不发布 Dataset 或执行 fallback policy。
- 证券主数据 Dataset 已完成：`InstrumentMasterDataset` 复用 canonical `InstrumentId` 与 `ProviderSymbolMapping`，记录证券/交易所/资产类型/上市退市/状态/行业和 Provider 映射有效期，并通过 `ArtifactStore` 发布 deterministic JSON；本层不建立 Catalog/latest alias，不实现交易日历、PIT、fallback policy 或真实 Provider 调用。
- 交易日历 Dataset 已完成：`TradingCalendarDataset` 复用 P1 `Market`，以 `market + trade_date` 表达市场时区、交易/闭市/半日/异常休市/停牌 session、午休窗口、UTC 转换、前后交易日和 timestamp 开市状态查询，并通过 `ArtifactStore` 发布 deterministic JSON；本层不建立 Catalog/latest alias，不实现 raw daily bars、PIT、fallback policy 或真实 Provider 调用。
- 原始日线 Dataset 已完成：`RawDailyBarsDataset` 复用 canonical `InstrumentId`、Provider `DataBatch`/`Provenance`、Instrument Master as-of、Trading Calendar trading-day 和 Bronze source artifact，以 `instrument_id + trade_date + provider_id` 表达未复权 OHLCV/amount 日线，并通过 `ArtifactStore` 发布 deterministic JSON；本层不建立 Catalog/latest alias，不实现 PIT、fallback policy 或真实 Provider 调用。
- 公司行动与复权 Dataset 已完成：`CorporateActionsDataset` 按 `instrument_id + ex_date + action_type + provider_id` 表达现金分红、送转/拆股和配股，`AdjustedDailyBarsDataset` 按 `instrument_id + trade_date + provider_id + adjustment` 表达 `forward` / `backward` 复权价格和因子；复权从 raw bars 派生并按 raw bar provider 过滤同源公司行动，不覆盖原始价格，并通过 `ArtifactStore` 发布 deterministic JSON；本层不建立 Catalog/latest alias，不实现 PIT、fallback policy、Portfolio Ledger 入账或真实 Provider 调用。
- PIT 基本面 Dataset 已完成：`FundamentalsDataset` 按 `instrument_id + period_end + item + revision + provider_id` 表达时点正确的基本面记录，显式区分 `announced_at`、`available_at`、`ingested_at` 和 revision；PIT 查询硬过滤 `available_at <= decision_time`，无公告时间的 legacy/DSA-style 记录标记 `temporal_confidence=unknown` 且拒绝 formal backtest 查询，并通过 `ArtifactStore` 发布 deterministic JSON；本层不建立 Catalog/latest alias、fallback policy 或真实 Provider 调用。
- Arrow Schema Registry 已完成：`ArrowSchemaRegistry` 默认注册证券主数据、原始日线、公司行动、复权日线和 PIT 基本面 Dataset Schema；Schema 声明包含字段、主键、分区键、content type 和 canonical hash，minor/patch 只允许新增 nullable 字段，删除/改义/改类型/改主键等 breaking 变更必须新 major；PyArrow 仍为 lazy optional dependency，由 `quant` extra 提供。本层不建立质量门禁、fallback policy 或真实 Provider 调用。
- Dataset Catalog 与 Manifest 已完成：`LocalDatasetCatalog` 管理不可变 Dataset Version Manifest、Artifact 文件哈希、schema hash、previous/input lineage、run/stage/trace 和 metadata；`latest` 是单独持久化的可变 alias，只允许 discovery/research display，正式实验解析必须使用具体 dataset version。本层不实现质量规则、quarantine/blocking、fallback policy、真实 Provider 调用、Worker runtime、Quant Core、正式回测或 Evidence Agent。
- Data Quality Rule Engine 已完成：`DataQualityEngine` 对 schema-bound Dataset snapshots 执行离线规则，内置唯一主键、Schema/类型、OHLC、非负字段、空值漂移、交易日连续性、收益/成交量异常和复权因子跳变规则；`DataQualityReport` 输出 `passed` / `warning` / `quarantine` / `blocking`、issue counts、rule set version、trace/run/stage、deterministic Artifact 和 manifest metadata。
- Dataset 隔离区与原子发布已完成：`QualityGatedDatasetPublisher` 复用 Dataset Catalog、Data Quality Report 和 ArtifactStore，先写质量报告 Artifact 与不可变 Dataset Manifest，只有 `passed` 显式提升为 `latest`；`warning/quarantine/blocking` 写入 held/quarantine/blocking 记录并保留旧 latest，失败路径清理显式 tmp 根。本层不实现 fallback policy、Provider fixture、真实 Provider/LLM 调用、Worker runtime、Quant Core、正式回测或 Evidence Agent。
- Provider 契约 Fixture 已完成：`ProviderContractFixtureCatalog` 在 `integrations.data` 边界维护 AKShare、efinance、Tushare、BaoStock、YFinance 的离线脱敏样本；成功样本可生成不可变 `DataBatch` 与 Provider provenance，异常样本映射 `retryable/data_invalid/schema_drift`，快照绑定 `dataset.bars_1d_raw@1.0.0` Arrow schema hash；本层不实现 fallback policy、不导入 Provider SDK、不调用真实 Provider。
- Provider Policy 与 fallback trace 已完成：`ProviderPolicyEngine` 在 `integrations.data` 边界只消费离线 `DataBatch` / `ProviderError` outcomes；按 policy priority、market/capability、freshness、required fields 和 `DataQualityStatus` 选择来源，成功但 stale、缺字段、quality quarantine/blocking 或跨源 close 差异超阈值均不会静默成功；fallback trace 记录 attempts、冲突、raw-response hash、trace/run/stage 和最终状态。本层不调用 Provider SDK、不写 Dataset、不启动 Worker/Quant/Evidence。
- 增量同步与交易日调度已完成：`DataSyncScheduler` 使用 `TradingCalendarDataset` 和 checkpoint 生成交易日计划，支持 lookback window、非交易日 skip、Catalog latest previous lineage、默认缺口补数和显式完整重放；`LocalDataSyncStateStore` 以原子 JSON checkpoint 与文件独占 lock 防止并发；`DataSyncRun` 复用 `Run/Stage/Event`，只有 Provider Policy `selected` 且有具体 Dataset version 才推进 checkpoint，`exhausted/quarantined` 只记录失败等待重试。本层不调用真实 Provider/LLM、不发布真实 Dataset、不启动 Worker/PersistentTaskBackend/Quant/Evidence。
- PostgreSQL standalone Profile 已完成：`repositories.database` 复用 Runtime Profile 与 Alembic preflight，建立 PostgreSQL `psycopg` 连接池、statement timeout、redacted diagnostics、SQLite foreign key/busy timeout/WAL 默认值和 Repository Contract probe；同一 Contract suite 约束 UTC datetime、`Decimal`、date、JSON、duplicate key 和 rollback 语义。本层不启动 Compose service、PersistentTaskBackend、Worker lease、Celery/Redis、Quant Core、正式回测、Evidence Agent 或真实 Provider/LLM 调用。
- PersistentTaskBackend 已完成：`repositories.persistent_task_backend` 复用 `TaskBackend` Protocol 和 SQLAlchemy database profile，数据库表 `serenity_task_backend_runs` / `serenity_task_backend_events` 是任务快照、事件补发和恢复审计的权威来源；`CeleryTaskQueueRouter` 只向 Celery/Redis broker 投递 `task_id/run_id/task_type` 小型引用，queue message id 仅作诊断；Worker primitives 覆盖 lease、heartbeat、complete、fail 和 expired lease requeue。本层不启动完整 Worker loop、API/SSE、Quant Core、正式回测、Evidence Agent 或真实 Provider/LLM 调用。
- ScreeningProvider 已完成：`application.screening_provider` 定义平台筛选 Provider port、DTO、Fake 和统一错误语义，`integrations.alphasift.provider_adapter` 是唯一 AlphaSift 适配边界；Application/Domain 不导入 AlphaSift 内部类，真实 AlphaSift provider 调用受 profile guard 保护，LLM overlay 默认关闭且独立记录。
- CandidateBatch 已完成：`application.candidate_batch` 定义平台标准候选批次、canonical InstrumentId、具体 Dataset Version guard、source snapshot/discovered time、rank、L1/L2/L3 score records、reason/source lineage、LLM overlay independence、冻结 nested payload 和 JSON-friendly `to_record()`；后续 Screen/Factor 必须复用该契约，不得把 raw provider candidates 直接写入股票池。
- DSA 是产品主干，不是量化内核；真实组合回测、PIT 数据和硬风控必须独立实现。
- AlphaSift 只负责候选发现/快照筛选；Qlib 只能通过独立 Quant Worker Adapter 接入。
- 任何历史回测必须使用不可变 Dataset Version 与 `available_at <= decision_time` 的数据。
- 不接入实盘交易；LLM 没有交易、Shell 或任意数据库写权限。
- 后续实现不得绕过 ADR-001/002 与 Gate G1；不得在对应任务前启动 Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用或未经批准的大规模 DSA 源码迁移。

## 已接受风险

- `RSK-008` 已关闭：Serenity root Python 依赖由 `uv.lock` 锁定，`requirements.txt` 由 lock 导出并校验漂移，生产/桌面安装面不包含动态 Git 依赖；AlphaSift 已由 `SAL-P3-001` 锁定源码 commit 与停止条件，并由 `SAL-P3-002` 完成离线 Wheel intake、SBOM、许可证清单和内部制品引用。
- `RSK-010`：Web npm audit 仍有 10 个 high；后续由受控升级或 `SAL-P6-005` 发布安全门禁关闭/豁免。
- `RSK-011`：Web lockfile 混用 npmjs 与 npmmirror resolved URL；`SAL-P1-003` 仅治理 Python root lock，后续由受控前端依赖升级或发布前依赖治理统一策略。
- `RSK-012`：Docker image Grype 仍有 39 critical / 84 high；由 `SAL-P6-005` 前修复或正式豁免。

## 下一步

1. 优先执行 `SAL-P4-005` 锁定 Qlib 版本与隔离方案，审查许可证、依赖、平台兼容和 Worker 资源。
2. 不得直接启动正式组合回测运行、Evidence Agent、真实 Provider/LLM、Qlib runtime、Ledger/Risk/Quant Lab 或 Worker loop；真实调用仍只能在后续 Worker/调度任务中通过 profile guard、离线契约和 fallback trace 接入。
3. legacy DSA Signal Evaluation、AlphaSift T+N evaluation 或 Screen result 不得直接命名为正式组合回测；后续任务必须继续与 legacy `/api/v1/backtest/*` 兼容面隔离。

## 本次状态复核

- 2026-07-20：完成 `SAL-P1-001`，批准上游与模块化 ADR；后续实现继续受 ADR-001/002 约束。
- 2026-07-20：完成 `SAL-P1-002` 与 `SAL-P1-004`，新增 Python 项目元数据、DSA entry-point wrappers、目标包骨架和架构边界测试。当前已完成 `SAL-P0-001` 至 `SAL-P0-013` 和 `SAL-P1-001`、`SAL-P1-002`、`SAL-P1-004`，Gate G1 仍未通过；`SAL-P1-003` 与 `SAL-P1-006` 是推荐下一步。
- 2026-07-20：完成 `SAL-P1-003` 与 `SAL-P1-006`，新增 Python extras/lock/requirements drift guard 和 Run/Stage/Event 领域模型；当前已完成 `SAL-P0-001` 至 `SAL-P0-013` 和 `SAL-P1-001`、`SAL-P1-002`、`SAL-P1-003`、`SAL-P1-004`、`SAL-P1-006`，Gate G1 仍未通过；`SAL-P1-005`、`SAL-P1-007`、`SAL-P1-008`、`SAL-P1-011` 是推荐下一步。
- 2026-07-20：完成 `SAL-P1-005`，新增统一 `InstrumentId`、市场/交易所/资产类型和 Provider Symbol Mapping；当前已完成 `SAL-P0-001` 至 `SAL-P0-013` 和 `SAL-P1-001`、`SAL-P1-002`、`SAL-P1-003`、`SAL-P1-004`、`SAL-P1-005`、`SAL-P1-006`，Gate G1 仍未通过；`SAL-P1-007`、`SAL-P1-008`、`SAL-P1-011`、`SAL-P1-014` 是推荐下一步。
- 2026-07-20：完成 `SAL-P1-007`，新增 Artifact 纯领域模型和本地内容寻址存储；当前已完成 `SAL-P0-001` 至 `SAL-P0-013` 和 `SAL-P1-001`、`SAL-P1-002`、`SAL-P1-003`、`SAL-P1-004`、`SAL-P1-005`、`SAL-P1-006`、`SAL-P1-007`，Gate G1 仍未通过；`SAL-P1-008`、`SAL-P1-011`、`SAL-P1-014` 是推荐下一步。
- 2026-07-20：完成 `SAL-P1-008`，新增 TaskBackend Protocol、InMemory 实现和注入式 DSA 兼容 facade；当前已完成 `SAL-P0-001` 至 `SAL-P0-013` 和 `SAL-P1-001`、`SAL-P1-002`、`SAL-P1-003`、`SAL-P1-004`、`SAL-P1-005`、`SAL-P1-006`、`SAL-P1-007`、`SAL-P1-008`，Gate G1 仍未通过；`SAL-P1-011`、`SAL-P1-014`、`SAL-P1-009`、`SAL-P1-010` 是推荐下一步。
- 2026-07-20：完成 `SAL-P1-011`，新增结构化 JSON 日志、Trace context、脱敏和 ASGI middleware；当前已完成 `SAL-P0-001` 至 `SAL-P0-013` 和 `SAL-P1-001`、`SAL-P1-002`、`SAL-P1-003`、`SAL-P1-004`、`SAL-P1-005`、`SAL-P1-006`、`SAL-P1-007`、`SAL-P1-008`、`SAL-P1-011`，Gate G1 仍未通过；`SAL-P1-014`、`SAL-P1-009`、`SAL-P1-010` 是推荐下一步。
- 2026-07-20：完成 `SAL-P1-014`，新增配置 Profile、CI 密钥边界、脱敏诊断和无副作用更新预览；当前已完成 `SAL-P0-001` 至 `SAL-P0-013` 和 `SAL-P1-001`、`SAL-P1-002`、`SAL-P1-003`、`SAL-P1-004`、`SAL-P1-005`、`SAL-P1-006`、`SAL-P1-007`、`SAL-P1-008`、`SAL-P1-011`、`SAL-P1-014`，Gate G1 仍未通过；`SAL-P1-009`、`SAL-P1-010`、`SAL-P1-012` 是推荐下一步。
- 2026-07-20：完成 `SAL-P1-009`，新增 ResearchOrchestrator Protocol、run/chat DTO 和 DSA 注入式兼容 facade；当前已完成 `SAL-P0-001` 至 `SAL-P0-013` 和 `SAL-P1-001`、`SAL-P1-002`、`SAL-P1-003`、`SAL-P1-004`、`SAL-P1-005`、`SAL-P1-006`、`SAL-P1-007`、`SAL-P1-008`、`SAL-P1-009`、`SAL-P1-011`、`SAL-P1-014`，Gate G1 仍未通过；`SAL-P1-010`、`SAL-P1-012` 是推荐下一步。
- 2026-07-20：完成 `SAL-P1-010`，新增 API Problem Details 协议、稳定错误码、异常映射、脱敏和框架无关 ASGI middleware；当前已完成 `SAL-P0-001` 至 `SAL-P0-013` 和 `SAL-P1-001`、`SAL-P1-002`、`SAL-P1-003`、`SAL-P1-004`、`SAL-P1-005`、`SAL-P1-006`、`SAL-P1-007`、`SAL-P1-008`、`SAL-P1-009`、`SAL-P1-010`、`SAL-P1-011`、`SAL-P1-014`，Gate G1 仍未通过；`SAL-P1-012` 是推荐下一步。
- 2026-07-20：完成 `SAL-P1-012`，新增 Alembic baseline revision、空库升级命令和启动前 revision preflight；当前已完成 `SAL-P0-001` 至 `SAL-P0-013` 和 `SAL-P1-001`、`SAL-P1-002`、`SAL-P1-003`、`SAL-P1-004`、`SAL-P1-005`、`SAL-P1-006`、`SAL-P1-007`、`SAL-P1-008`、`SAL-P1-009`、`SAL-P1-010`、`SAL-P1-011`、`SAL-P1-012`、`SAL-P1-014`，Gate G1 仍未通过；`SAL-P1-013` 是推荐下一步。
- 2026-07-20：完成 `SAL-P1-013`，新增 SQLite fixture upgrade rehearsal、业务表内容校验、幂等重跑和失败恢复；当前已完成 `SAL-P0-001` 至 `SAL-P0-013` 和 `SAL-P1-001`、`SAL-P1-002`、`SAL-P1-003`、`SAL-P1-004`、`SAL-P1-005`、`SAL-P1-006`、`SAL-P1-007`、`SAL-P1-008`、`SAL-P1-009`、`SAL-P1-010`、`SAL-P1-011`、`SAL-P1-012`、`SAL-P1-013`、`SAL-P1-014`，Gate G1 仍未通过；`SAL-P1-015` 是推荐下一步。
- 2026-07-20：完成 `SAL-P1-015`，新增 Desktop 兼容和性能基线脚本，离线矩阵 PASS，Desktop 后端 health 启动 `5,822ms`、单股报告生成均值 `0.030ms`；当前已完成 P1 `15/16`，Gate G1 仍未通过；`SAL-P1-016` 是唯一推荐下一步。
- 2026-07-20：完成 `SAL-P1-016`，Gate G1 结论为 `GO with accepted risks`，P1 完成 `16/16`，总进度 `29/129`；项目已进入 P2，`SAL-P2-001` 是唯一推荐下一步。
- 2026-07-20：按用户要求复核最新开发状态；确认当前 Phase 为 P2，Gate G2 未通过，G0/G1 已通过，`SAL-P0-001..013` 与 `SAL-P1-001..016` 已完成，`SAL-P2-001` 为当前 `READY` 任务；本次同步同时更新 `tasks/lessons.md` 以固化阶段性任务完成后的状态同步习惯。
- 2026-07-21：完成 `SAL-P2-001`，冻结同步 Provider Protocol、Capability、不可变 DataBatch/Provenance、warning 和六类错误；Provider contract `23 passed`、相关套件 `109 passed`、全量 pytest `128 passed`，P2 进度 `1/20`、总进度 `30/129`，`SAL-P2-002` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-21：按用户要求再次同步最新状态；确认最近可评审交付为 `f7bc8ba8 feat(P2): 定义 Provider 领域契约`，当前工作从 `SAL-P2-002` 继续，仍不得提前启动 Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用或大规模 DSA 源码迁移。
- 2026-07-21：完成 `SAL-P2-002`，新增 DSA Provider Compatibility Adapter 和 feature-flag stock-history facade；Adapter target `8 passed`、相关套件 `22 passed`、全量 pytest `137 passed`，P2 进度 `2/20`、总进度 `31/129`，`SAL-P2-003` 与 `SAL-P2-004` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-21：按用户要求同步 `SAL-P2-002` checkpoint 后最新状态；确认最近可评审交付为 `68e8fea9 feat(P2): 实现 DSA Provider 兼容适配器`，当前已完成 `SAL-P0-001..013`、`SAL-P1-001..016`、`SAL-P2-001..002`，未完成范围为 P2 至 P6 剩余 98 项；下一步从 `SAL-P2-003` / `SAL-P2-004` 继续。
- 2026-07-21：完成 `SAL-P2-003`，新增 DSA 证券代码兼容 mapper 和不可变 mapping；Symbol target `25 passed`、相关套件 `72 passed`、全量 pytest `155 passed`，P2 进度 `3/20`、总进度 `32/129`，`SAL-P2-004` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-21：完成 `SAL-P2-004`，新增 Bronze 原始响应层、deterministic gzip Artifact、落盘前密钥/Cookie/PII 脱敏和 provider/request/time 追踪 helper；Bronze target `6 passed`、相关套件 `56 passed`、全量 pytest `162 passed`，P2 进度 `4/20`、总进度 `33/129`，`SAL-P2-005` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-21：完成 `SAL-P2-005`，新增证券主数据 Dataset、历史 as-of 查询、Provider 映射有效期和 deterministic Artifact 发布；Instrument master target `3 passed`、相关套件 `15 passed` 和 `81 passed`、全量 pytest `166 passed`，P2 进度 `5/20`、总进度 `34/129`，`SAL-P2-006` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-21：完成 `SAL-P2-006`，新增交易日历 Dataset、市场时区冻结、交易/闭市/半日/异常休市 session、午休窗口、UTC/Asia-Shanghai 转换金标、查询缓存和 deterministic Artifact 发布；Trading calendar target `3 passed`、相关套件 `56 passed`、全量 pytest `169 passed`，P2 进度 `6/20`、总进度 `35/129`，`SAL-P2-007` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-21：完成 `SAL-P2-007`，新增原始日线 Dataset、未复权 OHLCV/amount、Provider batch 转换、Instrument Master as-of 校验、Trading Calendar trading-day 校验、Bronze lineage、查询索引、增量合并和 deterministic Artifact 发布；Raw daily bars target `3 passed`、相关套件 `59 passed`、全量 pytest `172 passed`，P2 进度 `7/20`、总进度 `36/129`，`SAL-P2-008` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-22：完成 `SAL-P2-008`，新增公司行动 Dataset、现金分红/送转/配股固定样本、前复权/后复权因子、复权日线 Artifact、provider-scoped action filtering、raw price immutability 和 ProblemDetails validation mapping；Corporate actions target `3 passed`、相关套件 `68 passed`、全量 pytest `175 passed`，P2 进度 `8/20`、总进度 `37/129`，`SAL-P2-009` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-22：完成 `SAL-P2-009`，新增 PIT 基本面 Dataset、period/announced/available/ingested/revision 固定样本、`available_at <= decision_time` 查询、latest revision 选择、unknown temporal confidence research-only/formal-backtest rejection、Bronze lineage、incremental merge 和 ProblemDetails validation mapping；Fundamentals target `4 passed`、相关套件 `51 passed`、全量 pytest `179 passed`，P2 进度 `9/20`、总进度 `38/129`，`SAL-P2-010` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-22：完成 `SAL-P2-010`，新增 Arrow Schema Registry、五类 P2 Dataset 默认注册、lazy PyArrow conversion、schema metadata、semantic-version compatibility、duplicate version guard 和 Arrow/Pandas/Polars round-trip 测试；Schema registry target `6 passed`、instrument master related `9 passed`、P2 related suite `62 passed`、full pytest `185 passed`，compileall/lock/diff/tag checks PASS，P2 进度 `10/20`、总进度 `39/129`，`SAL-P2-011` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-22：完成 `SAL-P2-011`，新增 Dataset Catalog、不可变版本 Manifest、Artifact 文件哈希、schema hash binding、previous/input lineage、latest alias 和正式实验 latest 拒绝；Dataset catalog target `5 passed`、相关套件 `45 passed`、full pytest `190 passed`，compileall/lock/diff/tag checks PASS，P2 进度 `11/20`、总进度 `40/129`，`SAL-P2-012` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-22：完成 `SAL-P2-012`，checkpoint `3a846c6a feat(P2): 实现数据质量规则引擎`；新增 Data Quality Rule Engine、warning/quarantine/blocking quality report、issue 精确定位、deterministic report Artifact 和 manifest metadata helper；Data quality target `4 passed`、相关套件 `61 passed`、full pytest `194 passed`，compileall/lock/diff/tag checks PASS，P2 进度 `12/20`、总进度 `41/129`，`SAL-P2-013` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-23：完成 `SAL-P2-013`，新增 Dataset 隔离区与原子发布；Dataset publication target `5 passed`、相关套件 `66 passed`、full pytest `199 passed`，compileall/lock/diff/tag checks PASS，P2 进度 `13/20`、总进度 `42/129`，`SAL-P2-014` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-23：完成 `SAL-P2-014`，新增 Provider 契约 Fixture；Provider fixture target `4 passed`、相关 Provider/Schema/API/Architecture suite `58 passed`、full pytest `203 passed`，compileall/lock/diff/tag checks PASS，P2 进度 `14/20`、总进度 `43/129`，`SAL-P2-015` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-23：按用户要求再次复核最新开发状态并固化恢复提示；确认已完成范围仍为 `SAL-P0-001..013`、`SAL-P1-001..016`、`SAL-P2-001..014`，未完成范围从 `SAL-P2-015` 开始，当前 READY 任务为 `SAL-P2-015`，最近实现 checkpoint 为 `5016ced6 feat(P2): 建立 Provider 契约 Fixture`，上一状态同步 checkpoint 为 `8c70cde5 docs: 同步 SAL-P2-014 最新开发状态与恢复提示`。
- 2026-07-23：完成 `SAL-P2-015`，新增 Provider Policy 与 fallback trace；Provider policy target `6 passed`、相关 Provider/Quality/Publication/API/Architecture suite `59 passed`、full pytest `209 passed`，P2 进度 `15/20`、总进度 `44/129`，`SAL-P2-016` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-23：按用户要求同步 `SAL-P2-015` checkpoint 后最新状态；确认最近可评审交付为 `378ba734 feat(P2): 实现 Provider Policy 与 fallback trace`，当前已完成 `SAL-P0-001..013`、`SAL-P1-001..016`、`SAL-P2-001..015`，未完成范围从 `SAL-P2-016` 开始，当前 READY 任务为 `SAL-P2-016`，并已在 `tasks/lessons.md` 固化“阶段性任务完成后自动状态同步”的习惯。
- 2026-07-23：完成 `SAL-P2-016`，新增增量同步与交易日调度层；Data sync target `5 passed`、相关 Trading Calendar/Catalog/Provider Policy/Run lifecycle/Architecture suite `35 passed`、full pytest `214 passed`，compileall/lock/diff/tag checks PASS，P2 进度 `16/20`、总进度 `45/129`，`SAL-P2-017` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-23：按用户要求再次复核 `SAL-P2-016` 后最新开发状态；确认最近可评审交付为 `cfadc415 feat(P2): 实现增量同步与交易日调度`，上一状态同步 checkpoint 为 `70f82cee docs: 同步 SAL-P2-016 最新状态与恢复提示`，当前已完成 `SAL-P0-001..013`、`SAL-P1-001..016`、`SAL-P2-001..016`，未完成范围从 `SAL-P2-017` 开始，当前 READY 任务为 `SAL-P2-017`，并已在 `tasks/lessons.md` 再次固化“阶段性任务完成后自动状态同步并给出可复制提示词”的习惯。
- 2026-07-23：完成 `SAL-P2-017`，新增 PostgreSQL standalone Profile、连接池、readiness 和 Repository Contract probe；target database profile/repository/storage tests `10 passed, 3 skipped`、相关 repositories/config/API/architecture suite `50 passed, 3 skipped`、full pytest `220 passed, 3 skipped`，compileall/lock/diff/tag checks PASS，P2 进度 `17/20`、总进度 `46/129`，`SAL-P2-018` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-23：完成 `SAL-P2-018`，新增 PersistentTaskBackend、Celery/Redis 注入式队列路由、数据库权威 task events、取消请求、Worker lease/heartbeat/complete/fail 和 expired lease requeue primitives；target persistent backend tests `5 passed`、相关 TaskBackend/Repository/API/Architecture suite `35 passed, 3 skipped`、full pytest `225 passed, 3 skipped`，compileall/lock/diff/tag checks PASS，P2 进度 `18/20`、总进度 `47/129`，`SAL-P2-019` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-23：完成 `SAL-P2-019`，新增可恢复任务事件流、RunEvent 持久化、SSE `Last-Event-ID` replay、queued orphan redispatch、stalled lease requeue 和临时 Artifact cleanup；target task event stream tests `8 passed`、相关 TaskBackend/Repository/API/Architecture suite `40 passed, 3 skipped`、full pytest `233 passed, 3 skipped`，compileall PASS，P2 进度 `19/20`、总进度 `48/129`，`SAL-P2-020` 成为当前 `READY` 任务，Gate G2 仍未通过。
- 2026-07-23：完成 `SAL-P2-020` Gate G2 数据与任务评审，结论为 `GO with accepted risks`；新增 Gate G2 review、Gate integration test 和 AEV-049，验证离线 Provider fixture -> Provider Policy -> versioned A-share Dataset publication、Provider conflict quarantine、PersistentTaskBackend restart/SSE replay 和 DSA 单股兼容路径；Gate target `3 passed`、相关 P2 suite `80 passed, 3 skipped`、full pytest `236 passed, 3 skipped`、compileall/lock/diff/tag checks PASS，P2 完成 `20/20`、总进度 `49/129`，项目进入 P3，`SAL-P3-001` 成为当前 `READY` 任务。
- 2026-07-23：完成 `SAL-P3-001` AlphaSift 源码审查与锁定；锁定 `ZhuLinsen/alphasift@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`、source archive SHA-256 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a`、Apache-2.0 attribution、依赖清单、current-resolution SCA、已知限制、升级/替换/停止使用条件；Red doc test `2 failed`、target/dependency suite `6 passed`、full pytest `238 passed, 3 skipped`、compileall/lock/diff/tag checks PASS，P3 进度 `1/17`、总进度 `50/129`，`SAL-P3-002` 成为当前 `READY` 任务。
- 2026-07-23：完成 `SAL-P3-002` AlphaSift 离线 Wheel intake；source archive SHA-256 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a`、reproducible wheel SHA-256 `b71fe6f4b11c9655b2190f91217fee66361f9852ae344c53fe501455a4823ed2`、internal artifact URI、CycloneDX SBOM、license inventory 和 offline no-deps install check 已记录；Red intake test `4 failed`、Green target `4 passed`、related architecture suite `10 passed`、full pytest `242 passed, 3 skipped`，compileall/lock/diff/tag checks PASS，P3 进度 `2/17`、总进度 `51/129`，`SAL-P3-003` 成为当前 `READY` 任务。
- 2026-07-23：完成 `SAL-P3-003` ScreeningProvider；新增平台 `ScreeningProvider` Protocol、DTO、Fake、`AlphaSiftScreeningAdapter`、ProblemDetails 映射和架构边界测试；Red contract test `1 error`、Red adapter test `1 error`、Green target/related suite `22 passed`、full pytest `252 passed, 3 skipped`，compileall/lock/diff/tag checks PASS，P3 进度 `3/17`、总进度 `52/129`，`SAL-P3-004` 成为当前 `READY` 任务。
- 2026-07-23：完成 `SAL-P3-004` CandidateBatch；新增平台标准候选批次契约、canonical `InstrumentId`、具体 Dataset Version guard、source snapshot/discovered time、rank、L1/L2/L3 score records、reason/source lineage、LLM overlay independence、冻结 nested records、JSON-friendly `to_record()` 和 `ScreeningResult` metadata bridge；Red contract test `1 error`、Green target `3 passed`、related suite `25 passed`，full pytest `255 passed, 3 skipped`，compileall/lock/diff/tag checks PASS，P3 进度 `4/17`、总进度 `53/129`，`SAL-P3-005` 成为当前 `READY` 任务；实现 checkpoint 为 `07b5d526 feat(P3): 定义 CandidateBatch 候选契约`。
- 2026-07-23：完成 `SAL-P3-005` FactorDefinition 版本模型；新增 `quant.factor_definition@1.0.0`、FactorDefinition/Formula/Input/Window/Missing/PostProcessing DTO、draft/published/retired 生命周期、本地定义仓库、不可变 published manifest、独立 retirement record 和 audit events；Red contract test `1 error`、Green target `3 passed`、related suite `28 passed`，P3 进度 `5/17`、总进度 `54/129`，`SAL-P3-006` 成为当前 `READY` 任务；实现 checkpoint 为 `d405e6ab feat(P3): 实现 FactorDefinition 版本模型`。
- 2026-07-24：按用户要求复核 `SAL-P3-005` 后最新开发状态；确认最近可评审交付为 `d405e6ab feat(P3): 实现 FactorDefinition 版本模型`，当前已完成 `SAL-P0-001..013`、`SAL-P1-001..016`、`SAL-P2-001..020`、`SAL-P3-001..005`，未完成范围从 `SAL-P3-006` 开始，当前 READY 任务为 `SAL-P3-006`，并已在 `tasks/lessons.md` 再次固化“阶段性任务完成后自动状态同步并给出可复制提示词”的习惯。
- 2026-07-24：完成 `SAL-P3-006` Factor DSL 与算子白名单；新增 `serenity_factor_dsl@1.0.0`、白名单 parser/AST/validator/compiler、`FactorExpressionPlan`、`FactorExpressionNode`、`compile_factor_expression()` 和 `compile_factor_definition()`；Red contract test `1 error`、Green target `14 passed`、related suite `42 passed`，full pytest `272 passed, 3 skipped`，P3 进度 `6/17`、总进度 `55/129`，`SAL-P3-007` 成为当前 `READY` 任务；实现 checkpoint 为 `a63822d0 feat(P3): 实现因子 DSL 与算子白名单`。
- 2026-07-24：按用户要求再次复核 `SAL-P3-006` 后最新开发状态；确认最近可评审交付为 `a63822d0 feat(P3): 实现因子 DSL 与算子白名单`，上一状态同步 checkpoint 为 `6ee91eed docs: 同步 SAL-P3-006 checkpoint hash`，当前已完成 `SAL-P0-001..013`、`SAL-P1-001..016`、`SAL-P2-001..020`、`SAL-P3-001..006`，未完成范围从 `SAL-P3-007` 开始，当前 READY 任务为 `SAL-P3-007`，并已在 `tasks/lessons.md` 再次固化“阶段性任务完成后自动状态同步并给出可复制提示词”的习惯。
- 2026-07-24：完成 `SAL-P3-007` 首批基础因子；新增 `base_factor_catalog@1.0.0`、15 个 `FactorDefinition` draft、具体 `dsv_*` Dataset Version 引用、分类计数、适用市场、数据需求和 hand-authored DSL plan reference；Red contract test `1 error`、Green target `4 passed`、related suite `46 passed`，full pytest `276 passed, 3 skipped`，P3 进度 `7/17`、总进度 `56/129`，`SAL-P3-008` 成为当前 `READY` 任务；实现 checkpoint 为 `27b87c2e feat(P3): 交付首批基础因子`。
- 2026-07-24：按用户要求复核 `SAL-P3-007` 后最新开发状态；确认最近可评审交付为 `27b87c2e feat(P3): 交付首批基础因子`，上一状态同步 checkpoint 为 `e3ce4840 docs: 同步 SAL-P3-007 checkpoint hash`，当前已完成 `SAL-P0-001..013`、`SAL-P1-001..016`、`SAL-P2-001..020`、`SAL-P3-001..007`，未完成范围从 `SAL-P3-008` 开始，当前 READY 任务为 `SAL-P3-008`，并已在 `tasks/lessons.md` 再次固化“阶段性任务完成后自动状态同步并给出可复制提示词”的习惯。
- 2026-07-24：完成 `SAL-P3-008` 横截面因子后处理；新增 `quant.factor_cross_section_post_processing@1.0.0`、显式 Dataset Version guard、per-date universe grouping、缺失处理、winsorize、行业/`log_market_cap` neutralization、z-score 标准化和 edge-case warning；Red contract test `1 error`、Green target `4 passed`、factor related suite `25 passed`、相关 P3/Architecture suite `50 passed`、full pytest `280 passed, 3 skipped`，P3 进度 `8/17`、总进度 `57/129`，`SAL-P3-009` 成为当前 `READY` 任务；实现 checkpoint 为 `dc23e769 feat(P3): 实现横截面因子后处理`。
- 2026-07-24：完成 `SAL-P3-009` Factor Evaluation；新增 `quant.factor_evaluation@1.0.0`、版本化 `FutureReturnWindow`、具体 Dataset Version guard、PIT decision-time guard、sample-overlap warning、覆盖率、IC/ICIR、分组收益、方向调整单调性、目标组换手、暴露 summary 和 deterministic Artifact report 发布；Red contract test `1 error`、Green target `4 passed`、factor related suite `29 passed`、相关 P3/Architecture suite `54 passed`、full pytest `284 passed, 3 skipped`，P3 进度 `9/17`、总进度 `58/129`，`SAL-P3-010` 与 `SAL-P3-011` 成为当前 `READY` 任务；实现 checkpoint 为 `fb7beb02 feat(P3): 实现 Factor Evaluation`，上一实现 checkpoint 为 `dc23e769 feat(P3): 实现横截面因子后处理`。
- 2026-07-24：完成 `SAL-P3-010` Factor DAG/cache；新增 `factor_engine@1.0.0`、DAG node CSE、published FactorDefinition version binding、factor-specific Dataset/Factor/Universe/date-range/engine/partition cache key、time-series instrument/date partition、cross-section date partition、duplicate/date-range/identity guards、lookback incremental recompute、failed quality gate publication rejection 和 deterministic cache manifest Artifact；Red contract test `1 error`、review regression Red `5 failed, 3 passed`、Green target `8 passed`、factor related suite `37 passed`、相关 P3/Architecture suite `62 passed`、full pytest `292 passed, 3 skipped`，P3 进度 `10/17`、总进度 `59/129`，`SAL-P3-011` 成为当前 `READY` 任务；实现 checkpoint 为 `d34b8690 feat(P3): 实现 Factor DAG cache`，上一实现 checkpoint 为 `fb7beb02 feat(P3): 实现 Factor Evaluation`。
- 2026-07-24：完成 `SAL-P3-011` Historical Universe；新增 `quant.historical_universe@1.0.0`、具体 Dataset Version guard、PIT Instrument Master as-of membership/status、上市交易日、ST、退市、显式停牌、daily-bar availability、rule evidence completeness、deterministic `dsv_*` universe version 和 Artifact publication；Red contract test `1 error`、Green target `4 passed`、相关 HistoricalUniverse/P2 Dataset/P3 suite `45 passed`、full pytest `296 passed, 3 skipped`，P3 进度 `11/17`、总进度 `60/129`，`SAL-P3-012` 成为当前 `READY` 任务；实现 checkpoint 为 `adc7741f feat(P3): 实现 Historical Universe`，上一实现 checkpoint 为 `d34b8690 feat(P3): 实现 Factor DAG cache`。
- 2026-07-24：完成 `SAL-P3-012` ScreenDefinition 与 L0~L4 Pipeline；新增 `quant.screen_pipeline@1.0.0`、版本化 `ScreenDefinition`、具体 Dataset Version guard、published run guard、L1 Provider、L2 Factor、L3 LLM overlay、L4 `top_n`/`max_per_industry` deterministic risk gate、stage trace、candidate/exclusion DTO 和 deterministic Artifact publication；Red contract test `1 error`、Green target `3 passed`、相关 ScreenDefinition/HistoricalUniverse/FactorPostProcessing/FactorDAG/CandidateBatch/ScreeningProvider/Architecture suite `44 passed`、full pytest `299 passed, 3 skipped`，P3 进度 `12/17`、总进度 `61/129`，`SAL-P3-013` 成为当前 `READY` 任务；实现 checkpoint 为 `b2d8df93 feat(P3): 实现 ScreenDefinition Pipeline`，上一实现 checkpoint 为 `adc7741f feat(P3): 实现 Historical Universe`。
- 2026-07-24：完成 `SAL-P3-013` ScreenSnapshot 与解释轨迹；新增 `quant.screen_snapshot@1.0.0`、结果行、结构化 explanation steps、passed/failed rank 与 failed-stage invariants、本地 snapshot comparison 和 deterministic Artifact publication；Red contract test `1 error`、Green target `3 passed`、相关 ScreenSnapshot/ScreenDefinition/HistoricalUniverse/FactorPostProcessing/CandidateBatch/ScreeningProvider/AlphaSift/Architecture suite `39 passed`、full pytest `302 passed, 3 skipped`，P3 进度 `13/17`、总进度 `62/129`，`SAL-P3-014` 成为当前 `READY` 任务；实现 checkpoint 为 `10d97975 feat(P3): 实现 ScreenSnapshot 解释轨迹`，上一实现 checkpoint 为 `b2d8df93 feat(P3): 实现 ScreenDefinition Pipeline`。
- 2026-07-24：完成 `SAL-P3-014` Quant Screening API；新增 `application.quant_screening_api@1.0.0`、`/api/v1/quant` route metadata、FactorDefinition/ScreenDefinition create responses、screen run `202 Accepted`、required Idempotency-Key、same-request replay、stable cursor pagination、single-result lookup、ScreenSnapshot comparison 和 ProblemDetails validation boundary；Red contract test `1 error`、Green target `5 passed`、相关 QuantScreeningAPI/ScreenSnapshot/ScreenDefinition/FactorEvaluation/FactorDefinition/TaskBackend/APIErrors/Trace/Architecture suite `45 passed`、full pytest `307 passed, 3 skipped`，P3 进度 `14/17`、总进度 `63/129`，`SAL-P3-015` 成为当前 `READY` 任务；实现 checkpoint 为 `dd4e9465 feat(P3): 实现 Quant Screening API`，上一实现 checkpoint 为 `10d97975 feat(P3): 实现 ScreenSnapshot 解释轨迹`。
- 2026-07-25：按用户要求复核 `SAL-P3-014` 后最新开发状态；确认最近实现 checkpoint 为 `dd4e9465 feat(P3): 实现 Quant Screening API`，最新已落地状态同步 checkpoint 为 `cd0d6c6f docs: 同步 SAL-P3-014 checkpoint hash`，当前已完成 `SAL-P0-001..013`、`SAL-P1-001..016`、`SAL-P2-001..020`、`SAL-P3-001..014`，未完成范围从 `SAL-P3-015` 开始，当前 READY 任务为 `SAL-P3-015` Screen Lab，Gate G3 仍未通过。本次仅做状态文档和习惯固化，不启动 Screen Lab、Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用、Worker loop 或 DSA runtime source migration。
- 2026-07-25：完成 `SAL-P3-015` Screen Lab；新增 DSA Web `quantScreeningApi`、`ScreenLabPage`、`/screen-lab` route、SidebarNav/i18n 集成和 `DSA-PATCH-004`；Red API/page/route tests 捕获缺失实现，Green focused web `4 files / 24 passed`，full web `92 files / 973 passed / 2 skipped`，Python full pytest `307 passed, 3 skipped`，P3 进度 `15/17`、总进度 `64/129`，`SAL-P3-016` 成为当前 `READY` 任务；实现 checkpoint 为 `847e5263 feat(P3): 实现 Screen Lab`。
- 2026-07-23：按用户要求同步 `SAL-P3-001` checkpoint 后最新状态；确认最近可评审交付为 `4e6d5ee4 docs(P3): 完成 AlphaSift 源码审查与锁定`，当前已完成 `SAL-P0-001..013`、`SAL-P1-001..016`、`SAL-P2-001..020`、`SAL-P3-001`，未完成范围从 `SAL-P3-002` 开始，当前 READY 任务为 `SAL-P3-002`，并已在 `tasks/lessons.md` 再次固化“阶段性任务完成后自动状态同步并给出可复制提示词”的习惯。
- 2026-07-22：此前按用户要求复核 `SAL-P2-010` 后状态；当时最近可评审交付为 `3e2056fe feat(P2): 建立 Arrow Schema Registry`，已完成范围为 `SAL-P0-001..013`、`SAL-P1-001..016`、`SAL-P2-001..010`，未完成范围为 `SAL-P2-011..020` 与 P3 至 P6，并由此进入 `SAL-P2-011` Dataset Catalog 与 Manifest。
- 本状态文档已明确列出已完成、未完成、当前约束、已接受风险、下一步和下次启动提示词；后续每个阶段性任务结束时继续自动同步这些内容。

## 固定收尾习惯

每个阶段性任务完成、阻塞或形成可评审交付后，都要自动更新本状态快照、进度清单、验收证据、风险/决策登记、`tasks/todo.md` review 和下次启动提示词，并创建中文 checkpoint commit；不得等待用户额外提醒。

## 会话恢复步骤

1. 阅读根目录 `AGENTS.md`。
2. 阅读 `tasks/lessons.md`，先吸收本项目已记录的纠正规则。
3. 阅读本文件、[开发方案](./ai-stock-quant-platform-development-plan.md) 和任务清单。
4. 执行 `git status --short --branch` 与 `git log -3 --oneline`，确认工作区和基线。
5. 处理当前 `DOING/BLOCKED/READY` 任务；没有明确状态时以本文件的“当前可执行任务”为准。
6. 每完成一个可评审交付，更新状态、验收证据、风险/决策和相关文档。
7. 每完成一个 Phase Gate，必须完成校验并提交中文 checkpoint；阶段内形成可运行交付时也应单独提交。

## 下次启动提示词

```text
请继续开发 /Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab。

先阅读：
1. AGENTS.md
2. tasks/lessons.md
3. docs/development-status.md
4. docs/development-progress-checklist.md
5. docs/ai-stock-quant-platform-development-plan.md
6. docs/gate-g0-baseline-review.md
7. docs/gate-g2-data-task-review.md
8. docs/alphasift-source-review.md
9. docs/alphasift-wheel-intake.md
10. docs/screening-provider-contract.md
11. docs/candidate-batch-contract.md
12. docs/factor-definition-version-model.md
13. docs/factor-dsl-operator-whitelist.md
14. docs/base-factor-definitions.md
15. docs/factor-cross-sectional-post-processing.md
16. docs/factor-evaluation.md
17. docs/factor-dag-cache.md
18. docs/historical-universe.md
19. docs/screen-definition-pipeline.md
20. docs/screen-snapshot-explanation-trace.md
21. docs/quant-screening-api.md
22. docs/screen-lab.md
23. docs/screen-performance-reproducibility.md
24. docs/gate-g3-screen-factor-review.md
25. docs/dsa-signal-evaluation-characterization.md
26. docs/signal-evaluation-engine.md
27. docs/backtest-spec.md

随后执行 git status --short --branch 和 git log -3 --oneline，确认当前状态。

当前状态：
- Phase：P4 真实组合回测与确定性风控
- Gate：G4 未通过；G0、G1、G2、G3 已通过（GO with accepted risks）
- 已完成：SAL-P0-001 至 SAL-P0-013，SAL-P1-001 至 SAL-P1-016，SAL-P2-001 至 SAL-P2-020，SAL-P3-001 至 SAL-P3-017，SAL-P4-001 至 SAL-P4-004
- 最近完成：SAL-P4-004 定义 BacktestArtifact
- 最近可评审交付 checkpoint：本次 feat(P4): 定义正式 BacktestArtifact 提交后以最终回复和 git log -1 --oneline 为准；上一 checkpoint：1ecfaa2d feat(P4): 定义正式 BacktestSpec
- 最新状态同步 checkpoint：本次 docs: 同步 SAL-P4-004 checkpoint hash 提交后以最终回复和 git log -1 --oneline 为准；上一状态同步 checkpoint：d23d5883 docs: 同步 SAL-P4-003 checkpoint hash；最新状态复核 checkpoint：cec881a6 docs: 复核 SAL-P3-016 最新开发状态
- 进度：P0 13/13，P1 16/16，P2 20/20，P3 17/17，P4 4/22，总计 70/129

下一步优先执行：
1. SAL-P4-005 锁定 Qlib 版本与隔离方案，审查许可证、依赖、平台兼容和 Worker 资源
2. 不要直接启动正式组合回测运行、Evidence Agent、真实 Provider/LLM、Qlib runtime、Ledger/Risk/Quant Lab 或 Worker loop；真实 Provider/LLM 调用仍只能在后续 Worker/调度任务中通过 profile guard、离线契约和 fallback trace 接入
3. legacy DSA Signal Evaluation、AlphaSift T+N evaluation 或 Screen result 不得直接命名为正式组合回测；后续任务必须继续与 legacy /api/v1/backtest/* 兼容面隔离

严格遵守 AGENTS.md：
- 不要把未完成任务标为完成。
- 不要移动 `upstream/dsa-v3.26.1` tag。
- 保留用户已有改动，不执行破坏性 Git 操作。
- 不提交 .worktrees、.cache、node_modules、static、Playwright artifacts、pycache 或无关未跟踪目录。
- 后续实现必须遵守 ADR-001/002 与 Gate G2/G3；不要在对应任务前开始正式组合回测、Evidence Agent、真实 Provider/LLM 调用或未经批准的大规模 DSA 源码迁移。
- 每完成阶段性任务，自动更新 docs/development-status.md、docs/development-progress-checklist.md、验收证据、风险、决策、tasks/todo.md review 和下次启动提示词。
- 每形成可评审交付时主动提交详细中文 commit。
```

> 本文件是状态快照，不替代任务清单。发生冲突时，以任务清单中的任务状态、依赖和 Gate 证据为准。
