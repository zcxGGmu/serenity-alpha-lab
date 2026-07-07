# Serenity Alpha Lab Local UI Plan

## Goal

Build a polished local dashboard UI for Serenity Alpha Lab so nontechnical users can inspect the generated CPO research pack without reading raw Markdown files one by one.

## Product Shape

- Generate a self-contained static HTML dashboard at `output/ui/index.html`.
- Avoid server and JavaScript framework dependencies for the first product UI.
- Reuse the existing product outputs:
  - `output/reports/cpo-readiness-guarded.md`
  - `output/packs/cpo-guarded/index.md`
  - `output/packs/cpo-guarded/sources.md`
  - `output/packs/cpo-guarded/*-memo.md`
- Keep the interface research-only and avoid buy/sell/target-price language.

## Design Direction

- Professional investment research dashboard, not a marketing landing page.
- Dense but readable layout with clear hierarchy.
- Status strip for evidence volume, ready memo count, skipped count, and pack health.
- Readiness table with accessible status pills and tabular numeric metrics.
- Memo cards with direct links to generated Markdown memos.
- Featured memo preview with thesis, source coverage, risks, and invalidation conditions.
- Provenance preview with primary evidence and source excerpts.
- Responsive layout with no horizontal scroll on mobile.

## Implementation Steps

- [ ] Add failing tests for dashboard rendering, generated HTML content, and CLI integration.
- [ ] Implement `serenity_alpha_lab.ui` with Markdown parsing and HTML rendering.
- [ ] Add `build-ui` CLI command.
- [ ] Add `make ui` target and documentation.
- [ ] Generate `output/ui/index.html`.
- [ ] Verify tests, product run, UI generation, and smoke-read generated HTML.

## Verification

- `python3 -m pytest tests/test_ui.py tests/test_cli.py::test_cli_build_ui_writes_dashboard -q`
- `python3 -m pytest tests -q`
- `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui`
- `make verify`

