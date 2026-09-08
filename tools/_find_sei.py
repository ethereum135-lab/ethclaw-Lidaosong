#!/usr/bin/env python3
"""Find SEI BUY records in TRADES.md"""
import sys; sys.path.insert(0, '.')
from tools.trade_experience import *
import json

with open('audit/TRADES.md') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    stripped = line.replace('**', '').replace('\U0001f534', 'SELL').replace('\U0001f7e2', 'BUY').replace('\u26a0\ufe0f', '')
    parts_check = [p.strip() for p in stripped.split('|')]
    # Check for either BUY or SELL with SEI
    for action in ['BUY', 'SELL']:
        if action in parts_check and 'SEI' in stripped and 'NO TRADE' not in stripped:
            info = extract_trade_info(line)
            if info and info.get('symbol') == 'SEI':
                print(f'Line {i}: {line.rstrip()[:100]}')
                print(f'  Parsed: {json.dumps(info, indent=2, ensure_ascii=False)}')
                print()
