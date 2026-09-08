#!/usr/bin/env python3
"""
analyze-latest-sell.py — Cron-safe experience analysis wrapper
==============================================================

Call this from cron or terminal to analyze the latest sell trade
and update the MASTER_EXPERIENCE.json archive. Handles:
  - Finding latest sell + matching buy from TRADES.md
  - P&L calculation and exit quality classification
  - Signal performance tracking (E1-E6)
  - Automatic dedup (skips if already analyzed)
  - No emoji/Unicode in output (tirith-safe)

Usage (from project root):
  python3 tools/analyze-latest-sell.py

Output format (machine-parseable):
  RECORDED: SYMBOL | P&L:+X.X% | quality:correct/neutral/wrong | signals:['E2']
  SKIPPED: SYMBOL already analyzed
  NO_SELL: No complete sell+buy pair found

Croṇ-safe guarantees:
  - No f-strings with emoji (uses .format())
  - No inline python3 -c (runs as .py file)
  - All paths relative to project root via __file__ detection
"""

import sys
import os
import json

# Auto-detect project root (this script lives in tools/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)  # tools/
sys.path.insert(0, PROJECT_ROOT)

from trade_experience import get_last_exit, analyze_exit, record_trade_experience


def main():
    result = get_last_exit()
    if not result or not result.get('sell') or not result.get('buy'):
        print("NO_SELL: No complete sell+buy pair found")
        return

    sell = result['sell']
    buy = result['buy']
    analysis = analyze_exit(sell, buy)
    entry = record_trade_experience(analysis)

    if entry:
        msg = "RECORDED: {sym} | P&L:{pnl:+.1f}% | quality:{qty} | signals:{sig}"
        print(msg.format(
            sym=analysis['symbol'],
            pnl=analysis['pnl_pct'],
            qty=analysis['exit_quality'],
            sig=analysis['trigger_signals']
        ))
    else:
        print("SKIPPED: {sym} already analyzed".format(
            sym=analysis['symbol']
        ))


if __name__ == '__main__':
    main()
