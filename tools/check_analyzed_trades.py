#!/usr/bin/env python3
"""Check all SELL entries in TRADES.md against analyzed trade files."""
import sys
import os
sys.path.insert(0, 'tools')
from trade_experience import extract_trade_info

TRADE_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'audit', 'TRADES.md')
TRADES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'experience', 'trades')

with open(TRADE_LOG) as f:
    lines = f.readlines()

analyzed_files = set(os.listdir(TRADES_DIR)) if os.path.isdir(TRADES_DIR) else set()

unanalyzed = []
for line in lines:
    if 'SELL' not in line or 'NO TRADE' in line:
        continue
    info = extract_trade_info(line)
    if info and info.get('symbol') and info.get('time'):
        safe_time = info['time'].replace(' ', '_').replace(':', '-')
        expected = f"{safe_time}_{info['symbol']}.json"
        if expected not in analyzed_files:
            unanalyzed.append((info['time'], info['symbol'], expected))

if unanalyzed:
    print(f"FOUND {len(unanalyzed)} unanalyzed sells:")
    for tm, sym, fn in unanalyzed:
        print(f"  {tm} {sym} -> {fn}")
else:
    print("OK: All sells analyzed, none missing.")
