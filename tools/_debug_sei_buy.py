#!/usr/bin/env python3
import sys; sys.path.insert(0, '.')
from tools.trade_experience import *

with open('audit/TRADES.md') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    # Remove bold markers and colored circle emojis
    stripped = line.replace('**', '')
    for emoji in ['', '', '⚠️']:
        stripped = stripped.replace(emoji, '').replace(emoji+' ', '')
    parts_check = [p.strip() for p in stripped.split('|')]
    if 'BUY' in parts_check and 'SEI' in stripped and 'NO TRADE' not in stripped:
        info = extract_trade_info(line)
        print(f'Line {i}: {line.rstrip()[:120]}')
        print(f'  Parsed: {info}')
        print()
