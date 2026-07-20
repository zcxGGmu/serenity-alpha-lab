# InstrumentId 统一证券 ID 领域模型记录

> 任务：`SAL-P1-005` 实现统一 InstrumentId<br>
> 日期：2026-07-20<br>
> Phase：P1 工程加固<br>
> Gate：G1 未通过<br>
> 范围：纯领域值对象、解析/格式化、Provider Symbol Mapping 和 DSA 旧代码兼容格式

## 1. 目标

`InstrumentId` 为后续 Provider 契约、Dataset 主数据、PIT 数据和跨市场持久化主键提供统一证券身份。它替代“裸 symbol 字符串作为跨市场 ID”的隐式做法，但本任务不迁移现有 DSA 运行时代码。

本任务完成：

- `Market`：`cn`、`hk`、`us`、`jp`、`kr`、`tw`。
- `Exchange`：`XSHG`、`XSHE`、`XBSE`、`XHKG`、`XNAS`、`XNYS`、`XTKS`、`XKRX`、`XKOS`、`XTAI`、`ROCO`。
- `AssetType`：`equity`、`etf`、`index`、`unknown`；默认 `equity`。
- `InstrumentId`：不可变值对象，canonical 格式为 `<symbol>.<exchange>`。
- `ProviderSymbolMapping`：把领域 ID 与特定 Provider/旧代码 symbol 绑定。
- 错误类型：`AmbiguousInstrumentSymbol`、`InvalidInstrumentSymbol`、`UnsupportedProvider`。

## 2. Canonical 口径

| 市场 | 典型输入 | Canonical InstrumentId | 说明 |
|---|---|---|---|
| A 股 | `600519.XSHG` | `600519.XSHG` | 上交所 6 位代码，保留前导零规则不适用 |
| A 股 | `000001.XSHE` | `000001.XSHE` | 深交所 6 位代码，保留前导零 |
| 港股 | `00700.XHKG` | `00700.XHKG` | 统一补齐 5 位 |
| 美股 | `AAPL.XNAS` | `AAPL.XNAS` | 默认 NASDAQ；后续可由主数据修正具体上市交易所 |
| 日股 | `7203.XTKS` | `7203.XTKS` | 对应 Yahoo `.T` 后缀 |
| 韩股 | `005930.XKRX` | `005930.XKRX` | KOSPI / KRX，对应 Yahoo `.KS` |
| 韩股 | `035720.XKOS` | `035720.XKOS` | KOSDAQ，对应 Yahoo `.KQ` |
| 台股 | `2330.XTAI` | `2330.XTAI` | TWSE，对应 Yahoo `.TW` |
| 台股 | `6505.ROCO` | `6505.ROCO` | TPEx/OTC，对应 Yahoo `.TWO` |

`str(InstrumentId)` 与 `.canonical` 均返回 canonical 字符串。`InstrumentId.parse()` 只接受 canonical 形态；旧格式通过 `InstrumentId.from_legacy()` 进入。

## 3. 旧格式兼容

| 旧/Provider symbol | Canonical | 兼容目的 |
|---|---|---|
| `SH600519`、`600519.SH`、`600519.SS` | `600519.XSHG` | DSA / Yahoo 上海格式 |
| `SZ000001`、`000001.SZ` | `000001.XSHE` | DSA / Yahoo 深圳格式 |
| `HK00700`、`0700.HK`、`00700.HK` | `00700.XHKG` | DSA 港股前缀与 Yahoo 港股后缀 |
| `AAPL` with `market=us` | `AAPL.XNAS` | DSA 美股裸 ticker |
| `7203.T` | `7203.XTKS` | DSA/Yahoo 日股 |
| `005930.KS`、`035720.KQ` | `005930.XKRX`、`035720.XKOS` | DSA/Yahoo 韩股 |
| `2330.TW`、`6505.TWO` | `2330.XTAI`、`6505.ROCO` | DSA/Yahoo 台股 |

裸 6 位代码必须提供明确市场上下文；当前只对 `market=cn` 做确定性交易所推断。韩股、台股等后缀市场即使给出市场上下文，也仍要求 `.KS/.KQ/.TW/.TWO` 等可确定交易所的格式，避免跨市场或跨交易所碰撞。

## 4. Provider Symbol Mapping

`InstrumentId.to_provider_symbol("yahoo")` 提供 Yahoo/DSA 已使用的 suffix 形态：

- `600519.XSHG` -> `600519.SS`
- `000001.XSHE` -> `000001.SZ`
- `00700.XHKG` -> `00700.HK`
- `AAPL.XNAS` -> `AAPL`
- `7203.XTKS` -> `7203.T`
- `005930.XKRX` -> `005930.KS`
- `035720.XKOS` -> `035720.KQ`
- `2330.XTAI` -> `2330.TW`
- `6505.ROCO` -> `6505.TWO`

`InstrumentId.to_dsa_symbol()` 保留旧代码兼容写法：A 股使用 `SH/SZ/BJ` 前缀，港股使用 `HK` 前缀，美/日/韩/台沿用当前 DSA/Yahoo 形态。

## 5. 范围限制

- 不接入真实 Provider。
- 不迁移 DSA `normalize_stock_code` 调用点。
- 不实现证券主数据、上市/退市有效期、PIT Dataset 或 Provider Contract Test。
- 不启动 Quant Core、Qlib、正式回测或大规模 DSA runtime source 迁移。

后续 `SAL-P2-003` 将基于本值对象包裹 `normalize_stock_code`；`SAL-P2-005` 将用证券主数据补充交易所、资产类型和历史有效期口径。

## 6. 验证

- Red：新增 `tests/domain/test_instrument_id.py` 后，目标测试因缺少 `serenity_alpha_lab.domain.instruments` 失败。
- Green：实现 `src/serenity_alpha_lab/domain/instruments.py` 后，`tests/domain/test_instrument_id.py` 通过 `37 passed`。
- 边界：`tests/architecture tests/domain` 通过 `52 passed`，确认 domain 仍不导入 FastAPI、SQLAlchemy、Pandas、Qlib、LiteLLM、AKShare 或 DSA provider。
