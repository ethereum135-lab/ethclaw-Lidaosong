#!/usr/bin/env python3
"""检查FIL经验文件是否有新记录未分析"""
import json, os

exp_dir = 'data/experience/trades'
fil_files = sorted([f for f in os.listdir(exp_dir) if 'FIL' in f])

print('=== FIL经验文件一览 ===')
for f in fil_files:
    with open(os.path.join(exp_dir, f)) as fh:
        data = json.load(fh)
    a = data['analysis']
    sp = a['sell_price']
    print(f'  {f:40s} sell_time={a["sell_time"]:25s} sell_price={sp:>8.4f} PnL={a["pnl_pct"]:>+7.2f}% reason={a["exit_reason"]}')

print()

# Check if latest 0.9868 sell is recorded
latest_price = 0.9868
found = []
for f in fil_files:
    with open(os.path.join(exp_dir, f)) as fh:
        data = json.load(fh)
    a = data['analysis']
    if abs(a['sell_price'] - latest_price) < 0.001:
        found.append((f, a['sell_time'], a['pnl_pct']))

if found:
    for f, t, p in found:
        print(f'  price 0.9868 already recorded: {f}: sell_time={t} PnL={p:+.2f}%')
else:
    print(f'  WARNING: sell_price=0.9868 NOT recorded in experience files')
