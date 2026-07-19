# DSA 上游补丁登记

> 目的：记录 Serenity Alpha Lab 在锁定 DSA release 上必须携带的最小兼容补丁。所有补丁都必须有 Characterization Test、应用脚本和验证证据；能通过扩展点解决的问题不得修改上游核心。

## 当前补丁

分类口径见根目录 [UPSTREAM_BASE.md](../UPSTREAM_BASE.md)：`compatible` 表示保持上游运行语义并修复基线阻断项，`extension` 表示 Serenity-only 脚本/证据/CI，`divergence` 表示改变上游运行或产品语义并需要 ADR/Gate 批准。

| Patch ID | 状态 | 分类 | 上游基线 | 补丁文件 | 原因 | 验证 |
|---|---|---|---|---|---|---|
| DSA-PATCH-001 | APPLIED | `compatible` | `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` | `patches/dsa/v3.26.1/0001-isolate-intelligence-request-proxies.patch` | `IntelligenceService` 把模块级可变代理字典传给 `requests.get`，前序请求可污染后续离线测试，导致 `SAL-P0-004` full gate 顺序依赖失败 | `scripts/run-dsa-backend-offline-baseline.sh` 全 phase exit 0；`4455 passed, 4 deselected, 48 warnings, 416 subtests passed` |
| DSA-PATCH-002 | APPLIED | `compatible` | `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` | `patches/dsa/v3.26.1/0002-align-alert-market-region-test-contract.patch` | `AlertRuleForm` 的一个 Vitest 用例要求 market-light 区域出现 `jp/kr`，但 Web `MarketRegion` 类型、alert labels 和相邻用例均只支持 `cn/hk/us`，导致 `SAL-P0-005` Web baseline 稳定失败 | 修复前 targeted Vitest `17 passed / 1 failed`；补丁后 `npm run test -- src/components/alerts/__tests__/AlertRuleForm.test.tsx` 为 `18 passed` |
| DSA-PATCH-003 | APPLIED | `compatible` | `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` | `patches/dsa/v3.26.1/0003-align-web-smoke-e2e-contract.patch` | Playwright smoke 真实执行后暴露 e2e 契约漂移：首次登录未填 `passwordConfirm`、首页侧栏已演进为“个股栏”、ReportMarkdown smoke 缺少历史报告 fixture、chat/settings 断言使用旧文案或非唯一 selector | `scripts/seed-dsa-web-smoke-fixture.sh` 生成本地 auth/history fixture；`npm run test:smoke -- --reporter=line` 真实执行 `13 passed` |

当前 P0 没有登记为 `divergence` 的补丁。若后续需要改变上游运行或产品语义，必须先补 ADR 或 Gate 评审记录。

## DSA-PATCH-001：隔离 Intelligence 请求代理参数

### 背景

`SAL-P0-004` 首轮完整后端离线测试中，`tests/test_intelligence_service.py::IntelligenceServiceTestCase::test_fetch_enabled_sources_is_fail_open` 在全量顺序下失败，单独运行通过。排查后发现 `_DISABLE_REQUEST_PROXIES = {"http": None, "https": None}` 是模块级可变字典，并被直接作为默认 `proxies` 传入 `requests.get`。前序 suite 活动会让该字典出现额外键 `use: "false"`，从而污染后续请求参数。

### 修改

- 新增 Characterization Test：`test_request_proxy_defaults_are_isolated_between_fetches`，在 fake `requests.get` 中主动污染第一次收到的 `proxies` 字典，要求第二次 fetch 仍收到干净代理默认值。
- 最小实现：`request_kwargs.setdefault("proxies", dict(_DISABLE_REQUEST_PROXIES))`，每次默认请求传递独立字典副本。
- 新增 `scripts/apply-dsa-baseline-patches.sh`，对 `.worktrees/dsa-v3.26.1` 幂等应用 `patches/dsa/v3.26.1/*.patch`。
- `scripts/run-dsa-backend-offline-baseline.sh` 在运行 gate 前自动应用登记补丁。

### 验证

| 命令 | 结果 |
|---|---|
| 修复前运行新增回归测试 | 失败，第二次请求代理参数包含 `use: "false"` |
| `pytest tests/test_intelligence_service.py::IntelligenceServiceTestCase::test_request_proxy_defaults_are_isolated_between_fetches -q --tb=short` | 通过 |
| `pytest tests/test_intelligence_service.py::IntelligenceServiceTestCase::test_fetch_enabled_sources_is_fail_open -q --tb=short` | 通过 |
| 前 55 个复现测试文件 + `tests/test_intelligence_service.py` | 通过，`1257 passed, 2 skipped, 12 warnings` |
| `scripts/run-dsa-backend-offline-baseline.sh` | 通过，syntax/flake8/deterministic/collect/offline-tests 全部 exit 0 |

## DSA-PATCH-002：对齐 Alert market region 测试契约

### 背景

`SAL-P0-005` Web 基线中，`src/components/alerts/__tests__/AlertRuleForm.test.tsx::shows JP/KR options for market region in Chinese UI mode` 稳定失败。失败断言要求市场区域下拉存在 `日股（jp）` 与 `韩股（kr）`，但当前 Web alert 类型 `MarketRegion` 仅为 `cn | hk | us`，`ALERT_MARKET_REGION_LABELS` 与 `ALERT_MARKET_REGION_OPTIONS` 也只列出 A 股、港股和美股。同一测试文件相邻用例明确断言 market-light 规则不展示 JP/KR。

### 修改

- 将错误用例改名为 `limits market region options to supported market-light regions in Chinese UI mode`。
- 保留 `A 股（cn）`、`港股（hk）`、`美股（us）` 的可见性断言。
- 将 `日股（jp）`、`韩股（kr）` 从存在断言改为不存在断言，与类型定义和英文 UI 用例一致。

### 验证

| 命令 | 结果 |
|---|---|
| 修复前 `npm run test -- src/components/alerts/__tests__/AlertRuleForm.test.tsx` | 失败，`17 passed / 1 failed`，无法找到 `日股（jp）` option |
| 补丁后 `npm run test -- src/components/alerts/__tests__/AlertRuleForm.test.tsx` | 通过，`18 passed` |
| `scripts/apply-dsa-baseline-patches.sh --check-only` | 通过，`0001`、`0002` 和 `0003` 均识别为 already applied |

## DSA-PATCH-003：对齐 Web smoke E2E 契约

### 背景

`SAL-P0-005` 在设置 `DSA_WEB_SMOKE_PASSWORD` 后，Playwright smoke 不再跳过，但真实执行暴露出 e2e 契约漂移：登录 helper 只填写 password、不处理首次设置密码确认框；首页已从旧“历史分析”列表演进为“个股栏”工作区；ReportMarkdown 用例依赖历史报告但 smoke 环境没有固定 fixture；chat/settings 部分断言使用过时文案或非唯一 selector。

### 修改

- 登录 helper 在首次设置状态下填充 `#passwordConfirm`，同时保持已有密码登录路径不变。
- 首页 smoke 改为断言当前“个股栏”工作区及“历史/自选/今日”页签。
- chat smoke 使用 `chat-skill-picker-panel` 内的“策略”标题，避免 strict mode 命中多个元素。
- settings 英文语言切换 smoke 改为断言当前默认设置页的 `Reset`、`Save configuration` 与 `First-run setup check`。
- ReportMarkdown smoke 通过 `openFirstHistoryReport()` 明确打开本地 fixture 历史报告，并兼容移动端已自动选中报告的布局。
- 新增 `scripts/seed-dsa-web-smoke-fixture.sh`，在 `.cache/dsa-p0/web-smoke` 生成本地 auth password、env file 与 `600519` 历史报告 fixture。

### 验证

| 命令 | 结果 |
|---|---|
| 未预置密码/fixture 的真实 smoke | 失败，登录首次设置和历史报告 fixture 缺失导致 11 个用例失败 |
| 预置密码但未修 e2e 契约的 smoke | 失败，旧“历史分析”文案、chat strict selector、settings 旧按钮文案等导致 7 个用例失败 |
| 补丁后 `scripts/seed-dsa-web-smoke-fixture.sh` | 通过，生成/复用本地 smoke env、auth password 与历史报告 fixture |
| 补丁后 `npm run test:smoke -- --reporter=line` | 通过，`13 passed`，无 skipped |
| `npm run lint` / `npm run build` / `npm run test` | 通过；Vitest `90 passed` files，`965 passed, 2 skipped` |

## 应用方式

```bash
scripts/apply-dsa-baseline-patches.sh
DSA_WEB_SMOKE_PASSWORD=p0-smoke-password scripts/seed-dsa-web-smoke-fixture.sh
scripts/run-dsa-backend-offline-baseline.sh
```

补丁只修改隔离 DSA worktree，不把上游源码混入本项目工作树。后续同步 DSA 新 release 时，应先检查上游是否已吸收等效修复；若已吸收，移除本地补丁并保留迁移记录。
