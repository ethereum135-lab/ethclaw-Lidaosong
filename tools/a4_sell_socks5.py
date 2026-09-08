#!/usr/bin/env python3
"""A4 Blade — 紧急卖出(SOCKS5版)"""
import json, hashlib, hmac, time, sys, math
import requests

AUTH_PATH = "/Users/lidaosong/zq_web4_trading_system/config/auth.json"
auth = json.load(open(AUTH_PATH))["binance"]
API_KEY, API_SECRET = auth["api_key"], auth["api_secret"]

S = requests.Session()
S.proxies.update({"http": "socks5h://127.0.0.1:1080", "https": "socks5h://127.0.0.1:1080"})
S.headers.update({"User-Agent": "Mozilla/5.0", "X-MBX-APIKEY": API_KEY})

def signed(params, method="GET", path="/api/v3/account"):
    try:
        st = S.get("https://api.binance.com/api/v3/time", timeout=5).json()
        params["timestamp"] = st["serverTime"]
    except:
        params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 60000
    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    params["signature"] = hmac.new(API_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
    sig = params.pop("signature")
    qs2 = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    url = f"https://api.binance.com{path}?{qs2}&signature={sig}"
    if method == "GET":
        r = S.get(url, timeout=15)
    else:
        r = S.post(url, timeout=15)
    if r.status_code >= 400:
        return {"_error": r.status_code, "_msg": r.text[:300]}
    return r.json()

def public_get(path, params=None):
    if params is None: params = {}
    r = S.get(f"https://api.binance.com{path}", params=params, timeout=10)
    return r.json()

def round_step(qty, step_size):
    if step_size <= 0: return qty
    precision = max(0, -int(math.floor(math.log10(step_size))))
    return round(math.floor(qty / step_size) * step_size, precision)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 tools/a4_sell_socks5.py <SYMBOL> [pct=100]")
        sys.exit(1)
    symbol = sys.argv[1].upper().replace("USDT", "") + "USDT"
    sell_pct = float(sys.argv[2])/100.0 if len(sys.argv) > 2 else 1.0
    sell_pct = max(0.01, min(1.0, sell_pct))
    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()+8*3600))
    print(f"=== A4 SELL (SOCKS5) === {symbol} {sell_pct*100:.0f}% @ {ts} BJT")
    
    acct = signed({})
    if "_error" in acct:
        print(f"❌ 账户查询失败: {acct}")
        sys.exit(1)
    base = symbol.replace("USDT", "")
    total_qty = float(acct.get(base, 0) if isinstance(acct, dict) else 0)
    total_qty = 0
    for b in acct.get("balances", []):
        if b["asset"] == base:
            total_qty = float(b["free"])
            break
    if total_qty <= 0:
        print(f"❌ 没有 {base} 持仓")
        sys.exit(1)
    sell_qty_raw = total_qty * sell_pct
    
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
    
    price_data = public_get("/api/v3/ticker/price", {"symbol": symbol})
    price = float(price_data["price"]) if "_error" not in price_data else 0
    print(f"持仓: {total_qty:.6f} × ${price:.6f} = ${total_qty*price:.2f}")
    print(f"卖出: {sell_qty:.6f} (≈${sell_qty*price:.2f})")
    
    sell_params = {"symbol": symbol, "side": "SELL", "type": "MARKET",
                   "quantity": sell_qty, "newOrderRespType": "FULL"}
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
    
    time.sleep(1)
    acct2 = signed({})
    usdt_now = 0
    remaining = 0
    for b in acct2.get("balances", []):
        if b["asset"] == "USDT": usdt_now = float(b["free"])
        if b["asset"] == base: remaining = float(b["free"])
    print(f"\n余额验证: USDT: ${usdt_now:.2f}, {base}: {remaining:.6f}")
    print(f"=== DONE ===")
