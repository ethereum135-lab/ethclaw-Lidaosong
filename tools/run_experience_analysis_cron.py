#!/usr/bin/env python3
"""Cron job: analyze latest sell trades and update master experience archive.
Runs all sells from the current date, properly handles dust cleanup trades."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

from trade_experience import *

today = '2026-06-19'

# Collect all sells for today
with open(TRADE_LOG) as f:
    lines = f.readlines()

sells_in_scope = []
for line in lines:
    info = extract_trade_info(line)
    if (info and info.get('action') == 'SELL'
        and info.get('symbol') and info.get('price', '').replace('.', '').replace('-', '').strip()
        and info['time'].startswith(today)):
        sells_in_scope.append(info)

print(f"今日卖出分析 ({today}): {len(sells_in_scope)} 笔")

# Process each sell with its matching buy
new_entries = 0
skipped = 0
no_buy = 0
total_pnl = 0.0
quality_counts = {'correct': 0, 'wrong': 0, 'neutral': 0}

for sell_info in sells_in_scope:
    buy_info = None
    for line in lines:
        info = extract_trade_info(line)
        if (info and info.get('action') == 'BUY'
            and info.get('symbol') == sell_info['symbol']
            and info['time'] < sell_info['time']):
            if buy_info is None or info['time'] > buy_info['time']:
                buy_info = info

    symbol = sell_info['symbol']
    reason = sell_info.get('reason', '')
    price = sell_info['price']

    if buy_info:
        analysis = analyze_exit(sell_info, buy_info)
        entry = record_trade_experience(analysis)

        pnl = analysis['pnl_pct']
        total_pnl += analysis['pnl_usd']
        if analysis['exit_quality'] in quality_counts:
            quality_counts[analysis['exit_quality']] += 1

        if entry:
            new_entries += 1
            status = "新记录"
        else:
            skipped += 1
            status = "已存在(跳过)"

        sigs = '+'.join(analysis['trigger_signals']) if analysis['trigger_signals'] else '(无)'
        print(f"  {symbol:8s} | {analysis['exit_quality']:8s} | P&L:{pnl:+.2f}% | ${analysis['pnl_usd']:+.4f} | 信号:{sigs:10s} | {status}")
    else:
        no_buy += 1
        print(f"  {symbol:8s} | 尘仓清理 | 无对应买入记录 (疑似A4旧仓) | 价格:${price} | 原因:{reason[:40]}")

print(f"\n--- 汇总 ---")
print(f"  新分析: {new_entries} | 跳过(已存在): {skipped} | 无买入记录: {no_buy}")
if new_entries > 0:
    print(f"  退出质量分布: {json.dumps(quality_counts)}")
    print(f"  总盈亏: ${total_pnl:+.4f}")

print(f"\n{'='*50}")
print("总经验档案 (更新后):")
print(show_master())
