# Arrow Schema Registry 记录

> 任务：`SAL-P2-010` 建立 Arrow Schema Registry<br>
> 日期：2026-07-22<br>
> Gate：G2 未通过，本任务仅完成离线版本化 Arrow Schema Registry<br>
> 代码：`src/serenity_alpha_lab/datasets/schema_registry.py`<br>
> 测试：`tests/datasets/test_arrow_schema_registry.py`

## 1. 范围

本任务新增 Dataset 层 Arrow Schema Registry，覆盖：

- Registry：`ArrowSchemaRegistry` 管理不可变 `DatasetSchemaDeclaration`，按 `schema_name + schema_version` 查询，支持 `latest()` 和稳定注册顺序。
- Schema 声明：`DatasetSchemaField` 记录字段名、Arrow logical type、nullable 与字段含义；`DatasetSchemaDeclaration` 记录主键、分区键、content type 和 canonical schema hash。
- Arrow 转换：`to_pyarrow_schema()` 懒加载 `pyarrow`，生成带 `serenity:schema_name`、`serenity:schema_version`、`serenity:schema_hash`、主键和分区键 metadata 的 `pyarrow.Schema`。
- 类型校验：`validate_pyarrow_schema()` 校验字段顺序、Arrow 类型和默认严格 nullability；Polars 往返会丢失非空约束时可显式关闭 nullability 严格检查。
- 兼容规则：minor/patch 版本只允许新增 nullable 字段；删除字段、改变类型、改变已有字段含义、改变主键/分区/content type 或新增 required 字段均为 breaking change，必须使用新 major。
- 默认注册：默认 Registry 注册主数据、原始日线、公司行动、复权日线和 PIT 基本面五类 P2 Dataset Schema。
- Optional dependency：`serenity_alpha_lab.datasets` 和 Registry 本身在 `core+dev` 下可导入；只有执行 Arrow schema conversion / validation 时才需要 `pyarrow`，该依赖仍位于 `quant` extra。

本任务不建立 Dataset Catalog、不发布 latest alias、不实现质量门禁、不实现 fallback policy、不调用真实 Provider、不启动 Quant Core、正式回测或 Evidence Agent。

## 2. 注册 Schema

| Dataset | Schema name | Version | Primary key | Partition keys |
|---|---|---:|---|---|
| 证券主数据 | `dataset.instrument_master` | `1.0.0` | `instrument_id, valid_from` | `market` |
| 原始日线 | `dataset.bars_1d_raw` | `1.0.0` | `instrument_id, trade_date, provider_id` | `market, year, month` |
| 公司行动 | `dataset.corporate_actions` | `1.0.0` | `instrument_id, ex_date, action_type, provider_id` | `market, year` |
| 复权日线 | `dataset.bars_1d_adjusted` | `1.0.0` | `instrument_id, trade_date, provider_id, adjustment` | `market, year, month` |
| PIT 基本面 | `dataset.fundamentals` | `1.0.0` | `instrument_id, period_end, item, revision, provider_id` | `market, period_year` |

说明：

- `year`、`month` 和 `period_year` 是派生分区键，不要求出现在行级 Arrow field list 中。
- `InstrumentMasterDataset` 现在也输出 `partition_keys` 与 `field_schema`，与后续 P2 Dataset artifact payload 保持一致。
- nested `industries` 与 `provider_mappings` 在 Registry 中使用 explicit `list<struct<...>>` logical type，避免把主数据复杂字段降级为无约束 JSON 字符串。

## 3. 兼容规则

Registry 对同一 `schema_name` 的新增版本执行以下规则：

| 变更 | minor/patch 是否允许 | 处理 |
|---|---:|---|
| 新增 nullable 字段 | 允许 | `BACKWARD_COMPATIBLE` |
| 新增 required 字段 | 不允许 | breaking，必须新 major |
| 删除字段 | 不允许 | breaking，必须新 major |
| 修改字段 Arrow logical type | 不允许 | breaking，必须新 major |
| 把 nullable 字段改为 required | 不允许 | breaking，必须新 major |
| 修改已有字段 meaning | 不允许 | breaking，必须新 major |
| 修改 primary key / partition keys / content type | 不允许 | breaking，必须新 major |
| 完全相同 schema | 允许比较为 identical，但 Registry 拒绝重复注册同一 version | 防止同版本漂移 |

`SchemaCompatibilityReport` 暴露：

- `status`
- `breaking_changes`
- `compatible_changes`
- `is_backward_compatible`
- `requires_major_version`

## 4. PyArrow 与 Round-trip

`pyarrow` 仍只在 `quant` extra 中声明。Registry 采用懒加载：

```python
registry = default_dataset_schema_registry()
declaration = registry.get("dataset.bars_1d_raw", "1.0.0")
arrow_schema = declaration.to_pyarrow_schema()  # 这里才需要 pyarrow
```

测试覆盖：

- `core+dev` 路径可导入 `serenity_alpha_lab.datasets` 和创建默认 Registry。
- `core+quant+dev` 路径可把 Dataset schema 转为真实 `pyarrow.Schema`。
- Raw daily bars 固定样本可完成 Arrow -> Pandas -> Arrow 与 Arrow -> Polars -> Arrow 往返，并验证日期、timestamp 和数值类型不漂移。
- Polars 往返保留类型但会把 non-nullable 字段标成 nullable，测试使用 `strict_nullability=False` 显式记录该边界。

## 5. 验证

本任务使用 TDD：

- Red：`uv run --extra core --extra quant --extra dev python -m pytest tests/datasets/test_arrow_schema_registry.py -q` 先以缺少 `serenity_alpha_lab.datasets.schema_registry` 失败。
- Green target：`uv run --extra core --extra quant --extra dev python -m pytest tests/datasets/test_arrow_schema_registry.py -q`，`6 passed`。
- Instrument master related：`uv run --extra core --extra quant --extra dev python -m pytest tests/datasets/test_instrument_master.py tests/datasets/test_arrow_schema_registry.py -q`，`9 passed`。
- P2 related suite：`uv run --extra core --extra quant --extra dev python -m pytest tests/datasets tests/domain/test_provider_contract.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q`，`62 passed`。
- Full suite：`uv run --extra core --extra dev python -m pytest -q`，`185 passed`。
- Compile：`uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` 通过。
- Dependency lock：`scripts/verify-python-dependency-lock.sh` 通过。
- Whitespace：`git diff --check` 通过。
- Immutable tag：`git rev-parse upstream/dsa-v3.26.1` 仍为 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。

## 6. 范围限制

本任务明确未实现：

- Dataset Catalog、latest alias、发布事务、隔离区、质量门禁或 manifest repository。
- Provider fixture、fallback policy、真实 Provider/LLM 调用或联网探针。
- PersistentTaskBackend、Worker runtime、Quant Core、正式回测、Evidence Agent 或 DSA runtime source 迁移。

Gate G2 仍未通过。
