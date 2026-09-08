#!/usr/bin/env python3
"""Quick equity check via Binance API through AWS executor."""
import subprocess, json, sys

result = subprocess.run(
    ['ssh', 'web4',
     'cd /home/ubuntu/zq_web4_trading_system && python3 production/engine/aws_executor.py --check'],
    capture_output=True, text=True, timeout=30
)
data = json.loads(result.stdout)
if isinstance(data, list):
    balances = data
elif isinstance(data, dict):
    balances = data.get('balances', data.get('result', []))

# Filter to assets with free > 0
non_zero = [b for b in balances if float(b['free']) > 0]
usdt = 0
for b in non_zero:
    if b['asset'] == 'USDT':
        usdt = float(b['free'])
        
print(f'USDT: ${usdt:.2f}')
print(f'Non-zero assets: {len(non_zero)}')
for b in sorted(non_zero, key=lambda x: float(x['free']), reverse=True)[:10]:
    print(f"  {b['asset']}: {b['free']}")
