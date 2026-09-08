#!/usr/bin/env python3
"""Fetch crypto prices from Coingecko"""
import urllib.request, json

try:
    req = urllib.request.Request(
        'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,dogecoin,solana,ripple,cardano&vs_currencies=usd&include_24hr_change=true',
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    for coin, info in data.items():
        chg = info.get('usd_24h_change', 0)
        arrow = '↑' if chg > 0 else '↓'
        print(f'{coin}: ${info["usd"]} | 24h: {arrow} {abs(chg):.2f}%')
except Exception as e:
    print(f'ERROR: {e}')
