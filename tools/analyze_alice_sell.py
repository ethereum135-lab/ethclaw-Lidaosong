#!/usr/bin/env python3
"""Analyze the latest ALICE sell trade and record experience."""
import sys
sys.path.insert(0, 'tools')
from trade_experience import analyze_exit, record_trade_experience
import json

# From TRADES.md A4 execution node 2026-06-20T11:35BJT:
# SELL ALICE 251.13@$0.1118=$28.08 — SL触发(-4.0%@F&G=14)
# SELL_NOW table shows: entry=$0.1167, buy qty=251.14

# Construct sell info
sell = {
    'symbol': 'ALICE',
    'time': '2026-06-20 11:35',
    'price': '0.1118',   # unit price from execution line
    'qty': '251.13',     # from execution line
    'reason': 'SL触发(-4.0%@F&G=14)',
}

# Construct buy info from SELL_NOW table avg entry
buy = {
    'symbol': 'ALICE',
    'time': '2026-06-20 17:07',  # from the buy section header
    'price': '0.1167',   # avg entry from SELL_NOW table
    'qty': '251.14',
    'reason': '动量验证买入',
}

print(f"Sell: {json.dumps(sell, ensure_ascii=False)}")
print(f"Buy:  {json.dumps(buy, ensure_ascii=False)}")

analysis = analyze_exit(sell, buy)
print(f"\nAnalysis result:")
print(f"  Symbol: {analysis['symbol']}")
print(f"  P&L: {analysis['pnl_pct']:+.1f}%")
print(f"  P&L USD: ${analysis['pnl_usd']:.2f}")
print(f"  Exit quality: {analysis['exit_quality']}")
print(f"  Signals: {analysis['trigger_signals']}")
print(f"  Sell price: ${analysis['sell_price']:.4f}")
print(f"  Buy price: ${analysis['buy_price']:.4f}")
print(f"  Lesson: {analysis.get('lesson', '')}")

entry = record_trade_experience(analysis)
if entry:
    print(f"\n✅ 经验已记录到 data/experience/")
else:
    print(f"\n⚠️ 跳过重复（已分析过该交易）")

# Show updated master
from trade_experience import show_master
print(f"\n{show_master()}")
