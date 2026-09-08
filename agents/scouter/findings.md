# Scouter 发现记录
## 第1期 — 2026-05-11

**本期扫描范围：** freqtrade新策略、多Agent交易框架、数据源/情绪/链上工具、AI交易回测方法

---

## 评估汇总

| 发现 | 类型 | 有用吗 | 理由 | 集成难度 | 补缺口 |
|------|------|--------|------|---------|-------|
| **hftbacktest** (nkaz001) | 回测框架 | ✅ 有用 | 订单簿级HFT回测，延迟建模+队列位置模拟，tick级仿真。当前ZQ缺少专业回测引擎，Blade/Quant只能靠实盘验证策略。支持多交易所，pip一键安装。 | 中等（~300-500行封装层） | 策略多样性验证 |
| **Tomortec/CryptoTradingAgents** | 多Agent框架 | ✅ 有用 | 262★，Python多Agent分析系统。整合7+数据源（Binance K线/深度、Alternative.me F&G、CoinDesk、CoinStats、Blockbeats、Reddit情绪、taapi技术指标）。中文社区活跃，可填补NBZ的数据多样性缺口。 | 简单（~200行对接） | 情绪数据/策略多样性 |
| **sserrano44/CryptoAgents** | Agent框架/架构 | 🟡 可能有用 | 23★，LangGraph多Agent交易台模拟（分析师→研报→交易→风控→PM全链路Bull/Bear辩论）。架构设计值得借鉴，但仅8次提交，数据源只有CoinMarketCap。 | 中等（架构参考，非直接集成） | 策略多样性 |
| **OctoBot-Market-Making** | 做市工具 | 🟡 可能有用 | 32★，专注做市策略，15+交易所跨平台挂单簿创建维护，防套利保护。如果ZQ未来想做市策略，这是最成熟的开源选项。当前系统以趋势/动量为主，缺做市策略维度。 | 中等（~400行） | 策略多样性 |
| **TradeCat (tukuaiai/tradecat)** | 数据终端 | 🟡 可能有用 | 937★，专为AI Agent设计的数据缓存/展示终端，零安装脚本、多格式缓存(JSON/JSONL/CSV)、TUI浏览。数据流设计模式值得学习（缓存优先+异步探测），但数据源是Google Sheets CSV而非交易所。 | 简单（设计模式参考） | 数据架构 |
| **OnChainIQ** | 链上数据工具 | 🟡 可能有用 | MIT开源，Python库封装Etherscan/BscScan等API，内置缓存和聚合。ZQ已有etherscan集成，但OnChainIQ的聚合和缓存层可能简化现有代码。 | 简单（~100行替代现有实现） | 链上数据 |
| **CryptoInsight** | 情绪数据 | 🟡 可能有用 | 开源GPL-3.0，封装Alternative.co免费API + NLP新闻情绪分析。ZQ已有F&G但从Alternative.co直接拿，CryptoInsight新增NLP新闻情绪可填补"新闻文本情绪"维度。 | 简单（~100行） | 情绪数据 |

---

## 已排除项（不写入推荐）

| 发现 | 排除原因 |
|------|---------|
| Samiron18/freqtrade-strategy-hub | 仅1次提交、3★，名不符实——README写了一大堆但仓库尚空，太早期 |
| CryptoHFT (Meril99) | 仅4次提交、1★，虽然C++/Python混合架构有想法但不可用 |
| HyperEVM Cross-Pool Arbitrage | 付费商业产品(联系Telegram)，非开源，仅支持HyperEVM |
| MemeScope | 只聚焦Meme币，范围太窄 |
| Sentinel On-Chain | v0.5太早期(3天前发布)，功能不稳定 |
| ChainSage | 搜索结果存疑，repo可能不存在 |
| DeFi Pulse Data | DeFi TVL/借贷数据，与ZQ现货/合约交易无关 |
| Swapper Finance Toolkit | JavaScript/TypeScript，不兼容Python生态，且是执行层非分析层 |
| Manashwy/Crypto_Arbitrage | 2次提交，仅概念验证 |

---

## 详细说明

### 1. hftbacktest (nkaz001/hftbacktest) ✅ 强烈推荐

**GitHub:** https://github.com/nkaz001/hftbacktest
**Star:** 数百(上游项目)
**语言:** Python 3.10+ + Rust
**许可:** 开源
**安装:** `pip install hftbacktest`

**为什么有用：** ZQ Web 4.0当前没有独立的回测引擎——Blade实盘执行，Quant靠事后分析。hftbacktest提供：
- Tick级L2/L3订单簿重建
- 延迟建模（网络延迟、交易所撮合延迟）
- 队列位置模拟（订单在订单簿队列中的位置）
- Numba JIT加速
- 多交易所支持（Binance等）
- 回测结果可以直接转化为引擎参数

**集成方案：** 封装一个 `BacktestEngine` 类：
- 输入：历史K线/深度数据（从现有的data/node_history.jsonl或Binance API获取）
- 输出：回测报告（胜率、盈亏比、夏普率、最大回撤）
- 跑在Quant的每日23:00分析流程中，验证策略参数

**预计代码行数：** 300-500行封装层 + 策略适配

---

### 2. Tomortec/CryptoTradingAgents ✅ 有用

**GitHub:** https://github.com/Tomortec/CryptoTradingAgents
**Star:** 262★
**语言:** Python 3.10+
**许可:** Apache 2.0

**为什么有用：**
- 7+数据源整合：Binance (K线/深度)、Alternative.me (F&G)、CoinDesk、CoinStats、Blockbeats、Reddit情绪、taapi.io (技术指标)
- 多Agent分工：市场分析师、社交媒体分析师、新闻分析师、基本面分析师
- 中文社区活跃（README有中文版）
- 数据源丰富的模块可以直接抽取给NBZ用

**与ZQ的互补：**
- NBZ目前数据源：CoinGecko、F&G、新闻、聪明钱
- CryptoTradingAgents新增：Reddit情绪分析、Blockbeats新闻、CoinStats、taapi技术指标
- Agent报告PDF/MD生成模式可以参考

**集成方案：** 抽取其数据采集层（特别是Reddit情绪、Blockbeats、CoinStats），封装成NBZ的数据插件

**预计代码行数：** ~200行对接（主要是数据源API封装）

---

### 3. sserrano44/CryptoAgents 🟡 可能有用

**GitHub:** https://github.com/sserrano44/CryptoAgents
**Star:** 23★
**语言:** Python 3.13+
**许可:** 隐式（TradingAgents fork）

**架构参考价值：** LangGraph多Agent工作流——分析师→Bull/Bear辩论→交易团队→风控团队（激进/中性/保守）→PM综合决策。这种辩论和梯度风险管理的设计模式可以直接应用于Commander的决策流程。

**缺点：** 数据源单一（仅CoinMarketCap），仅8次提交，项目基本停滞（11个月前最后更新）

**使用方式：** 参考其LangGraph编排模式，不直接集成

---

### 4. OctoBot-Market-Making 🟡 可能有用

**GitHub:** https://github.com/Drakkar-Software/OctoBot-Market-Making
**Star:** 32★
**语言:** Python 3.x
**许可:** GPL-3.0

**特点：** 专注做市策略——创建维护订单簿、跨15+交易所参考价格同步、防套利保护、轻量级(250MB RAM)

**适用场景：** ZQ目前以趋势/动量策略为主，补充做市策略可增加策略多样性，降低单一策略依赖风险

**集成方式：** 作为独立模块运行（类似FK风控的独立进程），不干扰现有引擎

---

### 5. TradeCat (tukuaiai/tradecat) 🟡 可能有用

**GitHub:** https://github.com/tukuaiai/tradecat
**Star:** 937★
**语言:** Python 3.12+
**许可:** MIT

**为什么特别：** 专为AI Agent设计的数据终端。数据流设计极佳：缓存优先+异步探测→网络慢不阻塞界面。零安装脚本（一行命令获取数据）。多格式缓存（JSON给Agent、JSONL给Shell脚本、CSV给电子表格）。

**参考价值：** TradeCat的Agent Skill结构和零安装数据请求脚本值得在ZQ中复用。但数据源是Google Sheets CSV（公开的实时市场数据），不是交易所直连，所以作为数据源价值有限。

---

## 本期推荐

**可直接集成（有用）：** 2个
- **hftbacktest** → 回测引擎，填补策略验证缺口
- **Tomortec/CryptoTradingAgents** → 数据源插件，填补情绪数据多样性缺口

**可参考学习（可能有用）：** 5个
- sserrano44/CryptoAgents → LangGraph编排模式
- OctoBot-Market-Making → 做市策略
- TradeCat → Agent数据流架构
- OnChainIQ → 链上数据聚合层
- CryptoInsight → NLP新闻情绪

---

*下一期扫描：2026-05-18（每周一）*
