#!/usr/bin/env python3
"""快速运行最新卖出经验分析"""
import sys; sys.path.insert(0, 'tools')
from trade_experience import *

# 1) 获取最新卖出
result = get_last_exit()
if not result or not result['sell']:
    print("未找到卖出记录")
    sys.exit(0)

sell = result['sell']
buy = result['buy']

print(f"最新卖出: {sell['symbol']}")
print(f"  时间: {sell['time']}")
print(f"  数量: {sell['qty']}")
print(f"  价格: ${sell['price']}")
print(f"  原因: {sell['reason']}")

if buy:
    print(f"对应买入: {buy['symbol']}")
    print(f"  时间: {buy['time']}")
    print(f"  数量: {buy['qty']}")
    print(f"  价格: ${buy['price']}")
    print(f"  原因: {buy.get('reason', '')}")
else:
    print("  注意: 未找到匹配买入记录")

# 2) 分析
print("\n--- 分析中 ---")
analysis = analyze_exit(sell, buy)

# 3) 记录
entry = record_trade_experience(analysis)

if entry:
    print(f"\n经验已记录: {analysis['symbol']}")
    print(f"  P&L: {analysis['pnl_pct']:+.1f}%")
    print(f"  质量: {analysis['exit_quality']}")
    print(f"  信号: {analysis['trigger_signals']}")
    print(f"  教训: {analysis['lesson']}")
    if analysis['pnl_usd']:
        print(f"  PnL USD: ${analysis['pnl_usd']:.2f}")
else:
    # 已分析过，显示现有结果
    print(f"\n跳过: {analysis['symbol']} 已分析过 (去重)")
    print(f"  P&L: {analysis['pnl_pct']:+.1f}% | 质量: {analysis['exit_quality']}")

# 4) 显示更新后的总档案统计
print("\n--- 总经验档案 ---")
master = load_master()
print(f"  总分析交易数: {master['stats'].get('total_trades_analyzed', 0)}")
print(f"  正确退出: {master['stats'].get('correct_exits', 0)}")
print(f"  错误退出: {master['stats'].get('wrong_exits', 0)}")
print(f"  中性/过早退出: {master['stats'].get('too_early_exits', 0)}")
print(f"  经验规则数: {len(master.get('rules', []))}")
print(f"  信号类型: {list(master.get('exit_signal_performance', {}).keys())}")
