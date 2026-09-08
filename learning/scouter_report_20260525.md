# ZH侦察报告（为ZQ系统）— 2026-05-25 00:20

> **侦察视角：** ZH总控的独立侦察兵（不是ZQ-Scouter）
> **扫描时间：** 2026-05-25 00:20 CST（周一例行全网扫描）
> **上次报告：** 2026-05-18（第2期）
> **方法：** GitHub API搜索（6个方向×多关键词搜索）+ README详细审查 + 实时余额验证

---

## 执行摘要

本期扫描发现 **7个值得关注的新工具/库**，其中 **2个强烈推荐集成**、**2个推荐参考学习**、**3个可关注观察**。

**自05-18以来的重大变化：** ZQ系统在过去一周经历了显著退化。

| 指标 | 上期（05-18） | 当前（05-25） | 变化 |
|:----|:-----------:|:-----------:|:----:|
| 总权益 | $312.85 | **$296.68** | **-5.2%** 🔴 |
| USDT现金 | $199.56 | **$73.44** | **-63.2%** 🔴 |
| A3 findings.md | 存在 | **文件缺失** | 🔴 管线断裂 |
| NBZ findings | 较新 | **15天+陈旧** | 🔴 停摆 |
| 健康评分 | 32/35 | n/a | 退化 |
| 新交易 | 8笔/周 | **几乎零交易** | 🔴 |

**最严重的发现：05-18报告的P0推荐（CCXT集成 + Etherscan Monitor激活）依然未被集成。同一批P0任务已经持续3周未闭环。** 这是铁律一"日事日毕"的持续违反。

**本期核心发现来源：** 由于传统搜索引擎（**DuckDuckGo/Bing全部触发验证码拦截**），本期改用GitHub API搜索6大方向，辅以补充搜索。数据全部来自GitHub公开仓库。

---

## 新工具发现

### ⭐⭐ brokermr810/QuantDinger（强烈推荐）

| 字段 | 值 |
|:-----|:----|
| 平台 | `brokermr810/QuantDinger`（GitHub） |
| 免费/付费 | 完全开源 |
| 星数 | **6,420★**（极高质量项目） |
| 语言 | Python 3.x |
| 更新日期 | 2026-05-24（今日仍有更新） |
| 推荐理由 | AI量化交易平台，支持Crypto/股票/外汇三市场。内置回测+实时交易+市场数据+**多Agent研究**（"vibe-trading, trading-agents, ai-trader, ai-trading"）。这恰好是ZQ系统当前最缺的三大功能合一：回测验证 + 多Agent协作 + AI驱动。号称"开箱即用的AI量化交易平台" |
| 弥补缺口 | **策略回测维度 / Agent数据架构参考** |
| 集成难度 | 中等（参考架构设计，非直接替换） |
| URL | https://github.com/brokermr810/QuantDinger |

**集成方案：** 不是替换ZQ引擎，而是抽取其多Agent研究模块的架构思路（"vibe trading"、"trading-agents"），参考其AI交易模式设计，用于改进A4引擎的决策流程。Quant也可以参考其回测实现来补ZQ缺乏独立回测引擎的缺口。

---

### ⭐⭐ braedonsaunders/homerun（强烈推荐）

| 字段 | 值 |
|:-----|:----|
| 平台 | `braedonsaunders/homerun`（GitHub） |
| 免费/付费 | 完全开源 |
| 星数 | **73★**（新项目但质量高） |
| 语言 | Python 3.x |
| 推荐理由 | **开源预测市场交易平台**，支持Polymarket & Kalshi。可编写完整的Python策略和数据源→回测→模拟/实盘交易。内置25+策略、跟单交易（copy trading）、AI策略。对ZQ来说最吸引人的是**预测市场交易**维度——这是ZQ完全空白的方向。当前ZQ只做Binance现货/合约，预测市场（Polymarket/Kalshi）提供了不同维度的alpha |
| 弥补缺口 | **策略多样性 / 预测市场维度（新维度）** |
| 集成难度 | 中等（独立模块运行，与现有引擎并行） |
| URL | https://github.com/braedonsaunders/homerun |

**集成方案：** 作为Blade的一个可选模块，初期在Polymarket开小仓位（$10-20）测试预测市场交易策略。预测市场与现货市场低相关性，可在ZQ主系统冻结时提供替代盈利渠道。

---

### ⭐ clawinfra/whalecli（推荐参考）

| 字段 | 值 |
|:-----|:----|
| 平台 | `clawinfra/whalecli`（GitHub） |
| 免费/付费 | 完全开源 |
| 星数 | 新项目（2026-02） |
| 语言 | Python |
| 推荐理由 | **Agent原生鲸鱼钱包追踪CLI** + OpenClaw skill。实时链上资金流分析，JSONL流式输出供自主Agent使用。这正是ZQ系统从05-11开始就标记为P1需要的"链上聪明钱包"维度。同样服务于"聪明钱包追踪"缺口 |
| 弥补缺口 | **链上聪明钱包追踪 / 鲸鱼检测** |
| 集成难度 | 简单（CLI工具，直接调用） |
| URL | https://github.com/clawinfra/whalecli |

**集成方案：** pip安装后作为A1数据官的数据源插件，每日定时执行whalecli抓取鲸鱼活动数据，输出JSONL供NBZ和A3分析使用。与上期推荐的Arkham Intelligence Skill互补（Arkham看实体级，whalecli看钱包级）。

---

### ⭐ LLAW442/onchain-analysis（推荐参考）

| 字段 | 值 |
|:-----|:----|
| 平台 | `LLAW442/onchain-analysis`（GitHub） |
| 免费/付费 | 开源 |
| 星数 | 1★（新项目） |
| 语言 | Python |
| 推荐理由 | 可扩展链上分析平台，支持**区块交易追踪、鲸鱼活动检测、聪明钱流实时分析**。与whalecli互补——whalecli是CLI工具，这个是分析平台。代码结构清晰，可抽取其鲸鱼检测模块 |
| 弥补缺口 | **链上数据分析 / 聪明钱流动** |
| 集成难度 | 简单（~100行整合鲸鱼检测算法） |
| URL | https://github.com/LLAW442/onchain-analysis |

---

### 🟡 Cryptotrademate/cryptotrademate-backtesting-tool（可关注）

| 字段 | 值 |
|:-----|:----|
| 平台 | `Cryptotrademate/cryptotrademate-backtesting-tool`（GitHub） |
| 免费/付费 | 开源 |
| 星数 | 4★ |
| 语言 | Python |
| 推荐理由 | 开源回测工具，支持模拟/分析/优化加密货币策略。如果ZQ最终不集成QuantDinger，可以用它作为轻量替代。但当前价值有限——ZQ最缺的不是更多回测工具，而是把已有的回测需求真正写代码实现 |
| 弥补缺口 | 策略回测 |
| 集成难度 | 简单 | 
| URL | https://github.com/Cryptotrademate/cryptotrademate-backtesting-tool |

---

### 🟡 Hudie/crypto_algo_trading（可关注）

| 字段 | 值 |
|:-----|:----|
| 平台 | `Hudie/crypto_algo_trading`（GitHub） |
| 免费/付费 | 开源 |
| 星数 | 56★ |
| 语言 | Python |
| 推荐理由 | 量化框架专注加密市场，覆盖现货/永续合约/期货/期权（Deribit+BitMEX）。对ZQ的长期价值是**期权策略维度**——ZQ当前只有现货+合约永续，无期权维度 |
| 弥补缺口 | 期权策略（远期） |
| 集成难度 | 中等 |
| URL | https://github.com/Hudie/crypto_algo_trading |

---

### 🟡 51bitquant/howtrader（可关注）

| 字段 | 值 |
|:-----|:----|
| 平台 | `51bitquant/howtrader`（GitHub） |
| 免费/付费 | 开源 |
| 星数 | **917★** |
| 语言 | Python |
| 推荐理由 | 加密量化框架，支持策略开发/回测/实盘执行，**无缝集成TradingView信号**。中文社区活跃。TradingView信号的集成能力对ZQ价值最大——当前系统完全靠自己生成的评分信号，无外部信号源 |
| 弥补缺口 | 外部信号源集成 / TradingView信号 |
| 集成难度 | 简单（仅需接口封装） |
| URL | https://github.com/51bitquant/howtrader |

**集成方式（可选）：** 假如Commander决定引入TradingView信号作为辅助输入，howtrader的信号接收模块可以直接复用。

---

## 新策略发现

### 1. 预测市场交易策略（homerun）

**核心思路：** Polymarket/Kalshi预测市场的赔率反映了事件概率，当市场价格与真实概率偏差>阈值时交易。这与ZQ当前趋势追踪策略完全正交。

**对ZQ的价值：**
- 与现货市场低相关性 → 可做多样化
- 小资金($10-20)即可测试
- 有开源实现（homerun）可直接用
- 预测市场事件驱动，不依赖K线/技术指标

**适用场景：** ZQ主系统冻结期，可用闲置资金在Polymarket开小仓位做独立交易。

### 2. AI Agent驱动交易策略（QuantDinger参考）

**核心思路：** "Vibe trading"概念——AI Agent根据市场氛围和多个数据源做综合判断，而不是固定评分规则。

**对ZQ的价值：** ZQ当前的评分系统（min_enter_score/五因子）本质是固定规则加总。引入AI Agent综合判断维度，可补充规则系统无法捕获的"市场氛围"要素。

### 3. 跨所资金费率套利（Hummingbot/CCXT）

从搜索结果看，Hummingbot（18,674★）仍然是跨所套利的最成熟方案。ZQ的CCXT已装但零使用——激活CCXT后，Hummingbot的做市/套利策略可以参考。

**当前不推荐集成的原因：** ZQ资本~$297, USDT现金仅$73.44。做套利需要双份资金（多空各一），小资金难以执行。

### 4. 情绪驱动交易策略（CryptoSentAI）

**Github:** lordlethabo/CryptoSentAI (1★)
使用NLP情感分析 + LSTM预测 + 策略回测。价值点在于其NLP情感分析模块，可补充ZQ缺失的"新闻文本情绪"维度（上期CryptoInsight类似）。

**对ZQ的价值：** A1当前只有Alternative.me的F&G（数值型情绪），没有新闻文本层面的NLP分析。集成NLP情感后，NBZ选币可多一个维度。

---

## 新数据源发现

| 数据源 | 类型 | 免费/付费 | 填补缺口 | 集成难度 |
|:-------|:-----|:---------:|:---------|:--------:|
| **Polymarket API**（通过homerun） | 预测市场赔率/事件 | 免费 | **预测市场维度（全新）** | 中等 |
| **whalecli**（链上钱包追踪） | 鲸鱼/聪明钱 | 完全免费 | 链上聪明钱包（长期缺口） | 极简 |
| **onchain-analysis**（链上分析平台） | 链上数据/鲸鱼/聪明钱 | 完全免费 | 同上（但以分析平台为主） | 简单 |
| **TradingView Webhook**（通过howtrader） | 外部信号 | 免费 | 外部信号源（补充） | 简单 |

**数据源缺口持续状态（与05-18对比）：**

| 缺口维度 | 05-18状态 | 05-25状态 | 变化 |
|:---------|:---------:|:---------:|:----:|
| 聪明钱包/链上数据 | 缺 | **仍缺** | ❌ 未改变 |
| DEX实时价格 | 缺 | 仍缺 | 未改变 |
| 新闻文本NLP情绪 | 缺 | 仍缺 | 未改变 |
| 预测市场（新增识别） | 未识别 | 新发现 | 🆕 新维度 |

---

## 对比历史（2026-05-18 vs 2026-05-25）

### 上期（05-18）推荐了什么

| 推荐项 | 类型 | 本期状态 |
|:-------|:-----|:--------|
| **btc-hedge-lab** ⭐⭐ — BTC对冲策略 | 强烈推荐 | **未集成** — 仍无任何对冲机制 |
| **Arkham Intelligence Skill** ⭐⭐ — 链上智能钱 | 强烈推荐 | **未集成** — 聪明钱包缺口仍存在 |
| **funding-collector** ⭐ — 费率标准化 | 推荐参考 | **未集成** — 费率数据仍零散 |
| **awesome-crypto-trading-agents** ⭐ — 资源列表 | 推荐参考 | 已阅读，部分在本期使用 |
| mm-live — 做市引擎 | 🟡观察 | 保持观察 |
| Hermes Blockchain Oracle | 🟡观察 | 保持观察 |

### 上期P0任务执行情况

| P0任务（05-11报告提出） | 05-18状态 | 05-25状态 | 持续天数 |
|:-----------------------|:--------:|:--------:|:-------:|
| **CCXT集成（解决Binance 451）** | ❌ 未完成 | ❌ **仍未完成** | **14天** |
| **激活Etherscan Monitor** | ❌ 未完成 | ❌ **仍未完成** | **14天** |

**同一批P0任务已经持续三周未闭环。这个"推荐→集成"断裂区间从05-11的7个推荐全部未集成，扩大到05-18又新增4个推荐仍全部未集成。**

### 本期新增（05-25 vs 05-18）

| 新增项 | 对ZQ的价值 | 推荐级别 |
|:-------|:----------|:--------:|
| **QuantDinger** — 多Agent AI交易平台 | 填补回测+Agent参考维度 | ⭐⭐ |
| **homerun** — 预测市场交易平台 | 填补预测市场维度（全新） | ⭐⭐ |
| **whalecli** — 鲸鱼追踪CLI | 填补链上聪明钱包缺口 | ⭐ |
| **onchain-analysis** — 链上分析平台 | 同上 | ⭐ |
| howtrader — TradingView集成框架 | 外部信号源 | 🟡 |
| Crypto Algo Trading — 期权框架 | 期权策略远期储备 | 🟡 |
| CryptoSentAI — NLP情感模块 | 新闻文本情绪缺口 | 🟡 |

---

## 对ZQ系统的改进建议

### 🔴 P0 — 本周必须解决

**1. 激活CCXT + Etherscan Monitor（连续3周的P0，再不做就是态度问题）**

这是铁律一的直接违反——"日事日毕"。两个工具在05-11就被识别为P0，现在05-25仍然零调用。

| 工具 | 安装状态 | 调用次数 | 应该做的事 |
|:-----|:-------:|:--------:|:----------|
| CCXT 4.5.45 | ✅ 已安装 | **0次** | A4引擎用CCXT替代直接Binance REST API + 解决451问题 |
| Etherscan Monitor | ✅ 代码存在 | **0次** | 在A1数据官中import并周期性调用 |

- 05-11提出 → 14天过去 → 零进展
- 05-18再次强调 → 7天过去 → 零进展
- 需要Commander今天08:30直接分配：谁，什么时候，验证标准是什么

**2. 修复A3 findings.md管线断裂**

从auto_scan 05-24报告看，A3 findings.md文件缺失，NBZ findings 15天陈旧。这是当前系统"有框架无效果"的核心原因——A4只能依赖静默信号文件，无法获得文字推荐。

- **严重程度：** 没有A3推荐 → A4只能CHECK-HOLD → 系统冻结 → 日目标永远达不到
- **建议：** P0优先级，今天修复

**3. 总权益$296.68跌破$300气囊负值**

实时余额验证（2026-05-25 00:14 CST，来源：Binance API）：
- 总权益：**$296.68**
- USDT现金：**$73.44**
- 前5持仓：CATI($84.51), NEAR($50.67), FIDA($49.07), ZEC($24.58), DYM($6.30)

RL5气囊为负值（-$3.32），A4停新开仓。需要：
- 减仓CATI（过高的35.9%集中度）
- 释放至少$50-80现金
- 恢复RL5安全垫

### 🟠 P1 — 本周评估

**4. 评估QuantDinger的多Agent AI交易架构**

6,420★的项目不是随便来的。建议Commander花30分钟浏览其架构，评估是否有可复用的设计模式——特别是其AI Agent协同机制和回测实现。

**5. 评估homerun的Polymarket小仓位测试**

当前ZQ主系统冻结，$73.44 USDT中有$30-40闲置（减仓后可到$100+）。用$10-20在Polymarket开预测市场小仓位：
- 与现货零相关，真正的多样化
- 风险可控（$10-20）
- 如果成功，可成为系统冻结期的替代盈利源

**6. 安装whalecli并试运行**

这可能是本周最容易实现的"快速赢"——pip安装，一行命令启动试运行。不需要修改引擎，不需要复杂的集成。A1数据官可以直接调用其输出。

```bash
pip install whalecli
whalecli track --wallet-address <目标地址> --output jsonl
```

### 🟡 P2 — 持续跟踪

**7. 建立Scouter推荐追踪表**

当前Commander对Scouter的推荐无响应机制。建议在SHARED.md建立追踪表：

| 推荐日期 | 项目 | 推荐级别 | 状态 | 集成代码PR# |
|:--------:|:----|:-------:|:----|:----------:|
| 05-11 | CCXT激活 | ⭐⭐⭐ | ❌ 零使用 14天 | — |
| 05-11 | Etherscan Monitor | ⭐⭐⭐ | ❌ 零调用 14天 | — |
| 05-11 | hftbacktest回测 | ⭐ | ❌ 未评估 | — |
| 05-18 | btc-hedge-lab | ⭐⭐ | ❌ 未评估 | — |
| 05-18 | Arkham Intelligence | ⭐⭐ | ❌ 未评估 | — |
| 05-18 | funding-collector | ⭐ | ❌ 未评估 | — |
| 05-25 | QuantDinger | ⭐⭐ | 🆕 本期新增 | — |
| 05-25 | homerun | ⭐⭐ | 🆕 本期新增 | — |
| 05-25 | whalecli | ⭐ | 🆕 本期新增 | — |

**8. 68% coins未分类问题（other占比过高）**

这不是工具问题——选币库的赛道标签需要人工/规则更新。建议A2选币官本轮处理。

### 诚实判断：ZQ当前的根本问题

从Scouter的独立视角看，ZQ系统当前面临的不是工具缺乏问题，而是 **"有工具但不使用 + 有框架但管线断裂"** 的结构性问题：

1. **工具利用率极低** — CCXT和Etherscan Monitor两个已就绪工具零使用（14天）
2. **推荐闭环断裂** — 连续3周Scouter的推荐无一被集成（3期×共15+推荐项）
3. **A3管线断裂** — 最关键的数据流（A3→A4推荐）断裂，系统空转
4. **资金持续缩水** — $430本金 → $296.68（-31.0%），气囊负值
5. **日目标差距巨大** — 2%/天的目标几乎从未达成过

**本期的7个新发现中，即使全部推荐100%正确，不改变"发现→集成"断裂的现状，报告的价值就是零。** 这是Scouter最诚实的判断。

---

## 附录：已排除项（不写入推荐）

| 项目 | 排除原因 |
|:-----|:---------|
| scottgl9/cointraderv2 (6★) | 仅支持Coinbase Advanced，范围太窄 |
| PabloTBA/Chequita（2★） | LLM+RAG框架，代码质量一般，仅为研究项目 |
| Gyofy/ru_trading_newest（0★） | TSMOM策略实现，0星无社区验证 |
| thom899g/autonomous-cross-asset（0★） | 野心太大但0星，代码不可评估 |
| abc5051001/Crypto-Trading-bot（0★） | 2022年项目，已过时 |
| HuangAI-Com/HuangTrader（3★） | Freqtrade fork，无实质创新 |
| KeepALifeUS/ml-showcase（0★） | 仅展示项目，非可用工具 |
| SaintQuant/saintquant-crypto-trading-cli（0★） | 0星，无验证 |
| CybroZeus/Copy-Fail-Exploit（0★） | 漏洞利用工具，非交易相关 |
| ArmandBENETEAU/fiscal-crypt（3★） | 税务计算工具，非交易工具 |
| JudyaiLab/coinsifter（0★） | 8技术指标筛选工具但0星，未验证 |

---

*ZH侦察签名：2026-05-25 00:20 CST*
*下一期扫描：2026-06-01（周一）*
*报告文件：`learning/scouter_report_20260525.md`*
*实时余额来源：Binance API 2026-05-25 00:14 CST → $296.68*
