#!/usr/bin/env python3
"""Quick check STG and dust coins."""
import json, urllib.request, ssl
ctx = ssl.create_default_context()
def api_get(url):
    r = urllib.request.urlopen(url, context=ctx, timeout=15)
    return json.loads(r.read())

for sym in ['STGUSDT', 'DYMUSDT', 'UNIUSDT', 'ORDIUSDT']:
    try:
        info = api_get(f'https://api.binance.com/api/v3/exchangeInfo?symbol={sym}')
        s = info['symbols'][0]
        t = api_get(f'https://api.binance.com/api/v3/ticker/24hr?symbol={sym}')
        p = float(t['lastPrice'])
        chg = float(t['priceChangePercent'])
        vol = float(t['quoteVolume'])
        status = s['status']
        spot = s['isSpotTradingAllowed']
        ok = '✅' if (status == 'TRADING' and spot) else '❌'
        print(f"{sym}: ${p:.6f} | 24h: {chg:+.2f}% | Vol: ${vol:.0f} | status={status} {ok}")
    except Exception as e:
        print(f"{sym}: ERROR {e}")
