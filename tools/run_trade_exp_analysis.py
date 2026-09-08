#!/usr/bin/env python3
"""Run trade experience analysis on the latest sell trade."""
import sys
sys.path.insert(0, 'tools')
from trade_experience import get_last_exit, analyze_exit, record_trade_experience, show_master
import json

# Get latest sell from TRADES.md
result = get_last_exit()
if not result:
    print('未找到卖出记录')
    sys.exit(0)

sell = result['sell']
buy = result['buy']
print(f'最新卖出: {sell["symbol"]} @ {sell["time"]}')
print(f'卖出原因: {sell["reason"]}')
if buy:
    print(f'对应买入: {buy["time"]} @ {buy["price"]}')
else:
    print(f'⚠️ 未找到对应买入记录')
print()

# Run analysis
analysis = analyze_exit(sell, buy)
print(json.dumps(analysis, indent=2, ensure_ascii=False))

# Record experience
entry = record_trade_experience(analysis)
if entry:
    print(f'\n✅ 新经验已记录: {analysis["symbol"]} P&L:{analysis["pnl_pct"]:+.1f}% 质量:{analysis["exit_quality"]}')
else:
    print(f'\n➖ 此笔交易记录已存在，跳过重复分析')

# Show updated master stats
print('\n' + '='*60)
print('更新后总经验档案:')
print(show_master())
