# Input Fetch Report Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete only `SAL-P6-004` by adding framework-neutral URL/fetch policy, upload scanning contracts, report rendering safety validation and security headers.

**Architecture:** Add a small application-layer `input_fetch_security` contract that does not fetch, scan files from disk, call providers, register routes or start runtime loops. Reuse the trusted report renderer output but validate report display HTML and source links before presenter payloads leave the application boundary. Keep URL, upload and report hardening deterministic and auditable.

**Tech Stack:** Python dataclasses/enums/stdlib URL/IP parsing, pytest contract tests, existing `RenderedResearchReport` / `ResearchReportPagePresenter`, architecture import guards.

---

### Task 1: URL And Upload Security Contracts

**Files:**
- Create: `src/serenity_alpha_lab/application/input_fetch_security.py`
- Create: `tests/application/test_input_fetch_report_security.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`

- [x] **Step 1: Write failing tests for URL and upload policy**

Add tests that import `UrlFetchPolicy`, `UrlFetchHop`, `UrlFetchCandidate`, `FileUploadPolicy`, `FileUploadCandidate`, `InputSecurityDecisionStatus` and `InputSecurityIssueCode`.

Expected behavior:
- `UrlFetchPolicy.default(allowed_hosts=("reports.example.com",))` allows only HTTPS public hosts in the allowlist with caller-provided public resolved IPs.
- It denies `file://`, plain HTTP, URL credentials, localhost/private/link-local/metadata IPs, unapproved hosts, redirect chains that land on unsafe hosts and chains longer than the limit.
- It denies responses over the configured byte cap or with disallowed content types.
- `FileUploadPolicy.default()` allows small `.pdf`, `.txt`, `.csv` and `.json` inputs with matching content types, records SHA-256 of the supplied sample and sanitized filename.
- It denies path traversal filenames, oversized files, dangerous extensions/content types and executable/script signatures in supplied sample bytes.

- [x] **Step 2: Run focused Red**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_input_fetch_report_security.py -q
```

Expected: collection fails because `serenity_alpha_lab.application.input_fetch_security` does not exist.

- [x] **Step 3: Implement minimal contracts**

Create `input_fetch_security.py` with:
- `INPUT_FETCH_REPORT_SECURITY_CONTRACT_VERSION = "security.input_fetch_report_hardening@1.0.0"`
- `InputSecurityDecisionStatus`, `InputSecurityIssueCode`, `InputSecurityIssue`
- `UrlFetchHop`, `UrlFetchCandidate`, `UrlFetchPolicy`, `UrlFetchPolicyDecision`
- `FileUploadCandidate`, `FileUploadPolicy`, `FileUploadScanResult`
- deterministic `to_record()` and decision hashes

Do not import `requests`, `httpx`, `fastapi`, cloud SDKs, file scanners, Provider SDKs, LLM libraries, Qlib or SQLAlchemy.

- [x] **Step 4: Run focused Green**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_input_fetch_report_security.py -q
```

Expected: URL and upload policy tests pass.

### Task 2: Report Rendering And Delivery Safety

**Files:**
- Modify: `src/serenity_alpha_lab/application/input_fetch_security.py`
- Modify: `src/serenity_alpha_lab/application/report_delivery.py`
- Modify: `tests/application/test_input_fetch_report_security.py`
- Modify: `tests/application/test_report_delivery_ui.py`

- [x] **Step 1: Write failing report safety tests**

Add tests that verify:
- `ReportRenderSecurityPolicy.default().validate(rendered_report)` allows the existing trusted renderer output.
- It denies active HTML (`<script>`, `<iframe>`, event handler attributes, `javascript:` links and data links).
- `ResearchReportPagePresenter` rejects unsafe `rendered_report.html` and strips unsafe `source_link` values from evidence summaries while keeping safe `artifact://` and `https://` links.
- `ResearchReportPagePresenter` returns security headers: CSP, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`, and `Permissions-Policy`.

- [x] **Step 2: Run focused Red**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_input_fetch_report_security.py tests/application/test_report_delivery_ui.py -q
```

Expected: failures for missing report security policy and missing hardened presenter behavior.

- [x] **Step 3: Implement report security**

Extend `input_fetch_security.py` with:
- `ReportRenderSecurityPolicy`
- `ReportRenderSecurityDecision`
- `default_report_security_headers()`
- safe link checking for `https://` and `artifact://`
- active HTML checks without parsing trusted Markdown as authority

Update `ResearchReportPagePresenter` to:
- accept an optional `report_security_policy`
- validate `RenderedResearchReport.html` before building the page
- sanitize evidence `source_link` values into safe links plus deterministic security issue metadata
- merge default security headers into page headers

- [x] **Step 4: Run focused Green**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_input_fetch_report_security.py tests/application/test_report_delivery_ui.py -q
```

Expected: all focused tests pass.

### Task 3: Exports, Evidence Docs And Verification

**Files:**
- Modify: `src/serenity_alpha_lab/application/__init__.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`
- Create: `docs/input-fetch-report-hardening.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Export public symbols and architecture guard**

Export the new security symbols from `serenity_alpha_lab.application`. Add `test_input_fetch_security_stays_framework_neutral_and_runtime_free` with an explicit allowed import list.

- [x] **Step 2: Add evidence doc**

Create `docs/input-fetch-report-hardening.md` describing URL policy, upload scanning metadata, report HTML/link validation, security headers, non-goals and verification evidence.

- [x] **Step 3: Update progress and status**

Mark only `SAL-P6-004` complete. Advance P6 to `4/23`, total to `110/129`, keep G6 unpassed and set `SAL-P6-005` as next. Record subagent fallback due wrapper rejection.

- [x] **Step 4: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_input_fetch_report_security.py tests/application/test_report_delivery_ui.py tests/application/test_agent_tool_security.py tests/evidence/test_source_trust_cleaning.py tests/evidence/test_report_renderer.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

Expected: all tests/checks pass; immutable upstream tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

- [x] **Step 5: Commit**

Stage only relevant files and create a Chinese checkpoint commit:

```bash
git add src/serenity_alpha_lab/application/input_fetch_security.py src/serenity_alpha_lab/application/report_delivery.py src/serenity_alpha_lab/application/__init__.py tests/application/test_input_fetch_report_security.py tests/application/test_report_delivery_ui.py tests/architecture/test_architecture_boundaries.py docs/input-fetch-report-hardening.md docs/development-progress-checklist.md docs/development-status.md tasks/todo.md docs/superpowers/plans/2026-07-31-input-fetch-report-hardening.md
git commit -m "feat(P6): 加固输入抓取与报告渲染"
```
