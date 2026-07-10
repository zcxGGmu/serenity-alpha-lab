# Phase 7 Agent, Bot, Runtime, And Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate DSA Agent/Bot patterns and packaging/release capabilities into Serenity-owned research tools, a platform-neutral default-off Bot, a deferred desktop runtime contract, a no-secret Docker runtime, and a unified offline application release gate.

**Architecture:** Build pure Python contracts first, wrapping existing Serenity analysis/readiness/evidence outputs without implicit I/O. Add non-secret health diagnostics, then package the existing API and web app in a non-root container and make CI execute the same machine-readable release gate for pull requests, branches, and tags.

**Tech Stack:** Python 3.11+ / dataclasses / standard-library HTTP server / pytest / React + Vite + Vitest + Playwright / Docker / GitHub Actions.

---

## File Structure

- Create: `src/serenity_alpha_lab/agents/__init__.py`
  - Exports research tool contracts, built-in tools, and runtime registry.
- Create: `src/serenity_alpha_lab/agents/contracts.py`
  - Defines `ResearchToolContext`, `ResearchToolParameter`, `ResearchToolDefinition`, and `ResearchToolResult`.
- Create: `src/serenity_alpha_lab/agents/tools.py`
  - Implements `serenity_research_summary` and `serenity_evidence_gaps` over caller-provided Serenity analysis payloads.
- Create: `src/serenity_alpha_lab/agents/runtime.py`
  - Implements explicit allowlisting, default-off visibility, execution, failure sanitization, and output boundary validation.
- Create: `tests/test_research_agents.py`
  - Covers context requirements, evidence/readiness propagation, tool visibility, safety boundaries, and fail-open diagnostics.
- Create: `src/serenity_alpha_lab/bot/__init__.py`
  - Exports normalized Bot contracts and dispatcher.
- Create: `src/serenity_alpha_lab/bot/contracts.py`
  - Defines platform-neutral `BotMessage` and `BotResponse`.
- Create: `src/serenity_alpha_lab/bot/commands.py`
  - Defines `status`, `analyze`, and `evidence-gaps` research commands around injected services.
- Create: `src/serenity_alpha_lab/bot/dispatcher.py`
  - Implements command parsing, aliases, default-off behavior, rate limiting, validation, and sanitized errors.
- Create: `tests/test_research_bot.py`
  - Covers disabled mode, parsing, command reuse, readiness/gap formatting, rate limits, and safety vocabulary.
- Create: `src/serenity_alpha_lab/desktop_runtime.py`
  - Defines loopback-only desktop runtime and deferred packaging readiness contract.
- Create: `tests/test_desktop_runtime.py`
  - Covers packaging deferral, local commands, disabled updates, and no bundled credentials.
- Modify: `src/serenity_alpha_lab/app/config.py`
  - Adds default-off Agent/Bot fields and desktop runtime status.
- Modify: `src/serenity_alpha_lab/app/local_api.py`
  - Adds no-secret capability health diagnostics.
- Modify: `tests/test_app_api.py`
  - Covers Agent/Bot/Desktop health output.
- Create: `src/serenity_alpha_lab/release_gate.py`
  - Builds and runs the machine-readable offline application release checklist.
- Create: `scripts/verify_offline_release.py`
  - Thin CLI wrapper for plan output and execution.
- Create: `tests/test_release_gate.py`
  - Covers release metadata, safety/boundary checks, workflow reuse, Docker rules, and protected-artifact exclusions.
- Create: `.dockerignore`
  - Excludes credentials, DSA/generated/runtime/cache paths.
- Create: `docker/Dockerfile`
  - Builds Serenity web assets and a non-root Python runtime.
- Create: `docker/docker-compose.yml`
  - Defines local API and static web services.
- Modify: `apps/serenity-web/playwright.config.ts`
  - Uses bundled Chromium in CI and installed Edge locally.
- Modify: `.github/workflows/verify.yml`
  - Installs Python/Node dependencies, browser runtime, and runs the unified release gate.
- Modify: `Makefile`
  - Adds frontend and release-gate targets without changing existing `verify`.
- Modify during closeout: `docs/serenity-led-dsa-full-migration-tracker.md`, `tasks/todo.md`, `tasks/lessons.md`.
- Do not modify: protected generated `output/ui/*` artifacts.

## Source Reference Boundaries

- Agent references:
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/agent/tools/registry.py`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/agent/executor.py`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/agent/test_serenity_prompt_boundaries.py`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/agent/tools/test_serenity_evidence_quality_tool.py`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/agent/tools/test_serenity_evidence_gap_tool.py`
- Bot references:
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/bot/models.py`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/bot/commands/base.py`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/bot/dispatcher.py`
- Packaging/release references:
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/apps/dsa-desktop/main.js`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docker/Dockerfile`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docker/entrypoint.sh`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/scripts/serenity_release_check.py`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/.github/workflows/ci.yml`
- Never import these files from Serenity runtime.

### Task 1: Evidence-Grounded Agent Contracts And Tools

**Files:**
- Create: `tests/test_research_agents.py`
- Create after red: `src/serenity_alpha_lab/agents/__init__.py`
- Create after red: `src/serenity_alpha_lab/agents/contracts.py`
- Create after red: `src/serenity_alpha_lab/agents/tools.py`
- Create after red: `src/serenity_alpha_lab/agents/runtime.py`

- [ ] **Step 1: Write failing tests for default-off visibility and explicit context**

```python
from serenity_alpha_lab.agents import ResearchToolContext, build_research_tool_registry


def test_agent_tools_are_hidden_by_default_and_require_explicit_context():
    disabled = build_research_tool_registry(enabled=False)
    assert disabled.list_names() == []

    enabled = build_research_tool_registry(
        enabled=True,
        allowlist=["serenity_research_summary"],
    )
    result = enabled.execute("serenity_research_summary", context=None)
    payload = result.to_dict()
    assert payload["status"] == "blocked"
    assert payload["diagnostics"]["reason"] == "analysis_context_required"
    assert payload["research_only"] is True
```

- [ ] **Step 2: Write failing tests for evidence/readiness propagation and gap sorting**

```python
def _analysis_payload():
    return {
        "subject": {"code": "SIVE", "stock_name": "Sivers Semiconductors"},
        "readiness": {"status": "needs_work", "gaps": ["missing_primary_source", "missing_risk_coverage"]},
        "report_gate": {"available": False, "reason": "readiness_not_ready"},
        "signals": {
            "rating": "watch",
            "confidence": "low",
            "gaps": ["missing_primary_source", "missing_risk_coverage"],
            "evidence_ids": ["serenity:market-data:SIVE:quote:2026-07-10"],
        },
        "evidence": [
            {
                "id": "serenity:market-data:SIVE:quote:2026-07-10",
                "source_url": "serenity://market-data/SIVE/quote/2026-07-10",
                "claim_type": "fact",
            }
        ],
        "diagnostics": {"provider_status": "ok"},
    }


def test_agent_summary_preserves_readiness_report_gate_and_evidence_ids():
    registry = build_research_tool_registry(
        enabled=True,
        allowlist=["serenity_research_summary", "serenity_evidence_gaps"],
    )
    context = ResearchToolContext(analysis=_analysis_payload(), requested_by="test")

    summary = registry.execute("serenity_research_summary", context=context).to_dict()
    gaps = registry.execute("serenity_evidence_gaps", context=context).to_dict()

    assert summary["status"] == "needs_work"
    assert summary["readiness"]["status"] == "needs_work"
    assert summary["report_gate"]["available"] is False
    assert summary["evidence_ids"] == ["serenity:market-data:SIVE:quote:2026-07-10"]
    assert [item["gap_code"] for item in gaps["gaps"]] == [
        "missing_primary_source",
        "missing_risk_coverage",
    ]
```

- [ ] **Step 3: Write failing tests for recursive output safety and sanitized failures**

```python
def test_agent_runtime_blocks_recursive_trading_fields():
    registry = build_research_tool_registry(enabled=True, allowlist=["serenity_research_summary"])
    context = ResearchToolContext(
        analysis={**_analysis_payload(), "nested": {"operation_advice": "buy"}},
        requested_by="test",
    )

    payload = registry.execute("serenity_research_summary", context=context).to_dict()

    assert payload["status"] == "blocked"
    assert payload["diagnostics"]["reason"] == "forbidden_output_field"
    assert payload["diagnostics"]["field"] == "operation_advice"
```

- [ ] **Step 4: Run red Agent tests**

Run: `python3 -m pytest tests/test_research_agents.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.agents'`.

- [ ] **Step 5: Implement the minimal Agent contracts and registry**

Implement:

```python
@dataclass(frozen=True)
class ResearchToolContext:
    analysis: Mapping[str, Any]
    requested_by: str


@dataclass(frozen=True)
class ResearchToolResult:
    tool: str
    status: str
    payload: dict[str, Any]
    diagnostics: dict[str, Any]
    research_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "status": self.status,
            "research_only": self.research_only,
            **self.payload,
            "diagnostics": dict(self.diagnostics),
        }
```

`ResearchToolRegistry.execute()` must:

1. return `blocked` when the tool is unavailable or context is absent;
2. recursively scan input and output keys against the fixed forbidden field set;
3. call only allowlisted handlers;
4. catch exceptions and return `failed_open` with `error_type` only.

- [ ] **Step 6: Run green Agent tests**

Run: `python3 -m pytest tests/test_research_agents.py -q`

Expected: PASS.

- [ ] **Step 7: Run Agent regression and boundary guard**

Run: `python3 -m pytest tests/test_research_agents.py tests/test_analysis_pipeline.py tests/test_analysis_report.py tests/test_dsa_migration_boundaries.py -q`

Expected: PASS.

### Task 2: Platform-Neutral Default-Off Research Bot

**Files:**
- Create: `tests/test_research_bot.py`
- Create after red: `src/serenity_alpha_lab/bot/__init__.py`
- Create after red: `src/serenity_alpha_lab/bot/contracts.py`
- Create after red: `src/serenity_alpha_lab/bot/commands.py`
- Create after red: `src/serenity_alpha_lab/bot/dispatcher.py`

- [ ] **Step 1: Write failing disabled-mode and parsing tests**

```python
from serenity_alpha_lab.bot import BotMessage, ResearchBotDispatcher


def test_research_bot_is_disabled_by_default_and_does_not_call_services():
    calls = []
    dispatcher = ResearchBotDispatcher(analyze=lambda symbol: calls.append(symbol))
    response = dispatcher.dispatch(
        BotMessage(user_id="u1", content="/analyze SIVE"),
    )
    assert response.status == "disabled"
    assert calls == []
    assert response.research_only is True


def test_research_bot_parses_aliases_and_unknown_commands():
    dispatcher = ResearchBotDispatcher(enabled=True, analyze=lambda symbol: {})
    assert dispatcher.parse_command("分析 SIVE") == ("analyze", ["SIVE"])
    response = dispatcher.dispatch(BotMessage(user_id="u1", content="/unknown"))
    assert response.status == "error"
    assert "help" in response.text.lower()
```

- [ ] **Step 2: Write failing tests proving Bot reuse of Agent tool results**

```python
def test_bot_analyze_and_evidence_gap_commands_preserve_research_states():
    analysis = _analysis_payload()
    dispatcher = ResearchBotDispatcher(
        enabled=True,
        analyze=lambda symbol: analysis,
    )

    analyze_response = dispatcher.dispatch(BotMessage(user_id="u1", content="/analyze SIVE"))
    gap_response = dispatcher.dispatch(BotMessage(user_id="u1", content="/evidence-gaps SIVE"))

    assert analyze_response.status == "needs_work"
    assert "serenity:market-data:SIVE:quote:2026-07-10" in analyze_response.evidence_ids
    assert gap_response.status == "needs_work"
    assert "missing_primary_source" in gap_response.text
```

- [ ] **Step 3: Write failing rate-limit and safety tests**

```python
def test_bot_rate_limit_and_output_never_emit_trading_fields():
    dispatcher = ResearchBotDispatcher(
        enabled=True,
        analyze=lambda symbol: _analysis_payload(),
        max_requests=1,
        window_seconds=60,
    )
    first = dispatcher.dispatch(BotMessage(user_id="u1", content="/status"))
    second = dispatcher.dispatch(BotMessage(user_id="u1", content="/status"))
    assert first.status == "ok"
    assert second.status == "rate_limited"
    rendered = str(first.to_dict()).lower()
    assert "operation_advice" not in rendered
    assert "target_price" not in rendered
```

- [ ] **Step 4: Run red Bot tests**

Run: `python3 -m pytest tests/test_research_bot.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.bot'`.

- [ ] **Step 5: Implement Bot contracts and dispatcher**

Implement normalized contracts:

```python
@dataclass(frozen=True)
class BotMessage:
    user_id: str
    content: str
    message_id: str = ""


@dataclass(frozen=True)
class BotResponse:
    status: str
    text: str
    evidence_ids: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    research_only: bool = True
```

The dispatcher must:

- expose `status`, `analyze`, and `evidence-gaps`;
- use an injected `analyze(symbol)` callable;
- build Agent tool context from the returned analysis payload;
- return disabled before invoking any service;
- use a monotonic-time sliding window per user;
- sanitize exception responses to exception type only.

- [ ] **Step 6: Run green Bot tests**

Run: `python3 -m pytest tests/test_research_bot.py -q`

Expected: PASS.

- [ ] **Step 7: Run Agent/Bot combined regression**

Run: `python3 -m pytest tests/test_research_agents.py tests/test_research_bot.py tests/test_analysis_pipeline.py tests/test_dsa_migration_boundaries.py -q`

Expected: PASS.

### Task 3: Runtime Health And Desktop Readiness

**Files:**
- Create: `tests/test_desktop_runtime.py`
- Create after red: `src/serenity_alpha_lab/desktop_runtime.py`
- Modify: `src/serenity_alpha_lab/app/config.py`
- Modify: `src/serenity_alpha_lab/app/local_api.py`
- Modify: `tests/test_app_api.py`

- [ ] **Step 1: Write failing desktop runtime contract test**

```python
from serenity_alpha_lab.desktop_runtime import build_desktop_runtime_plan


def test_desktop_runtime_plan_is_loopback_only_and_packaging_is_deferred():
    payload = build_desktop_runtime_plan().to_dict()
    assert payload["runtime_mode"] == "local_web_api"
    assert payload["backend_command"] == ["serenity-alpha-lab", "serve-app"]
    assert payload["packaging_status"] == "deferred_until_runtime_parity"
    assert payload["automatic_updates_enabled"] is False
    assert payload["credentials_bundled"] is False
    assert payload["public_bind_enabled"] is False
```

- [ ] **Step 2: Add failing API health assertions**

Add to `tests/test_app_api.py`:

```python
def test_health_reports_agent_bot_and_desktop_capabilities_default_off():
    payload = _health_payload(AppRuntimeConfig())
    assert payload["research_agents"] == {"enabled": False, "execution": "explicit_context_only"}
    assert payload["research_bot"]["enabled"] is False
    assert payload["research_bot"]["platform_delivery"] == "disabled"
    assert payload["desktop"]["packaging_status"] == "deferred_until_runtime_parity"
    rendered = str(payload).lower()
    assert "token" not in rendered
    assert "secret" not in rendered
    assert "/users/" not in rendered
```

- [ ] **Step 3: Run red desktop/API tests**

Run: `python3 -m pytest tests/test_desktop_runtime.py tests/test_app_api.py::test_health_reports_agent_bot_and_desktop_capabilities_default_off -q`

Expected: FAIL because the desktop module and health fields do not exist.

- [ ] **Step 4: Implement desktop contract and health config**

Add immutable config fields:

```python
research_agents_enabled: bool = False
research_bot_enabled: bool = False
research_bot_platform_delivery_enabled: bool = False
desktop_packaging_status: str = "deferred_until_runtime_parity"
```

`build_desktop_runtime_plan()` must return only loopback/local commands and fixed disabled integration diagnostics.

- [ ] **Step 5: Run green desktop/API tests**

Run: `python3 -m pytest tests/test_desktop_runtime.py tests/test_app_api.py -q`

Expected: PASS.

### Task 4: Machine-Readable Offline Application Release Gate

**Files:**
- Create: `tests/test_release_gate.py`
- Create after red: `src/serenity_alpha_lab/release_gate.py`
- Create after red: `scripts/verify_offline_release.py`
- Modify: `Makefile`

- [ ] **Step 1: Write failing release-plan contract tests**

```python
from serenity_alpha_lab.release_gate import build_release_check_plan


def test_release_plan_is_no_secret_research_only_and_covers_all_surfaces():
    plan = build_release_check_plan()
    assert plan["offline_application_semantics"] is True
    assert plan["requires_secrets"] is False
    assert plan["requires_external_providers"] is False
    assert plan["protected_paths"] == ["output/ui"]
    ids = {check["id"] for check in plan["checks"]}
    assert {
        "python_tests",
        "doctor",
        "agent_bot_desktop",
        "report_safety",
        "dsa_boundary",
        "frontend_unit",
        "frontend_build",
        "frontend_smoke",
        "docker_static",
        "docker_smoke",
    } <= ids
```

- [ ] **Step 2: Write failing result and protected-path tests**

```python
def test_release_gate_never_treats_missing_required_check_as_passed(tmp_path):
    result = run_release_check(
        command_runner=lambda check: {"status": "blocked", "reason": "test_failure"},
        include_browser_smoke=False,
        include_docker_smoke=False,
    )
    assert result["status"] == "blocked"
    assert result["error_count"] >= 1


def test_release_plan_does_not_use_protected_generated_ui_as_input():
    rendered = str(build_release_check_plan()).lower()
    assert "output/ui/analyses/manifest.json" not in rendered
    assert "output/ui/reports/deliverable-research-report.md" not in rendered
```

- [ ] **Step 3: Run red release tests**

Run: `python3 -m pytest tests/test_release_gate.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.release_gate'`.

- [ ] **Step 4: Implement the release plan and runner**

The plan must use explicit command arrays and internal checks. The runner must:

- return `passed`, `blocked`, or `skipped`;
- capture return code and bounded stdout/stderr tails;
- set all Serenity external integration environment flags to false unless a test overrides them;
- run report-safety and DSA boundary scans without network;
- skip browser/Docker smoke only when the caller explicitly disables them;
- return nonzero from `scripts/verify_offline_release.py` when status is blocked.

- [ ] **Step 5: Add Make targets**

Add:

```make
.PHONY: frontend-test frontend-build frontend-smoke release-check

frontend-test:
	cd apps/serenity-web && npm test -- --run

frontend-build:
	cd apps/serenity-web && npm run build

frontend-smoke:
	cd apps/serenity-web && npm run test:smoke -- --reporter=line

release-check:
	PYTHONPATH=src python3 scripts/verify_offline_release.py
```

- [ ] **Step 6: Run green release tests**

Run: `python3 -m pytest tests/test_release_gate.py -q`

Expected: PASS.

### Task 5: Docker Runtime And Static Packaging Rules

**Files:**
- Create: `.dockerignore`
- Create: `docker/Dockerfile`
- Create: `docker/docker-compose.yml`
- Modify: `tests/test_release_gate.py`

- [ ] **Step 1: Add failing Docker static tests**

```python
def test_docker_runtime_is_non_root_no_secret_and_excludes_protected_outputs():
    dockerfile = Path("docker/Dockerfile").read_text(encoding="utf-8")
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")
    compose = Path("docker/docker-compose.yml").read_text(encoding="utf-8")

    assert "USER serenity" in dockerfile
    assert "/health" in dockerfile
    assert 'CMD ["serenity-alpha-lab", "serve-app", "--host", "0.0.0.0", "--port", "8010"]' in dockerfile
    assert "output/ui" in dockerignore
    assert ".env" in dockerignore
    assert "daily_stock_analysis" in dockerignore
    assert "SERENITY_RESEARCH_AGENTS_ENABLED=false" in compose
    assert "SERENITY_RESEARCH_BOT_ENABLED=false" in compose
```

- [ ] **Step 2: Run red Docker static test**

Run: `python3 -m pytest tests/test_release_gate.py::test_docker_runtime_is_non_root_no_secret_and_excludes_protected_outputs -q`

Expected: FAIL because Docker files do not exist.

- [ ] **Step 3: Implement Docker files**

`docker/Dockerfile` must:

1. build `apps/serenity-web` with Node 20;
2. install the Serenity package in Python 3.11 slim;
3. copy web `dist` to `/app/web`;
4. create and use non-root user `serenity`;
5. expose 8010;
6. use a Python standard-library health check;
7. default to `serve-app` with no secrets.

`docker/docker-compose.yml` must define:

- `api` on 8010;
- `web` on 4175 with `python -m http.server 4175 --bind 0.0.0.0 --directory /app/web`;
- all Agent/Bot/notification/provider integrations disabled.

- [ ] **Step 4: Run green Docker static tests**

Run: `python3 -m pytest tests/test_release_gate.py -q`

Expected: PASS.

- [ ] **Step 5: Build and smoke Docker when available**

Run:

```bash
docker build -f docker/Dockerfile -t serenity-alpha-lab:phase7 .
docker run --rm -d --name serenity-alpha-lab-phase7 -p 18010:8010 serenity-alpha-lab:phase7
python3 -c 'import json, urllib.request; payload=json.load(urllib.request.urlopen("http://127.0.0.1:18010/health", timeout=10)); assert payload["status"] == "ok"; assert payload["research_only"] is True'
docker stop serenity-alpha-lab-phase7
```

Expected: image builds, container starts without secrets, `/health` returns research-only status, and the container stops cleanly.

### Task 6: Frontend Smoke And Unified GitHub CI

**Files:**
- Modify: `apps/serenity-web/playwright.config.ts`
- Modify: `.github/workflows/verify.yml`
- Modify: `tests/test_release_gate.py`

- [ ] **Step 1: Add failing workflow and Playwright config tests**

```python
def test_verify_workflow_runs_one_release_gate_for_pr_branch_and_tags():
    workflow = Path(".github/workflows/verify.yml").read_text(encoding="utf-8")
    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert "actions/setup-node@" in workflow
    assert "npm ci" in workflow
    assert "playwright install --with-deps chromium" in workflow
    assert "scripts/verify_offline_release.py" in workflow
    assert "SERENITY_RESEARCH_AGENTS_ENABLED: \"false\"" in workflow
    assert "SERENITY_RESEARCH_BOT_ENABLED: \"false\"" in workflow
```

- [ ] **Step 2: Run red workflow test**

Run: `python3 -m pytest tests/test_release_gate.py::test_verify_workflow_runs_one_release_gate_for_pr_branch_and_tags -q`

Expected: FAIL because Node/frontend/release-gate steps are absent.

- [ ] **Step 3: Make Playwright select Chromium in CI**

Update the project configuration so:

```typescript
const browserUse = process.env.CI
  ? { ...devices['Desktop Chrome'] }
  : { ...devices['Desktop Chrome'], channel: 'msedge' };
```

The single smoke project must use `browserUse`.

- [ ] **Step 4: Expand the verification workflow**

The workflow must:

1. set up Python 3.11 and Node 20;
2. install pytest and the package;
3. run `npm ci`;
4. install Chromium for Playwright;
5. set Agent/Bot/notifications/providers disabled;
6. run `PYTHONPATH=src python3 scripts/verify_offline_release.py`;
7. run Docker build/no-secret health smoke in a separate job or release-gate check;
8. preserve the same gate for pull requests, branch pushes, and tag pushes.

- [ ] **Step 5: Run frontend and workflow verification**

Run:

```bash
cd apps/serenity-web && npm test -- --run
cd apps/serenity-web && npm run build
cd apps/serenity-web && npm run test:smoke -- --reporter=line
python3 -m pytest tests/test_release_gate.py -q
```

Expected: all pass.

### Task 7: Full Verification, Documentation, And Owned Commits

**Files:**
- Modify: `docs/serenity-led-dsa-full-migration-tracker.md`
- Modify: `tasks/todo.md`
- Modify: `tasks/lessons.md`
- Review all Phase 7 files.

- [ ] **Step 1: Run focused Phase 7 regression**

Run:

```bash
python3 -m pytest \
  tests/test_research_agents.py \
  tests/test_research_bot.py \
  tests/test_desktop_runtime.py \
  tests/test_release_gate.py \
  tests/test_app_api.py \
  tests/test_analysis_pipeline.py \
  tests/test_analysis_report.py \
  tests/test_dsa_migration_boundaries.py -q
```

Expected: PASS.

- [ ] **Step 2: Run static and safety checks**

Run:

```bash
python3 -m py_compile \
  src/serenity_alpha_lab/agents/*.py \
  src/serenity_alpha_lab/bot/*.py \
  src/serenity_alpha_lab/desktop_runtime.py \
  src/serenity_alpha_lab/release_gate.py \
  scripts/verify_offline_release.py
rg -n "daily_stock_analysis|/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis" src/serenity_alpha_lab scripts docker apps/serenity-web .github/workflows
rg -n "operation_advice|target_price|position_sizing|stop_loss|take_profit|sniper_points|broker|order_placement" src/serenity_alpha_lab/agents src/serenity_alpha_lab/bot src/serenity_alpha_lab/desktop_runtime.py
git diff --check
```

Expected: compile succeeds; DSA runtime/path scan has no matches; trading scan matches only fixed forbidden-field constants/tests where intentional; diff check passes.

- [ ] **Step 3: Run full backend and frontend verification**

Run:

```bash
make verify
make frontend-test
make frontend-build
make frontend-smoke
PYTHONPATH=src python3 scripts/verify_offline_release.py
```

Expected: all required checks pass with fresh output.

- [ ] **Step 4: Verify protected output state is unchanged**

Run:

```bash
git status --short output/ui
git diff -- output/ui/analyses/manifest.json output/ui/reports/deliverable-research-report.md output/ui/runs.json
```

Expected: only the pre-existing protected local dirt remains; Phase 7 made no intentional changes.

- [ ] **Step 5: Perform independent specification and quality review**

Review:

- every approved design requirement maps to an implementation/test;
- no external Bot/LLM/updater/platform adapter was added;
- no protected generated file is staged;
- Docker and health payloads contain no secrets;
- CI uses the same release gate for PR/branch/tag;
- desktop packaging remains explicitly deferred.

- [ ] **Step 6: Update tracker, task review, lessons, and restart prompt**

Record:

- red/green evidence;
- focused and full verification output;
- Docker availability/result;
- final Phase 7 files and boundaries;
- latest implementation and handoff commit IDs;
- next unfinished migration or hardening task;
- protected file exclusions.

- [ ] **Step 7: Commit implementation files only**

Run `git add` with an explicit Phase 7 file list. Do not use `git add .`.

Commit message:

```text
feat: 完成 Serenity Phase 7 研究运行与发布能力迁移
```

- [ ] **Step 8: Commit closeout documentation only**

After implementation commit, refresh tracker/restart prompt with the actual commit ID and commit only owned documentation:

```text
docs: 记录 Phase 7 研究运行与发布迁移交接
```
