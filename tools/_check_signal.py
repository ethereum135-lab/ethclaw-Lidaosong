#!/usr/bin/env python3
import json, datetime
d = json.load(open("data/signals.json"))
print(f"scanned_at: {d.get('scanned_at','?')}")
print(f"signal_strength: {d.get('signal_strength','?')}")
sigs = d.get("signals", d.get("tokens", []))
print(f"signals count: {len(sigs)}")
if len(sigs) > 0:
    s = sigs[0]
    if isinstance(s, str):
        print(f"first signal: {s}")
    else:
        print(f"first signal keys: {list(s.keys())[:5]}")
