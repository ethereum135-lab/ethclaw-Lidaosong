#!/usr/bin/env python3
"""A4 Blade — 通用卖出执行脚本。直接调Binance API，无需SSH。
用法: python3 tools/a4_execute_sell.py <SYMBOL> [pct=100]
示例: python3 tools/a4_execute_sell.py ZRO 100    (全卖)
       python3 tools/a4_execute_sell.py DYDX 50    (卖一半)
"""
import json, hashlib, hmac, time, urllib.request, urllib.error, sys, math, ssl

AUTH_PATH = "/Users/lidaosong/zq_web4_trading_system/config/auth.json"
auth = json.load(open(AUTH_PATH))["binance"]
API_KEY, API_SECRET = auth["api_key"], auth["api_secret"]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def signed(params, method="GET", path="/api/v3/account"):
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 60000
    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sig = hmac.new(API_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
    url = f"https://api.binance.com{path}?{qs}&signature={sig}"
    req = urllib.request.Request(url, method=method)
    req.add_header("X-MBX-APIKEY", API_KEY)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15, context=CTX).read())
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
        return json.loads(urllib.request.urlopen(req, timeout=10, context=CTX).read())
    except Exception as e:
        return {"_error": str(e)[:200]}

def round_step(qty, step_size):
    if step_size <= 0: return qty
    precision = max(0, -int(math.floor(math.log10(step_size))))
    return round(math.floor(qty / step_size) * step_size, precision)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 tools/a4_execute_sell.py <SYMBOL> [pct=100]")
        sys.exit(1)
    
    symbol = sys.argv[1].upper().replace("USDT", "") + "USDT"
    sell_pct = float(sys.argv[2]) / 100.0 if len(sys.argv) > 2 else 1.0
    sell_pct = max(0.01, min(1.0, sell_pct))
    
    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()+8*3600))
    print(f"=== A4 SELL === {symbol} {sell_pct*100:.0f}% @ {ts} BJT")
    
    # 1. Get account balance for this asset
    acct = signed({})
    if "_error" in acct:
        print(f"❌ 账户查询失败: {acct}")
        sys.exit(1)
    
    balances = {b["asset"]: float(b["free"]) for b in acct["balances"] if float(b["free"]) > 0}
    base = symbol.replace("USDT", "")
    total_qty = balances.get(base, 0)
    
    if total_qty <= 0:
        print(f"❌ 没有 {base} 持仓")
        sys.exit(1)
    
    sell_qty_raw = total_qty * sell_pct
    
    # 2. Get exchange info for LOT_SIZE
    info = public_get("/api/v3/exchangeInfo", {"symbol": symbol})
    if "_error" in info:
        print(f"❌ exchangeInfo失败: {info}")
        sys.exit(1)
    
    sym_info = info.get("symbols", [{}])[0]
    step_size = 0.001
    min_qty = 0.001
    for f in sym_info.get("filters", []):
        if f["filterType"] == "LOT_SIZE":
            step_size = float(f["stepSize"])
            min_qty = float(f["minQty"])
            break
    
    sell_qty = round_step(sell_qty_raw, step_size)
    if sell_qty < min_qty:
        print(f"❌ 卖出数量 {sell_qty} < 最小 {min_qty}")
        sys.exit(1)
    
    # 3. Get price for display
    price_data = public_get("/api/v3/ticker/price", {"symbol": symbol})
    price = float(price_data["price"]) if "_error" not in price_data else 0
    
    print(f"持仓: {total_qty:.6f} × ${price:.6f} = ${total_qty*price:.2f}")
    print(f"卖出: {sell_qty:.6f} (≈${sell_qty*price:.2f})")
    
    # 4. Execute sell
    sell_params = {
        "symbol": symbol, "side": "SELL", "type": "MARKET",
        "quantity": sell_qty, "newOrderRespType": "FULL"
    }
    resp = signed(sell_params, "POST", "/api/v3/order")
    
    if "_error" in resp:
        print(f"❌ 卖出失败: {resp}")
        sys.exit(1)
    
    exec_qty = float(resp.get("executedQty", 0))
    exec_cost = float(resp.get("cummulativeQuoteQty", 0))
    avg_price = exec_cost / exec_qty if exec_qty > 0 else 0
    
    print(f"✅ {symbol} 卖出成功!")
    print(f"   数量: {exec_qty:.6f}")
    print(f"   均价: ${avg_price:.6f}")
    print(f"   收入: ${exec_cost:.2f} USDT")
    print(f"   状态: {resp.get('status', '?')}")
    
    # 5. Verify
    time.sleep(1)
    acct2 = signed({})
    bal2 = {b["asset"]: float(b["free"]) for b in acct2["balances"] if float(b["free"]) > 0}
    usdt_now = bal2.get("USDT", 0)
    remaining = bal2.get(base, 0)
    print(f"\n余额验证:")
    print(f"   USDT: ${usdt_now:.2f}")
    print(f"   {base}: {remaining:.6f} (剩余)")
    print(f"\n=== DONE ===")
