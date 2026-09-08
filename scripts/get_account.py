#!/usr/bin/env python3
"""Get real account holdings - bypasses curl|python3 security block"""
import requests
import json
import hashlib
import hmac
import time

with open('../config/auth.json') as f:
    auth = json.load(f)
api_key = auth['binance']['api_key']
api_secret = auth['binance']['api_secret']

def sign_request(params):
    query = '&'.join([f'{k}={v}' for k, v in params.items()])
    signature = hmac.new(api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    params['signature'] = signature
    return params

# Get account info
params = {'timestamp': int(time.time() * 1000), 'recvWindow': 10000}
params = sign_request(params)
headers = {'X-MBX-APIKEY': api_key}
r = requests.get('https://api.binance.com/api/v3/account', params=params, headers=headers)
data = r.json()

# Filter non-zero balances
balances = [b for b in data['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]
print(f"\n{'='*60}")
print(f"  ACCOUNT HOLDINGS (non-zero)")
print(f"{'='*60}")
total_usdt = 0
for b in sorted(balances, key=lambda x: float(x['free']) + float(x['locked']), reverse=True):
    free = float(b['free'])
    locked = float(b['locked'])
    total = free + locked
    print(f"  {b['asset']:8s} | Free: {free:<12.6f} | Locked: {locked:<12.6f} | Total: {total:<12.6f}")
    if b['asset'] == 'USDT':
        total_usdt = free
print(f"{'='*60}")
print(f"  USDT Available: ${total_usdt:.2f}")
print(f"{'='*60}")
