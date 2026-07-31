# README Product Homepage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a root README and standalone static product homepage that accurately present Serenity Alpha Lab's current evidence-first AI stock research and quant platform.

**Architecture:** Keep this as a documentation and static presentation change. The root README becomes the package readme and points to phase evidence, while `docs/product-homepage/` contains standalone HTML/CSS that can be opened directly without a build step.

**Tech Stack:** Markdown, static HTML5, CSS custom properties, existing Python package metadata and pytest verification.

---

### Task 1: Root README

**Files:**
- Create: `README.md`
- Modify: `pyproject.toml`
- Modify: `tasks/todo.md`

- [x] **Step 1: Add the README structure**

Create `README.md` with:

- project title and one-sentence positioning
- status strip for `110/129`, `P6 4/23`, `G5 GO with accepted risks`, `G6 not passed`
- TL;DR table for reader goals
- humans/agents sections
- architecture loop and capability matrix
- safety boundaries and current roadmap

- [x] **Step 2: Point package metadata at README**

Change `pyproject.toml` from:

```toml
readme = { file = "docs/ai-stock-quant-platform-development-plan.md", content-type = "text/markdown" }
```

to:

```toml
readme = { file = "README.md", content-type = "text/markdown" }
```

- [x] **Step 3: Record task review**

Add a top `tasks/todo.md` section recording:

- approved approach A
- files changed
- verification commands
- no SAL-P6-005 or runtime scope started

### Task 2: Static Product Homepage

**Files:**
- Create: `docs/product-homepage/index.html`
- Create: `docs/product-homepage/styles.css`
- Modify: `README.md`

- [x] **Step 1: Create semantic HTML**

Create a standalone page with:

- accessible skip link and navigation
- full-viewport hero with product workbench scene
- proof metrics strip
- operating loop section
- capability and trust-boundary sections
- roadmap/status section

- [x] **Step 2: Create responsive CSS**

Create CSS with:

- semantic color tokens
- responsive first viewport with no horizontal scroll
- accessible focus states
- reduced-motion support
- product workbench visual scene without external images or scripts

- [x] **Step 3: Link homepage from README**

Add a README link:

```markdown
Open the product homepage directly: `docs/product-homepage/index.html`.
```

### Task 3: Verification And Commit

**Files:**
- Verify all files above.

- [x] **Step 1: Run static checks**

Run:

```bash
test -f README.md
test -f docs/product-homepage/index.html
test -f docs/product-homepage/styles.css
rg -n "Serenity Alpha Lab|110/129|SAL-P6-005|product homepage" README.md docs/product-homepage/index.html tasks/todo.md
git diff --check
```

Expected: all commands exit `0`.

- [x] **Step 2: Run package and test verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
```

Expected: pytest passes with the current project baseline, compileall succeeds, dependency lock check resolves the pinned packages.

- [ ] **Step 3: Create Chinese checkpoint commit**

Run:

```bash
git add README.md pyproject.toml tasks/todo.md docs/product-homepage/index.html docs/product-homepage/styles.css docs/superpowers/specs/2026-07-31-readme-product-homepage-design.md docs/superpowers/plans/2026-07-31-readme-product-homepage.md
git commit -m "docs: 完善 README 与产品主页"
```

Expected: commit succeeds and no ignored generated directories are staged.
