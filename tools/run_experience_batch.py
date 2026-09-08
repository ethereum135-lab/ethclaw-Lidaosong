#!/usr/bin/env python3
"""批量处理所有未分析的最新卖出"""
import sys
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system/tools')
from trade_experience import *
import json
import os

TRADE_LOG = os.path.join(BASE_DIR, 'audit', 'TRADES.md')

with open(TRADE_LOG) as f:
    lines = f.readlines()

# 找到所有 SELL 记录 (从底部开始找同一批次)
sells = []
for line in reversed(lines):
    stripped = line.replace('**', '').replace('🔴 ', '').replace('🔴', ' ').replace('🟢 ', '').replace('🟢', ' ').replace('⚠️', '')
    parts_check = [p.strip() for p in stripped.split('|')]
    has_sell = 'SELL' in parts_check
    if has_sell and 'NO TRADE' not in stripped:
        info = extract_trade_info(line)
        if info and info.get('symbol') and info.get('price', '').replace('.', '').replace('-', '').strip():
            sells.append(info)

# 取最新时间批次的所有卖出
if not sells:
    print('NO_SELLS: no sells in TRADES.md')
    sys.exit(0)

latest_time = max(s['time'] for s in sells)
batch_sells = [s for s in sells if s['time'] == latest_time]
print(f'Latest sell batch @ {latest_time}: {len(batch_sells)} trades')
for s in batch_sells:
    print(f'  {s["symbol"]}  qty={s["qty"]}  price={s["price"]}  reason={s["reason"][:50]}')

# 为每个卖出找对应买入并按时间排序
results = []
for sell in batch_sells:
    buys = []
    for line in lines:
        stripped = line.replace('**', '').replace('🔴 ', '').replace('🔴', ' ').replace('🟢 ', '').replace('🟢', ' ').replace('⚠️', '')
        parts_check = [p.strip() for p in stripped.split('|')]
        if 'BUY' in parts_check:
            info = extract_trade_info(line)
            if info and info['symbol'] == sell['symbol'] and info['time'] < sell['time']:
                buys.append(info)
    
    buy = max(buys, key=lambda x: x['time']) if buys else None
    
    analysis = analyze_exit(sell, buy)
    entry = record_trade_experience(analysis)
    
    if entry:
        results.append({
            'symbol': analysis['symbol'],
            'pnl_pct': f'{analysis["pnl_pct"]:+.1f}%',
            'exit_quality': analysis['exit_quality'],
            'lesson': analysis['lesson'],
            'new': True
        })
    else:
        results.append({
            'symbol': analysis['symbol'],
            'pnl_pct': f'{analysis["pnl_pct"]:+.1f}%',
            'exit_quality': analysis['exit_quality'],
            'new': False
        })

# 显示总账
print()
print('=' * 60)
for r in results:
    status = 'NEW' if r['new'] else 'SKIP'
    print(f'  [{status}] {r["symbol"]:8s} P&L:{r["pnl_pct"]:>7s}  quality:{r["exit_quality"]}')
    if r.get('lesson'):
        print(f'          lesson: {r["lesson"]}')
print('=' * 60)

# 显示总经验档案
print()
print(show_master())
