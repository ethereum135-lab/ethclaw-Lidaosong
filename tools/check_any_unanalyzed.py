#!/usr/bin/env python3
"""Find all sells and check which ones aren't analyzed yet"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
from trade_experience import *

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE, 'audit', 'TRADES.md')) as f:
    lines = f.readlines()

# Get all pipe-format sells
sells = []
for line in lines:
    stripped = line.replace('**', '')
    if 'SELL' in stripped and 'NO TRADE' not in stripped:
        info = extract_trade_info(line)
        if info and info.get('symbol') and info.get('price','').replace('.','').replace('-','').strip() \
           and not info.get('is_table_format', False):
            sells.append(info)

print(f"Total pipe-format sells: {len(sells)}")

# Check which ones are already analyzed
analyzed = 0
unanalyzed = []
for s in sells:
    ts = s['time'].replace(' ', '_').replace(':', '-')
    base_name = f"{ts}_{s['symbol']}"
    # Check multiple possible filenames
    found = False
    for f in os.listdir(TRADES_DIR):
        if base_name in f:
            found = True
            break
    if found:
        analyzed += 1
    else:
        unanalyzed.append(s)

print(f"Analyzed: {analyzed}")
print(f"Unanalyzed: {len(unanalyzed)}")

# Check if unanalyzed ones have matching buys
if unanalyzed:
    for u in unanalyzed:
        sym = u['symbol']
        stime = u['time']
        buys = []
        for line in lines:
            stripped = line.replace('**', '')
            if 'BUY' in stripped and 'NO TRADE' not in stripped:
                bi = extract_trade_info(line)
                if bi and bi['symbol'] == sym and bi['time'] < stime:
                    buys.append(bi)
        buy = max(buys, key=lambda x: x['time']) if buys else None
        print(f"  {sym}@{stime} price={u['price']} -> buy={'FOUND' if buy else 'MISSING'}")
