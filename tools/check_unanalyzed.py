#!/usr/bin/env python3
"""检查TRADES.md中是否有未分析的卖出"""
import sys, os, re
sys.path.insert(0, 'tools')
from trade_experience import TRADES_DIR, TRADE_LOG, extract_trade_info

with open(TRADE_LOG) as f:
    lines = f.readlines()

# Load all analyzed sell timestamps
analyzed = set()
for fname in os.listdir(TRADES_DIR):
    if fname.endswith('.json'):
        parts = fname.replace('.json','').split('_', 2)
        if fname.startswith('FET_'):
            m = re.match(r'FET_(\d{8})_(\d{6})\.json', fname)
            if m:
                ts = m.group(1)[:4]+'-'+m.group(1)[4:6]+'-'+m.group(1)[6:]+' '+m.group(2)[:2]+':'+m.group(2)[2:4]+':'+m.group(2)[4:]
                analyzed.add(ts)
        elif len(parts) == 3:
            ts = parts[0] + ' ' + parts[1].replace('-', ':')
            analyzed.add(ts)
        elif len(parts) == 2:
            ts = parts[0] + ' ' + parts[1].replace('-', ':')
            analyzed.add(ts)

print(f'已分析 {len(analyzed)} 笔独特时间戳')

unanalyzed_count = 0
for line in lines:
    stripped = line.replace('**', '').replace('\U0001f534', '').replace('\U0001f7e2', '')
    parts = [p.strip() for p in stripped.split('|')]
    if 'SELL' in parts and 'NO TRADE' not in stripped:
        info = extract_trade_info(line)
        if info and info.get('time') and info['time'] not in analyzed and info.get('time') != 'TABLE_ROW':
            if unanalyzed_count < 5:
                print(f'[未分析] {line.rstrip()[:120]}')
            unanalyzed_count += 1

if unanalyzed_count == 0:
    print('=> 所有TRADES.md中的卖出均已分析')
else:
    print(f'=> {unanalyzed_count} 笔卖出未在经验数据库中')
