#!/usr/bin/env python3
"""Check latest sell and find unanalyzed trades"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from trade_experience import get_last_exit, extract_trade_info, TRADES_DIR, TRADE_LOG

result = get_last_exit()
if result and result['sell']:
    sell = result['sell']
    ts = sell['time'].replace(' ', '_').replace(':', '-')
    trade_file = os.path.join(TRADES_DIR, f'{ts}_{sell["symbol"]}.json')
    exists = os.path.exists(trade_file)
    print(f'最新卖出: {sell["symbol"]} {sell["time"]} price={sell["price"]} reason={sell["reason"]}')
    print(f'交易文件已存在: {exists} -> {trade_file}')
    
    print()
    print('=== 查找未分析卖出 ===')
    with open(TRADE_LOG) as f:
        lines = f.readlines()
    
    unanalyzed = []
    for line in lines:
        stripped = line.replace('**', '').replace(chr(128309), '').replace(chr(128308), '').replace(chr(9888), '')
        parts_check = [p.strip() for p in stripped.split('|')]
        if 'SELL' in parts_check and 'NO TRADE' not in stripped:
            info = extract_trade_info(line)
            if info and info.get('symbol') and info.get('price', '').replace('.', '').replace('-', '').strip():
                ts2 = info['time'].replace(' ', '_').replace(':', '-')
                tf = os.path.join(TRADES_DIR, f'{ts2}_{info["symbol"]}.json')
                if not os.path.exists(tf):
                    unanalyzed.append(info)
    
    if unanalyzed:
        for u in unanalyzed:
            print(f'  >>> 未分析: {u["symbol"]} @ {u["time"]} price={u["price"]} reason={u["reason"]}')
    else:
        print('  所有卖出均已分析过')
else:
    print('未找到卖出记录')
