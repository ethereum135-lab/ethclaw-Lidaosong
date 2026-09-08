#!/usr/bin/env python3
"""检查是否还有未处理的卖出"""
import sys
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system/tools')
from trade_experience import *
import os

with open('/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md') as f:
    raw = f.read()

lines = [l for l in raw.split('\n') if l.strip()]

sells_found = 0
unprocessed = []
for line in lines:
    stripped = line.replace('**','').replace('\U0001f534 ', '').replace('\U0001f534',' ').replace('\U0001f7e2 ', '').replace('\U0001f7e2',' ').replace('\u26a0\ufe0f','')
    parts_check = [p.strip() for p in stripped.split('|')]
    if 'SELL' in parts_check and 'NO TRADE' not in stripped:
        info = extract_trade_info(line)
        if info and info.get('symbol') and info.get('price','').replace('.','').replace('-','').strip():
            sells_found += 1
            ts = info['time'].replace(' ', '_').replace(':', '-')
            filename = f"{ts}_{info['symbol']}.json"
            trade_file = os.path.join('/Users/lidaosong/zq_web4_trading_system/data/experience/trades', filename)
            if not os.path.exists(trade_file):
                unprocessed.append(info)

if unprocessed:
    print(f"UNPROCESSED: {len(unprocessed)}")
    for u in unprocessed:
        print(f"  {u['symbol']:8s} @ {u['time']:22s} | reason: {u['reason']}")
else:
    print(f"CLEAR: all {sells_found} sells already analyzed")
