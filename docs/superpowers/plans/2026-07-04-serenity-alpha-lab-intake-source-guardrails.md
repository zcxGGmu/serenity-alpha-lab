# Serenity Alpha Lab Intake Source Guardrails Plan

## Goal

Prevent placeholder or sample URLs from entering formal readiness reports and memo packs through the manual evidence intake workflow.

## Scope

- Validate manual intake `source_url` before appending evidence.
- Reject placeholder/example/local URLs such as `example.com`, `localhost`, and `.invalid`.
- Ensure rejected intake evidence does not write JSONL rows or refresh formal outputs.
- Keep validation local and deterministic.

## TDD Plan

- Add failing tests for source URL validation.
- Add failing CLI test proving placeholder URLs are rejected before refresh.
- Implement the minimal URL guardrail in `evidence_intake`.
- Update existing intake tests to use a non-placeholder source URL.
- Run guarded sample commands and full verification.
