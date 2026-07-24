# Factor DSL 与算子白名单记录

> 任务：`SAL-P3-006` 实现因子 DSL 与算子白名单<br>
> 日期：2026-07-24<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-007 BASE FACTOR DEFINITIONS`

## 1. 交付结论

`SAL-P3-006` 已建立平台侧因子 DSL parser/AST/validator/compiler 契约。该层只把 `FactorDefinition.formula.expression` 编译为不可变、JSON-friendly 的 `FactorExpressionPlan`，用于后续因子执行器、DAG/cache 和基础因子任务消费；本任务不执行因子值、不发布计算缓存、不启动 Qlib/Quant Core、不进入正式回测或 Evidence Agent。

新增模块：

```text
src/serenity_alpha_lab/quant/factors/dsl.py
```

新增测试：

```text
tests/quant/test_factor_dsl_contract.py
```

## 2. DSL 契约对象

核心对象：

- `FactorExpressionPlan`：编译结果，包含原始表达式、engine/schema version、AST root、required inputs、required operators、lookback periods、Dataset Version 映射和可选 FactorDefinition 标识。
- `FactorExpressionNode`：不可变 AST 节点，记录 operation、value type、children、literal/input value、参数和 source。
- `FactorDslValueType`：当前冻结 `numeric`、`boolean`、`string` 三类编译期类型。
- `compile_factor_expression()`：从表达式、`FactorInput` 和 `FactorWindow` 编译 plan。
- `compile_factor_definition()`：从 `FactorDefinition` 编译 plan，并要求 `formula.language == "serenity_factor_dsl"`。

`FactorExpressionPlan.to_record()` 输出可 JSON 序列化记录，后续可进入 Screen/Factor artifact、API 或 golden tests。

## 3. 白名单语法

解析器只把 Python `ast.parse(..., mode="eval")` 用作语法前端，不执行 Python 代码。当前允许：

- 输入标识符：仅允许已声明的 `FactorInput.input_id`。
- 数值字面量：有限 `int` / `float`。
- 布尔/字符串字面量：仅用于编译期类型校验，不作为任意 Python 值执行。
- 算术：`+`、`-`、`*`、`/`；除法编译为 `guarded_divide`。
- 比较：`>`、`>=`、`<`、`<=`、`==`、`!=`，编译为 `comparison.*`。
- 布尔：`and`、`or`、`not`。
- 条件：`where(condition, true_value, false_value)` 和 Python 三元表达式。
- 时间序列：`delay(input, periods)`。
- rolling：`rolling_mean`、`rolling_sum`、`rolling_std`、`rolling_min`、`rolling_max`。
- 横截面/数学：`rank`、`abs`、`log`、`sqrt`。

## 4. 安全失败

编译器在以下场景抛出 `FactorDslError`：

- 任意 Python/module path：`__import__`、`globals()`、`open()`、`eval()`、属性访问、索引、comprehension、lambda、非白名单 call、keyword args、statement 均被拒绝。
- 未声明输入：表达式中的所有 name 必须匹配 `FactorInput.input_id`。
- 显式非数值输入：`FactorInput.data_type` 如果存在，必须是数值类型；例如 `string` 字段不能进入算术、rolling、rank 或 comparison 表达式。
- 未来引用：`delay()` periods 必须是正整数字面量，`<= 0` 被拒绝。
- 窗口声明：`delay()` periods 和 `rolling_*()` window 必须匹配声明的 `FactorWindow.length`。
- 类型错误：`rank()`、rolling、arithmetic 等只接受 numeric；`where()` condition 必须是 boolean。
- 除零：字面量 `x / 0` 在编译期拒绝；非字面量除法统一编译为 `guarded_divide`，由后续执行器做运行期安全处理。
- 语言不匹配：`compile_factor_definition()` 拒绝非 `serenity_factor_dsl` 的公式语言。

## 5. 与 FactorDefinition 的关系

`SAL-P3-006` 复用 `SAL-P3-005` 的 `FactorDefinition`、`FactorInput` 和 `FactorWindow`：

- `FactorInput.dataset_version` 仍由 FactorDefinition 层强制为具体 `dsv_*` Dataset Version，`latest` 继续被拒绝。
- 编译输出的 `dataset_versions` 只包含实际被表达式引用的输入所属 Dataset。
- `definition_id` 与 `semantic_version` 会进入 plan，方便后续 Factor Run、Artifact、API 和 ScreenDefinition 引用。
- 本任务不改变 draft/published/retired 生命周期，不修改 published manifest，不产生 factor version id。

## 6. 明确未做事项

- 未实现基础 15 个因子；该范围属于 `SAL-P3-007`。
- 未执行因子值、未实现后处理 winsorize/zscore/neutralize、未实现 Factor Evaluation。
- 未实现因子计算 DAG/cache、Historical Universe、ScreenDefinition、ScreenSnapshot、Quant Screening API 或 Screen Lab。
- 未启动 Quant Core、Qlib Adapter、正式组合回测、Portfolio Ledger、Risk Engine 或 Evidence Agent。
- 未调用真实 Provider、真实 LLM 或 Worker execution loop。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 7. 本地验证

| 验证 | 结果 |
|---|---|
| `uv run --extra core --extra dev python -m pytest tests/quant/test_factor_dsl_contract.py -q` | Red：`1 error`，缺少 `serenity_alpha_lab.quant.factors.dsl`；Green：`14 passed` |
| `uv run --extra core --extra dev python -m pytest tests/quant/test_factor_dsl_contract.py tests/quant/test_factor_definition_contract.py tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`42 passed` |
| `uv run --extra core --extra dev python -m pytest -q` | PASS：`272 passed, 3 skipped` |
| `uv run --extra core --extra dev python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | PASS：`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

最终完整验证结果同步记录在 `AEV-055`。
