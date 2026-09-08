#!/usr/bin/env python3
"""ZQ简化版选币+执行器 — 单币单仓，每小时运行一次"""
import json, hashlib, hmac, time, math, os, sys

CAPITAL_TOTAL = 198.0
RISK_PER_TRADE = 0.05
STOP_LOSS_PCT = 0.03
TAKE_PROFIT_PCT = 0.08
MAX_POSITIONS = 1
LOG_PATH = os.path.expanduser("~/zq_web4_trading_system/data/trades/simple_strategy.csv")

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
    except Exception as e:
        return {"_error": str(e)[:200]}

def public_get(symbol, interval="1h", limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15, context=CTX).read())
    except:
        return None

def rsi(closes, period=14):
    gains, losses = 0, 0
    for i in range(1, period+1):
        diff = closes[-i] - closes[-i-1]
        if diff >= 0: gains += diff
        else: losses -= diff
    avg_gain = gains/period
    avg_loss = losses/period
    rs = avg_gain/avg_loss if avg_loss else 100
    return 100 - 100/(1+rs)

def ema(closes, period):
    k = 2/(period+1)
    ema_val = sum(closes[:period])/period
    for c in closes[period:]:
        ema_val = c*k + ema_val*(1-k)
    return ema_val

if __name__ == "__main__":
    acct = api_call({})
    if "_error" in acct:
        print(f"❌ 账户查询失败: {acct['_error']}")
        sys.exit(1)
    
    balances = {b["asset"]: float(b["free"]) for b in acct["balances"] if float(b["free"]) > 0.001}
    usdt = balances.get("USDT", 0)
    
    # 过滤主要持仓（>$1）
    holdings = {k:v for k,v in balances.items() if k != "USDT" and v > 0}
    price_symbols = [s+"USDT" for s in holdings.keys() if s not in ["USDT","ETH","BTC"]]
    
    # 尝试用ETH
    klines = public_get("ETHUSDT")
    if not klines:
        print("❌ 无法获取K线（网络？）")
        sys.exit(1)
    
    closes = [float(k[4]) for k in klines]
    rsi_val = rsi(closes)
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    cp = closes[-1]
    
    print(f"📊 ETH: ${cp:.2f} RSI={rsi_val:.1f} EMA20=${ema20:.2f} EMA50=${ema50:.2f}")
    print(f"📊 USDT可用: ${usdt:.2f}")
    
    if rsi_val < 30 and cp > ema20 and usdt > 10:
        size = min(CAPITAL_TOTAL * RISK_PER_TRADE, usdt * 0.5)
        qty = math.floor(size / cp * 1000) / 1000
        if qty * cp >= 5:
            print(f"✅ 信号: RSI超卖({rsi_val:.1f}) + 价>EMA20 → 可买${size:.2f} ETH")
            # 尝试执行买入
            buy_params = {
                "symbol": "ETHUSDT",
                "side": "BUY",
                "type": "MARKET",
                "quoteOrderQty": round(size, 2)
            }
            result = api_call(buy_params, "POST", "/api/v3/order")
            if "_error" in result:
                print(f"❌ 买入失败: {result['_error']}")
            else:
                print(f"✅ 买入 ETH: ${size:.2f} @ 市价")
                # 设止损单
                stop_qty = float(result.get("executedQty", qty))
                if stop_qty > 0:
                    stop_price = round(cp * (1 - STOP_LOSS_PCT), 2)
                    stop_params = {
                        "symbol": "ETHUSDT",
                        "side": "SELL",
                        "type": "STOP_LOSS_LIMIT",
                        "quantity": stop_qty,
                        "stopPrice": stop_price,
                        "price": stop_price,
                        "timeInForce": "GTC"
                    }
                    stop_res = api_call(stop_params, "POST", "/api/v3/order")
                    if "_error" in stop_res:
                        print(f"⚠️ 止损单失败: {stop_res['_error']}")
                    else:
                        print(f"✅ 止损单设置: ${stop_price} (${size:.2f})")
        else:
            print(f"⏳ 金额${size:.2f}不足MIN_NOTIONAL($5)")
    elif usdt < 10:
        print("⏳ USDT不足$10")
    else:
        print(f"⏳ 无信号: RSI={rsi_val:.1f}(需<30)")
    
    print(f"=== 简化策略执行完毕 ===")
