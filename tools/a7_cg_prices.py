#!/usr/bin/env python3
"""Fetch specific coin prices from CoinGecko"""
import json, urllib.request

coins = ["dogecoin","bitcoin","ethereum","worldcoin","render-token","fetch-ai","near-protocol","hyperliquid","ondo-finance"]
ids = ",".join(coins)
try:
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    for cid in coins:
        if cid in data:
            d = data[cid]
            price = d.get('usd', 0)
            chg = d.get('usd_24h_change') or 0
            vol = (d.get('usd_24h_vol') or 0) / 1e6
            mcap = (d.get('usd_market_cap') or 0) / 1e9
            print(f"{cid:20s} | ${price:>8.4f} | 24h:{chg:>+7.2f}% | vol:{vol:.0f}M | mcap:{mcap:.2f}B")
        else:
            print(f"{cid:20s} | NOT FOUND")
except Exception as e:
    print(f"ERROR: {e}")
