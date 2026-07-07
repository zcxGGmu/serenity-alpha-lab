# Serenity Alpha Lab 研究备忘录

**研究问题:** 光模块
**关注标的:** AAOI
**证据数量:** 16
**综合研究评分:** 17/100
**Serenity 评级:** 观察池候选
**研究置信层级:** 低
**关键短板:** 综合评分偏低, 失效条件不够清晰, 拥挤风险偏高

## 评分卡

| 因子 | 原始分 | 加权贡献 | 证据 |
|---|---:|---:|---|
| bottleneck scarcity | 30 | 7.2 | github:fadewalk/serenity-stock-choke:a72c4ffa5a9c, github:yan-labs/serenity-aleabitoreddit:4fd75f23647d, github:yan-labs/serenity-aleabitoreddit:9f509bd6d356, github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, github:fadewalk/serenity-stock-choke:55f1d65d6fc7, github:yijiashu/serenity-skill:08537f7e63aa, github:ZadAnthony/serenity-skill:53011aa02f41, github:fadewalk/serenity-stock-choke:3bdcbf3fe9f7, github:onebluecloud/serenity-playbook:ea8d18d130d5 |
| demand certainty | 33 | 7.3 | github:fadewalk/serenity-stock-choke:a72c4ffa5a9c, github:yan-labs/serenity-aleabitoreddit:4fd75f23647d, github:yan-labs/serenity-aleabitoreddit:9f509bd6d356, github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, sec-companyfacts:AAOI:00c9a17ec040, github:fadewalk/serenity-stock-choke:55f1d65d6fc7, github:yijiashu/serenity-skill:08537f7e63aa, github:ZadAnthony/serenity-skill:53011aa02f41, github:fadewalk/serenity-stock-choke:3bdcbf3fe9f7, github:onebluecloud/serenity-playbook:79cd020126ab, github:onebluecloud/serenity-playbook:c7b869d5c91c, github:onebluecloud/serenity-playbook:ea8d18d130d5 |
| supply elasticity | 16 | 2.6 | github:fadewalk/serenity-stock-choke:a72c4ffa5a9c, github:yan-labs/serenity-aleabitoreddit:4fd75f23647d, github:yan-labs/serenity-aleabitoreddit:9f509bd6d356, github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, github:fadewalk/serenity-stock-choke:55f1d65d6fc7, github:yijiashu/serenity-skill:08537f7e63aa, github:ZadAnthony/serenity-skill:53011aa02f41, github:fadewalk/serenity-stock-choke:3bdcbf3fe9f7, github:onebluecloud/serenity-playbook:ea8d18d130d5 |
| evidence quality | 27 | 4.3 | sec-companyfacts:AAOI:1dde3c8a25f5, github:fadewalk/serenity-stock-choke:a72c4ffa5a9c, github:yan-labs/serenity-aleabitoreddit:4fd75f23647d, github:yan-labs/serenity-aleabitoreddit:9f509bd6d356, github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, sec-companyfacts:AAOI:00c9a17ec040, sec-companyfacts:AAOI:f0bd95191d47, github:fadewalk/serenity-stock-choke:55f1d65d6fc7, github:yijiashu/serenity-skill:08537f7e63aa, github:ZadAnthony/serenity-skill:53011aa02f41, github:fadewalk/serenity-stock-choke:3bdcbf3fe9f7, github:kooui/serenity-framework:92551d1dae6f, github:kooui/serenity-framework:dcbfa90b1fd4, github:onebluecloud/serenity-playbook:79cd020126ab, github:onebluecloud/serenity-playbook:c7b869d5c91c, github:onebluecloud/serenity-playbook:ea8d18d130d5 |
| crowding risk (扣分) | 47 | -5.6 | github:fadewalk/serenity-stock-choke:a72c4ffa5a9c, github:yan-labs/serenity-aleabitoreddit:4fd75f23647d, github:yan-labs/serenity-aleabitoreddit:9f509bd6d356, github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e |
| invalidation clarity | 9 | 0.9 | sec-companyfacts:AAOI:1dde3c8a25f5, github:fadewalk/serenity-stock-choke:a72c4ffa5a9c, github:yan-labs/serenity-aleabitoreddit:4fd75f23647d, github:yan-labs/serenity-aleabitoreddit:9f509bd6d356, github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, sec-companyfacts:AAOI:00c9a17ec040, sec-companyfacts:AAOI:f0bd95191d47, github:fadewalk/serenity-stock-choke:55f1d65d6fc7, github:yijiashu/serenity-skill:08537f7e63aa, github:ZadAnthony/serenity-skill:53011aa02f41, github:fadewalk/serenity-stock-choke:3bdcbf3fe9f7, github:kooui/serenity-framework:92551d1dae6f, github:kooui/serenity-framework:dcbfa90b1fd4, github:onebluecloud/serenity-playbook:79cd020126ab, github:onebluecloud/serenity-playbook:c7b869d5c91c, github:onebluecloud/serenity-playbook:ea8d18d130d5 |

## 投资分析结论

AAOI 当前可进入 Serenity 候选池复核。综合研究评分为 17/100，报告使用 16 条证据，其中 primary/fact 证据 3 条、风险/失效证据 5 条。下一步重点不是给出买卖建议，而是验证景气链条、瓶颈位置和业绩兑现路径。

## Serenity 选股因子

- **景气方向:** 当前证据覆盖 5 条正向线索和 5 条负向线索，需要判断需求是否已经传导到订单或收入。
- **产业链位置:** 已识别环节包括 company financials、component、interconnect、market_structure、memory、methodology，优先寻找供需最紧、替代最难的节点。
- **主题映射:** 主要主题包括 5-layer supply chain、A-share、AI infrastructure、AI supply-chain、CPO、Chinese skill，需要区分行业 beta 与公司 alpha。
- **拥挤与失效:** 如果市场关注先于公司证据大幅升温，应降低结论置信度并强化反证跟踪。

## 关键跟踪指标

- 公司公告、财报、电话会中是否出现客户验证、订单、产能或收入爬坡的直接证据。
- 同行业替代供应商是否加速扩产或拿到关键客户资格。
- 收入、毛利率、订单或 backlog 是否与景气逻辑同步改善。
- 主题热度、成交拥挤度和估值预期是否明显跑在基本面之前。
- 继续补充 primary source 以验证现有判断。

## 行业结构图

| 产业链环节 | 证据数量 | Primary/Fact | 风险 | 代表主题 |
|---|---:|---:|---:|---|
| company financials | 3 | 3 | 1 | SEC companyfacts, primary-source, profitability, revenue, share count |
| component | 8 | 0 | 1 | A-share, AI infrastructure, AI supply-chain, CPO, Chinese skill |
| interconnect | 1 | 0 | 1 | AI infrastructure, CPO, Serenity, risk, supply-chain bottleneck |
| market_structure | 1 | 0 | 1 | AI infrastructure, Serenity, risk, supply-chain bottleneck, ticker-resolution:AAOI |
| memory | 1 | 0 | 1 | AI infrastructure, CPO, Serenity, memory, supply-chain bottleneck |
| methodology | 2 | 0 | 0 | 5-layer supply chain, Serenity, framework, ticker-resolution:AAOI |

## 催化剂时间线

| 日期 | 类型 | 标的 | 证据 |
|---|---|---|---|
| 2026-02-26 | fact | AAOI | Primary SEC companyfacts data shows AAOI FY2025 Revenue from Contract with Customer, Excluding Assessed Tax of $455,715,000 from a filed annual report accession 0001437749-26-005875. |
| 2026-02-26 | fact | AAOI | Primary SEC companyfacts data shows AAOI FY2025 Net Income (Loss) Attributable to Parent of $-38,228,000 from a filed annual report accession 0001437749-26-005875. |
| 2026-02-26 | fact | AAOI | Primary SEC companyfacts data shows AAOI FY2025 Entity Common Stock, Shares Outstanding of 75,198,817 shares from a filed annual report accession 0001437749-26-005875. |

## 证据缺口优先级

| 优先级 | 缺口 | 影响 | 下一步证据 |
|---|---|---|---|
| P1 | invalidation_plan | 缺少反证条件会让报告无法及时降级。 | 明确客户流失、替代供给扩张、毛利恶化或收入延期的触发条件。 |
| P2 | crowding_risk | 拥挤度升高会压缩安全边际并放大回撤。 | 增加估值、成交热度、社媒关注和预期兑现节奏的对照证据。 |

## 论点摘要

AAOI 目前形成的是一个临时性的 Serenity 风格研究案例，覆盖 company financials、component、interconnect、market_structure、memory、methodology。当前最强主题包括 5-layer supply chain、A-share、AI infrastructure、AI supply-chain、CPO。该案例由 5 条正向证据支撑，同时受到 5 条明确风险证据约束。只有当 primary evidence 进一步确认客户验证、收入爬坡节奏和替代供给受限时，研究置信度才应提高。

## 声明类型组合

fact: 3, inference: 9, risk: 4

## 来源覆盖

**Focus ticker:** AAOI

**Coverage counts:** evidence 16, focus ticker 16, primary/fact 3, risk 5, external non-Serenity 3

**Concentration:** methodology 0%, SERENITY placeholder 0%

**Gate result:** No critical coverage flags.

## Primary Source 证据

- **sec-companyfacts:AAOI:1dde3c8a25f5** [SEC companyfacts AAOI Net Income (Loss) Attributable to Parent](https://data.sec.gov/api/xbrl/companyfacts/CIK0001158114.json) (2026-02-26, primary, fact, 置信度 0.88): Primary SEC companyfacts data shows AAOI FY2025 Net Income (Loss) Attributable to Parent of $-38,228,000 from a filed annual report accession 0001437749-26-005875.
- **sec-companyfacts:AAOI:00c9a17ec040** [SEC companyfacts AAOI Revenue from Contract with Customer, Excluding Assessed Tax](https://data.sec.gov/api/xbrl/companyfacts/CIK0001158114.json) (2026-02-26, primary, fact, 置信度 0.88): Primary SEC companyfacts data shows AAOI FY2025 Revenue from Contract with Customer, Excluding Assessed Tax of $455,715,000 from a filed annual report accession 0001437749-26-005875.
- **sec-companyfacts:AAOI:f0bd95191d47** [SEC companyfacts AAOI Entity Common Stock, Shares Outstanding](https://data.sec.gov/api/xbrl/companyfacts/CIK0001158114.json) (2026-02-26, primary, fact, 置信度 0.88): Primary SEC companyfacts data shows AAOI FY2025 Entity Common Stock, Shares Outstanding of 75,198,817 shares from a filed annual report accession 0001437749-26-005875.

## 行业上下文证据

- 没有匹配到跨标的 primary source 上下文。

## 支撑证据

- **github:fadewalk/serenity-stock-choke:55f1d65d6fc7** [fadewalk/serenity-stock-choke README.md](https://github.com/fadewalk/serenity-stock-choke/blob/main/README.md) (2026-07-04, derived, inference, 置信度 0.66): 电力、光模块/CPO、半导体设备、军工、新能源车、医疗器械、创新药、农药、OLED…… 任意 A 股板块均可分析 。
- **github:yijiashu/serenity-skill:08537f7e63aa** [yijiashu/serenity-skill SKILL.md](https://github.com/yijiashu/serenity-skill/blob/main/SKILL.md) (2026-07-04, derived, inference, 置信度 0.66): 1. $NBIS ：946次（最常提及） 2. $SIVE ：817次（CPO"卡脖子"环节） 3. $LITE ：657次（Lumentum，光模块） 4. $AXTI ：620次（AXT Inc，半导体材料） 5. $IREN ：607次（Iris Energy，比特币挖矿） 6. $NVDA ：515次（NVIDIA，AI芯片） 7. $AAOI ：501次（Applied Optoelectronics，光模块） 8. $MSFT ：309次（微软） 9. $GOOGL ：303次（谷歌） 10. $ME...
- **github:ZadAnthony/serenity-skill:53011aa02f41** [ZadAnthony/serenity-skill SKILL.md](https://github.com/ZadAnthony/serenity-skill/blob/main/SKILL.md) (2026-07-04, speculative, inference, 置信度 0.56): name: serenity description: 用 Serenity(@aleabitoreddit)的"供应链卡点逆向"投资逻辑分析股票/板块——帮你判断该怎么分析、往哪一层挖、什么会证实或证伪、值不值得投。把市场当物理系统而非代码列表,先建 thesis 再谈标的。当用户聊美股/AI 供应链/光模块(CPO/硅光/InP)/半导体/内存/NeoCloud/电力液冷/机器人等 AI 全产业链任意细分的投资分析,或主动 /serenity 时使用。
- **github:fadewalk/serenity-stock-choke:3bdcbf3fe9f7** [fadewalk/serenity-stock-choke README.md](https://github.com/fadewalk/serenity-stock-choke/blob/main/README.md) (2026-07-04, derived, inference, 置信度 0.66): | 标的 | 代码 | 涨幅 | 卡脖子定位 | | | | | | | AXT Inc | AXTI.US | +525%（YTD） | InP 衬底全球唯三产商 | | Applied Optoelectronics | AAOI.US | +348%（YTD） | CPO 激光器主力供应商 | | Sivers Semiconductors | SIVE.SE | — | CPO 激光器 + 硅光子 | | X FAB | XFAB.EU | — | 特色工艺晶圆代工 |
- **github:kooui/serenity-framework:92551d1dae6f** [kooui/serenity-framework README.md](https://github.com/kooui/serenity-framework/blob/main/README.md) (2026-07-04, derived, inference, 置信度 0.66): Read the $AAOI Case Study to see how Serenity applied this framework in practice.
- **github:kooui/serenity-framework:dcbfa90b1fd4** [kooui/serenity-framework README.md](https://github.com/kooui/serenity-framework/blob/main/README.md) (2026-07-04, derived, inference, 置信度 0.66): 阅读$AAOI 案例分析，看看 Serenity 如何在实践中应用这个框架。
- **github:onebluecloud/serenity-playbook:79cd020126ab** [onebluecloud/serenity-playbook SKILL.md](https://github.com/onebluecloud/serenity-playbook/blob/main/SKILL.md) (2026-07-04, derived, inference, 置信度 0.66): 高 alpha 域 （回测验证）：光子学/CPO（ 1）、存储/HBM、先进封装/基板、半导体设备与材料。 次级域 （她自认非专长但有框架）：电力/电网设备、散热、机器人、防务/航天、NeoCloud。 No go （她明说 zero clue）：生物科技、建筑、地产、农业。她的 crypto/fintech 提及被回测证明是负 alpha——fade。
- **github:onebluecloud/serenity-playbook:c7b869d5c91c** [onebluecloud/serenity-playbook references/methodology.md](https://github.com/onebluecloud/serenity-playbook/blob/main/references/methodology.md) (2026-07-04, derived, inference, 置信度 0.66): "The 1 thing to look out for is hyperscaler capex projections and $TSM projections." （s/2058618801554604040）："AI capex spend is expected to go to '$3 to $4 trillion annually' by 2030 from Jensen Huang projections… own the keys of the AI Kingdom: $AXTI（材料）$SOI...
- **github:onebluecloud/serenity-playbook:ea8d18d130d5** [onebluecloud/serenity-playbook references/methodology.md](https://github.com/onebluecloud/serenity-playbook/blob/main/references/methodology.md) (2026-07-04, derived, inference, 置信度 0.66): （s/2030418917592903895）："Photonics is the next major bottleneck. $NVDA has signaled each one ahead of time from: HBM (Samsung/SK Hynix) to CoWoS and now with the $LITE and $COHR investment: Laser Fab, CPO, and InP." 产能锁定剧本（s/2050833230736269767）："$NVDA ate up...

## 怀疑者复核

- 风险证据 `sec-companyfacts:AAOI:1dde3c8a25f5`: Primary SEC companyfacts data shows AAOI FY2025 Net Income (Loss) Attributable to Parent of $-38,228,000 from a filed annual report accession 0001437749-26-005875.
- 风险证据 `github:fadewalk/serenity-stock-choke:a72c4ffa5a9c`: | 标的 | 代码 | 卡脖子定位 | 核心逻辑 | | | | | | | AXT Inc | AXTI.US | InP衬底全球唯三产商 | 6英寸InP产能全球稀缺 | | Applied Optoelectronics | AAOI.US | CPO激光器主力供应商 | 微软/谷歌核心供应商 | | Sivers Semiconductors | SIVE.SE | CPO激光器+硅光子 | 德国K受益产线 | | X FAB | XFAB.EU | 特色工艺晶圆代工 | 工业/汽车晶圆不可替代 |
- 风险证据 `github:yan-labs/serenity-aleabitoreddit:4fd75f23647d`: The February article is a crypto market structure critique. It is not relevant to the default AI/semi/CPO portfolio unless the user is evaluating BTC, stablecoin yield, crypto exchanges, crypto treasuries, or crypto legislation beta.
- 风险证据 `github:yan-labs/serenity-aleabitoreddit:9f509bd6d356`: Self reported, unverified returns. His YTD figures, from 237% in Feb 2026 to 4502.45% on May 26, are his own images. No independent verification exists. Estimated public call calibration, not trading proof. A 2026 05 27 recheck found ~61% 30 day directional a...
- 风险证据 `github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e`: What: Find the single point of failure in a fast growing supply chain — the upstream chokepoint a downstream buyer must pay through rather than design around. "Who is the real bottleneck?" Signal: A supplier with sole or near sole source position, pricing pow...
- 推测性证据在提高置信度前需要进一步确认：github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, github:ZadAnthony/serenity-skill:53011aa02f41。
- 检查社交关注度是否已经跑在公司确认的客户爬坡之前。
- 将瓶颈候选标的与替代供应商、客户内部采购方案进行对比。

## 失效条件

- AAOI 无法展示客户验证进展或 design-in 证据。
- 收入爬坡时间推迟，但估值或市场关注度已经提前反映成功预期。
- 替代供应商扩张快于预期，削弱原先判断的瓶颈属性。
- Primary filings、电话会记录或客户数据与推断的供应链角色相矛盾。

## 证据补齐行动清单

- **反证计划:** 明确哪些客户流失、替代供应扩张、毛利率恶化或收入延期会推翻当前论点。
- **拥挤度复核:** 增加估值、成交热度、社媒关注和预期兑现节奏的对照证据。
- **晋级门槛:** 在上述证据短板解决前，AAOI 只能保持观察池状态。

## 后续研究任务

- 为 company financials、component、interconnect、market_structure、memory、methodology 建立来源表，覆盖 primary filings、客户引用和产能线索。
- 对每一条关键论点区分直接证据与推断链接。
- 跟踪会改变需求确定性、供给弹性或交易拥挤度的新证据。
- 为每个关键论点步骤补充至少一个非 Serenity 来源。

## 免责声明

本报告仅供研究，不构成投资建议，不推荐任何交易；任何资金决策前都需要独立验证。
