#!/usr/bin/env python3
"""Execute a Binance market buy using API keys from config/auth.json"""
import json, hashlib, hmac, time, urllib.request, urllib.parse, sys

ZQ_ROOT = "/Users/lidaosong/zq_web4_trading_system"
with open(f"{ZQ_ROOT}/config/auth.json") as f:
    creds = json.load(f)["binance"]

API_KEY = creds["api_key"]
API_SECRET = creds["api_secret"]

def binance_request(method: str, path: str, params: dict = None) -> dict:
    """Signed Binance API request"""
    if params is None:
        params = {}
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 10000
    
    query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    query += f"&signature={signature}"
    
    url = f"https://api.binance.com{path}?{query}"
    req = urllib.request.Request(url, method=method)
    req.add_header("X-MBX-APIKEY", API_KEY)
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"error": str(e)}

# Check what we're working with
action = sys.argv[1] if len(sys.argv) > 1 else "check"

if action == "check":
    # Check account status
    r = binance_request("GET", "/api/v3/account")
    if "error" in r:
        print(f"❌ {r['error']}")
    else:
        balances = {b["asset"]: float(b["free"]) for b in r.get("balances", []) if float(b["free"]) > 0}
        usdt = balances.get("USDT", 0)
        print(f"USDT: ${usdt:.2f}")
        for asset, qty in sorted(balances.items()):
            if asset != "USDT" and qty > 0:
                print(f"  {asset}: {qty}")

elif action == "buy":
    symbol = sys.argv[2]
    usdt_amount = float(sys.argv[3])
    r = binance_request("POST", "/api/v3/order", {
        "symbol": symbol,
        "side": "BUY",
        "type": "MARKET",
        "quoteOrderQty": str(usdt_amount),
    })
    if "error" in r:
        print(f"❌ BUY {symbol} ${usdt_amount}: {r['error']}")
    else:
        fills = r.get("fills", [])
        avg_price = sum(float(f["price"]) * float(f["qty"]) for f in fills) / sum(float(f["qty"]) for f in fills) if fills else 0
        total_qty = sum(float(f["qty"]) for f in fills)
        print(f"✅ BUY {symbol} ${usdt_amount}: {total_qty} @ ${avg_price:.4f} | status={r.get('status','?')}")

elif action == "sell":
    symbol = sys.argv[2]
    qty = float(sys.argv[3])
    r = binance_request("POST", "/api/v3/order", {
        "symbol": symbol,
        "side": "SELL",
        "type": "MARKET",
        "quantity": str(qty),
    })
    if "error" in r:
        print(f"❌ SELL {symbol} {qty}: {r['error']}")
    else:
        fills = r.get("fills", [])
        avg_price = sum(float(f["price"]) * float(f["qty"]) for f in fills) / sum(float(f["qty"]) for f in fills) if fills else 0
        total_qty = sum(float(f["qty"]) for f in fills)
        total_usdt = avg_price * total_qty
        print(f"✅ SELL {symbol} {total_qty} @ ${avg_price:.4f} = ${total_usdt:.2f} | status={r.get('status','?')}")
