#!/usr/bin/env python3
"""Analyze latest sell trade and record experience"""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import json

# Get and record
result = get_last_exit()
if result and result['buy']:
    analysis = analyze_exit(result['sell'], result['buy'])
    entry = record_trade_experience(analysis)
    if entry is None:
        print('SKIP: trade already analyzed (duplicate)')
    else:
        print('OK: recorded')
    print()
    print(show_master())
else:
    print('NO_TRADE: no valid sell found')
