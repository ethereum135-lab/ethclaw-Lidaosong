#!/usr/bin/env python3
"""Execute hardstop sells for MEME and BABY via Binance API"""
import json, hmac, hashlib, time, requests, sys

AUTH_PATH = '/Users/lidaosong/zq_web4_trading_system/config/auth.json'
BINANCE_API = 'https://api.binance.com'

with open(AUTH_PATH) as f:
    auth = json.load(f)
API_KEY = auth['binance']['api_key']
API_SECRET = auth['binance']['api_secret']

def binance_post(endpoint, params):
    """Binance signed POST with params as form body"""
    params['timestamp'] = int(time.time() * 1000)
    qs = '&'.join([f'{k}={v}' for k,v in sorted(params.items())])
    sig = hmac.new(API_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
    url = f'{BINANCE_API}{endpoint}'
    headers = {'X-MBX-APIKEY': API_KEY, 'Content-Type': 'application/x-www-form-urlencoded'}
    body = f'{qs}&signature={sig}'
    resp = requests.post(url, headers=headers, data=body, timeout=20)
    return resp

def binance_get(endpoint, params=None):
    """Binance signed GET"""
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    qs = '&'.join([f'{k}={v}' for k,v in sorted(params.items())])
    sig = hmac.new(API_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
    url = f'{BINANCE_API}{endpoint}?{qs}&signature={sig}'
    headers = {'X-MBX-APIKEY': API_KEY}
    resp = requests.get(url, headers=headers, timeout=15)
    return resp

def sell_market(symbol, quantity):
    """Market sell - quantity is integer for MEME/BABY"""
    params = {
        'symbol': symbol,
        'side': 'SELL',
        'type': 'MARKET',
        'quantity': str(int(quantity)),
        'newOrderRespType': 'FULL',
        'recvWindow': '10000'
    }
    return binance_post('/api/v3/order', params)

def get_price(symbol):
    r = requests.get(f'{BINANCE_API}/api/v3/ticker/price?symbol={symbol}', timeout=10)
    if r.status_code == 200:
        return float(r.json()['price'])
    return None

def get_account():
    r = binance_get('/api/v3/account', {'omitZeroBalances': 'true'})
    if r.status_code == 200:
        return r.json()
    return None

# Get current prices
print('=== CURRENT PRICES (hardstop trigger check) ===')
for sym in ['MEMEUSDT','BABYUSDT','MANTRAUSDT','PARTIUSDT']:
    p = get_price(sym)
    if p: print(f'{sym}: ${p:.6f}')

# MEME hardstop calc: entry=0.000575, hardstop=0.00054625
meme_price = get_price('MEMEUSDT')
if meme_price and meme_price < 0.00054625:
    print(f'\n⚠️ MEME HARDSTOP CONFIRMED: ${meme_price:.6f} < $0.00054625')
else:
    print(f'\n✅ MEME above hardstop: ${meme_price:.6f}')

# BABY hardstop calc: entry=0.01587, hardstop=0.0150765
baby_price = get_price('BABYUSDT')
if baby_price and baby_price < 0.0150765:
    print(f'⚠️ BABY HARDSTOP CONFIRMED: ${baby_price:.6f} < $0.0150765')
else:
    print(f'✅ BABY above hardstop: ${baby_price:.6f}')

print('\n=== 1. SELL MEME (144530 tokens) ===')
r1 = sell_market('MEMEUSDT', 144530)
if r1.status_code == 200:
    result = r1.json()
    qty = sum(float(f['qty']) for f in result.get('fills',[]))
    cum = sum(float(f['qty'])*float(f['price']) for f in result.get('fills',[]))
    avg = cum/qty if qty>0 else 0
    print(f'✅ MEME SELL SUCCESS: {qty:.0f} @ ${avg:.6f} = ${cum:.2f}')
else:
    print(f'❌ MEME SELL FAILED: {r1.status_code} {r1.text[:300]}')
    # Try different qty
    print('Trying with exact free balance...')
    r1b = sell_market('MEMEUSDT', 144530)
    if r1b.status_code == 200:
        result = r1b.json()
        qty = sum(float(f['qty']) for f in result.get('fills',[]))
        cum = sum(float(f['qty'])*float(f['price']) for f in result.get('fills',[]))
        avg = cum/qty if qty>0 else 0
        print(f'✅ MEME SELL SUCCESS: {qty:.0f} @ ${avg:.6f} = ${cum:.2f}')
    else:
        print(f'❌ MEME SELL AGAIN FAILED: {r1b.status_code} {r1b.text[:300]}')

print('\n=== 2. SELL BABY (3287 tokens) ===')
r2 = sell_market('BABYUSDT', 3287)
if r2.status_code == 200:
    result2 = r2.json()
    qty2 = sum(float(f['qty']) for f in result2.get('fills',[]))
    cum2 = sum(float(f['qty'])*float(f['price']) for f in result2.get('fills',[]))
    avg2 = cum2/qty2 if qty2>0 else 0
    print(f'✅ BABY SELL SUCCESS: {qty2:.0f} @ ${avg2:.6f} = ${cum2:.2f}')
else:
    print(f'❌ BABY SELL FAILED: {r2.status_code} {r2.text[:300]}')

print('\n=== FINAL BALANCE ===')
acct = get_account()
if acct:
    for b in acct.get('balances', []):
        free = float(b['free'])
        if free > 0 and b['asset'] in ['USDT','MEME','BABY','PARTI','MANTRA']:
            print(f'{b["asset"]}: free={free:.4f}')
    # Print total USDT
    usdt_free = 0.0
    for b in acct.get('balances', []):
        if b['asset'] == 'USDT':
            usdt_free = float(b['free'])
    print(f'\nUSDT available: ${usdt_free:.2f}')
    # Estimate total equity
    print(f'Estimated equity: MANTRA=${9026*0.007600:.2f} + PARTI=${638*0.0552:.2f} + USDT=${usdt_free:.2f} = ${9026*0.007600 + 638*0.0552 + usdt_free:.2f}')
