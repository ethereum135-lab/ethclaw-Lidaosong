#!/usr/bin/env python3
"""物理验证：精确计算Binance账户总估值"""
import requests, json, hashlib, hmac, time, os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open("config/auth.json") as f:
    d = json.load(f)
ak = d['binance']['api_key']
sk = d['binance']['api_secret']

def sign(params, secret):
    query = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()

params = {'timestamp': int(time.time() * 1000), 'recvWindow': 60000}
params['signature'] = sign(params, sk)
r = requests.get("https://api.binance.com/api/v3/account", params=params, headers={'X-MBX-APIKEY': ak}, timeout=10)
if r.status_code != 200:
    print(f"API错误: {r.status_code} {r.text[:200]}")
    exit(1)

data = r.json()
non_zero = []
for b in data['balances']:
    qty = float(b['free']) + float(b['locked'])
    if qty > 0:
        non_zero.append((b['asset'], qty))

# Get prices
symbols = [f"{a}USDT" for a, q in non_zero if a not in ('USDT', 'USDC', 'BUSD')]
prices = {}
if symbols:
    for i in range(0, len(symbols), 100):
        chunk = symbols[i:i+100]
        r2 = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbols={json.dumps(chunk)}", timeout=10)
        if r2.status_code == 200:
            for p in r2.json():
                prices[p['symbol'].replace('USDT', '')] = float(p['price'])

# Calculate total
total = 0
print(f"=== 组合总估值（{time.strftime('%m-%d %H:%M')}）===")
for asset, qty in non_zero:
    if asset in ('USDT',):
        total += qty
    elif asset in ('USDC', 'BUSD', 'FDUSD', 'DAI', 'TUSD'):
        total += qty
    elif asset in prices:
        val = qty * prices[asset]
        total += val
        if val >= 1:
            print(f"  {asset}: {qty:.4f} @ ${prices[asset]:.4f} = ${val:.2f}")

print(f"  {'='*35}")
print(f"  💰 总估值: ${total:.2f}")
print(f"  本金430U: {((total-430)/430*100):+.2f}%")
