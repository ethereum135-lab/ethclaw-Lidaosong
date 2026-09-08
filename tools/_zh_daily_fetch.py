#!/usr/bin/env python3
"""ZH Daily Market Research — fetch gainers + read signals + check balance"""
import json, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- 1a. Fetch Binance top gainers ---
import subprocess, urllib.request, ssl

# Try SOCKS5 first, then direct, then binance API
data = None
for method_name, cmd in [
    ("SOCKS5", 'curl --socks5-hostname 127.0.0.1:1080 -s --max-time 30 "https://api.binance.com/api/v3/ticker/24hr"'),
    ("Direct", 'curl -s --max-time 30 "https://api.binance.com/api/v3/ticker/24hr"'),
    ("binance.com", None),  # direct urllib fallback
]:
    if method_name == "binance.com":
        try:
            ctx = ssl.create_default_context()
            resp = urllib.request.urlopen("https://api.binance.com/api/v3/ticker/24hr", timeout=30, context=ctx)
            data = json.loads(resp.read())
            print(f"[{method_name}] OK")
            break
        except Exception as e:
            print(f"[{method_name}] {e}")
            continue
    else:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=45)
        if r.returncode == 0 and r.stdout.strip():
            try:
                data = json.loads(r.stdout)
                print(f"[{method_name}] OK")
                break
            except json.JSONDecodeError:
                print(f"[{method_name}] bad JSON, len={len(r.stdout)}")
                continue
        else:
            print(f"[{method_name}] failed (rc={r.returncode})")
            continue

if data is None:
    print("ERROR: Could not fetch Binance data from any source")
    sys.exit(1)

# Filter USDT pairs with positive change
EXCLUDE = ['UP','DOWN','BULL','BEAR','BUSD','USDC','TUSD','DAI','FDUSD',
           'USDP','AEUR','EUR','GBP','AUD','BRL','TRY','ZAR','SAND',
           'IDRT','USTC','USDD']
coins = [d for d in data if d['symbol'].endswith('USDT') and
         not any(x in d['symbol'] for x in EXCLUDE) and
         float(d['priceChangePercent']) > 0]
coins.sort(key=lambda x: float(x['priceChangePercent']), reverse=True)

print('\n=== TOP 20 GAINERS (24h) ===')
print('RNK|SYMBOL    |CHG%    |VOL$        |PRICE')
for i, c in enumerate(coins[:20], 1):
    sym = c['symbol'].replace('USDT','')
    chg = float(c['priceChangePercent'])
    vol = float(c['quoteVolume'])
    price = float(c['lastPrice'])
    print(f'{i:2d}|{sym:8s}|+{chg:5.1f}%|${vol:>8,.0f}|{price:.8f}')

# Also export for later steps
gainers_list = [{'symbol': c['symbol'].replace('USDT',''),
                 'change': float(c['priceChangePercent']),
                 'volume': float(c['quoteVolume']),
                 'price': float(c['lastPrice'])} for c in coins[:20]]

out_path = os.path.join(BASE, 'data', 'zh_gainers_cache.json')
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w') as f:
    json.dump({'timestamp': '2026-06-18 08:34 BJT', 'gainers': gainers_list}, f)
print(f'\nCached to {out_path}')

# --- 1b. Check local signals ---
sig_path = os.path.join(BASE, 'data', 'signals.json')
if os.path.exists(sig_path):
    try:
        sig = json.load(open(sig_path))
        print(f'\n=== SIGNALS (signals.json) ===')
        if isinstance(sig, list):
            for s in sig[:10]:
                print(f'  {s.get("symbol","?")}: {s.get("signal","?")} conf={s.get("confidence","?")}')
        elif isinstance(sig, dict):
            for k, v in list(sig.items())[:10]:
                print(f'  {k}: {v}')
    except: print('  signals.json: parse error')
else:
    print('\n  signals.json: not found')

# --- 1c. Check TRADES.md last node for USDT total ---
trades_path = os.path.join(BASE, 'audit', 'TRADES.md')
if os.path.exists(trades_path):
    with open(trades_path) as f:
        lines = f.readlines()
    # Find last total line
    import re
    for line in reversed(lines[-50:]):  # check last 50 lines
        m = re.search(r'总资~\$?([0-9.]+)', line)
        if m:
            print(f'\n=== TOTAL ASSETS ===')
            print(f'  总资: ${float(m.group(1)):.2f}')
            break
        m2 = re.search(r'total~\$?([0-9.]+)', line)
        if m2:
            print(f'\n=== TOTAL ASSETS ===')
            print(f'  Total: ${float(m2.group(1)):.2f}')
            break

# --- 1d. Check current positions from TRADES.md ---
print(f'\n=== CURRENT POSITIONS (last 30 lines) ===')
for line in lines[-30:]:
    if 'HOLD' in line or 'WATCH' in line or 'SELL' in line or 'BUY' in line:
        print(f'  {line.strip()}')

print(f'\n=== DONE ===')
