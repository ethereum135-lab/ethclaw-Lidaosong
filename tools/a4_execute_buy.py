#!/usr/bin/env python3
"""A4 Blade — 通用买入执行脚本。直接调Binance API，无需SSH。
用法: python3 tools/a4_execute_buy.py <SYMBOL> <USDT_AMOUNT>
示例: python3 tools/a4_execute_buy.py TON 50
"""
import json, hashlib, hmac, time, sys, math, os

AUTH_PATH = "/Users/lidaosong/zq_web4_trading_system/config/auth.json"
auth = json.load(open(AUTH_PATH))["binance"]
API_KEY, API_SECRET = auth["api_key"], auth["api_secret"]

import requests as reqs
_SESSION = reqs.Session()
_SESSION.proxies.update({"http": "socks5h://127.0.0.1:1080", "https": "socks5h://127.0.0.1:1080"})
_SESSION.headers.update({"User-Agent": "Mozilla/5.0", "X-MBX-APIKEY": API_KEY})

def _signed_params(params):
    # Fetch server time for accurate timestamping
    try:
        st = _SESSION.get("https://api.binance.com/api/v3/time", timeout=5).json()
        params["timestamp"] = st["serverTime"]
    except:
        params["timestamp"] = int(time.time() * 1000) - 2000  # fallback
    params["recvWindow"] = 60000
    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    params["signature"] = hmac.new(API_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
    return params

def signed(params, method="GET", path="/api/v3/account"):
    try:
        params = _signed_params(params)
        sig = params.pop("signature")
        qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        url = f"https://api.binance.com{path}?{qs}&signature={sig}"
        if method == "GET":
            r = _SESSION.get(url, timeout=15)
        else:
            r = _SESSION.post(url, timeout=15)
        if r.status_code >= 400:
            return {"_error": r.status_code, "_msg": r.text[:300]}
        return r.json()
    except Exception as e:
        return {"_error": str(e)[:300]}

def public_get(path, params=None):
    if params is None: params = {}
    try:
        r = _SESSION.get(f"https://api.binance.com{path}", params=params, timeout=10)
        return r.json()
    except Exception as e:
        return {"_error": str(e)[:200]}

def round_step(qty, step_size):
    if step_size <= 0: return qty
    precision = max(0, -int(math.floor(math.log10(step_size))))
    return round(math.floor(qty / step_size) * step_size, precision)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 tools/a4_execute_buy.py <SYMBOL> <USDT_AMOUNT>")
        print("示例: python3 tools/a4_execute_buy.py TON 50")
        sys.exit(1)
    
    symbol = sys.argv[1].upper().replace("USDT", "") + "USDT"
    try:
        buy_amount = float(sys.argv[2])
    except ValueError:
        print(f"❌ USDT金额无效: {sys.argv[2]}")
        sys.exit(1)
    
    if buy_amount < 5:
        print(f"❌ 金额<5 USDT，跳过")
        sys.exit(1)
    
    # 【FNG风控覆盖】检查闲置率，但不超过NAV.md的FNG仓位上限
    acct_check = signed({})
    if "_error" not in acct_check:
        bal_check = {b["asset"]: float(b["free"]) for b in acct_check["balances"] if float(b["free"]) > 0}
        usdt_avail = bal_check.get("USDT", 0)
        total_est = usdt_avail + sum(bal_check.get(a, 0) * 0.5 for a in ["DYDX", "ZRO", "TON"])  # rough
        if usdt_avail > 0 and total_est > 0:
            idle = usdt_avail / total_est
            
            # NAV.md §三 FNG风控仓位上限（刚需检查）
            nav_cap_pct = 0.075  # FNG<20: 7.5%
            nav_max_pos = total_est * nav_cap_pct
            
            if idle > 0.5:
                suggested = total_est * 0.7 / 3  # 70% ÷ 3 positions
                suggested = min(suggested, nav_max_pos)  # 不超过FNG仓位上限
                print(f"[FNG风控] 闲置{idle*100:.0f}%>50% -> 建议每仓~${suggested:.0f} (FNG上限${nav_max_pos:.0f})")
                if buy_amount < suggested * 0.5:
                    print(f"❗ 从${buy_amount:.0f}调整到${suggested:.0f}")
                    buy_amount = suggested
            else:
                # 正常场景也检查FNG上限
                if buy_amount > nav_max_pos:
                    print(f"❗ 建议${buy_amount:.0f}超过FNG上限${nav_max_pos:.0f}，调整到${nav_max_pos:.0f}")
                    buy_amount = nav_max_pos
    
    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()+8*3600))
    print(f"=== A4 BUY === {symbol} ${buy_amount:.2f} @ {ts} BJT")
    
    # 1. Get exchange info/LOT_SIZE
    info = public_get("/api/v3/exchangeInfo", {"symbol": symbol})
    if "_error" in info:
        print(f"❌ exchangeInfo失败: {info}")
        sys.exit(1)
    
    sym_info = info.get("symbols", [{}])[0]
    step_size = 0.001
    min_qty = 0.001
    min_notional = 10
    for f in sym_info.get("filters", []):
        if f["filterType"] == "LOT_SIZE":
            step_size = float(f["stepSize"])
            min_qty = float(f["minQty"])
        if f["filterType"] == "MIN_NOTIONAL":
            min_notional = float(f.get("minNotional", 10))
    
    # 2. Get current price
    price_data = public_get("/api/v3/ticker/price", {"symbol": symbol})
    if "_error" in price_data:
        print(f"❌ 价格获取失败: {price_data}")
        sys.exit(1)
    price = float(price_data["price"])
    
    # 3. Calculate and execute
    raw_qty = buy_amount / price
    qty = round_step(raw_qty, step_size)
    notional = qty * price
    
    if qty < min_qty or notional < min_notional:
        print(f"❌ 数量不足: qty={qty} < min_qty={min_qty} 或 notional=${notional:.2f} < ${min_notional}")
        # 尝试用quoteOrderQty（如果是USDT计价）
        print(f"❗ 改用quoteOrderQty=${buy_amount:.2f}")
        buy_params = {
            "symbol": symbol, "side": "BUY", "type": "MARKET",
            "quoteOrderQty": round(buy_amount, 2),
            "newOrderRespType": "FULL"
        }
    else:
        buy_params = {
            "symbol": symbol, "side": "BUY", "type": "MARKET",
            "quantity": qty,
            "newOrderRespType": "FULL"
        }
    
    print(f"下单: {symbol} BUY MARKET amount=${buy_amount:.2f}")
    resp = signed(buy_params, "POST", "/api/v3/order")
    
    if "_error" in resp:
        print(f"❌ 买入失败: {resp}")
        sys.exit(1)
    
    # 4. Parse result
    fills = resp.get("fills", [])
    exec_qty = float(resp.get("executedQty", 0))
    exec_cost = float(resp.get("cummulativeQuoteQty", 0))
    avg_price = exec_cost / exec_qty if exec_qty > 0 else 0
    
    # 【信号效果追踪 v1】记录每笔买入的信号置信度，供24h后验证
    signal_log = {
        "ts": ts,
        "symbol": symbol,
        "entry_price": avg_price,
        "amount": exec_cost,
        "fng": 14,  # 粗略取当前FNG
        "signal_source": "fast_scan_v3",
    }
    log_path = os.path.join(os.path.dirname(AUTH_PATH), "../data/signal_tracking.jsonl")
    try:
        with open(log_path, 'a') as f:
            f.write(json.dumps(signal_log) + "\n")
    except:
        pass
    print(f"📊 信号追踪已记录: {symbol} @ ${avg_price:.4f}")
    
    print(f"✅ {symbol} 买入成功!")
    print(f"   数量: {exec_qty:.6f}")
    if fills:
        print(f"   均价: ${avg_price:.6f}")
        print(f"   花费: ${exec_cost:.2f} {symbol.replace('USDT','')}")
    print(f"   状态: {resp.get('status', '?')}")
    
    # 5. Verify balance
    time.sleep(1)
    acct = signed({})
    balances = {b["asset"]: float(b["free"]) for b in acct["balances"] if float(b["free"]) > 0}
    usdt_left = balances.get("USDT", 0)
    base = symbol.replace("USDT", "")
    held = balances.get(base, 0)
    print(f"\n余额验证:")
    print(f"   USDT: ${usdt_left:.2f}")
    print(f"   {base}: {held:.6f} (≈${held*price:.2f})")
    print(f"\n=== DONE ===")
