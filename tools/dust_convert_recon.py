#!/usr/bin/env python3
"""Step 1: Read-only recon - check dust balances & SAPI permission before converting."""
import sys, json, time, hashlib, hmac
sys.path.insert(0, '/home/ubuntu/zq_web4_trading_system/production/engine')
from aws_executor import load_auth
import requests
from urllib.parse import urlencode

api_key, api_secret = load_auth()

def signed_get(path, params=None):
    p = {'timestamp': int(time.time()*1000), 'recvWindow': 10000}
    if params: p.update(params)
    q = urlencode(p)
    sig = hmac.new(api_secret.encode(), q.encode(), hashlib.sha256).hexdigest()
    p['signature'] = sig
    r = requests.get('https://api.binance.com' + path, headers={'X-MBX-APIKEY': api_key}, params=p, timeout=10)
    return r

# 1. Balances
r = signed_get('/api/v3/account')
if r.status_code != 200:
    print(f"ACCOUNT FAIL {r.status_code}: {r.text[:200]}"); sys.exit(1)
data = r.json()
targets = ['MOVR', 'OPEN', 'NFP', 'USDT', 'BNB']
for b in data['balances']:
    if b['asset'] in targets and (float(b['free']) > 0 or float(b['locked']) > 0):
        print(f"BAL {b['asset']}: free={b['free']} locked={b['locked']}")

# 2. Permission probe: dribblet (read-only dust history)
r2 = signed_get('/sapi/v1/asset/dribblet', {'startTime': int(time.time()*1000) - 86400000})
print(f"\nDRIBBLET(perm probe) HTTP {r2.status_code}: {r2.text[:300]}")

# 3. Prices for reference
rp = requests.get('https://api.binance.com/api/v3/ticker/price', timeout=10)
prices = {p['symbol']: float(p['price']) for p in rp.json()}
for a in ['MOVR', 'OPEN', 'NFP']:
    print(f"PRICE {a}USDT: {prices.get(a+'USDT')}")
