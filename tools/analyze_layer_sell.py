#!/usr/bin/env python3
"""分析LAYER最新卖出交易并记录经验"""
import sys
sys.path.insert(0, 'tools')
from trade_experience import extract_trade_info, analyze_exit, record_trade_experience, load_master

with open('audit/TRADES.md', encoding='utf-8') as f:
    lines = f.readlines()

sell_line = None
buy_line = None

for line in lines:
    stripped = line.replace('\ufe0f', '').replace('\u200d', '').replace('**', '').strip()
    parts = [p.strip() for p in stripped.split('|')]
    has_sell = any(p == 'SELL' for p in parts)
    has_buy = any(p == 'BUY' for p in parts)
    if has_sell and 'LAYER' in stripped and 'NO TRADE' not in stripped:
        sell_line = line
    if has_buy and 'LAYER' in stripped and 'NO TRADE' not in stripped:
        buy_line = line

if sell_line and buy_line:
    sell_info = extract_trade_info(sell_line)
    buy_info = extract_trade_info(buy_line)

    print('=== LAYER 最新卖出 ===')
    print(f'卖出时间: {sell_info["time"]}')
    print(f'买入时间: {buy_info["time"]}')
    print(f'卖出价格: {sell_info["price"]}')
    print(f'买入价格: {buy_info["price"]}')
    print(f'数量: {sell_info["qty"]}')
    print(f'卖出原因: {sell_info["reason"]}')

    analysis = analyze_exit(sell_info, buy_info)
    result = record_trade_experience(analysis)

    if result is None:
        print('[跳过] 该交易已分析过')
    else:
        print(f'经验已记录: {analysis["symbol"]} P&L:{analysis["pnl_pct"]:+.1f}%')
        print(f'  P&L USD: {analysis["pnl_usd"]:+.2f}')
        print(f'  质量: {analysis["exit_quality"]}')
        print(f'  触发信号: {analysis["trigger_signals"]}')
        print(f'  教训: {analysis["lesson"]}')

    # 显示总经验档案统计
    master = load_master()
    stats = master.get('stats', {})
    print(f'\n=== 总经验档案 ===')
    print(f'已分析交易: {stats.get("total_trades_analyzed", 0)}')
    print(f'正确退出: {stats.get("correct_exits", 0)}')
    print(f'错误退出(过早): {stats.get("wrong_exits", 0)}')
    print(f'过早退出: {stats.get("too_early_exits", 0)}')
    print(f'信号表现: {json.dumps(master.get("exit_signal_performance", {}), indent=2)}')
else:
    print(f'sell_line={sell_line is not None}, buy_line={buy_line is not None}')
    print('排查:')
    for n, line in enumerate(lines, 1):
        if 'LAYER' in line:
            print(f'  L{n}: {line.strip()[:80]}')
