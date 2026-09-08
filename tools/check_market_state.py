#!/usr/bin/env python3
"""Check current market state for A4 Blade cycle."""
import json, urllib.request, ssl

ctx = ssl.create_default_context()

def api_get(url):
    r = urllib.request.urlopen(url, context=ctx, timeout=15)
    return json.loads(r.read())

# BTC 24h stats
btc_24h = api_get('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT')
btc_price = float(btc_24h['lastPrice'])
btc_change = float(btc_24h['priceChangePercent'])
btc_high = float(btc_24h['highPrice'])
print(f"BTC: ${btc_price:.2f} | 24h: {btc_change:+.2f}% | High: ${btc_high:.2f}")

# Check POND and ALLO 24h
for sym in ['PONDUSDT', 'ALLOUSDT']:
    try:
        t = api_get(f'https://api.binance.com/api/v3/ticker/24hr?symbol={sym}')
        p = float(t['lastPrice'])
        chg = float(t['priceChangePercent'])
        vol = float(t['quoteVolume'])
        print(f"{sym}: ${p:.6f} | 24h: {chg:+.2f}% | Vol: ${vol:.0f}")
    except:
        print(f"{sym}: ERROR fetching")

# Check exchange status for all BUY_READY candidates
coins = ['LOKA','MDX','ELF','PLA','WAVES','ERN','LIT','XMR','HEI','JST','XAUT','PAXG','TOMO','POND']
print("\n--- Exchange Status ---")
all_ok = True
for coin in coins:
    try:
        info = api_get(f'https://api.binance.com/api/v3/exchangeInfo?symbol={coin}USDT')
        s = info['symbols'][0]
        status = s['status']
        spot = s['isSpotTradingAllowed']
        ok = '✅' if (status == 'TRADING' and spot) else '❌'
        if not (status == 'TRADING' and spot):
            all_ok = False
        print(f"{coin}: status={status} spot={spot} {ok}")
    except:
        print(f"{coin}: NOT FOUND")

print(f"\nAll TRADING: {all_ok}")

# Check if we need new signals scan (last scan was 4+ hours ago)
print("\n--- Signal Freshness ---")
try:
    with open('/Users/lidaosong/zq_web4_trading_system/data/signals.json') as f:
        sig = json.load(f)
    print(f"Last scan: {sig['scanned_at']} ({sig['total_scanned']} coins)")
    print(f"STRONG: {sig['summary']['strong']} SIGNAL: {sig['summary']['signal']}")
except:
    print("Could not read signals.json")
