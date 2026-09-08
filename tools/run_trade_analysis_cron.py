#!/usr/bin/env python3
"""Run trade analysis on the latest sell trade and update experience archive."""
import sys
sys.path.insert(0, 'tools')
from trade_experience import get_last_exit, analyze_exit, record_trade_experience, show_master
import json

# Use get_last_exit to find the latest sell
result = get_last_exit()
if result:
    sell = result['sell']
    buy = result['buy']
    print('=== Latest SELL Found ===')
    print(f'Symbol: {sell["symbol"]}')
    print(f'Sell Time: {sell["time"]}')
    print(f'Sell Price: {sell["price"]}')
    print(f'Sell Qty: {sell["qty"]}')
    print(f'Sell Reason: {sell["reason"]}')
    print()
    if buy:
        print(f'Buy Time: {buy["time"]}')
        print(f'Buy Price: {buy["price"]}')
        print(f'Buy Qty: {buy["qty"]}')
        print()
    
    # Analyze
    analysis = analyze_exit(sell, buy)
    print('=== Analysis Result ===')
    for k, v in analysis.items():
        if isinstance(v, float):
            print(f'  {k}: {v:.4f}')
        else:
            print(f'  {k}: {v}')
    
    # Record
    entry = record_trade_experience(analysis)
    if entry:
        print('\n[OK] New experience recorded')
    else:
        print('\n[SKIP] This trade already analyzed')
    
    # Show updated master archive
    print('\n=== Updated Master Experience Archive ===')
    print(show_master())
else:
    print('No valid sell trades found')

# Show current master anyway
print('\n=== Current Master Experience Archive ===')
print(show_master())
