#!/usr/bin/env python3
"""Check POND and ALLO short-term trends for restore decision."""
import json, urllib.request, ssl

ctx = ssl.create_default_context()

def api_get(url):
    r = urllib.request.urlopen(url, context=ctx, timeout=15)
    return json.loads(r.read())

# Check 15m, 1h, 4h klines for POND and ALLO
for sym in ['PONDUSDT', 'ALLOUSDT']:
    coin = sym.replace('USDT','')
    print(f"\n--- {coin} ---")
    for interval, limit in [('15m',8),('1h',6),('4h',6)]:
        klines = api_get(f'https://api.binance.com/api/v3/klines?symbol={sym}&interval={interval}&limit={limit}')
        closes = [float(k[4]) for k in klines]
        vols = [float(k[5]) for k in klines]
        trend = '↑' if closes[-1] > closes[0] else ('↓' if closes[-1] < closes[0] else '→')
        vol_trend = '↑' if vols[-1] > vols[-3] else '↓'
        chg = (closes[-1]/closes[0] - 1)*100
        print(f"  {interval}: {closes[-1]:.6f} | {trend} {chg:+.2f}% | Vol: {vol_trend}")

# Check what's on the 24h gainers list currently
ticker24 = api_get('https://api.binance.com/api/v3/ticker/24hr')
gainers = [(float(t['priceChangePercent']), t['symbol']) for t in ticker24 if t['symbol'].endswith('USDT') and float(t['quoteVolume']) > 500000]
gainers.sort(reverse=True)
print("\n--- Top 15 Gainers (>$500K vol) ---")
for chg, sym in gainers[:15]:
    print(f"  {sym.replace('USDT',''):8s}: {chg:+.2f}%")
