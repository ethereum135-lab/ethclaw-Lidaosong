#!/usr/bin/env python3
"""分析最新卖出交易并更新经验档案"""
import sys
sys.path.insert(0, 'tools')
from trade_experience import get_last_exit, analyze_exit, record_trade_experience

# 用 built-in get_last_exit() 自动找最新卖出+对应的买入
result = get_last_exit()
if result and result['sell'] and result['buy']:
    sell_info = result['sell']
    buy_info = result['buy']

    analysis = analyze_exit(sell_info, buy_info)
    entry = record_trade_experience(analysis)

    if entry:
        print(f'SUCCESS: 经验已记录 {analysis["symbol"]}')
        print(f'P&L: {analysis["pnl_pct"]:+.2f}% ({analysis["pnl_usd"]:+.2f}USD)')
        print(f'入场: {analysis["buy_time"]} @ ${analysis["buy_price"]:.4f}')
        print(f'出场: {analysis["sell_time"]} @ ${analysis["sell_price"]:.4f}')
        print(f'退出质量: {analysis["exit_quality"]}')
        print(f'触发信号: {analysis["trigger_signals"]}')
        print(f'经验: {analysis["lesson"]}')
    else:
        print(f'SKIP: {analysis["symbol"]} 已分析过，跳过')
        print(f'P&L: {analysis["pnl_pct"]:+.2f}%')
        print(f'质量: {analysis["exit_quality"]}')
elif result and result['sell'] and not result['buy']:
    print(f'WARN: 最新卖出 {result["sell"]["symbol"]} 未找到对应买入记录')
    print(f'SELL详情: {result["sell"]}')
else:
    print('NO_TRADE: 本轮无卖出')
