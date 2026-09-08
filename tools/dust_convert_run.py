#!/usr/bin/env python3
"""Convert dust (MOVR/OPEN/NFP) to BNB via official Binance Convert-Dust API, then sell BNB to USDT."""
import sys, json, time, hashlib, hmac
sys.path.insert(0, '/home/ubuntu/zq_web4_trading_system/production/engine')
from aws_executor import load_auth, sell_market
import requests
from urllib.parse import urlencode

api_key, api_secret = load_auth()

def signed_post(path, params=None):
    p = {'timestamp': int(time.time()*1000), 'recvWindow': 10000}
    if params: p.update(params)
    q = urlencode(p)
    sig = hmac.new(api_secret.encode(), q.encode(), hashlib.sha256).hexdigest()
    p['signature'] = sig
    r = requests.post('https://api.binance.com' + path, headers={'X-MBX-APIKEY': api_key}, params=p, timeout=15)
    return r

def signed_get(path, params=None):
    p = {'timestamp': int(time.time()*1000), 'recvWindow': 10000}
    if params: p.update(params)
    q = urlencode(p)
    sig = hmac.new(api_secret.encode(), q.encode(), hashlib.sha256).hexdigest()
    p['signature'] = sig
    r = requests.get('https://api.binance.com' + path, headers={'X-MBX-APIKEY': api_key}, params=p, timeout=15)
    return r

def get_balance(asset):
    r = signed_get('/api/v3/account')
    if r.status_code != 200:
        print(f"ACCOUNT FAIL {r.status_code}: {r.text[:150]}"); return None
    for b in r.json()['balances']:
        if b['asset'] == asset:
            return float(b['free']), float(b['locked'])
    return 0.0, 0.0

# Step 1: Convert dust -> BNB
print("=== STEP 1: Convert Dust -> BNB ===")
r = signed_post('/sapi/v1/asset/dust', {'asset': 'MOVR,OPEN,NFP'})
print(f"HTTP {r.status_code}: {r.text[:600]}")

time.sleep(2)

# Step 2: Verify balances
print("\n=== STEP 2: Verify ===")
for a in ['MOVR', 'OPEN', 'NFP', 'BNB', 'USDT']:
    b = get_balance(a)
    if b: print(f"{a}: free={b[0]:.8f} locked={b[1]:.8f}")

# Step 3: Sell new BNB (keep 0.005 for fees)
print("\n=== STEP 3: Sell BNB -> USDT ===")
bnb_free, _ = get_balance('BNB')
if bnb_free > 0.006:
    qty = round(bnb_free - 0.005, 6)
    print(f"Selling {qty} BNB (keeping 0.005)...")
    res = sell_market(api_key, api_secret, 'BNB', qty)
    print(f"Result: {json.dumps(res, ensure_ascii=False)[:300]}")
else:
    print(f"BNB too small ({bnb_free:.8f}), skip selling")

time.sleep(2)
print("\n=== FINAL ===")
for a in ['BNB', 'USDT']:
    b = get_balance(a)
    if b: print(f"{a}: free={b[0]:.8f} locked={b[1]:.8f}")
