#!/usr/bin/env python3
"""每日经验分析汇总"""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import os

# 统计文件数和master对比
files = [f for f in os.listdir(TRADES_DIR) if f.endswith('.json')]
print(f'交易分析文件数: {len(files)}')

# 今日
today = '2026-06-23'
today_files = sorted([f for f in files if f.startswith(today)])
daily_file = os.path.join(DAILY_DIR, f'{today}.md')

if today_files:
    if os.path.exists(daily_file):
        print(f'今日汇总已存在: {len(today_files)} 笔')
    else:
        print('生成今日汇总...')
        summary = generate_daily_summary(today)
        print(summary)
    
    total_pnl = 0.0
    for f in today_files:
        with open(os.path.join(TRADES_DIR, f)) as fh:
            entry = json.load(fh)
            a = entry['analysis']
            total_pnl += a['pnl_usd']
            icon = '❌' if a['exit_quality'] == 'wrong' else ('✅' if a['exit_quality'] == 'correct' else '➖')
            print(f'  {icon} {a["symbol"]:8s} P&L:{a["pnl_pct"]:+.1f}%  ${a["pnl_usd"]:+.2f}  {a["exit_quality"]}')
    print(f'\n今日总盈亏: ${total_pnl:+.2f}')
    
    # 汇总信号表现
    signals = {}
    for f in today_files:
        with open(os.path.join(TRADES_DIR, f)) as fh:
            entry = json.load(fh)
            a = entry['analysis']
            for sig in a.get('trigger_signals', []):
                signals[sig] = signals.get(sig, 0) + 1
    if signals:
        print(f'\n今日触发信号: {signals}')
else:
    print(f'今日 ({today}) 无卖出交易分析')

# Master stats
master = load_master()
print(f'\n=== 总经验档案 ===')
print(f'总分析: {master["stats"]["total_trades_analyzed"]} | 正确: {master["stats"]["correct_exits"]} | 错误: {master["stats"]["wrong_exits"]} | 中性: {master["stats"]["too_early_exits"]}')
correct_rate = master["stats"]["correct_exits"] / max(master["stats"]["total_trades_analyzed"], 1) * 100
print(f'正确率: {correct_rate:.1f}%')
