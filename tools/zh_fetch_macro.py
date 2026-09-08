#!/usr/bin/env python3
"""Fetch macro crypto data for ZH direction fusion"""
import urllib.request, json, sys

# CoinGecko Global
try:
    req = urllib.request.Request(
        'https://api.coingecko.com/api/v3/global',
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    resp = urllib.request.urlopen(req, timeout=10)
    d = json.loads(resp.read())['data']
    mc = d.get('total_market_cap', {}).get('usd', 0)
    btc_d = d.get('market_cap_percentage', {}).get('btc', 0)
    chg_24h = d.get('market_cap_change_percentage_24h_usd', 0)
    print(f"CG_MC=${mc:,.0f}")
    print(f"CG_BTCD={btc_d:.1f}%")
    print(f"CG_CHG={chg_24h:.2f}%")
except Exception as e:
    print(f"CG_ERROR={e}")

# CoinGecko Trending
try:
    req2 = urllib.request.Request(
        'https://api.coingecko.com/api/v3/search/trending',
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    resp2 = urllib.request.urlopen(req2, timeout=10)
    coins = json.loads(resp2.read()).get('coins', [])
    print(f"TRENDING={','.join([c['item']['symbol'].upper() for c in coins[:8]])}")
except Exception as e:
    print(f"TRENDING_ERROR={e}")
