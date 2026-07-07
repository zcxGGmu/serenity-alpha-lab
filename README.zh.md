<p align="center">
  <strong>Serenity Alpha Lab</strong><br />
  <sub>本地证据。双语研究。持久工作流。</sub>
</p>

<h1 align="center">Serenity Alpha Lab</h1>

<p align="center">
  <strong>把杂乱的市场问题转化为可审计的研究工作流。</strong><br />
  一个 local-first 的 Serenity 风格投资研究实验室，用于股票、行业、赛道、主题分析。
</p>

<p align="center">
  <a href="pyproject.toml"><img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="Makefile"><img alt="Verification" src="https://img.shields.io/badge/verify-make%20verify-2ea44f?style=flat-square"></a>
  <a href="INSTALL.md"><img alt="Local first" src="https://img.shields.io/badge/local--first-research%20engine-6f42c1?style=flat-square"></a>
  <a href="docs/RELEASE_CHECKLIST.md"><img alt="Research only" src="https://img.shields.io/badge/boundary-research%20only-ff4d4f?style=flat-square"></a>
</p>

<p align="center">
  <code>证据 -> 评分卡 -> 仪表盘 -> 补证任务 -> 复跑 -> 交接</code>
</p>

<p align="center">
  <a href="README.md">English README</a>
</p>

> Serenity Alpha Lab 是本地研究系统，不是投资顾问。它不会生成买入/卖出/持有指令、目标价或仓位建议。所有输出都是研究材料，在任何资本决策前都必须独立核验。

## 近期亮点

**筛选后项目交接** — 保存项目库现在可以只复制当前筛选和排序后的项目队列，支持交接前预览，并把复制动作写入项目 review event log。

**协作型项目库** — 项目卡片和详情抽屉展示负责人、活动筛选、最新活动摘要、事件类型筛选、下一步队列、证据进度、最新证据影响和持久审计轨迹。

**后台分析任务** — 分析请求可以通过 `/api/analyze-jobs` 提交，立即返回持久任务元数据，并让 Run Center 轮询 queued、running、completed、failed、cancelled、retry 等状态。

**补证闭环** — 预检证据缺口会变成可执行任务，包含可复制搜索提示、报告内导入跳转、任务状态持久化、质量 delta 摘要和复跑上下文。

## 架构图

以下图表使用 `fireworks-tech-graph` 的 Claude Official style 6：暖色背景、圆角高对比节点、柔和蓝色来源节点、青绿色处理节点、米色基础设施节点、灰色持久状态节点。

### 系统架构

<p align="center">
  <img src="docs/assets/diagrams/serenity-system-architecture.png" alt="Serenity Alpha Lab 系统架构图" width="100%" />
</p>

系统刻意保持 local-first。JSONL 证据、配置目录和导入器输出进入 Python 研究引擎；CLI 编排 memo pack 与 UI 构建；本地 dashboard server 暴露 runs、projects、events、task statuses、evidence audits 等工作流 API。

### 研究生成流程

<p align="center">
  <img src="docs/assets/diagrams/serenity-research-flow.png" alt="Serenity Alpha Lab 研究生成流程图" width="100%" />
</p>

一个查询会被解析为 canonical theme 和候选 ticker，再与本地证据匹配排序，通过 Serenity scorecard 评分，由 readiness gate 检查质量，最后发布为双语 dashboard、memo pack、operational reports 和持久 run records。

### 证据闭环框架

<p align="center">
  <img src="docs/assets/diagrams/serenity-evidence-closure-framework.png" alt="Serenity Alpha Lab 证据闭环框架图" width="100%" />
</p>

证据缺口会转化为具体任务、导入跳转、任务状态记录、审计条目、质量 delta 摘要、复跑上下文、下一步队列，以及筛选后的 research-only 交接 brief。

SVG 源文件与 PNG 资源放在同一目录：

- [`serenity-system-architecture.svg`](docs/assets/diagrams/serenity-system-architecture.svg)
- [`serenity-research-flow.svg`](docs/assets/diagrams/serenity-research-flow.svg)
- [`serenity-evidence-closure-framework.svg`](docs/assets/diagrams/serenity-evidence-closure-framework.svg)

## Serenity Alpha Lab 是什么？

Serenity Alpha Lab 是一个 local-first 研究引擎，用于把行业、赛道、主题或 ticker 问题转化为可追踪的投资研究工作区。

它组合了：

- 证据支持的 claim storage
- fact、methodology、inference、risk、catalyst、invalidation 等 claim-type 分类
- 确定性检索和透明的 Serenity 风格评分
- skeptic review 和 invalidation 检查
- 在证据存在时提供 source-backed 本地财务上下文
- 中文和英文 dashboard/report 生成
- 带工作流状态、审计历史和交接材料的 saved-project library
- Markdown memo 生成与 drawer-based report reading

默认 CPO pack 使用本地证据、SEC companyfacts 快照、官方报告摘录和受保护的人工导入证据，评估 `AAOI`、`LITE`、`COHR`、`AXTI`、`SIVE`、`NVDA`。

```text
输入查询
  -> topic resolver
  -> evidence-backed candidates
  -> Serenity scorecard
  -> bilingual dashboard
  -> evidence acquisition queue
  -> project library / handoff
```

## 安装

从全新本地 checkout 开始，使用 Python 3.9 或更高版本：

```bash
python3 -m pip install -e .
make smoke
make verify
```

源码树 fallback：

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack --allow-skipped
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both
```

干净机器验证路径见 [`INSTALL.md`](INSTALL.md)。

## 快速开始

构建默认产品输出：

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack --allow-skipped
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-financial-metrics \
  --data data/enriched/github_plus_primary.jsonl data/primary/sive_official_report_evidence.jsonl \
  --out config/financial_metrics.json
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both
```

启动本地产品服务器：

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli serve-ui \
  --host 127.0.0.1 \
  --port 8767 \
  --language both
```

打开：

- 中文 UI：`http://127.0.0.1:8767/index.zh.html`
- 英文 UI：`http://127.0.0.1:8767/index.html`

使用 `启动分析` / `Start analysis` 创建新的本地行业、赛道、主题或 ticker 报告，例如 `存储芯片`、`HBM`、`半导体设备`、`AAOI`。页面搜索框只过滤当前 dashboard，不会启动新分析。

## 稳定产品运行

发布 gate：

```bash
make verify
```

它会运行：

- `python3 -m pytest tests -q`
- `PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor`
- `PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack`
- `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-coverage-matrix ...`

完整用户界面还应重新生成 metrics 和双语 UI：

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-financial-metrics \
  --data data/enriched/github_plus_primary.jsonl data/primary/sive_official_report_evidence.jsonl \
  --out config/financial_metrics.json

PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both
```

交接前扫描生成报告中的产品侧投资建议风险：

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli scan-report-safety \
  --reports output/packs/cpo-guarded/*-memo.md \
  --out output/reports/report-safety-scan.md
```

扫描器会区分产品正文和引用的外部证据摘录，所以外部证据中的投资动作词不会被误判为 Serenity Alpha Lab 自己生成的指引。

## 产品表面

| 表面 | 作用 |
| --- | --- |
| 双语 dashboard | 渲染中英文研究页面，包含候选对比、来源覆盖、风险预览和报告抽屉。 |
| Run Center | 持久化 queued、running、completed、failed、cancelled、retry 等分析生命周期状态。 |
| 项目库 | 将生成分析保存为可复用项目记录，包含质量快照、下一步、负责人和状态筛选。 |
| 证据任务 | 把 primary、risk、demand、invalidation、crowding 等缺口转为可执行采集任务。 |
| 审计日志 | 记录项目事件、证据验证、质量 delta 摘要、负责人变化和队列交接复制。 |
| 交接包 | 复制 research-only 项目队列、deliverable links、manifest、coverage matrix 和 evidence queue。 |

## 工作流表面

Serenity Alpha Lab 保持用户工作流显式可见：

| 步骤 | 用户动作 | 持久输出 |
| --- | --- | --- |
| Resolve | 输入行业、主题、赛道或 ticker。 | Canonical theme、候选 ticker、覆盖元数据。 |
| Generate | 通过本地 UI 或 CLI 启动分析。 | 双语 dashboard、memo pack、run record、analysis manifest。 |
| Compare | 先查看候选对比表。 | 评分、rating、confidence、key gaps、evidence coverage、financial context。 |
| Investigate | 打开报告抽屉和 operational reports。 | Deliverable research report、coverage matrix、evidence acquisition queue。 |
| Close gaps | 收集证据、导入证据、标记任务 verified。 | Task statuses、audit entries、quality-before/after context、rerun links。 |
| Handoff | 筛选项目队列并复制 research-only handoff brief。 | Review-event trace 和可分享工作流上下文。 |

## 生成输出

产品 pipeline 会重新生成：

- `data/enriched/github_plus_primary.jsonl`
- `output/reports/cpo-readiness-guarded.md`
- `output/packs/cpo-guarded/index.md`
- `output/packs/cpo-guarded/sources.md`
- `output/packs/cpo-guarded/` 下每个 ready ticker 的 memo
- `config/financial_metrics.json`
- `output/reports/universe-coverage-matrix.md`
- `output/ui/index.html`
- `output/ui/index.zh.html`
- `output/ui/analyses/<slug>/` 下的生成分析页面

每次 UI 启动的分析都会在 `output/ui/analyses/<slug>/reports/` 写入 query-specific operational reports：

- `universe-coverage-matrix.md`
- `evidence-acquisition-queue.md`
- `deliverable-research-report.md`

如果从中文 UI 启动分析，operational report 正文也会中文化，而不只是按钮中文化。

## 用户流程

中文用户：

1. 启动服务器并打开 `http://127.0.0.1:8767/index.zh.html`。
2. 在 `启动分析` 中输入行业、赛道、主题或 ticker，例如 `存储芯片` 或 `HBM`。
3. 等待生成 `output/ui/analyses/<slug>/` 下的分析页。
4. 先读 `候选对比`，按 Serenity score、rating、confidence、key gaps、evidence coverage 和 financial context 对比 ticker。
5. 用 `查看报告` 打开右侧报告抽屉。
6. 在信任或提升候选前查看 `证据补齐行动清单`。
7. 从生成分析页打开 `覆盖矩阵` 和 `证据采集队列`。
8. 使用 `最近报告` 和 saved-project library 重新打开、筛选、对比、交接分析。

英文用户使用 `http://127.0.0.1:8767/index.html` 走同样流程。

## 导入 Serenity GitHub 项目

GitHub importer 读取 curated repo manifest，抓取公开 markdown 文件，抽取 Serenity 风格供应链 claims，并写成可审计 evidence JSONL：

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli import-github \
  --repos imports/github_repos.json \
  --out data/imported/github_evidence.jsonl
```

然后基于 curated seed evidence 和 imported GitHub evidence 生成 memo：

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli \
  --data data/seed/evidence.jsonl data/imported/github_evidence.jsonl \
  --query "CPO laser bottleneck" \
  --ticker SIVE \
  --out output/memos/sive-cpo-enriched.md
```

Imported evidence 仍然是第三方研究上下文。在没有 primary filings、transcripts、customer disclosures 或 archived posts 独立确认前，应视为 derived 或 speculative。

## 报告结构

生成 memo 包含：

- research question
- scorecard
- Serenity rating、confidence tier、key evidence gaps
- 按供应链层级组织的 industry structure map
- 来自 dated fact/catalyst evidence 的 catalyst timeline
- 带下一步证据动作的 evidence gap priority table
- claim-type mix
- thesis summary
- supporting evidence
- skeptic review
- invalidation conditions
- evidence action plan
- next research tasks
- research-only disclaimer

中文生成报告还包含 `投资分析结论`、`Serenity 选股因子`、`关键跟踪指标` 和 `证据补齐行动清单`。

## 开发

编辑时运行 focused checks：

```bash
python3 -m pytest tests -q
python3 -m pytest tests/test_ui_http_e2e.py -q
```

修改 dashboard、launcher、report drawer 或本地服务器行为后，运行 HTTP 级 UI smoke：

```bash
PYTHONPATH=src python3 -m pytest tests/test_ui_http_e2e.py -q
```

该 smoke 会启动本地临时 HTTP server，打开中文首页，调用 `/analyze?query=存储芯片&language=zh`，跟随生成分析页，并验证报告抽屉使用的中文 memo 文件。

有用的发布与交接文档：

- [`INSTALL.md`](INSTALL.md)
- [`CHANGELOG.md`](CHANGELOG.md)
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md)

## 配置说明

可选 CPO pack 输出覆盖：

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack \
  --combined-out data/enriched/github_plus_primary.jsonl \
  --readiness-out output/reports/cpo-readiness-guarded.md \
  --pack-out-dir output/packs/cpo-guarded
```

可选 dashboard 输出覆盖：

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui \
  --readiness output/reports/cpo-readiness-guarded.md \
  --pack-dir output/packs/cpo-guarded \
  --out output/ui/index.html \
  --language both
```

可选 financial metrics 输出覆盖：

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-financial-metrics \
  --data data/enriched/github_plus_primary.jsonl data/primary/sive_official_report_evidence.jsonl \
  --out config/financial_metrics.json
```

## 灵感与 lineage

Serenity Alpha Lab 借鉴了聚焦型工具项目的 README 节奏：居中 identity、简洁 promise、current highlights、workflow tables、明确 verification gates。产品本身保持锚定在本地证据、双语研究工作流和透明 research-only 边界上。

## License

分发前请查看仓库 license。如果当前 checkout 中没有 license 文件，则在补充 license 前应视为未授权再分发。
