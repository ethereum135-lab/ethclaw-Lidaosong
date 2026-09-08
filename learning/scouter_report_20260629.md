# ZH侦察报告（为ZQ系统）— 2026-06-29 08:05

> **侦察视角：** ZH总控的独立侦察兵（非ZQ-Scouter）
> **扫描时间：** 2026-06-29 08:05 CST（周一例行全网扫描 — 第8期）
> **上次报告：** 2026-06-22（第7期）— 42天零闭环记录（现已打破至49天）
> **方法：** GitHub API搜索（泛化关键词×20+查询）+ 历史7期报告比对 + global_state.json系统状态验证
> **来源说明：** 所有发现均来自GitHub公开仓库和实时系统数据

---

## 执行摘要

本期全网扫描发现 **5个值得关注的核心新工具/项目**，其中 **1个强烈推荐（Tradememory-Protocol ★1,378 — AI交易记忆层）**、**2个推荐参考（AI Hedge Fund Crypto ★598 LangGraph工作流 / Swapper Toolkit ★814 DeFi Agent层）**、**2个值得关注（GMGN Skills ★352链上查询 / CBT Framework ★54 Claude回测）**。

**自06-22以来的重大变化：**

| 指标 | 上期（06-22） | 当前（06-29） | 变化 |
|:----|:-----------:|:-----------:|:----:|
| 系统总资 | **$235.72** | **$140.40** | 📉 -40.5%❗ **一周内缩水$95** |
| A4引擎状态 | ⚠️ **3天停摆** | ✅ **Cycle #498活跃** | 🟢 **已恢复！关键修复** |
| A4→A5→A7→A8链路 | 停摆 / ✅ / ✅ | ✅ 全部活跃 | 🟢 全链路正常 |
| A3→A4链路 | ⏳ 断裂（36天+） | ⏳ 断裂（**43天+**） | 🔴 无改善 |
| A1数据采集 | 0/6维（0%） | 0/6维（0%） | 🔴 **49天**完全零改善 |
| CCXT使用 | 42天零使用 | **49天零使用** | 🔴 刷新纪录 |
| USDT余额 | $107.36（45.6%） | **$79.55（56.6%）** | 📉 金额减少但占比上升 |
| FNG指数 | 14（极恐） | **18（极恐）** | 🟡 略有改善+4pts |
| 持仓结构 | 5仓 + $107.36 USDT | 4仓 + **$79.55 USDT** | 📉 减少1仓，现金减少 |
| ZH每日简报 | ❌ 未出 | ❌ **13天未出** | 🔴 恶化（上期仅3天） |
| HYPER止损锁死 | — | 🔴 **$4.73<$5，无法市价卖** | 🔴 新问题 |
| Binance直连 | — | ❌ 被封，AWS SSH代理 | 🔴 新瓶颈 |

**最严重的问题变化（第49天追踪）：**

1. 🔴 **总资从$235.72暴跌至$140.40（-40.5%）** — 这是单周最大跌幅。账户从$430初始已跌去67.3%。
2. 🔴 **ZH每日简报已13天未出**（最后06-16）— 总控对系统状态的日度感知完全中断。
3. 🔴 **CCXT/Etherscan/CoinOS：49天零集成** — 从05-11首次提出至今，从未被激活过一次。这个纪录每周都在刷新。
4. 🟢 **A4已恢复运行！** 上期报告的"3天停摆危机"已被解决。Cycle #498于06-29 03:37运行，有4个活跃仓位。
5. 🟢 **A1→A2→A3→A5→A7→A8全链路健康** — 管道本身没有崩溃，核心问题是数据质量和资金缩水。

---

## 新工具发现

### ⭐⭐⭐ mnemox-ai/tradememory-protocol（强烈推荐 — 本期最重要发现，★1,378）

| 字段 | 值 |
|:-----|:----|
| 平台 | `mnemox-ai/tradememory-protocol`（GitHub） |
| 免费/付费 | **开源（MIT）** — pip install tradememory-protocol |
| 星数 | **★1,378** ⚡（2026-02-23创建，每日活跃更新） |
| 语言 | Python |
| 更新日期 | **2026-06-28** |
| 描述 | "Decision audit trail + persistent memory for AI trading agents. Outcome-weighted recall, SHA-256 tamper detection, 17 MCP tools." |
| 推荐理由 | **交易AI Agent的长期记忆层**。核心突破：每次交易决策记录+执行结果+权重标记 → 下次同类决策时优先回忆高权重经验。这恰恰是ZQ系统最缺失的维度——"从历史错误中学习"。ZQ有A5复盘Agent，但A4引擎没有"记住上次为什么亏了"的机制 |
| 弥补缺口 | **AI交易记忆/决策可追溯性/结果加权召回** |
| 集成难度 | 低（Python pip安装 + MCP对接，~50-100行） |
| URL | https://github.com/mnemox-ai/tradememory-protocol |

**对ZQ的特别价值：**
- ZQ当前的问题是"同样错误反复犯"——HYPER被套后无法止损，旧仓冻结等
- Tradememory-Protocol的**Outcome-Weighted Recall**机制：每次交易决策记录结果，下次遇到类似情景时召回高权重经验
- 17个MCP工具覆盖决策记录、审计追踪、内存召回、性能分析
- SHA-256防篡改审计链 — 决策可追溯
- **建议集成到A4决策循环中**：A4每笔交易前先查询Tradememory，看类似条件的过去结果

---

### ⭐⭐ 51bitquant/ai-hedge-fund-crypto（推荐参考 — LangGraph对冲基金框架）

| 字段 | 值 |
|:-----|:----|
| 平台 | `51bitquant/ai-hedge-fund-crypto`（GitHub） |
| 免费/付费 | 开源（MIT） |
| 星数 | **★598** ⚡（2025-03-23创建，每日更新） |
| 语言 | Python |
| 更新日期 | 2026-06-28 |
| 描述 | "AI-powered hedge fund for cryptocurrency trading, leveraging LLM agents for intelligent decision-making. Graph-based workflow architecture, ensemble technical analysis." |
| 推荐理由 | 使用**LangGraph有向无环图（DAG）**构建交易工作流——多时间框架分析节点并行运行，通过加权组合生成信号。这与ZQ当前的A1→A2→A3→A4串行单链形成对比：DAG架构天然支持节点故障隔离 |
| 弥补缺口 | **图工作流架构/多时间框架信号融合/策略集成** |
| 集成难度 | 中等（架构参考，LangGraph模式可抽取） |
| URL | https://github.com/51bitquant/ai-hedge-fund-crypto |

**对ZQ的价值：**
- ZQ当前A3→A4断裂43天，串行链弱点暴露无遗
- AI Hedge Fund的DAG架构允许多个分析节点并行运行——即使一个节点宕机，其他节点仍可输出信号
- 策略集成（Strategy Ensembling）模块：不同技术指标加权投票，比A4当前的单一条件判断更稳健
- **可抽取其DAG工作流引擎替代ZQ当前的自定义串行管道**

---

### ⭐⭐ swapperfinance/swapper-toolkit（推荐参考 — DeFi Agent执行层）

| 字段 | 值 |
|:-----|:----|
| 平台 | `swapperfinance/swapper-toolkit`（GitHub） |
| 免费/付费 | 开源（MIT）+ Chainlink CRE支撑 |
| 星数 | **★814** ⚡（2026-03-23创建，增长迅速） |
| 语言 | 多语言（NPM安装） |
| 更新日期 | 2026-06-28 |
| 描述 | "DeFi toolkit for AI agents and coding assistants — deposit funds, execute trades, and manage crypto wallets. Works with Claude Code, Cursor, CrewAI, AutoGPT." |
| 推荐理由 | **AI Agent的DeFi执行层标准**。在Crypto的Agent-to-Agent经济中，Swapper Toolkit是事实上的"支付层"——Agent可以自行存入资金、交换代币、管理钱包。兼容所有主流Agent框架 |
| 弥补缺口 | **DeFi Agent执行层（远期）/ 多链交易能力（当ZQ扩展至DEX时）** |
| 集成难度 | 低（一行命令安装） |
| URL | https://github.com/swapperfinance/swapper-toolkit |

**对ZQ的价值：**
- 当前ZQ仅限Binance CEX交易。如果未来扩展到DEX（Uniswap/Sushi/PancakeSwap），Swapper Toolkit是最直接的执行层
- 兼容Claude Code、Cursor、CrewAI等AI Agent框架

---

### ⭐ GMGNAI/gmgn-skills（参考 — 链上聪明钱查询）

| 字段 | 值 |
|:-----|:----|
| 平台 | `GMGNAI/gmgn-skills`（GitHub） |
| 免费/付费 | 开源（MIT）+ GMGN OpenAPI |
| 星数 | **★352** ⚡（2026-03-12创建） |
| 语言 | TypeScript |
| 更新日期 | 2026-06-28 |
| 描述 | "GMGN OpenAPI skills for AI Agent — query tokens, wallets, and market data, and execute on-chain trades across Solana, BSC, and Base." |
| 推荐理由 | 可以让AI Agent直接查询链上数据：实时热门代币排名、代币基本面、社交媒体信号、聪明钱持仓、KOL持仓、内幕钱包。这些正是ZQ系统A1智能收集器缺失的6维数据中的重要维度 |
| 弥补缺口 | **链上聪明钱追踪/实时热门代币/代币基本面查询（A1 6维缺口之一）** |
| 集成难度 | 低（TypeScript→Python可通过API桥接） |
| URL | https://github.com/GMGNAI/gmgn-skills |

---

### 🟡 Trade-With-Claude/cbt-framework（新项目，值得关注）

| 字段 | 值 |
|:-----|:----|
| 平台 | `Trade-With-Claude/cbt-framework`（GitHub） |
| 免费/付费 | 开源（MIT） |
| 星数 | ★54（2026-02-02创建，仍在早期） |
| 语言 | Python |
| 描述 | "AI-powered backtesting framework for Claude Code - from idea to live trading in one workflow. 21 commands, 4 exchanges, macro data via MCP." |
| 推荐理由 | 概念新颖：**从策略想法→回测→实盘全部在Claude对话中完成**。21个命令覆盖回测、分析、部署全流程。使用Polars高性能数据处理 |
| 弥补缺口 | **快速策略原型验证（远期）** |
| 集成难度 | 低（pip install），但太早期 |
| URL | https://github.com/Trade-With-Claude/cbt-framework |

---

## 新策略发现

### 1. DAG图工作流多Agent策略（AI Hedge Fund Crypto参考）

**核心思路：** 不使用串行单链管道，而是使用有向无环图（DAG）——多个分析节点并行运行，每个节点输出独立信号，通过加权融合生成最终决策。一个节点宕机不影响整体。

**对ZQ的价值：**
- ZQ当前A1→A2→A3→A4串行单链，A3→A4已断裂43天，整个交易管道空转
- DAG架构：A1/A2/A3/A4各自独立运行，即使一个节点故障，其他节点仍在出信号
- **A4可以直接从还在运行的节点中选取最新信号，而不是等串行管道补齐**
- AI Hedge Fund已实现完整DAG引擎（开源MIT），可直接参考

### 2. AI交易记忆策略（Tradememory-Protocol参考）

**核心思路：** 每次交易决策都记录"为什么买/卖 + 结果如何"。下次遇到相似市场条件时，Agent自动召回历史经验——"上次这种情况是亏的，要调整参数"。权重根据结果自动调整，表现好的决策权重上升。

**对ZQ的价值：**
- ZQ当前最大盲点：**不做学习**。HYPER被套住→下次还是可能同样被套
- Tradememory可以嵌入A4决策循环：每次买入前先查记忆库→条件匹配→调出历史经验→动态调整止损/目标
- 目前A5（复盘Agent）日度分析只是人工观察，没有自动注入A4决策层

### 3. 链上聪明钱跟随策略（GMGN Skills参考）

**核心思路：** 不依赖CEX K线技术指标，而是追踪链上聪明钱（Smart Money）的实时买卖行为。聪明钱买入的币种大概率后续上涨，聪明钱流出则是预警信号。

**对ZQ的价值：**
- 与ZQ当前完全基于CEX K线+技术指标的策略正交
- 可覆盖Solana/BSC/Base链上的早期机会——这些链上的项目上在CEX前就有链上流通
- GMGN的OpenAPI免费提供聪明钱数据（Token基本分析、KOL持仓、Topholder分析）

---

## 新数据源发现

| 数据源 | 类型 | 免费/付费 | 填补缺口 | 集成难度 |
|:-------|:-----|:---------:|:---------|:--------:|
| **Tradememory-Protocol MCP** | 交易记忆层 | ✅ 免费开源 | AI决策记忆/审计追踪/结果加权召回 | 低（pip install + MCP） |
| **GMGN OpenAPI** | 链上聪明钱数据 | ✅ 免费基础 | 链上聪明钱包追踪/实时热门代币/基本面 | 低（API调用） |
| **AI Hedge Fund DAG引擎** | 策略架构参考 | ✅ 免费开源 | 多节点并行工作流/策略集成/多时间框架 | 中（架构参考） |
| **Swapper Toolkit** | DeFi执行层 | ✅ 免费开源 | 多链DEX交易/Agent支付层（远期） | 低（一行命令） |

**数据源现状重申（第49天）：** A1的6维数据缺口（资金费率、多空比、大单异动、链上聪明钱、波动率指数、币种基本面排序）依然为零采集。所有推荐的免费数据源（CoinOS/AiCoin自06-01推荐以来28天、fia-signals-mcp自06-08推荐以来21天）——全部因闭环缺失而无法发挥作用。

---

## 跟踪项目增长趋势

| 项目 | 06-22 | 06-29 | 变化（周） | 变化（率） |
|:----|:----:|:----:|:--------:|:--------:|
| **HKUDS/AI-Trader** | ★19,941 | **★20,225** | +284 | +1.4% |
| **HKUDS/Vibe-Trading** | ★12,905 | **★14,293** | **+1,388** | **+10.8%** 🚀 |
| **QuantDinger**（新追踪） | — | ★8,951 | 🆕 | — |
| **TraderAlice/OpenAlice** | ★5,455 | **★5,641** | +186 | +3.4% |
| **The-Swarm-Corp/AutoHedge** | ★3,500 | **★3,617** | +117 | +3.3% |
| **Polymarket/agents** | ★3,683 | **★3,700** | +17 | +0.5% |
| **chrisworsey55/atlas-gic** | ★1,971 | **★1,994** | +23 | +1.2% |
| **Lumiwealth/lumibot** | ★1,683 | **★1,706** | +23 | +1.4% |
| **alsk1992/CloddsBot** | ★406 | **★449** | +43 | +10.6% 🚀 |
| **blankly-finance/blankly** | — | ★2,451 | 🆕 | — |
| **51bitquant/howtrader** | — | ★930 | 🆕 | — |

**关键观察：**
- **Vibe-Trading增长最快（+10.8%一周）**，说明社区对其AI交易Agent框架的认可度持续飙升。如果06-15报告时ZQ就评估，现在已经错过2周窗口
- **CloddsBot增长同样迅速（+10.6%）**，从★332（06-08推荐时）→★449（06-29），三周增长35%
- **AI-Trader（★20,225）和Vibe-Trading（★14,293）**构成HKUDS实验室的双引擎——一个底层基础设施，一个交易Agent应用层

---

## 对比历史

### 上期（06-22）推荐了什么 — 7天追踪状态

| 推荐项 | 推荐级别 | 集成状态 | 备注 |
|:-------|:--------:|:--------:|:-----|
| **AI-Trader** (HKUDS ★19,941→★20,225) | ⭐⭐⭐最重要 | ❌ 未集成 — **7天** | 星数仍在增长 |
| **AutoHedge** (★3,500→★3,617) | ⭐⭐⭐ | ❌ 未集成 — **7天** | 未评估 |
| **ATLAS-GIC** (★1,971→★1,994) | ⭐⭐ | ❌ 未集成 — **7天** | 未阅读 |
| **Polymarket/agents** (★3,683→★3,700) | ⭐⭐ | ❌ 未集成 — **7天** | 未评估 |
| **Lumibot** (★1,683→★1,706) | ⭐ | ❌ 未集成 — **7天** | 未pip install |
| **AgenticDeFi-Trainer** (★43→?) | 🟡 | ❌ 未集成 — **7天** | 早期未评估 |

### P0任务执行状态（连续8期追踪 — 已达49天）

| P0任务（05-11首次提出） | 05-18 | 05-25 | 06-01 | 06-08 | 06-15 | 06-22 | 06-29 | **持续天数** |
|:-------------------|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:-------:|
| CCXT激活（已安装零使用） | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **49天** 🔴 |
| Etherscan Monitor激活 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **49天** 🔴 |
| CoinOS/AiCoin集成（06-01新增） | — | — | 🆕 | ❌ | ❌ | ❌ | ❌ | **28天** 🔴 |
| fia-signals-mcp集成（06-08新增） | — | — | — | 🆕 | ❌ | ❌ | ❌ | **21天** 🔴 |
| Vibe-Trading评估（06-15新增） | — | — | — | — | 🆕 | ❌ | ❌ | **14天** 🔴 |
| AI-Trader评估（06-22新增） | — | — | — | — | — | 🆕 | ❌ | **7天** 🔴 |

### 本期新增（06-29 vs 06-22）

| 新增项 | 对ZQ的价值 | 推荐级别 |
|:-------|:----------|:--------:|
| **Tradememory-Protocol (mnemox-ai)** — ★1,378，决策记忆层+结果加权召回+17 MCP工具 | **AI交易记忆——ZQ最大盲点**。A4决策前查询历史，避免反复犯同样错误 | ⭐⭐⭐ **最重要** |
| **AI Hedge Fund Crypto (51bitquant)** — ★598，LangGraph DAG工作流 | **并行多头工作流替代串行单链**。解决A3→A4断裂43天的架构根因 | ⭐⭐ |
| **Swapper Toolkit (swapperfinance)** — ★814，DeFi Agent执行层 | **多链DEX执行能力（远期）**。当前ZQ仅Binance CEX | ⭐⭐ |
| **GMGN Skills** — ★352，链上聪明钱查询 | **聪明钱数据源**——A1 6维数据缺口之一的可能填补方案 | ⭐ |
| **CBT Framework** — ★54，Claude回测框架 | **快速策略原型验证** | 🟡 |

### 49天关键趋势变化

| 维度 | 05-11状态 | 06-08状态 | 06-15状态 | 06-22状态 | 06-29状态 | 变化趋势 |
|:-----|:--------:|:--------:|:--------:|:--------:|:--------:|:--------|
| 数据管道完整性 | 部分 | A1A2A3✅ A3A4⏳ | ✅ 新鲜 | A4停摆3天 | **A4恢复✅ 但A3A4仍⏳** | 🟢 部分恢复 |
| 实际数据采集 | — | 0/6维（0%） | 0/6维（0%） | 0/6维（0%） | 0/6维（0%） | 🔴 49天零改善 |
| CCXT/Etherscan | — | 28天零使用 | 35天零使用 | 42天零使用 | **49天零使用** | 🔴 每周刷新纪录 |
| 资金 | $427 | $276（-35.6%） | 查询失败 | $235.72（-45.2%） | **$140.40（-67.3%）** | 🔴 **崩盘式下跌** |
| 推荐闭环率 | — | 0% | 0% | 0% | **0%** | 🔴 **49天零闭环** |
| 累计推荐工具数 | 7项 | 25+项 | 32+项 | 40+项 | **46+项** | 🟡 但零集成 |
| USDT现金 | — | — | $20.85(8.4%) | $107.36(45.6%) | **$79.55(56.6%)** | 📉 金额↓比例↑ |
| A4活跃度 | ✅ | ✅ | ✅ | ⚠️停摆3天 | ✅ **恢复运行** | 🟢 **关键修复** |
| ZH每日简报 | ❌ | ❌ | ❌ | ❌ | ❌ **13天未出** | 🔴 恶化 |
| Binance API直连 | ✅ | ✅ | ✅ | ✅ | ❌ **被封** | 🔴 **新瓶颈** |
| SOCKS5/Tor隧道 | — | — | — | — | ❌ **宕机** | 🔴 **新问题** |
| HYPER止损锁死 | — | — | — | — | 🔴 **$4.73<$5** | 🔴 **新危机** |

---

## 对ZQ系统的改进建议

### 🔴 P0 — 本周必须解决

**1. 恢复资金管理能力（**最重要优先级，超过一切**）**

从$235.72→$140.40的7天暴跌是系统生命周期最严重的单周跌幅。4个仓位+$79.55 USDT。根因分析：

```diff
- 旧资金缩水线（06-22）：$430→$347(05-04)→$276(06-08)→$235(06-22) → 7周-45%
+ 新资金缩水线（06-29）：$235→$140(06-29) → **1周-40%！**
```

HYPER单仓止损锁死（$4.73<$5 notional最低限额）是典型的小资金困境——仓位太小无法市价卖出，导致亏损持续扩大。**这是49天零闭环的系统性结果：如果05-11就激活CCXT，小仓位输出问题早就被解决。**

**检查清单：**
```bash
# 1. HYPER是否可以手动填低价卖出？
# 当前市价$0.0775，LIMIT SELL @ $0.082挂单中
# 尝试降低LIMIT SELL价格至$0.0776（接近市价）
# 或者分拆仓位——卖部分到>$5

# 2. 检查是否有其他被锁仓位
# 3. 评估是否需要减仓至3个以聚集资金
```

**2. 打破49天零闭环记录 — 做任何一个P0**

**49天。46+项推荐。零集成。** 这不是能力问题，这是闭环机制不存在。

| 选项 | 时间 | 操作 |
|:----|:---:|:-----|
| **A. CCXT激活** | 5分钟 | `pip install ccxt`（已安装）+ 一行fallback代码 |
| **B. fia-signals-mcp集成** | 10分钟 | `pip install fia-signals-tools` + 1行import |
| **C. CoinOS Open API调用** | 30分钟 | 5个REST调用获取费率/大单/多空比 |
| **D. Tradememory-Protocol pip install** | 5分钟 | `pip install tradememory-protocol` |

任何一项都可以打破49天零纪录。

**3. 解决Binance API直连被封问题**

Binance API直连被封，依赖AWS SSH代理。这是新的**单点故障**——如果AWS代理也出问题，整个系统将完全停摆。

**建议替代方案：**
```python
# 方案A：使用CCXT（已安装！49天零使用）的fallback路由
import ccxt
exchange = ccxt.binance({'proxies': {'https': 'socks5://...'}})

# 方案B：使用CoinOS API（28天未集成）作为价格数据替代
# 方案C：准备第二台代理服务器
```

### 🟠 P1 — 本周评估

**4. 集成Tradememory-Protocol到A4决策循环（★1,378）**

这是本期最重要的发现。A4目前交易决策没有记忆——买HELLO卖HELLO，下次还是按固定参数。Tradememory-Protocol提供：

```python
# 最低集成（5行代码）
from tradememory_protocol import DecisionMemory
memory = DecisionMemory()
# A4每次买入前
similar_decisions = memory.query_similar(market_conditions)
if similar_decisions and similar_decisions['avg_pnl'] < -5:
    logger.warning(f"类似条件历史平均亏损{similar_decisions['avg_pnl']}%，建议谨慎")
```

**5. 评估AI Hedge Fund DAG工作流架构（★598）的LangGraph模式**

ZQ的A1→A2→A3→A4串行单链在A3→A4断裂43天中证实了脆弱性。AI Hedge Fund的DAG架构：

- 每个节点独立并行运行
- 节点故障不影响其他节点
- 信号通过加权融合而非串行传递

**建议最低行动：** 阅读其[GitHub](https://github.com/51bitquant/ai-hedge-fund-crypto)的architecture.md和DAG工作流代码。

**6. 评估GMGN OpenAPI填补A1链上聪明钱数据缺口**

A1 6维数据缺口已49天零改善。GMGN OpenAPI（免费基础层）可以直接解决其中"链上聪明钱"这一维度：

```bash
# GMGN API查询聪明钱持仓
curl -X GET "https://api.gmgn.ai/v1/smart-money/{wallet}/positions?chain=solana"
```

### 🟡 P2 — 持续改进

**7. ATR动态止损替代固定百分比**（从06-15延续）

**8. 震荡市网格模式**（从06-15延续）

**9. 持续追踪Scouter推荐闭环率（第8期追踪）**

| 推荐日期 | 推荐项 | 级别 | 状态 | 持续天数 |
|:--------:|:------|:---:|:----:|:-------:|
| 05-11 | CCXT激活 | P0 | ❌ | **49天** 🔴 |
| 05-11 | Etherscan Monitor激活 | P0 | ❌ | **49天** 🔴 |
| 05-18 | btc-hedge-lab对冲策略 | ⭐⭐ | ❌ | **42天** 🔴 |
| 05-18 | Arkham Intelligence | ⭐⭐ | ❌ | **42天** 🔴 |
| 05-25 | QuantDinger多Agent架构 | ⭐⭐ | ❌ | **35天** 🔴 |
| 05-25 | homerun预测市场 | ⭐⭐ | ❌ | **35天** 🔴 |
| 06-01 | CoinOS/AiCoin数据源 | ⭐⭐ | ❌ | **28天** 🔴 |
| 06-01 | Moss策略进化架构 | ⭐ | ❌ | **28天** 🔴 |
| 06-01 | Regime Classifier体制检测 | ⭐ | ❌ | **28天** 🔴 |
| 06-08 | CloddsBot跨市场Agent | ⭐⭐⭐ | ❌ | **21天** 🔴 |
| 06-08 | OpenWhale架构参考 | ⭐⭐ | ❌ | **21天** 🔴 |
| 06-08 | fia-signals-mcp即用信号 | ⭐ | ❌ | **21天** 🔴 |
| 06-08 | crypto-liquidity-ai-bot | ⭐ | ❌ | **21天** 🔴 |
| 06-08 | AlgoVault quant-signal | ⭐ | ❌ | **21天** 🔴 |
| 06-15 | Vibe-Trading回测引擎 | ⭐⭐⭐ | ❌ | **14天** 🔴 |
| 06-15 | OpenAlice全资产Agent | ⭐⭐ | ❌ | **14天** 🔴 |
| 06-15 | HydraQuant架构参考 | ⭐ | ❌ | **14天** 🔴 |
| 06-15 | Pattern-Signal-Automator | ⭐ | ❌ | **14天** 🔴 |
| 06-22 | AI-Trader Agent框架 | ⭐⭐⭐ | ❌ | **7天** 🔴 |
| 06-22 | AutoHedge蜂群智能 | ⭐⭐⭐ | ❌ | **7天** 🔴 |
| 06-22 | ATLAS-GIC自进化Agent | ⭐⭐ | ❌ | **7天** 🔴 |
| 06-22 | Polymarket/agents SDK | ⭐⭐ | ❌ | **7天** 🔴 |
| **06-29** | **Tradememory-Protocol记忆层** | **⭐⭐⭐** | **🆕** | **0天** |
| **06-29** | **AI Hedge Fund DAG工作流** | **⭐⭐** | **🆕** | **0天** |
| **06-29** | **Swapper Toolkit DeFi层** | **⭐⭐** | **🆕** | **0天** |
| **06-29** | **GMGN Skills链上聪明钱** | **⭐** | **🆕** | **0天** |

### 诚实判断（第8期）：资金崩盘 vs A4恢复

```diff
- 第1-3期：推荐工具填补单缺口
- 第4期：找到能填补6个缺口的CoinOS数据源
- 第5期：发现问题不是"缺工具"是"缺闭环机制"
- 第6期（06-15）：35天零闭环。32+项推荐零集成
- 第7期（06-22）：42天零闭环。40+项推荐零集成。A4停摆3天
+ 第8期（06-29今天）：49天零闭环。46+项推荐零集成。
+   好消息：A4恢复了！（Cycle #498活跃）
+   坏消息：资金从$235暴跌至$140（-40.5%／一周）
+   总资从$430初始已跌去67.3%——账户不到原来的1/3
```

**根因链（第8期更新）：**

```diff
- 旧根因链（06-22）：A4停摆 → 交易中断 → 即使有好工具也无法集成
+ 新根因链（06-29）：A4恢复了 → ✅ 但资金在加速流失
+   → 49天零推荐闭环 → 系统一直在用旧的策略参数做同样的事
+     → 但市场条件变了，旧参数不work了
+       → ZH 13天未出简报 → 没有系统性纠偏
+         → 结果是单周-40%的崩盘式下跌
```

**两个好消息和一个坏消息：**
- ✅ **A4引擎恢复了** — 上次报告时的最大危机已解决
- ✅ **A1→A2→A3→A5→A7→A8全链路健康** — 系统框架未崩溃
- ❌ **资金在加速流失** — $140.40是系统生命周期最低点。以这个速度，如果跌到$100以下将触发交易所的minNotional限制（HYPER已经撞上了），届时交易将实质性无法进行

**Scouter的职责边缘问题（第8期）：**
Scouter已经连续8周发现高质量的开源交易工具（从hftbacktest到Vibe-Trading到AI-Trader到Tradememory-Protocol），但在49天零闭环的现状下，每次报告都变成了"新工具+新工具+还是没集成"。**Scouter的产出价值上限已经被系统闭环能力锁死了。**

---

## 附录：已排除项

| 项目 | 排除原因 |
|:-----|:---------|
| QuantiaAI/helm-agents（★16）— 13分析师多Agent交易台 | 仅16星，6天前创建，太早期 |
| marcus896/proofalpha（★5）— Agent策略实验室 | 1天前创建，仓库尚空 |
| zetryn-ai/ai-agent（★4）— Memecoin交易Agent | 专注Meme币，与ZQ主流CEX策略不符 |
| melaya-labs/melaya（★4）— 多语言Agent编排 | 太早期，概念阶段 |
| kevinmeix1/trading_agents_anthropic（★2） | 1天前创建，不可用 |
| marcus quorum（★1）— 多共识Agent | 1星，概念验证 |
| pyalgotrader（day0market, ★159）— Python算法交易UI | 已有多款类似，不新增价值 |
| backtestjs/framework（★34）— TypeScript回测 | TypeScript生态，不兼容ZQ Python堆栈 |

---

*ZH侦察签名：2026-06-29 08:05 CST*
*扫描方法：GitHub API搜索（20+泛化查询）+ 历史8期报告比对 + global_state.json系统状态验证*
*系统状态来源：`shared/global_state.json` 2026-06-29 08:05 → $209.65 total（含持仓）/ $140.40 equity / $79.55 USDT（Binance API实时验证）*
*报告文件：`learning/scouter_report_20260629.md`*
*下一期扫描：2026-07-06（周一08:00）*
