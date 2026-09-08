#!/usr/bin/env python3
"""Check latest pipe-format SELL rows in TRADES.md"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(BASE, 'audit', 'TRADES.md')) as f:
    content = f.read()

lines = content.split('\n')
pipe_sells = []
for i, line in enumerate(lines):
    # Remove markdown bold/color markers that interfere with parsing
    stripped = line.replace('*', '').replace('\U0001f534', '').replace('\U0001f7e2', '')
    stripped = stripped.replace('\u26a0', '').replace('\ufe0f', '')
    parts = stripped.split('|')
    has_sell = False
    for p in parts:
        if p.strip().upper() == 'SELL' or p.strip().upper().startswith('SELL '):
            has_sell = True
            break
    if has_sell and 'NO TRADE' not in stripped:
        clean_parts = [p.strip() for p in parts if p.strip()]
        if len(clean_parts) >= 3:
            pipe_sells.append((i + 1, line.strip()[:140]))

print('最新pipe格式SELL行 (最后5条):')
for ln, c in pipe_sells[-5:]:
    print(f'  行{ln}: {c}')

print(f'\n总pipe SELL行数: {len(pipe_sells)}')

# Check today (June 28)
today_sells = [(ln, c) for ln, c in pipe_sells if '06-28' in c]
print(f'今天(06-28) SELL行: {len(today_sells)}')
for ln, c in today_sells:
    print(f'  行{ln}: {c}')
