#!/usr/bin/env python3
"""验证get_last_exit修复 + 批量分析遗漏卖出"""
import sys, os, json
sys.path.insert(0, 'tools')
from trade_experience import get_last_exit, extract_trade_info, load_master

# 验证修复后能正确找到最近卖出
exit_data = get_last_exit()
if exit_data and exit_data['sell']:
    sell = exit_data['sell']
    buy = exit_data['buy']
    print(f'最新卖出: {sell["symbol"]} @ {sell["time"]}')
    print(f'  价格: {sell["price"]} | 数量: {sell["qty"]}')
    print(f'  原因: {sell["reason"]}')
    if buy:
        print(f'  买入: {buy["time"]} @ {buy["price"]}')
    else:
        print(f'  买入: 未找到')
else:
    print('未找到卖出交易')

# 浏览所有含SELL的行，标记紧凑格式的
with open('audit/TRADES.md', encoding='utf-8') as f:
    lines = f.readlines()

print('\n=== 检查紧凑格式SELL（可能被旧版遗漏）===')
count = 0
for line in lines:
    stripped = line.replace('\ufe0f', '').replace('\u200d', '').replace('**', '').strip()
    if '|SELL|' in stripped and '| SELL |' not in stripped and 'NO TRADE' not in stripped:
        info = extract_trade_info(line)
        if info and info.get('symbol'):
            ts = info['time'].replace(' ', '_').replace(':', '-')
            trade_file = os.path.join('data', 'experience', 'trades', f"{ts}_{info['symbol']}.json")
            status = '\u5df2\u5206\u6790' if os.path.exists(trade_file) else '\u672a\u5206\u6790'
            print(f'  {info["symbol"]} @ {info["time"]} | {info["price"]} | {status}')
            count += 1

print(f'共{count}笔紧凑格式SELL')

# 显示总档案
master = load_master()
stats = master.get('stats', {})
perf = master.get('exit_signal_performance', {})
print(f'\n=== 总经验档案 (v{master.get("version", "?")}) ===')
print(f'总分析交易: {stats.get("total_trades_analyzed", 0)}')
print(f'正确退出:    {stats.get("correct_exits", 0)}')
print(f'错误退出:    {stats.get("wrong_exits", 0)}')
print(f'过早退出:    {stats.get("too_early_exits", 0)}')
print(f'信号表现:')
for sig, data in sorted(perf.items()):
    correct_rate = data['correct']/data['total']*100 if data['total'] > 0 else 0
    print(f'  {sig}: 总{data["total"]} 正确{data["correct"]}({correct_rate:.0f}%) 错误{data["wrong"]} 中立{data["neutral"]}')
