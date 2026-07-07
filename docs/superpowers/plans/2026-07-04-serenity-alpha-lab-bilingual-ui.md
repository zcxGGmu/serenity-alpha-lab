# Serenity Alpha Lab Bilingual UI Plan

## Goal

Provide polished English and Chinese dashboard versions so users can review the same research pack in either language.

## Product Requirements

- Generate `output/ui/index.html` as the English dashboard.
- Generate `output/ui/index.zh.html` as the Chinese dashboard.
- Add visible language-switch links on both dashboards.
- Keep generated memo/source links working from both language versions.
- Preserve the interactive search, status filter, result count, and research-only posture.

## Implementation Steps

- [ ] Add failing tests for bilingual dashboard generation and Chinese UI copy.
- [ ] Add locale-aware UI copy and render both versions from one data model.
- [ ] Add `build-ui --language en|zh|both`, defaulting to `both`.
- [ ] Update documentation with bilingual usage.
- [ ] Regenerate UI and verify HTTP access.

## Verification

- `python3 -m pytest tests/test_ui.py tests/test_cli.py::test_cli_build_ui_writes_bilingual_dashboards -q`
- `python3 -m pytest tests -q`
- `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui`
- HTTP smoke check for `/index.html` and `/index.zh.html`

