#!/usr/bin/env python3
"""Find all SEI records in TRADES.md - both BUY and SELL"""
with open('audit/TRADES.md') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'SEI' in line:
        print(f'Line {i}: {line.rstrip()[:200]}')
