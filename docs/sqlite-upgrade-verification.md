# SQLite 历史库升级验证记录

> 任务：`SAL-P1-013` 验证历史 SQLite 升级<br>
> 日期：2026-07-20<br>
> Phase：P1 工程加固<br>
> Gate：G1 未通过<br>
> 范围：使用 P0 脱敏 `fixture.sql` 演练 legacy DSA SQLite 数据库到 Alembic baseline head 的 backup、stamp、verify 和 failure recovery；不新增业务 Schema，不迁移 DSA runtime `storage.py`，不切换 Repository 读写路径，不启动 Provider/LLM、PIT Dataset、Quant Core 或正式回测。

## 目标

`SAL-P1-012` 已让空库可通过 Alembic 创建 DSA baseline schema。`SAL-P1-013` 验证已有 DSA 历史库的升级路径：在保留业务数据的前提下创建备份、将数据库 stamp 到 Alembic head、校验业务表行数和内容哈希不变，并在失败时恢复原库。

## 实现

`src/serenity_alpha_lab/repositories/sqlite_upgrade.py` 提供：

| API | 作用 |
|---|---|
| `restore_sqlite_fixture()` | 从 P0 `fixture.sql` 重建脱敏历史 SQLite 数据库，用于测试和演练。 |
| `inspect_sqlite_database()` | 统计业务表行数并计算稳定内容哈希，排除 `alembic_version`。 |
| `upgrade_legacy_sqlite_to_alembic_head()` | 备份 SQLite 文件，执行 Alembic `stamp`，验证业务内容不变；异常时恢复备份。 |
| `SQLiteUpgradeReport` | 记录 source、backup、target revision、升级前后 inspection 和 validation 结果。 |

升级演练使用 Alembic `stamp` 而不是重新执行 baseline DDL，因为 P0 fixture 已经具备 DSA `v3.26.1` 的 28 张业务表和 177 个索引。Alembic 只新增/更新 `alembic_version`，业务表行数和内容哈希必须保持一致。

## 验证口径

| 检查 | 结果 |
|---|---|
| fixture restore | P0 `docs/baselines/dsa-v3.26.1/database/fixture.sql` 可恢复为 SQLite 文件。 |
| Alembic stamp | `alembic_version.version_num` 等于 `20260720_dsa_v3261_baseline`。 |
| 行数 | `analysis_history=2`、`schema_migrations=1`，所有业务表升级前后 row_counts 完全一致。 |
| 内容哈希 | 所有业务表升级前后 content_hashes 完全一致。 |
| 幂等 | 成功升级后重复运行仍保持 validation passed，业务内容不变。 |
| 失败恢复 | 注入 backup 后失败时恢复原 SQLite 文件，且不残留 `alembic_version`。 |
| 边界 | 升级代码不导入 `src.storage` / `DatabaseManager`，不调用 `metadata.create_all` 或 `.create_all()`。 |

## 范围限制

- 不执行新业务 schema expand/backfill；当前 Alembic head 与 P0 DSA schema 对齐。
- 不验证大规模生产库性能、锁等待、磁盘空间或真实用户数据；这些属于后续 RC/发布迁移 runbook。
- 不改变 DSA runtime 启动路径；Repository 和 API 迁移仍需后续任务接入。
- 不提交运行时 SQLite、备份文件、`.cache` 或 fixture restore 产物。

## 验证

| 验证 | 结果 |
|---|---|
| Red 测试 | `tests/repositories/test_sqlite_upgrade.py` 初始因缺少 `serenity_alpha_lab.repositories.sqlite_upgrade` 失败：`4 failed` |
| 目标测试 | `.cache/dsa-p0/venv/bin/python -m pytest tests/repositories/test_sqlite_upgrade.py -q`：`4 passed` |
| 相关套件 | `.cache/dsa-p0/venv/bin/python -m pytest tests/repositories tests/architecture -q`：`26 passed` |
| 全量 pytest | `.cache/dsa-p0/venv/bin/python -m pytest -q`：`103 passed` |
| 语法检查 | `py_compile` 覆盖新增 sqlite upgrade、storage migrations、repository exports 和 tests，通过 |
| 依赖与状态保护 | 本任务未新增依赖；`scripts/verify-python-dependency-lock.sh`、`git diff --check`、`git rev-parse upstream/dsa-v3.26.1` 通过，tag 仍为 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

## 后续衔接

- `SAL-P1-015` 可在该升级路径基础上重跑 DSA Desktop/API 主路径和性能基线。
- `SAL-P1-016` Gate G1 需要把 Alembic baseline、SQLite upgrade rehearsal 和 Desktop 兼容基线共同作为进入 P2 的工程地基证据。
