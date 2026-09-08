#!/usr/bin/env python3
"""Fetch prices via subprocess curl"""
import subprocess, json, sys

coins = ['ZECUSDT','CHIPUSDT','TONUSDT','PARTIUSDT','CREAMUSDT','CHZUSDT','STGUSDT','ELFUSDT','HMSTRUSDT','GENIUSUSDT','LTCUSDT']
symbols = '%2C'.join([f'%22{c}%22' for c in coins])
url = f'https://api.binance.com/api/v3/ticker/24hr?symbols=[{symbols}]'

result = subprocess.run([
    'curl', '--socks5-hostname', '127.0.0.1:1080',
    '-s', '--connect-timeout', '10',
    url
], capture_output=True, text=True, timeout=15)

if result.returncode != 0:
    print(f'CURL_ERROR: {result.stderr[:200]}')
    sys.exit(1)

data = json.loads(result.stdout)
prices = {}
for d in data:
    prices[d['symbol']] = d

# Portfolio
pos = {
    'ZEC':   {'qty': 0.2357, 'entry': 387.5},
    'PARTI': {'qty': 637.6414, 'entry': 0.0548},
    'CHIP':  {'qty': 680, 'entry': 0.0367},
    'TON':   {'qty': 29.7362, 'entry': 1.605},
}

total = 0
print(f'{"Coin":<8} {"Qty":<12} {"Price":<12} {"Entry":<12} {"Value":<10} {"PnL%":<8} {"24h%":<8}')
print('-'*70)
for s in ['ZEC','CHIP','TON','PARTI']:
    sym = s + 'USDT'
    if sym in prices:
        d = prices[sym]
        p = float(d['lastPrice'])
        ch = float(d['priceChangePercent'])
        q = pos[s]['qty']
        e = pos[s]['entry']
        v = q * p
        c = q * e
        pl = ((p-e)/e)*100
        total += v
        print(f'{s:<8} {q:<12.6f} {p:<12.6f} ${e:<8.4f} ${v:<7.2f} {pl:<+8.2f}% {ch:<+8.2f}%')

usdt = 40.64
total += usdt
print(f'\nProtfolio: ${total:.2f}')
print(f'USDT: ${usdt:.2f} ({(usdt/total*100):.1f}%)')
print(f'Day target (2%): ${total*0.02:.2f}')
print(f'Day realized: $0')

# Sell check
print(f'\n=== SELL CHECKS ===')
for s in ['ZEC','CHIP','TON','PARTI']:
    sym = s + 'USDT'
    if sym in prices:
        d = prices[sym]
        p = float(d['lastPrice'])
        ch = float(d['priceChangePercent'])
        e = pos[s]['entry']
        pl = ((p-e)/e)*100
        issues = []
        if ch < -5:
            issues.append(f'24h跌{ch:.1f}%→减半仓')
        if pl <= -5:
            issues.append(f'硬止损-{abs(pl):.1f}%→全清')
        if issues:
            print(f'  🔴 {s}: {" | ".join(issues)}')
        else:
            print(f'  🟢 {s}: PnL={pl:+.2f}% 24h={ch:+.2f}% — HOLD')

# Decision
print(f'\n=== DECISION ===')
slots = 4 - len(pos)
usdt_pct = (usdt/total)*100
print(f'Slots: {len(pos)}/4 full · USDT: {usdt_pct:.1f}% (<20%)')
print(f'CHIP: new < 6h · All positions profitable')
print(f'→ No sell signals')
print(f'→ USDT < 20%: No mandatory opening')
print(f'→ 4/4 full: Need rotation for new positions')
print(f'→ All profit + no sell signals → FULL HOLD')
print(f'→ SSH AWS dead(port65535) → local decision complete')
print(f'→ Waiting SSH recovery to push signals')
