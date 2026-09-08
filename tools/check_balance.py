#!/usr/bin/env python3
"""物理验证：实时查询Binance账户余额（支持SOCKS5代理绕过451）"""
import requests, json, hashlib, hmac, time, os, sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open("config/auth.json") as f:
    keys = json.load(f)
k = keys["binance"]["api_key"]
s = keys["binance"]["api_secret"]

PROXY = "socks5h://127.0.0.1:1080"

def binance_get(url, params, headers, proxies=None):
    """请求Binance API，自动尝试代理回退"""
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10, proxies=proxies)
        if r.status_code == 200:
            return r
        # 451 → 重试带代理
        if r.status_code == 451 and proxies is None:
            return binance_get(url, params, headers, {"http": PROXY, "https": PROXY})
        return r
    except (requests.ConnectionError, requests.Timeout):
        if proxies is None:
            # 直连失败 → 重试带代理
            return binance_get(url, params, headers, {"http": PROXY, "https": PROXY})
        raise

timestamp = int(time.time() * 1000)
params = "timestamp=" + str(timestamp)
sig = hmac.new(s.encode(), params.encode(), hashlib.sha256).hexdigest()
r = binance_get("https://api.binance.com/api/v3/account?" + params + "&signature=" + sig,
                None, {"X-MBX-APIKEY": k})
if r.status_code != 200:
    print("ERR:", r.status_code, r.text[:200])
    exit(1)

data = r.json()
usdt = 0
holdings = []
for b in data["balances"]:
    free = float(b["free"])
    locked = float(b["locked"])
    total = free + locked
    if b["asset"] == "USDT":
        usdt = total
    elif total > 0:
        holdings.append({"asset": b["asset"], "qty": total})

total_val = usdt
ts = time.strftime("%H:%M:%S")
print(f"📊 实时账户余额 ({ts})")
print(f"  USDT: ${usdt:.2f}")

if holdings:
    syms = json.dumps([h["asset"] + "USDT" for h in holdings])
    r2 = binance_get("https://api.binance.com/api/v3/ticker/price?symbols=" + syms, None, {})
    prices = {}
    if r2.status_code == 200:
        for p in r2.json():
            prices[p["symbol"].replace("USDT", "")] = float(p["price"])
    for h in holdings:
        price = prices.get(h["asset"], 0)
        val = h["qty"] * price
        total_val += val
        if val >= 0.5:
            asset = h["asset"]
            print(f"  {asset}: {h['qty']:.4f} @ ${price:.4f} = ${val:.2f}")

print("  " + "="*35)
print(f"  💰 组合总估值: ${total_val:.2f}")
print(f"  起始本金430U: {((total_val-430)/430*100):+.2f}%")
