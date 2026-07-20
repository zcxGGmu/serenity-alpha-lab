# Gate G1 工程地基评审

> 任务：`SAL-P1-016` Gate G1：工程地基评审<br>
> 评审日期：2026-07-20<br>
> Phase：P1 工程加固<br>
> 上游基线：`ZhuLinsen/daily_stock_analysis v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 评审结论：`GO with accepted risks`

## 1. Gate 结论

Gate G1 通过。P1 工程加固完成度为 `16/16`，项目总完成度推进到 `29/129`，允许进入 P2 数据版本、Provider 收口与持久任务开发。

本结论批准开始 `SAL-P2-001` Provider 领域契约及后续 P2 数据/任务基础工作，但不批准以下事项：

- 不移动 `upstream/dsa-v3.26.1`，不直接跟踪上游 `main`。
- 不把 DSA runtime source 大规模迁入当前工作树。
- 不绕过 ADR-001/ADR-002 的同步分支、补丁登记、Compatibility Facade 和模块边界要求。
- 不把 DSA Signal Evaluation 解释为正式组合回测。
- 不在对应任务前启动 Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用或发布级部署门禁。

## 2. 通过条件核对

| Gate 条件 | 结论 | 证据 |
|---|---|---|
| 上游与模块化 ADR 已批准 | PASS | [ADR-001](./adr/ADR-001-upstream-takeover-sync-and-patch-policy.md) 与 [ADR-002](./adr/ADR-002-progressive-modularization-and-compatibility-facade.md) 已批准；`55946536` 不 cherry-pick，`487e49e5` 延期到 sync 分支 |
| Python 元数据、extras、lock 和安装面可复现 | PASS | `pyproject.toml`、`uv.lock`、`requirements.txt` 与 [Python 依赖 Extras 与锁文件记录](./python-dependency-lock.md)；`scripts/verify-python-dependency-lock.sh` PASS |
| 目标包骨架和架构边界已建立 | PASS | `src/serenity_alpha_lab/`、`tests/architecture/` 与 [目标包骨架记录](./development-progress-checklist.md#sal-p1-004-建立目标包骨架)；架构/领域/应用/仓储/集成测试 PASS |
| Run、Instrument、Artifact 纯领域契约可用 | PASS | [Run / Stage / Event 领域模型记录](./run-stage-event-domain-model.md)、[InstrumentId 统一证券 ID 领域模型记录](./instrument-id-domain-model.md)、[Artifact 模型与本地存储记录](./artifact-store-domain-model.md) |
| TaskBackend 与 ResearchOrchestrator 兼容 facade 可用 | PASS | [TaskBackend 协议与 DSA 兼容 Facade 记录](./task-backend-facade.md)、[ResearchOrchestrator 协议与 DSA 兼容 Facade 记录](./research-orchestrator-facade.md) |
| API 错误、Trace 日志和配置 Profile 边界可用 | PASS | [API 错误协议记录](./api-error-protocol.md)、[结构化日志与 Trace 记录](./structured-trace-logging.md)、[配置 Profile 与密钥边界记录](./config-profile-facade.md) |
| Alembic 和 SQLite 历史升级验证可用 | PASS | [Alembic 存储迁移接入记录](./storage-migration-alembic.md)、[SQLite 历史库升级验证记录](./sqlite-upgrade-verification.md) |
| Desktop/API/CLI/Bot/契约金标兼容回归通过 | PASS | [Desktop 兼容和性能基线记录](./desktop-compatibility-performance-baseline.md)；本地重新运行 `scripts/run-p1-desktop-compatibility-performance.sh --python /Users/zq/.local/bin/python3.11` PASS |
| 未解决阻断项有明确处理 | PASS | 无 G1 阻断项。供应链、Web audit、Docker image 漏洞继续作为发布前风险，不阻断进入 P2 |

## 3. P1 交付核对

| 任务 | 结论 | 核心证据 |
|---|---|---|
| `SAL-P1-001` | DONE | ADR-001/ADR-002 批准，上游候选 commit 处理已登记 |
| `SAL-P1-002` | DONE | 根 `pyproject.toml`、PEP 621 元数据、console wrappers 和安装入口验证 |
| `SAL-P1-003` | DONE | `core/providers/desktop/quant/dev` extras、`uv.lock`、`requirements.txt` 和 drift guard |
| `SAL-P1-004` | DONE | 目标包骨架和架构边界测试 |
| `SAL-P1-005` | DONE | `InstrumentId`、Provider symbol mapping 和旧 symbol 兼容 |
| `SAL-P1-006` | DONE | `Run` / `Stage` / `RunEvent` 生命周期与状态转换 |
| `SAL-P1-007` | DONE | Artifact manifest、内容寻址本地存储和原子发布 |
| `SAL-P1-008` | DONE | `TaskBackend` Protocol、InMemory backend 和 DSA queue facade |
| `SAL-P1-009` | DONE | `ResearchOrchestrator` Protocol 和 DSA Agent facade |
| `SAL-P1-010` | DONE | `application/problem+json`、稳定错误码和脱敏中间件 |
| `SAL-P1-011` | DONE | `TraceContext`、结构化 JSON 日志、脱敏和 ASGI middleware |
| `SAL-P1-012` | DONE | Alembic baseline revision、空库升级和启动前 preflight |
| `SAL-P1-013` | DONE | SQLite fixture backup/stamp/hash verify/restore rehearsal |
| `SAL-P1-014` | DONE | runtime profiles、CI 真实 key/网络拒绝和脱敏诊断 |
| `SAL-P1-015` | DONE | Desktop/API/CLI/Bot/契约金标离线兼容矩阵和性能基线 |
| `SAL-P1-016` | DONE | 本 Gate G1 评审记录和 P2 入口约束 |

## 4. 接受风险与后续约束

| 风险/限制 | Gate G1 处理 | 后续关闭条件 |
|---|---|---|
| Web npm audit 仍有 high 漏洞 | 接受但继续阻断发布。P1 未改写上游 Web lockfile | `SAL-P6-005` 或受控前端依赖升级修复/豁免 |
| Docker image Critical/High 漏洞 | 接受但继续阻断发布。P1 未重建发布镜像 | `SAL-P6-005` 修复 base image/runtime packages 或完成正式豁免 |
| Web registry resolved URL 混用 | 接受。P1 仅治理 Serenity root Python lock | 发布前依赖治理统一 registry 策略 |
| 上游 `487e49e5` DecisionSignal persistence 候选 | 不吸收到当前 G1 基线 | 通过 `sync/dsa-487e49e5` 分支评审、刷新相关基线后决定 |
| Desktop GUI/签名/安装升级未做发布级验收 | 不阻断 P2。P1 只批准离线兼容与性能基线 | 发布/RC 阶段补充平台矩阵、签名、安装升级和人工验收 |

## 5. 本地评审验证

| 验证 | 结果 |
|---|---|
| `bash scripts/bootstrap-dsa-baseline.sh --validate-only` | PASS：baseline tag 与隔离 worktree 均为 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| `scripts/apply-dsa-baseline-patches.sh --check-only` | PASS：`DSA-PATCH-001..003` 均已应用 |
| `.cache/dsa-p0/venv/bin/python -m pytest tests/architecture tests/domain tests/application tests/repositories tests/integrations -q` | PASS：`103 passed` |
| `.cache/dsa-p0/venv/bin/python -m pytest -q` | PASS：`103 passed` |
| `scripts/verify-python-dependency-lock.sh` | PASS：`uv.lock` 与 `requirements.txt` 无 drift |
| `scripts/run-p1-desktop-compatibility-performance.sh --python /Users/zq/.local/bin/python3.11` | PASS：Desktop/API/CLI/Bot/契约金标离线矩阵通过 |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

## 6. P2 入口约束

P2 第一入口为 `SAL-P2-001` Provider 领域契约。P2 实现必须沿用 P1 已冻结的工程地基：

- Provider、Dataset、Persistent TaskBackend 和 Worker 不得直接绕过 `RuntimeProfile`、`ProblemDetail`、`TraceContext`、`ArtifactStore`、`Run/Stage/Event` 和 Alembic preflight。
- CI profile 默认保持离线和无真实 key；真实 Provider/LLM 调用只能在明确授权的后续任务或人工环境中执行。
- P2 可以开始 PIT Dataset 相关任务，但每个 Dataset/Provider 任务必须显式记录 `available_at <= decision_time`、数据版本、来源和质量门禁。
- P2 仍不启动 Quant Core 或正式组合回测；这些属于 P4，除非清单和 Gate 明确变更。

## 7. 最终判定

`SAL-P1-016` 判定为 `DONE`。Gate G1 通过后，P1 工程加固完成度为 `16/16`，项目进入 P2 数据版本、Provider 收口与持久任务阶段。下一步唯一推荐入口是 `SAL-P2-001`。
