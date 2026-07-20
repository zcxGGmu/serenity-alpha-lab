# Alembic 存储迁移接入记录

> 任务：`SAL-P1-012` 接入 Alembic<br>
> 日期：2026-07-20<br>
> Phase：P1 工程加固<br>
> Gate：G1 未通过<br>
> 范围：Alembic 配置、DSA `v3.26.1` SQLite baseline revision、空库升级命令和启动前 revision preflight；不迁移 DSA runtime `storage.py`，不执行历史 SQLite 升级演练，不启动 Provider/LLM、PIT Dataset、Quant Core 或正式回测。

## 目标

`SAL-P1-012` 将 Serenity root 的 Schema 创建入口收口到 Alembic。P1 先把 P0 冻结的 DSA SQLite Schema 固化为 baseline revision，并提供应用启动前可调用的只读检查，避免新路径继续散落 `Base.metadata.create_all()` 或 DSA `DatabaseManager` 手工迁移。

## 产物

| 文件 | 作用 |
|---|---|
| `alembic.ini` | 根 Alembic 配置，指向 `migrations/`。 |
| `migrations/env.py` | Alembic online/offline 环境入口，不绑定 ORM metadata。 |
| `migrations/script.py.mako` | 后续 revision 生成模板。 |
| `migrations/baselines/dsa_v3_26_1_schema.sql` | 从 P0 `schema.sql` 复制的 DSA baseline DDL，SHA-256 与 P0 快照一致。 |
| `migrations/versions/20260720_dsa_v3261_baseline.py` | DSA `v3.26.1` SQLite baseline revision。 |
| `src/serenity_alpha_lab/repositories/storage_migrations.py` | `StorageMigrationFacade` helper：配置、升级、当前 revision 查询和启动前 head assertion。 |

## Baseline Revision

| 字段 | 值 |
|---|---|
| Alembic revision | `20260720_dsa_v3261_baseline` |
| DSA upstream tag | `v3.26.1` |
| DSA upstream commit | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| DSA schema version | `2026-06-05-create-all-baseline` |
| Baseline SQL SHA-256 | `8d39743b05e5f6b6b7417805ced0fc27d5e5323d2ac04f791ac22c50038a5a51` |
| P0 source | [database schema baseline](./database-schema-baseline.md) |

The baseline migration creates the 28 DSA business tables and 177 indexes from the P0 snapshot, then inserts one `schema_migrations` row with the P0 DSA schema version. Alembic records its own head in `alembic_version`.

## Startup Contract

`src/serenity_alpha_lab/repositories/storage_migrations.py` exposes:

| API | Behavior |
|---|---|
| `upgrade_database(database_url, revision="head")` | Runs Alembic upgrade and returns `MigrationStatus`. |
| `current_migration_status(database_url)` | Reads current database revision without creating business tables. |
| `assert_database_at_head(database_url)` | Raises `StorageMigrationRequired` if the DB is missing or behind head. |
| `baseline_schema_sql_path()` / `baseline_schema_sql_sha256()` | Verifies the committed baseline SQL artifact. |

Application startup should call `assert_database_at_head()` and fail fast with a user-visible migration error instead of silently creating or altering tables. Historical SQLite upgrade rehearsal remains `SAL-P1-013`.

## 范围限制

- 不导入 DSA `src.storage`、`DatabaseManager`，不调用 `metadata.create_all()` 或 `.create_all()`。
- 不改写现有 DSA runtime startup behavior；P1 先建立 Serenity migration facade。
- Baseline revision 当前只支持 SQLite，因为 P0 frozen schema 来自 DSA SQLite；PostgreSQL profile 的正式迁移口径留给后续 Repository/Service 任务。
- 不执行从历史 fixture 的 expand/backfill/verify；该工作属于 `SAL-P1-013`。

## 验证

| 验证 | 结果 |
|---|---|
| Red 测试 | `tests/repositories/test_storage_migrations.py` 初始因缺少 `serenity_alpha_lab.repositories.storage_migrations`、`migrations/env.py` 和 baseline revision 失败：`4 failed` |
| 目标测试 | `.cache/dsa-p0/venv/bin/python -m pytest tests/repositories/test_storage_migrations.py -q`：`4 passed` |
| 相关套件 | `.cache/dsa-p0/venv/bin/python -m pytest tests/repositories tests/architecture -q`：`22 passed` |
| 全量 pytest | `.cache/dsa-p0/venv/bin/python -m pytest -q`：`99 passed` |
| 语法检查 | `py_compile` 覆盖新增 repository、migration env/revision 和 tests，通过 |
| 依赖与状态保护 | `alembic>=1.13.0` 已加入 root `core` extra；`scripts/verify-python-dependency-lock.sh`、`git diff --check`、`git rev-parse upstream/dsa-v3.26.1` 通过，tag 仍为 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

## 后续衔接

- `SAL-P1-013` 使用 P0 `fixture.sql` 演练历史 SQLite upgrade、备份、校验和失败恢复。
- `SAL-P1-015` 在新 lock、协议和迁移基础上重跑 Desktop/DSA 主路径。
- `SAL-P1-016` Gate G1 需要把 Alembic baseline、SQLite upgrade rehearsal 和兼容回归一起纳入工程地基评审。
