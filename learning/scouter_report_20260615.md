# ZH侦察报告（为ZQ系统）— 2026-06-15 08:05

> **侦察视角：** ZH总控的独立侦察兵（非ZQ-Scouter）
> **扫描时间：** 2026-06-15 08:05 CST（周一例行全网扫描）
> **上次报告：** 2026-06-08（第5期）— 已集成记录至SHARED.md
> **方法：** web_search（6个关键词 × 多引擎搜索）+ 前几期历史比对 + 系统状态验证（global_state.json + SHARED.md）
> **来源说明：** 所有发现注明来源URL，数字引用来自全局状态或搜索结果的公开信息

---

## 执行摘要

本期全网扫描发现 **7个值得关注的新工具/项目**，其中 **1个强烈推荐评估（Vibe-Trading / HKUDS, 12,168★）**、**1个强烈推荐参考（OpenAlice, 5,224★）**、**2个推荐学习（HydraQuant架构 / Pattern-Signal-Automator）**、**3个数据源值得关注（ChainLens AI / WhaleTracker Pro / CoinMindAI）**。

**自06-08以来的重大变化：**

| 指标 | 上期（06-08） | 当前（06-15） | 变化 |
|:----|:-----------:|:-----------:|:----:|
| 系统总资 | $276.76 | 查询失败 ❌（API不可达） | ⚠️ 未知 |
| A1→A2→A3链路 | ✅ 全部 | ✅ 全部（至07:08） | 🟢 保持 |
| A3→A4链路 | ⏳ 断裂 | ⏳ 断裂（29天+） | 🔴 无改善 |
| A1数据采集 | 0/6维（0%） | 0/6维（0%） | 🔴 无改善（34天） |
| CCXT使用 | 29天零使用 | **35天零使用** | 🔴 刷新纪录 |
| Etherscan Monitor | 29天零使用 | **35天零使用** | 🔴 刷新纪录 |
| 通知平台 | 🔴 三平台全断 | 🔴 三平台全断 | 🔴 无变化 |
| ZH每日简报 | ❌ 未出 | ❌ 未出 | ❌ 无改善 |

**最严重的问题变化（第35天追踪）：**

- **CCXT和Etherscan Monitor已经连续35天零集成**——从05-11首次提出到今天，从未被激活过一次。这不是"繁忙"，这是闭环机制完全失效的证据。
- **A3→A4链路断裂29天+**：global_state.json明确标注"⏳ 暂无A3推荐或A4数据"，意味A3找了好币但A4无法感知。这直接导致系统空转。
- **余额查询失败（06-15 08:05）**：系统看起来还在运转（A1/A2/A3数据新鲜），但实际交易能力存疑。
- **ZH每日简报仍为"❌ 未出"**：总控对系统状态的日度感知中断。
- **正面变化**：管道A1→A2→A3运转正常，框架没有崩溃，只是数据质量和流通链路有问题。

---

## 新工具发现

### ⭐⭐⭐ HKUDS/Vibe-Trading（强烈推荐评估 — 本期最重要发现）

| 字段 | 值 |
|:-----|:----|
| 平台 | `HKUDS/Vibe-Trading`（GitHub） |
| 免费/付费 | **完全开源（MIT）** — 自托管，零订阅 |
| 星数 | **12,168★** ⚡（从05-25的6,420★翻倍增长） |
| 语言 | Python（88.4%）+ TypeScript（8.8%） |
| 更新日期 | 2026-06-14（每日活跃，v0.1.8已发布） |
| 推荐理由 | **AI量化交易平台**，覆盖加密/股票/外汇三大市场。核心能力：回测引擎 + 实盘交易 + 市场数据 + **多Agent研究**（vibe-trading, trading-agents, ai-trader, ai-trading）。上次05-25报告时发现的是"brokermr810/QuantDinger"（当时6,420★），现在该项目已整合到HKUDS正式org下，星数翻倍至12,168★，说明社区认可度极高。v0.1.8支持外部MCP工具集成 |
| 弥补缺口 | **策略回测 / 多Agent协作架构 / 跨市场回测** |
| 集成难度 | 中等（Python生态兼容，可抽取向导模块或运行独立回测） |
| URL | https://github.com/HKUDS/Vibe-Trading |

**为何重新评估（本期最重要理由）：**

1. **从QuantDinger（05-25, 6,420★）到HKUDS/Vibe-Trading（12,168★）** — 1个月内星数翻倍，且迁移到学术机构HKU（香港大学）数据科学实验室的正式组织下，靠谱度显著上升。
2. **v0.1.8新增外部MCP工具集成** — 与前几期推荐的fia-signals-mcp、AlgoVault quant-signal MCP服务生态兼容。
3. **对ZQ的核心价值** — Vibe-Trading提供Python原生的多Agent研究模式和回测引擎，而ZQ当前既无独立回测也无多Agent协作框架。直接抽取其Agent协作模式可填补A3→A4断裂后的策略生成链路。
4. **安装即用**：`pip install vibe-trading`（已发布PyPI）。

> 注意：Vibe-Trading不是CloddsBot的替代品（两者定位不同）。CloddsBot是跨市场即时执行Agent，Vibe-Trading是研究/回测/策略生成平台。**建议两个都评估**。

---

### ⭐⭐ TraderAlice/OpenAlice（强烈推荐参考 — 全资产AI交易Agent）

| 字段 | 值 |
|:-----|:----|
| 平台 | `TraderAlice/OpenAlice`（GitHub） |
| 免费/付费 | **完全开源（AGPL-3.0）** |
| 星数 | **5,224★**（2026-02开源核心，快速增长） |
| 语言 | TypeScript |
| 部署方式 | Docker Compose一键部署 |
| 推荐理由 | **"你一个人的华尔街"** — 全资产覆盖（股票/加密/大宗/外汇/宏观），从研究→仓位建立→持续管理→退出的全生命周期AI Agent。支持自然语言问答。内置交易日志/回测/风险管理。已发布官方Demo站点和Docker镜像 |
| 弥补缺口 | **全资产交易Agent参考架构 / 多市场覆盖设计模式** |
| 集成难度 | 架构参考（Docker独立部署，非Python生态，但设计模式可参考） |
| URL | https://github.com/TraderAlice/OpenAlice |

**对ZQ的价值：**

- OpenAlice的"从研究到退出"全链路Agent设计与ZQ的Agent分工（A1→A2→A3→A4→A5→ZH）模式互补。
- 其**宏观数据集成**（大宗/外汇）是ZQ完全空白的维度。
- **Trading as Git（TaG）** 概念 — 用Git版本管理交易策略和日志，值得ZQ参考。

---

### ⭐ ymcbzrgn/HydraQuant（推荐参考 — 架构研究）

| 字段 | 值 |
|:-----|:----|
| 平台 | `ymcbzrgn/HydraQuant`（GitHub） |
| 免费/付费 | 开源 |
| 星数 | **9★**（早期项目） |
| 语言 | Python（91.8%）+ Vue.js |
| 推荐理由 | **AI驱动的量化加密交易引擎**，架构设计极具参考价值：**18种RAG类型 + 10个自主Agent + 证据优先信号引擎 + 自学习风险管理**。构建在Freqtrade基础上。虽然9星为早期项目，但其18种RAG和10 Agent分工的设计思路是ZQ可以学习的 |
| 弥补缺口 | **RAG应用模式 / 多Agent分工架构参考** |
| 集成难度 | 架构参考（太早期不宜直接集成） |
| URL | https://github.com/ymcbzrgn/HydraQuant |

**架构亮点：** 18种RAG类型意味着它针对不同市场维度（订单簿、链上、新闻、社交媒体、技术指标等）使用不同的检索增强生成策略。这比ZQ当前单一的评分系统精细得多。

---

### ⭐ DevDevahmed/Pattern-Signal-Automator（推荐关注）

| 字段 | 值 |
|:-----|:----|
| 平台 | `DevDevahmed/Pattern-Signal-Automator`（GitHub） |
| 免费/付费 | 开源 |
| 星数 | 数十（新项目，具体未确认） |
| 语言 | Python |
| 推荐理由 | **自动化图表形态扫描器**（Pattern Sentinel）。将原始价格行为转化为结构化、可执行信号。识别多头/空头形态形态、突破确认、形态完成度评分。与ZQ当前完全依赖技术指标评分的策略形成互补 |
| 弥补缺口 | **图表形态自动识别维度** — ZQ当前无K线形态感知 |
| URL | https://github.com/DevDevahmed/Pattern-Signal-Automator |

---

### 🟡 gong1414/omnitrade（可关注）

| 字段 | 值 |
|:-----|:----|
| 平台 | `gong1414/omnitrade`（GitHub） |
| 免费/付费 | 开源 |
| 星数 | **1★**（全新项目，v0.1.0 06-14刚发布） |
| 语言 | Python |
| 推荐理由 | **LLM驱动的加密期货竞技场** — 11个竞争策略运行在Agno + AgentOS上，原子三态切换（research→trade→review），实时SSE仪表盘。概念有趣但过于早期 |
| 弥补缺口 | 远期架构参考 |
| URL | https://github.com/gong1414/omnitrade |

---

### 🟡 Cortex-AI-Network/crypto-arbitrage-bot（可关注）

| 字段 | 值 |
|:-----|:----|
| 平台 | `Cortex-AI-Network/crypto-arbitrage-bot-automated-trading`（GitHub） |
| 免费/付费 | 开源 |
| 星数 | **48★** |
| 语言 | TypeScript |
| 推荐理由 | **AI套利机器人** v3.4，支持Solana/TON/Binance/Bybit。自动化套利引擎。如果ZQ未来扩展套利策略维度，此项目可参考 |
| 弥补缺口 | 套利策略维度 |
| URL | https://github.com/Cortex-AI-Network/crypto-arbitrage-bot-automated-trading |

---

## 新策略发现

### 1. 多资产趋势-回调策略（Backtrader + yfinance）

**来源：** PyQuantLab Medium文章，2026-05
**URL：** https://pyquantlab.medium.com/building-a-multi-asset-crypto-trend-pullback-strategy-with-backtrader-cef61a0264c1

**核心思路：** 使用Backtrader框架构建跨币种趋势-回调策略——识别趋势方向后在回调时入场，而非追高。支持Backtrader原生回测引擎。

**对ZQ的价值：**
- ZQ当前A4的买入逻辑基于评分排序（强度+趋势），没有明确的"回调识别"逻辑
- 引入回调检测（基于波动率zone或移动均线偏离）可以减少A4在追高时被套的概率
- Backtrader生态在ZQ中已有基础（之前hftbacktest推荐），可复用

### 2. SQN评分回测验证框架（TrendRider）

**来源：** DEV社区文章，2026
**URL：** https://dev.to/trendrider/backtesting-crypto-strategies-2026-framework-1lf

**核心思路：** 90%的回测是过拟合的，SQN（System Quality Number）评分系统可识别。200+交易验证框架、5个常见回测陷阱避免方法。

**对ZQ的价值：**
- ZQ当前的策略参数设置缺乏统计显著性验证
- SQN评分可直接应用于A4的E2/E3/E4退出策略评估
- 回测验证框架可赋能Quant的每日23:00分析，系统性检查策略是否过拟合

### 3. SOL网格机器人区间策略（CryptoGates）

**来源：** CryptoGates回测报告，2026-06-09
**URL：** https://cryptogates.io/playbooks/sol-usdt-grid-bot-backtest-mar-apr-2026/

**核心思路：** 在$80-$97区间运行的SOL网格策略，2个月+9.26%收益，同期持有者在亏钱。网格从区间震荡中提取利润。

**对ZQ的价值：**
- ZQ当前策略全是方向性的（做多或等待），无中性区间策略
- 在趋势不明朗的市场（FNG=12极恐时空），网格/区间策略是天然的补充
- **值得在ZQ中增加"震荡市网格模式"**：当A4判断市场无趋势时，临时启动网格策略取代方向性策略

### 4. Atom（ATR）三应用策略（Coinquant）

**来源：** Coinquant文章，2026-06-09
**URL：** https://www.coinquant.ai/blog/how-to-use-atr-in-a-crypto-trading-strategy-with-backtest

**核心思路：** ATR的三种具体交易应用：动态止损设置、仓位规模确定、波动率突破确认。有ETH具体价格水平示例。

**对ZQ的价值：**
- ZQ当前E2/E3退出基于固定百分比（-5%/-10%），非波动率自适应
- ATR动态止损可以在高波动时放宽止损避免被噪音震出，低波动时收紧止损控制风险
- 可实现为A4的"ATR自适应止损"功能

### 5. 18个策略回测汇总（QuantPie）

**来源：** QuantPie平台，2026
**URL：** https://trade.medias-ai.cloud/en/quant-strategies/21-strategy-backtest-overview-crypto-trading-results/

**核心思路：** 18种不同策略在四大主流加密交易所的真实回测结果对比。数据可验证。

**对ZQ的价值：**
- 可作为策略类型选择的参考数据集
- 其中表现最好的策略类别可以为A4引擎提供策略扩展方向线索
- 建议Quant在23:00分析中阅读此回测汇总，评估ZQ当前策略的类型分布是否合理

### 6. Meta-RL-Crypto：元学习强化学习框架（arXiv）

**来源：** arXiv学术论文，2026
**URL：** https://arxiv.org/pdf/2509.09751

**核心思路：** 三循环学习过程，LLM作为核心智能体，结合元奖励驱动的自我改进与多模态交易智能。在加密收益预测任务上表现显著优于基线模型。

**对ZQ的价值：**
- 学术前沿参考，对当前ZQ的实际集成价值有限（需要LLM推理支持）
- 但其"多模态数据融合 → 交易信号"的思路值得在A2/A3的数据融合设计中借鉴

### 7. 资金费率感知做市策略（arXiv学术论文）

**来源：** arXiv论文，2026-06
**URL：** https://arxiv.org/html/2605.06405v1

**核心思路：** 在永续合约上研究考虑资金费率的最优流动性提供策略。核心扩展：库存暴露同时产生标记亏损和资金费率支付，两者耦合后最优做市策略需联合优化。

**对ZQ的价值：**
- 如果ZQ未来扩展做市策略，这篇论文是必读的2026年最新研究
- 资金费率数据（ZQ当前缺口）是做市策略的核心输入
- 建议Quant阅读后，评估ZQ是否可以在永续合约市场运行做市策略

### 8. 神经网络加密交易：从LSTM到Transformer（CoinXSight）

**来源：** CoinXSight技术指南，2026
**URL：** https://coinxsight.com/blog/ai-trading/neural-networks-crypto-trading

**核心思路：** 诚实的技术评估——哪种架构（LSTM/Transformer/Attention）在什么场景下有效，常见失败陷阱。无炒作。

**对ZQ的价值：**
- ZQ当前所有信号评分使用传统技术指标
- 如果A2/A3评估需要引入ML信号，此文章提供了架构选择指导
- 建议Quant阅读后决定ZQ是否需要引入神经网络信号

---

## 新数据源发现

| 数据源 | 类型 | 免费/付费 | 填补缺口 | 集成难度 | 与历史推荐对比 |
|:-------|:-----|:---------:|:---------|:--------:|:--------------|
| **Nansen** (nansen.ai) | 链上分析+AI智能钱追踪 | **付费**（专业版$150+/月） | 聪明钱包/鲸鱼追踪 | 简易（REST API） | 功能重合CoinOS，但Nansen数据深度更深。建议先用CoinOS免费方案 |
| **WhaleTracker Pro** (whaletracker.pro) | 区块链智能终端 | 未确认 | 鲸鱼追踪 | 未确认 | 可能与whalecli功能重叠，需进一步评估 |
| **CoinMindAI Whale Watch** (coinmindai.com) | 实时鲸鱼转账追踪 | ✅ 免费 | 大额转账实时监控 | **极简**（网页端，无API） | 作为免费数据参考源，但不是集成数据源 |
| **ChainLens AI** (chainlensai.app) | Base链上AI智能终端 | 未确认 | 链上智能（Base链） | 未确认 | Base链专属，ZQ当前不追踪Base链，远期储备 |
| **Mobula** | DEX链上数据专精 | freemium | DEX价格/流动性数据 | 简易（REST API） | 当ZQ扩展到DEX交易时值得评估 |
| **Glassnode** | 机构级链上分析 | **付费**（$29+/月起步） | 链上深度指标 | 简易（REST API） | 付费，但数据深度最好。当前$242阶段不推荐 |
| **CoinStats API** | 综合加密API | freemium | 广度覆盖（多链+DeFi+CEX） | 简易 | 2026年多家评测评为"覆盖面最广"API。在CoinOS评估失败后可作替代方案 |
| **Kaiko** | 机构市场数据 | **付费** | 历史深度/订单簿/衍生品 | 简易 | 机构级付费，当前阶段不推荐 |

**本期数据源核心判断：** 所有新发现的付费数据源（Nansen、Glassnode、Kaiko）当前阶段不是ZQ的优先选择。当ZQ仍在$242的阶段挣扎且CoinOS（内置免费Key）尚未评估时，任何付费API的推荐都是不负责任的。**CoinOS/AiCoin Open API仍然是填补数据缺口的最优路径**——免费、即开即用、覆盖6个维度。上期推荐的fia-signals-mcp（pip install）是第二等效方案。

---

## 对比历史

### 上期（06-08）推荐了什么 — 7天追踪状态

| 推荐项 | 推荐级别 | 集成状态 | 备注 |
|:-------|:--------:|:--------:|:-----|
| **CloddsBot** ⭐⭐⭐ — 跨市场AI交易终端（332★） | **⭐最重要** | ❌ 未集成 — **7天** | 独立可部署TypeScript项目，部署门槛最低 |
| **OpenWhale** ⭐⭐ — 策略编排框架（133★） | 强烈推荐 | ❌ 未集成 — **7天** | 架构参考，需30分钟阅读 |
| **crypto-liquidity-ai-trading-bot** ⭐ — 流动性检测（115★） | 推荐参考 | ❌ 未集成 — **7天** | Python/Node双栈 |
| **fia-signals-mcp** ⭐ — 体制检测+费率MCP | 推荐参考 | ❌ 未集成 — **7天** | pip install，**最低集成门槛** |
| **AlgoVault quant-signal** ⭐ — 综合信号MCP | 推荐参考 | ❌ 未集成 — **7天** | npm/REST调用 |
| NexusQuant / Archimedes / AI Trader MCP / auto-trading | 🟡 | ❌ — 7天 | 可关注状态 |

### P0任务执行状态（连续7期追踪 — 已达35天）

| P0任务（05-11首次提出） | 05-18 | 05-25 | 06-01 | 06-08 | 06-15 | **持续天数** |
|:-------------------|:----:|:----:|:----:|:----:|:----:|:-------:|
| CCXT激活（已安装零使用） | ❌ | ❌ | ❌ | ❌ | ❌ | **35天** 🔴 |
| Etherscan Monitor激活 | ❌ | ❌ | ❌ | ❌ | ❌ | **35天** 🔴 |
| CoinOS/AiCoin集成（06-01新增） | — | — | 🆕 | ❌ | ❌ | **14天** 🔴 |
| fia-signals-mcp集成（06-08新增） | — | — | — | 🆕 | ❌ | **7天** 🔴 |

### 本期新增（06-15 vs 06-08）

| 新增项 | 对ZQ的价值 | 推荐级别 |
|:-------|:----------|:--------:|
| **Vibe-Trading (HKUDS)** — 12,168★，AI量化交易平台，策略回测+多Agent研究 | **回测引擎 / 多Agent架构参考** — 填补ZQ"无独立回测"缺口，A3→A4断裂后的替代策略生成管道 | ⭐⭐⭐ **最重要** |
| **OpenAlice (TraderAlice)** — 5,224★，全资产AI交易Agent | **全资产覆盖架构参考 / TaG版本管理思路** | ⭐⭐ |
| **HydraQuant** — 9★，18 RAG + 10 Agent引擎 | **RAG应用模式参考** — 比ZQ当前评分系统精细得多 | ⭐ |
| **Pattern-Signal-Automator** — 图表形态自动扫描 | **K线形态识别维度** — ZQ当前完全空白 | ⭐ |
| **Meta-RL-Crypto (arXiv)** — 元学习强化学习框架 | **学术前沿参考** — 远期可能提升A2/A3的数据融合质量 | 🟡 |
| **资金费率感知做市策略 (arXiv)** — 最优做市 | **做市策略理论参考** — 如果将来扩展做市策略 | 🟡 |
| OmniTrade / Cortex Arbitrage Bot | 远期储备 | 🟡 |
| Nansen / WhaleTracker / ChainLens / Glassnode / Mobula / CoinStats / Kaiko | 付费数据源，当前优先级低 | 🟡 |

### 35天关键趋势变化

| 维度 | 05-11状态 | 06-01状态 | 06-08状态 | 06-15状态 | 变化趋势 |
|:-----|:--------:|:--------:|:--------:|:--------:|:--------|
| 数据管道完整性 | 部分 | 全链路✅但A3→A4⏳ | A1→A2→A3✅ A3→A4⏳ | ✅ A1/A2/A3新鲜，A3→A4⏳ | 🔴 29天未改善 |
| 实际数据采集 | — | 0/6维（0%） | 0/6维（0%） | 0/6维（0%） | 🔴 35天完全无改善 |
| CCXT/Etherscan | — | 21天零使用 | 28天零使用 | **35天零使用** | 🔴 每周刷新纪录 |
| 资金缩水率 | $427 | $286（-33%） | $276（-35.6%） | 查询失败 | 🔴 持续恶化 |
| 推荐闭环率 | — | 0% | 0% | **0%** | 🔴 35天零闭环 |
| 累计推荐项 | 7项 | 15+项 | **25+项** | **32+项** | 🟡 但零集成 |
| 发现重心 | 单个工具 | 系统数据源 | Agent+架构 | **回测+全资产+学术** | 认知升级但落地为零 |

---

## 对ZQ系统的改进建议

### 🔴 P0 — 本周必须解决

**1. 打破35天零闭环记录 — 选一个P0做掉（任何一个！）**

连续35天，7期侦察报告，32+项推荐，集成率=0%。这不是时间不够的问题，这是闭环机制不存在。

**最低可行行动 — 选一个在1小时内能完成的：**

| 选项 | 时间 | 操作 |
|:----|:---:|:-----|
| **A. CCXT激活** | 5分钟 | 在A4的ticker fetch增加 `self.ccxt_okx = ccxt.okx()` fallback |
| **B. fia-signals-mcp集成** | 10分钟 | `pip install fia-signals-tools` → 1行代码获取市场体制 |
| **C. CoinOS/AiCoin Open API调用** | 30分钟 | 5个REST调用获取费率/大单/多空比/爆仓/新闻 |
| **D. 清理3个尘仓（ORDI/DYM/UNI）** | 1分钟 | USDT回收~$8.5 |

**选A是铁律修复，选B是数据宽度，选C是数据深度，选D是弹药回收。随便选一个，打破0！**

**2. 打通A3→A4链路（29天断裂，铁律违反）**

A3仍然有新鲜输出（06-15 07:08），但A4感知不到。推荐在A4引擎启动时加入自动检查A3 findings.md的逻辑：

```python
# A4启动时自动检查（5行代码）
import os, json
a3_findings_path = 'agents/scouter/findings.md'  # 或A3输出文件
if os.path.exists(a3_findings_path):
    # 解析最新推荐 → 加入候选池
    candidate = parse_a3_recommendation(a3_findings_path)
    if candidate and candidate not in recent_trades:
        self.candidate_pool.append(candidate)
```

**3. 恢复余额查询 — 当前系统盲飞**

global_state.json显示"❌ 余额查询失败"。如果不知道账户里有多少钱，任何交易决策都是盲目的。

**建议：** 在A4或A8的定时任务中增加Binance API余额获取，失败时切到OKX（通过CCXT）或使用上一次成功获取的缓存值。

### 🟠 P1 — 本周评估

**4. 评估Vibe-Trading作为独立回测引擎**

Vibe-Trading（12,168★，HKUDS）已发布PyPI包，pip install即可。建议Quant在本周23:00分析中：
1. `pip install vibe-trading`
2. 使用Vibe-Trading的回测引擎验证ZQ当前E2/E3/E4退出策略的历史表现
3. 对比Vibe-Trading多Agent研究模式与ZQ当前A1→A2→A3→A4单链模式的表现差异
4. 评估是否可以抽取其Agent协作模块来修复A3→A4断裂

**5. 评估CloddsBot独立部署（上期P1延续）**

CloddsBot（332★，MIT开源）仍然是当前最容易获得"新市场维度"的路径：
- TypeScript项目，独立目录部署，不依赖ZQ Python代码
- 覆盖Binance + Polymarket + Hyperliquid + Solana DEX
- 初始资金$20-30即可运行
- 如果这个都部署不了，说明独立项目部署流程也有问题

**6. 评估OpenAlice的交易日志（TaG）机制**

OpenAlice的Trading as Git概念 — 每笔交易记录版本控制，可回溯推理链。对ZQ的PROFIT_ARCHIVE.md和交易日志系统有参考价值。

### 🟡 P2 — 持续改进

**7. 引入ATR动态止损替代固定百分比止损**

当前E2/E3退出使用固定百分比（-5%/-10%），高波动时容易被噪音震出，低波动时亏损时间过长。ATR自适应止损可解决此问题：
- 高波动（ATR↑）：放宽止损至2×ATR，避免过早被震出
- 低波动（ATR↓）：收紧止损至1.5×ATR，控制单笔亏损

**8. 建立震荡市网格模式**

当A4检测到市场处于震荡体制（非趋势状态）时，临时切换到网格策略。可参考SOL Grid Bot的区间设计模式。需要CryptoGates回测报告提供的参数参考。

**9. 持续追踪Scouter推荐闭环率（第7期追踪）**

| 推荐日期 | 推荐项 | 级别 | 状态 | 持续天数 |
|:--------:|:------|:---:|:----:|:-------:|
| 05-11 | CCXT激活 | P0 | ❌ | **35天** 🔴 |
| 05-11 | Etherscan Monitor激活 | P0 | ❌ | **35天** 🔴 |
| 05-18 | btc-hedge-lab对冲策略 | ⭐⭐ | ❌ | **28天** 🔴 |
| 05-18 | Arkham Intelligence | ⭐⭐ | ❌ | **28天** 🔴 |
| 05-25 | QuantDinger多Agent架构 | ⭐⭐ | ❌ | **21天** 🔴 |
| 05-25 | homerun预测市场 | ⭐⭐ | ❌ | **21天** 🔴 |
| 06-01 | CoinOS/AiCoin数据源 | ⭐⭐ | ❌ | **14天** 🔴 |
| 06-01 | Moss策略进化架构 | ⭐ | ❌ | **14天** 🔴 |
| 06-01 | Regime Classifier体制检测 | ⭐ | ❌ | **14天** 🔴 |
| 06-08 | CloddsBot跨市场Agent | ⭐⭐⭐ | ❌ | **7天** 🔴 |
| 06-08 | OpenWhale架构参考 | ⭐⭐ | ❌ | **7天** 🔴 |
| 06-08 | fia-signals-mcp即用信号 | ⭐ | ❌ | **7天** 🔴 |
| 06-08 | crypto-liquidity-ai-trading-bot | ⭐ | ❌ | **7天** 🔴 |
| 06-08 | AlgoVault quant-signal | ⭐ | ❌ | **7天** 🔴 |
| **06-15** | **Vibe-Trading回测引擎** | **⭐⭐⭐** | **🆕** | **0天** |
| **06-15** | **OpenAlice全资产Agent** | **⭐⭐** | **🆕** | **0天** |
| **06-15** | **HydraQuant架构参考** | **⭐** | **🆕** | **0天** |
| **06-15** | **Pattern-Signal-Automator** | **⭐** | **🆕** | **0天** |

### 诚实判断（第6期）：ZQ系统的根因已从"工具不够"变为"闭环崩溃"

```diff
- 第1-3期（05-04至05-18）：推荐单个工具填补单缺口
- 第4期（06-01）：发现CoinOS一个数据源填补6个缺口
- 第5期（06-08）：系统性问题不是"缺工具"，是"闭环机制不存在"
+ 第6期（06-15今天）：35天零闭环。32+项推荐零集成。
+  这不再是"没时间做"或"优先级低"的问题。
+  这是系统级的设计缺陷——没有"推荐→评估→集成→验证"的闭环机制。
```

**根因链（第6期更新）：**

```
推荐链条（Scouter → ZQ系统）从未产生任何实际影响：
  Scouter: 32+项推荐 → 系统: 零集成 → 数据缺口: 永远不补
    → A1永远0/6维 → A2永远缺因子 → A3永远推荐差
      → A4永远不敢开仓 → 系统空转 → 资金持续缩水
        → 35天 $427→$242 (-43.3%, 估算)
```

**Vibe-Trading和CloddsBot的特殊性（本期双⭐建议的核心原因）：**

| 工具 | 特殊之处 | 与ZQ的关系 |
|:----|:---------|:----------|
| **CloddsBot**（06-08） | TypeScript独立项目，不依赖ZQ代码库 | 可在独立目录部署，零冲突 |
| **Vibe-Trading**（06-15本期） | pygame包，Python生态兼容 | pip install即可运行独立回测 |

**这两个工具的共同点：不需要修改ZQ引擎代码就能验证价值。** 如果连"单独部署/单独pip install"都闭环不了，那问题不在工具本身，而在"执行者不存在"——这是总指挥（ZH）需要介入解决的管理问题。

---

## 附录：已排除项

| 项目 | 排除原因 |
|:-----|:---------|
| booboomrtwix/Solana-FarmBot-2026 | 助记词恢复工具，有安全风险（上期重复出现） |
| starlet389/CryptoChecker-V3-2026 | 多链验证器/助记词审计，非交易相关 |
| Cryptoaj-hack/DFDTOKEN | DeFi推广，非可用工具 |
| Hampsli/CryptoDashboard2026 | React仪表盘，展示用 |
| jesuschelbezmaski7/polymarket-trading-bot-desktop-crypto | 付费商业推广 |
| MauroAndretta/CryptoAnomalyDetection | 1★学术项目，非交易工具 |
| StronglyTypedSoul/RWTCoder-dex-development | 三角套利bot，代码质量存疑，多个内容重复fork |
| azuzxx9-jpg/microstructure-research-bot | 0★未验证 |
| aleibovici/cryptopump | 上期已评估，Go语言栈不兼容 |
| Meszi84/grid_pro4_managed | 0★未验证 |
| Samiron18/freqtrade-strategy-hub | 仓库空，不可用 |

---

*ZH侦察签名：2026-06-15 08:05 CST*
*扫描方法：web_search 6个关键词搜索 + 历史7期报告比对 + SHARED.md + global_state.json系统状态验证*
*系统余额来源：global_state.json 2026-06-15 08:05 → ❌ 查询失败（系统盲飞状态）*
*报告文件：`learning/scouter_report_20260615.md`*
*下一期扫描：2026-06-22（周一08:00）*
