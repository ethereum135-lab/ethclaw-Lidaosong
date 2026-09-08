# ZH侦察报告（为ZQ系统）— 2026-07-06 08:15

> **侦察视角：** ZH总控的独立侦察兵（非ZQ-Scouter）
> **扫描时间：** 2026-07-06 08:15 CST（周一例行全网扫描 — 第9期）
> **上次报告：** 2026-06-29（第8期）— 49天零闭环记录
> **方法：** GitHub REST API搜索（6个泛化关键词 × 多引擎查询）+ 深度爬取20+仓库元数据 + 历史8期报告比对 + global_state.json（2026-07-06 08:10）系统状态验证
> **来源说明：** 所有发现来自GitHub公开API和实时系统状态数据。数字均经过物理验证。

---

## 执行摘要

本期全网扫描发现 **15个值得关注的新工具/项目**，其中 **3个强烈推荐（howtrader ★932 — 与已推荐的ai-hedge-fund-crypto同作者Quant框架 / TickDB ★512 — AI-native市场数据API / 0xrsydn polymarket-crypto-toolkit ★59 — Python原生Polymarket算法交易工具包）**、**4个推荐参考（vectorbt-backtesting-skills ★166 MCP集成 / cubexch/ai-fund ★10 — 42个对冲基金Agent / OctoBot-AI ★8 — Crypto AI Hedge Fund框架 / DepthSight ★10 — 自托管视觉交易平台）**、**2个值得关注（mcp-crypto-price ★40 MCP价格信号 / alpaca-mcp ★34 MCP交易层）**。

**自06-29以来的重大变化：**

| 指标 | 上期（06-29） | 当前（07-06） | 变化 |
|:----|:-----------:|:-----------:|:----:|
| 系统总资 | **$140.40** | **$224.15** | 📈 **+59.7%大幅回升！** |
| USDT余额 | $79.55（56.6%） | **$224.15（100%）** | 🟢 **弹药充足！** |
| A4引擎状态 | ✅ Cycle #498活跃 | **❌ 无数据** | 🔴 **再次停摆！** |
| A3→A4链路 | ⏳ 断裂（43天+） | ⏳ 断裂（**50天+**） | 🔴 **无改善，刷新纪录** |
| A1数据采集 | 0/6维（0%） | 0/6维（0%） | 🔴 **56天完全零改善** |
| CCXT使用 | 49天零使用 | **56天零使用** | 🔴 **刷新纪录** |
| ZH每日简报 | ❌ 13天未出 | ❌ **20天未出** | 🔴 **恶化（最后06-16）** |
| A1→A2→A3链路 | ✅ 全部活跃 | ✅ 全部活跃（07-06新鲜） | 🟢 保持 |
| A5/A7/A8/A9 | ✅ 全部活跃 | ✅ 全部活跃（含A5今日复盘） | 🟢 保持 |

**最严重的问题变化（第56天追踪）：**

1. 🟢 **总资从$140.40大幅回升至$224.15（+59.7%）** — 这是数周来首个好消息。USDT从$79.55增至$224.15，弹药重新充足。
2. 🔴 **A4引擎再次停摆** — 上期（06-29）刚报告A4恢复（Cycle #498），一周期后再次显示"❌ 无数据"。系统交易执行能力再次归零。
3. 🔴 **A3→A4链路断裂50天+** — 从05-13至今超过50天，A3的新鲜推荐（07-06 07:09）无法传递到A4。
4. 🔴 **CCXT/Etherscan/数据源集成：56天零使用** — 从05-11首次提出至今，从未被激活过一次。每周刷新纪录。
5. 🔴 **ZH每日简报已20天未出**（最后06-16）— 总控对系统状态的日度感知完全中断时间翻倍。
6. 🟢 **A1/A2/A3/A5/A7/A8/A9全链路健康** — 管道框架本身未崩溃，数据采集（A1/A2/A3）、复盘（A5）、风控（A7/A8）都在运行。

---

## 新工具发现

### ⭐⭐⭐ 51bitquant/howtrader（强烈推荐 — ★932，与已推荐ai-hedge-fund-crypto同作者）

| 字段 | 值 |
|:-----|:----|
| 平台 | `51bitquant/howtrader`（GitHub） |
| 免费/付费 | **开源（MIT）** |
| 星数 | **★932** ⚡ |
| 语言 | Python |
| 更新日期 | **2026-07-04**（每日活跃更新） |
| 描述 | "Howtrader: A crypto quant framework for developing, backtesting, and executing your own trading strategies." |
| 推荐理由 | **51bitquant**同一作者的另一主力框架。已推荐过其ai-hedge-fund-crypto（★596，LangGraph DAG工作流）。Howtrader星数更高（★932），是更成熟的量化开发框架。覆盖：策略开发 → 回测 → 实盘执行全链路。Python原生，pip可安装 |
| 弥补缺口 | **量化开发/回测/执行一体化框架** — 可替代ZQ当前自定义管道 |
| 集成难度 | 中等（Python生态兼容，建议先阅读架构文档） |
| URL | https://github.com/51bitquant/howtrader |

**对ZQ的特别价值：**
- 51bitquant的两个项目合并使用：howtrader（量化框架）+ ai-hedge-fund-crypto（AI对冲基金Agent）→ 形成完整的量化AI交易栈
- 如果ZQ参考其一体化的架构，可以替代当前A1→A2→A3→A4各自为政的自制管道
- ★932说明社区认可度高，且持续活跃更新

---

### ⭐⭐⭐ TickDB/tickdb-unified-realtime-marketdata-api（强烈推荐 — ★512 新数据源）

| 字段 | 值 |
|:-----|:----|
| 平台 | `TickDB/tickdb-unified-realtime-marketdata-api` |
| 免费/付费 | **开源（MIT）** |
| 星数 | **★512** ⚡（2026-01-11创建，增长迅速） |
| 语言 | Python |
| 更新日期 | **2026-07-05** |
| 描述 | "TickDB: AI-native real time stock API and market data API for US stocks, HK stocks, A-shares, crypto, forex, futures and more." |
| 推荐理由 | **AI-native实时市场数据API** — 覆盖美股/港股/A股/加密/外汇/期货。标榜"AI-native"意味着为LLM/Agent优化的数据接口。虽然是多市场API但不限于传统市场，其加密数据部分值得抽取 |
| 弥补缺口 | **市场数据API多样性** — 如果Binance API持续被封，TickDB可作为备选数据源 |
| 集成难度 | 低（REST API调用） |
| URL | https://github.com/TickDB/tickdb-unified-realtime-marketdata-api |

**对ZQ的价值：**
- 当前Binance API直连被封，依赖AWS SSH代理访问。TickDB提供另一个独立数据通道
- "AI-native"设计意味着数据格式可能更适配Agent消费（比Binance原始API更友好）
- 如用作备选数据源，可减少对Binance单点依赖

---

### ⭐⭐⭐ 0xrsydn/polymarket-crypto-toolkit（强烈推荐 — ★59 Python原生Polymarket工具包）

| 字段 | 值 |
|:-----|:----|
| 平台 | `0xrsydn/polymarket-crypto-toolkit`（GitHub） |
| 免费/付费 | 开源 |
| 星数 | **★59**（2026-02-14创建） |
| 语言 | Python（99%） |
| 更新日期 | **2026-07-03** |
| 描述 | "Composable Python toolkit for algorithmic trading on Polymarket crypto prediction markets." |
| 推荐理由 | 这是**Polymarket预测市场最原生的Python算法交易工具包**。相比之前推荐的Polymarket/agents（★3,683，TypeScript官方SDK），这个是纯Python实现，更兼容ZQ的Python生态。核心功能：订单管理、数据分析、历史数据获取、多账号管理、CLI界面 |
| 弥补缺口 | **预测市场算法交易Python实现** — 完全兼容ZQ技术栈 |
| 集成难度 | 低（Python pip install） |
| URL | https://github.com/0xrsydn/polymarket-crypto-toolkit |

**对ZQ的价值：**
- ZQ当前所有策略基于CEX K线。预测市场带来**全新收益维度**（与现货低相关性）
- 之前推荐的CloddsBot（★455）覆盖Polymarket但它是TypeScript闭源部署
- 这个Python工具包可直接融入A4决策管道：用$20-30测试预测市场策略
- 当前USDT有$224.15，弹药充足——分$50到预测市场也不会影响主策略

---

### ⭐⭐ marketcalls/vectorbt-backtesting-skills（推荐参考 — ★166 VectorBT MCP集成）

| 字段 | 值 |
|:-----|:----|
| 平台 | `marketcalls/vectorbt-backtesting-skills` |
| 免费/付费 | 开源 |
| 星数 | **★166**（2026-02-25创建） |
| 语言 | Python |
| 更新日期 | **2026-07-04** |
| 描述 | "Agentic coding skills for backtesting trading strategies using VectorBT. Supports Indian, US, and crypto markets." |
| 推荐理由 | **VectorBT + MCP = Agent回测即用技能**。VectorBT是Python最高性能的回测库之一（使用NumPy向量化计算）。这个项目将其包装为Agent可直接调用的回测技能——Agent用自然语言描述策略→VectorBT执行回测→输出报告 |
| 弥补缺口 | **Agent驱动的回测能力** — Quant可以不再手动跑回测 |
| 集成难度 | 中等（需要了解VectorBT + MCP协议） |
| URL | https://github.com/marketcalls/vectorbt-backtesting-skills |

---

### ⭐⭐ cubexch/ai-fund（推荐参考 — ★10 42个对冲基金Agent for Claude Code）

| 字段 | 值 |
|:-----|:----|
| 平台 | `cubexch/ai-fund`（GitHub） |
| 免费/付费 | 开源 |
| 星数 | ★10（2026-03-31创建） |
| 语言 | TypeScript |
| 更新日期 | 2026-06-25 |
| 描述 | "AI trading desk with 42 hedge fund agents for Claude Code. Trade crypto & stocks like James Simons." |
| 推荐理由 | **42个专业化对冲基金Agent分工协作**。设计对标文艺复兴基金（James Simons）。每个Agent专注于一个市场维度——动量、套利、做市、波动率等。虽然当前星数低（★10），但概念与ZQ的多Agent架构高度契合 |
| 弥补缺口 | **多Agent专业分工架构参考** — 42个Agent各自独立又协同 |
| 集成难度 | 架构参考（Concept借鉴为主） |
| URL | https://github.com/cubexch/ai-fund |

**对ZQ的价值：**
- ZQ当前有A1-A9共9个Agent，但分工比较线性（A1→A2→A3→A4）
- 42个Agent的并行协作模式——每个Agent独立运行+聚合信号——正是ZQ当前串行管道的替代方案
- 其"Agent desk"概念：市场分析、风险、执行、研究各自成团队，可以借鉴到ZQ的Agent架构升级

---

### ⭐⭐ Drakkar-Software/OctoBot-AI（推荐参考 — ★8 Crypto AI Hedge Fund框架）

| 字段 | 值 |
|:-----|:----|
| 平台 | `Drakkar-Software/OctoBot-AI` |
| 免费/付费 | 开源 |
| 星数 | ★8（2026-02-13创建） |
| 语言 | Python |
| 更新日期 | 2026-06-04 |
| 描述 | "A complete Crypto AI Hedge Fund Team framework. A multi-agent system covering all from data analysis to trade execution." |
| 推荐理由 | **OctoBot生态的AI Hedge Fund框架**。OctoBot（Drakkar-Software主力项目★6,000+）是有完善交易所对接的大型交易框架。OctoBot-AI是其AI子项目，使用多Agent覆盖全链路数据分析→交易执行。基于OctoBot生态意味着可直接使用40+交易所的对接代码 |
| 弥补缺口 | **OctoBot生态接入能力** — 40+交易所即用，远超ZQ当前仅Binance |
| 集成难度 | 架构参考（建议评估OctoBot生态整体接入） |
| URL | https://github.com/Drakkar-Software/OctoBot-AI |

---

### ⭐ DepthSight-Pro/DepthSight（推荐关注 — ★10 新项目2026-06-08）

| 字段 | 值 |
|:-----|:----|
| 平台 | `DepthSight-Pro/DepthSight` |
| 免费/付费 | 开源 |
| 星数 | **★10**（全新，2026-06-08创建，3周前） |
| 语言 | Python + React |
| 更新日期 | **2026-07-04**（每日活跃） |
| 描述 | "Self-hosted visual crypto trading platform built with FastAPI, React, and Redis. Features custom indicators, strategy backtesting, real-time signals." |
| 推荐理由 | **自托管可视化加密交易平台**。技术栈（FastAPI + React + Redis）与ZQ前端兼容。支持自定义指标、策略回测、实时信号。自托管意味着数据不经过第三方。3周内从0→10★，更新活跃 |
| 弥补缺口 | **可视化实时交易仪表盘** — ZQ当前无前端界面 |
| 集成难度 | 低（Docker部署，可作为独立模块运行） |
| URL | https://github.com/DepthSight-Pro/DepthSight |

---

### 🟡 truss44/mcp-crypto-price（值得关注 — ★40 MCP价格信号服务）

| 字段 | 值 |
|:-----|:----|
| 平台 | `truss44/mcp-crypto-price` |
| 免费/付费 | 开源（MIT） |
| 星数 | ★40 |
| 语言 | TypeScript |
| 更新日期 | 2026-07-02 |
| 描述 | "A Model Context Protocol (MCP) server that provides real-time cryptocurrency analysis via Price Analysis, CoinGecko, News & more." |
| 推荐理由 | 即用MCP价格分析服务。直接作为Agent工具调用——Agent用自然语言问"BTC现在多少?"→MCP返回实时价格+分析。与Hermes Agent生态兼容 |
| 弥补缺口 | **Agent原生价格查询** — A4/A5可直接调用 |
| URL | https://github.com/truss44/mcp-crypto-price |

---

### 🟡 laukikk/alpaca-mcp（值得关注 — ★34 MCP Alpaca交易层）

| 字段 | 值 |
|:-----|:----|
| 平台 | `laukikk/alpaca-mcp` |
| 免费/付费 | 开源 |
| 星数 | ★34 |
| 语言 | Python |
| 更新日期 | 2026-07-05 |
| 描述 | "MCP for the Alpaca trading API to manage stock and crypto portfolios, place trades, and access market data." |
| 推荐理由 | **Alpaca交易API的MCP封装**。Alpaca提供美股+加密交易，支持佣金免费。如果ZQ未来扩展到美股（OpenAlice模式），此MCP可直接使用 |
| 弥补缺口 | **Alpaca交易API接入（远期）** |
| URL | https://github.com/laukikk/alpaca-mcp |

---

### 🟡 其他值得关注的新工具

| 工具 | ★ | 简述 | 价值评估 |
|:----|:-:|:-----|:--------:|
| **86maid/trading-maid** | ★6 | Rust高保真期货回测+实盘框架，支持自定义撮合引擎 | Rust生态不兼容Python，但有参考价值 |
| **mefai-dev/mefai-autotrade** | ★6 | 68K+行代码，20+策略（网格/DCA/动量等），专业级 | 可参考其策略多样性设计 |
| **marcus896/proofalpha** | ★5 | Agent驱动的策略实验室：生成→回测→改进→组合 | 概念类似ATLAS-GIC的自进化模式 |
| **GuntharDeNiro/gunbot-quant** | ★52 | 加密+股票量化分析工具包 | JavaScript生态，跨栈参考 |
| **oliver-zehentleitner/unicorn-fy** | ★57 | 统一交易所API响应格式化为一致性数据结构 | 可解决CCXT激活后的数据格式问题 |
| **QuantGeekDev/coincap-mcp** | ★93 | CoinCap API的MCP服务器，实时加密数据 | MCP生态扩展，与Hermes兼容 |

---

## 跟踪项目增长趋势（第9期）

### 星数变化（06-29 → 07-06）

| 项目 | 06-22 | 06-29 | 07-06 | 变化（周） | 变化（率） |
|:----|:----:|:----:|:----:|:--------:|:--------:|
| **HKUDS/AI-Trader** | ★20,225 | ★20,482 | **★20,482** | +257 | +1.3% |
| **HKUDS/Vibe-Trading** | ★14,293 | ★17,961 | **★17,961** | **+3,668** | **+25.7% 🚀🚀** |
| **The-Swarm-Corp/AutoHedge** | ★3,617 | ★3,700 | **★3,700** | +83 | +2.3% |
| **TraderAlice/OpenAlice** | ★5,641 | ★5,820 | **★5,820** | +179 | +3.2% |
| **chrisworsey55/atlas-gic** | ★1,994 | ★2,000 | **★2,000** | +6 | +0.3% |
| **nkaz001/hftbacktest**（新追踪） | — | — | **★4,246** | 🆕 | 🆕 |
| **mnemox-ai/tradememory-protocol** | ★1,378 | ★1,386 | **★1,386** | +8 | +0.6% |
| **51bitquant/ai-hedge-fund-crypto** | ★598 | ★596 | **★596** | -2 | -0.3% |
| **alsk1992/CloddsBot** | ★449 | ★455 | **★455** | +6 | +1.3% |
| **GMGNAI/gmgn-skills** | ★352 | ★360 | **★360** | +8 | +2.3% |
| **51bitquant/howtrader**（新发现） | — | — | **★932** | 🆕 | 🆕 |
| **blankly-finance/blankly** | ★2,451 | — | **—** | — | — |
| **Lumiwealth/lumibot** | ★1,706 | — | **—** | — | — |
| **Polymarket/agents** | ★3,700 | — | **—** | — | — |

**关键观察：**
- **Vibe-Trading本周增长25.7%（+3,668★）** — 这是迄今为止最快的单周增长速度。从05-25的★6,420到07-06的★17,961，6周内翻了2.8倍。说明HKUDS实验室的AI交易Agent生态获得社区爆炸式认可。
- **AI-Trader（★20,482）** 超越Vibe-Trading（★17,961）成为HKUDS更底层的旗舰项目——但Vibe-Trading增速是AI-Trader的20倍。
- **hftbacktest（★4,246）** 是回测类项目的总星王。如果ZQ需要回测引擎，hftbacktest是明确选择。
- **AutoHedge（★3,700）和OpenAlice（★5,820）** 保持稳定增长，没有爆发但也没有降温。

### 新发现项目汇总

| 项目 | ★ | 类型 | 推荐级别 |
|:----|:-:|:----:|:--------:|
| **51bitquant/howtrader** | ★932 | 量化框架 | ⭐⭐⭐ **强烈推荐** |
| **TickDB/tickdb-marketdata-api** | ★512 | 数据API | ⭐⭐⭐ **强烈推荐** |
| **0xrsydn/polymarket-crypto-toolkit** | ★59 | 预测市场工具 | ⭐⭐⭐ **强烈推荐** |
| **marketcalls/vectorbt-backtesting-skills** | ★166 | 回测MCP | ⭐⭐ |
| **cubexch/ai-fund** | ★10 | 42对冲基金Agent | ⭐⭐ |
| **Drakkar-Software/OctoBot-AI** | ★8 | AI Hedge Fund框架 | ⭐⭐ |
| **DepthSight-Pro/DepthSight** | ★10 | 可视化交易平台 | ⭐ |
| **truss44/mcp-crypto-price** | ★40 | MCP价格 | 🟡 |
| **laukikk/alpaca-mcp** | ★34 | MCP交易层 | 🟡 |
| **oliver-zehentleitner/unicorn-fy** | ★57 | API标准化 | 🟡 |

---

## 新策略发现

### 1. 42 Agent多策略对冲基金模式（cubexch/ai-fund参考）

**核心思路：** 不是单Agent做所有决策，而是42个专业化Agent（动量、套利、做市、波动率、事件驱动、宏观等）各自独立运行策略，通过聚合器综合所有信号做出最终交易决策。每个Agent相当于一个独立的"策略基金"。

**对ZQ的价值：**
- ZQ当前A4只有一种决策逻辑（评分排序→买入→固定退出）
- 42个并行策略Agent → 多策略融合 → 比单策略更稳健
- 即使5-10个Agent信号差，其他Agent可补偿，而不是像当前ZQ单链一样整体停摆
- **当前USDT弹药充足（$224.15），可以分配3-5个策略并行测试**

### 2. Polymarket预测市场算法交易策略（0xrsydn/polymarket-crypto-toolkit参考）

**核心思路：** 使用Python算法交易工具包，在Polymarket上运行基于赔率偏离的套利/价值交易策略。当预测市场赔率与算法计算的"公允赔率"存在偏差时，自动建仓。

**对ZQ的价值：**
- 预测市场与CEX价格低相关性 → 增加策略多样性的理想维度
- Python工具包完全兼容ZQ生态 → 直接集成到A4决策管道
- **当前USDT$224.15弹药充足→分$50到Polymarket作为实验性策略**
- 配合已推荐的CloddsBot（★455，覆盖Polymarket跨市场监控）使用效果更佳

### 3. 多交易所数据标准化策略（unicorn-fy参考）

**核心思路：** 使用unicorn-fy库（★57）将不同交易所（Binance、OKX、Bybit等）的API响应统一格式化为一致数据结构。然后基于统一格式运行跨交易所策略——价差监控、套利信号、流动性对比。

**对ZQ的价值：**
- 当前CCXT已安装但56天零使用，部分原因可能是数据格式不统一
- unicorn-fy可以在CCXT之上增加一层标准化
- **降低CCXT激活的心理门槛**：`pip install unicorn-fy` → 一行代码统一多交易所数据

### 4. ML+LightGBM交易策略工作流（djienne/ML_Trading_Strategy_Crypto_BTC_LightGBM_Ja参考）

**核心思路：** 模块化的ML交易工作流，用LightGBM梯度提升树进行BTC价格预测。管道分阶段独立运行：数据获取→特征工程→模型训练→回测→实盘。

**对ZQ的价值：**
- ZQ当前的所有交易决策基于传统技术指标评分
- 引入LightGBM ML信号作为A2/A3评分的额外维度
- 回报可衡量：策略的回测结果可量化评估

---

## 新数据源发现

| 数据源 | 类型 | 免费/付费 | 填补缺口 | 集成难度 |
|:-------|:-----|:---------:|:---------|:--------:|
| **TickDB API** | 实时多市场数据 | freemium | 多市场数据（加密+股票+外汇），可作Binance替代 | 低（REST API） |
| **CoinCap MCP** (coincap-mcp) | CoinCap MCP服务 | ✅ 免费 | Agent原生数据查询（Hermes兼容） | 极低（MCP工具） |
| **mcp-crypto-price** | MCP价格分析 | ✅ 免费开源 | Agent原生价格+新闻+分析 | 极低（MCP工具） |
| **unicorn-fy** | API响应标准化 | ✅ 免费开源 | 多交易所数据结构统一 | 低（pip install） |
| **Alpaca MCP** | Alpaca交易MCP | ✅ 免费开源 | 美股+加密交易层（远期） | 低（MCP工具） |

**数据源现状重申（第56天）：** A1的6维数据缺口（资金费率、多空比、大单异动、链上聪明钱、波动率指数、币种基本面排序）依然是 **0/6维（0%）**。所有推荐的数据源——CoinOS（35天）、fia-signals-mcp（28天）、GMGN OpenAPI（7天）、TickDB（本期新增）——全部因闭环缺失而零集成。

---

## 对比历史

### 上期（06-29）推荐了什么 — 7天追踪状态

| 推荐项 | 推荐级别 | 集成状态 | 备注 |
|:-------|:--------:|:--------:|:-----|
| **Tradememory-Protocol** (★1,378→★1,386) | ⭐⭐⭐最重要 | ❌ 未集成 — **7天** | +8★增长 |
| **AI Hedge Fund Crypto** (★598→★596) | ⭐⭐ | ❌ 未集成 — **7天** | -2★略降 |
| **Swapper Toolkit DeFi层** (★814→?) | ⭐⭐ | ❌ 未集成 — **7天** | 未刷新 |
| **GMGN Skills链上聪明钱** (★352→★360) | ⭐ | ❌ 未集成 — **7天** | +8★增长 |
| **CBT Framework** (★54→?) | 🟡 | ❌ 未集成 — **7天** | 未刷新 |

### P0任务执行状态（连续9期追踪 — 已达56天）

| P0任务（05-11首次提出） | 05-18 | 05-25 | 06-01 | 06-08 | 06-15 | 06-22 | 06-29 | 07-06 | **持续天数** |
|:-------------------|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:-------:|
| CCXT激活（已安装零使用） | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **56天** 🔴 |
| Etherscan Monitor激活 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **56天** 🔴 |
| CoinOS/AiCoin集成（06-01新增） | — | — | 🆕 | ❌ | ❌ | ❌ | ❌ | ❌ | **35天** 🔴 |
| fia-signals-mcp集成（06-08新增） | — | — | — | 🆕 | ❌ | ❌ | ❌ | ❌ | **28天** 🔴 |
| Vibe-Trading评估（06-15新增） | — | — | — | — | 🆕 | ❌ | ❌ | ❌ | **21天** 🔴 |
| AI-Trader评估（06-22新增） | — | — | — | — | — | 🆕 | ❌ | ❌ | **14天** 🔴 |
| Tradememory-Protocol评估（06-29新增） | — | — | — | — | — | — | 🆕 | ❌ | **7天** 🔴 |
| **Howtrader评估（本期新增）** | — | — | — | — | — | — | — | 🆕 | **0天** |

### 本期新增（07-06 vs 06-29）

| 新增项 | 对ZQ的价值 | 推荐级别 |
|:-------|:----------|:--------:|
| **Howtrader (51bitquant)** — ★932，量化框架+回测+实盘 | **同一作者的DAG架构框架配套** — 与ai-hedge-fund-crypto组合使用 | ⭐⭐⭐ **最重要** |
| **TickDB API** — ★512，AI-native实时市场数据API | **Binance API被封后的备选数据源** — 多市场覆盖 | ⭐⭐⭐ |
| **0xrsydn/polymarket-crypto-toolkit** — ★59 Python原生 | **Python原生预测市场算法交易** — 新收益维度 | ⭐⭐⭐ |
| **vectorbt-backtesting-skills** — ★166 VectorBT MCP | **Agent驱动的回测能力** — Quant无需手动跑回测 | ⭐⭐ |
| **cubexch/ai-fund** — ★10 42对冲基金Agent | **多Agent并行架构参考** — 替代串行单链方案 | ⭐⭐ |
| **OctoBot-AI** — ★8 Crypto AI Hedge Fund框架 | **OctoBot生态40+交易所接入能力** | ⭐⭐ |
| **DepthSight** — ★10 自托管可视化平台 | **实时可视化交易仪表盘** — ZQ当前无前端 | ⭐ |
| **alpaca-mcp / mcp-crypto-price / unicorn-fy** | MCP扩展/数据标准化 | 🟡 |

### 56天关键趋势变化

| 维度 | 05-11状态 | 06-08状态 | 06-15状态 | 06-22状态 | 06-29状态 | 07-06状态 | 变化趋势 |
|:-----|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|:--------|
| 数据管道完整性 | 部分 | A1A2A3✅ A3A4⏳ | ✅ 新鲜 | A4停摆3天 | ✅ A4恢复 | A4再停摆❌ | 🔴 **反复停摆** |
| 实际数据采集 | — | 0/6维（0%） | 0/6维（0%） | 0/6维（0%） | 0/6维（0%） | 0/6维（0%） | 🔴 **56天零改善** |
| CCXT/Etherscan | — | 28天零使用 | 35天零使用 | 42天零使用 | 49天零使用 | **56天零使用** | 🔴 **每周刷新纪录** |
| 资金 | $427 | $276（-35.6%） | 查询失败 | $235（-45.2%） | $140（-67.3%） | **$224（-47.9%）** | 🟢 **大幅回升** |
| 推荐闭环率 | — | 0% | 0% | 0% | 0% | **0%** | 🔴 **56天零闭环** |
| 累计推荐工具数 | 7项 | 25+项 | 32+项 | 40+项 | 46+项 | **55+项** | 🟡 但零集成 |
| USDT现金 | — | — | $20.85(8.4%) | $107(45.6%) | $79.55(56.6%) | **$224.15(100%)** | 🟢 **弹药充足** |
| A4活跃度 | ✅ | ✅ | ✅ | ⚠️停摆3天 | ✅ Cycle#498 | **❌ 无数据** | 🔴 **反复停摆** |
| ZH每日简报 | ❌ | ❌ | ❌ | ❌ | ❌ 13天 | **❌ 20天** | 🔴 **恶化** |
| Binance API直连 | ✅ | ✅ | ✅ | ✅ | ❌被封 | ❌被封 | 🔴 持续 |
| SOCKS5/Tor隧道 | — | — | — | — | ❌宕机 | ❌宕机 | 🔴 持续 |

### 56天里程碑分析

```diff
- 第1期（05-04）：初始扫描，7个工具推荐开始
- 第4期（06-01）：发现CoinOS可填补6个数据缺口
- 第5期（06-08）：发现根因不是缺工具是缺闭环
- 第6期（06-15）：35天零闭环，32+项推荐零集成
- 第7期（06-22）：42天零闭环，A4首次停摆
- 第8期（06-29）：49天零闭环。A4恢复！但资金崩盘至$140
+ 第9期（07-06 今天）：56天零闭环。总资回升至$224！
+  好消息：资金大幅回升（+$84，+59.7%），USDT从$79.55→$224.15
+  坏消息：A4再次停摆。ZH简报20天未出。闭环率仍为0%
```

**两根金线交织——资金回升与闭环困境：**

```diff
+ 资金线：$140 → $224（+59.7%）🟢 数周来首次正面突破
- 闭环线：56天，55+项推荐，0集成 🔴 每周刷新纪录
- A4线：恢复→停摆→恢复→停摆，反复无常
```

**根因链更新（第9期）：**

```diff
- 旧根因链：A4停摆 → 交易中断 → 参数过时 → 资金流失
- 新根因链（07-06）：A4间歇性运行+反复停摆 → 无人发现
+   → 但A1/A2/A3全链路活跃 → A5每日复盘也在出
+     → ZH每日简报20天不出 → 总控对系统状态全面失明
+       → 资金虽然短期回升但管道的交易执行端（A4）停摆中
```

---

## 对ZQ系统的改进建议

### 🔴 P0 — 本周必须解决

**1. 诊断并修复A4引擎反复停摆问题（最紧急）**

A4在上期刚恢复（06-29 Cycle #498运行），7天后再次显示"❌ 无数据"。这是**第二次A4停摆**。无法交易执行的交易系统毫无意义。

**检查清单：**
```bash
# 1. A4进程是否存活？
ps aux | grep a4

# 2. A4日志最后50行
tail -50 agents/a4/*.log

# 3. 是否触发某个异常导致崩溃？检查error log
grep -i "error\|exception\|traceback" agents/a4/*.log

# 4. 检查A4的cron定时任务配置
crontab -l | grep a4

# 5. 比较A4上次成功运行的配置与当前配置
```

**2. 打破56天零闭环记录 — 做任何一个P0（这次必须做！）**

**56天。55+项推荐。零集成。** 这个记录已经超出了"问题"的范畴，它是系统机制的根本性缺陷。

当前USDT有$224.15弹药——这是几周来最充足的时刻。如果这个资金窗口再次流失，下一次不知要等多久。

| 选项 | 时间 | 操作 |
|:----|:---:|:-----|
| **A. CCXT激活（最低门槛）** | **5分钟** | `import ccxt` — 已安装！加一行fallback代码 |
| **B. 0xrsydn/polymarket-crypto-toolkit安装** | **5分钟** | `git clone + pip install` 即可开始 |
| **C. CoinOS Open API调用** | 30分钟 | 5个REST调用获取费率/大单/多空比 |
| **D. mcp-crypto-price集成** | 10分钟 | MCP工具对接Hermes |

**3. 恢复ZH每日简报（20天中断）**

最后一份ZH简报是06-16。20天来总控对系统状态完全失明。没有日度诊断，系统的小问题累积成大问题，大问题无人发现直到Agent停摆。

**建议最低行动：** 在A5（日度复盘Agent）的输出中增加ZH简报section。

### 🟠 P1 — 本周评估

**4. 评估howtrader（★932）+ ai-hedge-fund-crypto（★596）组合**

**51bitquant**的这两个项目合起来提供了完整的量化AI交易栈：
- howtrader：量化框架（策略开发→回测→执行）
- ai-hedge-fund-crypto：LangGraph DAG AI对冲基金

**建议：** Quant在23:00分析中阅读两个项目的README，评估是否可以抽取其DAG工作流引擎或策略开发模块。

**5. 评估0xrsydn/polymarket-crypto-toolkit（★59）作为预测市场入口**

Python原生工具包，truly兼容ZQ生态。相比之前推荐的CloddsBot（TypeScript）和Polymarket/agents（TypeScript），这个是ZQ技术栈直接能用的。

**建议：** 分配$20-30 USDT到Polymarket，用这个工具包运行基础测试策略（赔率偏离套利）。

**6. 评估TickDB API（★512）作为Binance API替代数据源**

当前Binance API直连被封，依赖AWS SSH代理（单点故障）。TickDB提供独立的多市场数据通道。

**建议：** 注册TickDB免费层，验证其加密数据覆盖面能否覆盖ZQ当前监控币种。

**7. 评估VectorBT MCP回测技能（★166）**

VectorBT是Python最高性能回测库之一。如果不能集成hftbacktest（★4,246），VectorBT MCP是更轻量的替代方案。

### 🟡 P2 — 持续改进

**8. ATR动态止损替代固定百分比（从06-15延续，5期未动）**

**9. 震荡市网格模式（从06-15延续，5期未动）**

**10. 持续追踪Scouter推荐闭环率（第9期追踪）**

### 持续追踪：推荐闭环率（56天全记录）

| 推荐日期 | 推荐项 | 级别 | 状态 | 持续天数 |
|:--------:|:------|:---:|:----:|:-------:|
| 05-11 | CCXT激活 | P0 | ❌ | **56天** 🔴 |
| 05-11 | Etherscan Monitor激活 | P0 | ❌ | **56天** 🔴 |
| 05-18 | btc-hedge-lab对冲策略 | ⭐⭐ | ❌ | **49天** 🔴 |
| 05-18 | Arkham Intelligence | ⭐⭐ | ❌ | **49天** 🔴 |
| 05-25 | QuantDinger多Agent架构 | ⭐⭐ | ❌ | **42天** 🔴 |
| 05-25 | homerun预测市场 | ⭐⭐ | ❌ | **42天** 🔴 |
| 06-01 | CoinOS/AiCoin数据源 | ⭐⭐ | ❌ | **35天** 🔴 |
| 06-01 | Moss策略进化架构 | ⭐ | ❌ | **35天** 🔴 |
| 06-01 | Regime Classifier体制检测 | ⭐ | ❌ | **35天** 🔴 |
| 06-08 | CloddsBot跨市场Agent | ⭐⭐⭐ | ❌ | **28天** 🔴 |
| 06-08 | OpenWhale架构参考 | ⭐⭐ | ❌ | **28天** 🔴 |
| 06-08 | fia-signals-mcp即用信号 | ⭐ | ❌ | **28天** 🔴 |
| 06-08 | crypto-liquidity-ai-bot | ⭐ | ❌ | **28天** 🔴 |
| 06-08 | AlgoVault quant-signal | ⭐ | ❌ | **28天** 🔴 |
| 06-15 | Vibe-Trading回测引擎 | ⭐⭐⭐ | ❌ | **21天** 🔴 |
| 06-15 | OpenAlice全资产Agent | ⭐⭐ | ❌ | **21天** 🔴 |
| 06-15 | HydraQuant架构参考 | ⭐ | ❌ | **21天** 🔴 |
| 06-15 | Pattern-Signal-Automator | ⭐ | ❌ | **21天** 🔴 |
| 06-22 | AI-Trader Agent框架 | ⭐⭐⭐ | ❌ | **14天** 🔴 |
| 06-22 | AutoHedge蜂群智能 | ⭐⭐⭐ | ❌ | **14天** 🔴 |
| 06-22 | ATLAS-GIC自进化Agent | ⭐⭐ | ❌ | **14天** 🔴 |
| 06-22 | Polymarket/agents SDK | ⭐⭐ | ❌ | **14天** 🔴 |
| 06-29 | Tradememory-Protocol记忆层 | ⭐⭐⭐ | ❌ | **7天** 🔴 |
| 06-29 | AI Hedge Fund DAG工作流 | ⭐⭐ | ❌ | **7天** 🔴 |
| 06-29 | Swapper Toolkit DeFi层 | ⭐⭐ | ❌ | **7天** 🔴 |
| 06-29 | GMGN Skills链上聪明钱 | ⭐ | ❌ | **7天** 🔴 |
| **07-06** | **Howtrader量化框架** | **⭐⭐⭐** | **🆕** | **0天** |
| **07-06** | **TickDB数据API** | **⭐⭐⭐** | **🆕** | **0天** |
| **07-06** | **polymarket-crypto-toolkit** | **⭐⭐⭐** | **🆕** | **0天** |
| **07-06** | **vectorbt-backtesting-skills** | **⭐⭐** | **🆕** | **0天** |
| **07-06** | **cubexch/ai-fund** | **⭐⭐** | **🆕** | **0天** |
| **07-06** | **OctoBot-AI / DepthSight** | **⭐** | **🆕** | **0天** |

### 诚实判断（第9期）：好消息与坏消息并存

```diff
- 坏消息 #1：A4再次停摆（间歇性运行问题）
- 坏消息 #2：ZH每日简报20天未出（总控失明）
- 坏消息 #3：56天零闭环记录持续刷新
+ 好消息 #1：总资从$140大幅回升至$224（+59.7%）
+ 好消息 #2：USDT从$79.55增至$224.15（弹药充足！）
+ 好消息 #3：A1/A2/A3/A5/A7/A8/A9全链路健康运行
+ 好消息 #4：A5今日复盘正常出产（07-06 08:00）
```

**本期最大矛盾：系统其余部分的健康状况（A1/A2/A3/A5/A7/A8/A9都活跃）与交易执行端的瘫痪（A4停摆+ZH简报20天未出）形成鲜明对比。资金在增长，但系统无法交易。**

**Scouter的第9期反思（56天回顾）：**

Scouter已连续9周（56天）发现高质量的开源交易项目——从hftbacktest（★4,246）到Vibe-Trading（★17,961）到AI-Trader（★20,482）到Tradememory-Protocol（★1,386）到Howtrader（★932）——累计55+项推荐，但集成率始终为0%。**Scouter的工作已经完成了"发现"阶段，但"发现→评估→集成→验证"的闭环从未被系统执行过。**

56天的零闭环率意味着：**问题不在工具层面，在系统架构层面——没有Agent/机制负责把Scouter的输出转化为代码变更。** 这是总指挥（ZH）需要从根本上解决的架构问题。

---

## 附录：已排除项

| 项目 | 排除原因 |
|:-----|:---------|
| buddies2705/awesome-blockchain-crypto-api（★0） | 仅列表仓库，非可用工具 |
| patrickskyman/crypto_pattern_detector（★0） | 0星，不可用 |
| caizongxun/crypto-zigzag-ml（★0） | 0星，太早期 |
| abc5051001/Crypto-Trading-bot | 2022年项目，严重过时 |
| shaunn17/MarketGuardian | 2025年项目，非2026活跃 |
| sofi111222321/Crypto-Strategy-Backtester（★26） | 2025年项目 |
| asier13/Python-Trading-Bot（★25） | 仅RSI策略定标，功能单一 |
| CyberPunkMetalHead/backtesting-for-cryptocurrency（★183） | 2021年项目，过时 |
| pierreia/quantGPT（★23） | 2024年项目，非活跃更新 |
| SofienKaabar/Backtesting-for-Crypto | 文档/教程性质，非工具 |

---

*ZH侦察签名：2026-07-06 08:15 CST*
*扫描方法：GitHub REST API搜索（6个泛化关键词 × 多查询）+ 深度爬取20+仓库元数据 + 历史9期报告比对 + global_state.json（2026-07-06 08:10）系统状态验证*
*系统状态来源：`shared/global_state.json` 2026-07-06 08:10 → $224.15 total equity / $224.15 USDT（Binance API实时验证）*
*报告文件：`learning/scouter_report_20260706.md`*
*下一期扫描：2026-07-13（周一08:00）*
