# Screen Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build SAL-P3-015 Screen Lab as a DSA Web extension patch that consumes the frozen Quant Screening API contract and displays definition editing, run submission, results, explanations, and comparison states.

**Architecture:** Keep DSA runtime source isolated under `.worktrees/dsa-v3.26.1` and land the web changes as `patches/dsa/v3.26.1/0004-add-screen-lab.patch`. Add a typed `quantScreeningApi` client for `/api/v1/quant`, a lazy `/screen-lab` route, and a UI page that never calls legacy AlphaSift endpoints for Screen Lab data. Tests mock the API client and assert contract labels, state handling, result rows, explanation drawer, and comparison output.

**Tech Stack:** React 19, React Router, TypeScript, Vitest, Testing Library, DSA Web component primitives, Axios API client, Serenity Quant Screening API DTOs.

---

### Task 1: API Client Contract

**Files:**
- Create: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/api/quantScreening.ts`
- Create: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/api/__tests__/quantScreening.test.ts`

- [x] **Step 1: Write the failing API tests**

```typescript
import { quantScreeningApi } from '../quantScreening';

await quantScreeningApi.createScreenRun(request, 'idem-1');
expect(post).toHaveBeenCalledWith('/api/v1/quant/screen-runs', expectedSnakeBody, {
  headers: { 'Idempotency-Key': 'idem-1' },
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `npm run test -- src/api/__tests__/quantScreening.test.ts`
Expected: FAIL because `src/api/quantScreening.ts` does not exist.

- [x] **Step 3: Implement typed client**

```typescript
export const quantScreeningApi = {
  async createScreenRun(payload: QuantScreenRunCreatePayload, idempotencyKey: string) {
    const response = await apiClient.post('/api/v1/quant/screen-runs', toSnake(payload), {
      headers: { 'Idempotency-Key': idempotencyKey },
    });
    return toCamelCase<QuantScreenRunAccepted>(response.data);
  },
};
```

- [x] **Step 4: Run API test to verify it passes**

Run: `npm run test -- src/api/__tests__/quantScreening.test.ts`
Expected: PASS.

### Task 2: Screen Lab Page

**Files:**
- Create: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/pages/ScreenLabPage.tsx`
- Create: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/pages/__tests__/ScreenLabPage.test.tsx`

- [x] **Step 1: Write failing page tests**

```typescript
render(<ScreenLabPage />);
expect(await screen.findByText('Screen Lab')).toBeInTheDocument();
expect(screen.getByText('Draft')).toBeInTheDocument();
expect(screen.getByText('Published')).toBeInTheDocument();
expect(screen.getByText('Snapshot')).toBeInTheDocument();
expect(screen.getByText('History')).toBeInTheDocument();
expect(screen.getByText('Preview')).toBeInTheDocument();
expect(screen.getByText('Formal')).toBeInTheDocument();
```

- [x] **Step 2: Run test to verify it fails**

Run: `npm run test -- src/pages/__tests__/ScreenLabPage.test.tsx`
Expected: FAIL because `ScreenLabPage` does not exist.

- [x] **Step 3: Implement page**

Build one focused page with:
- left configuration panel for universe/filter/score/constraint and draft/published controls
- run panel that submits through `quantScreeningApi.createScreenRun()`
- right result table using `quantScreeningApi.getScreenRunResults()`
- details drawer backed by `quantScreeningApi.getScreenRunResult()`
- comparison panel backed by `quantScreeningApi.compareScreenRuns()`
- explicit loading, empty, partial, error, stale, and permission-denied states

- [x] **Step 4: Run page test to verify it passes**

Run: `npm run test -- src/pages/__tests__/ScreenLabPage.test.tsx`
Expected: PASS.

### Task 3: Route And Navigation Patch

**Files:**
- Modify: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/App.tsx`
- Modify: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/App.test.tsx`
- Modify: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/components/layout/SidebarNav.tsx`
- Modify: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/components/layout/__tests__/SidebarNav.test.tsx`
- Modify: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/i18n/uiText.ts`

- [x] **Step 1: Add route and nav tests**

```typescript
window.history.pushState({}, '', '/screen-lab');
render(<App />);
expect(await screen.findByTestId('screen-lab-page')).toBeInTheDocument();
expect(setCurrentRoute).toHaveBeenCalledWith('/screen-lab');
```

- [x] **Step 2: Implement lazy route and nav label**

Add lazy import for `ScreenLabPage`, route `/screen-lab`, nav key `screenLab`, and localized labels `layout.nav.screenLab` / `layout.route.screenLab.*`.

- [x] **Step 3: Run route test**

Run: `npm run test -- src/App.test.tsx`
Expected: PASS.

### Task 4: Registered Patch And Evidence

**Files:**
- Create: `patches/dsa/v3.26.1/0004-add-screen-lab.patch`
- Modify: `docs/upstream-patches.md`
- Create: `docs/screen-lab.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Generate patch from DSA worktree diff**

Run: `git -C .worktrees/dsa-v3.26.1 diff -- apps/dsa-web/src/App.tsx apps/dsa-web/src/App.test.tsx apps/dsa-web/src/api/quantScreening.ts apps/dsa-web/src/api/__tests__/quantScreening.test.ts apps/dsa-web/src/components/layout/SidebarNav.tsx apps/dsa-web/src/components/layout/__tests__/SidebarNav.test.tsx apps/dsa-web/src/i18n/uiText.ts apps/dsa-web/src/pages/ScreenLabPage.tsx apps/dsa-web/src/pages/__tests__/ScreenLabPage.test.tsx`
Expected: Diff contains only Screen Lab files.

- [x] **Step 2: Validate patch**

Run: `scripts/apply-dsa-baseline-patches.sh --check-only`
Expected: `0004-add-screen-lab.patch` can be applied or is already applied after local worktree edit.

- [x] **Step 3: Run verification**

Run target web tests, Python contract tests, `compileall`, lock guard, tag check, and `git diff --check`.

- [x] **Step 4: Commit**

Stage only tracked repo files for SAL-P3-015 and commit with a Chinese checkpoint message.
