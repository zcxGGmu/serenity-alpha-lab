# Serenity Alpha Lab Source Coverage Gate Plan

## Goal

Add a pre-memo source coverage quality gate so ticker-focused research memos expose whether retrieved evidence is strong enough to trust.

## Scope

- Build a pure `source_coverage` module for coverage checks and Markdown rendering.
- Integrate the rendered coverage section into generated memos.
- Keep behavior deterministic and local-only.
- Avoid blocking memo generation; surface warnings instead.

## Checks

- Focus ticker direct evidence exists.
- Focus ticker has primary/fact evidence.
- Retrieved evidence includes risk, negative, or invalidation coverage.
- Methodology evidence does not dominate the retrieved set.
- Placeholder `SERENITY` ticker evidence does not dominate retrieved evidence.

## TDD Plan

- Add tests for missing primary-source coverage.
- Add tests for missing risk coverage.
- Add tests for methodology concentration.
- Add tests for placeholder concentration.
- Add a passing AAOI-like case with primary and risk evidence.
- Add memo test asserting `## Source Coverage` appears before primary evidence.

## Verification

- Run source coverage tests red before implementation.
- Implement the minimal module and memo integration.
- Run targeted tests.
- Generate an updated AAOI memo.
- Run `python3 -m pytest tests -q`.
