import json
import hmac
import hashlib
import time
import requests

BASE_URL = 'https://api.binance.com'
AUTH_PATH = '/Users/lidaosong/zq_web4_trading_system/config/auth.json'

with open(AUTH_PATH) as f:
    auth = json.load(f)

API_KEY = auth['binance']['api_key']
API_SECRET = auth['binance']['api_secret']

def sign(params):
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

def request(method, path, params=None):
    if params is None: params = {}
    params['timestamp'] = int(time.time() * 1000)
    params['signature'] = sign(params)
    headers = {'X-MBX-APIKEY': API_KEY}
    res = requests.request(method, BASE_URL + path, params=params, headers=headers)
    return res.json()

# 1. Volume scan (Top 50 USDT, excl BTC/ETH)
tickers = requests.get(BASE_URL + '/api/v3/ticker/24hr').json()
usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT') and 'BTC' not in t['symbol'] and 'ETH' not in t['symbol']]
usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
top_50 = [p['symbol'] for p in usdt_pairs[:50]]

# 2. Check Balance
account = request('GET', '/api/v3/account')
balance = next(float(b['free']) for b in account['balances'] if b['asset'] == 'USDT')

action_reported = False
if balance > 10:
    for s in top_50:
        k5m = requests.get(BASE_URL + '/api/v3/klines', params={'symbol': s, 'interval': '5m', 'limit': 20}).json()
        k1m = requests.get(BASE_URL + '/api/v3/klines', params={'symbol': s, 'interval': '1m', 'limit': 2}).json()
        if not isinstance(k5m, list) or len(k5m) < 20 or not isinstance(k1m, list) or len(k1m) < 2: 
            continue
        
        c5m = [float(k[4]) for k in k5m]
        c1m = [float(k[4]) for k in k1m]
        
        diffs = [c5m[i] - c5m[i-1] for i in range(1, len(c5m))]
        gains = sum([d for d in diffs if d > 0])
        losses = sum([-d for d in diffs if d < 0])
        rsi = 100 - (100 / (1 + (gains/losses))) if losses > 0 else (100 if gains > 0 else 50)
        
        drop = (c1m[0] - c1m[1]) / c1m[0]
        
        if drop > 0.01 and rsi < 35:
            price_res = requests.get(BASE_URL + '/api/v3/ticker/price', params={'symbol': s}).json()
            price = float(price_res.get('price', 0))
            if price == 0: continue
            
            ex_info = requests.get(BASE_URL + '/api/v3/exchangeInfo', params={'symbol': s}).json()
            sym_info = ex_info['symbols'][0]
            lot_filter = next(f for f in sym_info['filters'] if f['filterType'] == 'LOT_SIZE')
            step = float(lot_filter['stepSize'])
            
            # Using 95% to cover fees and price movement
            qty = (balance * 0.95) / price
            qty = float(int(qty / step) * step)
            
            order = request('POST', '/api/v3/order', {
                'symbol': s,
                'side': 'BUY',
                'type': 'MARKET',
                'quantity': f"{qty:.8f}".rstrip('0').rstrip('.')
            })
            
            if 'orderId' in order:
                print(f"ACTION: Bought {s} at {price}")
                action_reported = True
                break

if not action_reported:
    print(f"STATUS: Scanning 50 coins, no signal. USDT: {balance:.2f}")
