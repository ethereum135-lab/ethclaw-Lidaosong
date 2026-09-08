#!/usr/bin/env python3
"""A4 cycle quick price check — CRCLB/BABY/BTC live ticker + BABY 5m momentum."""
import json
import urllib.request

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode())

try:
    syms = json.dumps(["CRCLBUSDT", "BABYUSDT", "BTCUSDT"])
    url = "https://api.binance.com/api/v3/ticker/24hr?symbols=" + urllib.parse.quote(syms)
    for d in get(url):
        print(f"{d['symbol']}: last={d['lastPrice']} chg24h={d['priceChangePercent']}% quoteVol={d['quoteVolume']}")
except Exception as e:
    print(f"ticker error: {e}")

try:
    url = "https://api.binance.com/api/v3/klines?symbol=BABYUSDT&interval=5m&limit=3"
    k = get(url)
    if k:
        c0 = float(k[0][4]); c2 = float(k[-1][4])
        print(f"BABY 5m: {c0} -> {c2} ({(c2/c0-1)*100:+.3f}%)")
    url2 = "https://api.binance.com/api/v3/klines?symbol=CRCLBUSDT&interval=5m&limit=3"
    k2 = get(url2)
    if k2:
        c0 = float(k2[0][4]); c2 = float(k2[-1][4])
        print(f"CRCLB 5m: {c0} -> {c2} ({(c2/c0-1)*100:+.3f}%)")
except Exception as e:
    print(f"kline error: {e}")
