# 结构化日志与 Trace 记录

> 任务：`SAL-P1-011` 统一结构化日志与 Trace<br>
> 日期：2026-07-20<br>
> Phase：P1 工程加固<br>
> Gate：G1 未通过<br>
> 范围：Trace context propagation、结构化 JSON log schema、脱敏过滤和框架无关 ASGI middleware；不实现 OpenTelemetry exporter、Prometheus/Grafana、Provider/Qlib/LLM instrumentation、API route rewrite、Quant Core、PIT Dataset 或正式回测。

## 目标

`src/serenity_alpha_lab/application/tracing.py` 为后续 API、TaskBackend、Worker、Provider、Agent 和报告链路提供统一 `trace_id/run_id/stage_id/user_id` 上下文。P1 先建立 stdlib-only 观测基础，避免把框架或外部 telemetry backend 作为早期依赖。

## 契约

| 类型/函数 | 作用 |
|---|---|
| `TraceContext` | 当前执行上下文，包含 `trace_id`、`run_id`、`stage_id` 和 `user_id`。 |
| `use_trace_context()` | ContextVar 上下文管理器，进入时设置、退出时恢复，避免跨请求泄漏。 |
| `current_trace_context()` | 读取当前 trace context。 |
| `TraceContextFilter` | logging filter，把当前上下文字段附加到 log record。 |
| `StructuredLogFormatter` | 输出 redacted JSON，包含 timestamp、level、logger、module、message 和 trace 字段。 |
| `TraceContextMiddleware` | 框架无关 ASGI middleware，从 `x-trace-id/x-run-id/x-stage-id/x-user-id` 读取上下文，并在响应 header 回写 `x-trace-id`。 |
| `redact_sensitive_data()` | 递归脱敏 secret、token、authorization、api key、prompt、messages、body/content 等敏感字段。 |

## 脱敏口径

日志格式化时会先聚合 standard log fields、active trace context 和 `extra` 字段，再递归脱敏。以下字段类别写入日志时统一替换为 `[REDACTED]`：

- `api_key` / `x-api-key` / `authorization` / `token` / `secret` / `password` / `credential`。
- `prompt`、`messages`、`body`、`content`、`private_body`。
- 任意 key 中包含 `secret`、`token` 或 `password` 的字段。

本任务不记录 request body，不记录完整 Prompt，不接入外部 telemetry exporter。

## 范围限制

- 不引入 FastAPI、Starlette、OpenTelemetry、Prometheus、Grafana 或第三方 logging backend。
- 不改造现有 DSA API route，不接 Provider/Qlib/LLM/Agent instrumentation。
- 不实现 metrics、sampling、span exporter、trace query UI 或告警。

## 验证

- Red：新增 `tests/application/test_trace_context.py` 后，目标测试因缺少 `serenity_alpha_lab.application.tracing` 失败。
- Green：实现 tracing 模块后，`tests/application/test_trace_context.py` 通过 `4 passed`。
- 语法：`py_compile` 覆盖 `src/serenity_alpha_lab/application` 和 `tests/application`。
- Checkpoint：全量 `.cache/dsa-p0/venv/bin/python -m pytest -q` 通过 `70 passed`；`scripts/verify-python-dependency-lock.sh`、`git diff --check` 和 `git rev-parse upstream/dsa-v3.26.1` 通过。
