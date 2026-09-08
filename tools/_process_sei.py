#!/usr/bin/env python3
"""Process SEI sell trade from 2026-05-27 23:30 using reason field for prices"""
import sys; sys.path.insert(0, '.')
from tools.trade_experience import *
import json
import re

# The sell record at Line 566 has the entry/exit prices embedded in the reason
# reason: "硬止损-5%—入场$0.07164出场$0.06806(-5.00%)..."
# We need to parse buy_price=$0.07164, sell_price=$0.06806 from the reason

with open('audit/TRADES.md') as f:
    lines = f.readlines()

# Find the SEI sell line
sell_line = None
for line in lines:
    stripped = line.replace('**', '')
    parts = [p.strip() for p in stripped.split('|')]
    if 'SELL' in parts and 'SEI' in stripped and 'NO TRADE' not in stripped:
        sell_line = line
        break

if not sell_line:
    print("No SEI sell found")
    sys.exit(1)

# Parse sell
info = extract_trade_info(sell_line)
print(f"Sell info: {json.dumps(info, indent=2, ensure_ascii=False)}")

# Extract entry/exit prices from reason
reason = info['reason']
entry_match = re.search(r'入场[：:]?\$?(\d+\.?\d*)', reason)
exit_match = re.search(r'出场[：:]?\$?(\d+\.?\d*)', reason)

entry_price = float(entry_match.group(1)) if entry_match else None
exit_price = float(exit_match.group(1)) if exit_match else None

if not entry_price or not exit_price:
    print(f"Could not parse prices from reason: {reason}")
    sys.exit(1)

print(f"Entry: ${entry_price}, Exit: ${exit_price}")

# Build buy_info manually from sell reason
buy_info = {
    'time': '2026-05-27 09:06:00',  # from the buy text description
    'symbol': info['symbol'],
    'price': str(entry_price),
    'qty': info['qty']
}

sell_info = {
    'time': info['time'],
    'symbol': info['symbol'],
    'price': str(exit_price),
    'qty': info['qty'],
    'reason': info['reason']
}

analysis = analyze_exit(sell_info, buy_info)
print(f"Analysis: {json.dumps(analysis, indent=2, ensure_ascii=False)}")

# Record it
entry = record_trade_experience(analysis)
if entry:
    print(f"经验已记录: {analysis['symbol']} P&L:{analysis['pnl_pct']:+.1f}% 质量:{analysis['exit_quality']}")
else:
    print(f"经验文件已存在（跳过重复记录）")
