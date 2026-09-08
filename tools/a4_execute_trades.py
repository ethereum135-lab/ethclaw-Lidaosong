#!/usr/bin/env python3
"""
A4执行脚本 — 在AWS上运行，执行卖出尘仓+买入BIO
使用方式：ssh到AWS后 python3 /tmp/a4_execute.py
"""
import json, hashlib, hmac, time, urllib.request, sys

AUTH_PATH = "/home/ubuntu/zq_web4_trading_system/config/auth.json"
auth = json.load(open(AUTH_PATH))["binance"]
api_key = auth["api_key"]
api_secret = auth["api_secret"]

def signed_request(method="GET", path="/api/v3/account", params=None):
    if params is None:
        params = {}
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 60000
    query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sig = hmac.new(api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f"https://api.binance.com{path}?{query}&signature={sig}"
    req = urllib.request.Request(url, method=method)
    req.add_header("X-MBX-APIKEY", api_key)
    req.add_header("User-Agent", "Mozilla/5.0")
    if method == "POST":
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        data = urllib.request.urlopen(req, timeout=15).read()
        return json.loads(data)
    except urllib.error.HTTPError as e:
        return {"error": e.code, "msg": e.read().decode()[:200]}
    except Exception as e:
        return {"error": str(e)[:200]}

def get_balance():
    data = signed_request("GET", "/api/v3/account")
    if "error" in data:
        print(f"Balance error: {data}")
        return {}
    return {x["asset"]: float(x["free"]) + float(x["locked"]) for x in data["balances"]}

def get_price(symbol):
    req = urllib.request.Request(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
    data = json.loads(urllib.request.urlopen(req, timeout=5).read())
    return float(data["price"])

def market_sell(symbol, quantity):
    params = {
        "symbol": symbol,
        "side": "SELL",
        "type": "MARKET",
        "quantity": quantity,
        "newOrderRespType": "FULL"
    }
    result = signed_request("POST", "/api/v3/order", params)
    return result

def market_buy(symbol, quote_order_qty):
    params = {
        "symbol": symbol,
        "side": "BUY",
        "type": "MARKET",
        "quoteOrderQty": quote_order_qty,
        "newOrderRespType": "FULL"
    }
    result = signed_request("POST", "/api/v3/order", params)
    return result

# === Main execution ===
print("=== A4 Execution Node ===")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()+8*3600))} BJT")

# 1. Get current balance
balance = get_balance()
if not balance:
    print("ERROR: Cannot get balance, stopping")
    sys.exit(1)

print(f"\nCurrent USDT: {balance.get('USDT', 0):.2f}")

# Check holdings
for asset in ["XLM","TIA","OPEN","PEPE","PENGU","DYM","UNI"]:
    qty = balance.get(asset, 0)
    if qty > 0:
        try:
            price = get_price(f"{asset}USDT")
            val = qty * price
            print(f"  {asset}: {qty:.4f} x ${price:.6f} = ${val:.2f}")
        except:
            print(f"  {asset}: {qty:.4f} (price unknown)")

# 2. Execute sells: DYM, UNI (dust), PEPE, PENGU (dust <$25)
SELL_LIST = [
    ("PEPEUSDT",   "PEPE",   True),   # dust <$25 + bearish
    ("PENGUUSDT",  "PENGU",  True),   # dust <$25 + bearish
    ("DYMUSDT",    "DYM",    True),   # dust
    ("UNIUSDT",    "UNI",    True),   # dust
]

trades = []

for sym, asset, should_sell in SELL_LIST:
    qty = balance.get(asset, 0)
    if qty <= 0:
        print(f"\n{asset}: 无持仓，跳过")
        continue
    
    price = get_price(sym)
    val = qty * price
    print(f"\n{asset}: {qty:.4f} x ${price:.6f} = ${val:.2f}")
    
    if should_sell and val > 1.0:
        print(f"  → 执行卖出...")
        result = market_sell(sym, qty)
        if "error" in result:
            print(f"  ❌ 卖出失败: {result}")
        elif result.get("status") == "FILLED":
            cum_qty = float(result.get("executedQty", 0))
            cum_quote = float(result.get("cummulativeQuoteQty", 0))
            print(f"  ✅ 卖出成功: {cum_qty:.4f} @ ${cum_quote/cum_qty:.6f} = ${cum_quote:.2f}")
            trades.append({"action": "SELL", "asset": asset, "qty": cum_qty, "value": cum_quote})
        else:
            print(f"  ⚠️ 订单状态: {json.dumps(result)[:200]}")
    elif val <= 1.0:
        print(f"  → 金额<$1，跳过（太小不值手续费）")
    else:
        print(f"  → 不卖出")

# 3. After sells, check new USDT balance
time.sleep(1)
new_balance = get_balance()
usdt_after = new_balance.get("USDT", balance.get("USDT", 0))
print(f"\n=== USDT after sells: ${usdt_after:.2f} ===")

# 4. Buy BIO (top BUY_READY candidate)
if usdt_after >= 10:
    buy_amount = min(usdt_after * 0.30, 25.0)  # 30% of USDT, max $25
    buy_amount = max(buy_amount, 5.0)  # min $5 (MIN_NOTIONAL)
    
    bio_price = get_price("BIOUSDT")
    print(f"\nBIO: 买入 ${buy_amount:.2f} @ ${bio_price:.6f}")
    
    result = market_buy("BIOUSDT", round(buy_amount, 2))
    if "error" in result:
        print(f"  ❌ 买入失败: {result}")
    elif result.get("status") == "FILLED" or result.get("status") == "NEW":
        cum_qty = float(result.get("executedQty", 0))
        cum_quote = float(result.get("cummulativeQuoteQty", 0))
        if cum_qty > 0:
            print(f"  ✅ 买入成功: {cum_qty:.4f} @ ${cum_quote/cum_qty:.6f} = ${cum_quote:.2f}")
        else:
            print(f"  ⚠️ 订单状态: {result.get('status')}")
    else:
        print(f"  ❌ 结果: {json.dumps(result)[:200]}")
else:
    print(f"USDT不足(${usdt_after:.2f})，无法买入")

# 5. Final balance
time.sleep(1)
final_balance = get_balance()
print(f"\n=== Final Balance ===")
usdt_final = final_balance.get("USDT", 0)
print(f"USDT: ${usdt_final:.2f}")
for asset in ["PEPE","PENGU","DYM","UNI","XLM","TIA","OPEN"]:
    qty = final_balance.get(asset, 0)
    if qty > 0:
        try:
            price = get_price(f"{asset}USDT")
            print(f"  {asset}: {qty:.4f} x ${price:.6f} = ${qty*price:.2f}")
        except:
            print(f"  {asset}: {qty:.4f}")

print("\n=== Execution Complete ===")
