# DSA Desktop、CLI 与 Bot Smoke 基线记录

> 任务：`SAL-P0-006` 建立 Desktop、CLI 与 Bot Smoke 基线<br>
> 执行日期：2026-07-19<br>
> 上游基线：`upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 当前状态：`DONE`

## 1. 执行结论

本次已在隔离 DSA worktree 中固定 Desktop、CLI 和 Bot 的自动化 smoke 主路径，并完成离线/Stub 安全验证。`SAL-P0-006` 可标记为 `DONE`。

本记录只证明 DSA `v3.26.1` 的 Desktop、CLI、本地 API 健康检查和 Bot 命令层 smoke 可运行；不替代 `SAL-P0-004` 后端全量离线测试、`SAL-P0-005` Web Playwright 真实 smoke、`SAL-P0-007` Docker 基线或 `SAL-P0-011` 完整 SBOM。

收尾复验：2026-07-19 再次执行 Desktop `npm test`，47/47 通过；再次执行 Desktop packaging、API health、CLI local backend、Bot status/dispatcher 和 Bot market command 组合 pytest，121/121 通过，保留 7 个 warning。

## 2. 环境与基线

| 项目 | 结果 |
|---|---|
| Serenity branch | `codex/p0-baseline-status` |
| DSA worktree | `.worktrees/dsa-v3.26.1` |
| DSA HEAD | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Python for smoke | `.cache/dsa-p0/venv/bin/python` -> Python `3.11.15` |
| Node | `v25.9.0` |
| npm | `11.12.1` |
| Desktop package | `apps/dsa-desktop/package-lock.json` |
| Dependency cache | `.cache/dsa-p0` |

说明：本机最先检测到的 `python3` 是 `3.9.9`，不符合 DSA 后端基线要求；本次通过 `/Users/zq/.local/bin/python3.11` 建立 `.cache/dsa-p0/venv` 后执行 Python smoke。

## 3. Desktop Smoke

### 3.1 入口

DSA Desktop 位于 `apps/dsa-desktop`，`package.json` 定义以下入口：

| Script | 命令 | 用途 |
|---|---|---|
| `dev` | `electron .` | 本地 Electron 启动 |
| `build` | `electron-builder` | 桌面安装包构建 |
| `test` | `node --test tests/*.test.js` | Headless Desktop 主进程/bridge 测试 |

Desktop 主进程在启动路径中负责选择端口、准备 `.env`、启动后端、轮询 `/api/health` 并加载 `http://127.0.0.1:<port>/?desktop_version=...`。

### 3.2 执行结果

| 命令 | 结果 | 说明 |
|---|---|---|
| `bash scripts/bootstrap-dsa-baseline.sh --install-desktop` | 通过 | `npm ci` 安装 332 个 packages，audit 333 个 packages |
| `npm test`（在 `.worktrees/dsa-v3.26.1/apps/dsa-desktop`） | 通过 | 47 个 Node tests 全部通过 |
| `python -m pytest tests/test_desktop_packaging_assets.py tests/test_desktop_installer_config.py -q` | 通过 | 6 个 Desktop packaging/installer 测试通过 |
| `python -m pytest tests/test_api_health.py -q` | 通过 | 7 个本地 API health 契约测试通过 |

Desktop `npm ci` audit 摘要为 9 个漏洞：1 个 moderate、8 个 high。本任务不运行 `npm audit fix`，避免改写上游 lockfile；后续由供应链任务和发布门禁处理。

## 4. CLI Smoke

### 4.1 入口

DSA 的 CLI smoke 采用本地生成后端 `src.llm.local_cli_backend.LocalCliGenerationBackend`，该路径支持 Codex CLI、Claude Code CLI 和 OpenCode CLI preset，并通过 mock CLI、Stub LLM 和受限执行环境验证本地 CLI 调用契约。

### 4.2 执行结果

| 命令 | 结果 | 说明 |
|---|---|---|
| `python3.11 -m pytest tests/test_local_cli_backend.py -q` | 初始失败 | 未安装 DSA Python 依赖时缺 `json_repair` |
| `bash scripts/bootstrap-dsa-baseline.sh --python /Users/zq/.local/bin/python3.11 --install-ci-tools` | 通过 | 创建 `.cache/dsa-p0/venv`，安装 CI 依赖；AlphaSift Git 依赖可在本机克隆并构建 wheel |
| `.cache/dsa-p0/venv/bin/python -m pytest tests/test_local_cli_backend.py -q` | 通过 | 77 个 CLI 后端测试通过，1 个 Starlette/httpx warning |

该 CLI smoke 使用 mock CLI 与 Stub，不调用真实 LLM、不需要密钥，也不产生外部费用。

## 5. Bot Smoke

### 5.1 入口

Bot 命令入口位于 `bot/commands` 和 `bot/dispatcher.py`。本次选择无需真实平台 webhook、真实密钥或真实 LLM 的离线命令路径：

- `/status`：通过 `bot.commands.status.StatusCommand` 汇总 LLM/通知配置状态。
- dispatcher async/sync：通过 `bot.dispatcher.CommandDispatcher` 验证命令分发、异步包装、webhook async handler 和 NL routing Stub。
- `/market`：通过 `bot.commands.market.MarketCommand` 验证交易日区域过滤、运行时构建调用和锁释放路径，依赖均 mock。

### 5.2 执行结果

| 命令 | 结果 | 说明 |
|---|---|---|
| `.cache/dsa-p0/venv/bin/python -m pytest tests/test_bot_status_command.py tests/test_bot_dispatcher_async.py -q` | 通过 | 25 个 Bot status/dispatcher 测试通过，6 个 warning |
| `.cache/dsa-p0/venv/bin/python -m pytest tests/test_bot_market_command.py -q` | 通过 | 6 个 Bot market command 测试通过，1 个 warning |

该 Bot smoke 使用离线 Stub/mocks，覆盖命令层返回路径，不连接飞书、钉钉、Telegram、Discord、Slack 或 AstrBot 的真实外部平台。

## 6. 仍不覆盖的范围

- 不证明后端全量 `backend-gate` 通过；该范围仍属于 `SAL-P0-004`。
- 不证明 Web Playwright 真实登录/分析/历史页面 smoke；该范围仍属于 `SAL-P0-005`。
- 不证明 Docker server/analyzer profile 可构建运行；该范围仍属于 `SAL-P0-007`。
- 不证明 Python SBOM、镜像 digest 或镜像 SBOM 完整；该范围仍属于 `SAL-P0-011`。
- 不执行真实 Bot 平台 webhook、真实 LLM 调用或真实通知发送；P0 smoke 只采用离线 Stub 和命令层测试。

## 7. 后续建议

- `SAL-P0-007` 前启动 Docker daemon 并重新执行 Docker profile 构建/健康检查。
- `SAL-P0-004` 可在本机利用已成功安装的 `.cache/dsa-p0/venv` 继续尝试后端离线测试，但需要单独记录，不应混入 `SAL-P0-006`。
- `SAL-P0-011` 应复用本次 AlphaSift wheel 构建证据补充 Python SBOM，但仍需 Docker daemon 解除镜像 SBOM 阻塞。
