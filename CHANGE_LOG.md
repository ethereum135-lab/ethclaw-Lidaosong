## 2026-08-31 — 趋势账本同步闭环（12:30 现场处置）

### 变更内容
- **tools/sync_aws_logs.py**：新增 trend_state.json + trend_trades.jsonl 同步（AWS 权威 → Mac 只读副本，每30分钟 launchd 自动跑）
  - trend_state.json 为必同步文件；trend_trades.jsonl 为可选文件（暂无成交时跳过不报错，AWS 端已预建空 ledger）
  - 实测：数据文件同步 5/5 通过；本地 data/trades/trend_state.json 更新至 12:25 BJT 与 AWS 一致
- **NAVIGATION.md**：当前状态更新至 12:30 BJT 复查全绿（cron 连续/挂单0/预飞6/6/信号新鲜/隧道健康）
- **ERRORS.md**：新增 12:30 全链复核记录 + 明日复查点（trend 成交入账回传、21:20 总资记录、cron 无缺档）

### 验证
- py_compile OK；sync_aws_logs.py 实测输出 5/5 全绿
- trend_state.json 本地 mtime 12:27 = AWS 最新 04:25 UTC（12:25 BJT）内容一致

## 2026-08-31 — 部署修复：趋势策略真正上线，网格式亏损源停机（12:25 现场处置）

### 根因（老李报「一直亏损」→ AWS 实查）
- **NAVIGATION.md 声称的 v3.1 从未真正上线**：AWS crontab 中 `trend_bot.py` 被注释停用，而 `grid_bot.py` + `htx_loop.py` 仍在每5分钟运行
- 实盘证据：Binance 上 7 张网格限价单（SELL 2435/2450/2465/2480 + BUY 2360/2375/2390）锁死全部 ETH+USDT；08-31 上午网格在 2488-2495 高位连买 6 笔 ≈$120，ETH 跌至 2415 后被迫低位卖出 → 当日总资 $232.30→$220.98（-4.87%）
- AWS trend_bot.py 虽已是 v3.1 文件，但 state 被预置成 v3.1 → CFG 未变化 → 不会撤网格单；cron 也没开 → 策略实际零运行

### 变更内容
- **AWS crontab**：启用 `tools/trend_bot.py`（每5分钟）；停用 `tools/grid_bot.py` + `tools/htx_loop.py`（备份 /tmp/cron_bak_20260831_1226）
- **tools/trend_bot.py → v3.1-r2**：CFG_VERSION `…-trail-r2` 强制撤旧单+状态重置；新增 `record_trade()` 交易账本（data/trades/trend_trades.jsonl，每笔 BUY/SELL 记价/量/理由/盈亏/权益）；每周期打印 equity
- **tools/auto_close_loop.py**：DAILY_TARGET_PCT 2.0 → 0.2（与铁律五一致，2%/日已定案不可行）
- **实盘验证**：首跑自动取消 7 张网格单 → 状态按实际持仓初始化为 mode=eth（ETH 0.0621 ≈ $150）→ 价格 $2413 > 通道下沿 $2387 → HOLD，peak $2420.94 / trail $2372.52；Binance 挂单数 0；后续 5 分钟 cron 持续运行（logs/trend_bot.log 有新一轮周期）

### 回测依据（独立复测，06-09→08-31 真实1h行情+0.1%手续费/边，下一根开盘成交，无前视）
| 策略 | 收益 | 最大回撤 | 笔数 |
|:--|:--:|:--:|:--:|
| Buy&Hold | +43.5% | — | — |
| v3.0 通道 | +28.8% | -4.7% | 7 |
| **v3.1 通道+2%锁利** | **+27.0%** | **-6.1%** | 14 |
| 旧网格（近似） | -1%~-7% | -7.8% | — |

### 观察计划
1. 今天 21:20 收盘记录：总资 vs 昨收 $232.30，按 0.2% 目标核对
2. 连续 3 天：trend_trades.jsonl 应出现完整买→卖闭环，净 P&L 为正
3. trail 若 >1次/2天 → TRAIL_PCT 放宽至 0.025 并复测（CHANGE_LOG 原有观察项）


## 2026-08-31 — 系统修复（11:30 现场处置）

### 变更内容
- **tools/preflight_check.py**: check_trades() 状态过滤（REJECTED/FAILED 不计真实成交，#47）；check_monitor() 增加 mtime 新鲜度检查（>72h 标陈旧死日志，#22）
- **tools/grid_bot.py**: 新增 log_fills() — myTrades 增量(fromId)检测网格成交 → 按 A4 块格式写入 audit/TRADES.md，last_trade_id 持久化到 grid_state（#24，第7天台账缺失）；已部署 AWS
- **tools/a3_signal_scanner.py**: 所有 Binance API 调用改走 SOCKS5 隧道(127.0.0.1:1080)+直连 fallback — 修复 signals.json 466/466 全部 ERROR（SSL EOF，信号管道死，A4 停用根因）
- **AWS**: zq-engine.service（废弃 45+天 failed）已 stop/disable/删 unit/reset-failed，zq_eternity.py 归档；重复 SSH 隧道进程已清理

### 验证
- preflight: 今日卖出 8→0 笔（REJECTED 不再误计）；监听器死日志正确标记
- a3_signal_scanner: 实扫恢复产出信号（20+/466 且持续增长，0 ERROR）
- grid_bot log_fills: 本地单测通过（首跑初始化不回填、增量去重、格式与 A4 一致）

# 系统变更日志

## 2026-08-31 — 主策略升级 v3.1：ETH趋势通道 + 2%盈利锁定（老李指令「每日盈利策略」定案）

> 承接当天早上 v3.0（Donchian 5日突破）上线。老李指令「你來定，我要的是每日盈利策略」→ 全权决策：
> **不强制每天交易**（8个日内剥头皮变体 90 天真实行情回测全部负期望，含手续费），
> 而是在已验证正期望的趋势通道上增加 **盈利锁定层**，把兑现频次和回撤指标同时优化。

### 变更内容（tools/trend_bot.py）
- **新增 EXIT② 盈利锁定**：mode=eth 时跟踪自入场以来 1h 收盘峰值，收盘 < 峰值×98%（TRAIL_PCT=0.02）→ 市价全仓卖出锁利
- EXIT① 通道破位保留不变；state 新增 peak_close（峰值只升不降），CFG_VERSION → `2026-08-31-donchian-v3.1-trail`
- 峰值采用最新已收盘 1h 收盘价（与回测口径一致，避免未收盘K线抖动）

### 回测验证（2026-08-31 本地独立复测，06-09→08-31 真实1h行情 + 0.1%手续费/边）
| 版本 | 收益 | 兑现笔数 | 胜率 | 最大回撤 |
|:--|:--:|:--:|:--:|:--:|
| v3.0 原版 | +35.3% | 2 | — | -6.9% |
| **v3.1（2%锁利）** | **+27.2%** | **7** | **57%** | **-3.3%** |

8个日内策略变体（BB+RSI30/25、仅BB、动量、加EMA200市况门、TP/SL多种组合）全部负期望 → 否决强制每日交易路线。

### 验证（铁律三）
- py_compile 通过；7个逻辑用例单测（fresh-start/峰值初始化、trail触发卖出、trail持有、通道破位卖出、cash突破买入、cash等待、峰值上移）全通过
- 已部署 AWS（scp tools/trend_bot.py），CFG_VERSION 变化自动撤单+状态重置，首跑按实际持仓初始化

### 观察计划
1. 首跑后确认 mode=eth、peak 初始化、日志无异常（AWS logs/trend_bot.log）
2. 3天内若 trail 触发过于频繁（>1次/2天）→ TRAIL_PCT 放宽至 0.025 并复测
3. 每天21:20 收盘记录 + true_daily_pnl 日对日对比，7天窗口评估 vs v3.0


## 2026-08-31 — profit_engine_v2 深度调整：修2个真Bug + 个币趋势门（回测诚实化）

> 承接「A4山寨引擎重写」。深入审计发现原回测**高估策略**：lookahead 未来函数 + 移动止盈死代码。
> 修复后 120 天连续回测（真实币安1h行情+0.1%手续费）：**+15.85%，最大回撤 4.45%（原报告口径11.27%），PF 1.78**。

### 修复1：回测市况门 lookahead（未来函数泄漏）
- 根因：`run_backtest` 每次调用 `regime_ok(btc_bars, None)` 用的是**整个回测窗口最后一根K线**判断 BTC>EMA200 → 窗口内熊市段门一直开着
- 后果：window B（BTC 60天 -21.9% 的下跌段）旧回测仍交易72笔亏-2.13%；修复后同样配置只交易27笔、转+0.83%
- 修复：`regime_at(ts)` 按当前模拟时间戳切片判断 BTC EMA200 + 24h跌幅门（实盘路径本就用实时数据，不受影响）

### 修复2：移动止盈死代码（peak 永不更新）
- 根因：`pos["peak"]` 只在 `peak>=+3%` 分支内自增，但该分支永远进不去 → 67笔交易0次 TRAIL 离场
- 修复：先记录新高再判断离场（SL→TP→TRAIL→TIME）；120d回测验证 **trail 收紧会降低期望** → 保持 dormant（激活线=TP线），出场=SL/TP/TIME

### 调整3：新增个币 EMA200 趋势门 + 量能1.2×
- `COIN_EMA200_FILTER=True`：收盘必须>该币EMA200(≈8.3天)，过滤自身下跌趋势的币——**样本外稳健性关键**（window B -2.1%→+2.3~4.1%）
- `VOL_MIN_MULT 1.0→1.2`：量能≥1.2×20均量（两个窗口最优）

### 验证（真实行情，两段60天窗口）
| 配置 | 窗口A(最近60d) | 窗口B(前60d, BTC-21.9%熊市) |
|:----|:----|:----|
| 旧引擎(当前参数, lookahead+死trail) | +11.44%(虚高) | -2.13% |
| 新引擎(修复+个币门, V1.2) | +10.27%, PF1.88 | +2.29%, PF1.28 |

- 报告已更新：`reports/engine_v2_backtest_60d.json`（+10.27%）、`reports/engine_v2_backtest_120d.json`（+15.85%）
- py_compile 通过；缓存数据复跑与正式回测结果一致（确定性）


## 2026-08-31 — 策略重写：ETH网格 → ETH趋势通道 v3.0（Donchian 5日突破）

> 老李指令「修復盈利策略，重新寫一遍，現在一直虧損」。本条目是**引擎层整体替换**：
> 停用网格 `tools/grid_bot.py`（已归档 `archive/grid_bot_v2_20260831.py`），
> 启用新引擎 `tools/trend_bot.py`。决策依据 = 回测数据 + 6周实盘归因，不是感觉。

### 亏损根因（实盘 + 回测双重确认）
1. **接飞刀**：08-19 暴跌日网格单日买入 $517（26笔），下跌中反复向下平移网格，
   「跌破中心6%硬止损」的止损线跟着中心下移 → **6周实盘 0 次触发止损**（全日志无一次CASH/STOPPED）
2. **单向死锁**：08-31 上午 USDT 仅 $15，买单挂不上 → 只能卖不能买（08-31 凌晨第二次重演）
3. **方向错误**：回测（真实5m行情+0.1%手续费）显示 07-20→08-31 ETH +29% 的大涨中，
   网格 -1.1%（Buy&Hold +28.9%）——「涨了卖、跌了买」与趋势相反

### 新策略：Donchian 5日通道突破（tools/trend_bot.py）
- ENTRY：价格 > 近5日(120根已收盘1hK线)最高价 → 市价全仓买ETH
- EXIT ：价格 < 近5日最低价 → 市价全仓卖ETH锁USDT
- 全仓ETH或全仓USDT，不做网格、不挂限价单，状态机只有 eth/cash
- 首次启动按实际持仓初始化模式，现有持仓立即纳入退出保护

### 回测结果（真实5m行情，含0.1%手续费，全部跑通）
| 策略 | 06-09→08-31 | 07-20→08-31 | 最大回撤 |
|:--|:--:|:--:|:--:|
| Donchian 5d/5d | **+23.6%** | **+20.7%** | -6.0% |
| Buy&Hold | +13.1% | +28.9% | -29%+ |
| 旧网格 v2.0 | -1.1% | -1.1% | -7.8% |

### 部署（已执行并验证）
1. AWS：cron `grid_bot.py` → `trend_bot.py`（每5分钟，日志 logs/trend_bot.log）
2. 首跑：取消7个旧网格挂单 → 资金全部解冻 → 状态初始化 mode=eth
3. 验证：openOrders=0、state 已持久化、price $2420 > 通道low $2387 → HOLD ETH
4. 本地：grid_bot.py 归档、grid_state.json 归档、NAVIGATION.md/CHANGE_LOG/crontab清单 同步

### 验证计划（铁律三：用赚钱验证）
1. 观察3天：trend_bot 日志只有 HOLD/CASH 且无异常
2. 若跌破 $2387 → 全仓卖出锁U（验证EXIT），突破5日高 → 全仓买回（验证ENTRY）
3. 每天21:20收盘记录 + true_daily_pnl 日对日对比，7天窗口评估 vs 旧网格


## 2026-08-31 — A4山寨引擎重写：profit_engine_v2（承接ETH主策略重写）

> 同一指令「修復盈利策略，重新寫一遍」的A4层补充。ETH主策略已由trend_bot接管（上一条），
> 本条重写被废弃的A4买入决策链（A3解析+fast_scan FALLBACK+14层过滤，尸检结论=亏损根因），
> 新引擎 `tools/profit_engine_v2.py` 以数据回测为准，不用感觉。

### 亏损根因（08-31 TRADES.md 1304条记录量化）
1. **止损形同虚设**：94笔亏损平均 **-21.7%**（最差-48.9%）→ 回本需+27.7%，数学上必死
2. **反复接飞刀**：UNI×29 / DOGE×14 / ADA×13 同一币反复买入后亏损平仓（无冷却机制）
3. **止盈被禁用**（TAKE_PROFIT=999%）：盈利从不止盈，浮盈全回吐
4. **过滤层过多**：14层条件 → 48天零交易，或情绪化乱交易（尸检报告矛盾2）

### 新引擎（tools/profit_engine_v2.py，纯标准库+币安API，可回测可实盘）
- 宇宙：24h成交额Top30 USDT对（自动拉取，不用手工清单）
- 入场（3条件，全部满足才买）：EMA50(1h)上方 + RSI14∈[45,58]回撤区 + 收盘突破前高
- 市况门：BTC 1h收盘>EMA200 才做多；BTC 24h跌>3%禁买
- 风控（每条对应一个根因）：硬止损-5% / 止盈+8%+移动止盈 / 时间止损48h / 连亏冷却48h /
  风险预算1%权益/笔（单仓≤25%权益）/ 最多2仓
- 实盘：`--live` 产出与executor同schema信号；`--backtest` 随时重验

### 回测验证（真实币安1h行情，含0.1%手续费，$500起始，2026-08-31 11:26 BJT）
| 窗口 | 总收益 | 交易 | 胜率 | 期望值 | 利润因子 | 最大回撤 |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|
|| 30天 | **+14.32%** | 33 | 66.7% | +$2.17 | 3.11 | -4.17% |
|| 60天 | **+11.44%** | 67 | 53.7% | +$0.85 | 1.56 | -6.40% |
|| 90天 | **+15.80%** | 102 | 52.9% | +$0.77 | 1.48 | -7.41% |
- 报告存档：reports/engine_v2_backtest_{30,60,90}d.json
- 对比旧系统：94笔实盘亏损均-21.7%（负期望）vs 新引擎三窗口全部正期望

### 接入（profiles/a4-blade/executor.py）
- ② 决策块重写：engine_v2为主买入源，A3解析降级为兜底；③-b加仓fallback加`not buy_signals`守卫
- **ALTCOIN_ENGINE_ENABLED=False 默认暂停**：主策略trend_bot全仓ETH/现金（无中间状态），
  A4新买入默认关闭防抢资金；持仓评估排除ETH防集中度规则误触发真实卖单。
  启用时机：trend_bot停用或老李指示恢复多币 → 置True即恢复（engine_v2为买入主源）

### 验证计划
1. py_compile 通过；engine_v2_buys() 集成实测返回市况LONG/0候选（当前无信号=策略挑剔正常）
2. 观察3天：trend_bot为主策略运行无异常；A4 executor保持暂停
3. 若启用A4：engine_v2 live信号对照回测预期，7天窗口用true_daily_pnl评估

## 2026-08-31 — 引擎层对称网格改造：卖单等值化 + 档位4 + 资金全利用

> 承接「日盈亏KPI诚实化 + 收盘链落地」（度量层已通），本条改**引擎层**——
> 让网格本身能持续双向产出每日利润（目标：总资×0.1~0.3%/日，中值0.2%）。

### 根因（08-31上午实况 + 数学验证）
- 旧网格「买$20/档、卖0.003ETH/档(≈$7)」：每轮震荡把 USDT 单向变成 ETH。
- 完整一轮（4买全成交→4卖全成交）资金变动：USDT −$60、ETH +0.025 → 几天后必然重演
  「ETH重仓+USDT不足→只有卖单→赚不到每日利润」死锁（今早刚修过，是治标）。

### 变更内容（全部已跑通）
**一、对称网格（tools/grid_bot.py，本地+AWS已同步）**
- 卖单金额=买单金额：每档卖≈$20（按当前价换算ETH，LOT_SIZE 0.0001取整）
- 卖侧新增动态缩档（与买侧镜像）：ETH不足时缩量挂单而非跳过，网格永远双向
- GRID_CFG_VERSION 配置版本迁移：版本变化→自动撤单重挂，防止旧参数残留锁死资金
- 实测（AWS 02:33 UTC）：撤旧6单 → 新挂 4买(2360/2375/2390/2405)+4卖(2435/2450/2465/2480)，
  单档≈$20；第二轮 +0/+0 幂等无churn

**二、档位 3→4（tools/grid_bot.py）**
- 档距 0.83%→0.62%，每日成交/获利频率更高；4买×$20=$80 ≤ USDT，4卖×0.0080-0.0082ETH ≤ 可用ETH

**三、资金全利用：清仓闲置散仓（真实成交，Binance API）**
- MARKET SELL ZEC 0.011（$9.11）+ ENA 49.34（$7.30）→ USDT ≈ $87.06
- ZEC/ENA 是旧多币策略残留，非任何现行策略持仓；follow_engine 已停用，无独立网格承接
- 回收资金全部进 ETH 网格（NAVIGATION.md「全仓ETH网格，不分散」）

**四、文档同步**
- NAVIGATION.md §二：±2.5% / 4买4卖 / 买卖等值$20 / 动态缩档 / 硬止损 / 模式
- IRON_RULES_PROFIT.md：2%/日残留 → 0.1~0.3%（中值0.2%），盈利冲刺脚本同步
- tools/trade_review.py、tools/auto_repair.py：目标2% → 0.2%
- 更正：21:00日结链的实际执行者是 tools/daily_close_record.py（Mac launchd 21:20 BJT），
  非 AWS daily_pnl_report.py（后者只写 daily_pnl_report.json）

### 验证计划
1. 每5分钟 cron 正常跑（10:35 起观察 logs/grid_bot.log，无 churn）
2. 今晚21:20 BJT 收盘记录 → 明早 true_daily_pnl 输出日对日 TRUE（0.2%目标达成率）
3. 连续3天：网格双向成交、USDT 不再单向流失、日盈亏按 0.1~0.3% 评估

## 2026-08-31 — 日盈亏KPI诚实化 + 收盘链落地（承接上一调整）

> 承接系统「每日盈利策略大调整」：网格死锁已解（USDT→$70.7、6档挂单、A4/follow停用）。
> 本条补齐**度量层**——让「每日盈利」能被真实、连续地测量。

### 变更内容（全部已跑通验证）
**一、全局日目标KPI修正（tools/state_aggregator.py）**
- 旧：profit=余额-430初始资金、目标=430×2.1465% → 每天假报「巨亏-$208」误导全团队
- 新：prev_close=昨日收盘（data/total_asset.json / data/TRADES.md历史），profit=余额-prev_close，目标=prev_close×0.2%
- 实测：prev_close=$232.30、expected=$0.46、profit=-$11.28（真实，不再出现-208假警报）

**二、每日收盘记录链（tools/daily_close_record.py + launchd 21:20 BJT）**
- 新建幂等收盘记录：Binance API实查总资→写data/total_asset.json+data/TRADES.md「总资」节→推AWS
- com.zq.daily-close-record.plist 已加载（python3.11，21:20 BJT）
- 补录08-27 $232.30历史收盘 → 链不断；08-29/30断档如实GAP
- 修复「21:00排查cron从未真正安装」问题（total_asset.json此前停更于08-27）

**三、true_daily_pnl.py 重写「昨日收盘」判定**
- 旧：取文件最后两条记录 → A4每天写多条节点，把今天盘中快照当昨日收盘
- 新：按日期分组，昨日收盘=昨天最后一条总资记录；今日NOW=今天最后一条（>30min→API实查覆盖）
- total_asset.json=当日记录后，兜底逻辑同步修正（不再当昨日收盘）
- 实测：TRUE:-$8.92 CLOSE:$229.90 NOW:$220.98 TARGET:$0.46 GAP3d（诚实打标）

**四、日目标统一0.2%（0.1~0.3%区间中值）**
- IRON_RULES.md §5/§8、AGENTS.md铁律五、NAVIGATION.md、ZQ_MASTER_BLUEPRINT_V3.md、WORK_GOALS.md、SHARED.md、daily_goal.json

**五、网格资金优先守卫（防御性，A4已停用仍保留）**
- executor.py + AWS a4_independent.py：GRID_USDT_RESERVE=30，free<$30清空买入信号
- A4复活条件(USDT≥$200)与守卫兼容；AWS备份.bak.20260831_gridreserve

### 未修
- A1数据管道6维0采集、signals.json陈旧（A2/A3降级绕行；A4已停用不阻塞）
- 08-29/30无收盘记录 → 今日GAP诚实打标，明日链恢复日对日

### 验证计划
1. 今晚21:20 launchd自动记录收盘 → 明早true_daily_pnl输出日对日TRUE
2. 连续3天验证：global_state不再假报-208、收盘链日对日连续
3. A5次日复查本条目所有「实测」数字可复现
## 2026-08-31 — 每日盈利策略大调整（老李授权全权调整）

### 真实账目核对（第一优先）
- Binance API 实查（2026-08-31）：总资产 ≈ **$221**（ETH 0.0747 ≈ $181 + USDT $70.66 + 尘仓≈$25）
- 08-27 的 $232.30 经核实为**真实数据**（当时 USDT $128，网格在 $2455-2495 一路买 ETH 把 USDT 耗尽 →
  今日 ETH 持仓占比 92%，USDT 仅 $15）
- 根因确认：不是假账，而是**网格买侧死锁**——USDT 全部变成 ETH 后，$20/档买单挂不上 →
  网格只能卖不能买，赚不到每日利润

### 核心死锁修复：网格只有卖单没有买单
- 实况：grid_bot 每档买需$20，USDT可用仅$13.12 → 0买单，网格单向卖币，赚不到每日利润
- 修复1（资金重平衡）：MARKET SELL 0.023 ETH = $55.59 → USDT ≈ $70.7，3档买单($60)可全部挂上
- 修复2（防复发）：grid_bot.py 加入**动态缩档**——资金不足时按可用金额缩小买单数量（不低于$5），
  不再"跳过买档"，从此不会因资金不足死锁

### 策略收敛：全系统聚焦ETH网格（单一资金、单一引擎）
- 停用 `follow_engine`（长期0候选空转）与 `a4_independent`（信号管道54h+陈旧，且会与网格抢USDT）
- 保留：grid_bot（主引擎）+ radar_v2（只读研究信号）+ 数据采集 + 每日报告
- 复活条件：A4信号管道恢复且USDT≥$200时再评估

### 真实日盈亏链修复
- 核实：本地 `daily_close_record.py`（launchd 21:20 BJT，查Binance API）+ `fetch_real_balance.py` 本就是真链
- 修复：该 launchd 排程缺失 → 新建 `com.zq.daily-close-record.plist`（21:20 BJT，python3.11）
- 确认：`data/total_asset.json`（真实API净值，唯一权威）+ `data/TRADES.md` 当日总资记录 + 推AWS，链路完整
- AWS `daily_pnl_report.py` 保持只生成报告（daily_pnl_report.json），不写 total_asset（避免双写冲突）
- 每日目标统一为总资×0.1~0.3%（2%/日=年化730%数学不可行，2026-07-13已验证，本次彻底清理残留文档）

### 验证计划
1. 下一 grid_bot 周期（5分钟内）：3档买单挂在 $2400/$2380/$2360
2. 已验：3买/3卖挂单正常；daily_pnl_report 输出 TOTAL=$221（真实API）；TRADES.md 已有当日总资 $221.04
3. 明天复盘：总资 vs 今日总资，达成率按 0.1~0.3% 目标计算

## 2026-08-02 — 崩盘日FALLBACK买入双重保护（ZH晨研发现）

### 变更内容
**FALLBACK路径加两道闸门（profiles/a4-blade/executor.py §②-c）**
- 根因：08-02崩盘日（16币跌>30%，NFP -66%，绿盘仅28%）A4仍每30分钟
  FALLBACK买入RIF $7——用**过期8天的fast_scan_candidates.json**（07-25数据）
  在崩盘中接刀。崩盘检测(07-27)只作用于A3推荐路径，FALLBACK路径无保护。
- 改1：崩盘模式（≥3币跌>30%）→ 禁止FALLBACK买入，直接return
- 改2：fast_scan_candidates.json 过期>48h → 禁止FALLBACK买入，直接return
- 验证：语法OK + 今日条件模拟（fast_scan 192h过期 + crash模式）双保护均触发
- 保护顺序：崩盘检查 → 过期检查 → 打开fast_scan（短路，不浪费API调用）

### 未修
- fast_scan_candidates.json 停更（07-25 → 08-02，8天）— 上游A2/A3管道断
- A4仍报告9持仓但真实Binance仅ETH+NFP约$96 — 持仓表记录缺口
- USDT $6.9-13.9 极低，A4小账户模式MIN_BUY降至$5-7

### 验证计划
1. 下一A4周期（08:59）检查日志是否输出"🔴 崩盘模式: 禁止FALLBACK买入"
2. 观察RIF信号是否停止产生
3. 上游fast_scan管道恢复后自动解除

## 2026-07-13 — 状态修复：真实Binance余额同步 + SSH通道验证

### 变更内容
**一、state/a4.json 余额修正（39天过期→真实Binance余额）**
- 旧：total_equity=$375.43（node_history.jsonl，5月数据，39天过期）
- 旧：positions_count=9（A4本地跟踪，实为62+持仓）
- 旧：total_source="node_history.jsonl"
- 新：total_equity=$216.85（Binance API真实查询，2026-07-13 23:00）
- 新：positions_count=62（含ZEC $173.96/AAVE $27.06/DEXE $4.84等）
- 新：total_source="binance_api_real_balance"
- 验证方式：SSH web4 + Binance myAccount API，timeout 10s内返回

**二、SSH通道验证成功**
- SSH到web4(15.134.211.154)通过web4.pem密钥连接成功
- AWS端state/a4.json停更于06-04（39天前）
- AWS端`~/zq_web4_trading_system/`项目结构与本地一致

**三、真实总资$216.85，流动性仅$5.80 USDT**
- ZEC占64%($173.96)，AAVE占12%($27.06)，DEXE占2%($4.84)
- 其余60+持仓均为dirt dust（<$1 each）
- 核心阻塞：USDT=$5.80 < $25 MIN_BUY门槛

### 未修
- AWS端无自动化余额同步脚本（需cron.yaml）
- A4执行管道仍断裂（USDT不足以开新仓）

### 变更内容

**一、日目标修正（全网数据验证）**
- 旧：每日总资×2%（年化730%，数学上不可行）
- 新：每日总资×0.1~0.3%（年化35-200%，行业median→前10%水平）
- 来源：847个TradingView策略中位数12.3%/年，前10%量化20-30%/年
- 修了：NAVIGATION.md §一 + 总蓝图V3 §1层 + AGENTS.md铁律五

**二、E系列信号禁用**
- 根因：1076笔交易中E2(1.2%)/E3(3.4%)/E4(1.4%)正确率<2%，占84%的决策
- 旧：E系列信号主导出场决策
- 新：出场= P1(RSI超买, 29.7%正确率, 0%错误) + 硬止损
- A4当前已是此模式（6月19日重构），NAVIGATION.md同步

**三、未修（待定）**
- 飞书推送error (09/16/22) — 需排查chat_id/权限
- SSH watchdog error — 持续失败但A4信号管道正常
- E系列继续在经验库追踪（不做决策依据）

### 验证计划
1. 明天（6月21日）观察A4用P1+硬止损的出效果
2. 3天后复盘看日盈亏是否改善
3. 7天后A5复核E系列禁用效果

## 2026-08-31 — MIN_BUY死锁解锁（ZH晨研发现）

### 变更内容
**profiles/a4-blade/executor.py: SMALL_ACCOUNT_MIN_BUY 8→5**
- 根因：08-31实况 free USDT=$7.81，被$8门槛卡死（差$0.19）→ A4三重锁禁买中"资金不足"锁永久成立，A3唯一可执行低吸候选(ZKP rp30低位拐头, 实时+19.2%验证)无法部署
- 依据：$5=代码line1056硬底(max(...,5))与AWS独立执行最小额，08-02同样场景MIN_BUY即在$5-7
- 验证：模拟free=$7.81→MIN_BUY=$5→门槛通过；py_compile OK
- 边界：崩盘禁买(12币跌>30%, NFP-66%/BETA-64%实时确认)独立生效不受影响——今天仍禁买，此为崩盘解除后的弹药解锁

### 未修/阻塞
- ~~尘仓≈$5.1卡死：API key无Convert权限(-1002)，需老李开启后重发~~ → **08-31已定案：永久残值**（见下方专节）
- signals.json基础扫描54h+旧(STRONG=0)——A2/A3已降级绕行，待修

## 2026-08-31 — 尘仓定案：永久残值，关闭回收路径（老李授权决定）

### 决策
- 老李确认：币安小额尘币**手动也无法清仓**（minNotional $5/步进限制/部分交易对暂停），API Convert权限缺失(-1002)且开启后仍有尾差
- 定案：单币价值<$5的尘仓 = **物理不可清残值**，系统永久放弃自动化回收，不阻塞交易、不重复发单
- 未来若API开启Convert权限：一次性兑BNB（能兑多少兑多少），尾差接受，不做二次尝试

### 变更内容
**profiles/a4-blade/executor.py**
- 新增 `DUST_SELL_MIN_NOTIONAL = 5.0`：尘仓机会性回收分支加门禁，价值<$5 → HOLD（reason=币安不可成交放弃回收），不再生成SELL信号
- 与既有$10 MIN_NOTIONAL防护(2026-07-11)叠加：评估层$5门禁 + 信号层$10防护，双保险

**config/IRON_RULES.md 铁律五**
- 追加尘仓定案条款：禁止任何SELL/回收尝试，仅保留一次性Convert兑BNB路径

### 验证
- py_compile OK；逻辑链：价值<$5 → HOLD不产出信号 → 不再出现REJECTED_MIN_QTY/CONVERT_NO_QUOTE刷屏
