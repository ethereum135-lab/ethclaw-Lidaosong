#!/usr/bin/env python3
"""Record the latest C sell trade experience"""
import sys
sys.path.insert(0, 'tools')
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system/tools')
from trade_experience import *
from datetime import datetime
import re
import os

os.chdir('/Users/lidaosong/zq_web4_trading_system')

# Read TRADES.md to find the C sell
with open('audit/TRADES.md') as f:
    lines = f.readlines()

# C sell info from line 313
sell_info = {
    'symbol': 'C',
    'time': '2026-06-07 15:05:00',
    'price': '0.10644000',
    'qty': '299.40000000',
    'reason': '轮换出—ZEC(just_starting conf=9|score123STRONG)信号更优|C+8.6%盈利退出'
}

# Compute buy price from sell reason: +8.6%
sell_price = 0.10644
pnl_float = 8.6
buy_price = round(sell_price / (1 + pnl_float/100), 6)

print(f'SELL price: ${sell_price}')
print(f'BUY price (derived from +8.6%): ${buy_price}')

# Find the earliest NODE_CHECK mentioning C as held
# From TRADES.md, first mention is 2026-06-07 05:45 line
buy_time = '2026-06-07 05:00:00'

buy_info = {
    'symbol': 'C',
    'time': buy_time,
    'price': str(buy_price),
    'qty': '299.4',
    'reason': 'A4 Blade entered C position'
}

# Run analysis
analysis = analyze_exit(sell_info, buy_info)
print(f'\n=== Analysis Results ===')
print(f'P&L: {analysis["pnl_pct"]:+.2f}%')
print(f'P&L USD: ${analysis["pnl_usd"]:+.2f}')
print(f'Exit quality: {analysis["exit_quality"]}')
print(f'Lesson: {analysis["lesson"]}')
print(f'Trigger signals: {analysis["trigger_signals"]}')

# Record to experience archive
entry = record_trade_experience(analysis)
if entry:
    print('\n✅ Trade experience recorded successfully!')
else:
    print('\n⚠️  File already exists (dedup) — checking master stats...')

# Show master
print('\n' + show_master())
