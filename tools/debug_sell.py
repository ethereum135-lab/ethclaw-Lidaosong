#!/usr/bin/env python3
"""Debug: why get_last_exit finds no sell records"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

from trade_experience import extract_trade_info

with open('audit/TRADES.md') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    stripped = line.replace('**', '').replace('\U0001f534', '').replace('\U0001f7e2', '').replace('\u26a0\ufe0f', '')
    parts = [p.strip() for p in stripped.split('|')]
    has_sell = 'SELL' in parts or any(p.startswith('SELL ') for p in parts)
    if has_sell and 'NO TRADE' not in stripped:
        info = extract_trade_info(line)
        if info:
            print(f"L{i+1}: sym={info.get('symbol')} price={info.get('price')} time={info.get('time')} action={info.get('action')}")
        else:
            print(f"L{i+1}: extract_trade_info returned None. raw: {line.rstrip()[:80]}")
