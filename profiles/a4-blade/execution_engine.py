#!/usr/bin/env python3
"""
A4 交易官 — 执行引擎脚本
从config/auth.json读取Binance API密钥，执行交易。
"""
import json, os, time, hmac, hashlib, requests
from urllib.parse import urlencode

# 路径
BASE = os.path.dirname(os.path.abspath(__file__))
AUTH_PATH = os.path.join(BASE, "../../config/auth.json")

def load_auth():
    """加载Binance API密钥"""
    with open(AUTH_PATH) as f:
        auth = json.load(f)
    return auth["binance"]["api_key"], auth["binance"]["api_secret"]

def sign_request(params, secret):
    """HMAC SHA256签名"""
    query = urlencode(params)
    signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature
    return params

def get_balance(api_key, secret):
    """查询USDT余额"""
    params = {"timestamp": int(time.time() * 1000)}
    params = sign_request(params, secret)
    headers = {"X-MBX-APIKEY": api_key}
    resp = requests.get(
        "https://api.binance.com/api/v3/account",
        headers=headers, params=params, timeout=10
    )
    data = resp.json()
    for bal in data.get("balances", []):
        if bal["asset"] == "USDT":
            return float(bal["free"])
    return 0.0

def get_price(symbol, use_binance_auth=False, api_key=None, secret=None):
    """查询当前价格 — 多源兜底"""
    sym = symbol.upper()

    # 方案1：OKX公开API（永续合约）
    try:
        resp = requests.get(
            f"https://www.okx.com/api/v5/market/ticker?instId={sym}-USDT-SWAP",
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "0":
                return float(data["data"][0]["last"])
    except:
        pass

    # 方案2：OKX现货
    try:
        resp = requests.get(
            f"https://www.okx.com/api/v5/market/ticker?instId={sym}-USDT",
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "0":
                return float(data["data"][0]["last"])
    except:
        pass

    # 方案3：Binance认证查询（避开地区限制）
    if api_key and secret:
        params = {
            "symbol": f"{sym}USDT",
            "timestamp": int(time.time() * 1000),
        }
        params = sign_request(params, secret)
        headers = {"X-MBX-APIKEY": api_key}
        resp = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            headers=headers, params=params, timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            if "price" in data:
                return float(data["price"])

    # 方案4：CoinGecko（兜底）
    try:
        resp = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={sym.lower()}&vs_currencies=usd",
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            if sym.lower() in data:
                return float(data[sym.lower()]["usd"])
    except:
        pass

    raise Exception(f"所有价格数据源均不可用 ({sym})")

def buy_market(api_key, secret, symbol, usdt_amount):
    """市价买入"""
    params = {
        "symbol": f"{symbol}USDT",
        "side": "BUY",
        "type": "MARKET",
        "quoteOrderQty": str(usdt_amount),
        "timestamp": int(time.time() * 1000),
    }
    params = sign_request(params, secret)
    headers = {"X-MBX-APIKEY": api_key}
    resp = requests.post(
        "https://api.binance.com/api/v3/order",
        headers=headers, params=params, timeout=10
    )
    return resp.json()

def sell_market(api_key, secret, symbol, quantity):
    """市价卖出"""
    params = {
        "symbol": f"{symbol}USDT",
        "side": "SELL",
        "type": "MARKET",
        "quantity": str(quantity),
        "timestamp": int(time.time() * 1000),
    }
    params = sign_request(params, secret)
    headers = {"X-MBX-APIKEY": api_key}
    resp = requests.post(
        "https://api.binance.com/api/v3/order",
        headers=headers, params=params, timeout=10
    )
    return resp.json()

if __name__ == "__main__":
    # 测试模式
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        api_key, secret = load_auth()
        print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
        bal = get_balance(api_key, secret)
        print(f"USDT余额: ${bal:.2f}")
        if len(sys.argv) > 2:
            sym = sys.argv[2].upper()
            try:
                price = get_price(sym, api_key=api_key, secret=secret)
                print(f"{sym} 价格: ${price:.6f}")
            except Exception as e:
                print(f"{sym} 价格: 查询失败 - {e}")
