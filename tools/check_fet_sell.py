#!/usr/bin/env python3
"""Check FET sell and analyze it"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
from trade_experience import *

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE, 'audit', 'TRADES.md')) as f:
    lines = f.readlines()

# Find FET sell (2026-06-01 23:55:00) - last analyzable sell
fet_sell_line = None
for line in lines:
    stripped = line.replace('**', '')
    if 'SELL' in stripped and 'FET' in line and 'NO TRADE' not in stripped:
        fet_sell_line = line
        break

# Find FET buy (latest before sell)
fet_buy_line = None
fet_buy_time = ''
for line in lines:
    stripped = line.replace('**', '')
    if 'BUY' in stripped and 'FET' in line:
        info = extract_trade_info(line)
        if info and info.get('time', '') < '2026-06-01 23:55:00':
            if info['time'] > fet_buy_time:
                fet_buy_time = info['time']
                fet_buy_line = line

if fet_sell_line and fet_buy_line:
    sell_info = extract_trade_info(fet_sell_line)
    buy_info = extract_trade_info(fet_buy_line)
    print('Sell:', json.dumps(sell_info, ensure_ascii=False))
    print('Buy:', json.dumps(buy_info, ensure_ascii=False))
    
    analysis = analyze_exit(sell_info, buy_info)
    print('\nAnalysis:')
    print(f'  Symbol: {analysis["symbol"]}')
    print(f'  Buy price: {analysis["buy_price"]}')
    print(f'  Sell price: {analysis["sell_price"]}')
    print(f'  P&L: {analysis["pnl_pct"]:+.1f}%')
    print(f'  P&L USD: ${analysis["pnl_usd"]:+.2f}')
    print(f'  Exit quality: {analysis["exit_quality"]}')
    print(f'  Trigger signals: {analysis["trigger_signals"]}')
    print(f'  Lesson: {analysis["lesson"]}')
    
    # Check if already recorded
    ts = analysis['sell_time'].replace(' ', '_').replace(':', '-')
    filename = f"{ts}_{analysis['symbol']}.json"
    trade_file = os.path.join(TRADES_DIR, filename)
    if os.path.exists(trade_file):
        print(f'\nAlready analyzed: {trade_file}')
    else:
        print(f'\nReady to record (not yet analyzed)')
        entry = record_trade_experience(analysis)
        if entry:
            print(f'Recorded OK')
        else:
            print('record_trade_experience returned None')
else:
    print('Could not find FET sell or buy lines')
    if not fet_sell_line:
        print('No FET sell line found')
    if not fet_buy_line:
        print('No FET buy line found')
