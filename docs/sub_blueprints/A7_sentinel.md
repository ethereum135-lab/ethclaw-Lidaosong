# A7 舆情官 — 子蓝图

> **所属系统：** TraeCode（脑/决策层）
> **职责：** 情绪监控，社交媒体趋势追踪
> **运行方式：** Cron定时任务
> **更新日期：** 2026-09-09

---

## 1. 身份定义

| 属性 | 值 |
|------|-----|
| Agent编号 | A7 |
| 角色名 | 舆情官 |
| 身份 | zq-a7-sentinel-agent |
| 权限 | 读取社交媒体数据 + 写入情绪分析 |
| 禁止 | 下单、修改策略 |
| 学习频率 | 每天 |
| 协同 | A3(牛币) / ZH(决策) |

## 2. 核心组件

| 组件 | 脚本 | 频率 | 输出 |
|------|------|------|------|
| 舆情采集 | sentiment_collector.py | 4小时 | news/sentiment.json |
| 新闻情绪 | news_sentiment.py | 4小时 | news/ |
| 新闻黑名单 | news_blackout.py | — | events/blackout.json |
| 情绪获取 | data_sources/sentiment_fetcher.py | — | — |
| 新闻获取 | data_sources/news_fetcher.py | — | — |

## 3. 情绪指标

| 指标 | 来源 | 用途 |
|------|------|------|
| 恐惧贪婪指数 | Binance API | 辩论引擎7维之一 |
| 社交讨论量 | Twitter/微博 | 趋势判断 |
| 新闻情绪 | 新闻API | 多空判断 |
| 黑天鹅检测 | news_blackout | 紧急风控 |

## 4. 数据流

```
新闻API + 社交媒体 + Binance F&G
    ↓ A7采集
sentiment_collector + news_sentiment
    ↓ 写入
news/sentiment.json (情绪分数)
    ↓ 被读取
ZH辩论引擎 (7维度之一: sentiment)
A3牛币官 (社交脉冲)
```

## 5. 当前状态

| 指标 | 值 |
|------|-----|
| sentiment_collector.py | ✅ 存在 |
| news_sentiment.py | ✅ 存在 |
| news_blackout.py | ✅ 存在 |
| F&G指数 | 66 (Greed) |
| Cron | ✅ 每4小时(管道编排器) |

## 6. 缺口与改进

| 项目 | 状态 |
|------|------|
| Twitter API接入 | ⚠️ 未配置 |
| 微博数据 | ⚠️ 未接入 |
| 深度情绪分析 | ⚠️ 当前仅F&G指数 |
