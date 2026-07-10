# Post-Migration Runtime Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Serenity Web fixture-only production path with a versioned, read-only canonical stock-analysis artifact API and a strict frontend loader while preserving evidence-first research semantics, provenance, readiness, source coverage, skeptical review, report safety, and research-only guardrails.

**Architecture:** Extend the existing Serenity-owned stock-analysis manifest, validate it through a pure allowlisted repository, and expose only normalized latest-summary, validated manifest, and Markdown endpoints from the local API. The React application consumes the summary through a strict decoder and injectable source, owns loading/ready/unavailable/blocked lifecycle states, and never falls back to the sample fixture in production.

**Tech Stack:** Python 3.11+ / dataclasses / standard-library `http.server` / JSON + Markdown artifacts / pytest / TypeScript 5.9 / React 19 / Vite 7 / Vitest 4 / Testing Library / Playwright 1.58.

---

## File Structure

- Modify: `src/serenity_alpha_lab/analysis/report.py`
  - Generates one timestamp for Markdown and manifest, writes the versioned canonical manifest, and builds deterministic skeptical-review data.
- Modify: `tests/test_analysis_report.py`
  - Proves the manifest contains the approved runtime semantics and preserves key-claim provenance and report safety.
- Create: `src/serenity_alpha_lab/app/stock_analysis_artifacts.py`
  - Defines the pure read-only artifact repository, normalized summary DTO, recursive forbidden-key guard, path containment checks, and sanitized artifact errors.
- Create: `tests/test_stock_analysis_artifacts.py`
  - Covers valid normalization, unsupported schemas, missing semantics, provenance failures, forbidden fields, path escape, and sanitized errors without starting an HTTP server.
- Modify: `src/serenity_alpha_lab/app/config.py`
  - Adds `stock_analysis_artifact_dir`, defaulting to `output/stock-analysis`.
- Modify: `src/serenity_alpha_lab/app/local_api.py`
  - Adds the latest summary, manifest, and Markdown routes with stable status codes, content types, and no-store caching.
- Modify: `src/serenity_alpha_lab/app/__init__.py`
  - Exports artifact repository contracts needed by focused tests and future runtime composition.
- Modify: `src/serenity_alpha_lab/cli.py`
  - Adds `serve-app --stock-analysis-artifact-dir` and passes it into `AppRuntimeConfig`.
- Modify: `tests/test_app_api.py`
  - Covers the three HTTP endpoints, stable error envelope, no local-path leakage, no raw exception leakage, and compatibility of `/health`, `/version`, and `/run-state`.
- Modify: `tests/test_cli.py`
  - Covers the new CLI option without introducing static Web hosting.
- Modify: `apps/serenity-web/src/types.ts`
  - Separates wire-independent UI status unions and replaces fixture-only coverage and safety shapes with the canonical view model.
- Create: `apps/serenity-web/src/artifacts/canonicalReportArtifact.ts`
  - Defines the canonical snake_case wire contract, strict decoder, recursive forbidden-key validation, safe href checks, and snake_case-to-camelCase adapter.
- Create: `apps/serenity-web/src/artifacts/canonicalReportArtifact.test.ts`
  - Covers valid non-AAPL decoding and all fail-closed semantic requirements.
- Create: `apps/serenity-web/src/artifacts/reportArtifactSource.ts`
  - Defines `ReportArtifactSource`, production HTTP loading, stable blocked/unavailable errors, and response sanitization.
- Create: `apps/serenity-web/src/artifacts/reportArtifactSource.test.ts`
  - Covers relative endpoint use, `AbortSignal`, HTTP classification, invalid JSON, and sanitized network failures.
- Modify: `apps/serenity-web/src/App.tsx`
  - Accepts an injectable source and owns loading, ready, unavailable, blocked, retry, and stale-request handling.
- Create: `apps/serenity-web/src/App.test.tsx`
  - Covers the complete asynchronous lifecycle and proves blocked output has no artifact links.
- Modify: `apps/serenity-web/src/main.tsx`
  - Injects the production HTTP source and contains no sample fixture import.
- Move test data from: `apps/serenity-web/src/data/sampleReportArtifact.ts`
- Create: `apps/serenity-web/src/test/fixtures/reportArtifacts.ts`
  - Keeps canonical wire and projected view-model fixtures under the test-only tree.
- Modify: `apps/serenity-web/src/components/ReportSemanticsPanel.tsx`
  - Renders actual evidence, focus, primary, risk, and external-source counts plus structured coverage and safety findings.
- Modify: `apps/serenity-web/src/components/ReportSemantics.test.tsx`
  - Uses the test fixture and keeps provenance and forbidden-language regression coverage.
- Modify: `apps/serenity-web/src/pages/HistoryPage.tsx`
  - Labels the page as the latest available artifact rather than a complete history collection.
- Modify: `apps/serenity-web/src/styles.css`
  - Adds stable loading, unavailable, and blocked state styling without changing the product shell.
- Modify: `apps/serenity-web/vite.config.ts`
  - Proxies relative `/api` requests to `http://127.0.0.1:8010` in development.
- Modify: `apps/serenity-web/e2e/app-shell.spec.ts`
  - Intercepts the canonical endpoint with a non-AAPL response and proves Home, Analysis, History, and Report Reader use API data.
- Modify during closeout: `docs/serenity-led-dsa-full-migration-plan.md`
  - Reconciles the historical Phase 0-7 completion markers and replaces the obsolete Phase 0 immediate-next-step text.
- Modify during closeout: `docs/serenity-led-dsa-full-migration-tracker.md`
  - Records planning completion, implementation status, validation evidence, commits, blockers, deferred scope, and the copyable restart prompt.
- Modify during closeout: `tasks/todo.md`
  - Mirrors this plan as a checkable implementation sequence and records the planning review.
- Modify during closeout: `tasks/lessons.md`
  - Records the distinction between planning baselines and implementation evidence.
- Do not modify, stage, revert, or overwrite:
  - `output/ui/analyses/manifest.json`
  - `output/ui/reports/deliverable-research-report.md`
  - `output/ui/runs.json`
  - `output/ui/analyses/topic-2bde5fabbc/`

## Locked Contract Decisions

The implementation must use these exact public contracts unless a new approved design supersedes this plan.

### Canonical Summary DTO

```json
{
  "schema_version": 1,
  "artifact_type": "stock_analysis_report",
  "symbol": "MSFT",
  "stock_name": "Microsoft Corporation",
  "query": "MSFT market data research",
  "generated_at": "2026-07-10T00:00:00+00:00",
  "research_only": true,
  "readiness": {
    "status": "ready",
    "reason": "readiness_ready",
    "flags": []
  },
  "report_gate": {
    "status": "available",
    "reason": "readiness_ready",
    "research_only": true
  },
  "source_coverage": {
    "status": "ready",
    "focus_ticker": "MSFT",
    "evidence_count": 4,
    "focus_evidence_count": 4,
    "primary_count": 3,
    "risk_count": 1,
    "methodology_share": 0.0,
    "placeholder_share": 0.0,
    "external_non_serenity_count": 0,
    "flags": []
  },
  "skeptical_review": {
    "summary": "Risk coverage uses 1 risk or invalidation evidence item.",
    "counter_thesis": [
      "MSFT closed at 408.2 on 2026-07-08"
    ]
  },
  "reports": {
    "stock_analysis": "/api/artifacts/stock-analysis/latest/report",
    "manifest": "/api/artifacts/stock-analysis/latest/manifest"
  },
  "safety": {
    "passed": true,
    "boundary": "research only; not investment advice",
    "findings": []
  },
  "key_claims": []
}
```

The browser must display real coverage counts. It must not derive a fixture-only `required` count or synthesize thresholds that are absent from the backend.

### Stable Error Envelope

```json
{
  "error": {
    "code": "artifact_not_found",
    "reason": "stock_analysis_artifact_missing"
  }
}
```

Allowed HTTP classifications:

- `404` with `artifact_not_found`;
- `409` with `artifact_blocked`;
- `422` with `artifact_invalid`.

The response must not include exception text, raw manifest fragments, request-provided paths, repository paths, or absolute local filesystem paths.

### Backend Artifact Read Boundary

The repository may read only:

```text
<stock_analysis_artifact_dir>/analysis-report-manifest.json
<stock_analysis_artifact_dir>/reports/stock-analysis-report.md
```

The manifest may name the Markdown path, but the resolved target must remain inside the configured root and must equal the allowlisted report file after resolution. Browser query parameters or request bodies must never choose a filesystem path.

### Frontend Availability Classification

```ts
export type ArtifactAvailability =
  | { status: 'loading' }
  | { status: 'ready'; artifact: ReportArtifact }
  | { status: 'unavailable'; reason: string }
  | { status: 'blocked'; reason: string };
```

`404`, `422`, network failures, invalid JSON, decoder failures, and aborted initial loads map to sanitized `unavailable` states. `409` maps to `blocked`. Retry starts a fresh request and may move either state back to `loading`.

### Task 1: Versioned Canonical Manifest

**Files:**
- Modify: `tests/test_analysis_report.py`
- Modify after red: `src/serenity_alpha_lab/analysis/report.py`

- [ ] **Step 1: Add a deterministic generated timestamp fixture**

Add:

```python
from datetime import datetime, timezone


FIXED_GENERATED_AT = datetime(2026, 7, 10, 0, 0, tzinfo=timezone.utc)
```

- [ ] **Step 2: Write the failing versioned-manifest test**

```python
def test_write_stock_analysis_manifest_includes_runtime_parity_semantics(tmp_path) -> None:
    result = _ready_analysis()

    artifact = write_stock_analysis_report_artifacts(
        result,
        tmp_path,
        generated_at=FIXED_GENERATED_AT,
    )

    report_text = artifact.markdown_path.read_text(encoding="utf-8")
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))

    assert "**Generated:** 2026-07-10 00:00 UTC" in report_text
    assert manifest["schema_version"] == 1
    assert manifest["artifact_type"] == "stock_analysis_report"
    assert manifest["query"] == "AAPL market data research"
    assert manifest["generated_at"] == "2026-07-10T00:00:00+00:00"
    assert manifest["research_only"] is True
    assert manifest["readiness"] == {
        "status": result.readiness.status,
        "reason": result.report_gate.reason,
        "flags": result.readiness.flag_codes,
    }
    assert manifest["report_gate"] == result.report_gate.to_dict()
    assert manifest["source_coverage"]["status"] == result.readiness.status
    assert manifest["source_coverage"]["focus_ticker"] == "AAPL"
    assert manifest["source_coverage"]["evidence_count"] == len(result.evidence)
    assert manifest["source_coverage"]["primary_count"] == 3
    assert manifest["source_coverage"]["risk_count"] == 1
    assert manifest["source_coverage"]["flags"] == []
    assert manifest["skeptical_review"]["summary"] == (
        "Risk coverage uses 1 risk or invalidation evidence item."
    )
    assert manifest["skeptical_review"]["counter_thesis"] == [
        "AAPL closed at 41.1 on 2026-07-06"
    ]
    assert manifest["safety"]["boundary"] == "research only; not investment advice"
    assert all(claim["provenance_refs"] for claim in manifest["key_claims"])
```

- [ ] **Step 3: Write the failing missing-risk skeptical-review test**

```python
def test_write_stock_analysis_manifest_emits_missing_risk_counter_thesis(tmp_path) -> None:
    manager = StubMarketDataManager(
        quote_result(price=42.5),
        daily_bars(include_risk_bar=False),
    )
    result = StockAnalysisPipeline(market_data=manager).analyze(
        "AAPL",
        stock_name="Apple Inc.",
        query="AAPL market data research",
    )

    artifact = write_stock_analysis_report_artifacts(
        result,
        tmp_path,
        generated_at=FIXED_GENERATED_AT,
    )
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))

    assert manifest["source_coverage"]["risk_count"] == 0
    assert manifest["skeptical_review"]["summary"] == (
        "Risk coverage is incomplete because no risk or invalidation evidence item is available."
    )
    assert manifest["skeptical_review"]["counter_thesis"] == [
        "missing_risk_coverage: No negative, risk, or invalidation evidence was retrieved for AAPL."
    ]
```

- [ ] **Step 4: Run the manifest red tests**

Run:

```bash
python3 -m pytest \
  tests/test_analysis_report.py::test_write_stock_analysis_manifest_includes_runtime_parity_semantics \
  tests/test_analysis_report.py::test_write_stock_analysis_manifest_emits_missing_risk_counter_thesis \
  -q
```

Expected: FAIL because `write_stock_analysis_report_artifacts()` does not accept `generated_at` and the current manifest lacks the versioned runtime-parity fields.

- [ ] **Step 5: Implement one timestamp and deterministic skeptical review**

Change the public functions to:

```python
def render_stock_analysis_report_markdown(
    result: StockAnalysisResult,
    *,
    generated_at: datetime | None = None,
    additional_generated_sections: Mapping[str, str] | None = None,
) -> str:
    generated_at_value = generated_at or datetime.now(timezone.utc)
    generated_at_label = generated_at_value.strftime("%Y-%m-%d %H:%M UTC")
```

```python
def write_stock_analysis_report_artifacts(
    result: StockAnalysisResult,
    output_dir: str | Path,
    *,
    generated_at: datetime | None = None,
) -> StockAnalysisReportArtifact:
    generated_at_value = generated_at or datetime.now(timezone.utc)
    markdown = render_stock_analysis_report_markdown(
        result,
        generated_at=generated_at_value,
    )
```

Add pure helpers with these signatures:

```python
def build_source_coverage_summary(result: StockAnalysisResult) -> dict[str, object]:
    coverage = result.readiness.source_coverage
    flags = []
    for raw_flag in coverage.get("flags", []):
        if not isinstance(raw_flag, Mapping):
            continue
        flags.append(
            {
                "code": str(raw_flag.get("code", "")),
                "severity": str(raw_flag.get("severity", "")),
                "message": str(raw_flag.get("message", "")),
                "recommendation": str(raw_flag.get("recommendation", "")),
            }
        )
    return {
        "status": result.readiness.status,
        "focus_ticker": str(coverage.get("focus_ticker") or result.symbol),
        "evidence_count": int(coverage.get("evidence_count", 0)),
        "focus_evidence_count": int(coverage.get("focus_evidence_count", 0)),
        "primary_count": int(coverage.get("primary_count", 0)),
        "risk_count": int(coverage.get("risk_count", 0)),
        "methodology_share": float(coverage.get("methodology_share", 0.0)),
        "placeholder_share": float(coverage.get("placeholder_share", 0.0)),
        "external_non_serenity_count": int(
            coverage.get("external_non_serenity_count", 0)
        ),
        "flags": flags,
    }


def build_skeptical_review(result: StockAnalysisResult) -> dict[str, object]:
    risk_items = [
        item
        for item in result.evidence
        if str(item.get("claim_type")) in {"risk", "invalidation"}
        or str(item.get("direction")) == "negative"
    ]
    if risk_items:
        return {
            "summary": (
                f"Risk coverage uses {len(risk_items)} risk or invalidation "
                "evidence item."
            ),
            "counter_thesis": [
                str(item.get("claim", "")).strip()
                for item in risk_items
                if str(item.get("claim", "")).strip()
            ],
        }
    missing_risk = next(
        (
            flag
            for flag in result.readiness.source_coverage.get("flags", [])
            if isinstance(flag, Mapping)
            and flag.get("code") == "missing_risk_coverage"
        ),
        None,
    )
    diagnostic = (
        "missing_risk_coverage: "
        + str(missing_risk.get("message", "")).strip()
        if isinstance(missing_risk, Mapping)
        else "missing_risk_coverage: No risk evidence is available."
    )
    return {
        "summary": (
            "Risk coverage is incomplete because no risk or invalidation "
            "evidence item is available."
        ),
        "counter_thesis": [diagnostic],
    }
```

`build_source_coverage_summary()` must copy the allowlisted fields already present in `result.readiness.source_coverage`, preserve finite numeric values, add `status=result.readiness.status`, and convert the structured coverage flags into:

```python
[
    {
        "code": flag["code"],
        "severity": flag["severity"],
        "message": flag["message"],
        "recommendation": flag["recommendation"],
    }
]
```

`build_skeptical_review()` must:

1. select evidence with `claim_type in {"risk", "invalidation"}` or `direction == "negative"`;
2. use each selected evidence claim as a counter-thesis item;
3. when no risk evidence exists, use the `missing_risk_coverage` flag code and message;
4. never invent a risk conclusion or read an external source.

- [ ] **Step 6: Write the complete manifest payload**

Write exactly these top-level fields:

```python
manifest = {
    "schema_version": 1,
    "artifact_type": "stock_analysis_report",
    "symbol": result.symbol,
    "stock_name": result.stock_name,
    "query": result.context.query,
    "generated_at": generated_at_value.isoformat(),
    "research_only": result.research_only,
    "readiness": {
        "status": result.readiness.status,
        "reason": result.report_gate.reason,
        "flags": list(result.readiness.flag_codes),
    },
    "report_gate": result.report_gate.to_dict(),
    "source_coverage": build_source_coverage_summary(result),
    "skeptical_review": build_skeptical_review(result),
    "reports": {
        "stock_analysis": "reports/stock-analysis-report.md",
        "ui": "index.html",
    },
    "safety": {
        "passed": safety.passed,
        "boundary": "research only; not investment advice",
        "findings": [
            {
                "line_number": finding.line_number,
                "phrase": finding.phrase,
                "line": finding.line,
            }
            for finding in safety.findings
        ],
    },
    "key_claims": [claim.to_dict() for claim in key_claims],
}
```

- [ ] **Step 7: Run the manifest green tests**

Run:

```bash
python3 -m pytest tests/test_analysis_report.py -q
```

Expected: PASS.

- [ ] **Step 8: Run the focused report/pipeline/safety regression**

Run:

```bash
python3 -m pytest \
  tests/test_analysis_pipeline.py \
  tests/test_analysis_report.py \
  tests/test_report_safety.py \
  tests/test_dsa_migration_boundaries.py \
  -q
```

Expected: PASS with no external DSA runtime import and no unsupported actionability language.

- [ ] **Step 9: Commit the manifest contract**

```bash
git add src/serenity_alpha_lab/analysis/report.py tests/test_analysis_report.py
git diff --cached --check
git commit -m "feat: 完善版本化股票分析工件清单"
```

Before committing, confirm none of the protected `output/ui/*` paths is staged.

### Task 2: Pure Artifact Repository And Validation

**Files:**
- Create: `tests/test_stock_analysis_artifacts.py`
- Create after red: `src/serenity_alpha_lab/app/stock_analysis_artifacts.py`
- Modify after red: `src/serenity_alpha_lab/app/__init__.py`

- [ ] **Step 1: Add a focused canonical artifact fixture**

Create a test helper that writes:

```python
def write_canonical_artifact(root: Path, *, mutate=None) -> None:
    manifest = {
        "schema_version": 1,
        "artifact_type": "stock_analysis_report",
        "symbol": "MSFT",
        "stock_name": "Microsoft Corporation",
        "query": "MSFT market data research",
        "generated_at": "2026-07-10T00:00:00+00:00",
        "research_only": True,
        "readiness": {
            "status": "ready",
            "reason": "readiness_ready",
            "flags": [],
        },
        "report_gate": {
            "status": "available",
            "reason": "readiness_ready",
            "research_only": True,
        },
        "source_coverage": {
            "status": "ready",
            "focus_ticker": "MSFT",
            "evidence_count": 4,
            "focus_evidence_count": 4,
            "primary_count": 3,
            "risk_count": 1,
            "methodology_share": 0.0,
            "placeholder_share": 0.0,
            "external_non_serenity_count": 0,
            "flags": [],
        },
        "skeptical_review": {
            "summary": "Risk coverage uses 1 risk or invalidation evidence item.",
            "counter_thesis": ["MSFT closed lower on 2026-07-08."],
        },
        "reports": {
            "stock_analysis": "reports/stock-analysis-report.md",
            "ui": "index.html",
        },
        "safety": {
            "passed": True,
            "boundary": "research only; not investment advice",
            "findings": [],
        },
        "key_claims": [
            {
                "claim_id": "claim:MSFT:readiness",
                "claim": "Readiness is ready.",
                "provenance_refs": [
                    {
                        "evidence_id": "serenity:market-data:MSFT:quote:2026-07-10",
                        "source_url": "serenity://market-data/MSFT/quote/2026-07-10",
                        "source_title": "MSFT quote",
                        "excerpt": "Normalized quote evidence.",
                    }
                ],
                "diagnostics": [],
            }
        ],
    }
    if mutate is not None:
        mutate(manifest)
    (root / "reports").mkdir(parents=True)
    (root / "analysis-report-manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (root / "reports" / "stock-analysis-report.md").write_text(
        "# MSFT Research Report\n",
        encoding="utf-8",
    )
```

- [ ] **Step 2: Write the failing valid-normalization test**

```python
def test_repository_returns_allowlisted_summary_and_validated_artifacts(tmp_path) -> None:
    write_canonical_artifact(tmp_path)
    repository = StockAnalysisArtifactRepository(tmp_path)

    summary = repository.load_latest_summary()
    manifest = repository.load_latest_manifest()
    report = repository.load_latest_report()

    assert summary["symbol"] == "MSFT"
    assert summary["reports"] == {
        "stock_analysis": "/api/artifacts/stock-analysis/latest/report",
        "manifest": "/api/artifacts/stock-analysis/latest/manifest",
    }
    assert "ui" not in summary["reports"]
    assert manifest["schema_version"] == 1
    assert report == "# MSFT Research Report\n"
    assert str(tmp_path) not in json.dumps(summary)
```

- [ ] **Step 3: Write the failing block/invalid/path tests**

Parameterize:

```python
@pytest.mark.parametrize(
    ("mutate", "status_code", "code", "reason"),
    [
        (
            lambda payload: payload.update(research_only=False),
            409,
            "artifact_blocked",
            "research_only_required",
        ),
        (
            lambda payload: payload["safety"].update(passed=False),
            409,
            "artifact_blocked",
            "report_safety_failed",
        ),
        (
            lambda payload: payload.pop("readiness"),
            422,
            "artifact_invalid",
            "readiness_missing",
        ),
        (
            lambda payload: payload.update(schema_version=2),
            422,
            "artifact_invalid",
            "schema_version_unsupported",
        ),
        (
            lambda payload: payload["key_claims"][0].update(provenance_refs=[]),
            422,
            "artifact_invalid",
            "key_claim_provenance_missing",
        ),
        (
            lambda payload: payload["reports"].update(stock_analysis="../secret.md"),
            422,
            "artifact_invalid",
            "report_path_invalid",
        ),
        (
            lambda payload: payload.update(nested={"operation_advice": "buy"}),
            422,
            "artifact_invalid",
            "forbidden_field",
        ),
    ],
)
def test_repository_fails_closed_with_sanitized_errors(
    tmp_path,
    mutate,
    status_code,
    code,
    reason,
) -> None:
    write_canonical_artifact(tmp_path, mutate=mutate)
    repository = StockAnalysisArtifactRepository(tmp_path)

    with pytest.raises(ArtifactRepositoryError) as exc_info:
        repository.load_latest_summary()

    assert exc_info.value.status_code == status_code
    assert exc_info.value.code == code
    assert exc_info.value.reason == reason
    assert str(tmp_path) not in str(exc_info.value)
```

Also add:

```python
def test_repository_reports_missing_and_invalid_json_without_raw_details(tmp_path) -> None:
    repository = StockAnalysisArtifactRepository(tmp_path)
    with pytest.raises(ArtifactRepositoryError) as missing:
        repository.load_latest_summary()
    assert missing.value.to_payload() == {
        "error": {
            "code": "artifact_not_found",
            "reason": "stock_analysis_artifact_missing",
        }
    }

    (tmp_path / "analysis-report-manifest.json").write_text("{", encoding="utf-8")
    with pytest.raises(ArtifactRepositoryError) as invalid:
        repository.load_latest_summary()
    assert invalid.value.to_payload() == {
        "error": {
            "code": "artifact_invalid",
            "reason": "manifest_json_invalid",
        }
    }
```

- [ ] **Step 4: Run the repository red tests**

Run:

```bash
python3 -m pytest tests/test_stock_analysis_artifacts.py -q
```

Expected: FAIL during collection because `serenity_alpha_lab.app.stock_analysis_artifacts` does not exist.

- [ ] **Step 5: Implement the repository contracts**

Create:

```python
@dataclass(frozen=True)
class ArtifactRepositoryError(ValueError):
    status_code: int
    code: str
    reason: str

    def __str__(self) -> str:
        return f"{self.code}:{self.reason}"

    def to_payload(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "reason": self.reason}}
```

```python
class StockAnalysisArtifactRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def load_latest_summary(self) -> dict[str, object]:
        manifest = self.load_latest_manifest()
        return _normalize_summary(manifest)

    def load_latest_manifest(self) -> dict[str, object]:
        manifest = _read_manifest(self.root)
        _validate_manifest(manifest, self.root)
        return _allowlisted_manifest(manifest)

    def load_latest_report(self) -> str:
        manifest = self.load_latest_manifest()
        report_path = _resolve_report_path(self.root, manifest)
        try:
            return report_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ArtifactRepositoryError(
                404,
                "artifact_not_found",
                "stock_analysis_report_missing",
            ) from exc
        except OSError as exc:
            raise ArtifactRepositoryError(
                422,
                "artifact_invalid",
                "stock_analysis_report_unreadable",
            ) from exc
```

The module must define fixed allowlists for every returned object. It must recursively reject keys containing or equal to:

```python
FORBIDDEN_FIELDS = {
    "operation_advice",
    "buy",
    "sell",
    "target_price",
    "price_target",
    "stop_loss",
    "take_profit",
    "position_size",
    "position_sizing",
    "broker",
    "order",
    "trade_action",
}
```

Do not reject legitimate prose merely because it contains a substring such as `research`. The recursive guard applies to keys and explicit action fields; report safety continues to govern generated text.

The validation sequence must be deterministic:

1. file exists and parses as a JSON object;
2. no recursively forbidden keys;
3. `schema_version == 1`;
4. `artifact_type == "stock_analysis_report"`;
5. required strings and finite numeric coverage values;
6. `research_only is True`;
7. `report_gate.research_only is True`;
8. `safety.passed is True`;
9. non-empty safety boundary contains `research only`;
10. readiness, report gate, source coverage, and skeptical review are complete;
11. every key claim has at least one complete provenance ref;
12. report path resolves inside the configured root and to `reports/stock-analysis-report.md`.

- [ ] **Step 6: Run the repository green tests**

Run:

```bash
python3 -m pytest tests/test_stock_analysis_artifacts.py -q
```

Expected: PASS.

- [ ] **Step 7: Run the repository and manifest regression**

Run:

```bash
python3 -m pytest \
  tests/test_analysis_report.py \
  tests/test_stock_analysis_artifacts.py \
  tests/test_dsa_migration_boundaries.py \
  -q
```

Expected: PASS.

- [ ] **Step 8: Commit the pure repository**

```bash
git add \
  src/serenity_alpha_lab/app/__init__.py \
  src/serenity_alpha_lab/app/stock_analysis_artifacts.py \
  tests/test_stock_analysis_artifacts.py
git diff --cached --check
git commit -m "feat: 添加只读股票分析工件仓库"
```

### Task 3: Read-Only Artifact API, Runtime Config, And CLI

**Files:**
- Modify: `tests/test_app_api.py`
- Modify: `tests/test_cli.py`
- Modify after red: `src/serenity_alpha_lab/app/config.py`
- Modify after red: `src/serenity_alpha_lab/app/local_api.py`
- Modify after red: `src/serenity_alpha_lab/cli.py`

- [ ] **Step 1: Add HTTP test helpers that preserve error status**

Add:

```python
import urllib.error


def _get_response(url: str) -> tuple[int, dict[str, str], bytes]:
    try:
        response = urllib.request.urlopen(url, timeout=5)
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()
    with response:
        return response.status, dict(response.headers.items()), response.read()
```

- [ ] **Step 2: Write the failing latest-summary, manifest, and Markdown API test**

```python
def test_local_api_serves_validated_latest_stock_analysis_artifacts(tmp_path) -> None:
    artifact_dir = tmp_path / "stock-analysis"
    write_canonical_artifact(artifact_dir)
    config = AppRuntimeConfig(
        runs_path=tmp_path / "runs.json",
        stock_analysis_artifact_dir=artifact_dir,
    )

    server = ThreadingHTTPServer(("127.0.0.1", 0), create_api_handler(config))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        summary_status, summary_headers, summary_body = _get_response(
            f"{base_url}/api/artifacts/stock-analysis/latest"
        )
        manifest_status, manifest_headers, manifest_body = _get_response(
            f"{base_url}/api/artifacts/stock-analysis/latest/manifest"
        )
        report_status, report_headers, report_body = _get_response(
            f"{base_url}/api/artifacts/stock-analysis/latest/report"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    summary = json.loads(summary_body)
    manifest = json.loads(manifest_body)
    assert summary_status == 200
    assert summary_headers["Cache-Control"] == "no-store"
    assert summary["symbol"] == "MSFT"
    assert summary["reports"]["stock_analysis"].startswith("/api/")
    assert summary["reports"]["manifest"].startswith("/api/")
    assert manifest_status == 200
    assert manifest_headers["Content-Type"].startswith("application/json")
    assert manifest["schema_version"] == 1
    assert report_status == 200
    assert report_headers["Content-Type"] == "text/markdown; charset=utf-8"
    assert report_body.decode("utf-8") == "# MSFT Research Report\n"
    rendered = "\n".join(
        [
            summary_body.decode(),
            manifest_body.decode(),
            report_body.decode(),
        ]
    ).lower()
    assert str(tmp_path).lower() not in rendered
    assert "/users/" not in rendered
```

- [ ] **Step 3: Write the failing status-classification tests**

Parameterize missing, blocked, invalid, and escaped artifacts:

```python
@pytest.mark.parametrize(
    ("prepare", "expected_status", "expected_code", "expected_reason"),
    [
        (
            lambda root: None,
            404,
            "artifact_not_found",
            "stock_analysis_artifact_missing",
        ),
        (
            lambda root: write_canonical_artifact(
                root,
                mutate=lambda payload: payload.update(research_only=False),
            ),
            409,
            "artifact_blocked",
            "research_only_required",
        ),
        (
            lambda root: write_canonical_artifact(
                root,
                mutate=lambda payload: payload["key_claims"][0].update(
                    provenance_refs=[]
                ),
            ),
            422,
            "artifact_invalid",
            "key_claim_provenance_missing",
        ),
        (
            lambda root: write_canonical_artifact(
                root,
                mutate=lambda payload: payload["reports"].update(
                    stock_analysis="../secret.md"
                ),
            ),
            422,
            "artifact_invalid",
            "report_path_invalid",
        ),
    ],
)
def test_local_api_returns_sanitized_artifact_errors(
    tmp_path,
    prepare,
    expected_status,
    expected_code,
    expected_reason,
) -> None:
    artifact_dir = tmp_path / "stock-analysis"
    prepare(artifact_dir)
    status, headers, body = _request_latest_artifact(artifact_dir, tmp_path)
    payload = json.loads(body)

    assert status == expected_status
    assert headers["Cache-Control"] == "no-store"
    assert payload == {
        "error": {
            "code": expected_code,
            "reason": expected_reason,
        }
    }
    assert str(tmp_path) not in body.decode("utf-8")
```

- [ ] **Step 4: Write the failing runtime-config and CLI tests**

Extend the config default test:

```python
assert config.stock_analysis_artifact_dir == Path("output/stock-analysis")
```

Extend `test_cli_serve_app_invokes_serenity_api_without_building_static_dashboard`:

```python
artifact_dir = tmp_path / "stock-analysis"

exit_code = main(
    [
        "serve-app",
        "--host",
        "0.0.0.0",
        "--port",
        "8123",
        "--runs-path",
        str(runs_path),
        "--dashboard-path",
        str(dashboard_path),
        "--stock-analysis-artifact-dir",
        str(artifact_dir),
    ]
)

assert config.stock_analysis_artifact_dir == artifact_dir
```

- [ ] **Step 5: Run the API/config/CLI red tests**

Run:

```bash
python3 -m pytest \
  tests/test_app_api.py \
  tests/test_cli.py::test_cli_serve_app_invokes_serenity_api_without_building_static_dashboard \
  -q
```

Expected: FAIL because `AppRuntimeConfig` lacks `stock_analysis_artifact_dir`, the CLI option is unknown, and the artifact routes return `404 not_found`.

- [ ] **Step 6: Implement runtime config and CLI wiring**

Add:

```python
@dataclass(frozen=True)
class AppRuntimeConfig:
    host: str = "127.0.0.1"
    port: int = 8010
    runs_path: Path = Path("output/ui/runs.json")
    dashboard_path: Path = Path("output/ui/index.html")
    stock_analysis_artifact_dir: Path = Path("output/stock-analysis")
```

Add to `build_serve_app_parser()`:

```python
parser.add_argument(
    "--stock-analysis-artifact-dir",
    default="output/stock-analysis",
    help="Read-only stock-analysis artifact directory exposed by the local API.",
)
```

Pass `Path(args.stock_analysis_artifact_dir)` into `AppRuntimeConfig`.

- [ ] **Step 7: Implement the three API routes**

Instantiate one repository inside `create_api_handler()`:

```python
repository = StockAnalysisArtifactRepository(
    config.stock_analysis_artifact_dir,
)
```

Route handling:

```python
if parsed.path == "/api/artifacts/stock-analysis/latest":
    self._send_json(repository.load_latest_summary())
    return
if parsed.path == "/api/artifacts/stock-analysis/latest/manifest":
    self._send_json(repository.load_latest_manifest())
    return
if parsed.path == "/api/artifacts/stock-analysis/latest/report":
    self._send_text(
        repository.load_latest_report(),
        content_type="text/markdown; charset=utf-8",
    )
    return
```

Catch only `ArtifactRepositoryError` around artifact routes:

```python
except ArtifactRepositoryError as exc:
    self._send_json(exc.to_payload(), status=exc.status_code)
    return
```

Add:

```python
def _send_text(
    self,
    text: str,
    *,
    content_type: str,
    status: int = 200,
) -> None:
    body = text.encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", content_type)
    self.send_header("Cache-Control", "no-store")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)
```

Keep `/health`, `/version`, `/run-state`, and the existing generic `not_found` behavior unchanged.

- [ ] **Step 8: Run the API/config/CLI green tests**

Run:

```bash
python3 -m pytest \
  tests/test_stock_analysis_artifacts.py \
  tests/test_app_api.py \
  tests/test_cli.py::test_cli_serve_app_invokes_serenity_api_without_building_static_dashboard \
  -q
```

Expected: PASS.

- [ ] **Step 9: Run backend parity regression**

Run:

```bash
python3 -m pytest \
  tests/test_analysis_pipeline.py \
  tests/test_analysis_report.py \
  tests/test_stock_analysis_artifacts.py \
  tests/test_app_api.py \
  tests/test_cli.py \
  tests/test_dsa_migration_boundaries.py \
  tests/test_report_safety.py \
  -q
```

Expected: PASS.

- [ ] **Step 10: Commit the API/config/CLI slice**

```bash
git add \
  src/serenity_alpha_lab/app/config.py \
  src/serenity_alpha_lab/app/local_api.py \
  src/serenity_alpha_lab/cli.py \
  tests/test_app_api.py \
  tests/test_cli.py
git diff --cached --check
git commit -m "feat: 暴露只读最新股票分析工件 API"
```

### Task 4: Strict Frontend Wire Decoder And View Model

**Files:**
- Modify: `apps/serenity-web/src/types.ts`
- Create: `apps/serenity-web/src/artifacts/canonicalReportArtifact.ts`
- Create: `apps/serenity-web/src/artifacts/canonicalReportArtifact.test.ts`
- Create: `apps/serenity-web/src/test/fixtures/reportArtifacts.ts`
- Remove after replacement: `apps/serenity-web/src/data/sampleReportArtifact.ts`
- Modify: `apps/serenity-web/src/components/ReportSemantics.test.tsx`

- [ ] **Step 1: Define separate UI status and finding types**

Replace the over-broad status and fixture-only coverage types with:

```ts
export type ReadinessStatus = 'ready' | 'needs_work' | 'blocked';
export type ReportGateStatus = 'available' | 'blocked';
export type SourceCoverageStatus = 'ready' | 'needs_work' | 'blocked';

export interface CoverageFlag {
  code: string;
  severity: string;
  message: string;
  recommendation: string;
}

export interface SafetyFinding {
  lineNumber: number;
  phrase: string;
  line: string;
}
```

The `ReportArtifact` view model must include:

```ts
export interface ReportArtifact {
  schemaVersion: 1;
  artifactType: 'stock_analysis_report';
  symbol: string;
  company: string;
  query: string;
  generatedAt: string;
  researchOnly: true;
  markdownHref: string;
  manifestHref: string;
  readiness: {
    status: ReadinessStatus;
    reason: string;
    flags: string[];
  };
  reportGate: {
    status: ReportGateStatus;
    reason: string;
    researchOnly: true;
  };
  sourceCoverage: {
    status: SourceCoverageStatus;
    focusTicker: string;
    evidenceCount: number;
    focusEvidenceCount: number;
    primaryCount: number;
    riskCount: number;
    methodologyShare: number;
    placeholderShare: number;
    externalNonSerenityCount: number;
    flags: CoverageFlag[];
  };
  safety: {
    passed: true;
    boundary: string;
    findings: SafetyFinding[];
  };
  skepticalReview: {
    summary: string;
    counterThesis: string[];
  };
  keyClaims: KeyClaim[];
}
```

- [ ] **Step 2: Move fixtures under the test tree**

Create both:

```ts
export const canonicalReportArtifactWireFixture = {
  schema_version: 1,
  artifact_type: 'stock_analysis_report',
  symbol: 'MSFT',
  stock_name: 'Microsoft Corporation',
  query: 'MSFT market data research',
  generated_at: '2026-07-10T00:00:00+00:00',
  research_only: true,
  readiness: {
    status: 'ready',
    reason: 'readiness_ready',
    flags: [],
  },
  report_gate: {
    status: 'available',
    reason: 'readiness_ready',
    research_only: true,
  },
  source_coverage: {
    status: 'ready',
    focus_ticker: 'MSFT',
    evidence_count: 4,
    focus_evidence_count: 4,
    primary_count: 3,
    risk_count: 1,
    methodology_share: 0,
    placeholder_share: 0,
    external_non_serenity_count: 0,
    flags: [],
  },
  skeptical_review: {
    summary: 'Risk coverage uses 1 risk or invalidation evidence item.',
    counter_thesis: ['MSFT closed lower on 2026-07-08.'],
  },
  reports: {
    stock_analysis: '/api/artifacts/stock-analysis/latest/report',
    manifest: '/api/artifacts/stock-analysis/latest/manifest',
  },
  safety: {
    passed: true,
    boundary: 'research only; not investment advice',
    findings: [],
  },
  key_claims: [
    {
      claim_id: 'claim:MSFT:readiness',
      claim: 'Readiness is ready.',
      provenance_refs: [
        {
          evidence_id: 'serenity:market-data:MSFT:quote:2026-07-10',
          source_url: 'serenity://market-data/MSFT/quote/2026-07-10',
          source_title: 'MSFT quote',
          excerpt: 'Normalized quote evidence.',
        },
      ],
      diagnostics: [],
    },
  ],
} as const;
```

and a projected `reportArtifactFixture` matching `ReportArtifact`.

- [ ] **Step 3: Write the failing valid-decoder test**

```ts
import { decodeCanonicalReportArtifact } from './canonicalReportArtifact';
import { canonicalReportArtifactWireFixture } from '../test/fixtures/reportArtifacts';

it('decodes and maps a valid canonical artifact without semantic loss', () => {
  const artifact = decodeCanonicalReportArtifact(
    canonicalReportArtifactWireFixture,
  );

  expect(artifact.symbol).toBe('MSFT');
  expect(artifact.company).toBe('Microsoft Corporation');
  expect(artifact.generatedAt).toBe('2026-07-10T00:00:00+00:00');
  expect(artifact.reportGate).toEqual({
    status: 'available',
    reason: 'readiness_ready',
    researchOnly: true,
  });
  expect(artifact.sourceCoverage).toMatchObject({
    evidenceCount: 4,
    primaryCount: 3,
    riskCount: 1,
  });
  expect(artifact.keyClaims[0].provenanceRefs[0].evidenceId).toBe(
    'serenity:market-data:MSFT:quote:2026-07-10',
  );
});
```

- [ ] **Step 4: Write the failing fail-closed decoder matrix**

Parameterize mutations for:

- unsupported or missing `schema_version`;
- wrong `artifact_type`;
- missing or false `research_only`;
- missing readiness, report gate, source coverage, skeptical review, safety, or reports;
- `safety.passed !== true`;
- missing research-only boundary;
- `report_gate.research_only !== true`;
- non-finite or negative coverage counts;
- non-finite coverage shares;
- empty key-claim provenance;
- incomplete provenance fields;
- unsafe report hrefs such as `https://example.com/report`, `file:///tmp/report`, `../report`, or `//example.com/report`;
- recursive forbidden keys such as `operation_advice`, `target_price`, `position_sizing`, `broker`, or `order`.

Use:

```ts
it.each(invalidCases)('rejects $name', ({ payload, message }) => {
  expect(() => decodeCanonicalReportArtifact(payload)).toThrow(message);
});
```

Expected error messages are stable decoder codes such as:

```text
schema_version_unsupported
research_only_required
report_safety_failed
source_coverage_invalid
key_claim_provenance_missing
artifact_href_invalid
forbidden_field
```

- [ ] **Step 5: Run the decoder red tests**

Run:

```bash
npm --prefix apps/serenity-web test -- \
  src/artifacts/canonicalReportArtifact.test.ts
```

Expected: FAIL because the decoder module and canonical UI types do not exist.

- [ ] **Step 6: Implement the wire types and decoder**

The decoder entrypoint must remain:

```ts
export function decodeCanonicalReportArtifact(
  input: unknown,
): ReportArtifact
```

Implement small pure validators:

```ts
function requireRecord(value: unknown, code: string): Record<string, unknown>
function requireString(value: unknown, code: string): string
function requireBoolean(value: unknown, code: string): boolean
function requireFiniteNumber(value: unknown, code: string): number
function requireStringArray(value: unknown, code: string): string[]
function assertNoForbiddenFields(value: unknown): void
function requireApiHref(value: unknown): string
```

`requireApiHref()` must accept only strings beginning with:

```text
/api/artifacts/stock-analysis/latest/
```

and reject protocol-relative URLs, backslashes, fragments, query strings, `..`, and encoded parent traversal.

The decoder must build a new object field-by-field. It must not return the input object, spread unknown network objects into the view model, or use `as ReportArtifact`.

- [ ] **Step 7: Update component fixtures and semantics tests**

Change `ReportSemantics.test.tsx` to import `reportArtifactFixture` from the test fixture module. Replace `Primary 3/5` with assertions for:

```text
Evidence 4
Primary 3
Risk 1
```

Add a structured safety finding case and assert its phrase and line are rendered without converting the finding to a raw JSON string.

- [ ] **Step 8: Run the decoder and semantics green tests**

Run:

```bash
npm --prefix apps/serenity-web test -- \
  src/artifacts/canonicalReportArtifact.test.ts \
  src/components/ReportSemantics.test.tsx
```

Expected: PASS.

- [ ] **Step 9: Commit the decoder/model slice**

```bash
git add \
  apps/serenity-web/src/types.ts \
  apps/serenity-web/src/artifacts/canonicalReportArtifact.ts \
  apps/serenity-web/src/artifacts/canonicalReportArtifact.test.ts \
  apps/serenity-web/src/test/fixtures/reportArtifacts.ts \
  apps/serenity-web/src/components/ReportSemantics.test.tsx \
  apps/serenity-web/src/data/sampleReportArtifact.ts
git diff --cached --check
git commit -m "feat: 添加严格股票分析工件解码器"
```

The deleted production fixture path may be staged only after all tests import the replacement test fixture.

### Task 5: Injectable Artifact Source And App Lifecycle

**Files:**
- Create: `apps/serenity-web/src/artifacts/reportArtifactSource.ts`
- Create: `apps/serenity-web/src/artifacts/reportArtifactSource.test.ts`
- Modify: `apps/serenity-web/src/App.tsx`
- Create: `apps/serenity-web/src/App.test.tsx`
- Modify: `apps/serenity-web/src/main.tsx`
- Modify: `apps/serenity-web/src/styles.css`

- [ ] **Step 1: Write the failing source tests**

Define:

```ts
export interface ReportArtifactSource {
  loadLatest(signal?: AbortSignal): Promise<ReportArtifact>;
}
```

Test the production source:

```ts
it('requests the relative latest-artifact endpoint and decodes the response', async () => {
  const fetchImpl = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(canonicalReportArtifactWireFixture), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  );
  const source = createHttpReportArtifactSource(fetchImpl);
  const controller = new AbortController();

  const artifact = await source.loadLatest(controller.signal);

  expect(fetchImpl).toHaveBeenCalledWith(
    '/api/artifacts/stock-analysis/latest',
    expect.objectContaining({
      method: 'GET',
      cache: 'no-store',
      signal: controller.signal,
    }),
  );
  expect(artifact.symbol).toBe('MSFT');
});
```

Test stable classification:

```ts
it.each([
  [404, 'unavailable', 'stock_analysis_artifact_missing'],
  [409, 'blocked', 'report_safety_failed'],
  [422, 'unavailable', 'key_claim_provenance_missing'],
] as const)(
  'classifies HTTP %s without exposing response bodies',
  async (status, kind, reason) => {
    const source = createHttpReportArtifactSource(
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code:
                status === 409 ? 'artifact_blocked' : status === 404
                  ? 'artifact_not_found'
                  : 'artifact_invalid',
              reason,
            },
            raw: '/Users/example/private.json',
          }),
          { status },
        ),
      ),
    );

    let caught: unknown;
    try {
      await source.loadLatest();
    } catch (error) {
      caught = error;
    }

    expect(caught).toMatchObject({ kind, reason });
    expect(String(caught)).not.toContain('/Users/example');
  },
);
```

Also cover invalid JSON, decoder failure, network `TypeError`, and `AbortError`. Errors must expose only `kind` and a stable reason code.

- [ ] **Step 2: Run the source red tests**

Run:

```bash
npm --prefix apps/serenity-web test -- \
  src/artifacts/reportArtifactSource.test.ts
```

Expected: FAIL because `reportArtifactSource.ts` does not exist.

- [ ] **Step 3: Implement source errors and HTTP loading**

Create:

```ts
export class ReportArtifactLoadError extends Error {
  constructor(
    readonly kind: 'unavailable' | 'blocked',
    readonly reason: string,
  ) {
    super(reason);
    this.name = 'ReportArtifactLoadError';
  }
}
```

```ts
export function createHttpReportArtifactSource(
  fetchImpl: typeof fetch = fetch,
): ReportArtifactSource {
  return {
    async loadLatest(signal?: AbortSignal): Promise<ReportArtifact> {
      let response: Response;
      try {
        response = await fetchImpl(
          '/api/artifacts/stock-analysis/latest',
          {
            method: 'GET',
            cache: 'no-store',
            headers: { Accept: 'application/json' },
            signal,
          },
        );
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          throw new ReportArtifactLoadError('unavailable', 'request_aborted');
        }
        throw new ReportArtifactLoadError('unavailable', 'network_unavailable');
      }

      const payload = await readJsonOrThrow(response);
      if (!response.ok) {
        throw classifyArtifactError(response.status, payload);
      }
      try {
        return decodeCanonicalReportArtifact(payload);
      } catch {
        throw new ReportArtifactLoadError(
          'unavailable',
          'artifact_payload_invalid',
        );
      }
    },
  };
}
```

`readJsonOrThrow()` and `classifyArtifactError()` must read only `error.code` and `error.reason`, ignore all other response fields, and use fallback reasons when the envelope is malformed.

- [ ] **Step 4: Write the failing App lifecycle tests**

Render `App` with an injected fake source:

```ts
it('renders loading and then the canonical artifact', async () => {
  const deferred = createDeferred<ReportArtifact>();
  render(<App artifactSource={{ loadLatest: () => deferred.promise }} />);

  expect(
    screen.getByRole('status', { name: /loading research artifact/i }),
  ).toBeInTheDocument();

  deferred.resolve(reportArtifactFixture);
  expect(
    await screen.findByText('MSFT market data research'),
  ).toBeInTheDocument();
});
```

Add tests for:

- `unavailable` reason and retry;
- `blocked` reason with no `Open Markdown report` or `Open manifest` links;
- retry starts a second `loadLatest()` call;
- an old request cannot overwrite the result of a newer retry;
- unmount aborts the in-flight request;
- Settings and Not Found routes remain available without a ready artifact;
- production source injection is separate from test fixtures.

- [ ] **Step 5: Run the App red tests**

Run:

```bash
npm --prefix apps/serenity-web test -- \
  src/artifacts/reportArtifactSource.test.ts \
  src/App.test.tsx
```

Expected: FAIL because `App` does not accept a source and always renders the sample fixture.

- [ ] **Step 6: Implement the App lifecycle**

Use:

```ts
interface AppProps {
  artifactSource: ReportArtifactSource;
}

export default function App({ artifactSource }: AppProps) {
  const [requestVersion, setRequestVersion] = useState(0);
  const [availability, setAvailability] =
    useState<ArtifactAvailability>({ status: 'loading' });

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setAvailability({ status: 'loading' });

    artifactSource
      .loadLatest(controller.signal)
      .then((artifact) => {
        if (active) {
          setAvailability({ status: 'ready', artifact });
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        if (error instanceof ReportArtifactLoadError) {
          setAvailability({
            status: error.kind,
            reason: error.reason,
          });
          return;
        }
        setAvailability({
          status: 'unavailable',
          reason: 'artifact_unavailable',
        });
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [artifactSource, requestVersion]);
```

Render stable state components before route-specific artifact pages:

```tsx
function ArtifactState({
  availability,
  onRetry,
}: {
  availability: Exclude<ArtifactAvailability, { status: 'ready' }>;
  onRetry: () => void;
}) {
  if (availability.status === 'loading') {
    return (
      <section aria-label="Loading research artifact" role="status">
        <h1>Loading research artifact</h1>
      </section>
    );
  }
  return (
    <section role="alert">
      <h1>
        {availability.status === 'blocked'
          ? 'Research artifact blocked'
          : 'Research artifact unavailable'}
      </h1>
      <p>{availability.reason}</p>
      <button onClick={onRetry} type="button">
        Retry
      </button>
    </section>
  );
}
```

Do not add any fixture fallback in `catch`, timeout, or blocked paths.

- [ ] **Step 7: Inject only the production source in main**

Use:

```tsx
import { createHttpReportArtifactSource } from './artifacts/reportArtifactSource';

const artifactSource = createHttpReportArtifactSource();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App artifactSource={artifactSource} />
  </StrictMode>,
);
```

The production source tree must contain no import from `test/fixtures` or the deleted `data/sampleReportArtifact`.

- [ ] **Step 8: Run lifecycle green tests and static fixture guard**

Run:

```bash
npm --prefix apps/serenity-web test -- \
  src/artifacts/canonicalReportArtifact.test.ts \
  src/artifacts/reportArtifactSource.test.ts \
  src/App.test.tsx \
  src/components/ReportSemantics.test.tsx
```

Run:

```bash
rg -n "sampleReportArtifact|test/fixtures/reportArtifacts" \
  apps/serenity-web/src/App.tsx \
  apps/serenity-web/src/main.tsx
```

Expected: Vitest PASS; `rg` returns no matches.

- [ ] **Step 9: Commit the source and lifecycle slice**

```bash
git add \
  apps/serenity-web/src/App.tsx \
  apps/serenity-web/src/App.test.tsx \
  apps/serenity-web/src/main.tsx \
  apps/serenity-web/src/styles.css \
  apps/serenity-web/src/artifacts/reportArtifactSource.ts \
  apps/serenity-web/src/artifacts/reportArtifactSource.test.ts
git diff --cached --check
git commit -m "feat: 接入可注入股票分析工件来源"
```

### Task 6: Report Semantics, Latest-Only History, Vite Proxy, And Playwright

**Files:**
- Modify: `apps/serenity-web/src/components/ReportSemanticsPanel.tsx`
- Modify: `apps/serenity-web/src/components/ReportSemantics.test.tsx`
- Modify: `apps/serenity-web/src/pages/HistoryPage.tsx`
- Modify: `apps/serenity-web/vite.config.ts`
- Modify: `apps/serenity-web/e2e/app-shell.spec.ts`

- [ ] **Step 1: Write the failing semantics and latest-only History assertions**

Update component tests to assert:

```ts
expect(screen.getByText(/evidence 4/i)).toBeInTheDocument();
expect(screen.getByText(/focus 4/i)).toBeInTheDocument();
expect(screen.getByText(/primary 3/i)).toBeInTheDocument();
expect(screen.getByText(/risk 1/i)).toBeInTheDocument();
expect(screen.getByText(/latest available artifact/i)).toBeInTheDocument();
```

Add a structured coverage flag and safety finding to a fixture copy and assert code, severity, phrase, and line are all visible.

- [ ] **Step 2: Run the semantics red test**

Run:

```bash
npm --prefix apps/serenity-web test -- \
  src/components/ReportSemantics.test.tsx \
  src/App.test.tsx
```

Expected: FAIL because the existing component still renders fixture-only `collected/required` coverage and History does not label the latest-only limitation.

- [ ] **Step 3: Render actual canonical coverage and structured findings**

Replace the source-coverage card with actual fields:

```tsx
<strong>Evidence {artifact.sourceCoverage.evidenceCount}</strong>
<span>Focus {artifact.sourceCoverage.focusEvidenceCount}</span>
<span>Primary {artifact.sourceCoverage.primaryCount}</span>
<span>Risk {artifact.sourceCoverage.riskCount}</span>
<span>
  External {artifact.sourceCoverage.externalNonSerenityCount}
</span>
```

Render coverage flags by `code` and safety findings by a stable composite key:

```tsx
{artifact.safety.findings.map((finding) => (
  <li key={`${finding.lineNumber}:${finding.phrase}`}>
    <strong>{finding.phrase}</strong>
    <span>{finding.line}</span>
  </li>
))}
```

Change the History page copy to:

```text
Latest available artifact
This page shows the latest validated stock-analysis artifact. Complete run history is deferred to a separate source.
```

- [ ] **Step 4: Add the Vite loopback proxy**

Use:

```ts
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: false,
      },
    },
  },
});
```

Do not add CORS middleware, wildcard origins, path rewriting, or production static hosting.

- [ ] **Step 5: Write the failing non-AAPL Playwright flow**

Before `page.goto('/')`, intercept:

```ts
await page.route(
  '**/api/artifacts/stock-analysis/latest',
  async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(canonicalPlaywrightArtifact),
    });
  },
);
```

Use `NVDA` or `MSFT`, never AAPL. Assert:

- Home shows the intercepted query and symbol;
- Analysis shows canonical readiness, coverage, skeptical review, safety, and provenance;
- Report Reader dialog name uses the intercepted symbol;
- Markdown and manifest links use the two API-relative hrefs;
- History shows `Latest available artifact` and the intercepted query;
- Settings remains available;
- no AAPL text is present.

Add a second test intercepting:

```json
{
  "error": {
    "code": "artifact_blocked",
    "reason": "report_safety_failed"
  }
}
```

with status `409`, then assert the blocked state and absence of report/manifest links.

- [ ] **Step 6: Run Playwright red**

Run:

```bash
npm --prefix apps/serenity-web run test:smoke -- --reporter=line
```

Expected: FAIL because the current app never requests the intercepted API and still renders AAPL fixture data.

- [ ] **Step 7: Run frontend green verification**

Run:

```bash
npm --prefix apps/serenity-web test
npm --prefix apps/serenity-web run build
npm --prefix apps/serenity-web run test:smoke -- --reporter=line
```

Expected: all PASS.

- [ ] **Step 8: Run frontend boundary scans**

Run:

```bash
rg -n \
  "sampleReportArtifact|daily_stock_analysis|/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis" \
  apps/serenity-web/src \
  apps/serenity-web/e2e
```

Expected: no production fixture import and no external DSA checkout dependency. Test names may mention the fixture boundary only if the test is explicitly proving absence.

Run:

```bash
rg -n \
  "operation_advice|sentiment_score|you should buy|you should sell|target price|position sizing|stop loss|take profit" \
  apps/serenity-web/src \
  apps/serenity-web/e2e
```

Expected: matches only inside negative regression assertions or fixed forbidden-field constants, never user-facing production copy.

- [ ] **Step 9: Commit the UI semantics and browser flow**

```bash
git add \
  apps/serenity-web/src/components/ReportSemanticsPanel.tsx \
  apps/serenity-web/src/components/ReportSemantics.test.tsx \
  apps/serenity-web/src/pages/HistoryPage.tsx \
  apps/serenity-web/vite.config.ts \
  apps/serenity-web/e2e/app-shell.spec.ts
git diff --cached --check
git commit -m "feat: 完成最新研究工件 Web 运行时对等"
```

### Task 7: Full Verification, Documentation Reconciliation, And Handoff

**Files:**
- Modify: `docs/serenity-led-dsa-full-migration-plan.md`
- Modify: `docs/serenity-led-dsa-full-migration-tracker.md`
- Modify: `tasks/todo.md`
- Modify: `tasks/lessons.md`

- [ ] **Step 1: Run focused backend verification**

Run:

```bash
python3 -m pytest \
  tests/test_analysis_pipeline.py \
  tests/test_analysis_report.py \
  tests/test_stock_analysis_artifacts.py \
  tests/test_app_api.py \
  tests/test_cli.py \
  tests/test_dsa_migration_boundaries.py \
  tests/test_report_safety.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run the complete Python verification**

Run:

```bash
make verify
```

Expected: PASS; doctor healthy; `run-cpo-pack` and coverage matrix complete. This command does not replace frontend verification.

- [ ] **Step 3: Run complete frontend verification**

Run:

```bash
npm --prefix apps/serenity-web test
npm --prefix apps/serenity-web run build
npm --prefix apps/serenity-web run test:smoke -- --reporter=line
```

Expected: PASS.

- [ ] **Step 4: Run the unified offline release gate**

When the Docker daemon remains unavailable:

```bash
PYTHONPATH=src python3 scripts/verify_offline_release.py --skip-docker-smoke
```

Expected: required checks PASS and Docker smoke is explicitly skipped with a recorded reason.

When the Docker daemon becomes available:

```bash
PYTHONPATH=src python3 scripts/verify_offline_release.py
```

Expected: Docker image build and no-secret container `/health` smoke PASS. Do not claim this evidence until the real command succeeds.

- [ ] **Step 5: Run path, import, fixture, and safety scans**

Run:

```bash
rg -n \
  "daily_stock_analysis|/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis" \
  src/serenity_alpha_lab \
  apps/serenity-web/src
```

Expected: no runtime import or path dependency.

Run:

```bash
rg -n \
  "sampleReportArtifact" \
  apps/serenity-web/src/App.tsx \
  apps/serenity-web/src/main.tsx
```

Expected: no matches.

Run:

```bash
git diff --check
```

Expected: PASS.

- [ ] **Step 6: Verify representative API behavior without using protected artifacts**

Generate a disposable artifact:

```bash
tmp_dir="$(mktemp -d)"
PYTHONPATH=src python3 -m serenity_alpha_lab.cli analyze-stock \
  AAPL \
  --stub \
  --out-dir "$tmp_dir"
PYTHONPATH=src python3 -m serenity_alpha_lab.cli serve-app \
  --host 127.0.0.1 \
  --port 8010 \
  --stock-analysis-artifact-dir "$tmp_dir"
```

In a second terminal, inspect:

```bash
curl -fsS http://127.0.0.1:8010/api/artifacts/stock-analysis/latest
curl -fsS http://127.0.0.1:8010/api/artifacts/stock-analysis/latest/manifest
curl -fsS http://127.0.0.1:8010/api/artifacts/stock-analysis/latest/report
```

Expected: canonical summary, validated manifest, and Markdown report; no absolute repository path. Stop the server and delete the temporary directory after the smoke.

- [ ] **Step 7: Reconcile migration documentation**

Update `docs/serenity-led-dsa-full-migration-plan.md` so Phase 0-7 completion markers and the immediate-next-step section no longer contradict the tracker. Preserve the document as a migration plan; do not rewrite historical architecture decisions.

Update tracker and todo with four explicit categories:

- Completed;
- Not Started;
- Environment Blocked;
- Deferred.

Record:

- implementation commits;
- exact focused/full verification counts;
- frontend test/build/Playwright evidence;
- release-gate evidence;
- Docker daemon status;
- protected-file status;
- next unstarted follow-on slice.

- [ ] **Step 8: Update the reusable lesson**

Append:

```text
Runtime-parity planning checkpoints must distinguish pre-implementation baselines from implementation evidence. Every TDD task should name the exact red command and intended missing behavior, and planning must not be reported as runtime parity completion before those tests fail for the expected reason and later pass.
```

- [ ] **Step 9: Verify protected state before closeout**

Run:

```bash
git status --short
git diff --name-only --cached
```

Expected: the four protected `output/ui/*` entries remain untouched and unstaged. No `dist`, Playwright report, test-results, cache, `.venv`, database, or external DSA file is staged.

- [ ] **Step 10: Commit implementation closeout documentation**

```bash
git add \
  docs/serenity-led-dsa-full-migration-plan.md \
  docs/serenity-led-dsa-full-migration-tracker.md \
  tasks/todo.md \
  tasks/lessons.md
git diff --cached --check
git commit -m "docs: 记录股票分析运行时对等实现交接"
```

- [ ] **Step 11: Refresh the tracker with the final handoff commit**

After the documentation commit, update the tracker restart prompt with the actual final HEAD and create one final status-refresh commit if needed:

```bash
git add docs/serenity-led-dsa-full-migration-tracker.md tasks/todo.md
git diff --cached --check
git commit -m "docs: 刷新运行时对等最终状态"
```

Do not leave the restart prompt pointing at the implementation commit when a later handoff-docs commit is the actual HEAD.

## Plan Self-Review Checklist

- [x] Every approved manifest field maps to Task 1.
- [x] Every repository validation and safety rule maps to Task 2.
- [x] All three endpoints, status codes, content types, error envelope, config, and CLI option map to Task 3.
- [x] Wire/view-model separation, finite-number checks, href checks, provenance, forbidden fields, and no `as ReportArtifact` shortcut map to Task 4.
- [x] Injectable source, loading/ready/unavailable/blocked, retry, abort, stale-response handling, and no production fixture fallback map to Task 5.
- [x] Real coverage counts, structured findings, latest-only History, Vite proxy, and non-AAPL Playwright interception map to Task 6.
- [x] Focused regression, full Python verification, frontend tests/build/smoke, unified release gate, path scans, protected files, tracker/todo/lessons/restart prompt, and commit checkpoints map to Task 7.
- [x] No task introduces history aggregation, `/run-state` redesign, mutation endpoints, static Web hosting, wildcard CORS, Electron/updater, live Bot/LLM/provider integrations, notifications, broker/order actions, trading automation, or release publishing.
- [x] No task reads from or runtime-imports the external DSA checkout.
- [x] No task uses the protected `output/ui/*` state as a fixture.
- [x] Placeholder scan contains no undefined marker or incomplete follow-up implementation step.
