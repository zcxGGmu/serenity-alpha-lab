# Source Trust and Unstructured Cleaning

> Task: `SAL-P5-004` Implement Source Trust and Unstructured Cleaning<br>
> Date: 2026-07-26<br>
> Status: `APPROVED FOR SAL-P5-005 / SAL-P5-006 INPUT ONLY`

## Conclusion

`SAL-P5-004` adds a pure offline source trust and unstructured-text cleaning boundary:

```text
src/serenity_alpha_lab/evidence/source_trust.py
tests/evidence/test_source_trust_cleaning.py
```

The policy consumes caller-provided source metadata and raw text, canonicalizes URL identity, computes deterministic URL/body hashes, assigns an evidence trust level, removes external prompt/tool instructions from prompt-safe text and records explicit trust/time/conflict issues. It is designed as an input guard for later intel/reporting stages, not as a fetcher or Agent executor.

This task does not fetch announcements, news, search results or social content; does not execute Evidence Agent stages; does not call real Providers or LLMs; does not start Worker loops, Qlib runtime, production scheduling, citation validation, report rendering or formal portfolio backtest promotion.

## Contracts

| Item | Contract |
|---|---|
| Trust contract | `research.source_trust@1.0.0` |
| Trust schema | `research.source_trust` / `1.0.0` |
| Policy | `SourceTrustPolicy.default()` |
| Input | `UnstructuredSourceInput` |
| Verdict | `SourceTrustVerdict` |
| Source types | `official_disclosure`, `regulatory_filing`, `company_announcement`, `wire_news`, `news`, `search_result`, `social_post`, `unknown` |
| Issue severity | `info`, `warning`, `malicious` |

## Trust Policy

Default trust mapping:

| Source type | Trust | Strong claim by itself |
|---|---|---|
| `official_disclosure` | `authoritative` | Yes |
| `regulatory_filing` | `authoritative` | Yes |
| `company_announcement` | `high` | Yes |
| `wire_news` | `high` | Yes |
| `news` | `medium` | Yes unless time/instruction issues exist |
| `search_result` | `medium` | Yes unless time/instruction issues exist; corroboration still required |
| `social_post` | `low` | No |
| `unknown` | `untrusted` | No |

Low and untrusted sources emit `low_trust_requires_corroboration`, set `corroboration_required=true` and `strong_claim_allowed=false`. Later Claim/report stages must not use those sources alone to support strong conclusions.

## Cleaning Rules

The cleaner normalizes line endings and whitespace, then removes lines that look like external instructions rather than market facts. Detected examples include:

- attempts to ignore/disregard prior, system or developer instructions
- references to system/developer prompts
- requests to call, run, use or invoke tools/functions/APIs/shells
- `admin=true` / `root=true` style escalation hints
- requests to reveal prompts, instructions, secrets or tokens

Removed lines are replaced with `[REMOVED_EXTERNAL_INSTRUCTION]`. The raw body is never emitted by `to_prompt_safe_record()`, which exposes only prompt-safe `cleaned_body`, hashes, trust labels and issue metadata.

## Hashing and Time

URL canonicalization lowercases scheme/host, removes fragments, strips tracking query parameters such as `utm_*`, `fbclid` and `gclid`, sorts remaining query parameters and normalizes path encoding. The policy computes:

- `url_hash`: SHA-256 of the canonical URL.
- `raw_body_hash`: SHA-256 of normalized raw body text.
- `cleaned_body_hash`: SHA-256 of prompt-safe cleaned body text.

`published_at`, `observed_at` and `available_at` must be timezone-aware. If observed/available timestamps precede publication or availability precedes observation, the verdict emits `time_conflict`, requires corroboration and disallows strong claims until a later stage resolves the conflict.

## Non-Goals

- No live web, search, social, Provider SDK or browser fetching.
- No Evidence Store write integration or automatic `EvidenceRecord` creation.
- No EvidenceBundle rank changes beyond exposing trust metadata for later tasks.
- No Quant Evidence Adapter, Prompt/Output Schema Registry, Agent stage, model routing, budget execution or citation repair loop.
- No real Provider calls, real LLM calls, Worker loop, Qlib runtime, production scheduler, report renderer or notification workflow.
- No change to legacy DSA `/api/v1/backtest/*` Signal Evaluation behavior.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_source_trust_cleaning.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence.source_trust'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_source_trust_cleaning.py -q` -> `5 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/evidence/test_source_trust_cleaning.py tests/evidence/test_evidence_schema_contract.py tests/repositories/test_evidence_store.py tests/application/test_evidence_bundle_builder.py tests/architecture/test_architecture_boundaries.py -q` -> `33 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `423 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves offline source trust and prompt-safe unstructured cleaning as input to `SAL-P5-005` Quant Evidence Adapter and `SAL-P5-006` Prompt/Output Schema Registry. Later P5 tasks must still implement Quant evidence production, prompt/schema registry, Agent stages, citation validation, model budgeting and renderers before Gate G5 can pass.
