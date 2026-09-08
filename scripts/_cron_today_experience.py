#!/usr/bin/env python3
"""Run trade experience analysis on latest sell — cron version."""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import json

result = get_last_exit()
if result and result['sell']:
    analysis = analyze_exit(result['sell'], result['buy'])
    entry = record_trade_experience(analysis)
    if entry:
        print(f'NEW_EXPERIENCE: {analysis["symbol"]} P&L:{analysis["pnl_pct"]:+.1f}% quality:{analysis["exit_quality"]}')
        print(f'  buy_price:{analysis["buy_price"]:.4f} sell_price:{analysis["sell_price"]:.4f}')
        print(f'  signals:{analysis["trigger_signals"]}')
        print(f'  lesson:{analysis["lesson"]}')
    else:
        print(f'ALREADY_ANALYZED: {analysis["symbol"]} P&L:{analysis["pnl_pct"]:+.1f}% quality:{analysis["exit_quality"]}')
    # Show current master stats
    master = load_master()
    print()
    print('=== MASTER_EXPERIENCE Stats ===')
    print(f'Total analyzed: {master["stats"].get("total_trades_analyzed", 0)}')
    print(f'Correct: {master["stats"].get("correct_exits", 0)}')
    print(f'Wrong: {master["stats"].get("wrong_exits", 0)}')
    print(f'Neutral: {master["stats"].get("too_early_exits", 0)}')
else:
    print('NO_SELL_THIS_ROUND')
