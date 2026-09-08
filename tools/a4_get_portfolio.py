#!/usr/bin/env python3
"""Get current portfolio from Binance via SOCKS5 proxy."""
import json, subprocess, sys

AUTH_PATH = "/Users/lidaosong/zq_web4_trading_system/config/auth.json"
auth = json.load(open(AUTH_PATH))["binance"]
API_KEY, API_SECRET = auth["api_key"], auth["api_secret"]

def socks_curl(method, path, params=None):
    import hashlib, hmac, time
    p = dict(params or {})
    p["timestamp"] = int(time.time() * 1000)
    p["recvWindow"] = 60000
    qs = "&".join(f"{k}={v}" for k, v in sorted(p.items()))
    sig = hmac.new(API_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
    url = f"https://api.binance.com{path}?{qs}&signature={sig}"
    cmd = ["curl", "-s", "--connect-timeout", "10", "--max-time", "15",
           "--socks5-hostname", "127.0.0.1:1080",
           "-H", f"X-MBX-APIKEY: {API_KEY}",
           "-H", "User-Agent: Mozilla/5.0"]
    if method == "POST":
        cmd.extend(["-X", "POST", "--data", ""])
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    if r.stdout:
        return json.loads(r.stdout)
    return {"error": r.stderr[:300]}

# Get current account
account = socks_curl("GET", "/api/v3/account", {})
balances = {}
for b in account.get("balances", []):
    free = float(b["free"])
    locked = float(b["locked"])
    if free > 0 or locked > 0:
        balances[b["asset"]] = {"free": free, "locked": locked}

# Show relevant assets
assets_of_interest = ["USDT", "SOL", "ZEC", "ENA", "SYN"]
for asset in assets_of_interest:
    if asset in balances:
        print(f"{asset}: free={balances[asset]['free']:.6f} locked={balances[asset]['locked']:.6f}")

# Get current prices
prices = {"USDT": 1.0}
for sym in ["SOLUSDT", "ZECUSDT", "ENAUSDT", "SYNUSDT"]:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={sym}"
    r = subprocess.run(
        ["curl", "-s", "--connect-timeout", "8", "--max-time", "10",
         "--socks5-hostname", "127.0.0.1:1080", url],
        capture_output=True, text=True, timeout=15)
    if r.stdout:
        pdata = json.loads(r.stdout)
        prices[sym.replace("USDT", "")] = float(pdata["price"])

# Calculate portfolio
total = 0
entries = {}
for asset, bal in balances.items():
    b = bal["free"] + bal["locked"]
    if asset == "USDT":
        val = b
    elif asset in prices:
        val = b * prices[asset]
    else:
        continue
    total += val
    entries[asset] = {"bal": b, "price": prices.get(asset, 1.0), "value": val}

print("\n=== PORTFOLIO SUMMARY ===")
for asset, info in sorted(entries.items(), key=lambda x: -x[1]["value"]):
    print(f"{asset}: {info['bal']:.4f} x ${info['price']:.5f} = ${info['value']:.2f}")
usdt_val = entries.get("USDT", {}).get("value", 0)
print(f"TOTAL EQUITY: ${total:.2f}")
print(f"USDT: ${usdt_val:.2f} ({usdt_val/total*100:.1f}%)")
print(f"Invested: ${total-usdt_val:.2f} ({100-usdt_val/total*100:.1f}%)")
