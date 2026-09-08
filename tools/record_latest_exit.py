#!/usr/bin/env python3
"""记录最新卖出交易的经验分析"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))

# Add tools dir to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from trade_experience import *
import json

exit_info = get_last_exit()
if not exit_info:
    print("未找到任何卖出记录")
    sys.exit(0)

sell = exit_info['sell']
buy = exit_info['buy']

print("=== 最新卖出 ===")
print(f"  币种: {sell['symbol']}")
print(f"  时间: {sell['time']}")
print(f"  数量: {sell['qty']}")
print(f"  价格: {sell['price']}")
reason_short = sell['reason'][:120] if sell.get('reason') else 'N/A'
print(f"  原因: {reason_short}")

if buy:
    print(f"\n=== 对应买入 ===")
    print(f"  时间: {buy['time']}")
    print(f"  数量: {buy['qty']}")
    print(f"  价格: {buy['price']}")
    
    analysis = analyze_exit(sell, buy)
    record_trade_experience(analysis)
    print(f"\n经验已记录: {analysis['symbol']} P&L:{analysis['pnl_pct']:+.1f}% 质量:{analysis['exit_quality']}")
    print(f"  信号触发: {analysis['trigger_signals']}")
    print(f"  教训: {analysis['lesson']}")
else:
    print(f"\n未找到{sell['symbol']}的买入记录")
    # Still create a record with available info for the master archive
    try:
        analysis = analyze_exit(sell, buy)  # buy=None path
        record_trade_experience(analysis)
        print(f"  经验已记录(无买入数据): {analysis['symbol']} 信号:{analysis.get('trigger_signals',[])} 质量:{analysis['exit_quality']}")
    except Exception as e:
        print(f"  记录失败: {e}")

# Show master stats summary
master = load_master()
print(f"\n=== 总经验档案 ===")
print(f"  规则数: {len(master.get('rules', []))}")
print(f"  交易经验文件: {len(os.listdir(TRADES_DIR)) if os.path.isdir(TRADES_DIR) else 0} 个")
perf = master.get('exit_signal_performance', {})
if perf:
    print(f"  信号表现:")
    for sig, stats in sorted(perf.items()):
        print(f"    {sig}: {stats}")
