# Artifact 模型与本地存储记录

> 任务：`SAL-P1-007` 实现 Artifact 模型与本地存储<br>
> 日期：2026-07-20<br>
> Phase：P1 工程加固<br>
> Gate：G1 未通过<br>
> 范围：纯领域 Artifact 契约、本地内容寻址存储、manifest-last 原子发布；不实现 Evidence Agent、Dataset Catalog、PIT Dataset、Quant Core、正式回测或数据库迁移。

## 目标

`Artifact` 是后续 Evidence、Dataset Version、任务输出、报告包和回测证据的持久输出单元。本任务先建立最小可验证契约：内容以 SHA-256 寻址，Manifest 记录可查询元数据，本地存储通过临时文件和最后发布 manifest 避免失败写入变成已发布记录。

## 领域契约

| 类型 | 作用 |
|---|---|
| `ArtifactUri` | 内容寻址 URI，格式为 `artifact://sha256/<64 hex digest>`。 |
| `ArtifactManifest` | 查询元数据，包含 `artifact_id`、URI、SHA-256、大小、schema、content type、生产 run/stage、保留等级和创建时间。 |
| `ArtifactRetentionTier` | 保留等级：`temporary`、`standard`、`archive`、`legal_hold`。 |
| `ArtifactStore` | 领域端口 Protocol，定义 `put_bytes()`、`get_bytes()`、`get_manifest()`。 |
| `ArtifactNotFound` / `ArtifactIntegrityError` | 缺失记录和内容完整性错误。 |

`ArtifactManifest.create()` 根据内容哈希、schema、content type、生产 run/stage 和保留等级派生稳定 `artifact_id`，同一 payload 与元数据重复写入会返回同一记录；不同 run/stage 的同内容 artifact 可以形成独立 manifest。

## 本地存储

`src/serenity_alpha_lab/repositories/local_artifact_store.py` 提供 `LocalArtifactStore`：

- Blob 路径：`blobs/sha256/<digest-prefix>/<digest>.blob`。
- Manifest 路径：`manifests/<artifact_id>.json`。
- 临时文件路径：`tmp/<artifact_id>.<token>.*.tmp`。
- 写入顺序：先写临时 blob 和临时 manifest，再发布 blob，最后发布 manifest。
- 如果 manifest 发布失败，store 会清理临时文件；若本次新发布了 blob，也会删除该 blob，避免产生可查询记录或遗留内容文件。
- `get_bytes()` 会根据 manifest 校验 size 和 SHA-256，不一致时抛出 `ArtifactIntegrityError`。

## 范围限制

- 不接入数据库、对象存储、Evidence Agent、Dataset Catalog、Provider、Quant Core、PIT Dataset 或正式回测。
- 不迁移 DSA 运行时代码，不创建 API endpoint，不改变 upstream tag。
- 本地实现仅作为后续持久化/对象存储 adapter 的可测试基准。

## 验证

- Red：新增 `tests/domain/test_artifacts.py` 和 `tests/repositories/test_local_artifact_store.py` 后，目标测试因缺少 `serenity_alpha_lab.domain.artifacts` 失败。
- Green：实现 `src/serenity_alpha_lab/domain/artifacts.py` 和 `src/serenity_alpha_lab/repositories/local_artifact_store.py` 后，目标测试通过 `6 passed`。
- 相关套件：`tests/architecture tests/domain tests/repositories` 通过 `58 passed`，确认 domain 仍不导入框架、供应商、repositories、services 或 integrations。
- 语法：`py_compile` 覆盖 `src/serenity_alpha_lab/domain`、`src/serenity_alpha_lab/repositories`、`tests/domain` 和 `tests/repositories`。
