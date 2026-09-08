#!/usr/bin/env python3
"""检查TRADES.md中有无未分析的SELL记录"""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import os, json

# 所有已分析交易的symbol+time集合
analyzed = set()
for f in os.listdir(TRADES_DIR):
    if not f.endswith('.json'):
        continue
    fpath = os.path.join(TRADES_DIR, f)
    with open(fpath) as fh:
        entry = json.load(fh)
        a = entry['analysis']
        analyzed.add((a['symbol'], a['sell_time']))

print(f'已分析交易数: {len(analyzed)}')

# 在TRADES.md中找pipe-delimited SELL
with open(TRADE_LOG) as f:
    lines = f.readlines()

unanalyzed = []
for line in lines:
    emoji_free = line.replace('**', '').replace('🔴 ', '').replace('🔴', ' ')
    emoji_free = emoji_free.replace('🟢 ', '').replace('🟢', ' ').replace('⚠️', '')
    parts = [p.strip() for p in emoji_free.split('|')]
    if len(parts) >= 6 and 'SELL' in parts and 'NO TRADE' not in emoji_free:
        info = extract_trade_info(line)
        if info and info.get('symbol') and info.get('price'):
            key = (info['symbol'], info['time'])
            if key not in analyzed and not info.get('is_table_format', False):
                bad_price = info['price'].replace('$','').strip() in ('0.0000', '0', '0.0')
                if not bad_price:
                    unanalyzed.append(info)

if unanalyzed:
    print(f'\n未分析SELL记录 ({len(unanalyzed)}):')
    for u in unanalyzed:
        msg = u['reason'][:60] if u.get('reason') else ''
        print(f'  {u["time"]} | {u["symbol"]:8s} | price={u["price"]} | {msg}')
else:
    print('\n所有SELL记录均已分析 ✅')
