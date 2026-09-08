#!/usr/bin/env python3
import json
d = json.load(open("data/signals.json"))
print(f"scanned_at: {d.get('scanned_at','?')}")
print(f"signal_strength: {d.get('signal_strength','?')}")
print(f"Top-level keys: {list(d.keys())}")
for k in ['signals', 'tokens', 'candidates', 'buy_signals', 'results', 'coins']:
    v = d.get(k, [])
    if isinstance(v, list):
        print(f"  {k}: list of {len(v)} items")
        if len(v) > 0:
            print(f"    first: {json.dumps(v[0], indent=2)[:200]}")
    elif isinstance(v, dict):
        print(f"  {k}: dict with {len(v)} keys")
