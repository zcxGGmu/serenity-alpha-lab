# DSA Web 测试与构建基线记录

> 任务：`SAL-P0-005` 建立 Web 测试与构建基线<br>
> 执行日期：2026-07-19<br>
> 上游基线：`upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 当前状态：`DONE`

## 1. 执行结论

`SAL-P0-005` 已解除阻塞。Web 依赖安装、lint、Vitest、Vite build 与真实 Playwright smoke 均已在锁定 DSA worktree 中完成。阻断项通过登记补丁处理：`DSA-PATCH-002` 对齐 Alert market region 测试契约，`DSA-PATCH-003` 对齐 Web smoke E2E 与当前 UI/fixture 契约。

本任务没有运行 `npm audit fix`，没有改写上游 lockfile，也没有把 `.worktrees`、`node_modules`、`static`、Playwright `test-results`、`.cache` 或截图产物纳入提交。

## 2. 环境与版本

| 项目 | 结果 |
|---|---|
| DSA worktree | `.worktrees/dsa-v3.26.1` |
| DSA HEAD | `e8a9ca77`，detached at locked upstream baseline |
| Node | `v24.12.0`，满足 Web engines `>=20.19.0 <27` |
| npm | `11.6.2`，满足 Web engines `>=10` |
| Vite | `7.3.1` |
| Web package | `apps/dsa-web/package-lock.json` |
| 本地 smoke env | `.cache/dsa-p0/web-smoke/.env`，由 `scripts/seed-dsa-web-smoke-fixture.sh` 生成 |

## 3. 执行记录

| 命令 | 结果 | 说明 |
|---|---|---|
| `npm ci` | 通过 | 安装 461 个 packages；audit 仍为 16 个漏洞（1 low、5 moderate、10 high） |
| `scripts/apply-dsa-baseline-patches.sh --check-only` | 通过 | `0001`、`0002`、`0003` 均识别为 already applied |
| `npm run test -- src/components/alerts/__tests__/AlertRuleForm.test.tsx` | 通过 | 1 个文件、18 个测试通过 |
| `npm run lint` | 通过 | `eslint .` 返回 0 |
| `npm run build` | 通过 | `tsc -b && vite build` 通过，3229 modules transformed |
| `npm run test` | 通过 | 90 个测试文件通过；965 passed、2 skipped |
| `scripts/seed-dsa-web-smoke-fixture.sh` | 通过 | 创建/复用本地 auth password 与 `600519` 历史报告 fixture |
| `npm run test:smoke -- --reporter=line` | 通过 | 13 个 Playwright tests 真实执行并通过，未 skipped |

## 4. 本地补丁

### DSA-PATCH-002：Alert market region 测试契约

失败用例原先要求中文市场区域选项存在 `日股（jp）` 与 `韩股（kr）`，但当前 Web `MarketRegion` 类型、`ALERT_MARKET_REGION_OPTIONS` 与相邻用例均只支持 `cn`、`hk`、`us`。该问题分类为上游测试契约矛盾，而不是产品选项缺失。

处理方式：将用例改为断言 market-light 区域仅展示 A 股、港股、美股，并明确 JP/KR 不展示。修复前 targeted Vitest 为 `17 passed / 1 failed`；修复后为 `18 passed`。

### DSA-PATCH-003：Web smoke E2E 契约

真实 smoke 首轮暴露三类测试契约问题：

- 登录 helper 未处理首次设置密码的 `passwordConfirm` 输入。
- 首页侧栏已由旧“历史分析”列表演进为“个股栏”工作区，旧 selector 失效。
- ReportMarkdown smoke 依赖历史报告，但原 smoke 环境没有 fixture；chat/settings 部分断言使用了过时文案或非唯一 selector。

处理方式：补丁只修改 e2e specs，不改产品实现；新增 `scripts/seed-dsa-web-smoke-fixture.sh` 在 `.cache/dsa-p0/web-smoke` 生成本地 auth/env/SQLite fixture，确保 Playwright 覆盖登录、首页分析入口、问股页、移动导航、设置页、回测页和 Markdown 报告复制路径。

## 5. 构建摘要

`npm run build` 已生成 `../../static/` 产物。主要 bundle 摘要如下：

| 产物 | 原始大小 | gzip |
|---|---:|---:|
| `assets/vendor-charts-BxScyN67.js` | 366.87 kB | 107.88 kB |
| `assets/SettingsPage-F7BNzGFb.js` | 300.74 kB | 97.27 kB |
| `assets/HomePage-CLRT5BZX.js` | 205.46 kB | 62.62 kB |
| `assets/vendor-react-BzB2o5Ol.js` | 193.20 kB | 60.61 kB |
| `assets/index-CQEA9A3U.js` | 170.73 kB | 52.08 kB |
| `assets/index-gMNygBal.css` | 177.69 kB | 27.19 kB |

构建产物保留在被忽略的 DSA worktree 输出目录中，不纳入本项目提交。

## 6. 供应链提示

`npm ci` 后的 audit 摘要仍为 16 个漏洞：1 个 low、5 个 moderate、10 个 high。P0 基线阶段不直接运行 `npm audit fix`，避免修改上游 lockfile；该风险已由 `SAL-P0-011` 供应链基线登记，后续由 `SAL-P6-005` 安全门禁关闭或豁免。

## 7. 复跑方式

```bash
scripts/apply-dsa-baseline-patches.sh
DSA_WEB_SMOKE_PASSWORD=p0-smoke-password scripts/seed-dsa-web-smoke-fixture.sh

cd .worktrees/dsa-v3.26.1/apps/dsa-web
npm run lint
npm run build
npm run test
ENV_FILE=/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/.cache/dsa-p0/web-smoke/.env \
DATABASE_PATH=/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/.cache/dsa-p0/web-smoke/stock_analysis.db \
ADMIN_AUTH_ENABLED=true \
DSA_WEB_SMOKE_PASSWORD=p0-smoke-password \
DSA_WEB_SMOKE_BACKEND_CMD="/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/.cache/dsa-p0/venv/bin/python main.py --webui-only --host 127.0.0.1 --port 8000" \
npm run test:smoke -- --reporter=line
```

## 8. 不做事项

- 不把 npm audit high 风险当作已修复；只记录 baseline。
- 不用 `npm audit fix` 或 `npm update` 改写上游 lockfile。
- 不提交本地 smoke password、SQLite DB、Playwright trace、截图或 generated static assets。
- 不把 `SAL-P0-005` 的完成解释为 Gate G0 完成；G0 仍依赖 `SAL-P0-008` 至 `SAL-P0-013`。
