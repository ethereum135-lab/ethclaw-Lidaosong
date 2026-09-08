# ZH侦察报告（为ZQ系统）— 2026-08-24 00:30

> **侦察视角：** ZH总控的独立侦察兵（不自称ZQ-Scouter）
> **扫描时间：** 2026-08-24 00:30 CST（周一例行全网扫描 — 第14期）
> **上次报告：** 2026-08-17（第13期）
> **方法：** 6维泛化关键词 × GitHub API 5类搜索+15仓库实时验证 × README深度提取（OpenAlice/Binance Skills Hub/Kraken CLI/VectorBT Skills）× 系统内闭环状态物理核查
> **来源说明：** 所有星数为GitHub API 2026-08-24 00:2x CST实时查询[来源：GitHub API]；系统余额为Binance API物理直查[来源：Binance API 2026-08-24 00:20 CST，fetch_real_balance.py]
> **诚实声明：** quantt.co.uk / altfins.com / sonartracker.io 三个深度页面被本环境网络拦截（返回"Blocked: private network address"，属环境问题非网站问题），仅按搜索摘要级引用并标注，未做深度提取。

---

## 执行摘要

本期最大的发现不是某个工具，而是一个**行业结构性变化：交易所官方下场做"Agent原生交易界面"**。Binance官方发布Skills Hub（★977），其中**binance-trading-signal技能提供官方Smart Money链上信号（钱包买卖事件+收益/退出率数据+策略回测）**——这是13期以来第一个**免费、官方、Agent原生**的"链上聪明钱"方案，直接填上ZQ从第1期就挂账的A1 6维数据缺口（此前Nansen/Arkham/Glassnode全为付费商业平台）。

同时，**系统资金三周来首次回升**：$213.54 → **$233.93（+9.5%）**。但**闭环病灶仍在加深**：coinos接入P0连续第3期未执行；更严重的是**Quant报告管道自06-17停更2个月+**——reports/目录最新文件停留在6月，Commander的决策输入链本身断了。

### 本期三大发现

| 发现 | 级别 | 说明 |
|:-----|:----:|:-----|
| **Binance官方Skills Hub（★977）含Smart Money链上信号技能** | 🟢 重大 | 官方免费"链上聪明钱"数据+信号策略管理+回测，Agent原生（SKILL.md格式，Hermes/OpenClaw生态兼容）。13期未解的链上缺口出现官方解 |
| **OpenAlice（★6,665/6个月）"Trading as Git"审批门控执行** | 🟢 架构 | 把交易执行变成 git 式 stage→commit→review→push，下单必须过审批门——正是ZQ Blade+FK风控缺的工程化范式 |
| **资金回升但闭环病灶加深** | 🔴 P0 | 总权益$233.93（+9.5%）[来源：Binance API 2026-08-24 00:20 CST]；coinos P0第3期未执行；Quant报告管道停更2个月+ |

### 系统实时状态（物理验证）

- **总权益：$233.93**[来源：Binance API 2026-08-24 00:20 CST 物理直查]（USDT现金 $99.43 + 持仓约 $134.50）
- 资金轨迹：07-13 $228.76 → 08-10 $220.63 → 08-17 $213.54 → **08-24 $233.93**（+9.5%/周，**三周来首次上升**）
- 现金占比42.5%（$99.43/$233.93）——弹药仍充足
- 本期持仓（>$1）：ZEC $35.19、MORPHO $17.16、WLD $16.74、HBAR $16.71、PEPE $16.57、ETH $14.40、MOVR $4.10、OPEN $3.82、NFP $1.25
- **持仓结构变化**：ETH从$49.58降至$14.40（减仓）；ALICE/ROBO/LINK出清；MORPHO/WLD/HBAR/PEPE新进；**ZEC回归**（$35.19，占15%——集中度风险重现但远低于07-13的80%单仓）
- **Blade执行链存活**：TRADES.md今日06:08更新，a4_input_summary.md今日07:58更新[来源：文件mtime 2026-08-24]

---

## 新工具发现

### ⭐⭐⭐ binance/binance-skills-hub（Binance官方AI Agent技能市场 — 本期最重要发现）

| 字段 | 值 |
|:-----|:----|
| 平台 | `binance/binance-skills-hub`（GitHub） |
| 免费/付费 | **开源（官方）**，技能MIT |
| 星数 | **★977**（2026-03-03创建，最后推送2026-08-18）[来源：GitHub API 2026-08-24] |
| 语言 | SKILL.md技能包（YAML frontmatter + 指令），依赖binance-cli / baw (Node) |
| 描述 | 官方技能市场：**binance**（binance-cli操作现货/合约USD-S/Convert，需API key）、fiat/p2p/payment/onchain-pay/square-post；**binance-web3**：binance-trading-signal（**Smart Money信号**：钱包买卖事件+收益/退出率+自定义信号策略+回测+日报/月报+KOL持仓）、binance-wallet-tracker、crypto-market-rank、meme-rush、query-token-audit、query-token-info、binance-agentic-wallet、binance-leaderboard等12个Web3技能 |
| 推荐理由 | ①**binance-trading-signal = 官方免费链上聪明钱**：ZQ第1~13期反复标注"链上聪明钱无免费API方案"（Nansen/Arkham/Glassnode均付费）——这是官方自带的Smart Money数据，直接补上A1 6维缺口第4维；②SKILL.md格式与ZQ的Hermes技能生态同构，`npx skills add`一条命令安装；③官方binance-cli可作A1/Blade的Binance操作层（替代自维护REST封装） |
| 弥补缺口 | **链上聪明钱维度（A1第4维）+ 执行层官方化 + 信号策略回测** |
| 集成难度 | 低（Node.js 22+，`npx skills add https://github.com/binance/binance-skills-hub`；binance-cli为单二进制） |
| URL | https://github.com/binance/binance-skills-hub |

**对ZQ的特别价值：** ①Smart Money信号（每日/每月回测报告、maxGain排序、golden/silver/bronze命中率）与A8资金官形成"官方信号 vs 自家扫描"双工具交叉——正好落实08-10期提出的鲸鱼标签纪律（≥2类工具交叉验证）；②若接入binance技能，coinos（★52，停滞）可归档——但**先接一个再删另一个**（铁律九）。诚实提示：Web3钱包追踪大概率限于BSC/Solana及Binance自有追踪钱包集，覆盖面需实测，但作为免费起点远优于零。

---

### ⭐⭐ TraderAlice/OpenAlice（"Trading as Git" — 执行审批门控架构蓝本）

| 字段 | 值 |
|:-----|:----|
| 平台 | `TraderAlice/OpenAlice`（GitHub） |
| 免费/付费 | 开源（AGPL-3.0） |
| 星数 | **★6,665**（2026-02-18创建，最后推送2026-08-23，6个月从0到6.6K）[来源：GitHub API 2026-08-24] |
| 语言 | TypeScript（桌面应用+本地Runtime+Docker部署） |
| 描述 | "Your one-person Wall Street"——把交易工作映射成编码Agent已懂的工具：Workspaces（每任务一个git仓库+终端）、Issues（markdown任务卡）、Tracked Entities（记忆图）、Inbox（报告投递）、Market Tools（行情/新闻/基本面/技术指标CLI）、**Unified Trading Account**（Alpaca/IBKR/Longbridge/CCXT统一账户抽象）、**Trading as Git**（账户操作先stage→commit→review→push，审批门控后才会真正下单） |
| 推荐理由 | 它的**审批门控执行**正是ZQ Blade直连下单缺的工程化风险层：ZQ现在Blade执行→FK事后检查，OpenAlice是"操作必须先过审批门才能push"——把风控从"检查"升级为"门禁"。同时其Issues+Inbox模式就是ZQ"共享文件协作"的产品化形态 |
| 弥补缺口 | **执行风控架构层**（设计参考，非直接集成——TypeScript桌面应用与ZQ Python栈不兼容） |
| 集成难度 | 参考级（不集成代码；借鉴"审批门控"模式，~50行在Blade加pre-trade审批检查） |
| URL | https://github.com/TraderAlice/OpenAlice |

**对ZQ的特别价值：** ①"Trading as Git"三问可直接落地为Blade下单前检查：这笔交易stage了吗（有记录）？review了吗（FK风控签名）？push了吗（执行确认）？②AGPL许可注意：仅作设计参考，不复制代码。

---

### ⭐⭐ marketcalls/vectorbt-backtesting-skills（VectorBT回测技能包 — Quant工具链候选）

| 字段 | 值 |
|:-----|:----|
| 平台 | `marketcalls/vectorbt-backtesting-skills`（GitHub） |
| 免费/付费 | 开源 |
| 星数 | **★197**（2026-02-25创建，最后推送2026-07-12）[来源：GitHub API 2026-08-24] |
| 语言 | Python（VectorBT），经skills.sh支持40+编码Agent |
| 描述 | 回测技能集：`/setup`（环境一键装）、`/backtest`（生成完整回测脚本：信号+市场特定费率+基准对比+OpenStatz tearsheet+纯文本报告）、`/optimize`（参数网格搜索+Plotly热力图+最优参数vs基准）、`/quick-stats`、`/strategy-compare`（多策略并排对比）。**Crypto市场数据走yfinance/CCXT，现货+永续maker/taker费率建模**，12个预置策略模板（EMA/RSI/Donchian/Supertrend/MACD等），含robustness testing |
| 推荐理由 | 上期推荐的Sami001回测器（★5）是"零依赖单文件"，这个（★197）是**带完整工作流的技能包**：/backtest与/optimize直接对应Quant校准E2/止损参数的需求，且SKILL.md技能格式与ZQ的Hermes Agent技能生态同构，可直接`npx skills add marketcalls/vectorbt-backtesting-skills` |
| 弥补缺口 | **策略验证层**（Quant回测工具链）— 与Sami001（TV平价校验）互补：Sami001验证"回测引擎可信"，vectorbt-skills提供"工作流+参数优化" |
| 集成难度 | 低（技能包安装；VectorBT pip install） |
| URL | https://github.com/marketcalls/vectorbt-backtesting-skills |

---

### 🟡 krakenfx/kraken-cli（★693 — 多平台验证候选，官方AI原生CLI）

| 字段 | 值 |
|:-----|:----|
| 平台 | `krakenfx/kraken-cli`（GitHub，Kraken官方） |
| 免费/付费 | 开源（MIT） |
| 星数 | **★693**（2026-03-06创建，最后推送2026-08-07）[来源：GitHub API 2026-08-24] |
| 语言 | Rust（单二进制，macOS/Linux） |
| 描述 | 官方AI原生CLI：完整Kraken API访问、**内置MCP server**（Claude/Codex/Cursor等直接调用）、模拟盘/实盘、现货+衍生品+xStocks。可对话式操作："Open a 10x leveraged long on BTC futures paper with $5,000 collateral. Set trailing stop at 3%" |
| 推荐理由 | 填补**多平台验证**维度：ZQ选币库目前单Binance源，Kraken CLI免费提供第二交易所价格/深度对照（防单所操纵），且MCP server意味着A2选币官可自然语言查询 |
| 弥补缺口 | 多平台验证维度（远期） |
| 集成难度 | 低（单二进制安装；接入价值需先确认ZQ是否需要第二交易所） |
| URL | https://github.com/krakenfx/kraken-cli |

---

### 🟡 其他值得跟踪（本期新发现，观望）

| 项目 | 星数 | 说明 | 观望原因 |
|:-----|:----:|:-----|:---------|
| **pineforge-4pass/pineforge-engine** | ★175 | C++确定性PineScript v6回测运行时，**逐笔对照TradingView验证**（与上期Sami001同赛道但更活跃，推送至08-23） | 与Sami001二选一即可；C++非Python |
| **bwjoke/BTC-Trading-Since-2020** | ★1,212 | 2020年以来公开BTC交易上下文数据集（6年真实决策记录） | 数据源价值待评估——可能是公开交易日志语料，对A3牛币官叙事学习有用 |
| **alsk1992/CloddsBot** | ★738 | 开源AI交易Agent，1000+市场自主运行（TypeScript） | 架构参考级；06-26后未推送 |
| **richkuo/go-trader** | ★342 | Go交易机器人：回测/模拟/实盘+风控，推送至08-23活跃 | Go语言，与Python栈不兼容 |
| **Co-Messi/HyperData-Terminal** | ★14 | 开源交易终端：订单流+鲸鱼追踪+清算级联（Hyperliquid/Binance） | 概念好但早期；与A8重叠 |
| **PVinh-Quant/Kairos-v2** | ★32 | Python开源量化研究框架（2026-06创建，活跃） | 早期，观察其成熟度 |
| **Aliipou/mm-live** | ★5 | 事件驱动做市：Binance WebSocket+Kalman+订单簿不平衡公平价 | 做市维度（P2网格）参考，★5太早期 |
| **tfrmma/game-theory-trading-strats** | ★10 | Hyperliquid MFT/HFT做市套件（SAC/PPO RL Agent） | 同做市维度，早期 |

---

## 新策略发现

### 1. Binance Smart Money信号策略管理（官方链上信号+自定义策略回测 — 本期策略层最重要发现）

来自binance-skills-hub的binance-trading-signal技能（v3.3），三个信号源：**smart money（钱包买卖事件）**、平台策略、用户自定义策略（meme/fomo）。四个场景域：日报/月报回测复盘（BSC vs Solana、协议对比）、信号发现（按maxGain或多策略命中排序、token可买性判断）、分析（黄金/白银/青铜命中率、KOL持仓/流动性/协议影响因子）、策略管理（创建/删除/启用/调度回测/自动扫描/从策略大厅复制）。

**对ZQ的价值：** ①这是"策略+数据+回测"一体的官方方案——A3牛币官可用其maxGain排序交叉验证自己的精推；②其"信号必须带回测复盘（golden/silver/bronze率）"的模式，正是ZQ铁律"推荐了没验证=白推荐"的官方实现；③与A8资金官形成官方vs自研双源交叉。

### 2. OpenAlice "Trading as Git" 执行审批范式（给Blade/FK的工程化风控）

交易操作四步：**stage（记录意图）→ commit（固化参数）→ review（人工/风控审批）→ push（真正下单）**。对比ZQ现状：Blade下单→FK事后35分钟检查。建议范式升级：下单前必须过FK审批门（pre-trade gate），把"检查"变"门禁"。

### 3. 做市研究方向进入平台期（确认，无新增量）

本期market making搜索命中：DWF Labs四策略（2024旧文）、Bookmap（2024）、quantt.co.uk 2026综述（被网络拦截未深度提取，仅摘要级）、crypticweb3服务商清单——**无新论文级突破**，与上期判断一致（上期已报Microstructure Lab/arXiv 2607.11888/HRL-GridMM）。HRL-GridMM（上期，Sharpe 3.38）仍是"震荡市网格"P2的最强背书，本期无更新。

### 4. altFINS 26个AI检测图表形态库（信号形态参考）

altFINS整理26个图表形态×4时间框架（15m/1h/4h/1d），称最可靠为**倒头肩（84%成功率）**、头肩等[来源：搜索摘要，页面被拦截未深度提取]。可作为A3牛币官信号形态的第三方校验清单（与ZQ现有E2/趋势信号独立验证）。

---

## 新数据源发现

| 数据源 | 类型 | 免费/付费 | 填补缺口 | 集成难度 |
|:-------|:-----|:---------:|:---------|:--------:|
| **Binance Web3 Smart Money信号**（binance-skills-hub技能，官方） | 钱包买卖事件+收益/退出率+KOL持仓+策略回测 | ✅ **免费官方** | **链上聪明钱维度（A1第4维）— 13期首次出现免费方案** | 低（Node 18+，baw CLI） |
| **bwjoke/BTC-Trading-Since-2020** | 6年公开BTC交易上下文数据集 | ✅ 免费 | 叙事/交易日志语料（A3牛币官学习用） | 中（需评估数据格式） |
| **altFINS免费API** | 预计算技术指标+交易信号（免费层） | ✅ 免费 | 技术指标第三方校验（A2选币官） | 低（REST） |
| **Kraken CLI行情**（krakenfx官方） | 第二交易所实时价格/深度 | ✅ 免费 | 多平台验证维度 | 低（单二进制） |

**链上聪明钱缺口现状（第14期重大更新）：** 第1~13期持续标注"Nansen/Arkham/Glassnode/CryptoQuant免费层有限，无免费API方案"。**本期Binance官方Smart Money信号出现，缺口有解**——虽覆盖面（BSC/Solana/自有追踪钱包）需实测，但这是官方免费起点，优先级高于一切商业平台。Swiss Whale Intelligence（上期，BTC网页源无API）维持暂缓。

---

## 对比历史

### 上期（08-17）P0建议 — 7天追踪状态（物理核查）

| 推荐项 | 级别 | 08-17→08-24 | 真实状态（本期核查） |
|:-------|:--------:|:-----------:|:-----|
| **coinos接入A1**（30分钟动作） | 🔴 P0 | — | ❌ **未执行，连续第3期**。coinos仍仅被tools/agent_tool_audit.py引用，主链路零调用；TOOL_LOG.md文件已不存在（上期还说"自05-17无新增"，本期文件整体消失） |
| **Quant模板加"诚实模拟"4条纪律** | 🔴 P0 | — | ❌ 未采纳。全系统grep无"诚实模拟/nhocconan/Sami001"引用（排除报告自身） |
| **Sami001回测器P1评估** | 🟠 P1 | — | ❌ 无证据 |
| **余额与持仓确认** | 🔴 P0 | — | ✅ 已执行：$233.93，见执行摘要 |
| **HRL-GridMM论文精读→网格设计** | 🟠 P1 | — | ❌ 无证据 |
| **MCP统一数据层评估** | 🟠 P1 | — | ❌ 无证据（但本期kraken-cli/binance-cli进一步证明MCP化是标配） |

**🔴 新增重大病灶：Quant报告管道停更2个月+。** reports/目录最新文件为2026-06-17（deep_learning_2026-06-17.md、ZH_review_2026-06-16.md），此后无任何Quant分析产出。这不是"工具没接"——是**Commander的决策输入链本身断了**。比coinos零调用更根本。

### 已追踪项目星数（08-17 → 08-24，7天）[来源：GitHub API 2026-08-24 00:2x CST]

| 项目 | 08-17 | 08-24 | 变化 | 备注 |
|:----|:----:|:----:|:----:|:----|
| **HKUDS/Vibe-Trading** | ★31,041 | **★31,562** | +521 (+1.7%) | 增速持续放缓（+9.4%→+1.9%→+1.7%），观察是否见顶 |
| HKUDS/AI-Trader | ★21,430 | ★21,510 | +80 (+0.4%) | 平稳 |
| OpenByteInc/QuantDinger | ★10,745 | **★11,011** | +266 (+2.5%) | 稳定增长，突破11K |
| Drakkar-Software/OctoBot | ★6,414 | ★6,457 | +43 (+1.3%) | 稳定 |
| nkaz001/hftbacktest | ★4,368 | ★4,439 | +71 (+1.6%) | 微加速 |
| mnemox-ai/tradememory-protocol | ~1,408 | ★1,412 | +4 | 稳定 |
| GMGNAI/gmgn-skills | ~431 | ★468 | +37 (+8.6%) | 持续增长（Solana memecoin情报） |
| aicoincom/coinos-skills | ★52 | ★52 | 0 | 停滞 |
| alltick | ~597 | ★601 | +4 | 平稳 |
| **hackobi/AI-Scalpel** | ★454 | **GitHub 404** 🔴 | — | **仓库消失**（删除/改名/私有化），从追踪列表移除 |
| **TraderAlice/OpenAlice** | — | **★6,665** | 🆕 | 本期新发现（6个月6.6K星） |
| **binance/binance-skills-hub** | — | **★977** | 🆕 | 本期新发现 |
| **krakenfx/kraken-cli** | — | **★693** | 🆕 | 本期新发现 |
| **marketcalls/vectorbt-backtesting-skills** | — | **★197** | 🆕 | 本期新发现 |

**关键观察：** ①Vibe-Trading连续两期增速放缓（+1.9%→+1.7%），"自然语言→策略"赛道热度确认进入平台期；②本期新发现全部指向**"Agent原生交易基础设施"**（官方CLI/技能市场/审批门控）——2026年下半年的竞争从"策略"转向"Agent与交易所的接口层"；③AI-Scalpel仓库消失提醒：追踪列表需定期清理，工具生态淘汰在加速。

### 系统资金轨迹（实测）

| 日期 | 总权益 | 现金 | 来源 |
|:----:|:------:|:----:|:-----|
| 07-13 | $228.76 | ? | 上期报告（未独立验证） |
| 08-10 | $220.63 | $96.79 | Binance API 2026-08-10 00:50 CST |
| 08-17 | $213.54 | $99.24 | Binance API 2026-08-17 00:27 CST |
| **08-24** | **$233.93** | **$99.43** | **Binance API 2026-08-24 00:20 CST 物理直查** |

**诚实判断：** +9.5%是三周来首次上升，且现金占比仍42.5%——说明盈利来自持仓浮盈（ZEC $35.19回归+新仓MORPHO/WLD/HBAR/PEPE），而非结构性机制改善。**一次回升不改变"工具就位≠接入"的结论：Quant管道断了2个月、coinos P0拖了3期，而本期Binance官方把"链上聪明钱"直接端到Agent嘴边。**

---

## 对ZQ系统的改进建议

### 🔴 P0 — 本周必须解决

**1. 打破使用级零闭环 — 第3期重复，但本期给出第二条（更好的）路**

- **路线A（原方案）**：coinos资金费率接入A1（30分钟）——`python3 -c "from tools.coinos_client import coinos; print(coinos.futures_interest('btcusdt:binance'))"`
- **路线B（本期新发现，推荐评估）**：**binance-skills-hub官方技能**——binance-cli现货/合约+binance-trading-signal Smart Money一条龙，官方维护、Agent原生、覆盖维度更广（费率/信号/回测全有）。若选B，coinos按铁律九归档（先接后删）。
- **无论A/B，本周必须产出第一份真实数据文件。** 这仍是全系统当前唯一最重要的事——第14期了。

**2. 恢复Quant报告管道（比工具接入更根本）**

reports/停更于06-17（2个月+），Commander的决策输入链已断。要求Quant立即恢复每日23:00产出，并采用本期vectorbt-backtesting-skills的`/backtest`+`/optimize`命令对E2/止损做首次参数校准（对照Anny OOS基准+Sami001 TV平价回测器），报告模板加入08-17期"诚实模拟"4条纪律（无前视/t+1成交/成本必计/资金费率按方向）。

**3. 余额与持仓确认**

总权益$233.93、现金$99.43（42.5%）[来源：Binance API 2026-08-24 00:20 CST]。ZEC回归至15%（$35.19）——建议Quant评估ZEC集中度风险（07-13单仓80%巨亏的历史重演风险）；同时分析本周+9.5%是浮盈还是机制改善。

### 🟠 P1 — 本周评估

**4. binance-trading-signal技能试点**：安装binance-skills-hub，用Smart Money信号与A8资金官交叉验证（落实08-10期"鲸鱼标签纪律"≥2工具交叉）。实测其钱包覆盖面（BSC/Solana？）后决定是否作为A1第4维正式数据源。

**5. OpenAlice"审批门控"落地Blade**：借鉴Trading as Git模式，Blade下单前加FK pre-trade审批门（stage→review→push三步检查），把风控从"事后35分钟检查"升级为"事前门禁"。~50行改动。

**6. VectorBT技能包接入Quant工作流**：`npx skills add marketcalls/vectorbt-backtesting-skills`，作为Sami001的互补（工作流+参数优化 vs TV平价校验）。

### 🟡 P2 — 持续改进

**7. 震荡市网格**（06-15起第11期）：HRL-GridMM背书仍在，但优先级低于P0/P1——先恢复管道和闭环再说新策略。
**8. kraken-cli多平台验证**：评估Kraken作为第二价格源的价值（免费，单二进制）。
**9. 追踪口径更新**：AI-Scalpel从追踪列表移除（404）；TOOL_LOG.md已消失需在审计中说明；Vibe-Trading增速观察（连续放缓，可能见顶）。

### 持续追踪：推荐闭环率（第14期）

| 状态 | 数量 | 说明 |
|:-----|:----:|:-----|
| 文件级已安装 | ~10项 | freqtrade/coin_pool/coinos(含3策略模板)/a4_trend_checker等（05-07~05-17） |
| **使用级已接入** | **0项** 🔴 | 主数据管道零调用——第3期（连续） |
| 累计推荐工具 | 95+项 | 14期累计 |
| **Quant报告管道** | **停更2个月+** 🔴 | reports/最新文件2026-06-17 |

---

## 附录：已排除项

| 项目 | 排除原因 |
|:-----|:---------|
| coinquant.ai / bravosresearch / coinbureau / YouTube"回测1000次" | 新手向策略清单文/视频，无新量化内容，与上期同源营销文 |
| CoinMarketCap / CoinAPI / Kaiko / Amberdata / Tardis.dev | 均已追踪过；企业级付费或免费层不足，CoinAPI已在P1评估中 |
| DWF Labs四策略（2024）/ Bookmap / crypticweb3 / easyreadernews | 做市旧文/服务商清单，无数值可验证 |
| Nansen/Arkham/Glassnode类商业鲸鱼工具（bingx/cryptonews/spark.money清单） | 付费商业平台，且本期已有Binance官方免费方案 |
| swapperfinance/swapper-toolkit（★844） | JS/TS DeFi执行层，05-11已排除同款，与ZQ Python现货/合约栈不匹配 |
| braedonsaunders/homerun（★175）/ 0xrsydn/polymarket-crypto-toolkit / ddchack/sharkflow / yyq7903/auto-trading | Polymarket/Kalshi预测市场，与ZQ Binance现货/合约主战场无关 |
| Trade-With-Claude/cbt-framework（★62） | Claude Code专用回测框架，2月后未更新，非通用 |
| nirholas/modelcontextprotocol.name（★19） | MCP聚合索引，无自有数据，价值低于直接装binance/kraken官方技能 |

---

*ZH侦察签名：2026-08-24 00:30 CST*
*扫描方法：6维泛化关键词语义搜索 × GitHub API 5类搜索+15仓库实时验证 × README深度提取（4仓库）× 系统内闭环状态物理核查*
*关键数字来源：星数=GitHub API 2026-08-24 00:2x CST实时查询；余额=Binance API 2026-08-24 00:20 CST物理直查（fetch_real_balance.py）*
*未验证项：quantt.co.uk/altfins/sonartracker深度页面被环境拦截（仅搜索摘要级引用，已标注）*
*报告文件：`learning/scouter_report_20260824.md`*
*下一期扫描：2026-08-31（周一08:00）*
