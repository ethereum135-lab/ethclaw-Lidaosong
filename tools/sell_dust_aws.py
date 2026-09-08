#!/usr/bin/env python3
"""Sell ALL dust positions on Binance to free USDT"""
import sys, json, os, time
sys.path.insert(0, '/home/ubuntu/zq_web4_trading_system/production/engine')
from aws_executor import sell_market, load_auth
import requests

api_key, api_secret = load_auth()

# Get all dust balances via simple signed call
import hashlib, hmac
from urllib.parse import urlencode

params = {'timestamp': int(time.time()*1000), 'recvWindow': 10000}
query = urlencode(params)
sig = hmac.new(api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
params['signature'] = sig

r = requests.get('https://api.binance.com/api/v3/account',
    headers={'X-MBX-APIKEY': api_key},
    params=params, timeout=10)
data = r.json()

balances_raw = data.get('balances', [])
balances = {b['asset']: float(b['free']) for b in balances_raw if float(b['free']) > 0}

# Get prices
rp = requests.get('https://api.binance.com/api/v3/ticker/price', timeout=10)
prices = {p['symbol']: float(p['price']) for p in rp.json()}

# Skip: stablecoins, earn products, small <$3  
skip_assets = {'USDT', 'USDC', 'BUSD', 'DAI', 'FDUSD', 'TUSD',
    'BNB', 'ETH', 'BTC', 'SOL', 'XRP', 'ADA', 'DOGE', 'TRX',
    'LDBNB', 'LDETH', 'LDSOL', 'LDLUNA', 'LDCRV', 'LDAVAX',
    'LDSHIB2', 'LDSUI', 'LDPEPE', 'LDSEI', 'LDXAI', 'LDBERA',
    'LDSXT', 'LDXPL', 'LDZEC'}

dust_to_sell = []
total_value = 0.0

for asset, qty in sorted(balances.items()):
    if asset in skip_assets:
        continue
    pair = f'{asset}USDT'
    price = prices.get(pair, 0)
    value = price * qty
    if value >= 5:
        dust_to_sell.append((asset, qty, value, price))
        total_value += value

print(f"Dust to sell: {len(dust_to_sell)} positions, total value ≈ ${total_value:.2f}")
print()

for idx, (asset, qty, value, price) in enumerate(dust_to_sell):
    print(f"[{idx+1}/{len(dust_to_sell)}] SELL {asset}: {qty:.6f} × ${price:.4f} ≈ ${value:.2f}")
    try:
        result = sell_market(api_key, api_secret, asset, qty)
        result_str = json.dumps(result)[:200]
        if 'orderId' in result_str:
            print(f"  -> OK (orderId: {result.get('orderId', '?')})")
        else:
            print(f"  -> {result_str}")
    except Exception as e:
        print(f"  -> FAILED: {str(e)[:120]}")
    time.sleep(0.3)

print(f"\n=== Done ===")
print(f"Sold {len(dust_to_sell)} positions, freed ~${total_value:.2f} USDT")
