# Gate G0 基线接管评审

> 任务：`SAL-P0-013` Gate G0：基线接管评审<br>
> 评审日期：2026-07-20<br>
> Phase：P0 上游接管与行为基线<br>
> 上游基线：`ZhuLinsen/daily_stock_analysis v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 评审结论：`GO with accepted risks`

## 1. Gate 结论

Gate G0 通过。Serenity Alpha Lab 正式采用 DSA `v3.26.1` 作为 P1 工程加固的接管基线，允许进入 `SAL-P1-001` 批准上游与模块化 ADR。

本结论只批准基于已冻结 P0 证据进入 P1，不批准以下事项：

- 不漂移到上游 `main` 或未发布 commit。
- 不把 DSA 源码整体合入当前项目工作树。
- 不启动 Quant Core、PIT 数据、正式回测或发布加固范围外工作。
- 不把供应链 Critical/High 风险解释为发布可接受。

后续任何基线升级、上游同步、兼容外壳边界、源码整合方式或架构拆分，都必须通过 `SAL-P1-001` 的 ADR 记录并重新跑相应基线。

## 2. 通过条件核对

| Gate 条件 | 结论 | 证据 |
|---|---|---|
| 上游版本唯一且不可变 | PASS | `upstream/dsa-v3.26.1` 锁定到 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`；见 [DSA 上游基线选择记录](./upstream-baseline-selection.md) 和 [Git 历史导入记录](./upstream-history-import.md) |
| 运行环境可复现 | PASS | Windows/Linux/CI/Docker/Desktop 环境矩阵、隔离 worktree 与缓存策略已记录；见 [DSA 基线运行环境记录](./dsa-baseline-environment.md) |
| 后端离线测试稳定 | PASS | `4455 passed, 4 deselected, 48 warnings, 416 subtests passed`；见 [后端离线测试基线记录](./backend-offline-test-baseline.md) |
| Web lint/test/build/smoke 稳定 | PASS | `npm ci`、lint、build、Vitest `965 passed, 2 skipped`、Playwright smoke `13 passed`；见 [Web 测试与构建基线记录](./web-baseline-test-build.md) |
| Desktop/CLI/Bot 主路径可运行 | PASS | Desktop `47/47`、packaging/API `13/13`、CLI `77/77`、Bot `31/31`；见 [Desktop、CLI 与 Bot Smoke 基线记录](./desktop-cli-bot-smoke-baseline.md) |
| Docker profile 可构建运行 | PASS | 镜像 digest `serenity-dsa-p0@sha256:7de0eca96fa8622e8b4b7292890f413e1a8fc52417f02c9c9a2829a364918076`，server health 与 analyzer import smoke 通过；见 [Docker 基线记录](./docker-baseline.md) |
| API 与配置契约已冻结 | PASS | OpenAPI `3.1.0`、105 paths、119 operations、186 schemas；配置 inventory 386 fields；见 [API 与配置契约基线记录](./api-config-contract-baseline.md) |
| 数据库 Schema 与 fixture 已冻结 | PASS | 28 tables、177 indexes、31 fixture rows，SQL restore/FK/content hash round-trip 全部通过；见 [数据库 Schema 与迁移样本基线记录](./database-schema-baseline.md) |
| 报告与信号评价金标已冻结 | PASS | 2 个结构化报告、3 个 Markdown 报告、6 个 Signal Evaluation cases，关键 validation 全部通过；见 [报告与信号评价金标基线记录](./report-signal-golden-baseline.md) |
| 供应链风险已基线化并定责 | PASS with accepted risks | Python/Web/Image SBOM、license 和 vulnerability baseline 已生成；Critical/High 不在 P0 修复，进入后续门禁；见 [供应链基线记录](./supply-chain-baseline.md) |
| 上游补丁和 CI required checks 已固化 | PASS | `DSA-PATCH-001..003` 均为 `compatible`，无 `divergence`；四个 P0 required check 候选已记录；见 [UPSTREAM_BASE](../UPSTREAM_BASE.md) 与 [补丁登记](./upstream-patches.md) |

## 3. 接受风险

| 风险 | Gate G0 处理 | 后续关闭条件 |
|---|---|---|
| `RSK-006`：锁定 release 后遗漏上游 main 高价值修复 | 接受。`55946536` 与 `487e49e` 继续作为同步候选，不改变 P0 初始基线。 | `SAL-P1-001` ADR 评审是否吸收，并通过新 sync 分支刷新基线。 |
| `RSK-008`：Python 依赖未正式锁定且含 AlphaSift Git 依赖 | 接受但阻断发布。P0 已记录缓存、SBOM、audit 和动态 Git 风险。 | `SAL-P1-003` 引入正式 lock、extras、离线缓存和 AlphaSift 审计路径。 |
| `RSK-010`：Web npm audit 有 10 个 high 漏洞 | 接受但阻断发布。P0 不运行 `npm audit fix` 改写上游 lockfile。 | 受控依赖升级、上游同步或 `SAL-P6-005` 发布安全门禁关闭/豁免。 |
| `RSK-011`：Web lockfile 混用 npmjs 与 npmmirror resolved URL | 接受。P0 原样冻结，不在基线 commit 中重写 lockfile。 | `SAL-P1-003` 或发布前依赖治理统一 registry 策略。 |
| `RSK-012`：Docker image Grype 有 39 critical / 84 high | 接受但阻断发布。P0 只完成镜像漏洞 baseline 和 owner 定责。 | `SAL-P6-005` 前修复 base image/runtime packages，或完成逐项正式豁免。 |

## 4. Phase 1 入口约束

`SAL-P1-001` 可以开始，但必须先把 P0 的结论转化为 ADR：

- ADR-001：上游接管、同步分支、tag 不可变策略和升级回滚。
- ADR-002：DSA 兼容外壳、模块化边界和后续删除旧路径条件。
- 任何吸收上游 `main` 候选 commit 的动作必须先建 `sync/dsa-*` 分支，不能直接移动 `upstream/dsa-v3.26.1`。
- P1 仍不得把 Signal Evaluation 视为正式组合回测；真实组合回测、PIT 数据、Ledger 和 Risk 属于 P4。

## 5. 本地评审验证

本次 G0 收尾使用轻量可复跑验证，不重新执行所有重量级 P0 套件；重量级套件的完整结果已经冻结在各 P0 evidence 记录中。

| 验证 | 预期 |
|---|---|
| `bash scripts/bootstrap-dsa-baseline.sh --validate-only` | 锁定 tag 与 worktree 仍有效 |
| `scripts/apply-dsa-baseline-patches.sh --check-only` | 登记补丁可识别且无未登记偏离 |
| `.github/workflows/p0-required-baselines.yml` YAML parse | CI workflow 结构可解析 |
| `jq` 摘要断言 | API/config、database、report/signal baseline 关键数量和 validation 布尔值符合 G0 记录 |
| `git diff --check` | 文档和脚本变更无 whitespace error |
| active 状态扫描 | `docs/development-status.md`、`docs/development-progress-checklist.md` 和 `UPSTREAM_BASE.md` 不再残留活跃的 `P0 12/13`、`12/129` 或 `G0 未通过` 状态 |

## 6. 最终判定

`SAL-P0-013` 判定为 `DONE`。Gate G0 通过后，P0 上游接管基线完成度为 `13/13`，项目总完成度为 `13/129`。下一步唯一推荐入口是 `SAL-P1-001`，先完成上游与模块化 ADR，再进入 P1 工程加固实现。
