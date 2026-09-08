#!/usr/bin/env python3
"""Cron: analyze latest sell trade and update experience archive."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from trade_experience import *

# Get all actual sell lines from TRADES.md (recent 30 days)
import re
with open('audit/TRADES.md') as f:
    lines = f.readlines()

# Find all SELL lines with dates
sells = []
for i, line in enumerate(lines):
    stripped = line.replace('**','').replace('NO TRADE','')
    parts_check = [p.strip() for p in stripped.split('|')]
    has_sell = 'SELL' in parts_check or any(p.startswith('SELL ') for p in parts_check)
    if has_sell and 'SELL_NOW' not in line:
        info = extract_trade_info(line)
        if info and info.get('symbol') and info.get('time') and '2026-06-21' in info['time']:
            sells.append((i+1, info['time'], info['symbol'], info.get('price',''), info.get('reason','')))

print('=== 今日(2026-06-21) SELL记录 ===')
for ln, tm, sym, pr, rs in sells:
    print(f'  行{ln}: {tm} | {sym} | {pr} | {rs[:40]}')

# Check which ones are recorded
print()
print('=== 已记录经验文件 ===')
recorded_files = sorted([f for f in os.listdir('data/experience/trades') if f.endswith('.json') and '2026-06-21' in f])
for fn in recorded_files:
    with open(os.path.join('data/experience/trades', fn)) as jf:
        data = json.load(jf)
    a = data['analysis']
    print(f'  {fn}: {a["symbol"]} P&L={a["pnl_pct"]:+.1f}% 质量={a["exit_quality"]}')

# Show master summary
print()
print('=== 总经验档案 ===')
master = load_master()
s = master['stats']
print(f'  总分析: {s["total_trades_analyzed"]} | 正确: {s["correct_exits"]} | 错误: {s["wrong_exits"]} | 中性: {s["too_early_exits"]}')
print(f'  正确率: {s["correct_exits"]/s["total_trades_analyzed"]*100:.1f}%')
