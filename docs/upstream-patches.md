# DSA 上游补丁登记

> 目的：记录 Serenity Alpha Lab 在锁定 DSA release 上必须携带的最小兼容补丁。所有补丁都必须有 Characterization Test、应用脚本和验证证据；能通过扩展点解决的问题不得修改上游核心。

## 当前补丁

| Patch ID | 状态 | 上游基线 | 补丁文件 | 原因 | 验证 |
|---|---|---|---|---|---|
| DSA-PATCH-001 | APPLIED | `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` | `patches/dsa/v3.26.1/0001-isolate-intelligence-request-proxies.patch` | `IntelligenceService` 把模块级可变代理字典传给 `requests.get`，前序请求可污染后续离线测试，导致 `SAL-P0-004` full gate 顺序依赖失败 | `scripts/run-dsa-backend-offline-baseline.sh` 全 phase exit 0；`4455 passed, 4 deselected, 48 warnings, 416 subtests passed` |

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

## 应用方式

```bash
scripts/apply-dsa-baseline-patches.sh
scripts/run-dsa-backend-offline-baseline.sh
```

补丁只修改隔离 DSA worktree，不把上游源码混入本项目工作树。后续同步 DSA 新 release 时，应先检查上游是否已吸收等效修复；若已吸收，移除本地补丁并保留迁移记录。
