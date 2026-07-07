# Serenity Alpha Lab Interactive UI Plan

## Goal

Upgrade the first static dashboard into a more usable local product interface for investment research triage.

## User Journeys

- As a research user, I can search by ticker, memo text, flags, or source claim without reading every memo.
- As a research user, I can filter readiness by status and focus on one ticker's memo preview.
- As a research user, I can expand primary evidence details when I need provenance, while keeping the dashboard scannable.
- As a nontechnical user, I can run one command to preview the UI locally in a browser-compatible HTTP server.

## Implementation Steps

- [ ] Add failing tests for interactive controls, data attributes, and the `serve-ui` CLI route.
- [ ] Add semantic filter/search controls to the generated HTML.
- [ ] Add small dependency-free JavaScript for search, status filtering, ticker focus, and provenance expansion.
- [ ] Add `serve-ui` command backed by Python's standard-library HTTP server.
- [ ] Add `make serve-ui` and document product usage.
- [ ] Regenerate UI and run full verification.

## Verification

- `python3 -m pytest tests/test_ui.py tests/test_cli.py::test_cli_serve_ui_builds_dashboard_and_invokes_server -q`
- `python3 -m pytest tests -q`
- `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui`
- `make verify`

