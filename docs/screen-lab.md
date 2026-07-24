# Screen Lab 记录

> 任务：`SAL-P3-015` Screen Lab
> 日期：2026-07-25
> 状态：完成；Gate G3 仍未通过，下一步为 `SAL-P3-016` 筛选性能与复现验收。

## 结论

`SAL-P3-015` 以 DSA Web extension patch 形式交付 Screen Lab，不把 DSA runtime 源码搬入根项目。可评审交付是：

- `patches/dsa/v3.26.1/0004-add-screen-lab.patch`
- `docs/superpowers/plans/2026-07-25-screen-lab.md`
- 本记录、`docs/upstream-patches.md`、`docs/development-progress-checklist.md`、`docs/development-status.md` 和 `tasks/todo.md`

实现 checkpoint 由本次提交生成；提交后以 `git log -1 --oneline` 和最终交接为准。

## 补丁内容

`DSA-PATCH-004` 只覆盖 DSA Web Screen Lab 文件：

- `apps/dsa-web/src/api/quantScreening.ts`
- `apps/dsa-web/src/api/__tests__/quantScreening.test.ts`
- `apps/dsa-web/src/pages/ScreenLabPage.tsx`
- `apps/dsa-web/src/pages/__tests__/ScreenLabPage.test.tsx`
- `apps/dsa-web/src/App.tsx`
- `apps/dsa-web/src/App.test.tsx`
- `apps/dsa-web/src/components/layout/SidebarNav.tsx`
- `apps/dsa-web/src/components/layout/__tests__/SidebarNav.test.tsx`
- `apps/dsa-web/src/i18n/uiText.ts`

其他 `.worktrees/dsa-v3.26.1` 修改属于既有 P0 patch layer 或本地构建产物，不进入 `0004-add-screen-lab.patch`。

## 契约复用

Screen Lab 使用 `SAL-P3-014` Quant Screening API 作为唯一 UI 数据入口：

- `POST /api/v1/quant/screen-runs`：创建 Preview/Formal run，携带 `Idempotency-Key`。
- `GET /api/v1/quant/screen-runs/{run_id}/results`：读取稳定分页结果。
- `GET /api/v1/quant/screen-runs/{run_id}/results/{instrument_id}`：读取单只证券解释行。
- `GET /api/v1/quant/screen-runs/{current_run_id}/comparison?previous_run_id=...`：比较历史 run。

页面展示并保留 `ScreenSnapshot` / `ScreenDefinition Pipeline` / `CandidateBatch` / `FactorDefinition` / `Factor Evaluation` / Dataset Catalog Manifest 口径中的关键 lineage：`as_of`、具体 `dsv_*` Dataset Version、schema name/version、trace/run/stage、snapshot id、pipeline id 和 Artifact manifest。

## UI 语义

- 定义编辑：Universe、Filter、Score、Constraint 配置区均作为 ScreenDefinition draft 输入展示。
- 生命周期：Draft 与 Published 明确分离，避免把未发布定义伪装为正式版本。
- 运行模式：Preview 与 Formal 是显式互斥模式，提交时进入 Quant Screening API。
- 结果浏览：表格显示 passed/failed、rank、final score、failed stage、reason code 与 lineage。
- 解释抽屉：单行详情通过 result lookup 加载 authoritative explanation steps、factor contribution 和 source ids。
- 历史比较：输入 previous run id 后调用 comparison endpoint，展示 added/removed/retained、rank change 和 score delta。

## 状态覆盖

测试覆盖以下 Screen Lab 状态：

- loading：提交 run 或刷新结果时显示加载状态。
- empty：无结果时显示空态，不把空表伪装为已加载数据。
- partial：分页结果标记 partial 时显示部分结果提示。
- stale：结果标记 stale 时显示过期提示。
- error：普通 API 错误显示可读错误。
- permission-denied：403/permission 问题显示权限边界提示。

## 验证记录

| 命令 | 结果 |
|---|---|
| `npm run test -- src/api/__tests__/quantScreening.test.ts` | Red：缺少 `src/api/quantScreening.ts`；Green：API client tests pass |
| `npm run test -- src/pages/__tests__/ScreenLabPage.test.tsx` | Red：缺少 `ScreenLabPage`；Green：page tests pass |
| `npm run test -- src/App.test.tsx` | Red：`/screen-lab` 未路由；Green：route tests pass |
| `npm run test -- src/components/layout/__tests__/SidebarNav.test.tsx src/api/__tests__/quantScreening.test.ts src/pages/__tests__/ScreenLabPage.test.tsx src/App.test.tsx` | `4 passed files / 24 passed tests` |
| `npm run test` | 初次全量在 stale `SidebarNav` expected order 失败，修正后又遇到一次 unrelated `HomePage` timeout；单跑 `HomePage` 为 `42 passed`，重跑全量为 `92 passed files / 973 passed / 2 skipped` |
| `npm run lint` | PASS |
| `npm run build` | 初次发现 `explanationSteps` optional narrowing 问题；修复后 PASS |
| `.venv/bin/python -m pytest tests/application/test_quant_screening_api.py tests/quant/test_screen_snapshot.py tests/quant/test_screen_definition_pipeline.py tests/architecture/test_architecture_boundaries.py -q` | `25 passed` |
| `.venv/bin/python -m pytest -q` | `307 passed, 3 skipped` |
| `.venv/bin/python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS，`Resolved 298 packages` |
| `scripts/apply-dsa-baseline-patches.sh --check-only` | `0001..0004` 均为 already applied |
| `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

## 评审记录

尝试调用 code-review subagent，但当前客户端 wrapper 仍注入空 optional field 并触发 `reasoning_effort must not be empty`，因此执行本地 senior review。复核结果：

- `ScreenLabPage` 与 `quantScreeningApi` 不调用 legacy AlphaSift endpoint 作为 Screen Lab 数据源。
- `/screen-lab` 路由、SidebarNav、zh/en i18n 和 route labels 一致。
- 生成 patch 只包含 9 个 Screen Lab web 文件。
- DSA patch stack `0001..0004` 可幂等识别为已应用。
- 未引入真实 Provider/LLM、Worker loop、Quant Core/Qlib、正式回测、Evidence Agent 或 DSA runtime source migration。

## 非目标

本任务不实现 `SAL-P3-016` 性能/复现验收、不通过 Gate G3、不启动 Quant Core/Qlib、不实现正式回测、不接入 Evidence Agent、不触发真实 Provider/LLM 调用、不实现 Worker execution loop，也不移动或重打 `upstream/dsa-v3.26.1` tag。
