#!/usr/bin/env python3
import json, datetime
d = json.load(open("data/signals.json"))
r = d.get("results", [])
print(f"scanned_at: {d.get('scanned_at','?')}")
print(f"total_scanned: {d.get('total_scanned',0)}")
levels = {}
for item in r:
    lvl = item.get("level","?")
    levels[lvl] = levels.get(lvl, 0) + 1
print(f"Level distribution: {levels}")
# Show top STRONG signals
strong = [x for x in r if x.get("level") == "STRONG"]
strong.sort(key=lambda x: x.get("total_score",0), reverse=True)
print(f"\nTop STRONG (top 10):")
for s in strong[:10]:
    print(f"  {s['symbol']:12s} score={s['total_score']:3d} price=${s['price']:<10} gain_24h={s.get('gain_24h',0):+.2f}%")

# Also show SIGNAL level
signal = [x for x in r if x.get("level") == "SIGNAL"]
print(f"\nSIGNAL count: {len(signal)}")
for s in signal[:5]:
    print(f"  {s['symbol']:12s} score={s['total_score']:3d} price=${s['price']:<10} gain_24h={s.get('gain_24h',0):+.2f}%")

# Show buy_signals summary  
print(f"\nsummary: {d.get('summary','')}")
