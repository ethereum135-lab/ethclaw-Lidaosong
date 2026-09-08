#!/usr/bin/env python3
import json, hashlib, hmac, time, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open("/home/ubuntu/zq_web4_trading_system/config/auth.json") as f:
    auth = json.load(f)["binance"]

params = {"timestamp": int(time.time()*1000), "recvWindow": 60000}
qs = "&".join(f"{k}={v}" for k,v in sorted(params.items()))
sig = hmac.new(auth["api_secret"].encode(), qs.encode(), hashlib.sha256).hexdigest()
req = urllib.request.Request(f"https://api.binance.com/api/v3/account?{qs}&signature={sig}")
req.add_header("X-MBX-APIKEY", auth["api_key"])
data = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())

non_zero = []
for b in data["balances"]:
    f = float(b["free"])
    l = float(b["locked"])
    if f + l > 0:
        non_zero.append(b)

price_req = urllib.request.Request("https://api.binance.com/api/v3/ticker/price")
prices = json.loads(urllib.request.urlopen(price_req, timeout=10, context=ctx).read())
price_map = {p["symbol"]: float(p["price"]) for p in prices}

total = 0
for b in non_zero:
    if b["asset"] == "USDT":
        val = float(b["free"]) + float(b["locked"])
        total += val
        print(f"  USDT     {b['free']}+{b['locked']} = ${val:.2f}")
        continue
    pair = f"{b['asset']}USDT"
    price = price_map.get(pair, 0)
    val = (float(b["free"]) + float(b["locked"])) * price
    total += val
    if val > 3:
        print(f"  {b['asset']:8s}  = ${val:.2f}  (qty={b['free']}+{b['locked']} x ${price:.4f})")

usdt_free = float(non_zero[0]["free"]) if non_zero and non_zero[0]["asset"] == "USDT" else 0
print(f"\nTotal: ${total:.2f}")
print(f"USDT free: ${usdt_free:.2f}")
