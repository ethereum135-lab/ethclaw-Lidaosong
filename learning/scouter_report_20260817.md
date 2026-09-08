# ZH侦察报告（为ZQ系统）— 2026-08-17 01:00

> **侦察视角：** ZH总控的独立侦察兵（不自称ZQ-Scouter）
> **扫描时间：** 2026-08-17 01:00 CST（周一例行全网扫描 — 第13期）
> **上次报告：** 2026-08-10（第12期）
> **方法：** 6维泛化关键词 × GitHub API 12仓库实时验证 × 深度页面提取（AutoResearch回测引擎/Sami001 TV平价回测器/HRL-GridMM论文）× 系统内闭环状态物理核查
> **来源说明：** 所有星数为GitHub API 2026-08-17 00:20 CST实时查询[来源：GitHub API]；系统余额为Binance API物理直查[来源：Binance API 2026-08-17 00:27 CST]。

---

## 执行摘要

本期全网扫描发现 **2个值得评估的回测/策略自生成工具** + **1个做市RL框架（为9期未动的震荡市网格建议提供理论与实盘背书）**。本期最重要的不是新工具，而是**系统现状的物理核查**：上期P0（coinos接入A1）**仍未执行**，使用级零闭环进入第2期。

### 本期三大发现

| 发现 | 级别 | 说明 |
|:-----|:----:|:-----|
| **策略自生成+"诚实模拟"回测成2026主线** | 🟢 趋势 | nhocconan把Karpathy的autoresearch用于自主策略研究（★5/478次提交/47个CI测试）；Sami001做出TradingView全兼容平价回测器（★5/零依赖/115项TV平价校验）——"LLM生成策略→不可变引擎验证"模式从Vibe-Trading（★31,041）扩散到小项目 |
| **HRL-GridMM（分层RL网格做市）** | 🟢 策略 | 现货-合约delta中性网格做市：年化Sharpe 3.38 vs 手工网格2.89（+17%），Gate.io 10天实盘试点69K笔/672K USDT——为ZQ自06-15起连续9期未动的"震荡市网格"建议提供了理论+实盘双重背书 |
| **使用级零闭环进入第2期** | 🔴 P0 | 上期P0（coinos接入A1，30分钟动作）未执行：全系统coinos仅被agent_tool_audit.py引用，主链路零调用；TOOL_LOG.md自05-17后无任何新增行 |

### 系统实时状态（物理验证）

- **总权益：$213.54**[来源：Binance API 2026-08-17 00:27 CST]（USDT现金 $99.24 + 持仓约 $114.30）
- 资金轨迹：07-13 $228.76 → 08-10 $220.63 → **08-17 $213.54**（-3.2%/周，**连续两期下滑**）
- 现金占比46.5%（$99.24/$213.54）——弹药充足但未产生结构性盈利
- 本期主要持仓：ETH $49.58（08-10为$39.13，+27%）、ALICE $15.93、ROBO $15.69、LINK $15.25、MOVR $4.60
- **ZQ的A1 6维数据缺口（资金费率/多空比/大单异动/链上聪明钱/波动率/基本面排序）：工具已备（coinos等），接入仍为 0/6 维**

---

## 新工具发现

### ⭐⭐ nhocconan/AutoResearch-based-Trading-Strategy-Generation-and-Testing（策略自生成研究引擎 — 流程蓝本级）

| 字段 | 值 |
|:-----|:----|
| 平台 | `nhocconan/AutoResearch-based-Trading-Strategy-Generation-and-Testing`（GitHub） |
| 免费/付费 | 开源（MIT） |
| 星数 | **★5**（2026-03-20创建，478次提交，最后推送2026-06-12）[来源：GitHub API 2026-08-17] |
| 语言 | Python |
| 描述 | 用Karpathy的autoresearch做**自主交易策略研究**：LLM生成策略假设 → 不可变回测引擎验证 → 审计。核心是"诚实模拟"原则：信号在t根K线只能在**t+1成交**（无前视偏差）、高周期数据在K线收盘前不可见、往返成本必须实计、**资金费率按持仓方向计**。47个CI测试全部用合成OHLCV数据构建，保证引擎本身不可作弊 |
| 推荐理由 | 与Vibe-Trading（★31,041）"自然语言→策略"同赛道，但这个项目把**验证纪律**做到了极致——引擎不可变、评估不能自己放水。这正是ZQ Quant缺的：回测验证的防作弊清单 |
| 弥补缺口 | **策略验证纪律层** — Quant每日23:00分析的报告模板可直接采用其"诚实模拟"检查清单 |
| 集成难度 | 低（不集成代码，采纳方法论；若要跑其引擎~100行） |
| URL | https://github.com/nhocconan/AutoResearch-based-Trading-Strategy-Generation-and-Testing |

**对ZQ的特别价值：** ①其"信号t+1成交/跨周期不可见/费用必计/资金费率按方向"四条纪律可直接写进Quant报告模板；②不可变引擎+CI测试的理念，对应ZQ铁律八"三跑通三验证"的工程化实现。

---

### ⭐⭐ Sami001-OG/Crypto-Backtester-and-Strategy-Optimizer（TradingView平价回测器 — 最低门槛回测接入候选）

| 字段 | 值 |
|:-----|:----|
| 平台 | `Sami001-OG/Crypto-Backtester-and-Strategy-Optimizer`（GitHub） |
| 免费/付费 | 开源（无明确license标注，README称纯标准库） |
| 星数 | **★5**（2026-06-05创建，最后推送2026-07-15）[来源：GitHub API 2026-08-17] |
| 语言 | Python（**纯标准库，零pip依赖**，Python 3.7+） |
| 描述 | 复刻**TradingView策略测试器**的完整回测框架：TV券商模拟器的成交规则、等权仓位、bar内回撤、Performance Summary公式全部对齐（**115项手工计算的TV平价校验**）。含16个内置策略、并行网格搜索、**walk-forward验证**、自适应随机搜索、Binance Vision全历史数据管道 |
| 推荐理由 | ZQ第1期（05-11）就推荐过hftbacktest（现★4,368）做回测引擎，但那是Rust底层、封装300-500行。**这个项目纯Python零依赖**，TradeView平价意味着Pine Script策略移植后数字可直接对照TradingView验证——对ZQ来说是接入成本最低的回测选项 |
| 弥补缺口 | **策略验证层**（回测引擎）— 08-10期Anny策略库（30个OOS策略）作为"外部基准"，Sami001可作为"内部回测引擎"，两者配合 |
| 集成难度 | 低（~50-100行，纯stdlib直接import） |
| URL | https://github.com/Sami001-OG/Crypto-Backtester-and-Strategy-Optimizer |

**对ZQ的特别价值：** ①walk-forward + 网格搜索开箱即用，Quant校准E2/止损参数有工具了；②Binance Vision数据管道与ZQ数据源一致；③零依赖意味着部署零风险，不污染现有环境。

---

### 🟡 witness1993x/whale-pulse-evm（EVM多链鲸鱼雷达 — 观望）

| 字段 | 值 |
|:-----|:----|
| 平台 | `witness1993x/whale-pulse-evm`（GitHub） |
| 免费/付费 | 开源（MIT） |
| 星数 | **★0**（2026-05-02创建，最后推送2026-06-13）[来源：GitHub API 2026-08-17] |
| 语言 | TypeScript |
| 描述 | 实时多链EVM（ETH/Polygon/BSC/Arbitrum）大额转账+鲸鱼钱包雷达，基于ChainStream Transfers，可选Claude AI推理 |
| 推荐理由 | 概念与ZQ A8资金官（全链DEX大额成交+稳定币大额转账扫描）高度重叠。0★、1个open issue、4周未推送——**仅观望**，若A8需要EVM多链补充可作参考 |
| 弥补缺口 | 链上聪明钱维度（A8已有类似能力） |
| 集成难度 | 早期（★0，不推荐现在集成） |
| URL | https://github.com/witness1993x/whale-pulse-evm |

---

### 🟡 avdheshcharjan/polymarket-market-maker（Polymarket做市实证研究 — 方法论参考）

| 字段 | 值 |
|:-----|:----|
| 平台 | `avdheshcharjan/polymarket-market-maker`（GitHub，含docs/findings/） |
| 免费/付费 | 开源 |
| 星数 | **★0**（2026-04-23创建）[来源：GitHub API 2026-08-17] |
| 描述 | 基于568M笔成交数据集（915,852个唯一maker地址、$13.99B USDC量）：**Polymarket做市在所有maker层级都盈利，且按成交量单调分层** |
| 推荐理由 | 研究方法质量高（大样本实证+分层分析），但其结论仅适用于Polymarket预测市场，与ZQ Binance现货/合约趋势交易无关。与上期polymarket-whalewatch（★1）、polymarket-research（★0）同赛道，**全部观望** |
| URL | https://github.com/avdheshcharjan/polymarket-market-maker/blob/main/docs/findings/01-markouts-by-decile.md |

---

## 新策略发现

### 1. HRL-GridMM：分层强化学习做市（为"震荡市网格"P2建议提供理论+实盘背书 — 本期策略层最重要发现）

| 字段 | 值 |
|:-----|:----|
| 来源 | Zenodo开放论文（2026-03-04发布），BeeTrade Technologies；代码：github.com/Thanh-Van-2001/HRL-GridMM（★0，Python+Rust，2026-04-03创建） |
| URL | https://doi.org/10.5281/zenodo.18864061 |
| 核心架构 | **三时间尺度分层**：① Transformer宏观Agent（1分钟）— 市场regime检测+对冲模式选择；② Soft Actor-Critic中观Agent（10秒）— 连续网格参数优化；③ 确定性规则微引擎（tick级）— 保住做市结构性保证。现货-合约**delta中性**跨所对冲 |
| 实证结果 | 模拟4个币对/2交易所/3个月：年化Sharpe **3.38 vs 手工网格2.89（+17%）**，回撤相当；比SOTA RL交易方法高14-32%风险调整收益；**Gate.io 10天实盘试点：69K笔成交、672K USDT量**，暴露的失败模式正是逆向选择+regime切换回撤 |

**对ZQ的价值：** ZQ自06-15提出"震荡市网格模式"（P2），连续9期未动。这篇论文是**第一个把"网格"升级为"自适应网格"并提供实盘证据**的工作——其"宏观regime检测+中观参数自适应+微观规则执行"的分层思想可直接移植到ZQ网格模式设计（ZQ不需要上RL，三层职责划分本身就是设计框架）。同时其诚实披露失败模式（逆向选择）正是ZQ网格模式要预设的风控点。

### 2. "策略自生成 + 不可变回测验证"纪律清单（nhocconan — 给Quant的验证标准）

从该仓库提炼的4条硬纪律，建议写入Quant每日分析报告模板：
1. **无前视**：t根K线的信号只能在t+1成交；高周期数据在K线收盘前不可见
2. **成本必计**：往返手续费+滑点必须实扣，不能"理想化成交"
3. **资金费率按方向计**：多/空仓资金费符号不同，必须分开计
4. **引擎不可变**：评估者不能改引擎让结果变好看——对应ZQ"三跑通三验证"的工程化表达

### 3. 做市研究主线延续（上期已报，本期无新增量）

- Microstructure Lab"1.33亿笔成交价差分解"（Binance/GateIO/OKX，付费）— 上期已追踪
- arXiv 2607.11888 Optimal Adaptive Market Making（2026-04）— 上期已追踪
- 本期搜索再次命中以上两项，无新论文突破，说明该方向研究进入平台期

---

## 新数据源发现

| 数据源 | 类型 | 免费/付费 | 填补缺口 | 集成难度 |
|:-------|:-----|:---------:|:---------|:--------:|
| **CoinDesk Data**（data.coindesk.com/trade-data） | 300+交易所/300,000交易对，实时+历史统一API/WebSocket | 💰 付费（企业级） | 多平台验证维度（远期选项） | 中 |
| **Swiss Whale Intelligence**（swisswhaleintelligence.com/btc/） | 实时BTC鲸鱼仪表盘：24h内800笔≥100BTC转账、4,723个活跃鲸鱼地址、实体标注 | ✅ 免费（网页） | 链上聪明钱维度（BTC方向） | 中（需爬虫/无API） |
| **whale-pulse-evm** | EVM多链大额转账雷达（ChainStream） | ✅ 免费开源 | 链上聪明钱维度（EVM方向） | 早期观望 |
| **ChainAnalyzer / Deep Blue Alpha** | 10链分析SaaS / ETH鲸鱼数据库 | 💰 付费 | 链上聪明钱维度 | 排除（付费+与A8重叠） |

**数据源现状（第2期修正口径）：** 工具已备未接入——coinos（含资金费率/鲸鱼/清算3个Freqtrade策略模板）与coinos_client.py就位，**主链路零调用**。链上聪明钱维度（Nansen/Arkham/Glassnode/CryptoQuant商业平台免费层有限）仍无免费API方案；本期发现的Swiss Whale Intelligence是免费网页源，但无官方API，集成成本高于其价值，暂缓。

---

## 对比历史

### 上期（08-10）P0建议 — 7天追踪状态（物理核查）

| 推荐项 | 级别 | 08-10→08-17 | 真实状态（本期核查） |
|:-------|:--------:|:-----------:|:-----|
| **coinos接入A1**（30分钟动作，资金费率先行） | 🔴 P0 | — | ❌ **未执行**。全系统搜索：coinos仅被 `tools/agent_tool_audit.py`（审计登记）引用，主链路零调用；TOOL_LOG.md自05-17后无任何新增行。**使用级零闭环进入第2期** |
| **Anny Trade策略库接入Quant基准** | 🔴 P0 | — | ❌ 未接入。仅A8的learning_2026-07-14提及Anny.trade Bitcoin Institutional Radar（ETF AUM数据），非策略库基准 |
| **余额与持仓确认** | 🔴 P0 | — | ✅ 已执行（本期物理直查）：$213.54，见执行摘要 |
| **MCP统一数据层评估**（CoinAPI/Anny/AllTick/Hummingbot） | 🟠 P1 | — | ❌ 无证据 |
| **Hummingbot架构参考** | 🟠 P1 | — | 未动（合理，仅参考） |
| **鲸鱼标签纪律落地A8** | 🟠 P1 | — | ❌ 无证据 |

### 已追踪项目星数（08-10 → 08-17，7天）[来源：GitHub API 2026-08-17 00:20 CST]

| 项目 | 08-10 | 08-17 | 变化 | 备注 |
|:----|:----:|:----:|:----:|:----|
| **HKUDS/Vibe-Trading** | ★30,458 | **★31,041** | +583 (+1.9%) | 🚀 仍第一，但**增速显著放缓**（上两周+9.4% → 本周+1.9%） |
| HKUDS/AI-Trader | ★21,225 | ★21,430 | +205 (+1.0%) | 稳定 |
| OpenByteInc/QuantDinger | ★10,426 | ★10,745 | +319 (+3.1%) | 稳定增长 |
| Drakkar-Software/OctoBot | ★6,331 | ★6,414 | +83 (+1.3%) | 稳定 |
| nkaz001/hftbacktest | ★4,348 | ★4,368 | +20 (+0.5%) | 平稳 |
| aicoincom/coinos-skills | ★52 | ★52 | 0 | 停滞 |
| hackobi/AI-Scalpel | ★453 | ★454 | +1 | 停滞 |
| **nhocconan/AutoResearch** | — | **★5** | 🆕 | 本期新发现 |
| **Sami001-OG/Backtester** | — | **★5** | 🆕 | 本期新发现 |
| **Thanh-Van-2001/HRL-GridMM** | — | **★0** | 🆕 | 本期新发现（论文开放获取） |
| **witness1993x/whale-pulse-evm** | — | **★0** | 🆕 | 本期新发现 |

**关键观察：** ①Vibe-Trading增速从爆发（+35.5%/2周）回落到常态（+1.9%/周），AI交易Agent赛道的社区热度进入平台期；②QuantDinger（★10,745）持续稳定增长，仍是ZQ管道重构的架构参考；③本周新发现集中在"回测/验证"工具（2个）而非数据源——与ZQ"已装未接"的病灶同频：**验证能力是2026年交易Agent的下一战场**。

### 系统资金轨迹（实测）

| 日期 | 总权益 | 现金 | 来源 |
|:----:|:------:|:----:|:-----|
| 07-13 | $228.76 | ? | 上期报告（未独立验证） |
| 08-10 | $220.63 | $96.79 | Binance API 2026-08-10 00:50 CST |
| **08-17** | **$213.54** | **$99.24** | **Binance API 2026-08-17 00:27 CST 物理直查** |

**诚实判断：** 连续两期下滑（-3.2%），但现金占比升至46.5%——系统在"少亏"但"不赚"。持仓从ZEC单仓80%的风险结构（07-13）已变为ETH $49.58+4个$15级小仓的分散结构，风险敞口改善，但盈利机制无改善。**工具就位（coinos/回测器/Anny基准）与"接入"之间，隔着的还是那个30分钟动作。**

---

## 对ZQ系统的改进建议

### 🔴 P0 — 本周必须解决

**1. coinos接入A1 — 30分钟动作，第2期重复（这是使用级零闭环的打破点）**

上期原样转达，未执行。最低验证命令：
```bash
python3 -c "from tools.coinos_client import coinos; print(coinos.futures_interest('btcusdt:binance'))"
```
通过后把**资金费率**维度（对应已装的FundingRateStrategy模板）写进A1采集脚本，产出第一份真实数据文件。**这是全系统当前唯一需要做的事——比再发现10个新工具都重要。**

**2. Quant报告模板加入"诚实模拟"验证纪律（半天）**

把nhocconan四条纪律（无前视/t+1成交、成本必计、资金费率按方向、引擎不可变）+ Anny的OOS/PSR置信度，写入Quant每日23:00分析模板。同时用 **Sami001回测器（纯stdlib零依赖）** 在ZQ历史数据上复现1-2个现有策略参数（E2/止损），产出第一份可对照TradingView的回测报告。

**3. 余额与现金利用率分析**

总权益$213.54、现金$99.24（46.5%）[来源：Binance API 2026-08-17 00:27 CST]。连续两期下滑+现金高占比——建议Quant单独分析：是选币（E2筛选过严）还是入场（信号太少）导致资金空转。

### 🟠 P1 — 本周评估

**4. Sami001回测器P1评估**：对比hftbacktest（Rust，300-500行封装）vs Sami001（纯stdlib，~50行）——若TV平价校验可信（115项自查），这是ZQ回测层的最优起点。

**5. HRL-GridMM论文精读 → 震荡市网格设计**：06-15起连续9期未动的P2建议终于有了理论+实盘背书。采纳其**三时间尺度分层**（宏观regime检测/中观参数自适应/微观规则执行）和**delta中性对冲**思想到网格模式设计，预设"逆向选择"风控点（论文实证暴露的头号失败模式）。

**6. MCP统一数据层**：CoinAPI免费额度测资金费率/OI/清算三维（上期P1延续）。

### 🟡 P2 — 持续改进

**7. ATR动态止损**（06-15起连续10期未动）：改动小、见效快，优先落地。
**8. 追踪口径**：Vibe-Trading增速放缓观察（若持续，其"自然语言→策略"模式热度可能见顶）；whale-pulse-evm（★0）观望。
**9. 持续追踪闭环率**：使用级零闭环第2期（修正口径后）。

### 持续追踪：推荐闭环率（第13期）

| 状态 | 数量 | 说明 |
|:-----|:----:|:-----|
| 文件级已安装 | ~10项 | freqtrade/coin_pool/coinos(含3策略模板)/a4_trend_checker等（05-07~05-17） |
| **使用级已接入** | **0项** 🔴 | 主数据管道零调用——第2期（修正口径后） |
| 累计推荐工具 | 85+项 | 13期累计 |

---

## 附录：已排除项

| 项目 | 排除原因 |
|:-----|:---------|
| Monoscope（Stellar鲸鱼告警） | 仅支持Stellar链，与ZQ主战场（Binance主流币）无关 |
| ChainAnalyzer（日本10链SaaS） | 付费企业级，功能与A8重叠，免费层有限 |
| Deep Blue Alpha（ETH鲸鱼库） | 付费（$9.99-49/月），且ETH单链，A8已有类似扫描 |
| Swiss Whale Intelligence | 免费但仅BTC+网页无API，集成成本高于价值，暂缓 |
| CoinDesk Data | 企业级付费，ZQ现有Binance直连+CoinGecko已覆盖需求 |
| TradingStrategy.ai Master Vault | DeFi vault-of-vaults资产配置，与ZQ现货/合约趋势交易无关 |
| darkbot.io / troniex / Medium / YouTube ML文章 | 营销文/清单文，无数值可验证 |
| CoinLedger开源机器人清单 | freqtrade等已知项目汇总，无新东西 |

---

*ZH侦察签名：2026-08-17 01:00 CST*
*扫描方法：6维泛化关键词语义搜索 × GitHub API 12仓库实时验证 × 深度页面提取 × 系统内闭环状态物理核查*
*关键数字来源：星数=GitHub API 2026-08-17 00:20 CST实时查询；余额=Binance API 2026-08-17 00:27 CST物理直查（fetch_real_balance.py）*
*报告文件：`learning/scouter_report_20260817.md`*
*下一期扫描：2026-08-24（周一08:00）*
