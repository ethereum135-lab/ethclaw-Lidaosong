#!/usr/bin/env python3
"""Retry NFP convert -> USDT with backoff."""
import sys, time, json, hashlib, hmac
sys.path.insert(0, '/home/ubuntu/zq_web4_trading_system/production/engine')
from aws_executor import load_auth
import requests
from urllib.parse import urlencode

api_key, api_secret = load_auth()

def sp(path, params=None, timeout=15):
    p = {'timestamp': int(time.time()*1000), 'recvWindow': 10000}
    if params: p.update(params)
    q = urlencode(p)
    sig = hmac.new(api_secret.encode(), q.encode(), hashlib.sha256).hexdigest()
    p['signature'] = sig
    return requests.post('https://api.binance.com' + path, headers={'X-MBX-APIKEY': api_key}, params=p, timeout=timeout)

def sg(path, params=None):
    p = {'timestamp': int(time.time()*1000), 'recvWindow': 10000}
    if params: p.update(params)
    q = urlencode(p)
    sig = hmac.new(api_secret.encode(), q.encode(), hashlib.sha256).hexdigest()
    p['signature'] = sig
    return requests.get('https://api.binance.com' + path, headers={'X-MBX-APIKEY': api_key}, params=p, timeout=15)

for i in range(5):
    try:
        r = sp('/sapi/v1/convert/getQuote', {'fromAsset': 'NFP', 'toAsset': 'USDT', 'fromAmount': '691.52'})
        print(f"try{i+1}: HTTP {r.status_code}: {r.text[:150]}")
        if r.status_code == 200:
            q = r.json()
            ra = sp('/sapi/v1/convert/acceptQuote', {'quoteId': q['quoteId']}, timeout=20)
            print(f"accept: HTTP {ra.status_code}: {ra.text[:200]}")
            break
    except Exception as e:
        print(f"try{i+1} error: {str(e)[:120]}")
    time.sleep(15)

time.sleep(2)
r = sg('/api/v3/account')
for b in r.json()['balances']:
    if b['asset'] in ('NFP', 'USDT'):
        print(f"BAL {b['asset']}: free={b['free']} locked={b['locked']}")
