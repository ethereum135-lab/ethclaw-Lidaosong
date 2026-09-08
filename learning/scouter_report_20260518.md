# ZH侦察报告（为ZQ系统）— 2026-05-18 08:12

> **侦察视角：** ZH总控的独立侦察兵，不是ZQ-Scouter
> **扫描时间：** 2026-05-18 08:12 CST（周一例行全网扫描）
> **上次报告：** 2026-05-11（第1期）
> **方法：** GitHub API搜索（6个方向×10结果×10条阅读）+ README详细审查

---

## 执行摘要

本期扫描发现 **8个值得关注的新工具/库**（较上期+1），其中 **2个强烈推荐集成**、**3个推荐参考学习**、**3个可关注**。

**重大变化：** 过去一周（5/11→5/18），ZQ系统状态发生显著转变。系统从$319冻结状态逐步恢复至$303-$312区间稳定运行。A4引擎稳定执行（每30分钟节点），A3牛币官持续产出，但系统整体仍处保守阶段（USDT>$199现金储备，多币种HOLD为主）。从侦察角度看，系统当前最需要的不是更多工具，而是**让已有工具发挥作用**——特别是上期推荐的CCXT（已装零使用）和Etherscan Monitor（已写零调用）。

**本期核心发现：**
- ⭐⭐ **btc-hedge-lab** — BTC对冲策略实验室（delta对冲/基差/资金费率捕获/保护性看跌/领子期权），可直接填补ZQ缺少的**风控对冲策略维度**
- ⭐⭐ **Vyntral/arkham-intelligence-claude-skill** — Arkham Intelligence链上分析，鲸鱼追踪+智能钱+钱包分析，填补A1**聪明钱包/链上数据维度**
- ⭐ **clementslowik/funding-collector** — 多交易所资金费率收集器，无需API密钥，可替代当前零散的资金费率采集
- ⭐ **shakeebshaan/awesome-crypto-trading-agents** — 2026年最全的加密交易Agent列表，可作为持续学习的入口清单

---

## 新工具发现

### ⭐⭐ btc-hedge-lab（强烈推荐）
| 字段 | 值 |
|:-----|:----|
| 平台 | `shakeebshaan/btc-hedge-lab`（GitHub） |
| 免费/付费 | 完全免费（MIT） |
| 星数 | 新项目，高质量代码（2026年4月创建） |
| 语言 | Python 3.11+ |
| 集成难度 | 中等（~200行封装层） |
| 推荐理由 | **ZQ当前缺少风控对冲策略维度**。该库提供5种可验证的BTC对冲策略：delta对冲、基差交易、资金费率捕获、保护性看跌、领子期权。向量化pandas实现，回测速度快，可直接嵌入Quant的每日分析流程 |
| 弥补缺口 | 策略多样性 / 风控对冲 |
| URL | https://github.com/shakeebshaan/btc-hedge-lab |

**集成方案：** 作为Quant的辅助分析工具，在每日23:00分析流程中增加对冲策略评估模块。ZQ以小资本为主（~$300），BTC对冲策略可帮助保护现有持仓不因系统性下跌而爆仓。

---

### ⭐⭐ Vyntral/arkham-intelligence-claude-skill（强烈推荐）
| 字段 | 值 |
|:-----|:----|
| 平台 | `Vyntral/arkham-intelligence-claude-skill`（GitHub） |
| 免费/付费 | 需Arkham API Key（有免费额度） |
| 星数 | 13★，2026-05-10创建 |
| 语言 | Shell + Claude Code Skill |
| 集成难度 | 简单（API key配置 + ~50行对接） |
| 推荐理由 | **直接填补A1数据官3/6维度的链上聪明钱包缺口**。Arkham Intelligence支持10+链，可追踪鲸鱼移动、分析钱包持仓、监控智能钱、研究交易所/做市商实体资金流。这正是ZQ在05-11 SHARED.md中标记的P1待办 |
| 弥补缺口 | 链上数据 / 聪明钱包追踪 / 鲸鱼检测 |
| URL | https://github.com/Vyntral/arkham-intelligence-claude-skill |

**集成方案：** 申请Arkham API Key（免费额度足够小规模使用），封装为A1的数据插件，每日采集链上鲸鱼数据和智能钱流动。与已有Etherscan Monitor互补（Etherscan看单地址，Arkham看实体级资金流）。

---

### ⭐ clementslowik/funding-collector（推荐参考）
| 字段 | 值 |
|:-----|:----|
| 平台 | `clementslowik/funding-collector`（GitHub） |
| 免费/付费 | 完全免费（MIT） |
| 星数 | 新项目（2026-04） |
| 语言 | Python 3.x |
| 集成难度 | 极简（`pip install` + 3行代码） |
| 推荐理由 | ZQ当前资金费率数据源分散（从CoinGecko和交易所分别采集）。funding-collector统一Binance/Bybit/OKX三所资金费率+24h成交量，SQLite存储，**无需API密钥**。自动计算每个symbol的正确结算间隔（4h/8h/1h），避免年化收益率算错 |
| 弥补缺口 | 费率数据标准化 / 多交易所费率对比 |
| URL | https://github.com/clementslowik/funding-collector |

---

### ⭐ shakeebshaan/awesome-crypto-trading-agents（推荐持续跟踪）
| 字段 | 值 |
|:-----|:----|
| 平台 | `shakeebshaan/awesome-crypto-trading-agents`（GitHub） |
| 免费/付费 | 完全免费（CC0） |
| 星数 | 新列表（2026-04），内容质量高 |
| 语言 | 资源列表 |
| 集成难度 | 读就完了 |
| 推荐理由 | **这是2026年最全的加密交易Agent资源汇编**。涵盖AI Agent框架（jesse-ai/freqtrade/tensortrade）、回测引擎、策略库、数据源、RL框架、执行层、风险对冲、LLM+交易、学术论文等10+分类。可作为Scouter每周扫描的起点清单 |
| 弥补缺口 | 持续学习的入口 / 未来工具发现的索引 |
| URL | https://github.com/shakeebshaan/awesome-crypto-trading-agents |

---

### 🟡 Aliipou/mm-live（可能有用，观察）
| 字段 | 值 |
|:-----|:----|
| 平台 | `Aliipou/mm-live`（GitHub） |
| 免费/付费 | MIT |
| 星数 | 3★，2026-05新项目 |
| 语言 | Python 3.11+ |
| 集成难度 | 复杂（独立做市引擎，需完整部署） |
| 推荐理由 | 事件驱动的实时做市系统：Kalman滤波公允定价 + Avellaneda-Stoikov自适应报价 + 跨所套利。336个测试用例全部通过，代码质量高。适合ZQ未来扩大规模后引入做市策略，当前小资本阶段不急需 |
| 弥补缺口 | 做市策略维度（远期） |
| URL | https://github.com/Aliipou/mm-live |

---

### 🟡 gizdusum/hermes-blockchain-oracle（可能有用，观察）
| 字段 | 值 |
|:-----|:----|
| 平台 | `gizdusum/hermes-blockchain-oracle`（GitHub） |
| 免费/付费 | MIT |
| 星数 | 4★，2026-05-17（昨天创建！） |
| 语言 | Python 3.10+ |
| 集成难度 | 简单（`pip install hermes-blockchain-oracle`） |
| 推荐理由 | 专为Hermes Agent设计的Solana区块链MCP服务器。支持钱包查询、代币信息、NFT、交易详情、**实时鲸鱼检测**、网络健康。因为刚创建（1天），可能不稳定，但方向正确。不急于集成，观察几周 |
| 弥补缺口 | Solana链上数据 / 鲸鱼检测（远期） |
| URL | https://github.com/gizdusum/hermes-blockchain-oracle |

---

### 🟡 fintechees/Expert-Advisor-Studio（可能有用，观察）
| 字段 | 值 |
|:-----|:----|
| 平台 | `fintechees/Expert-Advisor-Studio`（GitHub） |
| 免费/付费 | 免费+商业版 |
| 星数 | 344★ |
| 语言 | JavaScript |
| 集成难度 | 中等（JS生态，与ZQ Python栈不直接兼容） |
| 推荐理由 | 免费Crypto/Forex历史数据API插件、浏览器端EA代码生成器。数据API部分可直接用，EA部分与ZQ不兼容。建议只提取其免费数据API部分 |
| 弥补缺口 | 历史数据源（补充） |
| URL | https://github.com/fintechees/Expert-Advisor-Studio |

---

### 🟡 zbarge/stocklook（可能有用，观察）
| 字段 | 值 |
|:-----|:----|
| 平台 | `zbarge/stocklook`（GitHub） |
| 免费/付费 | 开源 |
| 星数 | 173★ |
| 语言 | Python |
| 集成难度 | 中等 |
| 推荐理由 | 多交易所（BitMEX/Bittrex/CoinBase/Gdax/Poloniex）统一API封装，内置市场做市spread交易。但部分交易所API可能已过时（Cryptopia已关），且其市场做市功能已被mm-live取代。不优先推荐 |
| 弥补缺口 | 多交易所统一API（但CCXT已覆盖） |
| URL | https://github.com/zbarge/stocklook |

---

## 新策略发现

### 1. BTC对冲策略集合（btc-hedge-lab）
5种对冲策略，向量化回测已验证：
| 策略 | 年化收益 | 最大回撤 | Sharpe |
|:-----|:--------:|:--------:|:-----:|
| 裸多Buy-and-Hold | +142.3% | -76.8% | 0.81 |
| 50% delta对冲 | +58.4% | -24.1% | 1.24 |

**对ZQ的价值：** 当前ZQ以趋势/动量策略为主，无任何对冲机制。加入delta对冲策略后，可在系统性下跌时保护持仓。建议作为Quant的每日分析辅助工具，当F&G<30（目前正是F&G=27极度恐惧）时评估是否需要对冲。

### 2. 资金费率套利策略
- **fundarb（mkzung）** — 跨所资金费率套利CLI（Hyperliquid+Orderly+Backpack），专注资金费率差异捕获
- **SAGISaiKrishna/crypto-arbitrage-strategy** — Delta中性ETH资金费率捕获（2021-2026回测）
- **GareBear99/BrokeBot** — TRON资金费率套利，ATR止损，每日/连续止损熔断

**对ZQ的价值：** $300小资本难以执行完整的资金费率套利（需要同时开多空头寸锁定仓位），但可以作为策略储备。当ZQ资本扩大到$1000+时可考虑。

### 3. Avellaneda-Stoikov做市策略（mm-live）
学术界经典的做市模型，mm-live实现了完整的事件驱动版本。ZQ当前不适合做市策略（资本太小、订单簿深度不足），但可作为远期储备。

---

## 新数据源发现

| 数据源 | 类型 | 免费/付费 | 填补缺口 | 集成难度 | 对比现有 |
|:-------|:-----|:---------:|:---------|:--------:|:---------|
| **Arkham Intelligence API** | 链上智能钱/鲸鱼追踪 | 免费额度 | **聪明钱包追踪⭐** | 简单 | 完全填补当前缺口（A1 3/6维度） |
| **funding-collector** | 多交易所资金费率 | 完全免费 | 费率数据标准化 | 极简 | 替代现有零散费率采集 |
| **fintechees 免费数据API** | 历史Crypto数据 | 免费+付费 | 历史数据补充 | 中等 | 补充现有Binance数据 |
| **Hermes Blockchain Oracle** | Solana链上数据 | 免费 | Solana链上（远期） | 简单 | 初期不优先 |

---

## 对比历史（2026-05-11 vs 2026-05-18）

### 上期（05-11）推荐了什么

| 推荐项 | 类型 | 本期状态 |
|:-------|:-----|:--------|
| **hftbacktest** ⭐ 回测引擎 | 强烈推荐 | **未集成** — 仍无回测引擎 |
| **Tomortec/CryptoTradingAgents** ⭐ 多Agent数据源 | 强烈推荐 | **未集成** — 数据多样性缺口的建议未被采纳 |
| sserrano44/CryptoAgents (LangGraph编排) | 参考学习 | 仍未集成 |
| OctoBot-Market-Making (做市) | 参考学习 | 被mm-live替代（更先进） |
| TradeCat (Agent数据流架构) | 参考学习 | 未被采纳 |
| OnChainIQ (链上数据聚合) | 参考学习 | 未被采纳 |
| CryptoInsight (NLP新闻情绪) | 参考学习 | 未被采纳 |
| CCXT（已装零使用） | ⭐ P0今天 | **仍零使用** — 已装但未被A4引擎调用 |

### 上期P0今天（05-11报告）的执行情况
- ✅ CCXT集成（解决Binance 451）→ **未完成**。CCXT已装但未被任何Agent调用
- ✅ 激活Etherscan Monitor → **未完成**。代码存在但从未被调用

### 本期新增（05-18）
| 新增项 | 对ZQ的价值 | 推荐级别 |
|:-------|:----------|:--------:|
| **btc-hedge-lab** — BTC对冲策略 | 填补风控对冲维度 | ⭐⭐ |
| **Arkham Intelligence Skill** — 链上智能钱 | 填补聪明钱包数据缺口 | ⭐⭐ |
| **funding-collector** — 费率标准化 | 改进现有费率数据 | ⭐ |
| **awesome-crypto-trading-agents** — 资源列表 | 持续学习入口 | ⭐ |
| mm-live — 做市引擎 | 远期储备 | 🟡 |
| Hermes Blockchain Oracle | 远期储备 | 🟡 |

### 趋势判断
**上期的7个推荐中，0个被实际集成。** 这是系统性的"发现→集成"断裂。部分原因可以理解（系统在05-11到05-18经历了$319→$315→$302→$312的波动期），但Scouter的推荐-集成闭环仍未形成。

---

## 对ZQ系统的改进建议

### P0 — 本周必须解决

1. **上期P0闭环：激活CCXT + Etherscan Monitor**
   - CCXT已装（`ccxt 4.5.45`）但在任何Agent中未被import
   - Etherscan Monitor已有完整代码（131行）+ API Key就绪，但从未被调用
   - **这是老李铁律一"日事日毕"的直接违反** — 两周前的P0任务仍未闭环
   - 建议Commander今天08:30决策：谁负责激活这两个已就绪资产

2. **建立"推荐-评估-决策-集成"四步闭环**
   - 当前Scouter产出报告后，Commander无响应机制
   - 建议在`SHARED.md`增加"Scouter推荐追踪表"，每期推荐都标记：✅已集成/🔄评估中/❌已排除
   - 参考BHZ闭环专员检查机制

### P1 — 本周评估

3. **评估接入Arkham Intelligence API填补聪明钱包数据缺口**
   - A1当前3/6维度已接入（市场/费率/情绪）
   - 缺口维度：聪明钱包（P1）、链上数据（P1）、新闻舆情（P2）
   - Arkham Intelligence API免费额度足够小规模使用
   - 集成后可立即改善NBZ的选币数据质量

4. **评估btc-hedge-lab的delta对冲策略**
   - 当前F&G=27极度恐惧区间，系统性风险较高
   - 最简单的对冲方式：在Binance永续合约开等量空单对冲现货
   - 建议Quant在今晚23:00分析中评估：是否应在当前恐惧区间引入对冲

5. **用funding-collector替换现有零散费率采集**
   - 现有费率数据分散在多处（CoinGecko + 交易所直采）
   - funding-collector统一三所费率+正确结算间隔+24h成交量
   - 集成难度极低（`pip install funding-collector` + 3行代码）

### P2 — 持续改进

6. **将awesome-crypto-trading-agents作为Scouter的持续学习入口**
   - 该列表持续更新，覆盖10+分类
   - 建议Scouter每周从该列表中选取2-3个未评估的项目深入审查

7. **监控mm-live的发展（做市策略远期储备）**
   - 当前336测试用例全部通过，代码质量高
   - 当ZQ资本>$1000时，做市策略可增加策略多样性

### 当前ZQ系统健康诊断（基于自检报告05-18 07:00）

> 以下为引用数据校验：
> - 总资$312.85（来源：`shared/global_state.json` 2026-05-18 06:55，但需Binance API确认实时值）
> - USDT现金$199.56（来源：A4节点数据，需Binance API验证）
> - F&G=27极度恐惧（来源：A1数据官05-18 06:03产出）
> - 系统评分32/35（来源：ZJ自检官05-18 07:00）

**核心矛盾：** 系统功能完善（32/35分），但实际交易活性低（8笔/周）。USDT现金占比~63.8%（$199.56/$312.85），大量现金闲置。这不是工具缺乏的问题，而是策略信心和决策效率的问题。

**Scouter的诚实判断：** ZQ当前最需要的不全是新工具，而是将已有工具（CCXT、Etherscan Monitor）和上期推荐（hftbacktest回测、Tomortec数据源）真正用起来。本期推荐的btc-hedge-lab和Arkham Intelligence是锦上添花，不是雪中送炭。

---

## 附录：已排除项（不写入推荐）

| 项目 | 排除原因 |
|:-----|:---------|
| fatalik98955/solana-trading-bot-2026 | 2★，0 fork，疑似低质量Scam项目 |
| FiendMailman/TRX-Crypto-Tool-2026（及变体） | 疑似恶意软件/drainer（trx-drainer-tool标签） |
| CryptoWolf-s/cryptowolfs | 0★，HTML项目，非可用工具 |
| KafKafrnZ/Market_Making_Model-Crypto- | 1★，LSTM做市模型但代码质量不可评估 |
| pranay123-stack/crypto-hft-market-making-trading-profitable-system | 1★，名称夸大（"profitable system"），实际为空壳 |
| SAGISaiKrishna/crypto-arbitrage-strategy | 0★，策略思路好但不可用（仅Jupyter Notebook） |

---

*ZH侦察签名：2026-05-18 08:12 CST*
*下一期扫描：2026-05-25（周一08:00）*
*报告文件：`learning/scouter_report_20260518.md`*
