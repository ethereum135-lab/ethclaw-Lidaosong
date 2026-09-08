#!/usr/bin/env python3
"""经验分析工具运行：处理最新卖出交易并更新总经验档案"""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import json
import os
import glob

print("=" * 60)
print("  经验分析运行报告")
print("=" * 60)

# 1) 检查有无最近未记录的pipe格式卖出
result = get_last_exit()
new_recorded = False
if result and result['sell']:
    ts = result['sell']['time'].replace(' ', '_').replace(':', '-')
    trade_file = os.path.join('data/experience/trades', f"{ts}_{result['sell']['symbol']}.json")
    if not os.path.exists(trade_file):
        analysis = analyze_exit(result['sell'], result['buy'])
        entry = record_trade_experience(analysis)
        print(f"\n✅ 新交易已记录: {analysis['symbol']} P&L={analysis['pnl_pct']:+.1f}%")
        new_recorded = True
    else:
        print(f"\n➖ 最后pipe格式卖出已分析过: {result['sell']['symbol']} @ {result['sell']['time']}")
        print(f"   买入${result['buy']['price']} → 卖出${result['sell']['price']} | 原因: {result['sell'].get('reason','')}")
else:
    print("\n⚠️  未找到未处理的pipe格式卖出记录")

# 2) 统计今日交易经验文件
print(f"\n--- 今日(2026-07-02)交易经验统计 ---")
today_files = sorted(glob.glob('data/experience/trades/2026-07-02_*.json'))
print(f"  总交易经验文件: {len(today_files)} 笔")

# 按symbol分组
trades_by_symbol = {}
total_pnl = 0
correct = wrong = neutral = 0
for f in today_files:
    with open(f) as fh:
        d = json.load(fh)
    a = d['analysis']
    sym = a['symbol']
    if sym not in trades_by_symbol:
        trades_by_symbol[sym] = []
    trades_by_symbol[sym].append(a)
    total_pnl += a['pnl_usd']
    if a['exit_quality'] == 'correct':
        correct += 1
    elif a['exit_quality'] == 'wrong':
        wrong += 1
    else:
        neutral += 1

# 按币种显示明细
for sym in sorted(trades_by_symbol.keys()):
    entries = trades_by_symbol[sym]
    sym_pnl = sum(e['pnl_usd'] for e in entries)
    sym_pnl_pct = sum(e['pnl_pct'] for e in entries) / len(entries)
    first = entries[0]
    last = entries[-1]
    print(f"  {sym:6s}: {len(entries):3d}笔 | 首笔买${first['buy_price']:.4f} → 末笔卖${last['sell_price']:.4f} | "
          f"均P&L={sym_pnl_pct:+.1f}% | 总盈亏${sym_pnl:+.2f}")

print(f"\n  质量分布: ✅正确={correct} | ❌错误={wrong} | ➖中性={neutral}")
print(f"  今日总盈亏: ${total_pnl:+.2f}")

# 3) 显示总档案
print(show_master())
