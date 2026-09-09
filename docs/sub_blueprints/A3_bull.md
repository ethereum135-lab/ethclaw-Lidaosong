# A3 牛币官 — 子蓝图

> **所属系统：** TraeCode（脑/决策层）
> **职责：** 研究涨幅榜根因，发现交易机会
> **运行方式：** Cron定时任务
> **更新日期：** 2026-09-09

---

## 1. 身份定义

| 属性 | 值 |
|------|-----|
| Agent编号 | A3 |
| 角色名 | 牛币官 |
| 身份 | zq-a3-bull-agent |
| 权限 | 读取市场数据 + 写入研究结论 |
| 禁止 | 下单、修改策略参数 |
| 学习频率 | 每天 |
| 协同 | A2(选币) / A4(执行) / Quant |

## 2. 核心组件

| 组件 | 脚本 | 频率 | 输出 |
|------|------|------|------|
| 信号扫描 | tools/a3_signal_scanner.py | 每小时 | data/signals/ |
| 涨幅分析 | profiles/a3-bull | 每日07:00 | data/radar/ |
| 链上监控 | tools/etherscan_watcher.py | 每小时 | data/node_history.jsonl |

## 3. 分析框架

| 维度 | 分析内容 | 数据来源 |
|------|----------|----------|
| 涨幅根因 | 为什么涨？放量/消息/板块轮动 | 币安涨幅榜 |
| 链上流向 | 大额转入/转出 | Etherscan |
| 社交脉冲 | 讨论量/情绪 | A7舆情 |
| 板块轮动 | 赛道热点 | 行业扫描 |

## 4. 数据流

```
A2选币池 + Binance涨幅榜 + Etherscan + A7舆情
    ↓ A3分析
信号扫描 + 根因研究
    ↓ 写入
data/radar/ (雷达信号)
data/signals/ (交易信号)
    ↓ 被读取
ZH/Commander 综合决策
A4/Blade 执行交易
```

## 5. 当前状态

| 指标 | 值 |
|------|-----|
| profiles/a3-bull | ✅ 存在 |
| a3_signal_scanner.py | ✅ 存在 |
| etherscan_watcher.py | ✅ 存在 |
| Cron | ✅ 每日07:00(管道编排器) |

## 6. 缺口与改进

| 项目 | 状态 |
|------|------|
| 当前策略只做ETH | A3研究范围可扩展到ETH相关DeFi |
| patch_scanner.py | ✅ 存在，工具扫描 |
