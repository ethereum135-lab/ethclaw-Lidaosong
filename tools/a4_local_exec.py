#!/usr/bin/env python3
"""A4 local execution via SOCKS5 proxy — Path B fallback when SSH to AWS is down"""
import json, sys, hashlib, hmac, time

PROXY = "socks5h://127.0.0.1:1080"
ZQ_ROOT = "/Users/lidaosong/zq_web4_trading_system"

with open(f"{ZQ_ROOT}/config/auth.json") as f:
    creds = json.load(f)["binance"]

API_KEY = creds["api_key"]
API_SECRET = creds["api_secret"]

import requests

def api_request(method="GET", path="/api/v3/account", params=None, data=None):
    if params is None:
        params = {}
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 60000
    query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sig = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f"https://api.binance.com{path}?{query}&signature={sig}"
    headers = {"X-MBX-APIKEY": API_KEY, "User-Agent": "Mozilla/5.0"}
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, proxies={"https": PROXY, "http": PROXY}, timeout=15)
        else:
            resp = requests.post(url, headers=headers, data=data, proxies={"https": PROXY, "http": PROXY}, timeout=15)
        return resp.json()
    except Exception as e:
        return {"error": str(e)[:300]}

def get_balance():
    data = api_request("GET", "/api/v3/account")
    if "error" in data:
        return {"error": data["error"]}
    return {x["asset"]: {"free": float(x["free"]), "locked": float(x["locked"])}
            for x in data["balances"] if float(x["free"]) + float(x["locked"]) > 0}

def market_sell(symbol, quantity):
    params = {
        "symbol": symbol,
        "side": "SELL",
        "type": "MARKET",
        "quantity": quantity,
        "newOrderRespType": "FULL"
    }
    return api_request("POST", "/api/v3/order", params)

def market_buy_quote(symbol, quote_order_qty):
    params = {
        "symbol": symbol,
        "side": "BUY",
        "type": "MARKET",
        "quoteOrderQty": quote_order_qty,
        "newOrderRespType": "FULL"
    }
    return api_request("POST", "/api/v3/order", params)

def get_price(symbol):
    try:
        resp = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
                           proxies={"https": PROXY, "http": PROXY}, timeout=5)
        return float(resp.json()["price"])
    except Exception as e:
        return {"error": str(e)[:200]}

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    
    if action == "check":
        bal = get_balance()
        if "error" in bal:
            print(f"ERROR: {bal['error']}")
            sys.exit(1)
        print("=== Local Balance (via SOCKS5 proxy) ===")
        usdt = bal.get("USDT", {})
        print(f"USDT: {usdt.get('free', 0):.2f} free, {usdt.get('locked', 0):.2f} locked")
        for asset, info in sorted(bal.items()):
            total = info["free"] + info["locked"]
            if total > 1 and asset != "USDT":
                price = get_price(f"{asset}USDT")
                print(f"{asset:10s} {info['free']:>12.4f} x ${price:<10.4f} = ${total * price:.2f}")
        total_value = usdt.get("free", 0)
        for asset, info in bal.items():
            if asset == "USDT": continue
            total = info["free"] + info["locked"]
            if total > 0.001:
                try:
                    p = get_price(f"{asset}USDT")
                    total_value += total * p
                except:
                    pass
        print(f"\nTotal equity: ${total_value:.2f}")
        
    elif action == "sell":
        symbol = sys.argv[2]
        qty = float(sys.argv[3])
        print(f"Selling {qty} {symbol}...")
        result = market_sell(symbol, qty)
        print(json.dumps(result, indent=2)[:500])
        
    elif action == "buy":
        symbol = sys.argv[2]
        usdt_amount = float(sys.argv[3])
        price = get_price(symbol)
        print(f"Buying ${usdt_amount:.2f} of {symbol} @ ~${price:.6f}")
        result = market_buy_quote(symbol, usdt_amount)
        print(json.dumps(result, indent=2)[:500])
        
    elif action == "price":
        symbol = sys.argv[2]
        p = get_price(symbol)
        print(f"{symbol}: ${p:.6f}")
