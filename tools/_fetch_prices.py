#!/usr/bin/env python3
"""Fetch crypto prices"""
import json, urllib.request

url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,dogecoin,hyperliquid,zcash&vs_currencies=usd&include_24hr_change=true"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read())

print('=== 主流币种价格 ===')
for coin, info in data.items():
    usd = info.get('usd', '?')
    chg = info.get('usd_24h_change', 0)
    print(f'{coin}: ${usd} (24h: {chg:.2f}%)')
