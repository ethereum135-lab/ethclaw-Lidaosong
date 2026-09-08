#!/usr/bin/env python3
"""Check meaningful positions (>$1) and compute P&L."""
import subprocess, json, math

# Get positions
result = subprocess.run(
    ['ssh', '-o', 'ConnectTimeout=10', '-i', '/Users/lidaosong/.zq_vault/web4.0.pem',
     'ubuntu@15.134.211.154',
     'python3 /home/ubuntu/zq_web4_trading_system/production/engine/aws_executor.py --check'],
    capture_output=True, text=True, timeout=30
)
data = json.loads(result.stdout)

# Price lookup function
def get_price(sym):
    r = subprocess.run(
        ['ssh', '-o', 'ConnectTimeout=10', '-i', '/Users/lidaosong/.zq_vault/web4.0.pem',
         'ubuntu@15.134.211.154',
         f'python3 /home/ubuntu/zq_web4_trading_system/production/engine/aws_executor.py --price {sym}'],
        capture_output=True, text=True, timeout=20
    )
    out = r.stdout.strip()
    if ':' in out:
        return float(out.split('$')[1])
    return None

# Entry prices from TRADES.md (known positions)
entries = {
    'DOGE': None,  # Unknown entry
    'HBAR': 0.0908,
    'HIGH': 0.1900,
    'LINK': 9.922,
    'LUNC': 0.00008151,
    'SAHARA': 0.03422,
    'SUI': 1.1468,
    'FIDA': None,
    'WLD': 0.2921,
}

# Known positions from rotation check
known_positions = ['DOGE','HBAR','HIGH','LINK','LUNC','SAHARA','SUI']

# aws_executor returns a list directly, not a dict with 'balances' key
balances = data if isinstance(data, list) else data.get('balances', [])
positions = [b for b in balances if float(b['free']) > 0]
print(f"{'Asset':<12} {'Free':<14} {'Price':<12} {'Value':<12} {'P&L':<10}")
print("-"*60)
total_value = 0
for p in positions:
    asset = p['asset']
    free = float(p['free'])
    if asset == 'USDT':
        print(f"{asset:<12} ${free:<10.2f} {'-':<12} ${free:<8.2f} {'-':<10}")
        total_value += free
    elif free > 0.001:
        price = get_price(asset)
        if price:
            val = free * price
            total_value += val
            if asset in entries and entries[asset]:
                entry = entries[asset]
                pnl = (price - entry) / entry * 100
            else:
                pnl = None
            pnl_str = f"{pnl:+.2f}%" if pnl is not None else "N/A"
            if val > 1.0:  # Only show >$1 positions
                print(f"{asset:<12} {free:<14.8f} ${price:<8.4f} ${val:<8.2f} {pnl_str:<10}")

print("-"*60)
print(f"{'TOTAL':<12} {'':<14} {'':<12} ${total_value:<.2f}")
print(f"{'USDT%':<12} {'':<14} {'':<12} {total_value and f'{38.84/total_value*100:.1f}%' or 'N/A'}")
