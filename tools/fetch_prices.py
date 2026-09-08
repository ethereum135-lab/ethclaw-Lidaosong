#!/usr/bin/env python3
"""Fetch real-time prices via SOCKS5 proxy."""
import json, sys
import socks, socket
import urllib.request

socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 1080)
socket.socket = socks.socksocket

symbols = ["BTCUSDT","ZECUSDT","ENAUSDT","NEARUSDT","XPLUSDT","WLDUSDT","SYNUSDT"]
params = json.dumps(symbols)
url = f"https://api.binance.com/api/v3/ticker/price?symbols={urllib.request.quote(params)}"

try:
    req = urllib.request.urlopen(url, timeout=10)
    data = json.loads(req.read())
    for d in data:
        print(f"{d['symbol']}: {d['price']}")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
