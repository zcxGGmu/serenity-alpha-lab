# 配置 Profile 与密钥边界记录

> 任务：`SAL-P1-014` 整理配置与运行 Profile
> 日期：2026-07-20
> 范围：定义 desktop/standalone/ci 运行 Profile、Pydantic Settings、密钥边界、脱敏诊断和配置来源追踪。

## 1. 结论

`SAL-P1-014` 新增应用层配置 Profile facade，作为后续 API、Worker、Desktop 和部署入口共享的配置边界。实现位于 `src/serenity_alpha_lab/application/config_profiles.py`，不改写 DSA runtime `.env`，不新增 Web/API 路由，不启动真实 Provider、LLM、Alembic、PIT Dataset、Quant Core 或正式回测。

## 2. 运行 Profile

| Profile | 网络调用 | 模型调用 | Provider 调用 | `.env` 变更 |
|---|---:|---:|---:|---:|
| `desktop` | 允许 | 允许 | 允许 | 仅生成可保存预览，本任务不执行写入 |
| `standalone` | 允许 | 允许 | 允许 | 禁止通过 service/profile API 改写部署 `.env` |
| `ci` | 禁止 | 禁止 | 禁止 | 禁止 |

`ci` profile 默认离线/stub 行为；如果传入真实模型或 Provider key，或显式打开网络/模型/Provider 调用，会抛出 `ConfigProfileError`。

## 3. 配置来源与脱敏诊断

`load_runtime_settings()` 从显式 mapping 或进程环境读取配置，并为每个字段记录来源：

- `SERENITY_PROFILE` / `RUNTIME_PROFILE`
- `SERENITY_DATABASE_URL` / `DATABASE_URL`
- `SERENITY_ALLOW_NETWORK`
- `SERENITY_ALLOW_MODEL_CALLS`
- `SERENITY_ALLOW_PROVIDER_CALLS`
- `SERENITY_CONFIG_VERSION`
- `OPENAI_API_KEY` / `SERENITY_OPENAI_API_KEY`
- `DEEPSEEK_API_KEY` / `SERENITY_DEEPSEEK_API_KEY`
- `TUSHARE_TOKEN` / `SERENITY_TUSHARE_TOKEN`
- `TAVILY_API_KEY` / `SERENITY_TAVILY_API_KEY`
- `SERPAPI_API_KEY` / `SERENITY_SERPAPI_API_KEY`

`redacted_config_diagnostics()` 输出字段值、来源和敏感级别；模型 API key、Provider token 和搜索 key 只显示 `[REDACTED]`，不会泄露完整密钥。

## 4. 更新预览边界

`preview_runtime_config_update()` 只验证更新并返回 `RuntimeConfigUpdatePreview`，不会写入文件。传入 `target_env_file` 时：

- `desktop` 会返回 `would_rewrite_env_file=True`，供后续显式保存流程使用。
- `standalone` 和 `ci` 返回 `would_rewrite_env_file=False`，并给出阻止原因。
- 目标 `.env` 内容在本任务内不会被修改。

## 5. 依赖处理

根 `pyproject.toml` 将 `pydantic-settings>=2.0.0` 加入 `core` extra。`uv.lock` 已以最小 diff 记录 Serenity 项目 core extra 的直接依赖，`requirements.txt` 由现有 drift guard 导出。

## 6. 验收证据

| 验证 | 结果 |
|---|---|
| Red 测试 | `tests/application/test_config_profiles.py` 初始因缺少 `serenity_alpha_lab.application.config_profiles` 失败 |
| 目标测试 | `.cache/dsa-p0/venv/bin/python -m pytest tests/application/test_config_profiles.py -q`：`9 passed` |
| 应用/架构套件 | `.cache/dsa-p0/venv/bin/python -m pytest tests/application tests/architecture -q`：`29 passed` |
| P1 相关套件 | `.cache/dsa-p0/venv/bin/python -m pytest tests/application tests/architecture tests/domain tests/repositories tests/integrations -q`：`79 passed` |
| 全量 pytest | `.cache/dsa-p0/venv/bin/python -m pytest -q`：`79 passed` |
| 依赖 drift guard | `scripts/verify-python-dependency-lock.sh`：通过 |

## 7. 后续衔接

- `SAL-P1-010` API 错误协议可复用 `ConfigProfileError` 映射为稳定 problem detail。
- `SAL-P1-012` / `SAL-P1-013` 可基于 profile 区分桌面 SQLite 与服务数据库迁移入口。
- P2 Provider、Worker 和 Agent 入口必须复用 `profile_policy()`，避免 CI 和测试环境发起真实网络/模型调用。
