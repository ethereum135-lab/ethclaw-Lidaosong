#!/usr/bin/env python3
"""Analyze latest sell trade and update experience archive.
Uses the proper extract_trade_info/get_last_exit from trade_experience module."""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import json

# Use the dedicated function that handles all TRADES.md formats
result = get_last_exit()

if result and result.get('sell'):
    analysis = analyze_exit(result['sell'], result['buy'])
    entry = record_trade_experience(analysis)
    
    if entry:
        print(json.dumps({
            "status": "recorded",
            "symbol": analysis["symbol"],
            "pnl_pct": round(analysis["pnl_pct"], 2),
            "pnl_usd": round(analysis["pnl_usd"], 2),
            "exit_quality": analysis["exit_quality"],
            "lesson": analysis["lesson"],
            "exit_reason": analysis.get("exit_reason", ""),
            "trigger_signals": analysis.get("trigger_signals", []),
            "sell_price": analysis["sell_price"],
            "buy_price": analysis["buy_price"],
            "sell_time": analysis["sell_time"],
            "buy_time": analysis["buy_time"],
        }, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({
            "status": "skipped_duplicate",
            "symbol": analysis["symbol"],
            "pnl_pct": round(analysis["pnl_pct"], 2),
            "exit_quality": analysis["exit_quality"],
        }, ensure_ascii=False))
else:
    print(json.dumps({"status": "no_sell_found"}, ensure_ascii=False))

# Show current master stats
master = load_master()
stats = master.get("stats", {})
sig_perf = master.get("exit_signal_performance", {})
print("--- MASTER_STATS ---")
print("total_trades_analyzed: %d" % stats.get("total_trades_analyzed", 0))
print("correct_exits: %d" % stats.get("correct_exits", 0))
print("wrong_exits: %d" % stats.get("wrong_exits", 0))
print("neutral_exits: %d" % stats.get("too_early_exits", 0))
print("--- SIGNAL_PERFORMANCE ---")
for sig, perf in sorted(sig_perf.items()):
    rate = perf["correct"] / perf["total"] * 100 if perf["total"] > 0 else 0
    print("%s: %d次, 正确率%.0f%% (c:%d/w:%d/n:%d)" % (
        sig, perf["total"], rate, perf["correct"], perf["wrong"], perf["neutral"]))
print("--- RULES ---")
for rule in master.get("rules", [])[-5:]:
    print("  [%s] %s = %s" % (rule.get("signal","?"), rule.get("condition",""), rule.get("effectiveness","")))
