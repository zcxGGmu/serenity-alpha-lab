# DSA 上游基线选择记录

> 任务：`SAL-P0-001` 锁定候选上游基线
> 评估日期：2026-07-19
> 上游仓库：`ZhuLinsen/daily_stock_analysis`
> 评估对象：最新稳定 release `v3.26.1` 与候选 `main@487e49e565ffd1b96a7cf4d855f99cee3c981eaa`

## 1. 最终结论

锁定 `ZhuLinsen/daily_stock_analysis v3.26.1` 作为 Serenity Alpha Lab 的唯一上游接管基线。

- Release：`v3.26.1`
- 上游 commit：`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`
- 发布时间：2026-07-12T10:57:39Z
- 上游 tag 类型：lightweight tag，直接指向 commit `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`
- 选择理由：该版本有正式 release、Desktop Release、Docker Release Publish 与 Create GitHub Release 成功记录；依赖与工作流边界明确，适合作为不可漂移的 P0 接管基线。
- 放弃候选 `main` 理由：`main@487e49e565ffd1b96a7cf4d855f99cee3c981eaa` 比 release 多 2 个 commit、19 个文件变更，核心集中在 DecisionSignal 重评估持久化，属于未发布的 API/Web/服务语义扩展，不适合作为初始稳定接管点。

未经 Gate G0 或后续 ADR 批准，P0 不再漂移到其他 DSA commit。`main@487e49e565ffd1b96a7cf4d855f99cee3c981eaa` 仅登记为后续同步候选。

## 2. 候选对比

| 项目 | `v3.26.1` | 候选 `main` |
|---|---|---|
| SHA | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` | `487e49e565ffd1b96a7cf4d855f99cee3c981eaa` |
| 日期 | 2026-07-12T10:56:21Z commit；2026-07-12T10:57:39Z release | 2026-07-16T11:22:14Z commit |
| 版本状态 | 正式 release | 未发布 main HEAD |
| 与 `v3.26.1` 差异 | 基线 | ahead 2 commits，behind 0 |
| 文件差异 | 基线 | 19 个文件，2,283 行变更（+2,171 / -112） |
| 依赖/工作流 | `requirements.txt`、`pyproject.toml`、`apps/dsa-web/package*.json` 与 workflow 固定 | 与 `v3.26.1` 相同 |
| 测试/文档资产规模 | 990 files；510 Python；232 Python test files；93 Web test files；10 workflows | 同左 |
| 发布证据 | Create Release、Desktop Release、Docker Release Publish 成功 | 无对应 release 产物；只有 push/schedule 类动作 |
| 接管风险 | 已知 release 级稳定点，可复现性后续在 SAL-P0-003..011 继续验证 | API/OpenAPI/Web 行为变更较大，需作为同步候选而非接管原点 |

## 3. `main` 相对 release 的增量

### 3.1 新增 commit

| SHA | 日期 | 摘要 | 评估 |
|---|---|---|---|
| `55946536a9765b3d4e2620edef6a50e79d0928d0` | 2026-07-13T13:54:34Z | `fix(issue-1996): [bug] (#1998)` | 仅文档/Changelog，解释 macOS Gatekeeper 对未签名未公证 DMG 的拦截；不影响初始源码基线，但应纳入后续文档同步。 |
| `487e49e565ffd1b96a7cf4d855f99cee3c981eaa` | 2026-07-16T11:22:14Z | `feat: 支持保存决策风格重评估结果 (#2014)` | 扩展 DecisionSignal reassess `persist=true`，涉及 API、Schema、服务、Web、OpenAPI 与大量测试；价值较高但未发布，应后续单独同步评审。 |

### 3.2 变更范围

| 顶层路径 | 文件数 | 变更行数 | 说明 |
|---|---:|---:|---|
| `api` | 2 | 49 | DecisionSignal reassess endpoint/schema 返回结构变化。 |
| `src` | 3 | 292 | DecisionSignal service、reassess service 与 profile policy 调整。 |
| `apps` | 6 | 819 | Web API/types/i18n/page 与 Vitest 覆盖新增 persist/blocked/existing/refreshed 场景。 |
| `tests` | 4 | 670 | 后端 API/schema/profile/docs 测试新增。 |
| `docs` | 4 | 453 | OpenAPI snapshot、DecisionSignal 文档、桌面安装文档和 Changelog 更新。 |

未发现 `requirements.txt`、`pyproject.toml`、`apps/dsa-web/package.json`、`apps/dsa-web/package-lock.json` 或 `.github/workflows` 在两个候选之间发生变化。

## 4. 验证结果

本任务只锁定上游 commit，不导入 DSA 源码，不替代 SAL-P0-003..011 的真实构建、测试、SBOM 和运行基线。

已执行的验证：

| 验证 | 结果 |
|---|---|
| `git status --short --branch` | 本地仓库开始时为 `## main`，无未提交改动。 |
| `git log -2 --oneline` | 最近提交为 `e64a255 docs(状态): 初始化可恢复的开发状态快照`、`9088456 docs(规划): 建立 DSA 主干研发方案与阶段执行清单`。 |
| `git ls-remote --heads --tags https://github.com/ZhuLinsen/daily_stock_analysis.git` | 确认 `refs/tags/v3.26.1` 指向 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`，`refs/heads/main` 指向 `487e49e565ffd1b96a7cf4d855f99cee3c981eaa`。 |
| GitHub release API | 确认 `v3.26.1` 发布时间、target commit 与 release notes。 |
| GitHub compare API | 确认 `v3.26.1...main` 为 ahead 2 commits、behind 0、19 个文件变更。 |
| GitHub contents/tree API | 确认依赖文件、lock 文件、workflow 数量和测试文件数量在两个候选间未变化。 |
| GitHub Actions metadata | `v3.26.1` 的 Create Release、Desktop Release、Docker Release Publish 成功；Network Smoke 成功。`main@487e49e` 的 scheduled analyze 与 Network Smoke 成功，但无 release 产物。 |

## 5. 已知风险

| 风险 | 影响 | 处理 |
|---|---|---|
| `v3.26.1` 之后已合入 macOS Gatekeeper 文档修复。 | release 文档可能让用户误以为 DMG 一定损坏。 | 记录为后续同步候选；P0 接管不因此漂移到 main。 |
| `main@487e49e` 已新增 DecisionSignal reassess persist 语义。 | 后续若基于 DecisionSignal 做 Evidence/报告能力，可能需要吸收该 API 契约。 | SAL-P0-002 后建立 upstream patch/sync backlog，先以 `v3.26.1` 建立行为基线，再评估是否 cherry-pick 或等待下一 release。 |
| 上游 scheduled daily analysis 在 `v3.26.1` 后有一次 cancelled 记录。 | 说明 schedule 任务不能作为 Gate G0 唯一稳定性证据。 | P0 后续必须执行本地/CI 后端、Web、Desktop、Docker、供应链全量基线验证。 |
| 本任务未运行 DSA 源码测试。 | 不能证明目标 Windows/Linux/Docker 环境可复现。 | 由 SAL-P0-003..011 分别完成环境、测试、构建、Schema、报告金标与 SBOM 验证。 |

## 6. 后续动作

1. SAL-P0-002 导入 DSA Git 历史时，创建不可变本地基线标签，例如 `upstream/dsa-v3.26.1`，指向 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。
2. 配置 `upstream` remote 指向 `https://github.com/ZhuLinsen/daily_stock_analysis.git`。
3. 建立后续同步候选登记：`55946536` 文档修复、`487e49e` DecisionSignal reassess persist。
4. Gate G0 前不得以 `main` HEAD 或未发布 commit 替代本基线。
