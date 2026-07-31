# DSA Git 历史导入记录

> 任务：`SAL-P0-002` 导入 DSA Git 历史<br>
> 执行日期：2026-07-19<br>
> 上游仓库：`https://github.com/ZhuLinsen/daily_stock_analysis.git`<br>
> 锁定基线：`v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`

## 1. 执行结论

已在当前仓库导入 `ZhuLinsen/daily_stock_analysis` 的 Git 历史对象与上游引用，并创建 Serenity 本地基线标签：

- `upstream` remote：`https://github.com/ZhuLinsen/daily_stock_analysis.git`
- 上游 release tag：`v3.26.1 -> e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`
- Serenity 基线 tag：`upstream/dsa-v3.26.1 -> e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`
- 上游 `main` 候选：`upstream/main -> 487e49e565ffd1b96a7cf4d855f99cee3c981eaa`

本次导入未切换工作树、未合并 DSA 文件、未压平复制源码；当前项目文档保持在本项目 `main` 工作树中。

## 2. 执行命令

```powershell
git status --short --branch
git log -2 --oneline
git remote add upstream https://github.com/ZhuLinsen/daily_stock_analysis.git
git fetch upstream +refs/heads/*:refs/remotes/upstream/* +refs/tags/*:refs/tags/* --prune
git tag upstream/dsa-v3.26.1 e8a9ca7742e8cb2498c8f491dd76d239b3064e1a
```

说明：首次 `git fetch upstream --tags --prune` 因全量上游引用较多在 120 秒超时，未写入有效引用；随后使用显式 refspec 和更长超时时间完成导入。

## 3. 验收证据

| 验证 | 结果 |
|---|---|
| 初始 `git status --short --branch` | `## main`，无未提交改动 |
| 初始 `git log -2 --oneline` | `1ba4325 docs(状态): 更新恢复入口与下次提示词`；`3cb69a6 docs(P0): 锁定 DSA 上游基线` |
| `git remote -v` | `upstream` fetch/push 指向 `https://github.com/ZhuLinsen/daily_stock_analysis.git` |
| `git branch -r` | 已导入 357 个 `upstream/*` 远程跟踪分支 |
| `git tag -l` | 已导入上游 release tags，并新增本地基线 tag；当前 tag 数 138 |
| `git rev-parse v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| `git rev-parse upstream/main` | `487e49e565ffd1b96a7cf4d855f99cee3c981eaa` |
| `git cat-file -t e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` | `commit` |
| `git fsck --connectivity-only --no-dangling` | 通过，无输出 |
| 导入后 `git status --short --branch` | `## main`，文档更新前工作树仍干净 |

## 4. Remote 说明

本次会话开始时当前仓库未配置任何 remote；文档要求保留 `origin`（本项目）与 `upstream`（DSA）的双 remote 模式，但仓库内没有本项目托管 URL。为避免伪造项目远端，本次只新增已知且可验证的 `upstream` remote。

后续一旦本项目托管地址确定，应执行：

```powershell
git remote add origin <serenity-alpha-lab-repository-url>
git remote -v
```

该项作为开放风险登记，不影响 DSA 历史、基线 tag 和后续本地 P0 基线任务继续推进。

## 5. 基线标签约束

`upstream/dsa-v3.26.1` 是 Serenity 的本地不可变基线标签。后续不得移动、删除或复用该 tag；如需升级 DSA，应创建新的 `sync/dsa-<version>` 分支和新的 `upstream/dsa-v<version>` 标签，并重新登记验证证据。

## 6. 后续同步候选

- `55946536a9765b3d4e2620edef6a50e79d0928d0`：macOS Gatekeeper 文档修复。
- `487e49e565ffd1b96a7cf4d855f99cee3c981eaa`：DecisionSignal reassess persist 语义扩展。

上述 commit 仅作为后续同步候选；Gate G0 前不得用未发布 `main` 替代 `v3.26.1` 初始基线。
