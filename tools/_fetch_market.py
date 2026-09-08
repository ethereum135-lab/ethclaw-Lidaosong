#!/usr/bin/env python3
"""Fetch current market data for sprint check."""
import urllib.request
import json

# ETH price
try:
    req = urllib.request.Request("https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT")
    eth_price = json.loads(urllib.request.urlopen(req, timeout=8).read())["price"]
    print(f"ETH: ${float(eth_price):.2f}")
except: print("ETH: FAILED")

# ETH 24hr stats
try:
    req = urllib.request.Request("https://api.binance.com/api/v3/ticker/24hr?symbol=ETHUSDT")
    d = json.loads(urllib.request.urlopen(req, timeout=8).read())
    print(f"ETH 24h: {float(d['priceChangePercent']):.2f}% | vol: ${float(d['quoteVolume']):,.0f}")
except: print("ETH 24h: FAILED")

# BTC price
try:
    req = urllib.request.Request("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
    btc_price = json.loads(urllib.request.urlopen(req, timeout=8).read())["price"]
    print(f"BTC: ${float(btc_price):.2f}")
except: print("BTC: FAILED")

# Top movers - check some coins
for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "BNBUSDT"]:
    try:
        req = urllib.request.Request(f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym}")
        d = json.loads(urllib.request.urlopen(req, timeout=5).read())
        pcp = float(d['priceChangePercent'])
        lp = float(d['lastPrice'])
        emoji = "🟢" if pcp > 0 else "🔴"
        print(f"{emoji} {sym.replace('USDT','')}: ${lp:.4f} ({pcp:+.2f}%)")
    except: pass

# F&G
try:
    req = urllib.request.Request("https://api.alternative.me/fng/?limit=1")
    d = json.loads(urllib.request.urlopen(req, timeout=8).read())
    fng = d['data'][0]
    print(f"F&G: {fng['value']} - {fng['value_classification']}")
except: print("F&G: FAILED")
