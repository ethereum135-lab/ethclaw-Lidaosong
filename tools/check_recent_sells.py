#!/usr/bin/env python3
"""Find latest unanalyzed sell and process it"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
from trade_experience import *

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Get all sells with pipe format that have corresponding buys
with open(os.path.join(BASE, 'audit', 'TRADES.md')) as f:
    lines = f.readlines()

sells = []
for line in lines:
    stripped = line.replace('**', '')
    if 'SELL' in stripped and 'NO TRADE' not in stripped:
        info = extract_trade_info(line)
        if info and info.get('symbol') and info.get('price','').replace('.','').replace('-','').strip() \
           and not info.get('is_table_format', False):
            # Find corresponding buy
            sym = info['symbol']
            stime = info['time']
            buys = []
            for l2 in lines:
                s2 = l2.replace('**', '')
                if 'BUY' in s2 and 'NO TRADE' not in s2:
                    bi = extract_trade_info(l2)
                    if bi and bi['symbol'] == sym and bi['time'] < stime:
                        buys.append(bi)
            buy = max(buys, key=lambda x: x['time']) if buys else None
            if buy:
                sells.append((info, buy))

if not sells:
    print("NO_UNANALYZED_SELLS: no sell+buy pairs found")
    sys.exit(0)

# Sort by sell time descending (most recent first)
sells.sort(key=lambda x: x[0]['time'], reverse=True)

for sell_info, buy_info in sells[:5]:
    ts = sell_info['time'].replace(' ', '_').replace(':', '-')
    filename = f"{ts}_{sell_info['symbol']}.json"
    trade_file = os.path.join(TRADES_DIR, filename)
    already = os.path.exists(trade_file)
    
    analysis = analyze_exit(sell_info, buy_info)
    print(f"{'NEW' if not already else 'OLD'}|{sell_info['symbol']}|{sell_info['time']}|P&L:{analysis['pnl_pct']:+.1f}%|{analysis['exit_quality']}|signals:{analysis['trigger_signals']}")
    
    if not already:
        entry = record_trade_experience(analysis)
        if entry:
            print(f"  -> RECORDED to {trade_file}")
        else:
            print(f"  -> record_trade_experience returned None")
