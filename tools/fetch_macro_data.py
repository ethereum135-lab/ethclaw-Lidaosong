#!/usr/bin/env python3
"""F&G + Trending + Global fetch for 07-12 scoring"""
import urllib.request, json, sys

results = []

# F&G
try:
    req = urllib.request.Request('https://api.alternative.me/fng/', headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    fng_val = data['data'][0]['value']
    fng_class = data['data'][0]['value_classification']
    results.append(f"F&G: {fng_val} ({fng_class})")
except Exception as e:
    results.append(f"F&G failed: {e}")

# Trending
try:
    req = urllib.request.Request('https://api.coingecko.com/api/v3/search/trending', headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    coins = data.get('coins', [])
    results.append("Trending TOP15:")
    for i, t in enumerate(coins[:15], 1):
        item = t.get('item', {})
        name = item.get('name', '?')
        symbol = item.get('symbol', '?')
        score = item.get('score', '?')
        price_btc = item.get('price_btc', 0)
        results.append(f"  {i}. {symbol} ({name}) score={score} price_btc={price_btc}")
except Exception as e:
    results.append(f"Trending failed: {e}")

# Global
try:
    req = urllib.request.Request('https://api.coingecko.com/api/v3/global', headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    d = data['data']
    mcap = d.get('total_market_cap', {}).get('usd', 0)
    vol24 = d.get('total_volume', {}).get('usd', 0)
    btc_d = d.get('market_cap_percentage', {}).get('btc', 0)
    results.append(f"CG Global: MCap=${mcap/1e12:.2f}T | Vol=${vol24/1e12:.2f}T | BTC.D={btc_d:.2f}%")
except Exception as e:
    results.append(f"CG Global failed: {e}")

print('\n'.join(results))
