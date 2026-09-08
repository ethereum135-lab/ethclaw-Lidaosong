#!/usr/bin/env python3
"""Fetch Binance 24h top gainers (USDT pairs only)"""
import json, urllib.request

try:
    req = urllib.request.Request("https://api.binance.com/api/v3/ticker/24hr",
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    # Filter USDT pairs, exclude stablecoins and leveraged products
    exclude = ['UP', 'DOWN', 'BULL', 'BEAR', 'USDC', 'USDP', 'TUSD', 'DAI', 'FDUSD', 'BUSD']
    usdt_pairs = [t for t in data if t['symbol'].endswith('USDT') and
                  not any(x in t['symbol'].upper() for x in exclude)]

    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['priceChangePercent']), reverse=True)
    top10 = sorted_pairs[:10]
    for i, p in enumerate(top10, 1):
        vol = float(p['quoteVolume'])
        vol_str = f"{vol:.0f}" if vol < 1e9 else f"{vol/1e9:.2f}B"
        print(f"{i}. {p['symbol']:15s} | 24h: {float(p['priceChangePercent']):+6.2f}% | Vol: {vol_str}USDT | Last: {p['lastPrice']}")
except Exception as e:
    print(f"ERROR: {e}")
