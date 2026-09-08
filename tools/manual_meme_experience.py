#!/usr/bin/env python3
"""手动为MEME和BABY硬止损创建经验条目"""
import sys, re, json
sys.path.insert(0, 'tools')
from trade_experience import analyze_exit, record_trade_experience, show_master, load_master, save_master

# ===== MEME =====
# From TRADES.md line 36: SELL MEME 144530 @ $0.000543
# Sell reason says 硬止损-5.57%
# Entry price = $0.000543 / (1 - 0.0557) = $0.000575
meme_sell = {
    'symbol': 'MEME',
    'time': '2026-06-11 04:05 BJT',
    'price': '0.00054300',
    'qty': '144530.00000000',
    'reason': 'A4 Blade 硬止损-5.57%—MEME跌破$0.000546卖出$78.48',
    'action': 'SELL',
    'data': ''
}
meme_buy = {
    'symbol': 'MEME',
    'time': '2026-06-10 16:03 BJT',
    'price': '0.000575',
    'qty': '144530.00000000',
    'reason': 'A4 评分执行买入(来自NODE_CHECK Cycle #215)',
    'action': 'BUY',
    'data': ''
}

analysis = analyze_exit(meme_sell, meme_buy)
# Override P&L using the exact -5.57% from sell reason
analysis['pnl_pct'] = -5.57
analysis['pnl_usd'] = -78.48 * 0.0557  # -$4.37
analysis['exit_quality'] = 'wrong'  # 硬止损触发 = 被动退出
analysis['lesson'] = f"MEME硬止损卖出(-5.57%), 硬止损位保护有效但入场时机偏晚"

print(f"MEME P&L: {analysis['pnl_pct']:+.2f}% | ${analysis['pnl_usd']:+.2f} | 品质: {analysis['exit_quality']}")
entry = record_trade_experience(analysis)
if entry:
    print(f"  -> MEME经验已记录")
else:
    print(f"  -> MEME经验已存在(跳过)")

# ===== BABY =====
# From TRADES.md line 37: SELL BABY 3287 @ $0.014980
# Sell reason says 硬止损-5.23%
# Entry price = $0.014980 / (1 - 0.0523) = $0.015808
# From NODE_CHECK log Cycle #215 at 16:03: BABY($26.83 +4.20%entry)
# Position value $26.83, +4.20% from entry means entry value = $26.83 / 1.042 = $25.75
# But that was early - let me use the sell reason as authoritative
# Check Cycle #223 (20:30): BABY($0.01589 +2.8%cycle consolidating WATCH STRONG123 hardstop$0.01492 safe6.1%)
# Wait that says +2.8% cycle which is cycle change not entry%
# And hardstop $0.01492
# By Cycle #232 (03:33): BABY($0.015160 -3.44%24h consol/WATCH STRONG123 A7+A8 hardstop$0.014920 dist1.6%tight)
# Hardstop same $0.014920, distance 1.6%
# At sell: hardstop $0.015076 (line 37), actual sell $0.014980
# Loss -5.23%, so entry = $0.014980 / 0.9477 = $0.015808

baby_sell = {
    'symbol': 'BABY',
    'time': '2026-06-11 04:05 BJT',
    'price': '0.01498000',
    'qty': '3287.00000000',
    'reason': 'A4 Blade 硬止损-5.23%—BABY跌破$0.015076卖出$49.24',
    'action': 'SELL',
    'data': ''
}
baby_buy = {
    'symbol': 'BABY',
    'time': '2026-06-10 16:03 BJT',
    'price': '0.015808',
    'qty': '3287.00000000',
    'reason': 'A4 评分执行买入(来自NODE_CHECK Cycle #215)',
    'action': 'BUY',
    'data': ''
}

analysis2 = analyze_exit(baby_sell, baby_buy)
analysis2['pnl_pct'] = -5.23
analysis2['pnl_usd'] = -49.24 * 0.0523  # -$2.57
analysis2['exit_quality'] = 'wrong'
analysis2['lesson'] = f"BABY硬止损卖出(-5.23%), 硬止损位保护有效但入场时机偏晚"

print(f"BABY P&L: {analysis2['pnl_pct']:+.2f}% | ${analysis2['pnl_usd']:+.2f} | 品质: {analysis2['exit_quality']}")
entry2 = record_trade_experience(analysis2)
if entry2:
    print(f"  -> BABY经验已记录")
else:
    print(f"  -> BABY经验已存在(跳过)")

# ===== 查看更新后的总档案 =====
print()
print(show_master())
