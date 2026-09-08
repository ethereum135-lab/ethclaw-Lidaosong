#!/usr/bin/env python3
"""Fetch CoinGecko market data"""
import json, urllib.request

try:
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=10&page=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    for c in data:
        sym = c['symbol'].upper()
        price = c['current_price']
        chg = c.get('price_change_percentage_24h', 0) or 0
        vol = c['total_volume'] / 1e9
        mcap = c['market_cap'] / 1e9
        print(f"{sym:10s} | ${price:>8.2f} | 24h:{chg:>+7.2f}% | vol:{vol:.2f}B | mcap:{mcap:.2f}B")
except Exception as e:
    print(f"CG_ERROR: {e}")
