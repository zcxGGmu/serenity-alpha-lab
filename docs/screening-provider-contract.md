# ScreeningProvider 契约与 AlphaSift Adapter 记录

> 任务：`SAL-P3-003` 定义 ScreeningProvider<br>
> 日期：2026-07-23<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-004 CANDIDATEBATCH CONTRACT`

## 1. 交付结论

`SAL-P3-003` 已完成平台侧 `ScreeningProvider` 隔离层。上层 Application/Domain 只依赖 Serenity 自有 DTO、Protocol 和错误类型；AlphaSift 真实运行入口被限制在 `integrations.alphasift` 包内，并且仅通过注入式 client 或 profile guard 后的懒加载进入。

本任务只定义 L1 筛选 Provider 边界和 raw candidate result 形状，不标准化 `CandidateBatch`。标准候选、层级分数、原因码、来源和 snapshot schema 属于 `SAL-P3-004`。

## 2. 平台契约

新增应用层模块：

```text
src/serenity_alpha_lab/application/screening_provider.py
```

核心对象：

- `ScreeningProvider` Protocol：提供 `status()`、`list_strategies()` 和 `screen(request)` 三个同步方法。
- `ScreeningRequest`：请求必须包含 `strategy_id`、`market`、`dataset_versions`、`max_results`、`use_llm_overlay` 和 `timeout_seconds`。
- `ScreeningResult`：返回 provider、strategy、market、dataset versions、raw candidates、snapshot/filter counts、warnings、source errors、trace/run/stage 和 LLM overlay 标记。
- `ScreeningProviderStatus` / `ScreeningStrategy`：统一 status 与 strategy list 的上层形状。
- `ScreeningProviderError` / `ScreeningProviderErrorCategory`：统一 `timeout`、`unavailable`、`invalid_request`、`schema_drift`、`data_invalid` 和 `permanent`。
- `FakeScreeningProvider`：用于测试、离线契约和后续 Screen/Factor 开发的确定性 fake。

`ScreeningRequest.dataset_versions` 必须引用具体 `dsv_*` Dataset Version id，并复用 `DatasetVersionRef.version()` 的校验；`latest` alias 被拒绝。该约束延续 Gate G2：正式筛选/因子运行不能用可漂移 latest 输入。

## 3. AlphaSift Adapter

新增集成模块：

```text
src/serenity_alpha_lab/integrations/alphasift/provider_adapter.py
```

`AlphaSiftScreeningAdapter` 只消费 AlphaSift `dsa_adapter` 的稳定形状：

- `get_status(context=...)`
- `list_strategies(context=...)`
- `screen(strategy, market, max_results, use_llm, context=...)`

Adapter 行为：

- 默认不在模块 import 阶段导入 `alphasift`；只有未注入 client 且 profile guard 允许时，才通过 `importlib.import_module("alphasift.dsa_adapter")` 懒加载。
- CI profile 禁止未注入 client 的真实 AlphaSift provider 调用。
- `use_llm_overlay=True` 时必须通过 Runtime Profile 的 model-call policy；CI 默认拒绝。
- 调用 AlphaSift screen 时把 `dataset_versions`、`trace_id`、`run_id`、`stage_id` 和 `timeout_seconds` 传入 context，方便后续 Worker/调度层接入离线契约与 fallback trace。
- `TimeoutError` 与 timeout 文本统一映射为 `ScreeningProviderErrorCategory.TIMEOUT`；schema/missing 字段映射为 `SCHEMA_DRIFT`；普通不可用路径映射为 `UNAVAILABLE`。
- `application.api_errors.problem_from_exception()` 将 `ScreeningProviderError` 映射为 provider-style ProblemDetails，沿用 trace 和脱敏规则。

## 4. 边界检查

新增架构测试确认：

- `application.screening_provider` 和 `domain` 不导入 `alphasift` 或 `alphasift.*`。
- `integrations.alphasift.provider_adapter` 不在顶层直接导入 `alphasift`，真实包只允许懒加载。

`tests/integrations/test_alphasift_screening_adapter.py` 使用注入式 fake client 覆盖 status、strategies、screen、profile guard、LLM overlay guard、timeout/error mapping 和 malformed strategy payload；没有真实 Provider、真实 LLM 或外部网络调用。

## 5. 明确未做事项

- 未定义 `CandidateBatch` 标准 schema、候选原因码、L1/L2/L3 分数或 rank 口径；该范围属于 `SAL-P3-004`。
- 未实现 FactorDefinition、Factor DSL、Factor Engine、ScreenDefinition、ScreenSnapshot、Screen Lab 或 Quant Screening API。
- 未启动 Quant Core。
- 未启动正式回测。
- 未启动 Evidence Agent。
- 未调用真实 Provider。
- 未调用真实 LLM。
- 未实现 Worker execution loop，未接入 Celery/Redis 实际执行。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 6. 本地验证

| 验证 | 结果 |
|---|---|
| `uv run --extra core --extra dev python -m pytest tests/application/test_screening_provider_contract.py -q` | Red：`1 error`，缺少 `serenity_alpha_lab.application.screening_provider`；Green：`3 passed` |
| `uv run --extra core --extra dev python -m pytest tests/integrations/test_alphasift_screening_adapter.py -q` | Red：`1 error`，缺少 `serenity_alpha_lab.integrations.alphasift`；Green：`5 passed` |
| `uv run --extra core --extra dev python -m pytest tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`22 passed` |
| `uv run --extra core --extra dev python -m pytest -q` | PASS：`252 passed, 3 skipped` |
| `uv run --extra core --extra dev python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

最终测试结果同步记录在 `AEV-052`。
