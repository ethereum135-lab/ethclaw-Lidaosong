#!/usr/bin/env python3
"""Check if any sells in TRADES.md are not yet analyzed."""
import os, sys, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from trade_experience import extract_trade_info, TRADES_DIR

# List all trade experience files
trades = sorted(os.listdir(TRADES_DIR), reverse=True)
print(f"已分析交易: {len(trades)} 笔")
print("最近5笔:")
for t in trades[:5]:
    with open(os.path.join(TRADES_DIR, t)) as f:
        e = json.load(f)
    a = e['analysis']
    print(f"  {a['sell_time']} {a['symbol']:8s} P&L:{a['pnl_pct']:+6.1f}%  {a['exit_quality']:8s} {a['exit_reason'][:50]}")
print()

# Find latest sells not yet analyzed
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'audit', 'TRADES.md')) as f:
    lines = f.readlines()

sell_lines = []
for line in reversed(lines):
    stripped = line.replace('**', '').replace('*', '')
    parts_check = [p.strip() for p in stripped.split('|')]
    if 'SELL' in parts_check and 'NO TRADE' not in stripped:
        sell_lines.append(line)

print(f"TRADES.md中发现 {len(sell_lines)} 笔SELL行")

# Check which ones are already analyzed
analyzed_set = set()
for t in trades:
    with open(os.path.join(TRADES_DIR, t)) as f:
        e = json.load(f)
    a = e['analysis']
    analyzed_set.add((a['symbol'], a['sell_time']))

unanalyzed = []
for line in sell_lines[:10]:
    info = extract_trade_info(line)
    if info and info.get('symbol') and info.get('price','').replace('.','').replace('-','').strip():
        key = (info['symbol'], info['time'])
        if key not in analyzed_set:
            unanalyzed.append(info)
            print(f"! 未分析: {info['time']} {info['symbol']:8s} {info['price']:>10s} {info.get('reason','')[:40]}")
        else:
            print(f"  Already: {info['symbol']:8s} at {info['time']}")

if not unanalyzed:
    print("所有卖出均已分析")

# Also show the most recent unanalyzed KMNO, ENJ sells
print()
print("--- 详细检查最近卖出 ---")
for line in sell_lines[:5]:
    info = extract_trade_info(line)
    if info:
        key = (info['symbol'], info['time'])
        status = "ANALYZED" if key in analyzed_set else "UNANALYZED"
        print(f"  {status}: {info['time']} {info['symbol']:8s} price={info['price']:>10s} reason={info.get('reason','')[:60]}")
