#!/usr/bin/env python3
"""快速查涨幅榜前几名当前价格"""
import urllib.request, json, sys

symbols = ["SYNUSDT","UTKUSDT","KDAUSDT","AGLDUSDT","GUSDT","NEARUSDT","INJUSDT"]
sym_str = "%2C".join(["%22"+s+"%22" for s in symbols])
url = f"https://api.binance.com/api/v3/ticker/24hr?symbols=[{sym_str}]"

req = urllib.request.Request(url)
req.add_header("User-Agent", "Mozilla/5.0")
try:
    data = json.loads(urllib.request.urlopen(req, timeout=10).read())
    for d in data:
        s = d["symbol"].replace("USDT","")
        p = float(d["lastPrice"])
        chg = float(d["priceChangePercent"])
        vol = float(d["quoteVolume"]) / 1_000_000
        print(f"{s:8s} ${p:<10.6f} {chg:+.2f}% vol${vol:<8.2f}M")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
