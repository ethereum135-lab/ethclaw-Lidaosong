#!/usr/bin/env python3
"""立即买入SYNUSDT — 有动静就建仓"""
import json, hashlib, hmac, time, math, os

AUTH_PATH = os.path.expanduser("~/zq_web4_trading_system/config/auth.json")
auth = json.load(open(AUTH_PATH))["binance"]
KEY = auth["api_key"]
SECRET = auth["api_secret"]

import urllib.request, ssl
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def api_call(params, method="GET", path="/api/v3/account"):
    params["timestamp"] = int(time.time()*1000)
    params["recvWindow"] = 60000
    qs = "&".join(f"{k}={v}" for k,v in sorted(params.items()))
    sig = hmac.new(SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(f"https://api.binance.com{path}?{qs}&signature={sig}", method=method)
    req.add_header("X-MBX-APIKEY", KEY)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15, context=CTX).read())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()[:200]}
    except Exception as e:
        return {"_error": str(e)[:200]}

SYMBOL = "SYNUSDT"
AMOUNT = 15.00

# 先查余额
acct = api_call({})
if "_error" in acct:
    print(f"❌ 账户查询失败: {acct}")
    exit(1)

balances = {b["asset"]: float(b["free"]) for b in acct["balances"] if float(b["free"]) > 0.001}
usdt = balances.get("USDT", 0)
print(f"📊 USDT可用: ${usdt:.2f}")

if usdt < AMOUNT:
    print(f"❌ USDT不足${AMOUNT}")
    exit(1)

# 执行买入
buy_params = {
    "symbol": SYMBOL,
    "side": "BUY",
    "type": "MARKET",
    "quoteOrderQty": AMOUNT
}

print(f"🚀 买入 {SYMBOL} ${AMOUNT}...")
result = api_call(buy_params, "POST", "/api/v3/order")

if "_error" in result:
    print(f"❌ 买入失败: {result}")
    exit(1)

fills = result.get("fills", [])
avg_price = sum(float(f["price"]) * float(f["qty"]) for f in fills) / sum(float(f["qty"]) for f in fills)
exec_qty = float(result.get("executedQty", 0))
cumm_qty = float(result.get("cummulativeQuoteQty", 0))

print(f"✅ 买入成功!")
print(f"   数量: {exec_qty:.2f} SYN")
print(f"   均价: ${avg_price:.4f}")
print(f"   金额: ${cumm_qty:.2f}")
print(f"   状态: {result.get('status', '?')}")

# 设止损单
stop_price = round(avg_price * 0.97, 4)
take_profit = round(avg_price * 1.08, 4)
print(f"\n📋 止损: ${stop_price} (-3%)")
print(f"📋 止盈: ${take_profit} (+8%)")

# 设限价止损单
stop_params = {
    "symbol": SYMBOL,
    "side": "SELL",
    "type": "STOP_LOSS_LIMIT",
    "quantity": round(exec_qty * 0.98, 1),
    "stopPrice": stop_price,
    "price": round(stop_price * 0.98, 4),
    "timeInForce": "GTC"
}
stop_res = api_call(stop_params, "POST", "/api/v3/order")
if "_error" in stop_res:
    print(f"⚠️ 止损单失败: {stop_res['_error']}")
else:
    print(f"✅ 止损单已设: ${stop_price}")

# 验证余额
acct2 = api_call({})
usdt2 = float([b["free"] for b in acct2["balances"] if b["asset"] == "USDT"][0])
print(f"\n📊 USDT余额: ${usdt2:.2f} (消费${cumm_qty:.2f})")
