# Qlib 版本锁定与隔离方案

> 任务：`SAL-P4-005` 锁定 Qlib 版本与隔离方案<br>
> 日期：2026-07-25<br>
> 前置任务：[`SAL-P4-003` BacktestSpec](./backtest-spec.md)、[`SAL-P4-004` BacktestArtifact](./backtest-artifact.md)<br>
> 结论：`APPROVED FOR SAL-P4-006 DATASET CONVERSION ONLY`

## 1. 交付结论

`SAL-P4-005` 已把 Qlib 接入推进到可审计的依赖与隔离策略状态，但没有启动 Qlib runtime。正式组合回测仍必须等待后续 P4 任务完成 Dataset 转换、Qlib Adapter、订单状态机、Ledger、费用/滑点、A 股执行规则、公司行动入账、RiskPolicy、偏差审计、绩效指标、BacktestRun 编排和资源控制。

```yaml
task: SAL-P4-005
package_name: pyqlib
locked_version: 0.9.7
pyproject_requirement: pyqlib==0.9.7
license_spdx: MIT
requires_python: ">=3.8.0"
approved_python: ">=3.11,<3.13"
runtime_scope: quant_worker_only
worker_queue: worker-quant
production_requirements_contains_pyqlib: false
formal_backtest_started: false
qlib_runtime_started: false
real_provider_calls_zero: true
real_llm_calls_zero: true
```

## 2. 版本与安装面

| 表面 | 决策 |
|---|---|
| Serenity root dependency | 不使用默认依赖；`project.dependencies` 仍为空 |
| `core + providers + desktop` | 不安装 Qlib；`requirements.txt` 不包含 `pyqlib` |
| `quant` extra | 精确锁定 `pyqlib==0.9.7`，同时保留 `polars`、`pyarrow`、`duckdb` |
| Lock file | `uv.lock` 记录 `pyqlib 0.9.7` wheel hash |
| Runtime import | 仅后续 Quant Worker Adapter 可延迟 import；本任务新增 policy 模块不 import `qlib` |

`pyqlib==0.9.7` 是本轮锁定版本；后续任何升级必须走 ADR-009 的升级流程，不能把 `>=` 范围依赖带入生产解析。

## 3. 许可证与依赖

PyPI metadata 将 `pyqlib 0.9.7` 分类为 MIT License；当前平台计划可在保留版权和许可证文本前提下接入。该结论只覆盖 Qlib 软件包本身，不覆盖行情数据、模型、第三方数据源、交易所规则或用户上传策略代码。

直接 runtime dependencies：

```text
pyyaml
numpy
pandas>=0.24
mlflow
filelock>=3.16.0
redis
dill
fire
ruamel.yaml>=0.17.38
python-redis-lock
tqdm
pymongo
loguru
lightgbm
gym
cvxpy
joblib
matplotlib
jupyter
nbconvert
pyarrow
pydantic-settings
```

依赖处理结论：

- `SAL-P4-005` 不新增 Qlib SBOM 或内部 wheelhouse；它锁定 root quant extra 与 lock evidence。
- 发布前仍需 `SAL-P6-005` 或等效供应链门禁对 Quant Worker 镜像执行完整 SBOM、license inventory 和 vulnerability scan。
- Qlib 的 `mlflow`、`redis`、`pymongo`、`jupyter`、`lightgbm`、`cvxpy` 等依赖较重，必须保留在 Quant Worker 镜像/环境内，不进入 FastAPI 或 Desktop core。

## 4. 平台兼容

PyPI wheel metadata 覆盖 CPython 3.11 和 3.12 的以下平台。生产初始支持口径明确锚定为 manylinux2014 x86_64；macOS/Windows 仅作为本地开发或后续验证入口。

| 平台 | Wheel |
|---|---|
| macOS universal2 | `pyqlib-0.9.7-cp311-cp311-macosx_10_9_universal2.whl`、`pyqlib-0.9.7-cp312-cp312-macosx_10_13_universal2.whl` |
| Linux worker | `pyqlib-0.9.7-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`、`pyqlib-0.9.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` |
| Windows amd64 | `pyqlib-0.9.7-cp311-cp311-win_amd64.whl`、`pyqlib-0.9.7-cp312-cp312-win_amd64.whl` |

Production Quant Worker support is initially limited to Linux x86_64 container images. macOS is allowed for local development and contract tests. Windows wheel availability does not mean Desktop core installs or initializes Qlib; Windows support remains non-default until a later Worker/profile task validates it. Qlib may run only in a dedicated Quant Worker process.

## 5. Worker 隔离策略

新增 policy module：

```text
src/serenity_alpha_lab/integrations/qlib/runtime_policy.py
```

默认资源与边界：

| 字段 | 值 |
|---|---:|
| `queue_name` | `worker-quant` |
| `process_isolation` | `dedicated_process` |
| `max_cpu_cores` | `2` |
| `max_memory_mb` | `4096` |
| `wall_clock_timeout_seconds` | `3600` |
| `heartbeat_interval_seconds` | `15` |
| `checkpoint_interval_seconds` | `300` |

硬约束：

- must not initialize Qlib in FastAPI。
- must not import Qlib in domain、application、datasets、providers、reports 或 DSA compatibility facades。
- must not call `qlib.init` at module import time。
- must not accept arbitrary Python module path from API、UI、YAML 或 strategy payload。
- must require persisted `run_id` / `stage_id` / trace context before Quant Worker work starts。
- must emit heartbeat and checkpoint records through the later `SAL-P4-018` resource/cancel/checkpoint implementation。

## 6. 后续任务边界

`SAL-P4-006` 可以开始 Dataset -> Qlib calendar/instrument/feature 转换，但仍只能处理离线、已发布、passed 的不可变 Dataset Version，并记录双向字段 lineage。`SAL-P4-007` 才能包装 Qlib Adapter；该任务仍不得让 Qlib 配置接受 arbitrary module path。

This task must not start formal portfolio backtest runs, must not initialize Qlib in FastAPI, must not call real Provider, must not call real LLM, must not start Evidence Agent, must not start Ledger/Risk/Quant Lab, and must not start Worker loop.

Legacy DSA `legacy_signal_evaluation`、AlphaSift T+N evaluation 和 Screen result 继续只作为信号评价或筛选结果，不得直接命名为正式组合回测。

## 7. 升级与停用条件

Qlib 升级必须同时满足：

- 新版本有明确 PyPI version、wheel hashes、license metadata 和 direct dependency diff。
- `uv lock`、`requirements.txt` drift guard、architecture tests 和 Qlib isolation policy tests 通过。
- 重新生成 Quant Worker SBOM、license inventory 和 vulnerability report。
- 后续固定 Dataset/Strategy golden 比较预测 hash、订单、净值、指标和审计 Artifact。
- 资源回归覆盖 timeout、OOM、取消、checkpoint 和 Worker 重投。

满足任一条件时停止使用 Qlib 或阻塞升级：

- Qlib import 进入 FastAPI、domain、application、datasets 或 provider path。
- Qlib 配置接受 arbitrary Python module path。
- `pyqlib` 出现在 production/Desktop `requirements.txt`。
- Qlib 结果绕过 `BacktestSpec`、`BacktestArtifact`、Dataset Version、Run/Stage/Event 或 ArtifactStore。
- License/SCA/平台兼容风险无法在 Gate G4/G6 前关闭或豁免。

## 8. 验证记录

| 验证 | 结果 |
|---|---|
| `uv run --extra core --extra dev python -m pytest tests/architecture/test_qlib_version_isolation.py -q` | Red：初始 `4 failed, 1 passed`，缺少 exact pin、Qlib doc、ADR 和 policy module；Green 结果见本任务最终 review |
| `uv lock --check` | Red 前 PASS，确认当前 lock 可解析 |
| `uv run --extra core --extra dev python - <<'PY' ... PyPI metadata ...` | PASS，记录 `pyqlib 0.9.7` license classifier、requires-python、direct dependencies 和 wheel hashes |

## 9. 本任务未做事项

- 未启动正式组合回测。
- 未调用 `qlib.init`。
- 未转换 Dataset 到 Qlib 格式。
- 未实现 Qlib QuantEngine Adapter。
- 未生成订单、成交、持仓、现金、净值、指标或偏差审计。
- 未启动 Ledger、Risk、Quant Lab、Evidence Agent 或 Worker loop。
- 未调用真实 Provider 或真实 LLM。
- 未改动 legacy `/api/v1/backtest/*` 兼容面。
