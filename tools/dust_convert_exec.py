#!/usr/bin/env python3
"""Execute Convert (flash exchange) for dust assets -> USDT. Retry NFP."""
import sys, json, time, hashlib, hmac
sys.path.insert(0, '/home/ubuntu/zq_web4_trading_system/production/engine')
from aws_executor import load_auth
import requests
from urllib.parse import urlencode

api_key, api_secret = load_auth()

def signed_post(path, params=None, timeout=15):
    p = {'timestamp': int(time.time()*1000), 'recvWindow': 10000}
    if params: p.update(params)
    q = urlencode(p)
    sig = hmac.new(api_secret.encode(), q.encode(), hashlib.sha256).hexdigest()
    p['signature'] = sig
    r = requests.post('https://api.binance.com' + path, headers={'X-MBX-APIKEY': api_key}, params=p, timeout=timeout)
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
    if r.status_code != 200: return None
    for b in r.json()['balances']:
        if b['asset'] == asset: return float(b['free']), float(b['locked'])
    return 0.0, 0.0

def convert(asset, qty, retries=3):
    for i in range(retries):
        try:
            rq = signed_post('/sapi/v1/convert/getQuote', {'fromAsset': asset, 'toAsset': 'USDT', 'fromAmount': qty})
            if rq.status_code != 200:
                print(f"{asset} getQuote fail: {rq.text[:150]}")
                time.sleep(2); continue
            q = rq.json()
            qid = q['quoteId']
            ra = signed_post('/sapi/v1/convert/acceptQuote', {'quoteId': qid}, timeout=20)
            print(f"{asset} -> {q.get('toAmount')} USDT | accept: HTTP {ra.status_code}: {ra.text[:200]}")
            return ra.status_code == 200
        except Exception as e:
            print(f"{asset} attempt {i+1} error: {str(e)[:120]}")
            time.sleep(2)
    return False

print("=== Convert dust -> USDT ===")
convert('MOVR', '5.753563')
time.sleep(1.5)
convert('OPEN', '23.2584')
time.sleep(1.5)
convert('NFP', '691.52')

time.sleep(2)
print("\n=== VERIFY ===")
for a in ['MOVR', 'OPEN', 'NFP', 'USDT', 'BNB']:
    b = get_balance(a)
    if b: print(f"{a}: free={b[0]:.8f} locked={b[1]:.8f}")
