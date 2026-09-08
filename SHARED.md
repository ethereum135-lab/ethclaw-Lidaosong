# ⚡ ZQ 共享知识库 — 多Agent信息交换中心

> **所有Agent启动时先读本文件了解全局状态。**
> 历史数据（2026-05-04~06-03）已归档：`archive/SHARED_history_20260612.md`

---

## 🔴 2026-08-31 策略重写：ETH网格 → ETH趋势通道 v3.0（Donchian 5日突破）

**老李指令「修復盈利策略，重新寫一遍，現在一直虧損」。**
- 旧网格 `tools/grid_bot.py` 已停用并归档 `archive/grid_bot_v2_20260831.py`
- 新引擎 `tools/trend_bot.py`（AWS每5分钟cron，日志 logs/trend_bot.log）：
  - ENTRY：价格突破近5日最高价 → 全仓买ETH
  - EXIT：价格跌破近5日最低价 → 全仓卖ETH锁USDT
  - **v3.1（12:00定案，老李指令「每日盈利策略」）：新增 EXIT② 盈利锁定——1h收盘自入场峰值回落≥2% → 全仓卖出锁利。**
    回测：+27.2%（7笔兑现/胜率57%/回撤-3.3%）vs 原版+35.3%（2笔兑现/回撤-6.9%）——兑现频次3.5×、回撤减半
- 回测（真实行情+0.1%手续费）：Donchian 5d +23.6% vs 网格 -1.1% vs Buy&Hold +13.1%
- 策略细节以 `NAVIGATION.md` 为唯一基准；日目标0.1~0.3%仍按 IRON_RULES_PROFIT.md 执行

## 🎯 当前系统状态（2026-06-12）

| 指标 | 值 |
|:-----|:---|
| 总目标 | 430U → 1,000,000U |
| 今日日目标 | 总资 × 2% |
| 策略基准 | `NAVIGATION.md`（唯一策略基准） |
| 团队协作 | `AGENTS.md` |
| 总蓝图 | `config/ZQ_MASTER_BLUEPRINT_V3.md` |
| 防御机制 | `post-fix-defense-mechanism`（修复后建防御） |
| 飞书 | 🔴 缺权限（contact:user.employee_id:readonly） |
| Telegram | 🔴 Token 401 过期 |
| 企微 | 🔴 连接断开 |

---

## ⚡ 当前P0/P1追踪

| 优先级 | 任务 | 状态 | 说明 |
|:------|:----|:----|:-----|
| **P0** | 各Agent身份文档 | 🔴 待做 | 14个Agent仅ZH有目录 |
| **P0** | 总蓝图细化到子蓝图 | 🔴 待做 | docs/仍是3个旧Navua文档 |
| **P1** | 第三方平台恢复 | 🔴 待修 | Telegram Token+飞书权限+企微重连 |
| **P1** | 旧文档清理（铁律九） | ⏸ 待排期 | A→B替代时删A |
| — | 更多详见 `config/ZQ_MASTER_BLUEPRINT_V3.md` 执行优先级表 |

---

## 📮 ZH Scouter: 全网扫描新报告 (2026-07-27 08:30)

### → `learning/scouter_report_20260727.md` (24.2KB) — 第11期/70天里程碑

**核心发现：**
- ⚠️ **70天零闭环里程碑刷新！** 从05-11至今，75+项工具推荐、全部零集成。连续11期报告重复同一个问题——这不是工具问题，是系统机制问题
- 🚀🚀🚀 **Vibe-Trading爆发★27,828（+35.5%/2周，+7,296★）** — 9周从★6,420翻4.3倍，超越AI-Trader成AI交易Agent领域第一项目。市场在用星数投票：自然语言→策略模式获压倒性认可
- 🚀 **QuantDinger突破★10,000**（迁移至OpenByteInc组织，+5.1%/2周）
- ⭐⭐ **coinos-skills（★49）** — AiCoin官方Agent工具包，40+工具覆盖资金费率/鲸鱼追踪/链上分析/CCXT — 一个工具填补A1多个数据缺口
- 🟡 **AI-Scalpel-Trading-Bot（★450）** — Python ML入场/出场优化交易机器人
- 🟡 **polymarket-whalewatch（★1）** — Polymarket鲸鱼监控（全新，07-26发布）
- **跟踪增长：** AI-Trader ★21,047(+1.5%) / TickDB ★574(+6.5%) / AllTick ★589(+0.7%) / Tradememory ★1,401(+0.6%) / Howtrader ★944(+1.2%)

**推荐最低行动：** CCXT激活（5分钟）或 coinos-skills REST调用（10分钟） — 任何一项即可打破70天零纪录。

## 📮 ZH Scouter: 全网扫描新报告 (2026-08-10 01:00)

→ `learning/scouter_report_20260810.md` (18.8KB) — 第12期

- 🔴 **闭环叙事重大修正：** 物理核查发现 `tools/coinos/`（CoinOS含资金费率/鲸鱼/清算3个Freqtrade策略模板+coinos_client.py）**05-17就已安装**——上期"70天零集成"不准确。真正的断点是**"安装→接入主数据管道"（使用级零闭环）**：主链路零调用、无cron运行。系统缺的不是再发现/再安装，是把已装好的接上
- ⭐⭐ **Anny Trade策略库**（anny.trade/strategies）— 30个AI策略全公开OOS回测（Sharpe/胜率/回撤/PSR置信度，含费滑点），本期最重要新发现，可作Quant策略验证基准（注意：ZEC 1h Edge Seeker回测0%——与ZQ实盘教训互证）
- ⭐⭐ **CoinAPI MCP**（400+交易所/678TB历史/含资金费率/OI/清算）— MCP接口一站式补A1多维缺口
- ⭐⭐ **Hummingbot MCP+Condor**（★19,386）— 做市Agent原生执行层，仅架构参考（$220资金做市不划算）
- 🟢 **MCP成2026数据API标配**：CoinAPI/Anny/AllTick/Hummingbot全提供MCP
- 🚀 **Vibe-Trading突破★30,458**（+9.4%/2周）[GitHub API 08-10]
- ⚠️ 追踪修正：TickDB GitHub仓库404（产品tickdb.ai存活）；AllTick仓库改名★597+新增MCP包
- **系统实时状态：** 总权益 **$220.63**（USDT现金$96.79，ZEC已出清，最大持仓ETH $39.13）[来源：Binance API 2026-08-10 00:50 CST]
- **P0行动：** ①跑通 `python3 -c "from tools.coinos_client import coinos; print(coinos.kline('btcusdt:okex','3600',5))"` 并把资金费率接入A1（30分钟）②Anny策略库做Quant回测基准 ③Quant分析43.9%现金利用率

## 📮 ZH Scouter: 全网扫描新报告 (2026-06-15 08:05)

→ `learning/scouter_report_20260615.md` (26.9KB)

**核心发现（7个新工具/项目，web_search 6大方向 + 历史比对 + 系统状态验证）：**
- ⭐⭐⭐ **Vibe-Trading（HKUDS/Vibe-Trading, 12,168★）** — **本期最重要发现**。从05-25的6,420★翻倍，香港大学数据科学实验室托管。AI量化交易平台（回测+实盘+多Agent研究），pip install即用。v0.1.8支持MCP工具集成
- ⭐⭐ **OpenAlice（TraderAlice/OpenAlice, 5,224★）** — "你一个人的华尔街"，全资产AI交易Agent（股票/加密/大宗/外汇/宏观），Docker部署
- ⭐ **HydraQuant（9★）** — 18 RAG类型 + 10自主Agent引擎架构参考
- ⭐ **Pattern-Signal-Automator** — 自动化图表形态扫描器
- 🟡 OmniTrade(1★)/Cortex Arbitrage Bot(48★)/Meta-RL-Crypto(arXiv论文) — 可关注
- ⚠️ **连续35天零闭环**：CCXT/Etherscan 35天零使用，推荐项累计32+项零集成。**闭环崩溃已从"没时间做"演变为"系统级设计缺陷"**
- 🔴 **余额查询失败（08:05）** — 系统盲飞

---

## 📋 今日文档更新（2026-06-12）

| 文档 | 更新内容 |
|:----|:---------|
| `ZQ_MASTER_BLUEPRINT_V2→V3` | 资金250U→430U、CHANGELOG软链接、执行优先级加进度列、引用防御机制 |
| `NAVIGATION.md` | 补PROFIT_ARCHIVE.md引用、加紧急修正例外、决策树整合极恐模式、规则交叉引用 |
| `AGENTS.md` | 标题「九条铁律」、补铁律七、补A1~A9协作定义、加策略基准+防御机制引用 |
| `PROFIT_ARCHIVE.md` | 新建（之前被NAVIGATION.md引用但不存在） |
| `CHANGELOG.md` | 新建软链接→`CHANGE_LOG.md` |
| `post-fix-defense-mechanism` skill | 新创建+三排查三跑通三验证+6个问题修复 |
| 排查准则库 | PC-001~PC-005已入库 |
| 历史SHARED.md | 归档到 `archive/SHARED_history_20260612.md` |

---

## 📡 自动排查九维度健康扫描 (2026-06-07 09:34)

→ `learning/auto_scan_2026-06-07.md`（9.8KB）

**核心发现:**
- 🟢 **全天系统正常运行** ✅ — SOCKS5通·SSH通·AWS通·信号管道全通
- 🟢 **ALLO +$12.28已收割(227%日目标)** 🏆 — 超预期完成每日2%目标
- 🟢 **C/PARTI持有中涨幅靠前** (C+15%/PARTI+17%/TON刚买+0.7%) — 持有方向正确
- 🟢 **signals 08:41新鲜** ✅ — 信号管道由陈旧恢复
- 🟡 **3/3满位+52% USDT闲置($141)** — 锁仓状态，新机会无法入场
- 🟡 **MANTA轮换(-1.1%浮亏)** — 刚轮换卖掉的MANTA今日+15%
- 🔴 **MASTER经验值: 65.4%过早退出(494/755)** — 基因未变
- ✅ **涨幅榜TOP15: 持有3个(C/PARTI/ALLO已卖)** — 覆盖率良好

## 📮 ZH Scouter: 新全网扫描报告 (2026-06-08 08:30)

→ `learning/scouter_report_20260608.md`（23.8KB）

**核心发现（9个新工具/库，GitHub API扫描6大方向 + 系统状态验证）：**
- ⭐⭐⭐ **CloddsBot（alsk1992/CloddsBot, 332★）** — **本期最重要发现**。开源自托管AI交易终端，Claude驱动，覆盖1000+市场（Polymarket/Kalshi/Binance/Hyperliquid/Solana DEX/5 EVM链）。14天10.7k clones，MIT开源。可独立部署不依赖ZQ引擎
- ⭐⭐ **OpenWhale（OpenWhale-Org/OpenWhale, 133★）** — AI原生策略编排框架，Monitor/Strategy/Executor三层解耦，与ZQ Agent架构高度匹配
- ⭐ **crypto-liquidity-ai-trading-bot（115★）** — 流动性感知交易框架，填补微观市场结构缺口
- ⭐ **fia-signals-mcp** — **最优先即用方案**：pip install即可获得市场体制检测+资金费率+信号
- ⭐ **AlgoVault/crypto-quant-signal-mcp** — 综合信号MCP服务，91.3% PFE胜率，100次免费/月
- 🟡 NexusQuant(83★)/Archimedes(6★)/AI Trader MCP(14★)/auto-trading(31★) — 可关注
- ⚠️ **连续5期追踪：CCXT和Etherscan Monitor已28天零使用。A1 0/6维(0%)。闭环崩溃是机制缺陷，非待办**
- 🔴 **系统余额$276.76（-35.64% vs 本金$430）** — 6周$427.68→$276.76无结构性改善
|---

## 📮 ZQ-Scouter: 每日复盘 (2026-06-13 00:10)

→ `learning/scouter_report_20260613.md`（7KB）

| 维度 | 状态 | 关键数据 |
|:----|:----|:--------|
| 系统健康 | 🟡 2.5/5 | A4活跃·A1/A2过期·A3→A4断裂·USDT$20.85(8.4%) |
| 执行质量 | 🟡 3/5 | 轮换PARTI→EDEN正确·5仓满·ENJ+14.6%最强·日亏-$1.07 |
| 选币/信号 | 🟡 2.5/5 | 信号新鲜02:00·候选充足但弹药不足·数据0/6维(33天) |
| 首要任务 | P0 | ①USDT回$48+②打通A3→A4链路③激活CCXT |
| 最大风险 | 🔴 | 三缺一：现金8.4%+5仓满+极恐12=FOMC前无防御 |

---

## 📮 ZH Scouter: 全网扫描新报告 (2026-07-13 08:30)

→ `learning/scouter_report_20260713.md` (32.4KB)

**核心发现（12个新工具/项目，GitHub API 6轮搜索 + 历史9期比对 + 系统状态实时验证）：**
- ⭐⭐⭐ **QuantDinger（brokermr810/QuantDinger, ★9,533）** — **本期最重要发现**。AI量化全栈平台（回测+实盘+市场数据+多Agent研究），Python/Apache-2.0，2026-07-12更新。与ZQ技术栈完全兼容，可能替代当前自制管道
- ⭐⭐⭐ **Homerun（braedonsaunders/homerun, ★111）** — 预测市场Python算法交易平台，25+内置策略+回测+AI评分+模拟交易。比polymarket-crypto-toolkit（★59）更完整的平台级方案
- ⭐⭐ **AllTick API（★585）** — 实时Tick级多市场数据API。Binance API被封的替代数据源
- ⭐⭐ **HyperData Terminal（★10）** — 订单流+鲸鱼追踪+清算级联TUI终端，一个工具覆盖A1 6维缺口中3个维度。Python原生
- ⭐⭐ **crypto-whale-watching-app（★639）** — Python Dash鲸鱼追踪应用，直接填补链上聪明钱维度
- ⭐⭐ **nirholas MCP生态（★19）** — 1100+加密MCP工具聚合，Hermes Agent原生兼容
- 🟢 **A4恢复运行！** — 07-06"❌无数据"→07-13"✅9持仓活跃"。总资$228.76（+2.1%）
- 🔴 **USDT从$224→$5.80（-97.4%）** — 弹药几乎打光。ZEC单币占80%（$182.43），集中度极高
- 🔴 **累计亏损-$201.77（-46.9%）** — 从$430初始资金已亏近半
- 🔴 **63天零闭环持续刷新纪录** — 65+推荐，0集成。**本周最低行动：15分钟部署鲸鱼追踪/10分钟安装homerun**
- 🔴 **A3→A4链路断裂61天+** — A4活跃但未使用A3最新推荐

## 共享机制

1. **所有Agent先读本文件了解全局状态**
2. Scouter → 写报告到 `learning/` → 追加标记到本文件
3. Quant → 写分析到 `reports/` → 追加标记到本文件
4. Blade → 执行优化/修复任务
5. Reporter → 生成复盘报告
6. Commander → 读标记 → 做决策 → 更新AGENTS.md/引擎

## 数据共享

- `data/node_history.jsonl` — 所有节点快照
- `data/trend_store.json` — OI/费率趋势
- `audit/TRADES.md` — 完整交易记录


## 📮 ZH Scouter: 全网扫描新报告 (2026-08-17 01:00)

→ `learning/scouter_report_20260817.md` — 第13期

- 🔴 **使用级零闭环进入第2期：** 上期P0（coinos接入A1，30分钟动作）未执行——coinos仍仅被agent_tool_audit.py引用，主链路零调用，TOOL_LOG自05-17无新增。打破点还是那个30分钟动作
- ⭐⭐ **Sami001-OG/Crypto-Backtester**（★5）— 纯Python零依赖的TradingView平价回测器（115项TV平价校验），walk-forward开箱即用，ZQ回测层最低门槛选项
- ⭐⭐ **nhocconan/AutoResearch策略研究**（★5，478 commits）— Karpathy autoresearch做自主策略研究，"诚实模拟"4条纪律（无前视/t+1成交/成本必计/资金费率按方向）建议写入Quant报告模板
- 🟢 **HRL-GridMM**（Zenodo开放论文）— 分层RL网格做市，Sharpe 3.38 vs 手工网格2.89，Gate.io 10天实盘69K笔——06-15起9期未动的"震荡市网格"P2终于有理论+实盘背书
- 📊 系统实测：总权益 **$213.54**（现金$99.24，46.5%）[Binance API 2026-08-17 00:27 CST]，连续两期下滑-3.2%
- 🚀 Vibe-Trading ★31,041（增速放缓至+1.9%/周）/ QuantDinger ★10,745 [GitHub API 08-17]


## 📮 ZH Scouter: 全网扫描新报告 (2026-08-24 00:30)

→ `learning/scouter_report_20260824.md` — 第14期

- ⭐⭐⭐ **Binance官方Skills Hub（★977）** — binance-trading-signal技能提供官方Smart Money链上信号+策略回测，13期来首个免费"链上聪明钱"方案，直接填A1 6维缺口第4维
- ⭐⭐ **OpenAlice（★6,665）** — "Trading as Git"审批门控执行范式，Blade/FK风控升级蓝本（事前门禁替代事后检查）
- ⭐⭐ **vectorbt-backtesting-skills（★197）** — /backtest+/optimize技能包，Quant恢复管道后的首个工具
- 🔴 **资金回升但病灶加深**：总权益 $233.93（+9.5

## 📮 ZH Scouter: 全网扫描新报告 (2026-08-24 00:30)

→ `learning/scouter_report_20260824.md` — 第14期

- ⭐⭐⭐ **Binance官方Skills Hub（★977）** — binance-trading-signal技能提供官方Smart Money链上信号+策略回测，13期来首个免费"链上聪明钱"方案，直接填A1 6维缺口第4维
- ⭐⭐ **OpenAlice（★6,665）** — "Trading as Git"审批门控执行范式，Blade/FK风控升级蓝本（事前门禁替代事后检查）
- ⭐⭐ **vectorbt-backtesting-skills（★197）** — /backtest+/optimize技能包，Quant恢复管道后的首个工具
- 🔴 **资金回升但病灶加深**：总权益 $233.93（+9.5%）[Binance API 08-24 00:20 CST]；coinos P0第3期未执行；**Quant报告管道停更2个月+（reports/最新06-17）**；AI-Scalpel仓库404消失
