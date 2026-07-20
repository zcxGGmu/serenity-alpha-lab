# API 错误协议记录

> 任务：`SAL-P1-010` 统一 API 错误协议<br>
> 日期：2026-07-20<br>
> Phase：P1 工程加固<br>
> Gate：G1 未通过<br>
> 范围：应用层 Problem Details DTO、稳定错误码、异常映射、脱敏和框架无关 ASGI middleware；不改写 DSA API route、不刷新 OpenAPI baseline、不实现前端解析、不启动 Provider/LLM、Alembic、PIT Dataset、Quant Core 或正式回测。

## 目标

`src/serenity_alpha_lab/application/api_errors.py` 为后续 API、Worker 和兼容 Facade 提供统一的 `application/problem+json` 输出口径。P1 只冻结协议和 middleware 基础，避免把 FastAPI/Starlette 绑定到应用层，同时复用 `TraceContext` 保证错误响应可关联运行链路。

## 契约

| 类型/函数 | 作用 |
|---|---|
| `ApiErrorCode` | 稳定错误码：`validation_error`、`not_found`、`conflict`、`provider_error`、`internal_error`。 |
| `ProblemDetail` | RFC 7807 风格响应体，包含 `type/title/status/detail/code`，可选 `instance/trace_id/errors`。 |
| `ApiProblemError` | 应用层可显式抛出的 problem error 基类。 |
| `ValidationProblem` / `NotFoundProblem` / `ConflictProblem` / `ProviderProblem` / `InternalProblem` | 常用 HTTP status 与错误码组合。 |
| `problem_from_exception()` | 把现有应用异常映射为稳定 `ProblemDetail`。 |
| `problem_response_body()` | 生成可 JSON 序列化的 response body。 |
| `redact_problem_detail()` | 脱敏自由文本错误详情，移除 stack trace、绝对路径和密钥/Prompt/Body。 |
| `ProblemDetailsMiddleware` | 框架无关 ASGI middleware，捕获异常并返回 `application/problem+json` 与 `x-trace-id`。 |

## 异常映射

| 来源异常 | HTTP status | code | 说明 |
|---|---:|---|---|
| `ValidationProblem` / `ValueError` / `ConfigProfileError` | 422 | `validation_error` | 请求或配置边界不满足。 |
| `TaskNotFound` | 404 | `not_found` | 任务或资源不存在。 |
| `TaskAlreadyExists` | 409 | `conflict` | 幂等或资源状态冲突。 |
| `ResearchOrchestratorError`（请求字段/模式错误） | 422 | `validation_error` | Research DTO 请求校验不满足。 |
| `ResearchOrchestratorError`（DSA/facade 运行失败） | 502 | `provider_error` | DSA/Agent/Provider 兼容外壳失败。 |
| `TaskBackendCapabilityError` / unknown `Exception` | 500 | `internal_error` | 服务能力或未知内部错误，不暴露内部细节。 |

## 脱敏口径

Problem details 不暴露以下信息：

- Python stack trace 与 `File "...", line ...` 调用栈。
- `/Users`、`/home`、`/tmp`、`/var`、Windows 用户目录等绝对路径。
- `api_key`、`token`、`secret`、`password`、`Authorization: Bearer ...` 和 `sk-*` 风格 key。
- `prompt`、`messages`、`body`、`content`、`private_body` 等私有正文。

普通应用错误会保留已脱敏的可理解 `detail`；未知内部异常固定返回 `An unexpected error occurred.`。

## 范围限制

- 不导入 FastAPI、Starlette 或 DSA runtime source。
- 不修改现有 DSA API route、OpenAPI snapshot、Web 客户端解析或桌面端行为。
- 不接入 Provider/LLM 调用，不启动 Evidence Agent、Quant Core、PIT Dataset、Alembic 或正式回测。
- 中间件只处理 response start 前抛出的异常；若下游已开始响应后再失败，会重新抛出以避免生成非法 ASGI 响应。

## 验证

| 验证 | 结果 |
|---|---|
| Red 测试 | `tests/application/test_api_errors.py` 和架构测试初始因缺少 `serenity_alpha_lab.application.api_errors` 失败：`5 failed` |
| 目标测试 | `.cache/dsa-p0/venv/bin/python -m pytest tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py::test_api_error_protocol_stays_framework_neutral -q`：`5 passed` |
| 相关套件 | `.cache/dsa-p0/venv/bin/python -m pytest tests/application tests/architecture -q`：`41 passed` |
| 全量 pytest | `.cache/dsa-p0/venv/bin/python -m pytest -q`：`95 passed` |
| 依赖与状态保护 | `scripts/verify-python-dependency-lock.sh`、`git diff --check`、`git rev-parse upstream/dsa-v3.26.1` 通过；tag 仍为 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| 语法检查 | `py_compile` 覆盖新增 application/test/export 文件，通过 |

## 后续衔接

- `SAL-P1-012` Alembic 接入后可复用该协议对迁移失败、schema drift 和启动前检查输出稳定错误。
- `SAL-P1-016` API 兼容检查可把 problem response 示例纳入 contract snapshot，但不在本任务刷新 OpenAPI baseline。
- P2 持久任务 API 必须使用这些稳定错误码区分 validation、not-found、conflict 和 internal/provider 失败。
