#!/usr/bin/env python3
"""
A4执行脚本 v2 — 带LOT_SIZE精度处理
"""
import json, hashlib, hmac, time, urllib.request, urllib.error, sys, math

AUTH_PATH = "/home/ubuntu/zq_web4_trading_system/config/auth.json"
auth = json.load(open(AUTH_PATH))["binance"]
api_key = auth["api_key"]
api_secret = auth["api_secret"]

def signed_request(params, method="GET", path="/api/v3/account"):
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 60000
    query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sig = hmac.new(api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f"https://api.binance.com{path}?{query}&signature={sig}"
    req = urllib.request.Request(url, method=method)
    req.add_header("X-MBX-APIKEY", api_key)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15).read())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()[:300]}
    except Exception as e:
        return {"_error": str(e)[:300]}

def get_exchange_info(symbols):
    sym_str = '["' + '","'.join(symbols) + '"]'
    url = f"https://api.binance.com/api/v3/exchangeInfo?symbols={urllib.request.quote(sym_str)}"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=10).read())
        info = {}
        for s in data["symbols"]:
            sym = s["symbol"]
            lot = [f for f in s["filters"] if f["filterType"] == "LOT_SIZE"][0]
            step = float(lot["stepSize"])
            min_qty = float(lot["minQty"])
            info[sym] = {"stepSize": step, "minQty": min_qty}
        return info
    except Exception as e:
        print(f"Exchange info error: {e}")
        return {}

def round_step(qty, step_size):
    if step_size == 0:
        return qty
    precision = max(0, -int(math.floor(math.log10(step_size))))
    return round(math.floor(qty / step_size) * step_size, precision)

def get_price(symbol):
    req = urllib.request.Request(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
    return float(json.loads(urllib.request.urlopen(req, timeout=5).read())["price"])

# === Main ===
print(f"=== A4 Execution Node === {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()+8*3600))} BJT")

# Get exchange info for LOT_SIZE
info = get_exchange_info(["PEPEUSDT","PENGUUSDT","DYMUSDT","UNIUSDT","BIOUSDT","XLMUSDT"])
print(f"Exchange info: {json.dumps(info, indent=2)}")

# Get balance
data = signed_request({})
if "_error" in data:
    print(f"Balance error: {data}")
    sys.exit(1)

bal = {x["asset"]: float(x["free"]) + float(x["locked"]) for x in data["balances"]}
print(f"\nUSDT: ${bal.get('USDT',0):.2f}")

for asset in ["XLM","TIA","OPEN","PEPE","PENGU","DYM","UNI"]:
    qty = bal.get(asset, 0)
    if qty > 0:
        pr = get_price(f"{asset}USDT")
        print(f"  {asset}: {qty:.4f} x ${pr:.6f} = ${qty*pr:.2f}")

# Sell PEPE, PENGU, DYM, UNI
SELLS = ["PEPE","PENGU","DYM","UNI"]

for asset in SELLS:
    qty = bal.get(asset, 0)
    if qty <= 0:
        print(f"\n{asset}: 无持仓")
        continue
    
    sym = f"{asset}USDT"
    pr = get_price(sym)
    val = qty * pr
    print(f"\n{asset}: {qty:.6f} x ${pr:.6f} = ${val:.2f}")
    
    if val < 2:
        print(f"  金额<$2，跳过")
        continue
    
    si = info.get(sym, {})
    step = si.get("stepSize", 1)
    adj_qty = round_step(qty, step)
    if adj_qty <= 0:
        print(f"  调整后数量为0，跳过")
        continue
    
    print(f"  LOT_SIZE step={step}, 调整后={adj_qty:.6f}")
    result = signed_request({
        "symbol": sym, "side": "SELL", "type": "MARKET",
        "quantity": adj_qty, "newOrderRespType": "FULL"
    }, method="POST", path="/api/v3/order")
    
    if "_error" in result:
        print(f"  ❌ 失败: {result['_error']} {result.get('_msg','')[:150]}")
    elif result.get("status") == "FILLED":
        eq = float(result.get("executedQty", 0))
        cq = float(result.get("cummulativeQuoteQty", 0))
        print(f"  ✅ 卖出 {eq:.4f} @ ${cq/eq:.6f} = ${cq:.2f}")
    else:
        print(f"  ⚠️ 状态: {result.get('status','?')} {json.dumps(result)[:200]}")

# Check USDT after sells
time.sleep(1)
data2 = signed_request({})
bal2 = {x["asset"]: float(x["free"]) + float(x["locked"]) for x in data2["balances"]}
usdt_now = bal2.get("USDT", 0)
print(f"\n=== USDT after sells: ${usdt_now:.2f} ===")

# Buy BIO
if usdt_now >= 5:
    buy_usdt = min(usdt_now * 0.30, 25.0)
    buy_usdt = max(buy_usdt, 5.0)
    
    sym = "BIOUSDT"
    si = info.get(sym, {})
    step = si.get("stepSize", 0.1)
    
    # For MARKET buy with quoteOrderQty, need to adjust qty to LOT_SIZE
    bio_price = get_price(sym)
    raw_qty = buy_usdt / bio_price
    adj_qty = round_step(raw_qty, step)
    adj_buy_usdt = adj_qty * bio_price
    
    print(f"\nBIO: 买入 ${buy_usdt:.2f} → 调整后 {adj_qty:.4f} @ ${bio_price:.6f} = ${adj_buy_usdt:.2f}")
    
    if adj_qty > si.get("minQty", 0):
        result = signed_request({
            "symbol": sym, "side": "BUY", "type": "MARKET",
            "quantity": adj_qty, "newOrderRespType": "FULL"
        }, method="POST", path="/api/v3/order")
        
        if "_error" in result:
            print(f"  ❌ 失败: {result['_error']} {result.get('_msg','')[:150]}")
        elif result.get("status") == "FILLED":
            eq = float(result.get("executedQty", 0))
            cq = float(result.get("cummulativeQuoteQty", 0))
            print(f"  ✅ 买入 {eq:.4f} @ ${cq/eq:.6f} = ${cq:.2f}")
        else:
            print(f"  ⚠️ 状态: {result.get('status','?')}")
    else:
        print(f"  数量小于最小要求，跳过")
else:
    print(f"USDT不足(${usdt_now:.2f})")

# Final
time.sleep(1)
data3 = signed_request({})
bal3 = {x["asset"]: float(x["free"]) + float(x["locked"]) for x in data3["balances"]}
print(f"\n=== Final ===")
print(f"USDT: ${bal3.get('USDT',0):.2f}")
for asset in ["XLM","TIA","OPEN","PEPE","PENGU","DYM","UNI","BIO"]:
    qty = bal3.get(asset, 0)
    if qty > 0:
        pr = get_price(f"{asset}USDT") if asset != "BIO" else 0
        if asset == "BIO":
            pr = get_price("BIOUSDT")
        print(f"  {asset}: {qty:.4f} x ${pr:.6f} = ${qty*pr:.2f}")

print("\n✅ 执行完成")
