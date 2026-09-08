#!/usr/bin/env python3
"""Run experience analysis on the latest exit trade."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import json
from trade_experience import get_last_exit, analyze_exit, record_trade_experience, show_master

def main():
    result = get_last_exit()
    if not result or not result['sell']:
        print("本轮无卖出")
        return

    sell = result['sell']
    buy = result['buy']
    print(f"Latest SELL: {sell['symbol']} at {sell['time']}")
    print(f"  Sell price: {sell.get('price','?')}, qty: {sell.get('qty','?')}, reason: {sell.get('reason','?')}")
    if buy:
        print(f"  Buy: {buy['symbol']} at {buy['time']}, price: {buy.get('price','?')}, qty: {buy.get('qty','?')}")
    else:
        print("  No matching buy found")

    analysis = analyze_exit(sell, buy)
    entry = record_trade_experience(analysis)
    if entry:
        print(f"-> 经验已记录: {analysis['symbol']} P&L:{analysis['pnl_pct']:+.1f}% 质量:{analysis['exit_quality']} 信号:{analysis['trigger_signals']}")
    else:
        print(f"-> 已存在跳过重复: {analysis['symbol']} P&L:{analysis['pnl_pct']:+.1f}% 质量:{analysis['exit_quality']}")
    
    # Show updated master
    print()
    print(show_master())

if __name__ == '__main__':
    main()
