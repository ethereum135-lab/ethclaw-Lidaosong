#!/usr/bin/env python3
"""Fetch CoinGecko top gainers (24h)"""
import json, urllib.request

try:
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=50&page=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    
    # Filter out stablecoins and sort by 24h change
    stable = ['USDT','USDC','DAI','BUSD','TUSD','USDP','FDUSD','USD1']
    coins = [c for c in data if c['symbol'].upper() not in stable and c.get('price_change_percentage_24h') is not None]
    coins.sort(key=lambda x: x['price_change_percentage_24h'], reverse=True)
    
    print("=== TOP 10 GAINERS (24h) ===")
    for i, c in enumerate(coins[:10], 1):
        sym = c['symbol'].upper()
        price = c['current_price']
        chg = c['price_change_percentage_24h']
        vol = c['total_volume'] / 1e6
        mcap = c['market_cap'] / 1e9
        print(f"{i:2d}. {sym:10s} | ${price:>8.4f} | 24h:{chg:>+7.2f}% | vol:{vol:.0f}M | mcap:{mcap:.2f}B")
    
    print("\n=== TOP 10 LOSERS (24h) ===")
    coins.sort(key=lambda x: x['price_change_percentage_24h'])
    for i, c in enumerate(coins[:10], 1):
        sym = c['symbol'].upper()
        price = c['current_price']
        chg = c['price_change_percentage_24h']
        vol = c['total_volume'] / 1e6
        print(f"{i:2d}. {sym:10s} | ${price:>8.4f} | 24h:{chg:>+7.2f}% | vol:{vol:.0f}M")
except Exception as e:
    print(f"CG_ERROR: {e}")
