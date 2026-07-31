# README And Product Homepage Design

> Date: 2026-07-31
> Scope: Refresh the public project narrative without starting any new runtime, provider, worker, scheduler, release packaging, or SAL-P6-005 implementation work.

## Context

Serenity Alpha Lab currently has a mature implementation plan, phase status, evidence documents, and a Python package, but no root `README.md`. The project also has only generated `apps/serenity-web/dist` output, so a maintainable product homepage should not depend on rebuilding or resurrecting the old React source tree.

The user asked to reference:

- `code-yeongyu/oh-my-openagent` for README structure and tone.
- `lazycodex.ai` for product homepage structure and interaction narrative.

## Goals

- Add a root README that explains the product in one strong pass: what it is, why it exists, how it works, where the evidence lives, how to run checks, and what remains unfinished.
- Add a static product homepage that can be opened directly in a browser from `docs/product-homepage/index.html`.
- Keep all copy faithful to the current project state: P6 `4/23`, total `110/129`, Gate G5 passed with accepted risks, G6 not passed.
- Avoid suggesting production readiness, live trading, real Provider/LLM execution, or finished release hardening.

## Design Direction

Use a concise "agent/harness" documentation style for README:

- strong opening claim
- quick start table
- humans/agents sections
- capability matrix
- evidence and safety boundaries
- current status and roadmap

Use a product landing page style for the homepage:

- first viewport brand signal: "Serenity Alpha Lab"
- short thesis: evidence-first AI stock research and quant platform
- visible workbench-style product scene in the hero
- compact proof strip with phase/gate/test status
- sections for operating loop, capabilities, trust boundaries, and roadmap

## Files

- `README.md`: new root README and package readme.
- `docs/product-homepage/index.html`: standalone semantic HTML homepage.
- `docs/product-homepage/styles.css`: standalone responsive CSS.
- `docs/superpowers/plans/2026-07-31-readme-product-homepage.md`: implementation plan.
- `docs/superpowers/specs/2026-07-31-readme-product-homepage-design.md`: this design record.
- `pyproject.toml`: update `project.readme` to root README.
- `tasks/todo.md`: add a concise review entry for this non-phase documentation task.

## Non-Goals

- Do not rebuild `apps/serenity-web` source.
- Do not introduce npm, Vite, React, Tailwind, or image-generation dependencies.
- Do not start real Provider/LLM, Worker loop, Qlib runtime, production scheduler, notification sender, release packaging, or formal portfolio backtest promotion.
- Do not mark SAL-P6-005 or Gate G6 complete.

## Validation

- `git diff --check`
- static checks for required README/page phrases
- HTML and CSS existence/readability checks
- focused package metadata check by importing package metadata if practical
- full Python test suite if the environment remains stable

