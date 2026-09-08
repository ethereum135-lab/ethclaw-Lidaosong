#!/usr/bin/env python3
"""Check for unprocessed sell trades in TRADES.md - detailed"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from trade_experience import extract_trade_info, TRADES_DIR, TRADE_LOG

with open(TRADE_LOG) as f:
    lines = f.readlines()

analyzed = set()
for fname in os.listdir(TRADES_DIR):
    if fname.endswith('.json'):
        with open(os.path.join(TRADES_DIR, fname)) as f:
            d = json.load(f)
        a = d.get('analysis', {})
        analyzed.add((a.get('symbol',''), a.get('sell_time','')))

# Print all sells and their status
for line in lines:
    stripped = line.replace('**','').replace('\U0001f534',' ').replace('\U0001f7e2',' ').replace('\u26a0\ufe0f','')
    parts_check = [p.strip() for p in stripped.split('|')]
    if 'SELL' in parts_check and 'NO TRADE' not in stripped:
        info = extract_trade_info(line)
        if info and info.get('symbol'):
            key = (info['symbol'], info['time'])
            status = 'PROCESSED' if key in analyzed else 'UNPROCESSED'
            print(f'{status}|{info["time"]}|{info["symbol"]}|qty={info["qty"]}|price={info["price"]}|reason={info["reason"]}')
