#!/usr/bin/env python3
"""Compute total equity from Binance and write to total_asset.json.
Run on local machine, connects via SSH to web4."""
import json, subprocess, os, sys
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

# Get account data via server
r = subprocess.run(['ssh', 'web4',
    'cd /home/ubuntu/zq_web4_trading_system && python3 production/engine/aws_executor.py --check'],
    capture_output=True, text=True, timeout=30)
data = json.loads(r.stdout)
bal = data if isinstance(data, list) else data.get('balances', [])

# Compute total equity using Binance public prices via SOCKS5
import urllib.request
non_zero = [(b['asset'], float(b['free'])) for b in bal if float(b['free']) > 0 and b['asset'] not in ['USDT','USDC']]
usdt = float(next((b['free'] for b in bal if b['asset'] == 'USDT'), 0))
usdc = float(next((b['free'] for b in bal if b['asset'] == 'USDC'), 0))
total_usd = usdt + usdc

# Batch price lookup
symbols = [a+'USDT' for a,_ in non_zero]
total_pos_val = 0.0
for i in range(0, len(symbols), 50):
    batch = symbols[i:i+50]
    url = 'https://api.binance.com/api/v3/ticker/price?symbols=' + json.dumps(batch)
    req = urllib.request.Request(url)
    # No proxy needed if running from local with SOCKS5 already active
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        prices = json.loads(resp.read())
        pm = {p['symbol']: float(p['price']) for p in prices}
        for asset, free in non_zero:
            if asset+'USDT' in pm:
                val = free * pm[asset+'USDT']
                if val > 0.50:
                    total_pos_val += val
    except:
        pass

total_equity = round(total_usd + total_pos_val, 2)
now_bjt = datetime.now(BJT).strftime('%Y-%m-%d %H:%M')

# Read old total_asset
old_total = None
old_path = '/Users/lidaosong/zq_web4_trading_system/data/total_asset.json'
if os.path.exists(old_path):
    with open(old_path) as f:
        old = json.load(f)
    old_total = old.get('total')

change_pct = 0
if old_total and old_total > 0:
    change_pct = round((total_equity - old_total) / old_total * 100, 2)

# Write new
new = {
    'total': total_equity,
    'date': now_bjt.split()[0],
    'time': now_bjt.split()[1],
    'change_pct': f'{change_pct:+.2f}%',
    'note': f'Live Binance scan @ {now_bjt} BJT'
}
with open(old_path, 'w') as f:
    json.dump(new, f, indent=2)

print(f'EQUITY:${total_equity:.2f} CHANGE:{change_pct:+.2f}% USDT:${usdt:.2f} POSITIONS:${total_pos_val:.2f}')
print(f'Updated: {old_path}')
