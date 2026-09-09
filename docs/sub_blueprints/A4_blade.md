# A4 交易执行 — 子蓝图

> **所属系统：** Hermes（手/执行层）
> **职责：** 仓位管理，策略执行，下单/平仓
> **运行方式：** Cron定时任务（每10分钟）
> **更新日期：** 2026-09-09

---

## 1. 身份定义

| 属性 | 值 |
|------|-----|
| Agent编号 | A4 / Blade |
| 角色名 | 交易执行官 |
| 身份 | zq-a4-blade-agent / Hermes人格 |
| 人格 | 铁血执行者 — 策略说买就买，说卖就卖 |
| 权限 | 下单/平仓/查询持仓/风控检查/写日志 |
| 禁止 | 改策略参数、覆盖止损、选交易品种、接触提现 |
| 学习频率 | 每天 |
| 协同 | A3(信号) / Quant(量化) |

## 2. 核心组件

| 组件 | 脚本 | 频率 | 说明 |
|------|------|------|------|
| **trend_bot.py** | tools/trend_bot.py | 每10分钟 | 唯一策略执行器（ETH趋势通道v3.1） |
| HTX桥接 | debate_htx_bridge.py | 每小时 | 多币种网格参数（备用） |
| 风控检查 | risk_manager.py | 每5分钟 | 11道风控门 |
| 紧急停止 | kill_switch.py | 守护 | 熔断/紧急平仓 |
| 状态文件 | data/trades/trend_state.json | — | mode/peak/channel |

## 3. 策略执行规则（NAVIGATION.md v3.1）

```
每10分钟循环:
  1. 读取 trend_state.json (mode=eth/cash)
  2. 获取 ETH 当前价格 + 近120根1h K线
  3. 计算通道: high=120根最高, low=120根最低
  4. 判断:
     if mode==cash and price > channel_high → 全仓买入ETH
     if mode==eth and price < channel_low → 全仓卖出ETH (通道破位)
     if mode==eth and 1h_close < peak*0.98 → 全仓卖出ETH (盈利锁定)
  5. 读取辩论结果（HOLD时仓位×0.70，止损收紧10%）
  6. 执行交易（通过Binance API）
  7. 更新 trend_state.json
  8. 写入 order_history.json
```

## 4. 11道风控门

| # | 门 | 规则 | 执行者 |
|---|-----|------|--------|
| 1 | 单笔亏损 | ≤总资×1% | risk_manager |
| 2 | 保证金下限 | ≥10% | risk_manager |
| 3 | 连亏熔断 | 3天不达标→全链审查 | risk_manager |
| 4 | 止损执行 | DSL止损 | risk_manager |
| 5 | 紧急停止 | kill_switch | kill_switch.py |
| 6-11 | 持仓/相关性/经济事件/冷却/开仓上限/辩论HOLD | — | risk_manager |

## 5. 当前状态

| 指标 | 值 |
|------|-----|
| 策略 | ETH趋势通道v3.1 |
| mode | eth（持有ETH） |
| 持仓 | 0.0323 ETH (~$80.61) |
| USDT | $2.61 |
| peak_close | $2509.65 |
| channel_high | $2546.66 |
| channel_low | $2431.61 |
| trail_pct | 2% |
| Cron | ✅ 每10分钟 |
| 最近运行 | 2026-09-09 06:00 |

## 6. 已停用策略

| 策略 | 停用日期 | 原因 |
|------|----------|------|
| grid_bot | 2026-09-06 | 改为mean_rev_bot |
| mean_rev_bot | 2026-09-09 | 与NAVIGATION.md冲突 |
| swing_engine | 2026-09-09 | 与NAVIGATION.md冲突 |
| debate_grid_bridge | 2026-09-09 | 网格策略已废弃 |
