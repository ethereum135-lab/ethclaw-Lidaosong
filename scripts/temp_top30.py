#!/usr/bin/env python3
"""Get Top 30 USDT pairs by volume from Binance"""
import json, urllib.request

data = json.loads(urllib.request.urlopen("https://api.binance.com/api/v3/ticker/24hr").read())
usdt_pairs = [d for d in data if d['symbol'].endswith('USDT') and d['symbol'] != 'USDCUSDT']
usdt_pairs.sort(key=lambda d: float(d['quoteVolume']), reverse=True)
for i, d in enumerate(usdt_pairs[:30]):
    print(f'{i+1:2d}. {d["symbol"]:12s} vol={float(d["quoteVolume"]):.0f} price={d["lastPrice"]} chg={d["priceChangePercent"]}%')
