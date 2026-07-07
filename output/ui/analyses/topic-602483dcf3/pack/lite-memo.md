# Serenity Alpha Lab 研究备忘录

**研究问题:** 存储芯片
**关注标的:** LITE
**证据数量:** 16
**综合研究评分:** 27/100
**Serenity 评级:** 观察池候选
**研究置信层级:** 低
**关键短板:** 综合评分偏低, 拥挤风险偏高

## 评分卡

| 因子 | 原始分 | 加权贡献 | 证据 |
|---|---:|---:|---|
| bottleneck scarcity | 49 | 11.8 | github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, github:yan-labs/serenity-aleabitoreddit:4fd75f23647d, github:yan-labs/serenity-aleabitoreddit:def987b8ef86, github:fadewalk/serenity-stock-choke:a72c4ffa5a9c, github:onebluecloud/serenity-playbook:ea8d18d130d5, github:yan-labs/serenity-aleabitoreddit:448d8ae69b1a, github:yan-labs/serenity-aleabitoreddit:65261a19982c, github:yan-labs/serenity-aleabitoreddit:80136fdc96d5, github:yan-labs/serenity-aleabitoreddit:ccb67a64ba63, github:muxuuu/serenity-skill:86f2b944edcb, github:onebluecloud/serenity-playbook:e4a0d025fd80, github:yan-labs/serenity-aleabitoreddit:d1e9674254cc |
| demand certainty | 43 | 9.5 | github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, github:yan-labs/serenity-aleabitoreddit:4fd75f23647d, github:yan-labs/serenity-aleabitoreddit:def987b8ef86, github:fadewalk/serenity-stock-choke:a72c4ffa5a9c, github:onebluecloud/serenity-playbook:ea8d18d130d5, github:yan-labs/serenity-aleabitoreddit:e73bd2d0ec43, sec-companyfacts:LITE:691f3ab6202a, github:yan-labs/serenity-aleabitoreddit:448d8ae69b1a, github:yan-labs/serenity-aleabitoreddit:65261a19982c, github:yan-labs/serenity-aleabitoreddit:80136fdc96d5, github:yan-labs/serenity-aleabitoreddit:ccb67a64ba63, github:muxuuu/serenity-skill:86f2b944edcb, github:onebluecloud/serenity-playbook:e4a0d025fd80, github:yan-labs/serenity-aleabitoreddit:d1e9674254cc |
| supply elasticity | 22 | 3.5 | github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, github:yan-labs/serenity-aleabitoreddit:4fd75f23647d, github:yan-labs/serenity-aleabitoreddit:def987b8ef86, github:fadewalk/serenity-stock-choke:a72c4ffa5a9c, github:onebluecloud/serenity-playbook:ea8d18d130d5, github:yan-labs/serenity-aleabitoreddit:65261a19982c, github:yan-labs/serenity-aleabitoreddit:80136fdc96d5, github:yan-labs/serenity-aleabitoreddit:ccb67a64ba63, github:muxuuu/serenity-skill:86f2b944edcb, github:onebluecloud/serenity-playbook:e4a0d025fd80, github:yan-labs/serenity-aleabitoreddit:d1e9674254cc |
| evidence quality | 49 | 7.8 | github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, github:yan-labs/serenity-aleabitoreddit:4fd75f23647d, github:yan-labs/serenity-aleabitoreddit:def987b8ef86, github:fadewalk/serenity-stock-choke:a72c4ffa5a9c, github:onebluecloud/serenity-playbook:ea8d18d130d5, github:yan-labs/serenity-aleabitoreddit:e73bd2d0ec43, sec-companyfacts:LITE:07dd4a6958ac, sec-companyfacts:LITE:49f8c5259831, sec-companyfacts:LITE:691f3ab6202a, github:yan-labs/serenity-aleabitoreddit:448d8ae69b1a, github:yan-labs/serenity-aleabitoreddit:65261a19982c, github:yan-labs/serenity-aleabitoreddit:80136fdc96d5, github:yan-labs/serenity-aleabitoreddit:ccb67a64ba63, github:muxuuu/serenity-skill:86f2b944edcb, github:onebluecloud/serenity-playbook:e4a0d025fd80, github:yan-labs/serenity-aleabitoreddit:d1e9674254cc |
| crowding risk (扣分) | 60 | -7.2 | github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, github:yan-labs/serenity-aleabitoreddit:4fd75f23647d, github:yan-labs/serenity-aleabitoreddit:def987b8ef86, github:fadewalk/serenity-stock-choke:a72c4ffa5a9c, github:onebluecloud/serenity-playbook:e4a0d025fd80 |
| invalidation clarity | 19 | 1.9 | github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, github:yan-labs/serenity-aleabitoreddit:4fd75f23647d, github:yan-labs/serenity-aleabitoreddit:def987b8ef86, github:fadewalk/serenity-stock-choke:a72c4ffa5a9c, github:onebluecloud/serenity-playbook:ea8d18d130d5, github:yan-labs/serenity-aleabitoreddit:e73bd2d0ec43, sec-companyfacts:LITE:07dd4a6958ac, sec-companyfacts:LITE:49f8c5259831, sec-companyfacts:LITE:691f3ab6202a, github:yan-labs/serenity-aleabitoreddit:448d8ae69b1a, github:yan-labs/serenity-aleabitoreddit:65261a19982c, github:yan-labs/serenity-aleabitoreddit:80136fdc96d5, github:yan-labs/serenity-aleabitoreddit:ccb67a64ba63, github:muxuuu/serenity-skill:86f2b944edcb, github:onebluecloud/serenity-playbook:e4a0d025fd80, github:yan-labs/serenity-aleabitoreddit:d1e9674254cc |

## 投资分析结论

LITE 当前可进入 Serenity 候选池复核。综合研究评分为 27/100，报告使用 16 条证据，其中 primary/fact 证据 3 条、风险/失效证据 4 条。下一步重点不是给出买卖建议，而是验证景气链条、瓶颈位置和业绩兑现路径。

## Serenity 选股因子

- **景气方向:** 当前证据覆盖 6 条正向线索和 4 条负向线索，需要判断需求是否已经传导到订单或收入。
- **产业链位置:** 已识别环节包括 company financials、component、interconnect、memory，优先寻找供需最紧、替代最难的节点。
- **主题映射:** 主要主题包括 A-share、AI infrastructure、AI supply-chain、CPO、SEC companyfacts、Serenity，需要区分行业 beta 与公司 alpha。
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
| company financials | 3 | 3 | 0 | SEC companyfacts, primary-source, profitability, revenue, share count |
| component | 5 | 0 | 2 | A-share, AI infrastructure, AI supply-chain, CPO, Serenity |
| interconnect | 1 | 0 | 1 | AI infrastructure, CPO, Serenity, risk, supply-chain bottleneck |
| memory | 7 | 0 | 1 | AI infrastructure, CPO, Serenity, memory, risk |

## 催化剂时间线

| 日期 | 类型 | 标的 | 证据 |
|---|---|---|---|
| 2025-08-19 | fact | LITE | Primary SEC companyfacts data shows LITE FY2025 Net Income (Loss) Attributable to Parent of $25,900,000 from a filed annual report accession 0001628280-25-040830. |
| 2025-08-19 | fact | LITE | Primary SEC companyfacts data shows LITE FY2025 Entity Common Stock, Shares Outstanding of 69,900,000 shares from a filed annual report accession 0001628280-25-040830. |
| 2025-08-19 | fact | LITE | Primary SEC companyfacts data shows LITE FY2025 Revenue from Contract with Customer, Excluding Assessed Tax of $1,645,000,000 from a filed annual report accession 0001628280-25-040830. |
| 2026-07-04 | catalyst | SIVE, AAOI, LITE, COHR | Sound like a direct investment research partner: |
| 2026-07-04 | catalyst | AXTI, IREN, LITE, LPK | `` 1. 锚定需求 → 2. 多跳拆链 → 3. 锁定卡点 → 4. OSINT 证据包 → 5. 财务翻译 → 6. 仓位构建 → 7. 论点维护 `` |
| 2026-07-04 | catalyst | SOI, RKLB, AXTI, SIVE | What: Explicit tiering (S/A/B/C/D/F lists) and conviction scaled sizing; smaller size on binary microcaps; calls instead of shares when a name could go to zero (e.g. China export ban risk). Signal: "Fundamentally de risked" (Mag7 counterparty + locked take or... |

## 证据缺口优先级

| 优先级 | 缺口 | 影响 | 下一步证据 |
|---|---|---|---|
| P1 | crowding_risk | 拥挤度升高会压缩安全边际并放大回撤。 | 增加估值、成交热度、社媒关注和预期兑现节奏的对照证据。 |

## 论点摘要

LITE 目前形成的是一个临时性的 Serenity 风格研究案例，覆盖 company financials、component、interconnect、memory。当前最强主题包括 A-share、AI infrastructure、AI supply-chain、CPO、SEC companyfacts。该案例由 6 条正向证据支撑，同时受到 4 条明确风险证据约束。只有当 primary evidence 进一步确认客户验证、收入爬坡节奏和替代供给受限时，研究置信度才应提高。

## 声明类型组合

catalyst: 3, fact: 3, inference: 6, risk: 4

## 来源覆盖

**Focus ticker:** LITE

**Coverage counts:** evidence 16, focus ticker 16, primary/fact 3, risk 4, external non-Serenity 3

**Concentration:** methodology 0%, SERENITY placeholder 0%

**Gate result:** No critical coverage flags.

## Primary Source 证据

- **sec-companyfacts:LITE:07dd4a6958ac** [SEC companyfacts LITE Net Income (Loss) Attributable to Parent](https://data.sec.gov/api/xbrl/companyfacts/CIK0001633978.json) (2025-08-19, primary, fact, 置信度 0.88): Primary SEC companyfacts data shows LITE FY2025 Net Income (Loss) Attributable to Parent of $25,900,000 from a filed annual report accession 0001628280-25-040830.
- **sec-companyfacts:LITE:49f8c5259831** [SEC companyfacts LITE Entity Common Stock, Shares Outstanding](https://data.sec.gov/api/xbrl/companyfacts/CIK0001633978.json) (2025-08-19, primary, fact, 置信度 0.88): Primary SEC companyfacts data shows LITE FY2025 Entity Common Stock, Shares Outstanding of 69,900,000 shares from a filed annual report accession 0001628280-25-040830.
- **sec-companyfacts:LITE:691f3ab6202a** [SEC companyfacts LITE Revenue from Contract with Customer, Excluding Assessed Tax](https://data.sec.gov/api/xbrl/companyfacts/CIK0001633978.json) (2025-08-19, primary, fact, 置信度 0.88): Primary SEC companyfacts data shows LITE FY2025 Revenue from Contract with Customer, Excluding Assessed Tax of $1,645,000,000 from a filed annual report accession 0001628280-25-040830.

## 行业上下文证据

- 没有匹配到跨标的 primary source 上下文。

## 支撑证据

- **github:onebluecloud/serenity-playbook:ea8d18d130d5** [onebluecloud/serenity-playbook references/methodology.md](https://github.com/onebluecloud/serenity-playbook/blob/main/references/methodology.md) (2026-07-04, derived, inference, 置信度 0.66): （s/2030418917592903895）："Photonics is the next major bottleneck. $NVDA has signaled each one ahead of time from: HBM (Samsung/SK Hynix) to CoWoS and now with the $LITE and $COHR investment: Laser Fab, CPO, and InP." 产能锁定剧本（s/2050833230736269767）："$NVDA ate up...
- **github:yan-labs/serenity-aleabitoreddit:e73bd2d0ec43** [yan-labs/serenity-aleabitoreddit serenity-aleabitoreddit/SKILL.md](https://github.com/yan-labs/serenity-aleabitoreddit/blob/main/serenity-aleabitoreddit/SKILL.md) (2026-07-04, derived, inference, 置信度 0.66): 1. Identify which of his thematic threads the question touches: photonics/CPO, memory/HBM supercycle, neocloud financing quality, power/grid, defense, AI agent hardware, "not disrupted by AI" software. 2. Pull the relevant theses and thread summaries from ref...
- **github:yan-labs/serenity-aleabitoreddit:448d8ae69b1a** [yan-labs/serenity-aleabitoreddit serenity-aleabitoreddit/references/methodology.md](https://github.com/yan-labs/serenity-aleabitoreddit/blob/main/serenity-aleabitoreddit/references/methodology.md) (2026-07-04, derived, inference, 置信度 0.66): What: Build a Bill of Materials for hyperscaler infrastructure by chaining hops from capex commitment down to feedstock, then identify who chokes each layer. He notes AI chatbots fail at this because the connections are obscured multi hop. Signal: Conference...
- **github:yan-labs/serenity-aleabitoreddit:65261a19982c** [yan-labs/serenity-aleabitoreddit README.md](https://github.com/yan-labs/serenity-aleabitoreddit/blob/main/README.md) (2026-07-04, derived, inference, 置信度 0.66): Claude Code (project local): cp r serenity aleabitoreddit <your project /.agents/skills/ ln s ../../.agents/skills/serenity aleabitoreddit <your project /.claude/skills/serenity aleabitoreddit Tickers: SIVE, AAOI, LITE, COHR. Themes: CPO, AI infrastructure, supply-chain bottleneck, semiconductor. Source: yan-labs/serenity-aleabitoreddit README.md.
- **github:yan-labs/serenity-aleabitoreddit:80136fdc96d5** [yan-labs/serenity-aleabitoreddit serenity-aleabitoreddit/SKILL.md](https://github.com/yan-labs/serenity-aleabitoreddit/blob/main/serenity-aleabitoreddit/SKILL.md) (2026-07-04, derived, inference, 置信度 0.66): 1. Take the list of tickers the reader provides (their holdings, a watchlist, a sector basket). 2. For each name, pull his view from references/theses.md and bucket into: Agreements — he is bullish on it. Conflicts — he is bearish/cautious on it (surface his...
- **github:yan-labs/serenity-aleabitoreddit:ccb67a64ba63** [yan-labs/serenity-aleabitoreddit README.md](https://github.com/yan-labs/serenity-aleabitoreddit/blob/main/README.md) (2026-07-04, derived, inference, 置信度 0.66): Don't buy the obvious shovel seller (NVDA) — trace the supply chain upstream to the single chokepoint a hyperscaler will pay anything to keep flowing (optical/CPO, compound semi substrates, memory, power), where the small market cap is most mispriced relative...
- **github:muxuuu/serenity-skill:86f2b944edcb** [muxuuu/serenity-skill SKILL.md](https://github.com/muxuuu/serenity-skill/blob/main/SKILL.md) (2026-07-04, speculative, catalyst, 置信度 0.56): Sound like a direct investment research partner:
- **github:onebluecloud/serenity-playbook:e4a0d025fd80** [onebluecloud/serenity-playbook SKILL.md](https://github.com/onebluecloud/serenity-playbook/blob/main/SKILL.md) (2026-07-04, speculative, catalyst, 置信度 0.56): `` 1. 锚定需求 → 2. 多跳拆链 → 3. 锁定卡点 → 4. OSINT 证据包 → 5. 财务翻译 → 6. 仓位构建 → 7. 论点维护 ``
- **github:yan-labs/serenity-aleabitoreddit:d1e9674254cc** [yan-labs/serenity-aleabitoreddit serenity-aleabitoreddit/references/methodology.md](https://github.com/yan-labs/serenity-aleabitoreddit/blob/main/serenity-aleabitoreddit/references/methodology.md) (2026-07-04, speculative, catalyst, 置信度 0.56): What: Explicit tiering (S/A/B/C/D/F lists) and conviction scaled sizing; smaller size on binary microcaps; calls instead of shares when a name could go to zero (e.g. China export ban risk). Signal: "Fundamentally de risked" (Mag7 counterparty + locked take or...

## 怀疑者复核

- 风险证据 `github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e`: What: Find the single point of failure in a fast growing supply chain — the upstream chokepoint a downstream buyer must pay through rather than design around. "Who is the real bottleneck?" Signal: A supplier with sole or near sole source position, pricing pow...
- 风险证据 `github:yan-labs/serenity-aleabitoreddit:4fd75f23647d`: The February article is a crypto market structure critique. It is not relevant to the default AI/semi/CPO portfolio unless the user is evaluating BTC, stablecoin yield, crypto exchanges, crypto treasuries, or crypto legislation beta.
- 风险证据 `github:yan-labs/serenity-aleabitoreddit:def987b8ef86`: Score a candidate against his lens. The more "yes", the more it fits his style — none of this is a buy signal on its own.
- 风险证据 `github:fadewalk/serenity-stock-choke:a72c4ffa5a9c`: | 标的 | 代码 | 卡脖子定位 | 核心逻辑 | | | | | | | AXT Inc | AXTI.US | InP衬底全球唯三产商 | 6英寸InP产能全球稀缺 | | Applied Optoelectronics | AAOI.US | CPO激光器主力供应商 | 微软/谷歌核心供应商 | | Sivers Semiconductors | SIVE.SE | CPO激光器+硅光子 | 德国K受益产线 | | X FAB | XFAB.EU | 特色工艺晶圆代工 | 工业/汽车晶圆不可替代 |
- 推测性证据在提高置信度前需要进一步确认：github:yan-labs/serenity-aleabitoreddit:ac1cef9a784e, github:yan-labs/serenity-aleabitoreddit:def987b8ef86, github:muxuuu/serenity-skill:86f2b944edcb, github:onebluecloud/serenity-playbook:e4a0d025fd80, github:yan-labs/serenity-aleabitoreddit:d1e9674254cc。
- 检查社交关注度是否已经跑在公司确认的客户爬坡之前。
- 将瓶颈候选标的与替代供应商、客户内部采购方案进行对比。

## 失效条件

- LITE 无法展示客户验证进展或 design-in 证据。
- 收入爬坡时间推迟，但估值或市场关注度已经提前反映成功预期。
- 替代供应商扩张快于预期，削弱原先判断的瓶颈属性。
- Primary filings、电话会记录或客户数据与推断的供应链角色相矛盾。

## 证据补齐行动清单

- **拥挤度复核:** 增加估值、成交热度、社媒关注和预期兑现节奏的对照证据。
- **晋级门槛:** 在上述证据短板解决前，LITE 只能保持观察池状态。

## 后续研究任务

- 为 company financials、component、interconnect、memory 建立来源表，覆盖 primary filings、客户引用和产能线索。
- 对每一条关键论点区分直接证据与推断链接。
- 跟踪会改变需求确定性、供给弹性或交易拥挤度的新证据。
- 为每个关键论点步骤补充至少一个非 Serenity 来源。

## 免责声明

本报告仅供研究，不构成投资建议，不推荐任何交易；任何资金决策前都需要独立验证。
