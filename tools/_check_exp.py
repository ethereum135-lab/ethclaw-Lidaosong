#!/usr/bin/env python3
"""Check experience data and master file."""
import sys; sys.path.insert(0, 'tools')
import os, json

# Check master
master_path = 'data/experience/MASTER_EXPERIENCE.json'
if os.path.exists(master_path):
    with open(master_path) as f:
        master = json.load(f)
    print("=== MASTER_EXPERIENCE.json ===")
    print(json.dumps(master, indent=2, ensure_ascii=False)[:3000])
else:
    print("MASTER_EXPERIENCE.json not found")

# Check trades dir
trades_dir = 'data/experience/trades'
if os.path.isdir(trades_dir):
    files = sorted(os.listdir(trades_dir))
    print(f"\n=== trades dir: {len(files)} files ===")
    for f in files[-10:]:
        print(f"  {f}")
        fp = os.path.join(trades_dir, f)
        with open(fp) as fh:
            data = json.load(fh)
        a = data.get('analysis', {})
        print(f"    sym={a.get('symbol')} quality={a.get('exit_quality')} pnl={a.get('pnl_pct','?')}% signals={a.get('trigger_signals',[])}")
else:
    print("\ntrades dir not found")
