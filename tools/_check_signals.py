#!/usr/bin/env python3
import json, datetime
now = datetime.datetime.now()
files = ["config/signals.json", "signals/a4_signals.json"]
for f in files:
    try:
        d = json.load(open(f))
        t = datetime.datetime.fromisoformat(d.get("scanned_at",""))
        age = (now - t).total_seconds()/3600
        print(f"{f}: scanned_at={t.strftime('%m/%d %H:%M')} age={age:.1f}h score={d.get('signal_strength','?')} count={len(d.get('signals',d.get('tokens',[])))}")
    except Exception as e:
        print(f"{f}: ERROR {e}")
