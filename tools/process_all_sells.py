#!/usr/bin/env python3
"""Process all SELL trades from TRADES.md and record experience."""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import json

# Read TRADES.md
with open('audit/TRADES.md') as f:
    lines = f.readlines()

# Find all sells (chronological order)
sells = []
for line in lines:
    if ' SELL ' in line and 'NO TRADE' not in line:
        sells.append(line)

print(f'Found {len(sells)} sells in TRADES.md')

def info_parser(raw):
    cols = [x.strip() for x in raw.split('|')]
    return {
        'symbol': cols[3],
        'time': cols[1],
        'price': cols[5].replace('$', ''),
        'qty': cols[4],
        'reason': cols[6] if len(cols) > 6 else ''
    }

# Process each sell
count = 0
for sell_line in sells:
    parts = [p.strip() for p in sell_line.split('|')]
    if len(parts) < 7:
        print(f'  SKIP (bad format): {parts}')
        continue
    
    symbol = parts[3]
    sell_time = parts[1]
    
    # Find corresponding buy (latest buy before sell for same symbol)
    buy_line = None
    for line in lines:
        p = [x.strip() for x in line.split('|')]
        if len(p) >= 7 and ' BUY ' in line and p[3] == symbol and p[1] < sell_time:
            buy_line = line
    
    if not buy_line:
        print(f'  SKIP {symbol}: no buy record found before {sell_time}')
        continue
    
    sell_info = info_parser(sell_line)
    buy_info = info_parser(buy_line)
    
    try:
        analysis = analyze_exit(sell_info, buy_info)
        record_trade_experience(analysis)
        pnl = analysis.get('pnl_pct', 0)
        quality = analysis.get('exit_quality', '?')
        reason = analysis.get('exit_reason', '')[:40]
        print(f'  OK {symbol}: P&L {pnl:+.1f}%  quality={quality}  reason={reason}')
        count += 1
    except Exception as e:
        print(f'  FAIL {symbol}: {e}')

print(f'\nProcessed {count}/{len(sells)} sells. Experience archived to audit/trade_experience.json')

# Show summary
exp_path = 'audit/trade_experience.json'
try:
    with open(exp_path) as f:
        data = json.load(f)
    entries = data.get('entries', [])
    print(f'\nTotal experience entries: {len(entries)}')
    print(f'Total trades: {data.get("total_trades", 0)}')
    print(f'Win rate: {data.get("win_rate", "N/A")}')
    if entries:
        print('\nLast 10 entries:')
        for e in entries[-10:]:
            print(f'  {e.get("symbol","?"):8s}  {e.get("time","?"):19s}  P&L {e.get("pnl_pct",0):+6.1f}%  {e.get("exit_quality","?"):10s}  {str(e.get("exit_reason",""))[:30]}')
except FileNotFoundError:
    print('\nExperience file not found!')
except Exception as e:
    print(f'\nRead error: {e}')
