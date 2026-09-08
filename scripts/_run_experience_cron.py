"""Analyze latest sell trade and update experience archive."""
import sys
sys.path.insert(0, '/Users/lidaosong/zq_web4_trading_system/tools')
import json
from trade_experience import get_last_exit, load_master

# 1) Master archive status
master = load_master()
print("=== MASTER EXPERIENCE ARCHIVE ===")
print(f"Last updated: {master.get('last_updated', '?')}")
stats = master.get('stats', {})
print(f"Total analyzed: {stats.get('total_trades_analyzed', 0)}")
print(f"  Correct exits: {stats.get('correct_exits', 0)}")
print(f"  Wrong exits:   {stats.get('wrong_exits', 0)}")
print(f"  Too early:     {stats.get('too_early_exits', 0)}")

# 2) Latest sell
result = get_last_exit()
if result:
    s = result['sell']
    b = result['buy']
    print(f"\n=== LATEST SELL: {s['symbol']} @ {s['time']} ===")
    print(f"  Sell price: ${s['price']} | Qty: {s['qty']} | Reason: {s.get('reason','')}")
    if b:
        print(f"  Match BUY: {b['time']} @ ${b['price']}")
    else:
        print(f"  WARNING: No BUY record found for {s['symbol']} in TRADES.md")
        # Check existing trade file as fallback
        ts = s['time'].replace(' ', '_').replace(':', '-')
        trade_file = f"/Users/lidaosong/zq_web4_trading_system/data/experience/trades/{ts}_{s['symbol']}.json"
        import os
        if os.path.exists(trade_file):
            with open(trade_file) as f:
                td = json.load(f)
            a = td['analysis']
            print(f"  Existing trade file found: {trade_file.split('/')[-1]}")
            print(f"  P&L: {a['pnl_pct']:+.1f}% | Quality: {a['exit_quality']} | Lesson: {a['lesson']}")
        else:
            print(f"  No trade file found either. LAYER buy was never recorded.")
else:
    print("No sells found in TRADES.md")

# 3) Show recent trades folder
import glob
trades = sorted(glob.glob("/Users/lidaosong/zq_web4_trading_system/data/experience/trades/*.json"))
print(f"\n=== RECENT TRADE FILES ===")
for f in trades[-5:]:
    with open(f) as fh:
        d = json.load(fh)
    a = d.get('analysis', {})
    print(f"  {f.split('/')[-1]}: P&L {a.get('pnl_pct',0):+.1f}% | {a.get('exit_quality','?')}")
print(f"\nTotal trade files: {len(trades)}")
