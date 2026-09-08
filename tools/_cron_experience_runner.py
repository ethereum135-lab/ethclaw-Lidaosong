#!/usr/bin/env python3
"""Cron runner: analyze latest sell trade and update experience master."""
import sys
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system/tools')
from trade_experience import *
import json
import os

os.chdir('/Users/lidaosong/zq_web4_trading_system')

result = get_last_exit()
if result and result['sell']:
    sell = result['sell']
    buy = result['buy']
    print(f'找到卖出: {sell["symbol"]} @ {sell["time"]}')
    print(f'  卖出价: ${sell["price"]}  数量: {sell["qty"]}  原因: {sell["reason"]}')
    if buy:
        print(f'匹配买入: {buy["symbol"]} @ {buy["time"]}')
        print(f'  买入价: ${buy["price"]}  数量: {buy["qty"]}  原因: {buy.get("reason","")}')
    else:
        print('⚠️  未找到匹配买入记录')
    
    analysis = analyze_exit(sell, buy)
    print(f'\n分析结果:')
    print(f'  买入价: ${analysis["buy_price"]:.6f}')
    print(f'  卖出价: ${analysis["sell_price"]:.6f}')
    print(f'  P&L: {analysis["pnl_pct"]:+.2f}%  (${analysis["pnl_usd"]:+.2f})')
    print(f'  触发信号: {analysis["trigger_signals"]}')
    print(f'  退出质量: {analysis["exit_quality"]}')
    print(f'  经验: {analysis["lesson"]}')
    
    entry = record_trade_experience(analysis)
    if entry:
        print(f'\n✅ 经验已记录: {analysis["symbol"]} P&L:{analysis["pnl_pct"]:+.1f}% 质量:{analysis["exit_quality"]}')
    else:
        print(f'\n➖ 已分析过，跳过重复写入')
    
    print(f'\n{show_master()}')
else:
    print('未找到可分析的卖出记录')
