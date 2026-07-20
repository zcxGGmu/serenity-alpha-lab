# Desktop 兼容和性能基线记录

> 任务：`SAL-P1-015` 验证 Desktop 兼容和性能基线<br>
> 日期：2026-07-20<br>
> Phase：P1 工程加固<br>
> Gate：G1 未通过<br>
> 范围：在当前 P1 lock、兼容 facade、配置 profile 和 Alembic/SQLite 升级基础上，复跑锁定 DSA `v3.26.1` 的 Desktop/API/CLI/Bot/契约金标离线主路径，并记录 Desktop 后端 health 启动与离线单股报告生成性能。

## 1. 结论

`SAL-P1-015` 通过。新增 `scripts/run-p1-desktop-compatibility-performance.sh` 作为可复跑入口；脚本只使用隔离 DSA worktree 和 `.cache/dsa-p0` 产物，不移动 `upstream/dsa-v3.26.1`，不提交 DSA runtime source、缓存、Desktop 构建产物、SQLite 运行库或 Playwright/Node 产物。

本次最新复跑结果为 `PASS`，摘要写入 `.cache/dsa-p0/p1-desktop-compatibility-performance/summary.md` / `summary.json`。缓存摘要不提交；本文件记录可审计结果。

## 2. 验证矩阵

| 验证 | 结果 | 耗时 |
|---|---:|---:|
| bootstrap DSA Python + CI tools + Desktop deps | PASS | 7,694ms |
| apply registered DSA patches | PASS | 98ms |
| Desktop `npm test` | PASS：47 passed / 0 failed | 3,513ms |
| Desktop packaging + API health + CLI + Bot pytest | PASS：121 passed / 7 warnings | 16,258ms |
| API/config contract baseline | PASS：`openapi.json`、`config-schema.json`、`config-env-inventory.json`、`summary.json` matched | 13,371ms |
| Database baseline | PASS：database snapshots matched | 1,326ms |
| Report/signal golden baseline | PASS：report/signal snapshots matched | 5,465ms |

`desktop_api_cli_bot_pytest` 覆盖：

- `tests/test_desktop_packaging_assets.py`
- `tests/test_desktop_installer_config.py`
- `tests/test_api_health.py`
- `tests/test_local_cli_backend.py`
- `tests/test_bot_status_command.py`
- `tests/test_bot_dispatcher_async.py`
- `tests/test_bot_market_command.py`

## 3. 性能口径

| 指标 | 结果 | 阈值 | 结论 |
|---|---:|---:|---|
| Desktop 后端 health 启动 | 5,822ms / 19 probes | 60,000ms | PASS |
| Report/signal golden 全脚本墙钟 | 5,465ms | 60,000ms | PASS |
| 离线单股报告生成均值 | 0.030ms，20 iterations，max 0.052ms | 5,000ms | PASS |

性能阈值是 P1 首次工程基线，不是容量优化目标。后续如果进入正式 Desktop RC、Web E2E 或发布性能门禁，应建立独立平台矩阵和硬件规格。

## 4. 防外部调用边界

- Desktop 后端启动使用 `main.py --serve-only --host 127.0.0.1 --port <ephemeral>`，只轮询 `/api/health`。
- 启动测量显式设置 `DSA_DESKTOP_MODE=true`、`WEBUI_ENABLED=false`、`WEBUI_AUTO_BUILD=false`、`BOT_ENABLED=false`、`DSA_RUNTIME_SCHEDULER_SUPPRESS_START=true` 和 `DSA_RUNTIME_SCHEDULER_RUN_IMMEDIATELY=false`。
- 单股报告性能使用已提交 P0 `structured-reports.json` 中的 Stub `AnalysisResult`，本地调用 `NotificationService.generate_single_stock_report()`；不调用真实 Provider、真实 LLM、真实通知或真实 Bot 平台。
- Report/signal baseline 继续使用 P0 Stub LLM、固定时钟和合成行情输入；日志确认未配置有效通知渠道，不发送推送。

## 5. 范围限制

- 不执行真实 GUI 人工验收、Desktop 打包/签名、安装升级或平台分发测试。
- 不重跑 Web Playwright smoke、Docker build、SBOM/漏洞扫描或完整后端 `backend-offline` 重量级 gate；这些仍由 P0 required baseline jobs / G1 评审按需调用。
- 不刷新 OpenAPI、database、report/signal committed snapshots；本次均为 matched。
- 不迁移 DSA runtime source，不改写 Web/desktop lockfile，不启动 Quant Core、PIT Dataset、正式回测、Provider/LLM 调用或大规模 DSA 源码迁移。

## 6. 验证命令

| 命令 | 结果 |
|---|---|
| `bash -n scripts/run-p1-desktop-compatibility-performance.sh` | PASS |
| `scripts/run-p1-desktop-compatibility-performance.sh --python /Users/zq/.local/bin/python3.11` | PASS |

## 7. 后续衔接

- `SAL-P1-016` Gate G1 可把本记录与 ADR-001/002、dependency lock、Run/Artifact/TaskBackend、ResearchOrchestrator、API errors、Trace、Config profile、Alembic 和 SQLite upgrade evidence 一起作为进入 P2 的工程地基证据。
- P2 开始后，数据/Provider/持久任务仍必须沿用 P1 已建立的 profile、migration、trace、error、artifact 和 facade 边界。
