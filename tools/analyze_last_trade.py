#!/usr/bin/env python3
"""分析最新卖出交易并记录经验"""
import sys; sys.path.insert(0, 'tools')
from trade_experience import *

exit_data = get_last_exit()
if exit_data and exit_data['sell']:
    sell_info = exit_data['sell']
    buy_info = exit_data['buy']

    print('=== 最新卖出交易 ===')
    print(f'币种: {sell_info["symbol"]}')
    print(f'时间: {sell_info["time"]}')
    print(f'卖出价: {sell_info["price"]}')
    print(f'数量: {sell_info["qty"]}')
    print(f'原因: {sell_info.get("reason","")}')
    if buy_info:
        print(f'买入价: {buy_info["price"]}')
        print(f'买入时间: {buy_info["time"]}')
    else:
        print('WARNING: 未找到对应买入记录')

    analysis = analyze_exit(sell_info, buy_info)
    print(f'\n=== 分析结果 ===')
    print(f'P&L: {analysis["pnl_pct"]:+.2f}%  ({analysis["pnl_usd"]:+.4f} USD)')
    print(f'出场质量: {analysis.get("exit_quality","?")}')
    print(f'触发信号: {analysis.get("signals",[])}')

    record_trade_experience(analysis)
    print(f'\n经验已记录至 data/experience/trades/')

    # 总经验档案摘要
    master = load_master()
    print(f'\n=== 总经验档案 v{master.get("version","?")} ===')
    stats = master.get('stats', {})
    if stats:
        print(f'总交易笔数: {stats.get("total_trades",0)}')
        print(f'胜率: {stats.get("win_rate",0)*100:.1f}%')
        print(f'平均盈亏: {stats.get("avg_pnl_pct",0):+.2f}%')
    rules = master.get('rules', [])
    if rules:
        print(f'经验规则数: {len(rules)}')
        for r in rules[-3:]:
            print(f'  - {r[:100]}')
else:
    print('本轮无卖出')
