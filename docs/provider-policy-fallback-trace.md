# Provider Policy 与 Fallback Trace 记录

> 任务：`SAL-P2-015` 实现 Provider Policy 与 fallback trace<br>
> 日期：2026-07-23<br>
> Phase：P2 数据与持久任务<br>
> Gate：G2 未通过<br>
> 代码：`src/serenity_alpha_lab/integrations/data/provider_policy.py`<br>
> 测试：`tests/integrations/test_provider_policy.py`

## 1. 范围

本任务新增全离线 Provider Policy 层，消费已经归一化的 `DataBatch` 与 `ProviderError`，按能力、市场、新鲜度、必需字段、质量状态和跨源冲突阈值做选择，并输出可持久化的 fallback trace。

覆盖范围：

- Policy：通过 YAML-compatible mapping 定义 `policy_id`、市场、Dataset、Provider priority、source capabilities、source quality score 和 cross-check 阈值。
- Selection：按 policy priority 遍历符合 market/capability 的候选 source，选择第一个新鲜、字段完整且质量状态未阻断的 `DataBatch`。
- Fallback：成功返回的数据若已 stale、缺少必需字段、质量状态为 `quarantine/blocking`，仍会被拒绝并尝试下一来源。
- Provider error：`retryable`、`schema_drift`、`data_invalid` 等 `ProviderError` 被记录为 `provider_<category>`，不会被吞掉或改写成成功。
- Dataset guard：`ProviderSelectionRequest.dataset_name` 必须匹配 policy dataset，避免把错误 Dataset 的请求套用到日线 Provider policy。
- Cross-check：当配置 `cross_check_provider` 与 `max_close_diff_bps` 时，同一证券/日期的 `close` 差异超阈值进入 `quarantine`，不做平均值或静默覆盖。
- Trace：每次决策输出 attempted order、attempts、selected provider、conflicts、trace/run/stage 标量和 raw-response hash。

## 2. 实现口径

| 类型 / 函数 | 作用 |
|---|---|
| `ProviderPolicy` | YAML-compatible policy DTO，支持 `from_mapping()` 和 deterministic `to_record()`。 |
| `ProviderPolicySource` | 记录 provider 支持的 market/capability 和 source quality score。 |
| `ProviderSelectionRequest` | 单次选择请求，携带 market、capability、required fields、evaluation time、质量状态和 trace/run/stage。 |
| `ProviderPolicyEngine` | 对注入的离线 `DataBatch` / `ProviderError` outcomes 执行选择；不调用 Provider SDK。 |
| `ProviderFallbackAttempt` | 记录单个 source 的 selected/rejected/quarantined 状态、原因、缺字段、质量状态、freshness 和 raw-response hash。 |
| `ProviderConflictRecord` | 记录跨源字段冲突、主键、provider values、观察 bps 差异、阈值和 `quarantine` 处置。 |
| `ProviderFallbackTrace` | 记录可序列化 Run Diagnostics 载荷。 |
| `ProviderSelectionResult` | 返回最终状态：`selected`、`quarantined` 或 `exhausted`。 |

## 3. 策略语义

示例 policy 仍保持 YAML-compatible，不引入 YAML 解析依赖：

```yaml
policy_id: cn-bars-fixture-policy
market: cn
dataset: bars_1d
priority: [akshare, efinance, tushare, baostock]
sources:
  akshare:
    markets: [cn]
    capabilities: [daily_bars]
    quality_score: 0.95
validation:
  cross_check_provider: tushare
  max_close_diff_bps: 5.0
```

决策规则：

- Provider 不在 policy priority 或不支持目标 market/capability 时不会被选择。
- Request dataset 与 policy dataset 不一致时直接抛出 `ProviderPolicyError`，不会尝试任何来源。
- `DataBatch.fresh_until < evaluation_time` 判为 `stale`，即使 Provider 返回成功也触发 fallback。
- 任一必需字段在任一记录缺失或为 `None`，判为 `missing_fields`。
- `DataQualityStatus.QUARANTINE` / `BLOCKING` 判为 `quality_quarantine` / `quality_blocking`；`WARNING` 只进入 trace，不自动提升 latest 或阻断选择。
- Provider 错误全部保留 category，形成 `provider_retryable`、`provider_schema_drift`、`provider_data_invalid` 等 trace reason。
- Cross-check 超阈值时返回 `ProviderPolicyStatus.QUARANTINED`，`selected_batch=None`，避免把冲突数据伪装成成功。

## 4. 安全与边界

- 本层不导入 AKShare、efinance、Tushare、BaoStock、YFinance SDK。
- 本层不调用 DSA `DataFetcherManager`，不访问网络，不执行真实 Provider/LLM 调用。
- 本层不写 Bronze、Dataset Catalog、Publication、Run/Event 存储或数据库；只返回可由后续 Worker/Diagnostics 持久化的纯 DTO。
- 本层不启动 PersistentTaskBackend、Worker runtime、Quant Core、正式回测、Evidence Agent、定时探针或大规模 DSA runtime source migration。
- Cross-provider conflict 只能 quarantine；不能通过平均、覆盖或忽略差异来继续发布成功结果。

## 5. 验证证据

| 验证 | 结果 |
|---|---|
| Red：policy module | `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_policy.py -q` 先以 `ModuleNotFoundError: No module named 'serenity_alpha_lab.integrations.data.provider_policy'` 失败。 |
| Green：target | `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_policy.py -q`，`6 passed`。 |
| Green：related | `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_policy.py tests/integrations/test_provider_contract_fixtures.py tests/domain/test_provider_contract.py tests/datasets/test_data_quality.py tests/datasets/test_dataset_publication.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q`，`59 passed`。 |
| Green：full pytest | `uv run --extra core --extra dev python -m pytest -q`，`209 passed`。 |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests`，PASS。 |
| Dependency lock | `scripts/verify-python-dependency-lock.sh`，PASS。 |
| Diff check | `git diff --check`，PASS。 |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1`，`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。 |

## 6. 后续衔接

`SAL-P2-016` 可以在本 policy trace 上实现增量同步与交易日调度：调度层负责 checkpoint、回看窗口、锁和补数；本层保持纯离线选择和诊断，不承担 Worker 生命周期、真实 Provider 调用或 Dataset 发布事务。
