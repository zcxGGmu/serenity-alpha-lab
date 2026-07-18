# DSA Web 测试与构建基线尝试记录

> 任务：`SAL-P0-005` 建立 Web 测试与构建基线<br>
> 执行日期：2026-07-19<br>
> 上游基线：`upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 当前状态：`BLOCKED`

## 1. 执行结论

本次已复验 DSA Web 依赖安装、lint、Vitest、Vite build 与 Playwright smoke 入口。`npm ci`、`npm run lint` 和 `npm run build` 可在隔离 worktree 中完成；但 `npm run test` 存在 1 个稳定失败用例，Playwright smoke 因缺少 `DSA_WEB_SMOKE_PASSWORD` 全部跳过，因此 `SAL-P0-005` 不得标记完成。

本任务只记录上游 Web 基线行为，不修改 `.worktrees/dsa-v3.26.1` 中的 DSA 源码、不修正测试期望，也不提交 `node_modules`、`static` 或 `test-results` 等生成产物。

## 2. 环境与版本

| 项目 | 结果 |
|---|---|
| DSA worktree | `.worktrees/dsa-v3.26.1` |
| DSA HEAD | `e8a9ca77`，detached at locked upstream baseline |
| Node | `v24.12.0`，满足 Web engines `>=20.19.0 <27` |
| npm | `11.6.2`，满足 Web engines `>=10` |
| Vite | `7.3.1` |
| Web package | `apps/dsa-web/package-lock.json` |

## 3. 执行记录

| 命令 | 结果 | 说明 |
|---|---|---|
| `scripts/bootstrap-dsa-baseline.ps1 -InstallWeb -InstallRetries 2` | 通过 | `npm ci` 安装 460 个 packages，audit 461 个 packages |
| `npm run lint` | 通过 | `eslint .` 返回 0 |
| `npm run test` | 失败 | 90 个测试文件中 89 通过、1 失败；967 个测试中 964 通过、1 失败、2 skipped |
| `npm run build` | 通过 | `tsc -b && vite build` 通过，3229 modules transformed，`vite build` 用时约 19.30s |
| `npm run test:smoke -- --reporter=line` | 无有效覆盖 | 13 个 Playwright 测试全部 skipped，命令返回 0 但不能作为 smoke 通过证据 |

## 4. Vitest 阻塞详情

失败用例：

```text
src/components/alerts/__tests__/AlertRuleForm.test.tsx
AlertRuleForm > shows JP/KR options for market region in Chinese UI mode
```

失败原因：中文 UI 的市场区域选项实际只有 `A 股（cn）`、`港股（hk）`、`美股（us）`，但该用例期望存在 `日股（jp）` 与 `韩股（kr）`。

同一测试文件中相邻用例又明确断言市场红绿灯规则不应出现 `日股（jp）` 与 `韩股（kr）`，与失败用例期望相互矛盾。当前源码 `src/locales/featureText.ts` 的 `ALERT_MARKET_REGION_OPTIONS` 也只定义了 `cn`、`hk`、`us` 三个区域。

该问题分类为上游测试/行为契约矛盾，不是本地依赖安装失败。解除前不能声明 Web Vitest 基线通过。

## 5. Playwright Smoke 阻塞详情

`npm run test:smoke -- --reporter=line` 启动了 13 个 Playwright 测试，但全部跳过。原因是 Web smoke 规范与 `playwright.config.ts` 都以 `DSA_WEB_SMOKE_PASSWORD` 作为执行条件：

- `e2e/smoke.spec.ts` 缺少该变量时跳过 authenticated smoke tests。
- `e2e/report-markdown.spec.ts` 缺少该变量时跳过 report markdown smoke tests。
- `playwright.config.ts` 仅在该变量存在时启动 backend 与 Vite webServer。

因此本次没有覆盖登录、初始化、分析页、历史页或关键页面截图；该命令返回 0 只能证明跳过逻辑生效，不能作为 Gate G0 的 Web smoke 通过证据。

## 6. 构建摘要

`npm run build` 已生成 `../../static/` 产物。主要 bundle 摘要如下：

| 产物 | 原始大小 | gzip |
|---|---:|---:|
| `assets/vendor-charts-BxScyN67.js` | 366.87 kB | 108.14 kB |
| `assets/SettingsPage-CTqhhHs0.js` | 300.74 kB | 98.67 kB |
| `assets/HomePage-Omgmpllf.js` | 205.46 kB | 62.89 kB |
| `assets/vendor-react-BzB2o5Ol.js` | 193.20 kB | 60.68 kB |
| `assets/index-bQzGTcS6.js` | 170.73 kB | 52.49 kB |
| `assets/index-gMNygBal.css` | 177.69 kB | 27.20 kB |

构建产物保留在被忽略的 DSA worktree 输出目录中，不纳入本项目提交。

## 7. 供应链提示

`npm ci` 后的 audit 摘要为 16 个漏洞：1 个 low、5 个 moderate、10 个 high。P0 基线阶段不直接运行 `npm audit fix`，避免修改上游 lockfile；该风险已登记到任务清单，后续由 `SAL-P0-011` 供应链基线和 `SAL-P6-005` 安全门禁继续处理。

## 8. 解除条件

- 明确市场区域 JP/KR 的期望行为：要么修正测试期望，要么补齐产品选项与后端契约，并留下上游兼容说明。
- 提供可用于本地 smoke 的 `DSA_WEB_SMOKE_PASSWORD`，并确认 backend webui-only 启动依赖已安装或可通过受控命令启动。
- 重新运行 `npm run test` 与 `npm run test:smoke -- --reporter=line`，记录真实通过数量、失败分类、截图/trace 或跳过豁免。
- 复核 10 个 high npm audit 项并在供应链登记中给出处理计划或批准的临时接受风险。

## 9. 不做事项

- 不把当前 Web 基线标记为 `DONE`。
- 不用 `npm audit fix` 改写上游 lockfile。
- 不跳过失败 Vitest 来伪造 Web 测试通过。
- 不把 13 个 skipped Playwright 用例当作 smoke 覆盖完成。
