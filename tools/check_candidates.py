#!/usr/bin/env python3
"""Check new gainers for TRADING status and trends."""
import json, urllib.request, ssl

ctx = ssl.create_default_context()

def api_get(url):
    r = urllib.request.urlopen(url, context=ctx, timeout=15)
    return json.loads(r.read())

# Check exchange status for potential new candidates
new_coins = ['NFP','UTK','HIFI','BOND','STG','ADADOWN']
print("--- Exchange Status ---")
for coin in new_coins:
    try:
        info = api_get(f'https://api.binance.com/api/v3/exchangeInfo?symbol={coin}USDT')
        s = info['symbols'][0]
        status = s['status']
        spot = s['isSpotTradingAllowed']
        ok = '✅' if (status == 'TRADING' and spot) else '❌'
        print(f"{coin}: status={status} spot={spot} {ok}")
    except Exception as e:
        print(f"{coin}: ERROR {e}")

# For tradeable ones, check trends
for coin in ['NFP','UTK','HIFI','BOND']:
    try:
        # Price + 24h
        t = api_get(f'https://api.binance.com/api/v3/ticker/24hr?symbol={coin}USDT')
        p = float(t['lastPrice'])
        chg = float(t['priceChangePercent'])
        vol = float(t['quoteVolume'])
        h24 = float(t['highPrice'])
        l24 = float(t['lowPrice'])
        
        # Klines for short-term trends
        k15 = api_get(f'https://api.binance.com/api/v3/klines?symbol={coin}USDT&interval=15m&limit=8')
        k1h = api_get(f'https://api.binance.com/api/v3/klines?symbol={coin}USDT&interval=1h&limit=6')
        k4h = api_get(f'https://api.binance.com/api/v3/klines?symbol={coin}USDT&interval=4h&limit=6')
        
        c15 = [float(k[4]) for k in k15]
        c1h = [float(k[4]) for k in k1h]
        c4h = [float(k[4]) for k in k4h]
        
        tr15 = '↑' if c15[-1] > c15[0] else ('↓' if c15[-1] < c15[0] else '→')
        tr1h = '↑' if c1h[-1] > c1h[0] else ('↓' if c1h[-1] < c1h[0] else '→')
        tr4h = '↑' if c4h[-1] > c4h[0] else ('↓' if c4h[-1] < c4h[0] else '→')
        
        vol_ratio = float(t['volume']) / float(t['count']) if float(t['count']) > 0 else 0
        
        # Phase classification logic
        if chg > 40:
            phase = "peaking ❌已泵顶"
            action = "AVOID"
        elif chg > 15:
            phase = "模糊区15-40%"
            action = "小仓观察"
        elif chg >= 3 and chg <= 15 and tr15 == '↑' and tr1h == '↑' and vol > 1000000:
            phase = "just_starting 🟢"
            action = "BUY_READY"
        elif chg > 0 and tr15 == '↑' and tr1h == '↑':
            phase = "trending 🟡"
            action = "HOLD"
        else:
            phase = "consolidating"
            action = "WATCH"
            
        print(f"\n{coin}: ${p:.6f} | 24h: {chg:+.2f}% | Vol: ${vol:.0f}")
        print(f"  15m{tr15} 1h{tr1h} 4h{tr4h}")
        print(f"  Range: ${l24:.6f} - ${h24:.6f}")
        print(f"  Phase: {phase} → {action}")
    except Exception as e:
        print(f"{coin}: ERROR {e}")
