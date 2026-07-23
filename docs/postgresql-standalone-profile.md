# PostgreSQL Standalone Profile 记录

> 任务：`SAL-P2-017` 建立 PostgreSQL standalone Profile<br>
> 日期：2026-07-23<br>
> 代码：`src/serenity_alpha_lab/repositories/database.py`<br>
> 测试：`tests/repositories/test_database_profile.py`、`tests/repositories/test_repository_contract.py`

## 范围

`SAL-P2-017` 新增数据库 Profile 与 Repository Contract 基础设施，让 `desktop/ci` SQLite 和 `standalone` PostgreSQL 使用同一套 SQLAlchemy 配置、健康检查和 repository 语义约束。

本任务只建立数据库配置、连接池、readiness 与 repository contract probe，不启动 Worker lease、PersistentTaskBackend、Celery/Redis、Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用或 DSA runtime source 迁移。

## 实现

| 能力 | 结果 |
|---|---|
| Profile 解析 | `resolve_database_profile()` 复用 `RuntimeSettings` / `RuntimeProfile`，支持 `sqlite` 与 `postgresql/postgresql+psycopg` URL；`standalone` profile 要求显式 `SERENITY_DATABASE_URL`。 |
| PostgreSQL 连接池 | `create_database_engine()` 为 PostgreSQL 配置 `pool_pre_ping=True`、`pool_size=5`、`max_overflow=10`、`pool_timeout=30s`、`statement_timeout=30000ms` 和 `application_name=serenity-alpha-lab`。 |
| SQLite 安全默认值 | SQLite 连接开启 `foreign_keys=ON`、`busy_timeout=5000ms`，文件库启用 WAL；`:memory:` 使用 `StaticPool` 保持测试语义稳定。 |
| Readiness | `check_database_ready()` 执行 `SELECT 1`，可选择 Alembic head preflight；未迁移数据库返回 `ready=False` 和稳定 failure reason，不静默 `create_all`。 |
| Repository Contract | `RepositoryContractProbeRepository` 约束 UTC datetime、`Decimal`、date、JSON、duplicate key 和 rollback 语义，SQLite 与可选 live PostgreSQL 使用同一测试套件。 |
| PostgreSQL driver | `core` extra 增加 `psycopg[binary]>=3.2.0`，`uv.lock` 与导出 `requirements.txt` 已刷新。 |

## Repository Contract 语义

- 时间统一归一到 UTC aware `datetime`，落库为 ISO 字符串，避免 SQLite 丢失时区。
- 金额/价格类 `Decimal` 以规范十进制字符串保存，避免 SQLite float coercion 和 PostgreSQL numeric 差异影响 contract。
- JSON 递归规范化 `Decimal`、`datetime` 和 `date`，避免 dialect-specific encoder 行为。
- `RepositoryConflict` 把唯一键冲突包装成稳定 repository 错误，不向上泄露 DBAPI 细节。
- `transaction()` context 在异常时回滚；测试覆盖失败事务不留下记录。

## 验证

| 验证 | 结果 |
|---|---|
| Red | `uv run --extra core --extra dev python -m pytest tests/repositories/test_database_profile.py tests/repositories/test_repository_contract.py -q` 先因缺少 `serenity_alpha_lab.repositories.database` 失败：`3 failed, 3 skipped, 3 errors`。 |
| Target | `uv run --extra core --extra dev python -m pytest tests/repositories/test_database_profile.py tests/repositories/test_repository_contract.py tests/repositories/test_storage_migrations.py -q`：`10 passed, 3 skipped`。 |
| Related | `uv run --extra core --extra dev python -m pytest tests/repositories tests/application/test_config_profiles.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q`：`50 passed, 3 skipped`。 |
| Full pytest | `uv run --extra core --extra dev python -m pytest -q`：`220 passed, 3 skipped`。 |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests`：PASS。 |
| Lock / diff / tag | `scripts/verify-python-dependency-lock.sh`、`git diff --check`、`git rev-parse upstream/dsa-v3.26.1`：PASS；tag 仍为 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。 |
| Driver | `uv run --extra core --extra dev python -c "import psycopg"` 成功，版本 `3.3.4`。 |

`SERENITY_TEST_POSTGRES_URL` 未配置时，live PostgreSQL contract cases 标记为 skip；同一 contract suite 已保留，一旦 CI/standalone 环境提供该 URL，会对 PostgreSQL 执行同一组时间、Decimal、JSON、duplicate key 和 rollback 断言。

## 后续

`SAL-P2-018` 可以基于本任务提供的 database profile、readiness 与 contract probe 接入 `PersistentTaskBackend`、Worker lease/heartbeat 和 Run/Event 权威状态表。该后续任务仍需独立 migration、Repository Contract 和 Worker 恢复测试。
