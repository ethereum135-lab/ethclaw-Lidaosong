#!/usr/bin/env python3
"""Debug: find latest sell and its corresponding buy"""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import json

result = get_last_exit()
if result:
    print('=== SELL ===')
    print(json.dumps(result['sell'], indent=2, ensure_ascii=False))
    if result['buy']:
        print('=== BUY ===')
        print(json.dumps(result['buy'], indent=2, ensure_ascii=False))
        analysis = analyze_exit(result['sell'], result['buy'])
        print('=== ANALYSIS ===')
        print(json.dumps(analysis, indent=2, ensure_ascii=False, default=str))
        entry = record_trade_experience(analysis)
        if entry is None:
            print('STATUS: TRADE ALREADY ANALYZED (skipped)')
        else:
            print('STATUS: RECORDED')
    else:
        print('NO_BUY_FOUND: no matching buy record found')
        # Show last sells for debugging
        with open('audit/TRADES.md') as f:
            lines = f.readlines()
        last_sells = []
        for i, line in enumerate(lines):
            stripped = line.replace('**', '').replace('\U0001f534 ', '').replace('\U0001f534', ' ').replace('\U0001f7e2 ', '').replace('\U0001f7e2', ' ').replace('\u26a0\ufe0f', '')
            parts_check = [p.strip() for p in stripped.split('|')]
            has_sell = 'SELL' in parts_check or any(p.startswith('SELL ') for p in parts_check)
            if has_sell and 'NO TRADE' not in stripped:
                info = extract_trade_info(line)
                if info:
                    last_sells.append((i+1, info))
        print(f'\nTotal sells found: {len(last_sells)}')
        for ln, s in last_sells[-3:]:
            print(f'  Line {ln}: time="{s["time"]}" sym={s["symbol"]} price={s["price"]} table={s.get("is_table_format",False)}')
else:
    print('get_last_exit() returned None')
