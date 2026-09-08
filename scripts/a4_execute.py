#!/usr/bin/env python3
"""A4 Blade - execute trades directly via Binance API"""
import json, hmac, hashlib, time, requests, sys, math

BINANCE_API = 'https://api.binance.com'
AUTH_PATH = '/Users/lidaosong/zq_web4_trading_system/config/auth.json'

with open(AUTH_PATH) as f:
    auth = json.load(f)
API_KEY = auth['binance']['api_key']
API_SECRET = auth['binance']['api_secret']

def signed_request(method, endpoint, params=None):
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    qs = '&'.join([f'{k}={v}' for k,v in sorted(params.items())])
    sig = hmac.new(API_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
    params['signature'] = sig
    headers = {'X-MBX-APIKEY': API_KEY, 'Content-Type': 'application/x-www-form-urlencoded'}
    url = f'{BINANCE_API}{endpoint}'
    if method == 'GET':
        resp = requests.get(url, headers=headers, params=params, timeout=15)
    else:
        resp = requests.post(url, headers=headers, params=params, timeout=15)
    return resp

def get_price(symbol):
    r = requests.get(f'{BINANCE_API}/api/v3/ticker/price?symbol={symbol}', timeout=10)
    if r.status_code == 200:
        return float(r.json()['price'])
    return None

def get_exchange_info(symbol):
    r = signed_request('GET', '/api/v3/exchangeInfo', {'symbol': symbol})
    if r.status_code == 200:
        data = r.json()
        for s in data.get('symbols', []):
            if s['symbol'] == symbol:
                return s
    return None

def sell_market(symbol, quantity):
    """Market sell"""
    params = {
        'symbol': symbol,
        'side': 'SELL',
        'type': 'MARKET',
        'quantity': quantity,
        'newOrderRespType': 'FULL'
    }
    r = signed_request('POST', '/api/v3/order', params)
    return r

def buy_market(symbol, usdt_amount):
    """Market buy using quoteOrderQty"""
    params = {
        'symbol': symbol,
        'side': 'BUY',
        'type': 'MARKET',
        'quoteOrderQty': str(usdt_amount),
        'newOrderRespType': 'FULL'
    }
    r = signed_request('POST', '/api/v3/order', params)
    return r

# ─── CHECK ───
print("=== A4 BLADE EXECUTION ===")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M BJT', time.gmtime(time.time()+28800))}")

# Check current prices
btc_price = get_price('BTCUSDT')
c_price = get_price('CUSDT')
mdx_price = get_price('MDXUSDT')
allo_price = get_price('ALLOUSDT')
jto_price = get_price('JTOUSDT')

print(f"BTC: ${btc_price:.2f}")
print(f"C: ${c_price:.4f}")
print(f"MDX: ${mdx_price:.6f}")
print(f"ALLO: ${allo_price:.4f}")
print(f"JTO: ${jto_price:.4f}")

# Get LOT_SIZE for C and MDX
c_info = get_exchange_info('CUSDT')
mdx_info = get_exchange_info('MDXUSDT')

if c_info:
    c_lot = next((f for f in c_info['filters'] if f['filterType']=='LOT_SIZE'), None)
    if c_lot:
        print(f"C LOT_SIZE: minQty={c_lot['minQty']}, stepSize={c_lot['stepSize']}")
        c_step = float(c_lot['stepSize'])
    else:
        c_step = 0.01

if mdx_info:
    mdx_lot = next((f for f in mdx_info['filters'] if f['filterType']=='LOT_SIZE'), None)
    if mdx_lot:
        print(f"MDX LOT_SIZE: minQty={mdx_lot['minQty']}, stepSize={mdx_lot['stepSize']}")
        mdx_step = float(mdx_lot['stepSize'])
    else:
        mdx_step = 0.01

# C: 412.3026 tokens
c_qty = 412.3026
# Round down to step size
step = float(c_lot['stepSize']) if c_info and c_lot else 0.01
precision = len(str(step).split('.')[1]) if '.' in str(step) else 0
c_qty_rounded = math.floor(c_qty / step) * step
c_qty_rounded = round(c_qty_rounded, precision if precision > 0 else 6)

print(f"\n--- EXECUTION ---")
print(f"1. SELL C: {c_qty_rounded} tokens @ ~${c_price:.4f} = ~${c_qty_rounded*c_price:.2f}")

sell_result = sell_market('CUSDT', str(c_qty_rounded))
if sell_result.status_code == 200:
    sell_data = sell_result.json()
    sell_price = 0
    sell_qty = 0
    for fill in sell_data.get('fills', []):
        sell_qty += float(fill['qty'])
        sell_price += float(fill['qty']) * float(fill['price'])
    if sell_qty > 0:
        sell_price = sell_price / sell_qty
    print(f"   ✅ SELL C executed: {sell_qty:.2f} @ ${sell_price:.4f} = ${sell_qty*sell_price:.2f}")
    c_proceeds = sell_qty * sell_price
else:
    print(f"   ❌ SELL C FAILED: {sell_result.status_code} {sell_result.text[:200]}")
    c_proceeds = 0

# Buy MDX $25
mdx_buy_usdt = 25.00
print(f"2. BUY MDX: ${mdx_buy_usdt:.2f} @ ~${mdx_price:.6f}")

buy_result = buy_market('MDXUSDT', mdx_buy_usdt)
if buy_result.status_code == 200:
    buy_data = buy_result.json()
    buy_qty = 0
    buy_price = 0
    for fill in buy_data.get('fills', []):
        buy_qty += float(fill['qty'])
        buy_price += float(fill['qty']) * float(fill['price'])
    if buy_qty > 0:
        buy_price = buy_price / buy_qty
    print(f"   ✅ BUY MDX executed: {buy_qty:.2f} @ ${buy_price:.4f} = ${buy_qty*buy_price:.2f}")
    mdx_cost = buy_qty * buy_price
else:
    print(f"   ❌ BUY MDX FAILED: {buy_result.status_code} {buy_result.text[:200]}")
    mdx_cost = 0

print(f"\n--- TRADE RECORD ---")
print(f"SELL C {c_qty_rounded:.2f} @ ${sell_price:.4f} = ${c_proceeds:.2f}")
print(f"BUY MDX ${mdx_buy_usdt:.2f} @ ${buy_price:.6f}")

# Final check
btc_final = get_price('BTCUSDT')
print(f"\nBTC final: ${btc_final:.2f}")
print("DONE")
