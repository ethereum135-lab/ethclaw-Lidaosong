#!/usr/bin/env python3
"""Check actual portfolio value from Binance spot account"""
import hmac, hashlib, json, time, requests

with open('/Users/lidaosong/zq_web4_trading_system/config/auth.json') as f:
    auth = json.load(f)
ak = auth['binance']['api_key']
sk = auth['binance']['api_secret']

def sign(params, secret):
    query = '&'.join(f'{k}={v}' for k, v in params.items())
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()

def req(path, params=None, signed=False):
    base = 'https://api.binance.com'
    p = dict(params or {})
    if signed:
        p['timestamp'] = int(time.time() * 1000)
        p['recvWindow'] = 60000
        p['signature'] = sign(p, sk)
    headers = {'X-MBX-APIKEY': ak}
    r = requests.request('GET', f'{base}{path}', headers=headers, params=p, timeout=10)
    return r.status_code, r.json()

# Account
code, acct = req('/api/v3/account', signed=True)
if code != 200:
    print(f'Account error {code}: {acct}')
    exit()

# Prices — get all tickers at once
code2, tickers = req('/api/v3/ticker/price')
prices = {}
if code2 == 200:
    for t in tickers:
        sym = t['symbol']
        if sym.endswith('USDT'):
            prices[sym.replace('USDT', '')] = float(t['price'])
        elif sym == 'USDTUSDT':
            prices['USDT'] = 1.0

# Special mappings
price_map = {
    'USDT': 1.0, 'USDC': 1.0, 'BUSD': 1.0, 'XUSD': 1.0,
    'LDBNB': prices.get('BNB', 0),
    'LDETH': prices.get('ETH', 0),
    'LDSOL': prices.get('SOL', 0),
    'LDLUNA': prices.get('LUNA', 0),
    'LDAVAX': prices.get('AVAX', 0),
    'LDSUI': prices.get('SUI', 0),
    'LDLUNC': prices.get('LUNC', 0),
    'LDPEPE': prices.get('PEPE', 0),
    'LDSHIB2': prices.get('SHIB', 0),
    'LDSEI': prices.get('SEI', 0),
    'LDXAI': prices.get('XAI', 0),
    'LDCRV': prices.get('CRV', 0),
    'LDZEC': prices.get('ZEC', 0),
    'LDBERA': prices.get('BERA', 0),
    'LDSXT': prices.get('SXT', 0),
    'LDXPL': prices.get('XPL', 0),
}

total = 0.0
rows = []
for b in acct.get('balances', []):
    free, locked = float(b['free']), float(b['locked'])
    qty = free + locked
    if qty == 0:
        continue
    asset = b['asset']
    p = price_map.get(asset, prices.get(asset, 0))
    if p == 0:
        # Try direct lookup
        try:
            _, t = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={asset}USDT',
                              headers={'X-MBX-APIKEY': ak}, timeout=5)
            if t.status_code == 200:
                p = float(t.json()['price'])
                prices[asset] = p
        except:
            pass
    usd = qty * p
    if usd > 0.10:
        total += usd
        rows.append((usd, asset, qty, p))

rows.sort(reverse=True)
print(f"{'Asset':<10} {'Qty':<14} {'Price':<12} {'Value':<10}")
print('-' * 48)
for usd, asset, qty, price in rows:
    print(f'{asset:<10} {qty:<14.4f} ${price:<10.4f} ${usd:<8.2f}')
print('-' * 48)
print(f'{"TOTAL":<10} {"":<14} {"":<12} ${total:<8.2f}')
print(f'Principal: $430.00')
print(f'P&L: ${total - 430:.2f} ({(total - 430) / 430 * 100:.1f}%)')
