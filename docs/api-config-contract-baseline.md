# DSA API 与配置契约基线记录

> 任务：`SAL-P0-008` 冻结 API 与配置契约<br>
> 执行日期：2026-07-19<br>
> 上游基线：`upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 当前状态：`DONE`

## 1. 执行结论

`SAL-P0-008` 已完成。当前已将锁定 DSA 基线的 FastAPI OpenAPI、Web 设置配置 Schema、环境变量/配置字段 inventory 冻结到可提交快照，并新增可复跑脚本用于 CI 检测非预期 API 或配置契约漂移。

本任务不启动真实 Provider、Scheduler、LLM、Bot 或 Web 服务；只创建 FastAPI app 对象并读取 DSA 配置 registry、`.env.example` 与 Python 代码中的环境变量引用。生成阶段使用空 `ENV_FILE`，并显式关闭 stock index 远程刷新与 runtime scheduler 立即运行语义，避免把本机 `.env`、密钥或网络状态纳入快照。

## 2. 快照产物

| Artifact | 内容 |
|---|---|
| `docs/baselines/dsa-v3.26.1/api-config/openapi.json` | FastAPI `create_app(...).openapi()` 规范化 JSON，105 个 paths、119 个 operations、186 个 component schemas、1 个 security scheme |
| `docs/baselines/dsa-v3.26.1/api-config/config-schema.json` | `src.core.config_registry.build_schema_response()` 输出，schema version `2026-06-29-claude-code-cli-backend`，8 个 category、179 个注册字段 |
| `docs/baselines/dsa-v3.26.1/api-config/config-env-inventory.json` | 环境变量与配置字段 inventory，覆盖 registry、`Config` dataclass、`.env.example`、代码中 `os.getenv/os.environ` 使用和动态字段模式 |
| `docs/baselines/dsa-v3.26.1/api-config/summary.json` | 关键数量与文件 SHA256 摘要 |

`summary.json` 当前摘要：

| 项目 | 值 |
|---|---:|
| OpenAPI version | `3.1.0` |
| API version | `1.0.0` |
| OpenAPI paths | 105 |
| OpenAPI operations | 119 |
| OpenAPI component schemas | 186 |
| Config registry fields | 179 |
| Config inventory fields | 386 |
| Secret-classified fields | 81 |
| Server-masked fields | 5 |
| Runtime mutable fields | 187 |
| Runtime hidden fields | 10 |
| Deprecated aliases | 4 |
| Dynamic patterns | 9 |

## 3. 字段分类口径

`config-env-inventory.json` 为每个字段记录以下契约信息：

| 分类 | 说明 |
|---|---|
| `config_schema` | DSA Web 设置页 registry 已注册字段，可由 UI schema 渲染 |
| `config_dataclass` | DSA `Config` dataclass 中存在的运行时配置字段 |
| `runtime_mutable` | 运行时配置字段或动态 pattern，可被 `.env` 或系统环境覆盖 |
| `runtime_hidden` | 已注册但被 Web 设置页隐藏的字段，如 `DATABASE_PATH`、SQLite 写入参数和代理字段 |
| `runtime_only` | 代码读取但未进入 Web 设置 registry 的字段 |
| `env_example` | `.env.example` 中出现的字段或示例字段 |
| `secret` | 密钥、token、password、webhook URL、HMAC secret、OAuth token cache 或可能携带凭据的 headers/template |
| `server_masked` | `SystemConfigService` 服务端读写时强制掩码的敏感字段 |
| `deprecated` | 兼容旧字段但已有替代项 |
| `compatibility_alias` | 兼容别名，当前仍参与运行时解析 |
| `dynamic_pattern` | 运行时动态展开字段，如 `LLM_<CHANNEL>_*`、`STOCK_GROUP_<N>`、`EMAIL_GROUP_<N>` |

当前已标记的废弃别名：

| Key | 替代项 |
|---|---|
| `OPENAI_VISION_MODEL` | `VISION_MODEL` |
| `AGENT_STRATEGY_DIR` | `AGENT_SKILL_DIR` |
| `AGENT_STRATEGY_AUTOWEIGHT` | `AGENT_SKILL_AUTOWEIGHT` |
| `AGENT_STRATEGY_ROUTING` | `AGENT_SKILL_ROUTING` |

兼容别名：

| Key | 说明 |
|---|---|
| `DISCORD_CHANNEL_ID` | `DISCORD_MAIN_CHANNEL_ID` 的兼容别名 |
| `RUN_IMMEDIATELY` | 旧启动标志，仍参与 scheduler 兼容逻辑 |

服务端强制掩码字段：

| Key |
|---|
| `ALPHASIFT_INSTALL_SPEC` |
| `LLM_HERMES_API_KEY` |
| `LLM_HERMES_API_KEYS` |
| `LLM_HERMES_EXTRA_HEADERS` |
| `LLM_USAGE_HMAC_SECRET` |

## 4. 复跑与 CI 用法

首次刷新快照或上游升级评审时：

```bash
scripts/run-dsa-api-config-baseline.sh --update-snapshots
```

CI/PR 默认检查：

```bash
scripts/run-dsa-api-config-baseline.sh
```

脚本执行步骤：

1. 校验本地 tag `upstream/dsa-v3.26.1` 指向 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。
2. 校验 `.worktrees/dsa-v3.26.1` HEAD 等于锁定 SHA。
3. 通过 `scripts/apply-dsa-baseline-patches.sh` 幂等应用 `DSA-PATCH-001` 至 `DSA-PATCH-003`。
4. 使用 `.cache/dsa-p0/venv` 和空 `.cache/dsa-p0/api-config-contract-artifacts/empty.env` 生成 OpenAPI/config 快照。
5. 与 `docs/baselines/dsa-v3.26.1/api-config/*.json` 做 byte-for-byte diff；若漂移，diff 写入 `.cache/dsa-p0/api-config-contract-artifacts/diff/`。

说明：锁定上游 worktree 中的 `docs/architecture/api_spec.json` 当前仅覆盖部分历史路径，已滞后于 `create_app().openapi()` 的运行时输出；因此 Serenity P0 以运行时 FastAPI 生成结果作为 API 契约冻结源。

## 5. 验证结果

| 命令 | 结果 |
|---|---|
| `bash -n scripts/run-dsa-api-config-baseline.sh` | 通过 |
| `scripts/run-dsa-api-config-baseline.sh --update-snapshots` | 通过；4 个 committed snapshot 与 freshly generated output 匹配 |
| `scripts/run-dsa-api-config-baseline.sh` | 通过；OpenAPI、config schema、config inventory、summary 均 `matched` |
| `jq` 摘要检查 | 确认 OpenAPI 105 paths / 119 operations / 186 schemas，配置 inventory 386 fields，secret 81，server_masked 5，deprecated 4 |
| `rg` 泄漏扫描 | 未发现本机绝对路径、`ENV_FILE` 临时路径或 smoke password；只存在上游文档示例占位值如 `sk-xxxx`、`your_*` |

## 6. 不做事项与限制

- 不把 `.cache/dsa-p0` 中的生成日志、diff、空 env 文件或 artifact 提交到仓库。
- 不把 `.worktrees/dsa-v3.26.1` 的源码复制进本项目工作树。
- 不修复或变更 DSA API、配置字段、认证语义或 Web 设置行为；本任务只冻结基线。
- 不将 `SAL-P0-009`、`SAL-P0-010`、`SAL-P0-012` 或 Gate G0 标记为完成。
- 当前 OpenAPI 快照包含上游 FastAPI 运行时规范；后续若吸收 `main@487e49e` 的 DecisionSignal persist 语义，必须更新快照并记录 OpenAPI diff。
