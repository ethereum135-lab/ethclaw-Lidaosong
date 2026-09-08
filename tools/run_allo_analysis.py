#!/usr/bin/env python3
"""ALLO尘仓经验分析 - 从reason字段提取价格并记录经验"""
import sys, re, json
sys.path.insert(0, 'tools')
from trade_experience import *

pair = get_last_exit()
sell_info = pair['sell']

reason = sell_info.get('reason', '')
symbol = sell_info['symbol']
sell_time = sell_info['time']
qty = float(sell_info['qty'])

# Extract prices from reason field
buy_m = re.search(r'入场(\d+\.?\d*)', reason)
sell_m = re.search(r'出场(\d+\.?\d*)', reason)

buy_price = float(buy_m.group(1)) if buy_m else 0
sell_price = float(sell_m.group(1)) if sell_m else 0

print('=' * 50)
print(f'经验分析: {symbol} SELL @ {sell_time}')
print('=' * 50)
print(f'数量: {qty}')
print(f'入场价(从reason提取): ${buy_price:.4f}')
print(f'出场价(从reason提取): ${sell_price:.4f}')

if buy_price > 0 and sell_price > 0:
    pnl_pct = (sell_price - buy_price) / buy_price * 100
    pnl_usd = qty * (sell_price - buy_price)
    print(f'')
    print(f'P&L: {pnl_pct:+.2f}%  (${pnl_usd:+.2f})')

    # Create analysis dict matching analyze_exit format
    analysis = {
        'symbol': symbol,
        'sell_time': sell_time,
        'buy_time': '遗产仓-未知',
        'sell_price': sell_price,
        'buy_price': buy_price,
        'exit_reason': reason,
        'qty': qty,
        'pnl_pct': pnl_pct,
        'pnl_usd': pnl_usd,
        'trigger_signals': ['尘仓清仓'],
        'exit_quality': 'neutral',
        'lesson': f'{symbol}尘仓清仓({pnl_pct:+.1f}%) - 小额亏损强制回笼资金,符合资金管理规则',
    }

    record = record_trade_experience(analysis)
    if record is None:
        print('(已存在,跳过重复)')
    else:
        print('经验已记录到总档案')

    # Show updated master
    master = load_master()
    print('')
    print('--- 总经验档案 ---')
    print(f'总分析交易: {master["stats"]["total_trades_analyzed"]}')
    print(f'正确退出: {master["stats"]["correct_exits"]}')
    print(f'错误退出: {master["stats"]["wrong_exits"]}')
    print(f'平进平出: {master["stats"]["too_early_exits"]}')
    print(f'积累规则数: {len(master["rules"])}')
else:
    print('无法提取价格,跳过')
