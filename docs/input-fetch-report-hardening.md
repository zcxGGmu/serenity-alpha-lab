# Input Fetch And Report Rendering Hardening

> Task: `SAL-P6-004` Harden input, fetch and report rendering<br>
> Date: 2026-07-31<br>
> Status: `APPROVED FOR SAL-P6-005 INPUT ONLY`

## Conclusion

`SAL-P6-004` adds a framework-neutral security contract for user input, external fetch metadata and trusted report display output:

```text
src/serenity_alpha_lab/application/input_fetch_security.py
tests/application/test_input_fetch_report_security.py
```

The implementation freezes `security.input_fetch_report_hardening@1.0.0` and covers URL/fetch policy decisions, caller-provided redirect and DNS metadata validation, file upload metadata scanning, trusted report HTML safety validation, safe source-link filtering and default report security headers. It does not perform live fetches, DNS lookups, file parsing, antivirus scanning, Provider/LLM calls, Worker execution, Qlib initialization, notification sending, production scheduling, release packaging or formal portfolio backtest promotion.

## Contracts

| Item | Contract |
|---|---|
| Contract version | `security.input_fetch_report_hardening@1.0.0` |
| Schema | `security.input_fetch_report_hardening` / `1.0.0` |
| URL policy | `UrlFetchPolicy` |
| URL input | `UrlFetchCandidate` / `UrlFetchHop` |
| Upload policy | `FileUploadPolicy` / `FileUploadCandidate` |
| Report policy | `ReportRenderSecurityPolicy` |
| Security headers | `default_report_security_headers()` |
| Decision status | `allowed` / `denied` |

## URL And Fetch Policy

`UrlFetchPolicy` is metadata-only. Callers must provide the requested URL, all redirect hops, resolved IP addresses, response content type and response size before any runtime adapter performs a fetch. The default policy:

- allows only `https://` URLs;
- requires explicit public DNS resolution metadata;
- blocks credentials, local hostnames, private/loopback/link-local/metadata/reserved IPs and unapproved hosts;
- evaluates every redirect hop and enforces a bounded redirect count;
- enforces response byte and content-type limits;
- emits deterministic issue records and decision hashes.

This contract closes the policy gap left by `SAL-P5-014` Agent Tool Security: Agent tool authorization remains offline and metadata-driven, while future fetch adapters must present their concrete redirect/DNS/response metadata to this policy before reading external content.

## Upload Policy

`FileUploadPolicy.default()` accepts only small `.pdf`, `.txt`, `.csv` and `.json` uploads with matching content types. The policy normalizes a safe basename, computes a SHA-256 hash over the supplied sample bytes and denies:

- path traversal or control-character filenames;
- oversized files;
- forbidden extensions or content types;
- executable, script or active-markup signatures in the caller-provided sample.

This is not a full antivirus engine. Runtime upload handlers still need sandboxed parsing and production malware scanning in later release work, but they now have a deterministic contract for first-line rejection and audit metadata.

## Report Rendering Safety

`ReportRenderSecurityPolicy` validates `RenderedResearchReport.html` before the `ResearchReportPagePresenter` builds a page payload. It blocks active tags, inline event handlers, `srcdoc`, `javascript:` / unsafe data links and local/private HTTP targets. `ResearchReportPagePresenter` now:

- rejects unsafe trusted-renderer display HTML with a structured `ReportDeliveryError`;
- keeps `RenderedResearchReport.trusted_report.authoritative_json` as the only authority;
- preserves safe `artifact://` and public `https://` source links;
- removes unsafe `source_link` values from evidence summaries and records deterministic `source_link_security` metadata;
- attaches default security headers including CSP, `nosniff`, `DENY` framing and restricted permissions.

Markdown and HTML remain derived display strings and are not parsed back into source data.

## Non-Goals

- No live web, search, social, Provider SDK, browser, DNS or HTTP client fetching.
- No real file upload endpoint, storage adapter, antivirus engine or sandbox parser.
- No FastAPI route/middleware registration or frontend settings page.
- No Agent/tool execution, Citation repair loop, Evidence Store write, notification sender, Worker loop, Qlib runtime, production scheduler, release packaging or formal portfolio backtest promotion.
- No change to DSA `upstream/dsa-v3.26.1` tag or upstream runtime behavior.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_input_fetch_report_security.py -q` failed during collection with missing `serenity_alpha_lab.application.input_fetch_security` (`1 error`) before implementation. |
| Focused Green | `uv run --extra core --extra dev python -m pytest tests/application/test_input_fetch_report_security.py tests/application/test_report_delivery_ui.py -q`: `6 passed in 0.40s`. |
| Architecture / focused security | `uv run --extra core --extra dev python -m pytest tests/application/test_input_fetch_report_security.py tests/application/test_report_delivery_ui.py tests/architecture/test_architecture_boundaries.py::test_input_fetch_security_stays_framework_neutral_and_runtime_free tests/architecture/test_architecture_boundaries.py::test_report_delivery_ui_stays_offline_and_runtime_free -q`: `8 passed in 0.40s`. |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/application/test_input_fetch_report_security.py tests/application/test_report_delivery_ui.py tests/application/test_agent_tool_security.py tests/evidence/test_source_trust_cleaning.py tests/evidence/test_report_renderer.py tests/architecture/test_architecture_boundaries.py -q`: `53 passed in 0.88s`. |
| Full suite | `uv run --extra core --extra dev python -m pytest -q`: `520 passed, 3 skipped in 3.57s`. |
| Compile / lock / tag / diff | `compileall` PASS; dependency lock guard PASS (`Resolved 298 packages`); immutable tag `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS. |

## Approval Record

This record approves framework-neutral input/fetch/report-rendering hardening as input to `SAL-P6-005` security and supply-chain gates only. Real fetch adapters, upload endpoints, production malware scanning, notification sender, Worker runtime, Qlib runtime and release packaging still require later P6 tasks and profile-guarded runtime evidence.
