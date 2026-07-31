# Agent Tool Security

> Task: `SAL-P5-014` Strengthen Agent Tool Security<br>
> Date: 2026-07-28<br>
> Status: `APPROVED FOR SAL-P5-015 INPUT ONLY`

## Conclusion

`SAL-P5-014` adds a pure offline Agent tool authorization boundary:

```text
src/serenity_alpha_lab/application/agent_tool_security.py
tests/application/test_agent_tool_security.py
```

The guard consumes a concrete `PromptRunBinding`, a caller-provided stage tool allowlist and caller-provided tool arguments. It returns deterministic allow/deny decisions, safe argument copies and issue records. It never executes tools, calls Providers or LLMs, reads Evidence bodies, writes Evidence Store, starts Workers, initializes Qlib, schedules production work, renders reports or promotes formal portfolio backtests.

## Contracts

| Item | Contract |
|---|---|
| Tool security contract | `research.agent_tool_security@1.0.0` |
| Authorization schema | `research.agent_tool_authorization` / `1.0.0` |
| Guard | `AgentToolSecurityGuard` |
| Request | `AgentToolInvocationRequest` |
| Decision | `AgentToolAuthorizationDecision` |
| Issue record | `AgentToolSecurityIssue` |
| Issue codes | `AgentToolSecurityIssueCode` |

## Authorization Rules

`AgentToolSecurityGuard.authorize()` is default-deny:

- requested tool name/version must exist in the concrete `PromptRunBinding`;
- requested tool name must be in the stage tool allowlist persisted or supplied by the caller;
- tool side effects must remain `none` or `read_only`;
- forbidden scopes such as `shell`, `trading`, `trade`, `brokerage`, `database_write`, `db_write` and `filesystem_write` are denied;
- denied decisions always return `safe_arguments={}` and `would_execute=false`;
- allowed decisions still return `would_execute=false`, because this boundary authorizes only and never invokes the tool.

## Parameter Schema Rules

The runtime guard validates the existing Prompt Registry JSON-Schema subset before any prompt-injection or URL checks:

- root and nested `object` schemas;
- `properties`, `required` and `additionalProperties=false`;
- scalar `type` checks for `string`, `integer`, `number`, `boolean`, `array`, `object` and `null`;
- array item schemas.

Schema failures return `input_schema_violation` issues instead of raising for ordinary caller input failures.

## SSRF And URL Rules

For argument fields named `url`, `uri`, `endpoint`, `source_url` or listed in tool metadata `url_argument_names`, the guard parses URL strings and rejects:

- non-HTTP(S) schemes;
- plain HTTP by default;
- URLs containing credentials;
- missing hosts;
- `localhost`, `.local`, `.localhost` and `.internal` names;
- loopback, private, link-local, multicast, reserved or unspecified IPs;
- hosts not listed in tool metadata `allowed_url_hosts` when such an allowlist is declared.

This is intentionally metadata-driven and offline. The guard does not resolve DNS and does not fetch the URL.

## Prompt-Injection Rules

The guard scans string arguments after schema validation and before authorization is allowed. It denies external instruction attempts such as:

- ignoring or disregarding previous/system/developer instructions;
- references to system prompts or developer messages;
- requests to call, run, use or invoke tools/functions/APIs/shells;
- attempts to reveal prompts, instructions, secrets, tokens or API keys;
- `admin=true`, `root=true` or direct `shell.run` hints.

This complements `SAL-P5-004` source-trust cleaning by preventing prompt-injection text from being reused as later tool parameters.

## Non-Goals

- No real Provider calls, real LLM calls, LiteLLM imports, API routes, Worker loops or queue dispatch.
- No tool execution, retry loop, browser/web fetch, database write, filesystem write, shell access, trading/brokerage action or DSA Agent runtime invocation.
- No Evidence Store writes, Evidence body reads, EvidenceBundle construction, Quant Evidence Adapter execution or Citation Validator repair loop.
- No report renderer, Markdown/HTML generation, notification workflow or report publication.
- No Qlib runtime, production scheduling or formal portfolio backtest promotion.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_agent_tool_security.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.agent_tool_security'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/application/test_agent_tool_security.py -q` -> `4 passed` |
| Architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_agent_tool_security_stays_offline_and_runtime_free -q` -> `1 passed` |
| Related P5/security suite | `uv run --extra core --extra dev python -m pytest tests/application/test_agent_tool_security.py tests/evidence/test_prompt_schema_registry.py tests/evidence/test_source_trust_cleaning.py tests/application/test_model_routing_cache_budget.py tests/repositories/test_agent_stage_store.py tests/architecture/test_architecture_boundaries.py -q` -> `47 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `479 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves offline Agent tool authorization, runtime schema validation, SSRF/host allowlist checks and prompt-injection argument rejection as input to `SAL-P5-015` trusted ResearchReport rendering. Later P5 tasks must still implement trusted report rendering, UI/notification surfaces, Agent evaluation and Worker runtime before Gate G5 can pass.
