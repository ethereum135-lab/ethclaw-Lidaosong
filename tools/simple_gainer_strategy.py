#!/usr/bin/env python3
"""涨幅榜动量策略 — FNG>20时激活。每小时跑，扫涨幅榜找刚启动的币"""
import json, hashlib, hmac, time, math, os, sys

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

def public_get(path, params=None):
    if params is None: params = {}
    qs = "&".join(f"{k}={v}" for k,v in sorted(params.items()))
    url = f"https://api.binance.com{path}?{qs}" if qs else f"https://api.binance.com{path}"
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

if __name__ == "__main__":
    # 1. 查FNG（简单替代：用Alternative.me直查）
    import urllib.request as ureq
    try:
        fng_req = ureq.urlopen("https://api.alternative.me/fng/?limit=1", timeout=10)
        fng_data = json.loads(fng_req.read())
        fng = int(fng_data["data"][0]["value"])
    except:
        fng = 20
    
    print(f"📊 FNG={fng}")
    
    if fng < 20:
        print("⏳ FNG<20→极恐模式，等simple_strategy的RSI抄底信号")
        sys.exit(0)
    
    # 2. 拉涨幅榜
    tickers = public_get("/api/v3/ticker/24hr")
    if not tickers or "_error" in str(tickers):
        print("❌ 无法获取涨幅榜")
        sys.exit(1)
    
    # 3. 过滤USDT对且量>1M
    usdt_pairs = [t for t in tickers if t["symbol"].endswith("USDT") 
                  and float(t["quoteVolume"]) > 1_000_000
                  and not any(x in t["symbol"] for x in ["UP","DOWN","BULL","BEAR","LUNA","UST"])]
    
    # 4. 找3-15%涨幅 + RSI合理
    candidates = []
    for t in usdt_pairs:
        chg = float(t["priceChangePercent"])
        vol = float(t["quoteVolume"])
        sym = t["symbol"]
        
        if 3 <= chg <= 15:
            # 查RSI
            klines = public_get("/api/v3/klines", {"symbol": sym, "interval": "1h", "limit": 50})
            if klines and len(klines) > 20:
                closes = [float(k[4]) for k in klines]
                rsi_val = rsi(closes)
                if rsi_val < 75:
                    candidates.append((sym, chg, rsi_val, vol))
    
    candidates.sort(key=lambda x: -x[1])
    
    print("\n📊 可考虑的币（3-15%涨幅 + RSI<75）:")
    for sym, chg, r, vol in candidates[:10]:
        print(f"  {sym:12s} +{chg:+.2f}% RSI={r:.1f} vol=${vol/1e6:.1f}M")
    
    # 5. 如果有候选且USDT够
    acct = api_call({})
    balances = {b["asset"]: float(b["free"]) for b in acct["balances"] if float(b["free"]) > 0.001}
    usdt = balances.get("USDT", 0)
    
    if candidates and usdt > 15:
        best = candidates[0]
        sym = best[0]
        size = min(usdt * 0.5, 15.0)
        
        print(f"\n✅ 选中最优: {sym} +{best[1]:+.2f}% RSI={best[2]:.1f}")
        print(f"   买入 ${size:.2f} → 止损-4% 止盈+8%")
        
        buy_params = {
            "symbol": sym,
            "side": "BUY",
            "type": "MARKET",
            "quoteOrderQty": round(size, 2)
        }
        result = api_call(buy_params, "POST", "/api/v3/order")
        if "_error" in result:
            print(f"❌ 买入失败: {result['_error']}")
        else:
            print(f"✅ 买入 {sym}: ${size:.2f}")
    else:
        print(f"\n⏳ 无合适候选 (USDT=${usdt:.2f})")
    
    print("=== 涨幅榜动量策略执行完毕 ===")
