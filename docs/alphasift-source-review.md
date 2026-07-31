# AlphaSift 源码审查与锁定记录

> 任务：`SAL-P3-001` 审查并锁定 AlphaSift<br>
> 日期：2026-07-23<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-002 WHEEL INTAKE ONLY`

## 1. 版本决策

```yaml
source_repository: https://github.com/ZhuLinsen/alphasift
locked_source_commit: 9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf
default_branch: main
commit_date_utc: 2026-07-03T12:30:38Z
commit_subject: "[codex] enrich strategy catalog metadata (#37)"
source_archive_sha256: 4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a
source_archive_size_bytes: 300697
package_name: alphasift
version: 0.2.0
license_spdx: Apache-2.0
requires_python: >=3.10
```

本任务锁定源码 commit `9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`，不锁定 `v0.2.0` tag。原因：

- DSA `v3.26.1` 的 AlphaSift 安装 pin 已使用同一 commit：`git+https://github.com/ZhuLinsen/alphasift.git@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf#egg=alphasift`。
- AlphaSift `v0.2.0` tag 指向较旧 commit `f2c2ca22ae3fcb18b0273b8494a9e055d82c01e0`，日期为 `2026-04-28T14:51:23Z`。
- GitHub compare 显示锁定 commit 相对 `v0.2.0` ahead `67` commits、behind `0`，包含 DSA adapter、source health、fallback、hotspot 和 strategy catalog 等 DSA 已记录能力。
- `pyproject.toml` 仍声明 `version: 0.2.0`，但该版本号没有区分 tag 与后续 67 个 commit；因此 `SAL-P3-002` 构建内部 Wheel 时必须把 commit hash 写入 wheel provenance、SBOM 和制品命名/元数据，不能只依赖 `0.2.0` 版本号。

## 2. 许可证与 NOTICE

- GitHub license metadata 和仓库 `pyproject.toml` 均标记 `license_spdx: Apache-2.0`。
- 选定 commit 包含根目录 `LICENSE`，文件大小 `10258` bytes，内容为 Apache License 2.0 正文。
- 选定 commit 未发现独立 `NOTICE` 文件；`SAL-P3-002` 构建内部 Wheel 时必须至少随制品保留 `LICENSE`。如果后续 AlphaSift 或其依赖出现 `NOTICE` / attribution 文件，必须同步纳入发布包与许可证清单。
- Apache-2.0 与当前平台计划相容；但它不自动覆盖行情数据源、LLM Provider、Tushare token、AkShare/efinance/BaoStock/YFinance/TickFlow 等服务条款，数据服务条款仍由 `RSK-005` 和 `SAL-P6-005` 发布门禁审查。

## 3. 依赖清单

从锁定 commit 的 `pyproject.toml` 读取：

```yaml
build_system:
  - setuptools>=68.0
runtime_dependencies:
  - pandas>=2.0
  - pyyaml>=6.0
  - litellm>=1.0
  - efinance>=0.4
  - akshare>=1.10
  - baostock>=0.8.9
  - tushare>=1.4
  - yfinance>=0.2
  - requests>=2.28
dev_dependencies:
  - pytest
  - ruff
console_scripts:
  - alphasift=alphasift.cli:main
package_data:
  - alphasift/strategies/*.yaml
  - SKILL.md
  - .env.example
  - LICENSE
  - agents/openai.yaml
```

依赖处理结论：

- `SAL-P3-001` 不把 AlphaSift 加入 Serenity root `pyproject.toml`、`uv.lock` 或生产 `requirements.txt`。
- `SAL-P3-002` 必须从锁定 commit 构建离线内部 Wheel，生成 wheel hash、source archive hash、SBOM 和许可证清单后，才能把它纳入受控安装面。
- 当前依赖均为范围约束，range dependencies are not a release lock；后续 Wheel intake 必须解析并冻结具体版本，不允许生产构建时动态 `git+https` 安装或浮动解析。

## 4. 漏洞与维护风险

本次运行的轻量 SCA：

```text
uvx --python 3.11 --from pip-audit pip-audit --requirement <alphasift-runtime-requirements> --progress-spinner off --format json
```

结果：

```yaml
pip_audit_current_resolution: 0 known vulnerabilities
resolved_dependency_count: 86
scanner_scope: declared runtime dependencies resolved at scan time
```

限制：

- AlphaSift itself is not PyPI-auditable；`pip-audit` 无法直接查询 GitHub 源码包自身的漏洞数据库记录。
- 首次尝试 `uvx --from pip-audit` 默认使用 Python 3.13，临时 venv `ensurepip` 以 `SIGABRT` 失败；已固定 `--python 3.11` 重跑并得到上述结果。
- 该扫描不是发布级 SBOM，也不是锁文件审计；它只证明当前解析出的依赖面没有已知 PyPI 漏洞。
- GitHub 仓库当前未归档，默认分支为 `main`；截至本次审查，open issues 为 `2`，open PR 为 `1`（`#38 fix: make LLM ranking completeness explicit`），主要贡献者集中在 `ZhuLinsen`。维护风险为中等：可用于受控插件 intake，但需要内部 Wheel、契约测试和替换策略兜底。

## 5. Known limitations

- AlphaSift 是候选发现与快照筛选插件，不是时点数据湖、正式因子引擎、组合回测系统或风控引擎。
- README 明确项目用于学习、研究和工程实验，不构成投资建议、收益承诺或买卖指令。
- 它可使用 AkShare、efinance、BaoStock、Tushare、YFinance、requests 和 LiteLLM；这些外部数据/模型路径不得进入 CI 默认路径或未受 guard 的生产路径。
- LLM ranking 是可选 overlay；在 Serenity 中默认不得覆盖确定性硬过滤和因子原始值。
- T+N evaluation 只能映射为 `CandidateOutcomeEvaluation` 或筛选后验，不能标记为 `PortfolioBacktest`。
- AlphaSift must not replace Dataset Catalog、must not replace PIT Dataset、must not replace Provider Policy；它只能消费后续 `ScreeningProvider` 契约允许的快照/候选输入。

## 6. 平台接入边界

`SAL-P3-001` 只批准进入 `SAL-P3-002` 的离线 Wheel intake，不批准直接运行或适配：

- must not start Quant Core。
- must not start formal backtesting。
- must not start Evidence Agent。
- 不调用真实 Provider 或真实 LLM；后续真实调用仍必须通过 Runtime Profile guard、离线契约、fallback trace 和 Worker/调度任务接入。
- 不绕过 P2 Dataset Catalog/Manifest、Quality Gate、Provider Policy/fallback trace、TraceContext、ProblemDetails、ArtifactStore 或 Run/Stage/Event。
- 不把 AlphaSift 内部类泄漏到 platform domain/application；`SAL-P3-003` 必须通过 `ScreeningProvider` 隔离。

## 7. Upgrade conditions

后续升级 AlphaSift 必须同时满足：

- 新 commit 或 tag 有明确 hash、source archive SHA-256、许可证和依赖差异记录。
- 与当前锁定 commit 做 compare，列出 adapter contract、数据源、策略 schema、LLM 行为和输出字段变化。
- 重新运行 Wheel build、SBOM、license inventory、`pip-audit`/SCA、contract tests 和 P3 相关 golden tests。
- 若新增真实数据源、LLM provider、网络调用路径或服务条款风险，必须更新风险登记并通过 profile guard。

## 8. Replacement conditions

满足任一条件时，应优先替换为自研筛选器或更窄的内部 adapter：

- AlphaSift 无法稳定离线构建，或无法提供可审计 Wheel、SBOM、hash 和许可证清单。
- 输出契约频繁变化，导致 `CandidateBatch`、reason code、score 或 source metadata 不能稳定版本化。
- 维护停滞导致关键 Provider、LLM 或安全问题无法在 P3/P6 时间窗内修复。
- 依赖引入高风险许可证、不可接受服务条款或未能豁免的高危漏洞。

## 9. Stop-use conditions

满足任一条件时，停止使用 AlphaSift 并关闭相关 feature flag：

- 锁定 commit 或内部 Wheel hash 与审查记录不一致。
- Apache-2.0 attribution、LICENSE 或未来 NOTICE 不能随制品完整保留。
- AlphaSift 运行路径绕过 Provider Policy/fallback trace、Dataset Version、Runtime Profile guard 或真实调用限制。
- AlphaSift 将 T+N evaluation、快照评分或 LLM ranking 冒充正式组合回测、Factor Evaluation 或 Evidence-backed investment claim。
- 新增 SCA/license/ToS 风险在 Gate G3/G6 前无法修复或正式豁免。

## 10. 下一步

`SAL-P3-002` 可开始构建离线 AlphaSift Wheel。该任务必须：

- 使用 `locked_source_commit: 9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`。
- 绑定 `source_archive_sha256: 4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a`。
- 生成 wheel hash、SBOM、license inventory 和 dependency lock evidence。
- 保持生产/桌面 requirements 不使用动态 `git+https`。
- 不启动 `SAL-P3-003` ScreeningProvider adapter，直到 Wheel intake 通过并记录证据。

## 11. 本地验证

| 验证 | 结果 |
|---|---|
| `uv run --extra core --extra dev python -m pytest tests/architecture/test_alphasift_source_review.py -q` | Red：`2 failed`，缺少本文件；Green：`2 passed` |
| `uv run --extra core --extra dev python -m pytest tests/architecture/test_alphasift_source_review.py tests/architecture/test_dependency_locking.py -q` | PASS：`6 passed` |
| `uv run --extra core --extra dev python -m pytest -q` | PASS：`238 passed, 3 skipped` |
| `uv run --extra core --extra dev python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `uvx --python 3.11 --from pip-audit pip-audit --requirement <alphasift-runtime-requirements> --progress-spinner off --format json` | PASS：`0 known vulnerabilities`，`86` dependencies |
| `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
