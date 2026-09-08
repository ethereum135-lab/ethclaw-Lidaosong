#!/usr/bin/env python3
"""Script to analyze the latest sell trade and update experience archive."""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import json

result = get_last_exit()
if result and result.get('sell'):
    sell = result['sell']
    buy = result['buy']
    print(f'Latest sell: {sell["symbol"]} at {sell["time"]}')
    print(f'  Sell price: {sell["price"]}, Qty: {sell["qty"]}')
    print(f'  Reason: {sell["reason"]}')
    if buy:
        print(f'Corresponding buy: {buy["symbol"]} at {buy["time"]}')
        print(f'  Buy price: {buy["price"]}, Qty: {buy["qty"]}')
    else:
        print('No corresponding buy found')
    
    analysis = analyze_exit(sell, buy)
    entry = record_trade_experience(analysis)
    
    print(f'\n=== Analysis Results ===')
    print(f'  Symbol: {analysis["symbol"]}')
    print(f'  P&L: {analysis["pnl_pct"]:+.1f}% (${analysis["pnl_usd"]:+.2f})')
    print(f'  Exit quality: {analysis["exit_quality"]}')
    print(f'  Trigger signals: {analysis["trigger_signals"]}')
    print(f'  Lesson: {analysis["lesson"]}')
    print(f'  Buy price: {analysis["buy_price"]:.4f}')
    print(f'  Sell price: {analysis["sell_price"]:.4f}')
    
    if entry:
        ts = analysis['sell_time'].replace(' ', '_').replace(':', '-')
        print(f'\n[OK] Experience recorded to data/experience/trades/{ts}_{analysis["symbol"]}.json')
    else:
        print(f'\n[SKIP] Trade already analyzed, skipping duplicate')
else:
    print('No sell trade found to analyze')
