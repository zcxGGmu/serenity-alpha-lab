# Dataset Catalog 与 Manifest 记录

> 任务：`SAL-P2-011` 实现 Dataset Catalog 与 Manifest<br>
> 日期：2026-07-22<br>
> Gate：G2 未通过，本任务仅完成离线 Dataset Catalog、不可变版本 Manifest 和 latest alias<br>
> 代码：`src/serenity_alpha_lab/datasets/catalog.py`<br>
> 测试：`tests/datasets/test_dataset_catalog.py`

## 1. 范围

本任务新增 Dataset Catalog 与 Manifest 层，覆盖：

- 不可变版本：`DatasetVersionManifest` 以 `version_id` 记录一个已发布 Dataset 版本；同一 `version_id` 只能幂等复读完全相同的 manifest，不能覆盖为不同内容。
- 文件清单：`DatasetFileManifest` 从 P1 `ArtifactManifest` 提取 `artifact_id`、内容寻址 URI、SHA-256、size、schema、content type、row count 和分区值。
- Schema 绑定：发布时从 `ArrowSchemaRegistry` 读取 `DatasetSchemaDeclaration`，把 canonical `schema_hash` 写入 Manifest，防止同名同版本 Schema 漂移。
- 血缘：Manifest 记录 `previous_version_id` 与 `input_version_ids`；这些 ID 必须能在本地 Catalog 中解析，避免写入无法追踪的血缘边。
- latest alias：`LocalDatasetCatalog` 将版本 Manifest 持久化后，再单独写入 `aliases/<dataset>/<scope>/latest.json`；alias 是可变指针，版本 Manifest 本身不可变。
- Run 引用规则：`DatasetVersionRef.latest()` 只允许 discovery / research display；`FORMAL_EXPERIMENT` 必须使用具体 `dataset_version` ID。
- 本地持久化：Catalog 使用 deterministic JSON 和临时文件 + `os.replace` 原子替换，版本记录和 alias 记录分离。

本任务不实现数据质量规则、warning/quarantine/blocking、失败 Dataset 阻断 latest、fallback policy、真实 Provider 调用、PersistentTaskBackend、Worker runtime、Quant Core、正式回测或 Evidence Agent。

## 2. 主要类型

| 类型 | 作用 |
|---|---|
| `DatasetFileManifest` | 单个 Dataset 文件或 Artifact 的哈希、大小、row count、Schema 和分区值 |
| `DatasetVersionManifest` | 不可变 Dataset 版本 Manifest，包含 schema hash、文件列表、run/stage、血缘和 metadata |
| `DatasetVersionRef` | 运行输入引用，可表达具体 `version_id` 或 research-only `latest` alias |
| `DatasetReferencePurpose` | 区分 `discovery`、`research_display` 和 `formal_experiment` 引用语义 |
| `LocalDatasetCatalog` | 本地文件系统 Catalog Repository，管理版本 Manifest、查询和 latest alias |

## 3. 持久化布局

```text
<catalog-root>/
  versions/
    dsv_<hash>.json
  aliases/
    dataset.bars_1d_raw/
      cn/
        latest.json
  tmp/
    *.tmp
```

写入顺序：

1. 校验 `dataset_name`、Schema 声明、文件 Artifact hash、row count、run/stage 和 lineage。
2. 生成或校验 `version_id`。
3. 写入 `versions/<version_id>.json`。
4. 若 `update_latest=True`，再写入 `aliases/<dataset>/<scope>/latest.json`。

如果 alias 写入失败，已发布的具体版本仍可通过 `version_id` 查询，旧 latest 指针保持不变；后续 `SAL-P2-013` 再实现质量失败阻断 latest、隔离区和临时 Artifact 清理。

## 4. Manifest 字段

版本 Manifest 包含：

- `dataset_name`
- `version_id`
- `schema_name`
- `schema_version`
- `schema_hash`
- `content_type`
- `created_at`
- `created_by_run_id`
- `created_by_stage_id`
- `trace_id`
- `previous_version_id`
- `input_version_ids`
- `row_count`
- `file_hashes`
- `files[]`
- `metadata`

文件 Manifest 包含：

- `artifact_id`
- `uri`
- `sha256`
- `size_bytes`
- `schema_name`
- `schema_version`
- `content_type`
- `row_count`
- `partition_values`

## 5. 验证

本任务使用 TDD：

- Red：`uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_catalog.py -q` 先以无法从 `serenity_alpha_lab.datasets` 导入 `catalog` 失败。
- Green target：`uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_catalog.py -q`，`5 passed`。
- Related suite：`uv run --extra core --extra quant --extra dev python -m pytest tests/datasets tests/domain/test_artifacts.py tests/repositories/test_local_artifact_store.py tests/architecture/test_architecture_boundaries.py -q`，`45 passed`。
- Full suite：`uv run --extra core --extra dev python -m pytest -q`，`190 passed`。
- Compile：`uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` 通过。
- Dependency lock：`scripts/verify-python-dependency-lock.sh` 通过。
- Whitespace：`git diff --check` 通过。
- Immutable tag：`git rev-parse upstream/dsa-v3.26.1` 仍为 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。

## 6. 范围限制

本任务明确未实现：

- 数据质量规则、warning/quarantine/blocking 报告、异常 fixture 或规则版本引擎。
- 阻止失败 Dataset 更新 latest、隔离区、发布事务回滚或垃圾回收。
- Provider fallback policy、契约探针、真实 Provider/LLM 调用或联网探针。
- PersistentTaskBackend、Worker runtime、Quant Core、正式回测、Evidence Agent 或 DSA runtime source 迁移。

Gate G2 仍未通过。
