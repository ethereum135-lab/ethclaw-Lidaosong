#!/usr/bin/env python3
"""Compute daily profit from TRADES.md SELL entries"""
import re

with open('TRADES.md') as f:
    content = f.read()

# Find all SELL lines with P&L info
# Pattern: |||DATE|SELL|SYMBOL|QTY|$PRICE|REASON
sell_pattern = re.findall(r'\|\|\|?\|?([\d\-: ]+)\|SELL\|(\w+)\|([\d.]+)\|\$?([\d.]+)\|([^|]+)', content)

total_pnl = 0.0
print("=== Today's SELLs (2026-05-21) ===")
for match in sell_pattern:
    date_str = match[0]
    if '2026-05-21' in date_str:
        sym = match[1]
        qty = match[2]
        price = match[3]
        reason = match[4]
        print(f"  {date_str} | SELL {sym} | qty={qty} | price=${price} | {reason[:50]}")
        # Try to extract P&L from reason or context

# Also find the daily profit line from the latest nodes
daily_lines = re.findall(r'daily_profit:?[:\s]*\+?\$?([\d.]+)/(?:\$?([\d.]+))?', content)
print(f"\n=== Daily Profit References ===")
for dl in daily_lines:
    print(f"  ${dl[0]}/{dl[1] if dl[1] else 'N/A'}")

print(f"\n=== Total P&L from matched SELLs ===")
# Let me just grep for the daily profit summary
for line in content.split('\n'):
    if 'daily_profit' in line.lower() or '每日目标' in line:
        print(f"  {line.strip()[:120]}")
