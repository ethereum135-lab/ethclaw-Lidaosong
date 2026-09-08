#!/usr/bin/env python3
"""Cron job: analyze latest sell trade and update experience archive."""
import sys
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system/tools')
from trade_experience import get_last_exit, analyze_exit, record_trade_experience, show_master
import json

# Find and analyze the latest sell trade
result = get_last_exit()
if not result or not result.get('sell'):
    print("[SILENT]")
    sys.exit(0)

sell = result['sell']
buy = result.get('buy')

print("=== 最新卖出 ===")
print(f"  币种: {sell.get('symbol', '?')}")
print(f"  时间: {sell.get('time', '?')}")
print(f"  数量: {sell.get('qty', '?')}")
print(f"  价格: {sell.get('price', '?')}")
print(f"  原因: {sell.get('reason', '?')}")

if buy:
    print(f"\n=== 对应买入 ===")
    print(f"  时间: {buy.get('time', '?')}")
    print(f"  价格: {buy.get('price', '?')}")
    print(f"  数量: {buy.get('qty', '?')}")
else:
    print("\n⚠️  未找到对应买入记录")

print()
analysis = analyze_exit(sell, buy)
print(f"P&L: {analysis['pnl_pct']:+.1f}%")
print(f"质量: {analysis['exit_quality']}")
print(f"经验: {analysis.get('lesson', 'N/A')}")
if analysis.get('trigger_signals'):
    print(f"触发信号: {', '.join(analysis['trigger_signals'])}")

# Record to experience archive
entry = record_trade_experience(analysis)
if entry:
    print(f"\n✅ 经验已记录至 data/experience/")
else:
    print(f"\nℹ️  该交易经验已存在，跳过重复记录")

# Show updated master stats
print()
master = json.load(open('/Users/lidaosong/zq_web4_trading_system/data/experience/MASTER_EXPERIENCE.json'))
print(f"=== 更新后总档案 ===")
print(f"  累计分析: {master['stats'].get('total_trades_analyzed', 0)}")
print(f"  正确退出: {master['stats'].get('correct_exits', 0)}")
print(f"  错误退出: {master['stats'].get('wrong_exits', 0)}")
print(f"  中性退出: {master['stats'].get('too_early_exits', 0)}")
