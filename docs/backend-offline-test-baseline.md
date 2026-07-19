# DSA 后端离线测试基线记录

> 任务：`SAL-P0-004` 建立后端离线测试基线<br>
> 执行日期：2026-07-19<br>
> 上游基线：`upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 当前状态：`DONE`

## 1. 执行结论

`SAL-P0-004` 已完成。当前本机隔离 DSA worktree 可通过后端离线 gate：`syntax`、`flake8`、`deterministic`、`collect` 和 `offline-tests` 全部返回 0。离线测试最终结果为 `4455 passed, 4 deselected, 48 warnings, 416 subtests passed in 142.10s`。

本次不是跳过失败用例。首轮完整 gate 曾稳定失败于 `tests/test_intelligence_service.py::IntelligenceServiceTestCase::test_fetch_enabled_sources_is_fail_open`，根因为 DSA `IntelligenceService` 把模块级可变 `_DISABLE_REQUEST_PROXIES` 字典直接传给 `requests.get`，前序请求会污染该共享字典并导致后续测试的代理参数断言失败。已按项目接管约定新增本地上游兼容补丁 `DSA-PATCH-001`，补 Characterization Test 后最小修复为每次请求传递 `dict(_DISABLE_REQUEST_PROXIES)`。

## 2. 环境与补丁

| 项目 | 值 |
|---|---|
| DSA baseline | `upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| DSA worktree | `.worktrees/dsa-v3.26.1` |
| Python | `3.11.15` |
| pip | `26.1.2` |
| pytest | `9.1.1` |
| flake8 | `7.3.0` |
| AlphaSift | `0.2.0` |
| Python test files | `232` |
| Local patch | `patches/dsa/v3.26.1/0001-isolate-intelligence-request-proxies.patch` |
| Patch apply script | `scripts/apply-dsa-baseline-patches.sh` |
| Gate wrapper | `scripts/run-dsa-backend-offline-baseline.sh` |
| Artifact dir | `.cache/dsa-p0/backend-offline-artifacts/` |

## 3. Gate 结果

| Phase | 命令 | Exit | Duration |
|---|---|---:|---:|
| syntax | `bash scripts/ci_gate.sh syntax` | 0 | 0s |
| flake8 | `bash scripts/ci_gate.sh flake8` | 0 | 4s |
| deterministic | `bash scripts/ci_gate.sh deterministic` | 0 | 3s |
| collect | `python -m pytest -m "not network" --collect-only -q` | 0 | 8s |
| offline-tests | `bash scripts/ci_gate.sh offline-tests` | 0 | 145s |

收集阶段输出：`4455/4459 tests collected (4 deselected) in 6.69s`。完整离线测试输出：`4455 passed, 4 deselected, 48 warnings, 416 subtests passed in 142.10s`。当前上游 `ci_gate.sh offline-tests` 未生成 JUnit 或 coverage 文件，因此本任务的可复跑证据以 wrapper summary、phase logs、test inventory 和环境记录为准。

## 4. Red/Green 证据

| 验证 | 结果 |
|---|---|
| 新增 `test_request_proxy_defaults_are_isolated_between_fetches` 后、修复前运行 | 失败，第二次请求收到 `{'http': None, 'https': None, 'use': 'false'}` |
| 修复后运行新增回归测试 | 通过，`1 passed, 1 warning` |
| 修复后运行原始失败用例 `test_fetch_enabled_sources_is_fail_open` | 通过，`1 passed, 1 warning` |
| 修复后重跑原复现组合：前 55 个测试文件 + `test_intelligence_service.py` | 通过，`1257 passed, 2 skipped, 12 warnings` |
| 修复后运行完整 wrapper `scripts/run-dsa-backend-offline-baseline.sh` | 通过，所有 phase exit 0 |

## 5. Artifact

| Artifact | 用途 |
|---|---|
| `.cache/dsa-p0/backend-offline-artifacts/summary.md` | phase exit code 与耗时摘要 |
| `.cache/dsa-p0/backend-offline-artifacts/environment.txt` | Python、pip、pytest、flake8、AlphaSift 版本 |
| `.cache/dsa-p0/backend-offline-artifacts/test-inventory.txt` | 测试文件数量与 pytest marker 摘要 |
| `.cache/dsa-p0/backend-offline-artifacts/collect.log` | collect-only 输出与 warning |
| `.cache/dsa-p0/backend-offline-artifacts/offline-tests.log` | 完整 offline-tests 输出 |
| `.cache/dsa-p0/backend-offline-artifacts/syntax.log` | syntax gate 输出 |
| `.cache/dsa-p0/backend-offline-artifacts/flake8.log` | flake8 gate 输出 |
| `.cache/dsa-p0/backend-offline-artifacts/deterministic.log` | deterministic gate 输出 |

## 6. 不做事项与限制

- 不把 `.worktrees/dsa-v3.26.1` 或 `.cache/dsa-p0` 下生成产物提交到本项目。
- 不将 `SAL-P0-005`、`SAL-P0-011` 或 Gate G0 标记为完成；Web 与供应链基线仍需单独解除阻塞。
- 不修改 AlphaSift 依赖锁定策略；Python SBOM、镜像 SBOM 和漏洞摘要仍归属 `SAL-P0-011`。
- 当前保留上游测试 warning 作为基线事实，不在本任务内做 unrelated refactor。
