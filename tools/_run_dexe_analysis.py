#!/usr/bin/env python3
"""Analyze DEXE sell (dust cleanup) and record to experience archive."""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import json

with open('audit/TRADES.md') as f:
    lines = f.readlines()

dexe_buy = dexe_sell = None
for line in lines:
    info = extract_trade_info(line)
    if info and info.get('symbol') == 'DEXE':
        if info['action'] == 'BUY':
            dexe_buy = info
            print(f'Found DEXE BUY: qty={info["qty"]} price={info["price"]} time={info["time"]}')
        elif info['action'] == 'SELL':
            dexe_sell = info
            print(f'Found DEXE SELL: qty={info["qty"]} price={info["price"]} time={info["time"]} reason={info["reason"]}')

if dexe_buy and dexe_sell:
    analysis = analyze_exit(dexe_sell, dexe_buy)
    print()
    print(json.dumps(analysis, indent=2, ensure_ascii=False))
    entry = record_trade_experience(analysis)
    if entry:
        print(f'Recorded: DEXE P&L:{analysis["pnl_pct"]:+.2f}% quality:{analysis["exit_quality"]}')
    else:
        print('Skipped (already recorded)')
    print()
    print(show_master())
else:
    print('DEXE buy/sell pair incomplete')
