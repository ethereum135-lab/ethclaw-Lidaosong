#!/usr/bin/env python3
"""Append A4 NODE_CHECK to TRADES.md"""
import datetime, os

BASE = os.path.expanduser("~/zq_web4_trading_system")
now = datetime.datetime.now()
ts = now.strftime("%H:%M")

report = f"""

## A4 NODE_CHECK — 2026-06-17 {ts} BJT

**总权益: $245.73 | USDT: $0.01 | 仓位: 3个有意义 + 5个尘仓**

**信号源新鲜度：**
- phase_analysis.json: ✅ 04:48 (新鲜)
- signals.json: ✅ 04:32 (新鲜)
- a4_input_summary.md: ✅ 04:58 (新鲜)
- SOCKS5隧道: ✅ 通

**持仓检查：**

### 卖出检查（要跌了的信号）

| 触发条件 | WLD | STG | JTO | HMSTR(dust) |
|:---------|:---:|:---:|:---:|:----------:|
| RSI(4h)>85? | RSI~80.5 ✅不触发 | RSI~52 ✅ | RSI~73 ✅ | RSI~50 ✅ |
| 量价背离? | 无异常 ✅ | 无异常 ✅ | 无异常 ✅ | 无异常 ✅ |
| -5%硬止损? | +0.12% ✅ | +0.41% ✅ | -1.69% ✅ | dust ✅ |
| BTC-5%+? | BTC -1.2% ✅正常 | — | — | — |
| phase=SELL_NOW? | WATCH conf=6 ✅ | WATCH conf=6 ✅ | WATCH conf=6 ✅ | WATCH conf=6 ✅ |
| smart信号方向? | BUY(长盈98.8%)✅同向 | BIAS_LONG✅同向 | BIAS_LONG✅同向 | BIAS_SHORT但dust |
| 实时动量(15min) | +0.97%(末棒-0.65%) | -1.18%回调 | +0.29%✅ | — |

**SELL结论：无持仓触发卖出信号 ✅ HOLD ALL**

### 买入候选检查
- 21个BUY_READY候选（PARTI conf=10, ENA conf=9, SAGA conf=8等）
- 但 **USDT=$0.01 < MIN_BUY $25 — 无法开新仓**

### 核心决策
| 仓位 | 决策 | 理由 |
|:----|:----:|:------|
| **WLD** | **HOLD** | trending, smart=BUY(鲸鱼长盈98.8%), RSI~80.5<85. ⚠️RSI高位 |
| **STG** | **HOLD** | trending, BIAS_LONG, A7+A8双重确认 |
| **JTO** | **HOLD** | trending, BIAS_LONG, 浮亏-1.69%距止损远 |
| **HMSTR/ROSE/CFG/DYM/UNI** | **HOLD(dust)** | 清理不能释放足够USDT |
| **开新仓** | **不能** | USDT=$0.01 < $25 MIN_BUY |

**防线检查：**
- RL5: JTO浮亏-$0.45 << 总资x1%=$2.46 ✅
- 资金全利用: USDT=$0.01 ✅
- BTC -1.2%正常范围 ✅

### 下一周期关注
1. WLD RSI(4h)追踪 — 若触及85需立即全清
2. STG短期回调恢复 — 15min -1.18%是否扩大
3. 候选池待机 — PARTI(conf=10)/ENA(conf=9)
4. BTC -1.2%，扩大至-5%+需减半仓
"""

path = os.path.join(BASE, "audit/TRADES.md")
with open(path, "a") as f:
    f.write(report)
print("TRADES.md updated")
