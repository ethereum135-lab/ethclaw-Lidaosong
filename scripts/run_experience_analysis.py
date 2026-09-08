#!/usr/bin/env python3
"""分析最新卖出交易并记录经验"""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import json

# 读取交易记录找最新的卖出
with open('audit/TRADES.md') as f:
    lines = f.readlines()

# 找最新一笔卖出（跳过持仓评估记录行）
recent_sell = None
for line in reversed(lines):
    if ' SELL ' in line and 'NO TRADE' not in line and line.strip().startswith('| 20'):
        recent_sell = line
        break

if not recent_sell:
    print('[SILENT]')
    sys.exit(0)

parts = [p.strip() for p in recent_sell.split('|')]

if len(parts) < 7:
    print(f'行格式异常: {len(parts)}列')
    sys.exit(1)

# 找对应的买入: same symbol, earlier time
symbol = parts[3]
sell_time = parts[1]
buy_line = None
for line in lines:
    p = [x.strip() for x in line.split('|')]
    if len(p) >= 7 and ' BUY ' in line and p[3] == symbol and p[1] < sell_time:
        buy_line = line
        break

if not buy_line:
    print(f'未找到 {symbol} 的买入记录')
    sys.exit(0)

def info_parser(raw):
    p = [x.strip() for x in raw.split('|')]
    return {
        'symbol': p[3],
        'time': p[1],
        'price': p[5].replace('$', ''),
        'qty': p[4],
        'reason': p[6] if len(p) > 6 else ''
    }

sell_info = info_parser(recent_sell)
buy_info = info_parser(buy_line)

analysis = analyze_exit(sell_info, buy_info)
result = record_trade_experience(analysis)

# 还要把P&L更新到总档案的stats
master = load_master()
master['stats']['total_pnl_usd'] = master['stats'].get('total_pnl_usd', 0) + analysis.get('pnl_usd', 0)
win_count = master['stats'].get('correct_exits', 0)
total_count = master['stats'].get('total_trades_analyzed', 0)
if total_count > 0:
    master['stats']['win_rate'] = round(win_count / total_count * 100, 1)
master['last_updated'] = datetime.now().isoformat()[:10]
save_master(master)

if result is None:
    print(f'已存在(跳过重复): {symbol} P&L:{analysis["pnl_pct"]:+.1f}% 质量:{analysis["exit_quality"]}')
else:
    print(f'经验已记录: {symbol} P&L:{analysis["pnl_pct"]:+.1f}% 质量:{analysis["exit_quality"]}')

print(f'  信号: {analysis["trigger_signals"]}')
print(f'  教训: {analysis["lesson"]}')
print(f'  总交易数: {total_count} | 胜率: {master["stats"].get("win_rate", 0)}%')
print(f'  总PnL: ${master["stats"].get("total_pnl_usd", 0):.2f}')
