# Bronze 原始数据层记录

> 任务：`SAL-P2-004` 建立 Bronze 原始数据层<br>
> 日期：2026-07-21<br>
> Gate：G2 数据与任务评审<br>
> 结论：`DONE`，仅完成原始响应审计落盘能力；Gate G2 仍未通过

## 1. 交付范围

`SAL-P2-004` 新增 repository 层 `BronzeRawStore`，用于把 Provider 原始响应和请求元数据写入既有 `ArtifactStore`，形成可审计、压缩、内容寻址的 Bronze artifact。

本任务交付：

- `src/serenity_alpha_lab/repositories/bronze_raw_store.py`
  - `BRONZE_RAW_SCHEMA_NAME = "bronze.raw_response"`
  - `BRONZE_RAW_SCHEMA_VERSION = "1.0.0"`
  - `BRONZE_RAW_CONTENT_TYPE = "application/vnd.serenity.bronze.raw-response+json+gzip"`
  - `BronzeRawArtifact`
  - `BronzeRawStore.put_raw_response()`
  - `BronzeRawStore.get_envelope()`
  - `BronzeRawStore.find_raw_artifacts()`
- `src/serenity_alpha_lab/repositories/__init__.py` 导出 Bronze public symbols。
- `tests/repositories/test_bronze_raw_store.py` 覆盖 schema、gzip、hash、traceability、Run/Stage 归因和落盘前脱敏。
- `tests/architecture/test_architecture_boundaries.py` 增加 repository 不直接导入 DSA provider runtime 的边界测试。

## 2. 数据格式

Bronze payload 是 deterministic JSON envelope，经 `gzip.compress(..., mtime=0)` 压缩后通过 `ArtifactStore.put_bytes()` 发布。

Envelope 关键字段：

- `schema_name` / `schema_version`
- `provider_id` / `provider_version`
- `operation`
- `request_parameters`
- `requested_at` / `fetched_at` / `source_timestamp`
- `source_raw_response_sha256`
- `sanitized_raw_response_sha256`
- `field_lineage`
- `trace_id` / `run_id` / `stage_id`
- `raw_response`

Artifact manifest 继续由 P1 `ArtifactStore` 管理，保留 SHA-256 内容地址、压缩后内容 hash、schema、content type、Run/Stage 归因、retention tier 和 manifest-last 原子发布语义。

## 3. 安全与脱敏

Bronze 层在任何 bytes 交给 `ArtifactStore` 前递归清洗请求参数和原始响应：

- 密钥字段：`api_key`、`token`、`secret`、`password`、`authorization`、`x-api-key`。
- Cookie 字段：`Cookie`、`Set-Cookie`、`session`。
- 私有正文：`body`、`content`、`messages`、`private_body`。
- 常见个人信息：`email`、`phone`、`mobile`、`telephone`、`id_card`、`identity_card`、`personal_id`、`ssn`。
- 字符串内的 token/API key、邮箱、手机号和身份证样式值会被替换为 redacted marker。

当前实现不会保存未脱敏原文；审计用 `source_raw_response_sha256` 记录 Provider Provenance 已给出的原始响应 hash，并额外记录 `sanitized_raw_response_sha256` 代表实际落盘前的脱敏 payload hash。

## 4. 范围限制

本任务未实现：

- Dataset Catalog、Silver/PIT 数据集、质量门禁或 `latest` 发布。
- Provider fallback policy、真实 Provider 探针、真实网络请求或 LLM 调用。
- PersistentTaskBackend、Worker runtime、Quant Core、正式回测或 Evidence Agent。
- DSA runtime source 迁移或 `upstream/dsa-v3.26.1` tag 变更。

`BronzeRawStore` 是后续 Dataset/Provider 工作的底层审计能力，不改变现有 DSA Provider Adapter 行为。

## 5. TDD 与验证

Red：

- `uv run --extra core --extra dev python -m pytest tests/repositories/test_bronze_raw_store.py -q`
- 预期失败：`ModuleNotFoundError: No module named 'serenity_alpha_lab.repositories.bronze_raw_store'`

Green / 验证：

- `uv run --extra core --extra dev python -m pytest tests/repositories/test_bronze_raw_store.py -q` → `6 passed`
- `uv run --extra core --extra dev python -m pytest tests/repositories tests/domain/test_provider_contract.py tests/application/test_trace_context.py tests/architecture/test_architecture_boundaries.py -q` → `56 passed`
- `uv run --extra core --extra dev python -m pytest -q` → `162 passed`
- `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` → PASS
- `scripts/verify-python-dependency-lock.sh` → PASS, `Resolved 296 packages`
- `git rev-parse upstream/dsa-v3.26.1` → `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`

`git diff --check` → PASS。
