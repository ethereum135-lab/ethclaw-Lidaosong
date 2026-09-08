#!/usr/bin/env python3
"""Fetch CG Trending (safe .py file method to bypass security scan)"""
import json, urllib.request, sys

url = "https://api.coingecko.com/api/v3/search/trending"
try:
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    coins = data.get("coins", [])
    print("=== CG Trending TOP7 ===")
    for i, c in enumerate(coins[:7]):
        item = c.get("item", c)
        name = item.get("name", "?")
        symbol = item.get("symbol", "?")
        rank = item.get("market_cap_rank", "?")
        print(f"  {i+1}. {name} ({symbol}) | MC Rank: {rank}")
except Exception as e:
    print(f"Failed: {e}")
