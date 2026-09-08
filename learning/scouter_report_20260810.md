# ZH侦察报告（为ZQ系统）— 2026-08-10 01:00

> **侦察视角：** ZH总控的独立侦察兵（不自称ZQ-Scouter）
> **扫描时间：** 2026-08-10 01:00 CST（周一例行全网扫描 — 第12期）
> **上次报告：** 2026-07-27（第11期）
> **方法：** 6维泛化关键词 × GitHub API 20仓库实时验证 × 深度页面提取（Anny策略库/CoinAPI/cryptoadventure鲸鱼方法论）× 系统内闭环状态物理核查
> **来源说明：** 所有星数为GitHub API 2026-08-10 00:45 CST实时查询[来源：GitHub API]；系统余额为Binance API物理直查[来源：Binance API 2026-08-10 00:50 CST]。

---

## 执行摘要

本期是**闭环叙事被修正的一期**。物理核查发现：上期报告"70天零集成"的表述不准确——`tools/coinos/`（CoinOS/AiCoin）及3个Freqtrade策略模板（FundingRateStrategy/WhaleFollowStrategy/LiquidationHunterStrategy）**2026-05-17就已安装**，freqtrade/coin_pool/a4_trend_checker等05-07~05-17均已"已安装"。真正的断点不是"发现→安装"，而是**"安装→接入主数据管道"（使用级零闭环）**：全系统除审计登记外，无任何主链路代码调用coinos_client.py，无cron运行coinos任务。

### 本期三大发现

| 发现 | 级别 | 说明 |
|:-----|:----:|:-----|
| **闭环状态修正：工具已装、从未接入** | 🔴 P0 | 系统缺的不是"再发现/再安装"，而是把已装好的 `tools/coinos_client.py` 接进A1采集链路。这是本期最重要的洞察 |
| **MCP成为2026数据API行业标配** | 🟢 趋势 | CoinAPI/Anny Trade/AllTick/Hummingbot 全部提供MCP接口——AI Agent数据接入标准已成型 |
| **Vibe-Trading突破★30,458** | 🟢 趋势 | +9.4%/2周（★27,828→★30,458），AI交易Agent赛道热度持续 |

### 系统实时状态（物理验证）

- **总权益：$220.63**[来源：Binance API 2026-08-10 00:50 CST]（USDT现金 $96.79 + 持仓约 $123.84）
- 上期（07-13）$228.76 → 本期 $220.63（**-3.6%**，基本横盘）；07-27报告未取到余额
- **ZEC已不在持仓**——上期"ZEC单仓80%"风险已自动解除；本期最大持仓ETH $39.13
- 现金占比43.9%（$96.79/$220.63）——弹药可用，但未见结构性盈利改善

---

## 新工具发现

### ⭐⭐ Anny Trade策略库（30个AI回测策略，全公开验证 — 本期最重要新发现）

| 字段 | 值 |
|:-----|:----|
| 平台 | anny.trade/strategies（+ MCP连接器 anny.trade/mcp，github.com/anny-trade/mcp-cookbook） |
| 免费/付费 | **策略库免费公开**（AI分析工具Anny Line为付费） |
| 描述 | 30个AI发现加密策略，每个均公开完整回测：总收益/Sharpe/胜率/盈亏比/最大回撤/**样本外(OOS)验证/walk-forward折叠/概率化Sharpe置信度**，回测含手续费+滑点、全仓复利 |
| 代表性策略 | DOT 4h Downshift Rider +486% (Sharpe 1.60) / HBAR 4h Pattern Runner +300% / SUI 4h Overshoot Fader +296% / DOT 1h Peak Fader +292% (Sharpe 2.53)；**ZEC 1h Edge Seeker 回测0.00%** |
| 推荐理由 | 这是ZQ缺的"策略验证基准层"：Quant每日23:00分析可对照这些OOS验证数字校准自己的参数（E2/止损），而不是凭感觉调参。且其验证流水线（OOS/walk-forward/PSR）正是ZQ回测流程要补的能力 |
| 集成难度 | 低（REST/MCP读取策略页数据，~50行） |
| URL | https://anny.trade/strategies / https://github.com/anny-trade/mcp-cookbook |

**对ZQ的特别价值：** ①第一个可量化复现的外部策略基准；②其"含费滑点+OOS+PSR"验证标准可直接复制为Quant报告模板；③ZEC策略回测0%——与ZQ 6-7月ZEC实盘亏损互为印证，说明其回测可信度较高。

---

### ⭐⭐ CoinAPI Market Data API（400+交易所统一数据层，原生MCP）

| 字段 | 值 |
|:-----|:----|
| 平台 | coinapi.io/products/market-data-api |
| 免费/付费 | 免费额度（Start With Free Credits）/ 付费分级 |
| 描述 | 400+交易所、916k+交易对、**678TB历史数据**；REST/WebSocket/FIX/JSON-RPC/**MCP**/S3六种接入；覆盖现货/合约/永续/期权/指数/**资金费率/未平仓/清算数据**；GeoDNS多区域容灾 |
| 推荐理由 | 一个API同时覆盖A1 6维缺口中的多个维度（资金费率✓ 清算✓ 多交易所验证✓）。MCP接口意味着A1/A3/A8可用标准协议直接查询，免去逐家封装 |
| 集成难度 | 低（MCP或REST，~100行） |
| URL | https://www.coinapi.io/products/market-data-api |

---

### ⭐⭐ Hummingbot MCP server + Condor（★19,386 — 做市机器人Agent原生化）

| 字段 | 值 |
|:-----|:----|
| 平台 | github.com/hummingbot/hummingbot |
| 免费/付费 | 开源（Apache-2.0） |
| 星数 | ★19,386[来源：GitHub API 2026-08-10] |
| 2026新能力 | **MCP server集成**（Claude Code/Gemini CLI等MCP Agent可直接编程下单）+ **Condor接口**（AI控制交易Agent的专用harness，移动/桌面Telegram控制）+ Binance TRADIFI_PERPETUAL（代币化股权/RWA永续，开源独有） |
| 推荐理由 | 若ZQ未来补"做市/网格"策略维度，Hummingbot是唯一Agent原生执行层（MCP直接下单），比自研网格引擎成熟得多。**但诚实提示：** 当前总权益$220.63，做市策略的收益/费率比在如此小资金下不划算，建议仅作架构参考 |
| 集成难度 | 中（独立进程部署，MCP层~100行） |
| URL | https://github.com/hummingbot/hummingbot（能力摘要见 https://coincodecap.com/open-source-trading-bots-on-GitHub） |

---

### 🟡 Dukesan-ai/crypto-ml-trading-framework（★1 — ML方法论参考）

| 字段 | 值 |
|:-----|:----|
| 平台 | github.com/Dukesan-ai/crypto-ml-trading-framework |
| 星数 | ★1（2026-06-26创建，MIT，Python，最近推送07-06） |
| 描述 | 单人实盘运行的加密永续ML系统：微观结构特征 + **防泄漏验证（CPCV组合交叉验证/DSR防过拟合）** + meta-labeling（元标注） |
| 推荐理由 | ★1太早期不推荐集成，但其"CPCV+DSR+meta-labeling"方法论与Anny的OOS/PSR验证思路同源，可作为Quant学习防过拟合技术的入口 |
| URL | https://github.com/Dukesan-ai/crypto-ml-trading-framework |

### 🟡 tlafargue/polymarket-research（★0 — 反过拟合研究参考）

| 字段 | 值 |
|:-----|:----|
| 平台 | github.com/tlafargue/polymarket-research |
| 星数 | ★0（2026-07-24创建，Python，含复现代码） |
| 描述 | "四个月的Polymarket边缘**证伪**研究：研究、数据与复现代码"——即系统性检验并证伪了多个Polymarket"边缘策略" |
| 推荐理由 | 证伪研究比赚钱研究更有教育价值——提醒ZQ任何"新发现边缘"必须先过OOS验证。Polymarket方向与上期polymarket-whalewatch（★1）同赛道，均观望 |
| URL | https://github.com/tlafargue/polymarket-research |

### 追踪项目状态变化（非新发现，但重要）

- **AllTick**：GitHub仓库改名 → `alltick/alltick-realtime-forex-crypto-stock-tick-finance-websocket-api`，**★597**（+8）[来源：GitHub API 2026-08-10]；新增 **npm `alltick-agent`**（MCP数据包，2026-03-22发布）——上期追踪名已失效，需更新
- **TickDB**：GitHub仓库 `TickDB/tickdb` **返回404**（删除/私有化/改名），但产品站 **tickdb.ai 仍在运营**（875+交易对、毫秒级WebSocket）——追踪状态改为"产品存活、仓库不可见"
- **signalcraft-trading-assistant**（搜索发现★7，DeepSeek V4驱动）：GitHub **404**，仓库已消失，排除

---

## 新策略发现

### 1. 市场做市（MM）研究主线（2026学术爆发 — 为P2"震荡市网格"提供理论支撑）

| 论文/来源 | 要点 | URL |
|:---------|:-----|:----|
| **"Market Making in Crypto"** — Sasha Stoikov等（2026） | **Avellaneda-Stoikov模型联合作者**的加密做市最新研究，SSRN | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5066176 |
| **Optimal Adaptive Market Making**（2026-04） | 永续合约市场高收益流动性提供的自适应做市理论框架 | https://arxiv.org/html/2607.11888 |
| **Microstructure Lab**（2026-04，付费） | **1.33亿笔成交**（Binance/GateIO/OKX）分解：有效价差=实现利润+逆向选择，1s/5s/30s/5min多尺度 | https://themicrostructurelab.substack.com/p/maker-alpha-across-133m-trades-why |
| **Neutralis**（2026） | 做市vs买入持有的诚实对比："取决于测量区间" | https://neutralis.finance/insights/market-making-beat-market-research |

**对ZQ：** 不推荐现在上做市（资金$220太小、手续费敏感），但"库存管理/逆向选择"思想可直接移植到P2的**震荡市网格模式**（06-15起已连续7期未动的建议）——网格本质是简化做市，Stoikov论文可作理论背书。

### 2. 情绪增强深度RL做BTC日线三态决策（FinMMEval 2026，CLEF）

- 论文：CLaC@FinMMEval 2026 Task 3 — 新闻+历史数据 → 每日**做多/空仓/做空**离散动作MDP，对比4种深度RL方法
- **与ZQ同构：** ZQ是"舆情(A7)→决策(Commander)→执行(Blade)"，该论文是"新闻情绪→RL决策"，其奖励设计（Alpha-Reward）可参考
- URL: https://arxiv.org/html/2607.16028v1

### 3. 深度学习配对交易（协整加密对实时预测）

- Frontiers（2026-01）：深度学习实时预测协整加密对价差——相对价值信号维度
- URL: https://www.frontiersin.org/journals/applied-mathematics-and-statistics/articles/10.3389/fams.2026.1749337/full

### 4. ArchetypeTrader（AAAI）：RL选择与精炼"可学习策略原型"

- 与Vibe-Trading"自然语言→策略"模式呼应——策略不再写死，而是由RL在原型库中组合
- URL: https://ojs.aaai.org/index.php/AAAI/article/view/40166

### 5. 鲸鱼追踪方法论纪律（cryptoadventure 2026指南 — 给A8/NBZ的硬约束）

- **标签会衰减**（实体换钱包、托管合并、平台间标签不一致）
- **鲸鱼存款≠卖出**（可能是抵押/托管/做市库存/OTC结算）——需后续订单簿压力/DEX卖出/稳定币收款/OI变化确认
- **工作流必须≥2类工具**（标签告警类 + 原始仪表盘类），防止单一界面成为全部论点
- URL: https://cryptoadventure.com/2026-on-chain-orderflow-tools-whale-tracking-without-overfitting/

---

## 新数据源发现

| 数据源 | 类型 | 免费/付费 | 填补缺口 | 集成难度 |
|:-------|:-----|:---------:|:---------|:--------:|
| **Anny Trade策略库** | 30个OOS验证回测策略（含Sharpe/胜率/回撤/PSR置信度） | ✅ 免费 | 策略验证基准（Quant校准E2/止损用） | 低（REST/MCP） |
| **CoinAPI** | 400+交易所统一市场数据（含资金费率/OI/清算/期权） | 🟡 免费额度 | A1多维缺口一站式 + 多平台验证 | 低（MCP） |
| **AllTick MCP包**（npm alltick-agent） | tick级实时行情MCP接入 | 🟡 免费key | 实时tick数据Agent化接入 | 低（MCP） |
| **SSRN/arXiv 2026做市+RL论文** | 策略理论依据（Stoikov等） | ✅ 免费 | 网格/做市策略理论支撑 | 阅读级 |
| **Microstructure Lab** | 1.33亿笔成交价差分解 | 💰 付费 | 微观结构数据（可暂缓） | — |

**A1 6维缺口现状（如实修正版）：** 工具已备但未接入——coinos含资金费率/鲸鱼追踪/清算三个Freqtrade策略模板，`tools/coinos_client.py`可查K线/ticker/搜索，**但主链路零调用**。链上聪明钱维度（Nansen/Arkham/Dune/Glassnode/CryptoQuant/Whale Alert均为商业平台，免费层有限）仍无免费接入方案。

---

## 对比历史

### 上期（07-27）推荐项 — 14天追踪状态（含重大修正）

| 推荐项 | 上期级别 | 07-27→08-10 | 真实状态（本期核查） |
|:-------|:--------:|:-----------:|:-----|
| **coinos-skills** | ⭐⭐最重要 | ★49→**★52** | ⚠️ **修正：文件级已装（05-17），使用级零接入**。上期标"❌未集成"不精确——它一直在`tools/coinos/`躺着 |
| AI-Scalpel-Trading-Bot | 🟡 | ★450→**★453** | ❌ 未集成 |
| polymarket-whalewatch | 🟡 | ★1 | ❌ 未集成（**修正：实际创建06-25**，非上期所说07-26；最近推送08-04） |

### P0任务真实状态（修正版 — 文件级 vs 使用级）

| P0任务（05-11提出） | 上期标注 | **本期核查结论** |
|:-------------------|:--------:|:----------------|
| CCXT激活 | ❌ 70天 | ⚠️ **部分激活**：coinos JS技能（exchange.mjs等）在用ccxt；但Python主引擎无 `import ccxt` |
| Etherscan Monitor | ❌ 70天 | ❌ 无证据 |
| CoinOS/AiCoin集成 | ❌ 56天 | ⚠️ **文件级✅（05-17安装），使用级❌（主链路零调用）** |
| fia-signals-mcp | ❌ | ❌ 无证据 |
| Vibe-Trading/AI-Trader/QuantDinger评估 | ❌ | ❌ 无证据 |

**核心修正：** 上期"75+项推荐、零集成"应为"**约1/4已安装（文件级），但全部未接入主数据管道（使用级）**"。TOOL_LOG.md显示freqtrade（05-07）、coin_pool_config（05-07）、CoinOS（05-17）、coinos_client.py（05-17）、a4_trend_checker（05-17）均已安装。**系统的病根从"不装"变成"装了不用"。**

### 已追踪项目星数（07-27 → 08-10，14天）[来源：GitHub API 2026-08-10]

| 项目 | 07-27 | 08-10 | 变化 | 备注 |
|:----|:----:|:----:|:----:|:----|
| **HKUDS/Vibe-Trading** | ★27,828 | **★30,458** | **+2,630 (+9.4%)** 🚀 | 突破30K，AI交易Agent第一 |
| HKUDS/AI-Trader | ★21,047 | ★21,225 | +178 (+0.8%) | 稳定 |
| OpenByteInc/QuantDinger | ★10,019 | ★10,426 | +407 (+4.1%) | 稳定增长 |
| Drakkar-Software/OctoBot | ★6,264 | ★6,331 | +67 (+1.1%) | 稳定 |
| nkaz001/hftbacktest | ★4,271 | ★4,348 | +77 (+1.8%) | 稳步 |
| GMGNAI/gmgn-skills | ~★360 | ★431 | +~71 (+20%) | 加速 |
| mnemox-ai/tradememory-protocol | ★1,401 | ★1,408 | +7 | 稳定 |
| 51bitquant/howtrader | ★944 | ★943 | -1 | 停滞 |
| pmaji/crypto-whale-watching-app | ★640 | ★639 | -1 | 停滞 |
| alltick（改名后） | ★589 | **★597** | +8 | 仓库改名+新增MCP包 |
| TickDB/tickdb | ★574 | **404** | 🔴 | GitHub仓库不可见，产品站tickdb.ai存活 |
| hackobi/AI-Scalpel | ★450 | ★453 | +3 | — |
| aicoincom/coinos-skills | ★49 | ★52 | +3 | — |

### 系统资金轨迹（实测）

| 日期 | 总权益 | 来源 |
|:----:|:------:|:-----|
| 07-13 | $228.76 | 上期报告（未独立验证） |
| 07-27 | ?（未取到） | — |
| **08-10** | **$220.63**（现金$96.79） | **Binance API 2026-08-10 00:50 CST 物理直查** |

### 与上期建议的对照

上期P0建议：A.CCXT激活（5分钟）/ B.coinos REST调用（10分钟）/ C.whale-watching部署 / D.tradememory安装。**14天后核查：B选项的工具实际05-17就已就位，但从未被调用**——上期把问题诊断为"没装"，本期证据显示是"装了不接"。

---

## 对ZQ系统的改进建议

### 🔴 P0 — 本周必须解决（换方向：不再发现新工具，把已装的接上）

**1. 接入已装好的CoinOS到A1数据采集（30分钟，本期唯一必须动作）**

工具已在 `tools/coinos_client.py`（K线/ticker/搜索）+ 3个Freqtrade策略模板（资金费率/鲸鱼/清算）。最低验证：
```bash
python3 -c "from tools.coinos_client import coinos; print(coinos.kline('btcusdt:okex','3600',5))"
```
通过后，把任一维度（建议先从**资金费率**开始，对应FundingRateStrategy）写进A1采集脚本，产出第一份真实数据文件。**这将打破"使用级零闭环"——比再装10个新工具都重要。**

**2. Anny策略库接入Quant基准（半天）**

从30个公开OOS策略中选2-3个与ZQ参数同构的（Band Fader=Bollinger+RSI、Downshift Rider=MACD，均与ZQ现有信号同族），在ZQ历史数据上复现回测，校准E2/止损参数。**这是第一个可量化复现的外部策略基准**，同时把"OOS+PSR置信度"引入Quant报告模板。

**3. 余额与持仓确认**

总权益$220.63[来源：Binance API 2026-08-10 00:50 CST]，现金$96.79（43.9%），最大持仓ETH $39.13，ZEC已出清。弹药可用但连续3个月无结构性盈利——建议Quant就"现金利用率"单独分析。

### 🟠 P1 — 本周评估

**4. MCP统一数据层**：CoinAPI/Anny/AllTick/Hummingbot均已MCP化。建议A1/A3/A8评估统一走MCP协议，避免逐家封装REST。CoinAPI免费额度可先测资金费率/OI/清算三个缺口维度。
**5. Hummingbot架构参考**：仅评估其MCP+Condor模式（Agent原生执行层），**不上做市实盘**（$220资金做市不划算，诚实结论）。
**6. 鲸鱼标签纪律落地A8**：按cryptoadventure方法论，A8输出"聪明钱信号"前必须过"存款≠卖出+标签衰减+≥2工具交叉"三检查，防止伪信号进NBZ。

### 🟡 P2 — 持续改进

**7. 震荡市网格/ATR动态止损**（06-15起连续8期未动）：本期找到理论支撑（Stoikov 2026做市研究+自适应做市论文），建议至少把ATR止损落地（改动小、见效快）。
**8. 修正历史追踪口径**：TickDB改为"产品存活、仓库404"；AllTick更新为新仓库名；Scouter报告模板增加"文件级/使用级"双状态列，避免再误报。
**9. 持续追踪**：Vibe-Trading突破30K后走向、QuantDinger 10K+、MCP生态（这是2026年AI交易基础设施的最大变量）。

### 持续追踪：推荐闭环率（第12期 — 修正口径）

| 状态 | 数量 | 说明 |
|:-----|:----:|:-----|
| 文件级已安装 | ~10项 | freqtrade/coin_pool/coinos(含3策略模板)/a4_trend_checker等（05-07~05-17） |
| **使用级已接入** | **0项** 🔴 | 主数据管道零调用——这是真正要破的纪录 |
| 累计推荐工具 | 80+项 | 12期累计 |

---

## 附录：已排除项

| 项目 | 排除原因 |
|:-----|:---------|
| signalcraft-trading-assistant（★7，DeepSeek V4） | GitHub 404，仓库已消失（虽然DeepSeek驱动与ZQ同栈，但不可用） |
| PlaceNL2026/best-of-algorithmic-trading | GitHub 404 |
| OpenCEX（★） | 交易所平台（撮合引擎），非交易工具 |
| Superalgos | 社区社交交易平台，与ZQ小资金CEX策略不匹配 |
| bravosresearch / troniex 策略清单 | 列表文章，无数值无回测 |
| YouTube "回测1000次日交易策略" | 不可验证 |
| Microstructure Lab（付费） | 有价值但付费，暂缓 |

---

*ZH侦察签名：2026-08-10 01:00 CST*
*扫描方法：6维泛化关键词语义搜索 × GitHub API 20仓库实时验证 × 深度页面提取 × 系统内闭环状态物理核查*
*关键数字来源：星数=GitHub API 2026-08-10 00:45 CST；余额=Binance API 2026-08-10 00:50 CST物理直查*
*报告文件：`learning/scouter_report_20260810.md`*
*下一期扫描：2026-08-17（周一08:00）*
