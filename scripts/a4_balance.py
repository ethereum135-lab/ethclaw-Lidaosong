#!/usr/bin/env python3
"""Quick balance valuation for A4"""
import json, hmac, hashlib, time, requests, sys

with open('/Users/lidaosong/zq_web4_trading_system/config/auth.json') as f:
    auth = json.load(f)
api_key = auth['binance']['api_key']
api_secret = auth['binance']['api_secret']

# Get account
ts = int(time.time() * 1000)
params = {'timestamp': ts, 'omitZeroBalances': 'true'}
qs = '&'.join([f'{k}={v}' for k,v in params.items()])
sig = hmac.new(api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
params['signature'] = sig
headers = {'X-MBX-APIKEY': api_key}
resp = requests.get('https://api.binance.com/api/v3/account', headers=headers, params=params, timeout=15)
if resp.status_code != 200:
    print(f"ERROR: {resp.status_code} {resp.text[:200]}")
    sys.exit(1)

data = resp.json()

# Get USDT price = 1
# For each asset, find its price via BTC pair
assets = [b['asset'] for b in data['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]
non_usdt = [a for a in assets if a != 'USDT']

# Batch price query
if non_usdt:
    symbols = [f"{a}USDT" for a in non_usdt]
    q = '["' + '","'.join(symbols) + '"]'
    pr = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbols={q}', timeout=10)
    if pr.status_code != 200:
        # Fallback: individual queries
        prices = {}
        for a in non_usdt[:5]:  # just top 5
            try:
                r = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={a}USDT', timeout=5)
                if r.status_code == 200:
                    prices[f"{a}USDT"] = float(r.json()['price'])
            except:
                pass
    else:
        prices = {s['symbol']: float(s['price']) for s in pr.json()}

    # Also get BTC price
    btcp = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', timeout=5)
    btc_price = float(btcp.json()['price']) if btcp.status_code == 200 else 0

    total = 0
    print(f"BTC: ${btc_price:.2f}")
    for b in data['balances']:
        a = b['asset']
        free = float(b['free'])
        locked = float(b['locked'])
        if a == 'USDT':
            val = free + locked
            total += val
            print(f"USDT: ${val:.2f}")
        else:
            sym = f"{a}USDT"
            p = prices.get(sym, 0)
            val = free * p
            if val > 0.10:
                total += val
                lstr = f" (+{locked} locked)" if locked > 0 else ""
                print(f"{a:12s}  {free:>12.6f}  @ ${p:<10.4f}  = ${val:<8.2f}{lstr}")

    print(f"\nTOTAL: ${total:.2f}")
else:
    usdt = float(next((b['free'] for b in data['balances'] if b['asset']=='USDT'), 0))
    print(f"USDT only: ${usdt:.2f}")
    print(f"TOTAL: ${usdt:.2f}")
