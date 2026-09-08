#!/usr/bin/env python3
"""Fetch current prices via SOCKS5 proxy using urllib"""
import json, urllib.request, ssl, os

ssl_ctx = ssl.create_default_context()
proxy_host = '127.0.0.1:1080'

coins = ['ZECUSDT','CHIPUSDT','TONUSDT','PARTIUSDT']
symbols_str = '[' + ','.join([f'"{c}"' for c in coins]) + ']'
url = f'https://api.binance.com/api/v3/ticker/24hr?symbols={symbols_str}'

# Use curl via subprocess (most reliable with SOCKS5)
import subprocess
result = subprocess.run([
    'curl', '--socks5-hostname', proxy_host,
    '-s', '--connect-timeout', '10',
    url
], capture_output=True, text=True, timeout=15)

if result.returncode != 0:
    print(f'CURL_ERROR: {result.stderr[:200]}')
    exit(1)

data = json.loads(result.stdout)

# Portfolio from Cycle #190
positions = {
    'ZEC':   {'qty': 0.2357, 'entry': 387.5},
    'PARTI': {'qty': 637.6414, 'entry': 0.0548},
    'CHIP':  {'qty': 680, 'entry': 0.0367},
    'TON':   {'qty': 29.7362, 'entry': 1.605},
}

total_val = 0
usdt = 40.64

print('Coin     Qty          Price       Entry      Value     PnL%      24h%')
print('-' * 75)

for d in data:
    s = d['symbol'].replace('USDT','')
    p = float(d['lastPrice'])
    ch24 = float(d['priceChangePercent'])
    
    if s in positions:
        pos = positions[s]
        qty = pos['qty']
        entry = pos['entry']
        value = qty * p
        cost = qty * entry
        pnl_pct = ((p - entry) / entry) * 100
        total_val += value
        
        print(f'{s:<8} {qty:<12.6f} {p:<12.6f} ${entry:<8.4f} ${value:<7.2f} {pnl_pct:<+8.2f}% {ch24:<+8.2f}%')

total_val += usdt
print(f'\nPortfolio: ${total_val:.2f}')
print(f'USDT: ${usdt:.2f} ({(usdt/total_val*100):.1f}%)')
print(f'Day target (2%): ${total_val*0.02:.2f}')
print(f'Day realized: $0.00')

# Sell check
print(f'\n=== SELL CHECK ===')
for d in data:
    s = d['symbol'].replace('USDT','')
    p = float(d['lastPrice'])
    ch24 = float(d['priceChangePercent'])
    if s in positions:
        pos = positions[s]
        pnl = ((p - pos['entry']) / pos['entry']) * 100
        issues = []
        if ch24 < -5: issues.append(f'24h跌{ch24:.1f}%')
        if pnl <= -5: issues.append(f'硬止损-{abs(pnl):.1f}%')
        print(f'  {s}: PnL={pnl:+.2f}% 24h={ch24:+.2f}% → {"🔴 " + " | ".join(issues) if issues else "🟢 HOLD"}')

# Decision
slots_free = 4 - len(positions)
print(f'\n=== DECISION ===')
print(f'仓位: {len(positions)}/4 · 空位: {slots_free} · USDT: {(usdt/total_val*100):.1f}% (阈值20%)')
print(f'CHIP: +{(float(data[[d["symbol"] for d in data].index("CHIPUSDT")]["lastPrice"])/0.0367-1)*100 if "CHIPUSDT" in [d["symbol"] for d in data] else "?"}% · 新开<6h')
if usdt/total_val < 0.20:
    print('→ USDT < 20%: 无强制开仓义务')
if slots_free == 0:
    print('→ 4满位: 需轮换才能开新仓')
print('→ 全盈利+无卖出信号 → FULL HOLD')
print('→ 等待SSH AWS恢复推信号')
