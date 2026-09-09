# ZH/Commander 决策中枢 — 子蓝图

> **所属系统：** TraeCode（脑/决策层）
> **职责：** 综合决策 + 辩论引擎 + 每日方向优先级
> **运行方式：** Cron定时任务（每小时）
> **更新日期：** 2026-09-09

---

## 1. 身份定义

| 属性 | 值 |
|------|-----|
| Agent编号 | ZH / Commander |
| 角色名 | 决策中枢 |
| 身份 | zh-commander-agent |
| 人格 | 冷静分析师 — 规则匹配/辩论/权重调整 |
| 权限 | 规则匹配/辩论/权重调整/发布A2A事件 |
| 禁止 | 直接下单、接触提现 |
| 学习频率 | 每天 |
| 协同 | 所有Agent |

## 2. 核心组件

| 组件 | 脚本 | 频率 | 输出 |
|------|------|------|------|
| **辩论引擎** | bull_bear_debate.py | 每小时 | strategy/debate_result.json |
| 规则库 | economy/rule_library.py | 每5分钟 | macro/rule_library.json |
| 策略桥接 | debate_strategy_bridge.py | 每小时 | 传递决策给trend_bot |
| 经济桥接 | economy/economy_debate_bridge.py | 每小时 | 经济维度决策 |
| 期货桥接 | debate_futures_bridge.py | 每4小时 | 期货策略 |
| 外汇桥接 | debate_fx_bridge.py | 每4小时 | 外汇策略 |
| HTX桥接 | debate_htx_bridge.py | 每小时 | 多币种网格参数 |
| 回测 | debate_backtest.py | 手动 | 辩论引擎回测 |
| 规则学习 | rule_learning.py | 每日10:00 | macro/rule_performance.json |

## 3. 辩论引擎 v4.0

### 7维度评分

| 维度 | 权重 | 数据来源 |
|------|------|----------|
| momentum (动量) | 动态 | 价格+成交量 |
| trend_filter (趋势) | 动态 | Donchian通道 |
| fg_reversal (F&G反转) | 动态 | 恐惧贪婪指数 |
| volatility (波动率) | 动态 | ATR |
| position_mgmt (仓位) | 动态 | 当前持仓 |
| sentiment (情绪) | 动态 | A7舆情 |
| cross_market (跨市场) | 动态 | DXY/VIX/TIPS |

### 决策输出

| 字段 | 说明 |
|------|------|
| decision | BUY / SELL / HOLD |
| confidence | 0-100% |
| intensity | low / neutral / high |
| scores | 7维度评分 |
| reason | 决策理由 |
| action | 操作建议 |
| usdt_balance | 当前USDT余额 |
| method | v4_nonlinear_adaptive |

### HOLD特殊处理

```
HOLD时:
  - 允许轻仓试探（仓位×0.70）
  - 止损收紧10%
  - trend_bot读取后调整执行力度
```

## 4. 学习闭环

```
交易执行 → traecode_bridge记录
    ↓
learning_loop (每日22:00) → 复盘
    ↓
rule_learning (每日10:00) → 评估规则命中率
    ↓
命中率 < 50% → 优先级降级
命中率 > 70% → 优先级升级
    ↓
rule_library → 下一轮规则匹配
    ↓ 回到顶部
```

## 5. 数据流

```
A1数据 + A2选币 + A3牛币 + A7舆情 + A8资金 + macro/economy
    ↓ ZH读取
bull_bear_debate.py (7维度辩论)
    ↓ 输出
strategy/debate_result.json (决策结果)
    ↓ 被读取
debate_strategy_bridge → trend_bot (执行)
debate_htx_bridge → htx策略
debate_fx_bridge → 外汇策略
debate_futures_bridge → 期货策略
    ↓ A2A事件
trade.buy / trade.sell / trade.hold
```

## 6. 当前状态

| 指标 | 值 |
|------|-----|
| 辩论版本 | v4_nonlinear_adaptive |
| 当前决策 | HOLD |
| 信心 | 25% |
| 强度 | neutral |
| 规则库 | ✅ 运行中 |
| 学习闭环 | ✅ 每日运行 |
| Cron | ✅ 每小时(管道编排器) |
| 规则学习 | ✅ 每日10:00 |

## 7. 缺口与改进

| 项目 | 状态 | 优先级 |
|------|------|--------|
| DeepSeek LLM集成 | ✅ 已配置API | — |
| Ollama降级 | ✅ qwen2.5:0.5b | — |
| 辩论结果 market=None | ⚠️ 需检查 | P2 |
| 规则命中率为0的规则 | ⚠️ R011已降级 | P2 |
| 多空信号 market 字段 | ⚠️ 输出无market | P2 |
