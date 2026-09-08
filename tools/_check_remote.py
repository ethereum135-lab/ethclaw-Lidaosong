#!/usr/bin/env python3
"""Check signal freshness and system state on remote server."""
import json, datetime, os, subprocess

now = datetime.datetime.now()
print(f"=== REMOTE CHECK @ {now.strftime('%Y-%m-%d %H:%M')} BJT ===")

# Signal freshness
for f in ["data/signals.json", "data/signals/a4_signals.json", "data/signals/a4_signal_latest.json"]:
    try:
        d = json.load(open(f))
        t = datetime.datetime.fromisoformat(d.get("scanned_at",""))
        age = (now - t).total_seconds()/3600
        sigs = d.get("signals", d.get("tokens", []))
        score = d.get("signal_strength", "?")
        print(f"SIGNAL|{f}: scanned_at={t.strftime('%m/%d %H:%M')} age={age:.1f}h score={score} count={len(sigs)}")
    except Exception as e:
        print(f"SIGNAL|{f}: ERROR {e}")

# Check if cron for A4 is running
try:
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
    a4_lines = [l for l in r.stdout.split('\n') if 'a4' in l.lower() or 'A4' in l]
    print(f"CRON|A4 lines: {len(a4_lines)}")
    for l in a4_lines[:3]:
        print(f"CRON|  {l}")
except Exception as e:
    print(f"CRON|ERROR: {e}")

# Last TRADES entry
try:
    with open("data/TRADES.md") as f:
        last = f.readlines()[-5:]
    print(f"TRADES|last 5 lines: {[l.strip() for l in last]}")
except Exception as e:
    print(f"TRADES|ERROR: {e}")

# Binance connectivity
r = subprocess.run(["curl", "--socks5-hostname", "127.0.0.1:1080", "-s", "--connect-timeout", "5", "https://api.binance.com/api/v3/ping"], capture_output=True, text=True, timeout=10)
print(f"BINANCE|curl exit={r.returncode} stdout={r.stdout.strip()[:50]} stderr={r.stderr.strip()[:100]}")

# Account equity
try:
    with open("data/TRADES.md") as f:
        content = f.read()
    import re
    equity_match = re.search(r'\*\*(~\$[\d.]+)\*\*', content.split('\n')[-20])
    if equity_match:
        print(f"EQUITY|Last known: {equity_match.group(1)}")
except Exception as e:
    print(f"EQUITY|ERROR: {e}")
