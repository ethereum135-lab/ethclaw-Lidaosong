#!/usr/bin/env python3
"""分析所有未处理的卖出交易并更新总经验档案"""
import sys; sys.path.insert(0, 'tools')
import os
from trade_experience import *

# 已分析交易去重
TRADES_DIR = os.path.join(BASE_DIR, 'data', 'experience', 'trades')
os.makedirs(TRADES_DIR, exist_ok=True)
analyzed = set()
if os.path.isdir(TRADES_DIR):
    for fname in os.listdir(TRADES_DIR):
        if fname.endswith('.json'):
            analyzed.add(fname)

print(f'已分析交易数: {len(analyzed)}')

# 读取交易日志
with open(TRADE_LOG) as f:
    lines = f.readlines()

# 所有卖出
sells = []
for i, line in enumerate(lines):
    if ' SELL ' in line and 'NO TRADE' not in line:
        info = extract_trade_info(line)
        if info:
            info['_line_idx'] = i
            sells.append(info)

print(f'总卖出记录数: {len(sells)}')

# 找每个卖出对应买入并分析
new_count = 0
for sell in sells:
    ts = sell['time'].replace(' ', '_').replace(':', '-')
    filename = f'{ts}_{sell["symbol"]}.json'
    if filename in analyzed:
        continue

    # 找对应买入：同一币种在该卖出前最近一次买入（按行顺序）
    buy = None
    for i in range(sell['_line_idx'] - 1, -1, -1):
        line = lines[i]
        if ' BUY ' in line and 'NO TRADE' not in line:
            info = extract_trade_info(line)
            if info and info['symbol'] == sell['symbol']:
                buy = info
                break

    if buy:
        analysis = analyze_exit(sell, buy)
        entry = record_trade_experience(analysis)
        if entry:
            new_count += 1
            icon = '✅' if analysis['exit_quality'] == 'correct' else ('❌' if analysis['exit_quality'] == 'wrong' else '➖')
            print(f'{icon} {analysis["symbol"]:8s} 买入:{float(buy["price"]):.4f}→卖出:{float(sell["price"]):.4f}  P&L:{analysis["pnl_pct"]:+.1f}%  USD:{analysis["pnl_usd"]:+.2f}  质量:{analysis["exit_quality"]}  信号:{analysis.get("trigger_signals", [])}')
    else:
        print(f'⚠️ {sell["symbol"]:8s} 在{sell["time"]}卖出但未找到对应买入')

print(f'\n新分析交易数: {new_count}')

# 打印最新总经验档案
print()
master = load_master()
print(show_master())
