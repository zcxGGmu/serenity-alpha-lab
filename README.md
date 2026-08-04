# Serenity Alpha Lab

Evidence-first AI stock research and quant analysis, built around the `daily_stock_analysis` product trunk and a deterministic Quant Core.

You bring an investment question. Serenity Alpha Lab turns it into versioned data, reproducible factors, bias-aware backtests, cited research reports, and explicit risk decisions. LLMs are allowed to explain and synthesize; they are not allowed to invent prices, recompute portfolio truth, or bypass safety gates.

> Current status: Phase P6 security and release hardening. Gate G5 is `GO with accepted risks`; Gate G6 is not passed. Progress is `110/129` tasks, with P6 at `4/23`.

## TL;DR

| You want | Start here | What you get |
| --- | --- | --- |
| Product overview | [`https://zcxggmu.github.io/serenity-alpha-lab/`](https://zcxggmu.github.io/serenity-alpha-lab/) | GitHub Pages product homepage |
| Local homepage preview | [`web/index.html`](web/index.html) | Static homepage source published by GitHub Pages |
| Current project state | [`docs/development-status.md`](docs/development-status.md) | Phase, gate, checkpoint, next task, and recovery prompt |
| Execution ledger | [`docs/development-progress-checklist.md`](docs/development-progress-checklist.md) | 129-task roadmap with evidence, decisions, and acceptance notes |
| Architecture plan | [`docs/ai-stock-quant-platform-development-plan.md`](docs/ai-stock-quant-platform-development-plan.md) | Full AI stock research and quant platform design |
| Run verification | `uv run --extra core --extra dev python -m pytest -q` | Current offline contract suite |

## What This Is

Serenity Alpha Lab is not a generic chatbot for stocks. It is a controlled research and quant platform with three separable layers:

- **Data and Quant Core**: instrument identity, PIT datasets, trading calendars, factors, screening, portfolio ledger, execution rules, cost models, risk policies, and formal backtest contracts.
- **Evidence Research System**: source trust, prompt/output schemas, citation validation, trusted report rendering, report delivery payloads, and agent regression evaluation.
- **Product Trunk**: DSA compatibility adapters, task backend, artifact store, report/UI delivery contracts, desktop profile, API contracts, and release gates.

The operating rule is simple: deterministic code computes financial truth; AI agents assemble arguments from bounded evidence.

## Why It Exists

Most AI stock tooling fails in the same places:

- it mixes narrative with calculations
- it loses data version and decision-time lineage
- it calls backtests something they are not
- it lets agents cite weak or unverified sources
- it treats "the model said it" as completion

Serenity Alpha Lab makes those failure modes first-class engineering constraints. Every meaningful output should have a dataset version, artifact hash, stage/run trace, source confidence, and gate status.

## System Loop

```text
Candidate discovery
  -> Provider and Dataset contracts
  -> Quant screening and factor evaluation
  -> Formal backtest contracts and risk gates
  -> Evidence-bound multi-agent research
  -> Trusted report rendering and delivery
  -> Security, supply-chain, release hardening
```

## Capability Matrix

| Area | Current status | Evidence |
| --- | --- | --- |
| Upstream DSA baseline | Gate G0 passed | [`docs/gate-g0-baseline-review.md`](docs/gate-g0-baseline-review.md) |
| Engineering foundation | Gate G1 passed | [`docs/gate-g1-engineering-foundation-review.md`](docs/gate-g1-engineering-foundation-review.md) |
| Data and task backbone | Gate G2 passed | [`docs/gate-g2-data-task-review.md`](docs/gate-g2-data-task-review.md) |
| Screen and factor lab | Gate G3 passed | [`docs/gate-g3-screen-factor-review.md`](docs/gate-g3-screen-factor-review.md) |
| Backtest and risk contracts | Gate G4 passed | [`docs/gate-g4-backtest-risk-review.md`](docs/gate-g4-backtest-risk-review.md) |
| Trusted research chain | Gate G5 passed | [`docs/gate-g5-trusted-research-review.md`](docs/gate-g5-trusted-research-review.md) |
| Security and release hardening | In progress | [`docs/development-status.md`](docs/development-status.md) |

## For Humans

Read these in order:

1. [`https://zcxggmu.github.io/serenity-alpha-lab/`](https://zcxggmu.github.io/serenity-alpha-lab/)
2. [`docs/development-status.md`](docs/development-status.md)
3. [`docs/ai-stock-quant-platform-development-plan.md`](docs/ai-stock-quant-platform-development-plan.md)
4. [`docs/development-progress-checklist.md`](docs/development-progress-checklist.md)

Then run the verification loop:

```bash
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
```

## For Agents

Start every session by reading:

1. [`AGENTS.md`](AGENTS.md)
2. [`tasks/lessons.md`](tasks/lessons.md)
3. [`docs/development-status.md`](docs/development-status.md)
4. [`docs/development-progress-checklist.md`](docs/development-progress-checklist.md)
5. the task-specific evidence docs named in the status file

Do not skip the current boundary: the next implementation task is `SAL-P6-005` supply-chain and security gates. Do not jump to `SAL-P6-006+`, real Provider/LLM execution, Worker loops, Qlib runtime, production scheduling, notification sender, release packaging, or formal portfolio backtest promotion.

## Installation

The root package targets Python `>=3.11,<3.13`.

```bash
uv sync --extra core --extra dev
uv run serenity-alpha-lab --help
```

Optional extras are split by boundary:

| Extra | Purpose |
| --- | --- |
| `core` | application contracts, repositories, DSA runtime dependency set |
| `providers` | market data provider libraries |
| `desktop` | desktop/chat delivery integrations |
| `quant` | heavy quant dependencies, including isolated Qlib usage |
| `dev` | pytest, formatting, linting, and security tools |

## Product Homepage

Open the product homepage through GitHub Pages:

```text
https://zcxggmu.github.io/serenity-alpha-lab/
```

Preview the same static source locally:

```text
web/index.html
```

It is intentionally static and published from [`web/`](web/) by [`deploy-pages.yml`](.github/workflows/deploy-pages.yml). No build system, analytics, external image, Provider call, LLM call, Worker loop, or runtime service is required.

## Safety Boundaries

- No live trading.
- No LLM-generated portfolio math.
- No formal backtest claim without formal backtest artifacts.
- No Provider/LLM runtime from docs, renderers, validators, resource grants, or config contracts.
- No unbounded web fetch; URL, upload, and report rendering policies are metadata-first and deny unsafe inputs.
- No release claim until Gate G6 passes.

## Current Checkpoints

- Latest implementation checkpoint: `47fd9cf2 feat(P6): 加固输入抓取与报告渲染`
- Latest status sync checkpoint: `268032b9 docs: 同步 SAL-P6-004 checkpoint hash`
- Latest hash-anchor checkpoint: `92ffad9a docs: 记录 SAL-P6-004 状态同步 hash`
- Latest main merge checkpoint: `00cea264 merge: 合并开发分支到主分支`

## License And Upstream

This project is built around `daily_stock_analysis v3.26.1` as the product trunk and keeps upstream integration decisions in [`UPSTREAM_BASE.md`](UPSTREAM_BASE.md), [`docs/upstream-patches.md`](docs/upstream-patches.md), and the ADRs under [`docs/adr/`](docs/adr/).

The immutable upstream tag remains:

```text
upstream/dsa-v3.26.1 = e8a9ca7742e8cb2498c8f491dd76d239b3064e1a
```
