#!/usr/bin/env python3
"""Run trade experience analysis on the latest sell and update MASTER_EXPERIENCE.json"""
import sys; sys.path.insert(0, 'tools')
from trade_experience import *
import json

result = get_last_exit()
if not result or not result['sell']:
    print("NO_SELL")
    sys.exit(0)

sell = result['sell']
buy = result.get('buy')
analysis = analyze_exit(sell, buy)
entry = record_trade_experience(analysis)

if entry:
    print(json.dumps(analysis, indent=2, ensure_ascii=False))
else:
    print("DUPLICATE")
