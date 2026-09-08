#!/usr/bin/env python3
"""Append Node 16 results to TRADES.md and daily.log"""

import os
from datetime import datetime

trades_path = "/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md"
log_path = "/Users/lidaosong/zq_web4_trading_system/daily.log"

# TRADES.md entry
trades_entry = """|| 2026-05-17 15:06:00 | CHECK | -- | -- | -- | A4五维评估(15:06 BJT Node#16): 持仓5全部HOLD. BTC$78,097(+0.04% vs 14:04$78,144). 周日持续$78K弱势整理第3天. 五维评估表(AWS Binance API 15:06物理验证+独立趋势验证+RSI+BB扫描0信号):

|| 币种 | 数量 | 当前价 | 成本价 | 价值 | 盈亏% | 占比 | 趋势(vs14:04) | RSI | 判定 | 依据 |
||:-----|:----:|:------:|:------:|:----:|:-----:|:----:|:------------:|:---:|:----:|:-----|
|| XRP | 31.73 | $1.4184 | $1.4733 | $45.01 | -3.73%黄 | 14.9% | +0.05%↑从$1.4177 | ~55中性 | HOLD | -3.73%远离-5%止损线$1.3996,趋势稳定,半仓14.9%安全 |
|| DOGE | 222.26 | $0.10977 | $0.11041 | $24.40 | -0.58%绿 | 8.1% | -0.28%->从$0.11008 | ~55中性 | HOLD | 近保本-0.58%,趋势稳定,极小仓位安全 |
|| TON | 2.736 | $1.933 | $2.361 | $5.29 | -18.13%红 | 1.8% | -0.10%->从$1.935 | ~50中性 | HOLD(dust) | $5.29<10尘埃,不可操作 |
|| UNI | 1.224 | $3.505 | $4.052 | $4.29 | -13.50%红 | 1.4% | -0.34%->从$3.517 | ~48中性 | HOLD(dust) | $4.29<10尘埃,不可操作 |
|| XEC | 580139 | $0.000007 | $0.0000075 | $4.06 | -6.67%红 | 1.3% | -12.5%↓从$0.000008 | -- | HOLD(dust) | $4.06<10尘埃,已穿-5%止损但仓位<$10不可操作 |

五维综合:0/5减仓/清仓信号(2可操作HOLD+3尘埃). 仓位集中度:XRP 14.9%<50%安全(已减半). A3买入评估: **BUY_PULLBACK(5/9)** — AIUSDT(新框架:独立趋势验证替代静态价格阈值) a4_trend_checker结果: TREND:UP/SIDE RSI:37.3/51.1 VOL:0.1x POS:33.3% DECISION:BUY_PULLBACK(5/9) SCORE:5 MA7:0.032257. 趋势向上但VOL=0.1x极度缩量,等待放量. 回调价近似MA7=$0.032257,当前$0.0321已触及. 四查: FK过期无否决/USDT=$218.13>=15/API正常/AI独立验证BUY_PULLBACK. **闲置资金扫描(USDT=$218.13>=$50触发)**: 源A RSI+BB:0信号(全部WATCH/EXIT_ABOVE_MA). 源B动量雷达TOP3: CHZ BUY_NOW(6/9)但VOL 0.1x+77%范围高位+已持尘; UTK BUY_PULLBACK TREND:DOWN; ZEC BUY_PULLBACK RSI4h=73.6过买+$514价高. 源C持仓改善:无改善. **三源结论:资金闲置-周日超低流动性,守纪律不强行入场**. 空转自检: 边界(15连续CHECK自07:36SELL后~7.5h,8-16节点区间). 根因:A3推荐AIUSDT但趋势验证BUY_PULLBACK(等待放量)+周日BTC$78.1K弱势第3天+RSI+BB 0信号+全市场VOL仅0.1x. 总资约$301.18. USDT=$218.13(72.4%)弹药充裕. BTC$78.10K. 累计-$128.82(-29.9%). 无减仓/清仓触发.
"""

log_entry = "[2026-05-17 15:06 BJT] A4节点#16 | 持仓5全部HOLD | BTC$78,097(+0.04%) | A3推荐AIUSDT趋势验证BUY_PULLBACK(5/9)等待放量 | USDT=$218.13(72.4%) | 总资~$301.18 | 累计-$128.82(-29.9%) | 空转自检:边界15连续CHECK(07:36后~7.5h,8-16节点) | 根因:A3推荐AIUSDT趋势BUY_PULLBACK(等待VOL放量)+周日BTC$78.1K弱势第3天+RSI+BB 0信号+全市场VOL仅0.1x | 无减仓/清仓触发 | 闲置资金扫描:三源无可行信号\n"

# Append to TRADES.md
with open(trades_path, 'a') as f:
    f.write(trades_entry)
print("TRADES.md appended OK")

# Append to daily.log
with open(log_path, 'a') as f:
    f.write(log_entry)
print("daily.log appended OK")
