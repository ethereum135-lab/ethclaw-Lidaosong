#!/usr/bin/env python3
"""Test 1: raw market sell to see real Binance error. Test 2: Convert getQuote for each dust asset."""
import sys, json, time, hashlib, hmac
sys.path.insert(0, '/home/ubuntu/zq_web4_trading_system/production/engine')
from aws_executor import load_auth
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

# Test 1: raw market SELL 1 MOVR (small, harmless test)
print("=== TEST 1: raw market sell 1 MOVR ===")
r = signed_post('/api/v3/order', {'symbol': 'MOVRUSDT', 'side': 'SELL', 'type': 'MARKET', 'quantity': '1'})
print(f"HTTP {r.status_code}: {r.text[:300]}")

# Test 2: Convert getQuote (read-only quote, no execution)
print("\n=== TEST 2: Convert getQuote ===")
for asset, qty in [('MOVR', '5.753563'), ('OPEN', '23.2584'), ('NFP', '691.52')]:
    r = signed_post('/sapi/v1/convert/getQuote', {'fromAsset': asset, 'toAsset': 'USDT', 'fromAmount': qty})
    print(f"{asset}: HTTP {r.status_code}: {r.text[:250]}")
    time.sleep(0.5)
