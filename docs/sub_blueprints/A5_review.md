# A5 全系统监督 — 子蓝图

> **所属系统：** OpenClaw（眼/监控层）
> **职责：** 复盘审查，每日全链路分析
> **运行方式：** Cron定时任务
> **更新日期：** 2026-09-09

---

## 1. 身份定义

| 属性 | 值 |
|------|-----|
| Agent编号 | A5 |
| 角色名 | 全系统监督 |
| 身份 | zq-a5-review-agent |
| 权限 | 读取所有Agent产出 + 写入复盘报告 |
| 禁止 | 下单、修改策略 |
| 学习频率 | 每天 |
| 协同 | 所有Agent |

## 2. 核心组件

| 组件 | 脚本 | 频率 | 输出 |
|------|------|------|------|
| 学习闭环 | learning_loop.py | 每日22:00 | reviews/review_YYYYMMDD.json+md |
| 每日学习 | daily_learning_review.py | 每日22:00 | logs/learning.log |
| 内容复盘 | content_review_generator.py | 每周日 | content/publish/review_*.md |
| 每日PnL | tools/daily_pnl_report.py | 每日13:00 | data/daily_pnl_report.json |

## 3. 复盘框架

### 每日复盘（22:00）

| 维度 | 检查内容 |
|------|----------|
| 盈利 | 今天为什么盈利/没盈利？ |
| 选币 | 选对币了吗？ |
| 入场 | 买对价了吗？ |
| 仓位 | 管对仓了吗？ |
| 出场 | 退对利润了吗？ |
| 根因 | 盈利/亏损的根因追溯 |

### 每周复盘（周日）

| 维度 | 检查内容 |
|------|----------|
| 策略表现 | 回测 vs 实盘偏差 |
| 规则命中 | rule_library命中率统计 |
| 内容效果 | 发布内容互动数据 |
| 系统健康 | 心跳/告警/错误统计 |

## 4. 数据流

```
所有Agent产出 (trades/strategy/risk/macro/content)
    ↓ A5读取
learning_loop.py 分析
    ↓ 写入
reviews/review_YYYYMMDD.json + .md
    ↓ 被读取
A9学研 + ZH决策 + rule_learning(自动调整)
```

## 5. 当前状态

| 指标 | 值 |
|------|-----|
| 复盘文件 | 8份（09-06~09-09，json+md各4份） |
| 最近复盘 | 2026-09-09 |
| Cron | ✅ 每日22:00 |
| daily_pnl_report | ✅ 每日13:00 |
| daily_profit_ledger | ✅ 存在 |

## 6. 缺口与改进

| 项目 | 状态 |
|------|------|
| 复盘质量 | ⚠️ 需要更深入的根因分析 |
| 连亏3天触发 | ⚠️ 需要自动触发全链审查的逻辑 |
