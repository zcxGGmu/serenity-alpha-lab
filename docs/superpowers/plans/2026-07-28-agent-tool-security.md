# Agent Tool Security Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P5-014` as an offline Agent tool authorization boundary that enforces default-deny tool execution, parameter schema checks, SSRF guards and prompt-injection rejection.

**Architecture:** Add a small application-layer module `src/serenity_alpha_lab/application/agent_tool_security.py` that consumes concrete `PromptRunBinding` and caller-provided stage tool allowlists. It returns deterministic allow/deny decisions and sanitized argument records only; it never executes tools, calls Providers/LLMs, reads Evidence bodies, writes stores, starts Workers, initializes Qlib or renders reports.

**Tech Stack:** Python dataclasses, enums, standard-library `urllib.parse` / `ipaddress` / `re`, existing `PromptRunBinding` and `ToolDeclaration`, pytest contract tests, architecture import guard.

---

### Task 1: Contract Tests And Architecture Guard

**Files:**
- Create: `tests/application/test_agent_tool_security.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`

- [x] **Step 1: Write failing contract tests**

Add tests for:

```python
def test_runtime_guard_defaults_to_deny_for_unbound_or_stage_unapproved_tools(): ...
def test_guard_authorizes_bound_read_only_tool_after_schema_validation_without_execution(): ...
def test_url_arguments_block_ssrf_and_require_declared_host_allowlist(): ...
def test_prompt_injection_text_in_tool_arguments_is_rejected(): ...
```

The tests must import `AgentToolSecurityGuard`, `AgentToolInvocationRequest`, `AgentToolAuthorizationStatus` and `AgentToolSecurityIssueCode` from `serenity_alpha_lab.application.agent_tool_security`.

- [x] **Step 2: Add architecture guard**

Add `test_agent_tool_security_stays_offline_and_runtime_free()` to `tests/architecture/test_architecture_boundaries.py`. Allow only standard library modules plus `serenity_alpha_lab.evidence.prompt_registry`; explicitly forbid `litellm`, Provider SDKs, `fastapi`, `sqlalchemy`, `qlib`, integrations, repositories, services, DSA agent runtime and quant runtime imports.

- [x] **Step 3: Run tests to verify Red**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_agent_tool_security.py -q
```

Expected: failure because `serenity_alpha_lab.application.agent_tool_security` does not exist.

### Task 2: Offline Tool Security Guard

**Files:**
- Create: `src/serenity_alpha_lab/application/agent_tool_security.py`
- Test: `tests/application/test_agent_tool_security.py`

- [x] **Step 1: Implement immutable request/result types**

Define:

```python
AGENT_TOOL_SECURITY_CONTRACT_VERSION = "research.agent_tool_security@1.0.0"

class AgentToolAuthorizationStatus(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"

class AgentToolSecurityIssueCode(StrEnum):
    TOOL_NOT_BOUND = "tool_not_bound"
    TOOL_NOT_STAGE_ALLOWED = "tool_not_stage_allowed"
    TOOL_SIDE_EFFECT_FORBIDDEN = "tool_side_effect_forbidden"
    TOOL_SCOPE_FORBIDDEN = "tool_scope_forbidden"
    INPUT_SCHEMA_VIOLATION = "input_schema_violation"
    UNSAFE_URL = "unsafe_url"
    PROMPT_INJECTION = "prompt_injection"
```

Add dataclasses for `AgentToolSecurityIssue`, `AgentToolInvocationRequest` and `AgentToolAuthorizationDecision`, each with deterministic `to_record()` output and hash where useful.

- [x] **Step 2: Implement default-deny authorization**

`AgentToolSecurityGuard.authorize(request)` must deny when the requested tool/version is not in the concrete `PromptRunBinding`, when it is absent from `stage_tool_allowlist`, when side effects are not `none` / `read_only`, or when scopes include shell/trading/brokerage/database/filesystem write classes.

- [x] **Step 3: Implement JSON-Schema subset validation**

Support the existing registry subset: object schemas with `properties`, `required`, `additionalProperties`, scalar `type` checks (`string`, `integer`, `number`, `boolean`, `object`, `array`) and nested object validation. Return a denied decision with `INPUT_SCHEMA_VIOLATION`; do not raise for ordinary caller input failures.

- [x] **Step 4: Implement SSRF and prompt-injection guards**

For string argument fields named like `url`, `uri`, `endpoint`, `source_url` or declared in tool metadata, parse URLs and reject:

- non-HTTPS by default,
- URLs with credentials,
- localhost / loopback / private / link-local / multicast / unspecified IPs,
- hostnames ending in `.local`, `.localhost` or `.internal`,
- hosts not listed in tool metadata `allowed_url_hosts`.

Scan all string arguments for external instruction attempts such as "ignore previous instructions", "system prompt", "developer message", "call/run/use tool", "shell", "api key", "token", "admin=true" and deny with `PROMPT_INJECTION`.

- [x] **Step 5: Run focused Green**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_agent_tool_security.py -q
```

Expected: all SAL-P5-014 focused tests pass.

### Task 3: Evidence Doc And Status Closeout

**Files:**
- Create: `docs/agent-tool-security.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Document SAL-P5-014 contract**

Create `docs/agent-tool-security.md` with contract name `research.agent_tool_security@1.0.0`, module/test paths, rules, non-goals and verification table.

- [x] **Step 2: Update progress/status registers**

Mark only `SAL-P5-014` done after verification. Add `DEC-100` for the tool-security decision and `AEV-102` for validation evidence. Advance P5 from `13/18` to `14/18` and total progress from `101/129` to `102/129`. Make `SAL-P5-015` the next READY task.

- [x] **Step 3: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_agent_tool_security.py tests/evidence/test_prompt_schema_registry.py tests/evidence/test_source_trust_cleaning.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

Expected: focused/related/full suites pass, compile passes, dependency lock passes, upstream tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`, diff hygiene passes.

- [x] **Step 4: Create Chinese checkpoint commit**

Stage only SAL-P5-014 code/tests/docs/status files. Do not stage `.worktrees`, `.cache`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files. Commit with:

```text
feat(P5): 实现 Agent 工具安全

完成内容：
- ...

兼容性与风险：
- ...

验证：
- ...

关联任务：SAL-P5-014, Gate G5
```
