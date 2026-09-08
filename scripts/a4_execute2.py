#!/usr/bin/env python3
"""Execute trades via Binance API directly - fixed signing"""
import json, hmac, hashlib, time, requests, sys, math

BINANCE_API = 'https://api.binance.com'
AUTH_PATH = '/Users/lidaosong/zq_web4_trading_system/config/auth.json'

with open(AUTH_PATH) as f:
    auth = json.load(f)
API_KEY = auth['binance']['api_key']
API_SECRET = auth['binance']['api_secret']

# Sync server time
st = requests.get(f'{BINANCE_API}/api/v3/time', timeout=10)
server_time = st.json()['serverTime'] if st.status_code == 200 else int(time.time()*1000)

def sign_and_send(method, endpoint, params):
    """Properly sign and send Binance API request"""
    params['timestamp'] = server_time
    params['recvWindow'] = 5000
    
    # Build query string - sorted by key as Binance expects
    qs = '&'.join([f'{k}={v}' for k,v in sorted(params.items())])
    
    # Sign
    sig = hmac.new(API_SECRET.encode('utf-8'), qs.encode('utf-8'), hashlib.sha256).hexdigest()
    full_qs = f'{qs}&signature={sig}'
    
    headers = {
        'X-MBX-APIKEY': API_KEY,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    url = f'{BINANCE_API}{endpoint}'
    
    if method == 'GET':
        resp = requests.get(f'{url}?{full_qs}', headers=headers, timeout=15)
    elif method == 'POST':
        resp = requests.post(url, headers=headers, data=full_qs, timeout=15)
    else:
        resp = None
    return resp

def get_price_uns(symbol):
    r = requests.get(f'{BINANCE_API}/api/v3/ticker/price?symbol={symbol}', timeout=8)
    return float(r.json()['price']) if r.status_code == 200 else None

def sell_market(symbol, qty):
    return sign_and_send('POST', '/api/v3/order', {
        'symbol': symbol, 'side': 'SELL', 'type': 'MARKET',
        'quantity': str(qty), 'newOrderRespType': 'FULL'
    })

def buy_market(symbol, usdt):
    return sign_and_send('POST', '/api/v3/order', {
        'symbol': symbol, 'side': 'BUY', 'type': 'MARKET',
        'quoteOrderQty': str(usdt), 'newOrderRespType': 'FULL'
    })

def get_exchange_info(symbol):
    r = requests.get(f'{BINANCE_API}/api/v3/exchangeInfo?symbol={symbol}', timeout=8)
    if r.status_code == 200:
        for s in r.json().get('symbols', []):
            if s['symbol'] == symbol:
                return s
    return None

# Get prices
btc = get_price_uns('BTCUSDT')
c = get_price_uns('CUSDT')
mdx = get_price_uns('MDXUSDT')
allo = get_price_uns('ALLOUSDT')
jto = get_price_uns('JTOUSDT')

print(f"=== A4 BLADE EXECUTION ===")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M BJT', time.gmtime(time.time()+28800))}")
print(f"Server time offset: {server_time - int(time.time()*1000)}ms")
print(f"BTC: ${btc:.2f}")
print(f"C: ${c:.4f} | ALLO: ${allo:.4f} | JTO: ${jto:.4f} | MDX: ${mdx:.6f}")

# Gets for C
c_info = get_exchange_info('CUSDT')
c_lot = next((f for f in c_info['filters'] if f['filterType']=='LOT_SIZE'), None) if c_info else None
c_step = float(c_lot['stepSize']) if c_lot else 0.01
c_prec = len(str(c_step).split('.')[1]) if '.' in str(c_step) else 0

# Round C qty to LOT_SIZE
c_qty = 412.3026
c_qty_rounded = math.floor(c_qty / c_step) * c_step
c_qty_rounded = round(c_qty_rounded, max(c_prec, 6))
c_val = c_qty_rounded * c
print(f"\nC: {c_qty_rounded} tokens × ${c:.4f} = ${c_val:.2f}")

# Test account access first
print(f"\n--- CHECKING ACCOUNT ACCESS ---")
test_resp = sign_and_send('GET', '/api/v3/account', {'omitZeroBalances': 'true'})
print(f"Account check: {test_resp.status_code}")
if test_resp.status_code == 200:
    data = test_resp.json()
    for b in data['balances']:
        a = b['asset']
        f = float(b['free'])
        l = float(b['locked'])
        if a == 'USDT':
            print(f"USDT balance: ${f+l:.2f} (free:${f:.2f}+locked:${l:.2f})")
        elif f > 0.10:
            print(f"  {a}: {f:.6f} (${f*get_price_uns(f'{a}USDT') or 0:.2f})")
else:
    print(f"Account check failed: {test_resp.text[:200]}")
    sys.exit(1)

# Execute SELL C
print(f"\n--- EXECUTING SELL C ---")
sr = sell_market('CUSDT', round(c_qty_rounded, 8))
if sr.status_code == 200:
    sd = sr.json()
    qty = sum(float(f['qty']) for f in sd.get('fills',[]))
    avg_p = sum(float(f['qty'])*float(f['price']) for f in sd.get('fills',[]))/qty if qty > 0 else 0
    print(f"✅ SELL C: {qty:.2f} @ ${avg_p:.4f} = ${qty*avg_p:.2f}")
    c_proceeds = qty * avg_p
else:
    print(f"❌ SELL C FAILED: {sr.status_code} {sr.text[:200]}")
    c_proceeds = 0

# Execute BUY MDX $25
print(f"\n--- EXECUTING BUY MDX $25 ---")
br = buy_market('MDXUSDT', '25.00')
if br.status_code == 200:
    bd = br.json()
    qty = sum(float(f['qty']) for f in bd.get('fills',[]))
    avg_p = sum(float(f['qty'])*float(f['price']) for f in bd.get('fills',[]))/qty if qty > 0 else 0
    print(f"✅ BUY MDX: {qty:.2f} @ ${avg_p:.6f} = ${qty*avg_p:.2f}")
    mdx_cost = qty * avg_p
else:
    print(f"❌ BUY MDX FAILED: {br.status_code} {br.text[:200]}")
    mdx_cost = 0

print(f"\n=== SUMMARY ===")
print(f"SELL C ≈ ${c_proceeds:.2f}")
print(f"BUY MDX ≈ ${mdx_cost:.2f}")
