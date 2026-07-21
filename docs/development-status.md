# Serenity Alpha Lab 当前开发状态

> 最后更新：2026-07-21<br>
> 最近阶段性任务：`SAL-P2-002` DSA Provider Compatibility Adapter<br>
> 工作区要求：从 `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab` 恢复，并重新执行 `git status`，以实际工作区为准<br>
> 当前 Phase：P2 数据与持久任务<br>
> 当前 Gate：G2，未通过；G0、G1 已通过（均为 `GO with accepted risks`）<br>
> 任务完成度：31/129<br>
> 当前可执行任务：`SAL-P2-003`、`SAL-P2-004`，状态均为 `READY`；证券代码兼容迁移和 Bronze 原始数据层必须复用已冻结的 Provider、Profile、ProblemDetails、Trace、Artifact、Run/Stage/Event、Alembic 和 Compatibility Facade<br>
> 最近可评审交付 checkpoint：`68e8fea9 feat(P2): 实现 DSA Provider 兼容适配器`<br>
> 最新状态同步 checkpoint：本文件所在提交（`docs(P2): 同步 DSA Provider Adapter 后开发状态`）；恢复时以 `git log -1 --oneline` 为准<br>
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

## 未完成

### 当前可执行 P2 任务

- `SAL-P2-003` 当前为 `READY`：用 `InstrumentId` 和 Symbol Mapping 包裹 `normalize_stock_code`，完成证券代码兼容迁移。
- `SAL-P2-004` 当前为 `READY`：建立 Bronze 原始数据层，保存可审计原始响应和请求元数据。

### 全局未完成

- 当前仓库已导入 DSA 上游 Git 历史和基线 tag，但尚未把 DSA 源码合入本项目工作树。
- P2 至 P6 仍有 98 项工程任务未完成。
- 已创建 Serenity 目标包骨架、Provider 领域契约和 DSA Provider Adapter，但尚未实现 Worker、Quant Core、PIT Dataset、正式回测、Evidence Agent 或部署环境。
- 供应链 Critical/High、Web registry 混用和 Docker 镜像漏洞是已接受的 G0 风险，但继续阻断发布或未评审依赖漂移；Serenity root Python 动态 Git 生产依赖风险已由 `SAL-P1-003` 关闭。

## 当前决策与约束

- Gate G0 与 Gate G1 已通过；Gate G2 尚未通过。DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` 仍是当前上游产品基线。
- `upstream/dsa-v3.26.1` 是本地不可变基线标签；后续升级必须新建 `sync/dsa-<version>` 分支和新基线 tag，不得移动该标签。
- ADR-001 已批准受控同步策略：所有上游吸收必须经 `sync/dsa-*` 分支、补丁结果登记、相关基线刷新和 Gate/ADR 记录。
- ADR-002 已批准渐进式模块化策略：旧 DSA 路径只能经显式 Compatibility Facade 迁移，P1 不拆微服务。
- DSA 源码通过 `.worktrees/dsa-v3.26.1` 隔离物化；依赖缓存放在 `.cache/dsa-p0`，两者均不提交。
- 当前本地偏离均为 `compatible` 或 `extension`，无 `divergence`；已登记补丁为 `DSA-PATCH-001` 至 `DSA-PATCH-003`。
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
- DSA 是产品主干，不是量化内核；真实组合回测、PIT 数据和硬风控必须独立实现。
- AlphaSift 只负责候选发现/快照筛选；Qlib 只能通过独立 Quant Worker Adapter 接入。
- 任何历史回测必须使用不可变 Dataset Version 与 `available_at <= decision_time` 的数据。
- 不接入实盘交易；LLM 没有交易、Shell 或任意数据库写权限。
- 后续实现不得绕过 ADR-001/002 与 Gate G1；不得在对应任务前启动 Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用或未经批准的大规模 DSA 源码迁移。

## 已接受风险

- `RSK-008` 已关闭：Serenity root Python 依赖由 `uv.lock` 锁定，`requirements.txt` 由 lock 导出并校验漂移，生产/桌面安装面不包含动态 Git 依赖；AlphaSift 审查后 wheel/package intake 留给后续 Adapter 任务。
- `RSK-010`：Web npm audit 仍有 10 个 high；后续由受控升级或 `SAL-P6-005` 发布安全门禁关闭/豁免。
- `RSK-011`：Web lockfile 混用 npmjs 与 npmmirror resolved URL；`SAL-P1-003` 仅治理 Python root lock，后续由受控前端依赖升级或发布前依赖治理统一策略。
- `RSK-012`：Docker image Grype 仍有 39 critical / 84 high；由 `SAL-P6-005` 前修复或正式豁免。

## 下一步

1. 优先执行 `SAL-P2-003` 证券代码兼容迁移，用 `InstrumentId` 和 Symbol Mapping 包裹 `normalize_stock_code`，处理 Provider 格式转换和歧义错误。
2. 可并行准备 `SAL-P2-004` Bronze 原始数据层，但不得提前实现 Dataset/PIT/fallback policy 或真实 Provider 调用。
3. 保持 P0/P1 required checks 和 Gate G1 约束作为基线保护，任何上游吸收必须遵守 ADR-001，任何模块化实现必须遵守 ADR-002。

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

随后执行 git status --short --branch 和 git log -3 --oneline，确认当前状态。

当前状态：
- Phase：P2 数据与持久任务
- Gate：G2 未通过；G0、G1 已通过（GO with accepted risks）
- 已完成：SAL-P0-001 至 SAL-P0-013，SAL-P1-001 至 SAL-P1-016，SAL-P2-001 至 SAL-P2-002
- 最近完成：SAL-P2-002 DSA Provider Compatibility Adapter
- 最近可评审交付 checkpoint：68e8fea9 feat(P2): 实现 DSA Provider 兼容适配器
- 最新状态同步 checkpoint：本提示词所在提交（docs(P2): 同步 DSA Provider Adapter 后开发状态）；启动后以 git log -1 --oneline 确认
- 进度：P0 13/13，P1 16/16，P2 2/20，总计 31/129

下一步优先执行：
1. SAL-P2-003 完成证券代码兼容迁移，用 InstrumentId 和 Symbol Mapping 包裹 normalize_stock_code
2. 可并行准备 SAL-P2-004 Bronze 原始数据层，但不要提前实现 Dataset/PIT/fallback policy 或真实 Provider 调用
3. 后续 Provider/Dataset/持久任务实现必须复用 Gate G1 已冻结的 Profile、ProblemDetails、Trace、Artifact、Run/Stage/Event、Alembic 和 Compatibility Facade

严格遵守 AGENTS.md：
- 不要把未完成任务标为完成。
- 不要移动 `upstream/dsa-v3.26.1` tag。
- 保留用户已有改动，不执行破坏性 Git 操作。
- 不提交 .worktrees、.cache、node_modules、static、Playwright artifacts、pycache 或无关未跟踪目录。
- 后续实现必须遵守 ADR-001/002 与 Gate G1；不要在对应任务前开始 Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用或未经批准的大规模 DSA 源码迁移。
- 每完成阶段性任务，自动更新 docs/development-status.md、docs/development-progress-checklist.md、验收证据、风险、决策、tasks/todo.md review 和下次启动提示词。
- 每形成可评审交付时主动提交详细中文 commit。
```

> 本文件是状态快照，不替代任务清单。发生冲突时，以任务清单中的任务状态、依赖和 Gate 证据为准。
