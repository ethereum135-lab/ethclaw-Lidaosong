# A2 选币官 — 子蓝图

> **所属系统：** Vibe-Trading（地基）
> **职责：** 精选池管理，每日筛选优质币种
> **运行方式：** Cron定时任务
> **更新日期：** 2026-09-09

---

## 1. 身份定义

| 属性 | 值 |
|------|-----|
| Agent编号 | A2 |
| 角色名 | 选币官 |
| 身份 | zq-a2-selector-agent |
| 权限 | 读取币安数据 + 写入选币池 |
| 禁止 | 下单、修改策略 |
| 学习频率 | 每天 |

## 2. 核心组件

| 组件 | 脚本 | 频率 | 输出 |
|------|------|------|------|
| 选币池管理 | tools/coin_pool_manager.py | 每日05:00 | data/coin_pool.json |
| 增量更新 | tools/coin_pool_incremental_update.py | 每日05:30 | data/coin_pool_prime.json |
| AWS选币 | aws_a2_selector.py | 备用 | — |

## 3. 选币标准

| 维度 | 权重 | 说明 |
|------|------|------|
| 成交量 | 30% | 24h成交量 > $10M |
| 涨幅 | 25% | 近7日涨幅排名 |
| 波动率 | 20% | 适合交易的波动区间 |
| 流动性 | 15% | 买卖价差 < 0.1% |
| 基本面 | 10% | 项目活跃度、社区 |

## 4. 数据流

```
Binance API (全市场数据)
    ↓ A2读取
coin_pool_manager.py 筛选
    ↓ 写入
data/coin_pool.json (精选池)
data/coin_pool_prime.json (核心池)
    ↓ 被读取
A3牛币官 研究根因
A4交易执行 决定交易对
```

## 5. 当前状态

| 指标 | 值 |
|------|-----|
| coin_pool.json | 881KB，882KB（含历史） |
| coin_pool_prime.json | 158KB |
| 最近更新 | 2026-09-09 04:00 |
| Cron | ✅ 每日05:00+05:30 |

## 6. 缺口与改进

| 项目 | 状态 |
|------|------|
| 选币标准需要与NAVIGATION.md对齐 | ⚠️ 当前策略只做ETH，选币池主要用于A3研究 |
| profiles/a2-selector | ✅ 存在 |
