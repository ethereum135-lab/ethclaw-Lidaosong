#!/usr/bin/env python3
"""Check STG trends and evaluate as BUY_READY candidate."""
import json, urllib.request, ssl
ctx = ssl.create_default_context()
def api_get(url):
    r = urllib.request.urlopen(url, context=ctx, timeout=15)
    return json.loads(r.read())

sym = 'STGUSDT'
t = api_get(f'https://api.binance.com/api/v3/ticker/24hr?symbol={sym}')
p = float(t['lastPrice'])
chg = float(t['priceChangePercent'])
vol = float(t['quoteVolume'])
h24 = float(t['highPrice'])
l24 = float(t['lowPrice'])

k15 = api_get(f'https://api.binance.com/api/v3/klines?symbol={sym}&interval=15m&limit=8')
k1h = api_get(f'https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h&limit=6')
k4h = api_get(f'https://api.binance.com/api/v3/klines?symbol={sym}&interval=4h&limit=6')

c15 = [float(k[4]) for k in k15]
c1h = [float(k[4]) for k in k1h]
c4h = [float(k[4]) for k in k4h]

tr15 = '↑' if c15[-1] > c15[0] else ('↓' if c15[-1] < c15[0] else '→')
tr1h = '↑' if c1h[-1] > c1h[0] else ('↓' if c1h[-1] < c1h[0] else '→')
tr4h = '↑' if c4h[-1] > c4h[0] else ('↓' if c4h[-1] < c4h[0] else '→')

vol_ratio = float(t['volume']) / float(t['count']) if float(t['count']) > 0 else 0
chg15 = (c15[-1]/c15[0] - 1)*100
chg1h = (c1h[-1]/c1h[0] - 1)*100

print(f"STG: ${p:.4f}")
print(f"24h: {chg:+.2f}% | Vol: ${vol:.0f}")
print(f"15m: {tr15} {chg15:+.2f}% | 1h: {tr1h} {chg1h:+.2f}% | 4h: {tr4h}")
print(f"Range: ${l24:.4f} - ${h24:.4f}")

# Phase classifier logic
if chg > 40:
    print("Phase: peaking ❌ AVOID")
elif chg > 15:
    print(f"Phase: fuzzy zone 15-40%, 15m={tr15} → small position observe")
elif chg >= 3 and chg <= 15 and tr15 == '↑' and tr1h == '↑':
    print(f"Phase: just_starting 🟢 BUY_READY (gain={chg:.1f}% in 3-15% range)")
elif chg > 0 and tr15 == '↑':
    print(f"Phase: trending 🟡 HOLD")
elif chg < -3:
    print(f"Phase: declining 🔴 AVOID")
else:
    print(f"Phase: consolidating WATCH")

# Check DYM
try:
    info = api_get('https://api.binance.com/api/v3/exchangeInfo?symbol=DYMUSDT')
    s = info['symbols'][0]
    print(f"\nDYMUSDT: status={s['status']} spot={s['isSpotTradingAllowed']}")
except:
    print(f"\nDYMUSDT: NOT FOUND on Binance")
