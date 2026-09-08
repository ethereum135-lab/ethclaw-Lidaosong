#!/usr/bin/env python3
"""A4 Blade Execution - Sell FIDA (hard stop), Buy DYDX (best momentum)"""
import json, hashlib, hmac, time, urllib.request, urllib.error, sys, math

AUTH_PATH = "/Users/lidaosong/zq_web4_trading_system/config/auth.json"
auth = json.load(open(AUTH_PATH))["binance"]
api_key, api_secret = auth["api_key"], auth["api_secret"]

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

def public_get(path, params=None):
    if params is None: params = {}
    qs = "&".join(f"{k}={v}" for k,v in sorted(params.items()))
    url = f"https://api.binance.com{path}?{qs}" if qs else f"https://api.binance.com{path}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=10).read())
    except Exception as e:
        return {"_error": str(e)[:200]}

def round_step(qty, step_size):
    if step_size == 0: return qty
    precision = max(0, -int(math.floor(math.log10(step_size))))
    return round(math.floor(qty / step_size) * step_size, precision)

ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()+8*3600))
print(f"=== A4 Blade Execution === {ts} BJT")

# 1. Get exchange info for FIDA and DYDX
info = public_get("/api/v3/exchangeInfo", {"symbols": '["FIDAUSDT","DYDXUSDT"]'})
if "_error" in info:
    print(f"ERROR getting exchange info: {info}")
    sys.exit(1)

lot_info = {}
for s in info.get("symbols", []):
    sym = s["symbol"]
    for f in s.get("filters", []):
        if f["filterType"] == "LOT_SIZE":
            lot_info[sym] = {"stepSize": float(f["stepSize"]), "minQty": float(f["minQty"])}
            break
    min_notional = None
    for f in s.get("filters", []):
        if f["filterType"] == "MIN_NOTIONAL":
            min_notional = float(f.get("minNotional", f.get("notional", "10")))
            break
    if min_notional:
        lot_info[sym]["minNotional"] = min_notional

print(f"LOT info: {json.dumps(lot_info, indent=2)}")

# 2. Get account balance
acct = signed_request({})
if "_error" in acct:
    print(f"ERROR getting account: {acct}")
    sys.exit(1)

bal = {b["asset"]: float(b["free"]) for b in acct["balances"] if float(b["free"]) > 0 or float(b["locked"]) > 0}
print(f"\nBalances:")
for a in sorted(bal.keys()):
    v = bal[a]
    if v > 0:
        print(f"  {a}: {v:.4f}")

usdt_free = bal.get("USDT", 0)
print(f"\nUSDT free: ${usdt_free:.2f}")

# 3. Get FIDA current holdings
fida_qty = bal.get("FIDA", 0)
if fida_qty > 0:
    fida_price = public_get("/api/v3/ticker/price", {"symbol": "FIDAUSDT"})
    fida_p = float(fida_price["price"])
    fida_val = fida_qty * fida_p
    print(f"\nFIDA: {fida_qty:.4f} @ ${fida_p:.6f} = ${fida_val:.2f}")
    
    # SELL FIDA - market sell
    fida_step = lot_info.get("FIDAUSDT", {}).get("stepSize", 0.001)
    sell_qty = round_step(fida_qty, fida_step)
    
    if sell_qty >= lot_info.get("FIDAUSDT", {}).get("minQty", 0.001):
        print(f"\n--- SELL FIDAUSDT ---")
        print(f"Qty: {sell_qty} (stop loss triggered: -3.04%, F&G=14)")
        sell_params = {"symbol": "FIDAUSDT", "side": "SELL", "type": "MARKET", "quantity": sell_qty}
        sell_resp = signed_request(sell_params, "POST", "/api/v3/order")
        if "_error" in sell_resp:
            print(f"SELL ERROR: {sell_resp}")
        else:
            print(f"SOLD! Fills: {json.dumps(sell_resp.get('fills', []), indent=2)}")
            print(f"Executed qty: {sell_resp.get('executedQty', 'N/A')}")
            # Update USDT
            for fill in sell_resp.get("fills", []):
                usdt_free += float(fill["qty"]) * float(fill["price"])
    else:
        print(f"FIDA qty {sell_qty} below min, skipping sell")
else:
    print("No FIDA position found")

# 4. BUY DYDX
dydx_price = public_get("/api/v3/ticker/price", {"symbol": "DYDXUSDT"})
dydx_p = float(dydx_price["price"])
print(f"\nDYDX current price: ${dydx_p:.6f}")

# Position size: F&G=14 → 7.5% × range mult 0.7
# 【2026-06-23 策略修正】闲置>50%时跳过FNG缩仓，直接70%部署
# Check idle rate from account
usdt_free = bal.get("USDT", 0)
total_bal = sum(float(b["free"]) for b in acct["balances"] if float(b["free"]) > 0)
# Find total equity estimate
# Approximate: USDT + known positions
position_pct = 0.075 * 0.7  # 5.25%
if usdt_free > 0 and total_bal > 0:
    idle_rate = usdt_free / total_bal
    if idle_rate > 0.5:
        # Override: deploy 70% across 3 positions
        position_pct = 0.70 / 3  # ~23% per position
        print(f"[FNG覆盖] 闲置{idle_rate*100:.0f}%>50% -> 单仓{position_pct*100:.0f}% (70%÷3)")
    else:
        print(f"[FNG正常] 闲置{idle_rate*100:.0f}% -> 单仓{position_pct*100:.0f}% (7.5%×0.7)")
buy_usdt = usdt_free * position_pct
dydx_step = lot_info.get("DYDXUSDT", {}).get("stepSize", 0.001)
dydx_min_qty = lot_info.get("DYDXUSDT", {}).get("minQty", 0.001)
dydx_min_notional = lot_info.get("DYDXUSDT", {}).get("minNotional", 10)

dydx_qty = round_step(buy_usdt / dydx_p, dydx_step)
dydx_notional = dydx_qty * dydx_p

print(f"\n--- BUY DYDXUSDT ---")
print(f"Budget: ${buy_usdt:.2f} (USDT {usdt_free:.2f} × 7.5% × 0.7)")
print(f"Qty: {dydx_qty} @ ${dydx_p:.6f} = ${dydx_notional:.2f}")

if dydx_qty >= dydx_min_qty and dydx_notional >= dydx_min_notional:
    buy_params = {"symbol": "DYDXUSDT", "side": "BUY", "type": "MARKET", "quoteOrderQty": round(buy_usdt, 2)}
    buy_resp = signed_request(buy_params, "POST", "/api/v3/order")
    if "_error" in buy_resp:
        print(f"BUY ERROR: {buy_resp}")
    else:
        print(f"BOUGHT! Fills: {json.dumps(buy_resp.get('fills', []), indent=2)}")
        print(f"Executed qty: {buy_resp.get('executedQty', 'N/A')}")
        print(f"Cummulative quote qty: {buy_resp.get('cummulativeQuoteQty', 'N/A')}")
else:
    print(f"SKIP: qty {dydx_qty} < min {dydx_min_qty} or notional {dydx_notional:.2f} < min {dydx_min_notional}")

# 5. Final balance check
time.sleep(1)
acct2 = signed_request({})
bal2 = {b["asset"]: float(b["free"]) for b in acct2["balances"] if float(b["free"]) > 0 or float(b["locked"]) > 0}
print(f"\n=== Final Balances ===")
total = 0
for a in ["USDT", "FIDA", "DYDX", "ZRO", "LAYER"]:
    q = bal2.get(a, 0)
    if q > 0 and a != "USDT":
        try:
            pr = public_get("/api/v3/ticker/price", {"symbol": f"{a}USDT"})
            p = float(pr["price"])
            v = q * p
            total += v
            print(f"  {a}: {q:.4f} × ${p:.6f} = ${v:.2f}")
        except:
            print(f"  {a}: {q:.4f} (price fetch failed)")
    elif a == "USDT":
        total += q
        print(f"  USDT: ${q:.2f}")
print(f"  TOTAL: ${total:.2f}")

print(f"\n=== A4 Node Complete ===")
