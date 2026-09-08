#!/usr/bin/env python3
"""Compute total equity from Binance account (run on web4)."""
import json, subprocess

r = subprocess.run(['python3', 'production/engine/aws_executor.py', '--check'],
                   capture_output=True, text=True, timeout=30)
data = json.loads(r.stdout)
bal = data if isinstance(data, list) else data.get('balances', [])

total_val = 0.0
usdt = 0.0
positions = []

for b in bal:
    free = float(b['free'])
    if free <= 0:
        continue
    asset = b['asset']
    if asset == 'USDT':
        usdt = free
        continue
    if asset in ['LDBNB','LDETH','LDZEC','LDSHIB2','LDUSDC']:
        continue  # skip liquid staking dust
    r2 = subprocess.run(['python3', 'production/engine/aws_executor.py', '--price', asset + 'USDT'],
                        capture_output=True, text=True, timeout=15)
    price_str = r2.stdout.strip()
    price = 0.0
    if price_str and '$' in price_str:
        try:
            price = float(price_str.split('$')[1].split()[0])
        except:
            pass
    val = free * price
    if val > 0.50:
        positions.append((asset, free, price, val))
        total_val += val

positions.sort(key=lambda x: x[3], reverse=True)
total_val += usdt

print(f'USDT: ${usdt:.2f}')
print(f'Positions (>$0.50): {len(positions)}')
for asset, free, price, val in positions:
    print(f'  {asset}: {free} x ${price:.4f} = ${val:.2f}')
print(f'----------------------')
print(f'TOTAL EQUITY: ${total_val:.2f}')
