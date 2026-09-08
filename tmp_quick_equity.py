#!/usr/bin/env python3
"""Quick equity estimate from Binance account via aws_executor.
Only checks positions likely >$1 in value.
Run on local machine, connects via SSH to web4."""
import subprocess, json, sys, urllib.request, os

# Step 1: Get account balances
r = subprocess.run(['ssh', 'web4',
    'cd /home/ubuntu/zq_web4_trading_system && python3 production/engine/aws_executor.py --check'],
    capture_output=True, text=True, timeout=30)
data = json.loads(r.stdout)
bal = data if isinstance(data, list) else data.get('balances', [])

# Collect non-zero assets
non_zero = [(b['asset'], float(b['free'])) for b in bal if float(b['free']) > 0 and b['asset'] != 'USDT']
usdt = float(next((b['free'] for b in bal if b['asset'] == 'USDT'), 0))

# Step 2: Batch get prices via SOCKS5 proxy
import urllib.request
symbols = [a+'USDT' for a, _ in non_zero]
# Binance allows up to 100 symbols per request
total_equity = usdt
print(f'USDT: ${usdt:.2f}')
print()

# Split into batches of 100
for i in range(0, len(symbols), 100):
    batch = symbols[i:i+100]
    url = 'https://api.binance.com/api/v3/ticker/price?symbols=' + urllib.parse.quote(json.dumps(batch))
    req = urllib.request.Request(url)
    req.set_proxy('socks5://127.0.0.1:1080', 'https')
    try:
        resp = urllib.request.urlopen(req, timeout=20)
        prices = json.loads(resp.read())
        price_map = {p['symbol']: float(p['price']) for p in prices}
        for asset, free in non_zero:
            asset_usdt = asset + 'USDT'
            if asset_usdt in price_map:
                val = free * price_map[asset_usdt]
                if val > 0.50:
                    print(f'{asset}: {free} x ${price_map[asset_usdt]:.4f} = ${val:.2f}')
                    total_equity += val
    except Exception as e:
        print(f'Error fetching batch {i}: {e}')

print(f'----------------------')
print(f'TOTAL EQUITY: ${total_equity:.2f}')
