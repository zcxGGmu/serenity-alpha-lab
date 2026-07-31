# Factor DSL and Operator Whitelist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P3-006` by adding a pure, auditable factor DSL parser, AST validator and compiler that accepts only whitelisted factor expressions.

**Architecture:** Add `src/serenity_alpha_lab/quant/factors/dsl.py` beside the existing FactorDefinition version model. The DSL layer parses formula text into immutable internal nodes, validates all identifiers against a published/draft `FactorDefinition`, and compiles to a JSON-friendly `FactorExpressionPlan` for later execution by future factor-engine/DAG tasks.

**Tech Stack:** Python 3.11+, stdlib `ast`, frozen dataclasses, pytest, existing `FactorDefinition` / `FactorInput` / `FactorWindow` contracts.

---

## Files

- Create: `src/serenity_alpha_lab/quant/factors/dsl.py` for DSL errors, AST nodes, operator registry, validator and compiler.
- Modify: `src/serenity_alpha_lab/quant/factors/__init__.py` to export the DSL contract symbols.
- Create: `tests/quant/test_factor_dsl_contract.py` for red/green contract coverage.
- Create: `docs/factor-dsl-operator-whitelist.md` for grammar, whitelisted operators, safety behavior, non-goals and evidence.
- Modify: `docs/development-progress-checklist.md`, `docs/development-status.md` and `tasks/todo.md` after implementation and verification.

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/quant/test_factor_dsl_contract.py`

- [ ] **Step 1: Write tests for supported expressions**

```python
from serenity_alpha_lab.quant.factors.dsl import compile_factor_expression

def test_factor_dsl_compiles_delay_rank_arithmetic_and_conditionals() -> None:
    plan = compile_factor_expression(
        "where(close > delay(close, 20), rank(close / delay(close, 20) - 1), 0)",
        inputs=_inputs("close"),
        windows=_windows(20),
    )
    assert plan.expression == "where(close > delay(close, 20), rank(close / delay(close, 20) - 1), 0)"
    assert plan.required_inputs == ("close",)
    assert "delay" in plan.required_operators
    assert "rank" in plan.required_operators
    assert "where" in plan.required_operators
```

- [ ] **Step 2: Write tests for rolling and window validation**

```python
def test_factor_dsl_validates_rolling_windows_against_declared_factor_windows() -> None:
    plan = compile_factor_expression(
        "rolling_mean(close, 20) / rolling_std(close, 20)",
        inputs=_inputs("close"),
        windows=_windows(20),
    )
    assert plan.lookback_periods == 20
```

- [ ] **Step 3: Write tests for forbidden syntax and unsafe references**

```python
import pytest
from serenity_alpha_lab.quant.factors.dsl import FactorDslError

@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo bad')",
        "close.__class__",
        "globals()",
        "[x for x in close]",
        "open('/tmp/x')",
        "delay(close, -1)",
    ],
)
def test_factor_dsl_rejects_arbitrary_python_and_future_references(expression: str) -> None:
    with pytest.raises(FactorDslError):
        compile_factor_expression(expression, inputs=_inputs("close"), windows=_windows(20))
```

- [ ] **Step 4: Run tests to verify red**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_factor_dsl_contract.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'serenity_alpha_lab.quant.factors.dsl'`.

### Task 2: DSL Module

**Files:**
- Create: `src/serenity_alpha_lab/quant/factors/dsl.py`
- Modify: `src/serenity_alpha_lab/quant/factors/__init__.py`

- [ ] **Step 1: Implement immutable plan types**

Create frozen dataclasses for `FactorExpressionPlan`, `FactorExpressionNode` and operator metadata. Include `to_record()` methods that return deterministic JSON-friendly dicts.

- [ ] **Step 2: Implement parser and validator**

Use Python `ast.parse(..., mode="eval")` only as a syntax front-end. Accept only constants, names, whitelisted calls, unary/binary arithmetic, comparisons, boolean operations and ternary/`where` conditionals. Reject attributes, subscripts, comprehensions, lambdas, dict/list/set literals, f-strings and all statements.

- [ ] **Step 3: Implement operator whitelist**

Allow only: `delay`, `rolling_mean`, `rolling_sum`, `rolling_std`, `rolling_min`, `rolling_max`, `rank`, `abs`, `log`, `sqrt`, `where`, arithmetic `+ - * /`, comparisons and boolean `and/or/not`. Compile `/` to `guarded_divide`.

- [ ] **Step 4: Implement FactorDefinition bridge**

Expose `compile_factor_definition(definition: FactorDefinition)` to compile `definition.formula.expression` using `definition.inputs` and `definition.windows`, returning the same `FactorExpressionPlan`.

- [ ] **Step 5: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_factor_dsl_contract.py -q`

Expected: PASS.

### Task 3: Documentation And Status

**Files:**
- Create: `docs/factor-dsl-operator-whitelist.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document DSL contract**

Document grammar scope, operator whitelist, compiler output, error semantics, known non-goals and verification evidence. State explicitly that no factor execution, DAG/cache, Qlib, formal backtest, Evidence Agent or real Provider/LLM path was started.

- [ ] **Step 2: Update progress and status**

Mark `SAL-P3-006` DONE, move `SAL-P3-007` to READY, update P3 progress to `6/17`, total progress to `55/129`, add decision/evidence records and refresh the next-start prompt.

- [ ] **Step 3: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/quant/test_factor_dsl_contract.py -q
uv run --extra core --extra dev python -m pytest tests/quant/test_factor_dsl_contract.py tests/quant/test_factor_definition_contract.py tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall src tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

Expected: target/related/full tests pass, compileall pass, lock guard pass, diff check pass, immutable tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

- [ ] **Step 4: Request code review**

Dispatch a focused code-review subagent with the implementation diff and this plan. Fix any critical or important issues before committing.

- [ ] **Step 5: Commit**

Stage only `SAL-P3-006` implementation, tests and documentation, then create a Chinese checkpoint commit using the project template.
