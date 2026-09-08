#!/usr/bin/env python3
"""Cron task: analyze latest sell and update master experience"""
import sys
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system/tools')
from trade_experience import *

result = get_last_exit()
if result and result['sell']:
    sell = result['sell']
    buy = result['buy']
    print('=== Recent Sell Found ===')
    print(f'Symbol: {sell["symbol"]}')
    print(f'Sell Time: {sell["time"]}')
    print(f'Sell Price: {sell["price"]}')
    print(f'Sell Qty: {sell["qty"]}')
    print(f'Exit Reason: {sell["reason"]}')
    if buy:
        print(f'Buy Time: {buy["time"]}')
        print(f'Buy Price: {buy["price"]}')
        print(f'Buy Qty: {buy["qty"]}')
    else:
        print('Buy: NOT FOUND')

    analysis = analyze_exit(sell, buy)
    entry = record_trade_experience(analysis)
    if entry:
        print(f'\n✅ 新经验已记录: {analysis["symbol"]} PnL:{analysis["pnl_pct"]:+.1f}% 质量:{analysis["exit_quality"]} 信号:{analysis["trigger_signals"]}')
    else:
        print(f'\n⏭️ 跳过重复: {analysis["symbol"]}（已在经验档案中）')
else:
    print('未找到卖出记录')

print()
print(show_master())
