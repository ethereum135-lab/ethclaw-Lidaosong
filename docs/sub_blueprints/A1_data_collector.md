# A1 数据采集 — 子蓝图

> **所属系统：** Vibe-Trading（地基）
> **职责：** 数据采集管道，所有系统的数据源头
> **运行方式：** Cron定时任务 + vibe-trading API
> **更新日期：** 2026-09-09

---

## 1. 身份定义

| 属性 | 值 |
|------|-----|
| Agent编号 | A1 |
| 角色名 | 数据采集管道 |
| 身份 | 非Agent（纯脚本） |
| 权限 | 只读API + 写入shared_context |
| 禁止 | 下单、修改策略、接触提现 |

## 2. 核心组件

| 组件 | 脚本 | 频率 | 输出 |
|------|------|------|------|
| 交易数据同步 | sync_trading_data.py | 5分钟 | trades/positions.json + trades/total_asset.json |
| 外汇汇率采集 | fx_rates_collector.py | 5分钟 | fx/fx_rates.json |
| 股票数据采集 | stock_data_collector.py | 每日 | stocks/*.json |
| 舆情采集 | sentiment_collector.py | 4小时 | news/sentiment.json |
| 经济指标 | economic_indicators.py | 每日9:00 | macro/economic_indicators.json |
| 经济日历 | economic_calendar.py | 每日9:00 | events/economic_calendar.json |
| 期权IV | options_iv_collector.py | 4小时 | macro/options_iv.json |
| Polymarket | polymarket_collector.py | 4小时 | macro/polymarket.json |

## 3. 数据流

```
Binance API / CoinGecko / 外汇API / 新闻API
    ↓
各 collector 脚本采集
    ↓
shared_context/ 对应子目录 (JSON格式)
    ↓
被 A3辩论引擎 / A4执行 / A5监督 / A7舆情 读取
```

## 4. 数据目录

| 目录 | 内容 | 更新频率 |
|------|------|----------|
| trades/ | 持仓、总资产 | 5分钟 |
| macro/ | F&G指数、市场制度、经济指标 | 5分钟~每日 |
| fx/ | 外汇汇率 | 5分钟 |
| events/ | 经济日历、新闻事件 | 每日 |
| news/ | 舆情、情绪 | 4小时 |
| stocks/ | A股/美股/港股数据 | 每日 |

## 5. 当前运行状态

| 组件 | Cron | 状态 |
|------|------|------|
| sync_trading_data | ✅ 每5分钟(管道编排器) | 运行中 |
| fx_rates_collector | ✅ 每5分钟(管道编排器) | 运行中 |
| economic_calendar | ✅ 每日9:00 | 运行中 |
| economic_indicators | ✅ 每日9:00 | 运行中 |
| sentiment_collector | ✅ 每4小时(管道编排器) | 运行中 |

## 6. 缺口与改进

| 项目 | 状态 | 说明 |
|------|------|------|
| data_sources/目录 | ⚠️ 已在.gitignore | 4个采集脚本在zq_web4中 |
| Polymarket | ⚠️ 未在Cron | 脚本存在但未调度 |
| 期权IV | ⚠️ 未在Cron | 脚本存在但未调度 |
