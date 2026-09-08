#!/usr/bin/env python3
"""Quick price & balance check for A4 Blade Agent"""
import json, hmac, hashlib, time, requests, sys

def get_prices(symbols):
    q = '[' + ','.join(f'"{s}"' for s in symbols) + ']'
    resp = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbols={q}', timeout=10)
    return {s['symbol']: float(s['price']) for s in resp.json()} if resp.status_code==200 else {}

# Load auth
with open('/Users/lidaosong/zq_web4_trading_system/config/auth.json') as f:
    auth = json.load(f)
api_key = auth['binance']['api_key']
api_secret = auth['binance']['api_secret']

# Get account
ts = int(time.time() * 1000)
params = {'timestamp': ts}
qs = '&'.join([f'{k}={v}' for k,v in params.items()])
sig = hmac.new(api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
params['signature'] = sig
headers = {'X-MBX-APIKEY': api_key}
resp = requests.get('https://api.binance.com/api/v3/account', headers=headers, params=params, timeout=10)
if resp.status_code != 200:
    print(f"ERROR: {resp.status_code} {resp.text[:200]}")
    sys.exit(1)

data = resp.json()
balances = {b['asset']: {'free': float(b['free']), 'locked': float(b['locked'])} for b in data['balances'] if float(b['free']) > 0 or float(b['locked']) > 0}

# Key symbols to price
key_syms = ['BTCUSDT','CUSDT','JTOUSDT','ALLOUSDT','DYMUSDT','NEARUSDT','ONDOUSDT','WLDUSDT','ENAUSDT','MEMEUSDT','EPICUSDT','INJUSDT','FILUSDT','TONUSDT','SUIUSDT','UNIUSDT','ARBUSDT','OPUSDT','APTUSDT','TIAUSDT','ORAIUSDT','DYDXUSDT','SEIUSDT','STGUSDT','FETUSDT','IDUSDT','BROCCOLI714USDT','HOMEUSDT','SAHARAUSDT','CUSDT','PENGUUSDT','1000CATUSDT','VIRTUALUSDT','BERAUSDT','GENIUSUSDT','OPGUSDT','ALPINEUSDT','GTCUSDT','QUICKUSDT','MBOXUSDT','FIDAUSDT','ACHUSDT','APEUSDT','OSMOUSDT','SYNUSDT','ALTUSDT','EIGENUSDT','BIOUSDT','AIXBTUSDT','COOKIEUSDT','NOMUSDT','FFUSDT','EDENUSDT','EULUSDT','ZBTUSDT','BANANAS31USDT','PLUMEUSDT','ASTERUSDT','XPLUSDT','NILUSDT','GPSUSDT','PARTIUSDT','BABYUSDT','INITUSDT','HEMIUSDT','KITEUSDT','MMTUSDT','SAPIENUSDT','NIGHTUSDT','MEGAUSDT','ZAMAUSDT','KATUSDT','CFGUSDT','AIGENSYNUSDT']
prices = get_prices(key_syms)

# USDT
usdt = balances.get('USDT', {}).get('free', 0)
print(f"=== BALANCE SNAPSHOT ===")
print(f"USDT: ${usdt:.2f}")
print()

# Non-trivial positions (>$0.10)
total = usdt
print("=== NON-TRIVIAL POSITIONS (>$0.10) ===")
for asset, bal in sorted(balances.items()):
    sym = f"{asset}USDT"
    price = prices.get(sym, 0)
    val = bal['free'] * price
    if val > 0.10:
        total += val
        pnl = ""
        print(f"  {asset:12s}  {bal['free']:>12.6f}  @ ${price:<10.4f}  = ${val:<8.2f}  {bal['locked']:>6}locked")

print(f"\n=== TOTAL PORTFOLIO VALUE === ${total:.2f}")
print(f"=== BTC PRICE === ${prices.get('BTCUSDT', 0):.2f}")
