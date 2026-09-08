# ZQ Web 4.0 团队日报告 — 2026-05-03

> 供5个profile使用：Commander / Quant / Scouter / Blade / Reporter
> 项目根目录: ~/zq_web4_trading_system

---

## 一、今日系统变更一览

### 引擎变更（v2.2 — Blade&Commander关注）

| 变更 | 文件 | 说明 |
|:---|---:|:---|
| 砍掉恐惧贪婪 | engine_realtime_v2.py | 移除fetch_fear_greed/calc_resonance_score中的market_gate |
| ta库替代手写指标 | engine_realtime_v2.py | calc_rsi/calc_trend改用ta.momentum.RSIIndicator/ta.trend.SMAIndicator |
| OI+费率历史存储 | engine_realtime_v2.py + data/trend_store.json | 每节点存Top20币费率+OI（保留96点/48小时） |
| 节点快照 | data/node_history.jsonl | 每节点自动存Top5评分+USDT+买卖（JSONL格式） |
| 选币库黑名单 | engine_realtime_v2.py | load_excluded_coins()集成进scan_top50 |
| skip-held-coin | engine_realtime_v2.py | decide_entry(snapshots, usdt_total, holdings) 跳过已有持仓 |
| TRADES.md v3 | engine_realtime_v2.py | 日志增加持仓时间(分)+退出编号(E1-E6) |
| 当前引擎 | 1025行/36函数 | 编译通过，已运行1节点验证 |

### 数据源状态（Scouter&Quant关注）

| 状态 | 数据源 | 说明 |
|:---:|---|---|
| ✅ | Binance SPOT (6个端点) | 核心行情+交易 |
| ✅ | Binance Futures (2个端点) | 资金费率+OI持仓量 |
| ✅ | CoinGecko | 热门币榜单 |
| ✅ | DexScreener | DEX热度 |
| ✅ | Etherscan | 链上转账监控（工具已就绪） |
| ❌移除 | Alternative.me恐惧贪婪 | 对决策零影响 |
| ⏸️暂缓 | TradingView Scanner | 先把Binance数据用透 |
| ⏸️暂缓 | DefiLlama链TVL | 日级别更新太慢，暂不接 |
| ⏸️暂缓 | Coinglass付费 | 自建趋势存储替代90%功能 |
| ⏸️暂缓 | Nansen $99/月 | 本金回来了再说 |

### 定时任务状态

| 任务 | 频率 | 状态 |
|:---|---:|:---:|
| 30分钟自动交易 | every 30m | ✅ 运行中 |
| 每日08:00晨报 | 0 8 * * * | ⚠️ 需检查（上次error） |
| 每日系统健康扫描 | 0 10,16,22 * * * | ✅ 已修复 |
| 每日21:00自我反思 | 0 21 * * * | ✅ 已修复 |
| 每日24:00复盘 | 0 0 * * * | ✅ 今晚验证 |
| 每周一全网学习 | 0 8 * * 1 | ✅ 新建 |
| 每日备份 | 0 4 * * * | ⚠️ 需检查 |
| 每周选币库更新 | 0 2 * * 0 | ⚠️ 已过时（引擎改用实时数据） |

---

## 二、系统哲学更新（Commander&全员关注）

### 2026-05-03 新增核心标准

**1. 四个核心问题是一条互锁的链条**
```
数据来源不全 → 选币依据不充分 → 行为数据积累不起来 → 经验是空壳
                                                                  ↓
                                                        系统永远在战术层面打转
                                                                  ↓
                                                    头痛医头、治标不治本
```
任何一环断了，整个系统都不转。必须四维同时推进。

**2. 模拟交易对AI无意义**
人类需要模拟是因为怕亏钱、有情绪。AI没有这些。有真实数据就直接上市场验证，跑坏了改代码就行。

**3. 定期全网学习搜索（新标准）**
「现在是信息万变的时代」— 每周一08:00自动执行5次搜索（新工具/新数据源/新策略/新框架/交易所新特性），输出报告到learning/。

**4. 工具不要贪多，先把手上的用透**
TradingView/DefiLlama/Coinglass都有价值，但当前阶段先把Binance API的数据价值榨干。自建趋势存储替代Coinglass 90%功能。

---

## 三、各Profile今日行动

### Commander（全局决策）
- [ ] 确认今晚24:00复盘执行
- [ ] 确认每周一08:00学习扫描正常触发

### Quant（量化策略）
- [ ] 了解ta库（pip install ta），引擎已用ta.trend.SMAIndicator和ta.momentum.RSIIndicator
- [ ] 准备回测：node_history.jsonl积累够3天数据后，用Pandas分析策略胜率/夏普
- [ ] 监控decide_entry的skip-held-coin是否有效

### Scouter（数据侦查）
- [ ] 每周一08:00搜索引擎新工具，报告到learning/
- [ ] 监控trend_store.json积累的数据（3天后可看趋势方向）
- [ ] 检查Etherscan工具是否正常运行

### Blade（交易执行）
- [ ] 引擎当前正常运行，1025行/36函数
- [ ] 注意：恐惧贪婪已移除，评分满分公式去掉了market_gate
- [ ] TRADES.md新字段：hold_min+exit_code

### Reporter（报告归档）
- [ ] 今日报告归档路径：reports/today_system_upgrade_20260503.md
- [ ] 明天24:00复盘需包含：新引擎运行效果、skip-held-coin验证
- [ ] 注意测试晨报cron(08:00)是否修复

---

## 四、待办清单（来自今日讨论）

| 优先级 | 事项 | 依赖 |
|:---:|---|---|
| P0 | 修复晨报cron(08:00) | 下个迭代 |
| P0 | 修复24:00复盘cron | 今晚验证 |
| P1 | 修复每日备份cron(04:00) | 下个迭代 |
| P1 | 回测工具搭建 | 积累3天node_history后 |
| P2 | 持仓时间保护期编码 | 下个迭代 |
| P2 | 引擎多时间框架嵌套评分 | 下个迭代 |

---

*文档版本: v1.0 | 生成时间: 2026-05-03 13:00 | 引擎版本: v2.2*
