# A9 本周工具与学习报告 — 第35周 (2026-08-31 周一)

> **执行时间：** 2026-08-31 09:00-09:45 BJT（每周研究cron）
> **当日健康状态（取自今日daily_inspection）：** 🟢 A4执行链17次全completed合规运行（认知纠正：08-30"双保险禁用"为第3次误禁已恢复）· **锁冲突错峰修复已实锤生效**（A8报告09:25 completed，08:00 TimeoutError消失；A6审计09:25触发）· 总资产$220.87（Binance实核，-2.9%）· 剩余裂缝：A5经验管道停摆29天 · A3 signals陈旧58h=老李停扫预期内 · ETH集中度85%
> **研究通道：** 🔧 本次 web_search 后端503（代理故障）+ 本机直连GFW阻断(curl 000) → **改用AWS SOCKS5代理(127.0.0.1:1080, SSH隧道) + GitHub API + Bing/DDG 完成全六维搜索**。此通道已实测可行（GitHub API 200/DDG 202），建议固化进周研究流程（详见文末）。
> **本周研究聚焦：** ①**QuantDinger生态**（老李08-28点名"现成策略来源"——11.2K stars实锤调研）②AI交易Agent记忆层（tradememory-protocol直击A5经验管道缺口）③退出策略缺口第2周追踪（MASTER 52.5% wrong_exits）④网格自适应对照

---

## 入口检查：上周(第34周)→本周进展

| 上周建议 | 本周状态 | 进展 |
|:---------|:---------|:----|
| 🔴 阶梯止盈落地(P1) | ⏳ **未落地（连续第2周）**——A5管道停摆29天是前置阻塞 | 🔴 持续 |
| 🔴 ETF/监管事件日历入A3(P1) | ⏳ 未评估；ZEC已高位减速（08-31 -1.26%浮亏），ETF叙事轮动进入兑现期 | 🟡 观察 |
| 🟡 动量回调入场标签(P2) | ⏳ 未落地 | ↔ 未执行 |
| 🟡 Bull/Bear反向论证(P2) | ⏳ 未落地（NBZ已有反向验证字段雏形） | ↔ 未执行 |
| 🟡 enrich阈值重审(P2) | 🔴 恶化至80%（56/70 boosted） | 🔴 连续4周 |
| 🟡 Volume Filter(连续13周) | ⏳ 仍被压制 | 🔴 第14周 |
| 🟢 SSH恢复稳定性 | 🟢 SSH_OK延续（A7 GFW阻断但SSH通道全通） | 🟢 |
| 🆕 A4执行链合规认知 | 🔴 08-30误禁第3次 → 🟢 08-31已纠正恢复 | 🟢 认知固化 |

### 第34→35周关键变化
| 痛点 | 第34周(08-24) | 第35周(08-31) | 变化 |
|:-----|:--------------|:--------------|:----|
| A4执行 | 5笔FILLED·回传sig_1660 | **17次全completed合规运行** | 🟢 |
| A4 USDT free | $0.26(现金率0.1%) | $7.81(<MIN_BUY $8,弹药枯竭) | 🔴 |
| 总资产 | $233.44 | **$220.87(Binance实核)** | 🔴 -5.4% |
| MASTER correct_exits | 零增长20天 | **零增长29天** | 🔴 恶化 |
| A8每小时报告 | 08:11 TimeoutError(第1天) | **错峰25分修复完成,09:25✅** | 🟢 修复 |
| A6审计 | 08-15撞锁未跑 | 09:25错峰触发✅ | 🟢 修复 |
| 锁冲突 | #79768单发 | **第3天连发→已根治(错峰)** | 🟢 |

---

## 六维研究（全网搜索 · GitHub API + Bing/DDG）

### 维度1 · 新工具扫描（本周核心）

| 工具 | 热度/状态 | 一句话 | 评估 |
|:-----|:---------|:-------|:-----|
| **⭐ QuantDinger** (OpenByteInc) | **11,244 stars** · Apache 2.0 · 08-30活跃 · v5 | **开源AI Trading OS**：AI研究→策略代码→回测→纸面/实盘→监控全链路，自托管 | **本周最大发现**。**支持交易所：Binance/OKX/Bitget/Bybit/Gate/HTX**（HTX=老李在用账户！）。Strategy API V2（意图/仓位/风险/回测/实盘运行时）+ Agent Gateway + MCP server + 中文文档。老李08-28指定生态实锤。详见落地评估#1 |
| **⭐ tradememory-protocol** (mnemox-ai) | 1,412 stars · MIT · 维护模式 | **AI交易Agent的记忆层**：每笔交易+结果+错误自动记录，SHA-256防篡改审计链；交易前检索"上次同类条件怎么结束"；outcome-weighted recall；连败检测/回撤警报 | **直击A5经验管道缺口**。我们A5=手写JSON+LLM cron写入，停摆29天/win_rate 10.2%；它=交易前问记忆+交易后自动记。不引入MCP依赖，借鉴其"检索-记录"闭环设计。详见落地评估#2 |
| TraderAlice/OpenAlice | 6,856 stars · TS · 08-31活跃 | 个人华尔街：覆盖股/币/商品/外汇/宏观，研究到执行全流程AI Agent | P3观察——宏观全能型，TypeScript栈与系统Python不符；研究边界与ZH重叠 |
| Lumiwealth/lumibot | 2,013 stars · Python | 可回测的AI交易Agent框架（股/期权/币/期货/外汇） | P3——回测框架参考，与freqtrade定位重叠 |
| **OctoBot** (Drakkar) | 6,494 stars · 08-30活跃 | 开源交易bot：AI/Grid/DCA/TradingView策略，Binance+Hyperliquid | P2——**网格策略对照物**：验证我们网格参数（±2.5%/re-center）与行业实现一致性 |
| **martin-binance** | 225 stars · 08-18活跃 | SPOT自适应**反网格**（马丁变体） | P2——网格策略变体参考；马丁风险高，仅研究不复刻 |
| akquant (akfamily) | 2,109 stars · Rust+Python | 高性能开源量化回测框架 | P3——回测备选 |
| backtrader | 23,026 stars | Python回测库标杆 | 已知维持P3 |
| 本周新星（created>07-01） | polymarket bots(136/106) · ai-robinhood-chain(128) · PeakPulse(90) | 预测市场bot/ML顶部雷达等 | ❌ 全部P3以下——预测市场/meme类与现货低吸体系无关，质量参差不评估 |

### 维度2 · 新数据源扫描

| 数据源 | 类型 | 评估 |
|:-------|:-----|:-----|
| CoinCodeCap《8 Best Crypto Market Data APIs》(08-2026) | API对比清单：CoinStats(钱包/市场/DeFi全能)/CoinGecko/Binance/Bitquery等 | P3存档——系统已有Binance+CG+DexScreener+Etherscan+Solscan 9源全活（A8 errors=[]），边际价值低；留作源故障备选 |
| Bitquery《Best Crypto Market Data APIs 2026》 | 机构级feeds vs 零售聚合 vs 链上indexer分层对比 | P3同上 |
| TheLedgerMind《Best On-Chain Analytics Tools 2026》(12平台实测) | 链上工具对比（追踪$2T+交易） | P3——Nansen/CryptoQuant在等待清单($500+门槛)，此清单可作选型参考 |
| CoinGecko Learn《Best APIs 2026》 | Data/Exchange/RPC API分类 | P3——与现有CG源同源 |

**结论：** 数据源维度无新增缺口——系统9源全活且A8采集正常。Nansen等待$500+门槛不变。

### 维度3 · 新策略扫描

| 策略 | 来源 | 核心规则 | 与系统匹配度 |
|:-----|:-----|:---------|:------------|
| 2026动量策略（具体规则版） | trendrider《Crypto Momentum Trading Strategies 2026》（500+ BTC/ETH回测） | RSI+volume+breakout精确入场规则；退出规则明确 | 🟡 与A3动量信号/A4低吸同向；具体规则页未抓全（反爬），从摘要看无超出系统认知的新颖点 |
| 均值回归何时胜过趋势 | coinquant.ai（BTC日线2018-2026回测） | 均值回归非万能——特定市场状态下才胜过趋势策略 | 🟡 **印证系统"低吸波段"逻辑**：均值回归只在区间震荡市有效；当前Top200分化整理（rp中高位）正是其适用窗口 |
| 横截面动量vs均值回归 | GitHub prams2104/crypto-momentum-backtest | 严格的train/validation分割评估两策略 | 🟡 方法论文档——可借鉴其"train/val分割"到A5回测验证（防过拟合） |
| 动量回调入场 | fortraders（上周已评） | 等回踩不追突破 | ⭐ 维持P2，与"脉冲一日游第8次验证"互相印证 |
| 网格自适应 | 本周未获新高质量资料（DDG/Bing被反爬） | — | ↔ 维持P3（martin-binance/OctoBot可作对照实现参考） |

### 维度4 · 案例学习（别人怎么亏/怎么赚）

| 案例 | 要点 | 系统映射 |
|:-----|:-----|:---------|
| **MASTER_EXPERIENCE 实况（系统自身最大案例库）** | total 1529笔：correct 160(10.2%) · **wrong_exits 802(52.5%)** · too_early 571(37.4%) · total_pnl +$3.26 | 🔴 **退出仍是唯一最大问题（89.9%）**——入场正确率高，卖错+卖早占9成。第2周确认：阶梯止盈是数据驱动的第一缺口，**但A5管道停摆29天使其无法落地验证**（先修管道！） |
| 脉冲一日游第8次验证（NIL/COTI/TST/BROCCOLI714批量退潮） | 追高单日脉冲必套 | ✅ 系统坚持低吸=正确；动量回调入场(P2)应加速落地 |
| 73%自动化交易者头6个月亏钱（goatfundedtrader,上周） | 主因=杠杆放大错误 | ✅ 系统现货+网格无杠杆，方向正确延续 |
| 多Agent系统失败率高（Medium $11,000测试,上周） | 仅1/10多Agent系统真正work | ⚠️ **本周QuantDinger 11.2K stars案例反向提示：成熟多Agent系统可以work**——差异在工程化（PostgreSQL状态/持久worker/审计日志）。我们缺的正是工程化而非架构 |

### 维度5 · 竞品扫描（AI量化系统）

| 竞品 | 架构 | 对比结论 |
|:-----|:-----|:---------|
| **QuantDinger** (11.2K) | 完整OS：API+5类worker+PostgreSQL/Redis双存储+Agent Gateway+MCP+可观测 | **架构工程化标杆**：我们A1-A9链=同分工但无持久worker/审计日志/状态管理。**差距=工程化层**（锁冲突#79768/经验管道停摆/回传断裂都是工程化不足的症状）。不迁移，但学习其进程职责分离（trading-worker/ scheduler-worker/celery-worker分离）可根治我们"单进程多cron抢锁"问题 |
| OpenAlice (6.9K) | 全能Agent（研究→执行） | 功能广度远超，但非专注加密现货；P3 |
| lumibot (2K) | 回测AI agents | 与freqtrade重叠；P3 |
| OctoBot (6.5K) | 策略插件化bot | 网格对照；P2 |
| TradingAgents (99.5K,上周) | LLM多Agent辩论 | 辩论机制借鉴P2延续 |
| Cobo Agentic AI共识（上周） | Sentiment/Technical/Risk分工 | 我们A7/A3/A5=同构，验证方向正确 |

### 维度6 · 工具缺口检查（A5经验档案数据驱动）

**MASTER_EXPERIENCE.json 实况（08-31读取）：**
```
version: v2.0 | last_updated: 08-28T22:17 | rules: 82
total_trades_analyzed: 1529 | correct_exits: 160 | wrong_exits: 802 | too_early_exits: 571
win_rate: 10.2% | total_pnl_usd: +$3.26
```

**数据解读（与上周对比）：**
- wrong_exits 802/1529 = **52.5%**（上周801，+1笔）——退出问题持续占主导
- correct_exits **零增长29天**——不是"没有错误卖出"，是**经验采集管道停摆**（stats内层last_updated=08-08,外层=08-28）
- **工具缺口排名：**
  1. 🔴 A5经验采集管道修复（前置阻塞，停29天）——**所有退出策略改进都无法被验证**
  2. 🔴 阶梯止盈机制（wrong_exits+too_early_exits=89.9%可同时缓解）——连续2周第一缺口
  3. 🟡 A4交易前"经验检索"（tradememory概念：买前查MASTER同类条件历史胜率）
  4. 🟡 回测train/val分割方法（防过拟合，prams2104方法论）
  5. 🟡 网格参数对照验证（OctoBot/martin-binance）

---

## 落地评估（赋能Agent / 接入步骤 / 优先级 / 理由）

| # | 优先级 | 项 | 赋能 | 接入步骤 | 不接入理由（如适用） |
|:-:|:------|:---|:-----|:---------|:-------------------|
| 1 | **P1** | **QuantDinger研究环境部署** | A3/A5/A4 | ①AWS部署（Docker Compose，需评估EC2内存≥4GB——当前2GB可能吃紧）②用其回测+纸面交易验证A3信号历史胜率 ③**HTX适配器可直接对标老李HTX账户** ④仅作研究/纸面环境，**不迁移实盘执行链** | 不接入实盘理由：总资$220远小于OS运维成本；现有freqtrade fork网格+follow_engine v6已运行稳定；迁移=重构风险 |
| 2 | **P1** | **A5经验管道修复 + tradememory"检索-记录"概念借鉴** | A5/A4 | ①先修A5采集停摆（correct_exits零增长29天根因排查）②借鉴tradememory闭环：A4执行前查MASTER同类条件历史（outcome-weighted recall）③A4执行后自动追加记录（不依赖LLM cron单点） | 无——数据89.9%退出问题+管道停摆双重实锤 |
| 3 | **P1** | **阶梯止盈落地**（第2周） | A4/A5 | A4退出逻辑改"分3档止盈(+10/+20/+30%各1/3)+移动止损"；MASTER加ladder_exit标签 | 前置依赖#2管道修复 |
| 4 | **P2** | 动量回调入场落地 | A3/A4 | rp高位+缩量+近前高打"突破观察"；A4等回踩前高支撑+放量2x确认 | 无——脉冲一日游第8次验证+动量回调方法论双支持 |
| 5 | **P2** | 网格参数对照验证 | A4 | 用OctoBot/martin-binance实现对照我们±2.5%网格与re-center逻辑；不引入代码，纯参数研究 | 网格稳定运行（NAVIGATION.md主策略），改动需Commander决策 |
| 6 | **P2** | enrich阈值重审（第4周） | A3/A2 | 80% boosted（56/70）连续4周>75%，Commander调低enrich加分上限 | 无 |
| 7 | **P3** | OpenAlice/lumibot/akquant观察 | — | 存档备选 | 与freqtrade/现有链重叠 |
| 8 | **P3** | 数据源2026备选清单 | A1/A8 | CoinCodeCap/Bitquery清单存档为源故障fallback | 9源全活无缺口 |
| 9 | **P3** | 新星项目（polymarket等） | — | 不评估 | 与现货低吸体系无关 |

---

## 系统洞察

### 洞察① 本周系统最大工程化进步=锁冲突根治（错峰模式）
- 08-29~08-31连续3天 #79768（A8报告/A6审计/ZH全网侦查撞A4持锁）→ 08-31错峰修复（A8→25分/A6→09:25/ZH→周一08:25）
- **09:25实测验证**：A8报告 completed（08:00 TimeoutError消失）+ A6审计触发 + fund_flow.md 09:29产出 + snapshot 09:25:08 errors=[]
- **普适模式**：A4执行节点每30分钟持TERMINAL_CWD锁~18分钟（整点/半点启动）→ **其他cron一律避开整点/半点±10分钟窗口，安全启动位=每小时25分**。建议写入AGENTS.md协同细则，防新cron再踩。

### 洞察② QuantDinger = 老李"外部更强资源"方向的最佳候选（工程化差距可视化）
- 老李08-28：「系统变强」=引入外部更强资源，QuantDinger生态=现成策略来源
- 实锤：11.2K stars、v5活跃（08-30）、**Binance+HTX适配器**、Strategy API V2、MCP、中文文档
- **但接入形态要清醒**：不是把实盘迁进去（$220总资不值得OS级重构），而是**部署为研究/回测/纸面环境**——验证A3信号胜率、回测阶梯止盈参数、对标HTX策略。与freqtrade回测框架P3项合并评估，QuantDinger功能更全（多交易所+AI研究+纸面实盘）。
- 对比我们：QuantDinger的进程职责分离（trading/scheduler/celery分离worker）正是我们锁冲突/回传断裂/经验停摆的根治模板——**工程化差距是本周竞品扫描最核心结论**。

### 洞察③ A5经验管道停摆29天=所有策略改进的验证黑洞
- correct_exits零增长29天 + stats内层last_updated停在08-08 → 阶梯止盈(连续2周P1)/退出策略优化全部无法用数据验证
- **根因假设**：经验采集依赖LLM cron单点写入（402/锁冲突都会打断），无自动兜底。tradememory的"执行层自动记录"设计是正解方向——A4 executor直接写经验，不经过LLM cron。
- 这是本周第2优先级（在QuantDinger研究环境之前——先让系统能验证，再引入外部验证工具）。

---

## 推荐落地（下周验证）

| # | 优先级 | 项 | 验证点 |
|:-:|:------|:---|:-------|
| 1 | **P1** | A5经验采集管道修复（根因排查：executions.db查A5采集cron 08-08后失败记录/402/锁冲突） | MASTER correct_exits开始增长；trades/目录有新文件 |
| 2 | **P1** | QuantDinger部署评估（AWS内存检查→可行则部署纸面环境） | AWS free -m ≥4GB？docker compose up成功？Binance/HTX适配器连通 |
| 3 | **P1** | 阶梯止盈设计（依赖#1管道） | MASTER出现ladder_exit标签 |
| 4 | **P2** | 动量回调入场落地 | A3"突破观察"标签出现；A4回踩入场记录 |
| 5 | **P2** | enrich阈值重审（第4周） | boosted比率<75% |
| 6 | **P3** | 网格对照研究（OctoBot实现） | 对照报告 |

---

## 📌 研究通道固化建议（本次实测）

**GFW+web_search后端503时的可用研究通道：**
```bash
# AWS SOCKS5代理（本机SSH隧道,端口1080）——实测GitHub API 200 / DDG 202
curl -x socks5h://127.0.0.1:1080 'https://api.github.com/search/repositories?q=crypto+trading+agent&sort=stars'
# DDG HTML解析（正则抓 result__a/result__snippet）; Bing需处理/ck/a重定向+base64解码
# GitHub raw README（无需API额度）: raw.githubusercontent.com/<owner>/<repo>/<branch>/README.md
```
- 已实测：本机直连000（GFW）· web_search后端503（代理故障）· **AWS隧道全通**
- 建议：此通道写入 skill zq-a9-research-agent 的周研究流程（替代 anysearch 依赖），并记录"A8/A6/ZH 25分安全窗口"防新cron撞锁

---
*A9学研官 2026-08-31 09:45 BJT | 数据源：GitHub API(限流内) + DuckDuckGo/Bing + MASTER_EXPERIENCE.json + executions.db + jobs.json + 今日daily_inspection*
*A9研究边界：工具/数据源/策略/市场案例。不做交易员人格研究。*
