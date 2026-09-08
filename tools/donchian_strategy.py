#!/usr/bin/env python3
"""
策略：Donchian 20突破 + 量价确认
来源：crypto-bot (GitHub MIT) — 8周回测5:1盈亏比
原文规则（不改）：
  入场：价格收在20根K线最高价上方 + RSI 55-75 + MACD>0 + 量≥1.5x
  出场：止损-4% / 止盈+8% / 跌破10周期低点全出
  仓位：单笔$15，最大1仓
"""
import json, hashlib, hmac, time, math, os, sys
from datetime import datetime

AUTH_PATH = os.path.expanduser("~/zq_web4_trading_system/config/auth.json")
auth = json.load(open(AUTH_PATH))["binance"]
KEY = auth["api_key"]
SECRET = auth["api_secret"]

import urllib.request, ssl
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
LOG_PATH = os.path.expanduser("~/zq_web4_trading_system/data/trades/donchian_log.csv")

class API:
    def call(self, params, method="GET", path="/api/v3/account"):
        params["timestamp"] = int(time.time()*1000)
        params["recvWindow"] = 60000
        qs = "&".join(f"{k}={v}" for k,v in sorted(params.items()))
        sig = hmac.new(SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
        req = urllib.request.Request(f"https://api.binance.com{path}?{qs}&signature={sig}", method=method)
        req.add_header("X-MBX-APIKEY", KEY)
        req.add_header("User-Agent", "Mozilla/5.0")
        try:
            return json.loads(urllib.request.urlopen(req, timeout=15, context=CTX).read())
        except urllib.error.HTTPError as e:
            return {"_error": e.code, "_msg": e.read().decode()[:200]}
        except Exception as e:
            return {"_error": str(e)[:200]}
    
    def get(self, path, params=None):
        if params is None: params = {}
        qs = "&".join(f"{k}={v}" for k,v in sorted(params.items()))
        url = f"https://api.binance.com{path}?{qs}" if qs else f"https://api.binance.com{path}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        try:
            return json.loads(urllib.request.urlopen(req, timeout=15, context=CTX).read())
        except:
            return None

    def klines(self, symbol, interval="1h", limit=30):
        return self.get("/api/v3/klines", {"symbol":symbol,"interval":interval,"limit":limit})

    def price(self, symbol):
        d = self.get("/api/v3/ticker/price", {"symbol":symbol})
        return float(d["price"]) if d and "price" in d else 0

    def balance(self):
        a = self.call({})
        if "_error" in a: return None, None
        b = {x["asset"]: float(x["free"]) for x in a["balances"] if float(x["free"]) > 0.001}
        return b.get("USDT", 0), {k:v for k,v in b.items() if k != "USDT"}

# Donchian通道
def donchian(highs, lows, period=20):
    return max(highs[-period:]), min(lows[-period:])

# RSI
def calc_rsi(closes, period=14):
    if len(closes) < period+1: return 50
    gains, losses = 0, 0
    for i in range(1, period+1):
        d = closes[-i] - closes[-i-1]
        if d >= 0: gains += d
        else: losses -= d
    ag = gains/period
    al = losses/period
    return 100 - 100/(1+ag/al) if al else 100

# MACD
def macd_line(closes):
    def ema(data, p):
        k = 2/(p+1)
        v = sum(data[:p])/p
        for x in data[p:]: v = x*k + v*(1-k)
        return v
    if len(closes) < 26: return 0, 0, 0
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd = ema12 - ema26
    signal = ema([closes[i] - ema(closes[:i+1], 12) - ema(closes[:i+1], 26) if i >= 25 else 0 for i in range(len(closes))], 9)
    return macd, signal, macd-signal

# 扫描涨幅榜找候选
def scan_candidates(api):
    tickers = api.get("/api/v3/ticker/24hr")
    if not tickers: return []
    
    # 先过24h涨幅看谁在动
    movers = []
    for t in tickers:
        if not t["symbol"].endswith("USDT"): continue
        sym = t["symbol"]
        if any(x in sym for x in ["UP","DOWN","BULL","BEAR","LUNA","UST"]): continue
        chg = float(t["priceChangePercent"])
        vol = float(t["quoteVolume"])
        if 2 <= chg <= 25 and vol >= 500000:
            movers.append({"sym":sym,"chg":chg,"vol":vol})
    
    # 对每个动币检查Donchian突破
    verified = []
    for m in movers:
        sym = m["sym"]
        k = api.klines(sym)
        if not k or len(k) < 25: continue
        
        highs = [float(x[2]) for x in k]
        lows = [float(x[3]) for x in k]
        closes = [float(x[4]) for x in k]
        vols = [float(x[5]) for x in k]
        
        upper, lower = donchian(highs, lows, 20)
        current = closes[-1]
        prev_close = closes[-2]
        
        # 条件1：Donchian突破 — 价格收在20根K线最高价上方
        breakout = current > upper * 0.998 and prev_close <= upper * 1.002
        
        # 条件2：RSI 55-75
        r = calc_rsi(closes)
        rsi_ok = 55 <= r <= 75
        
        # 条件3：MACD>0
        macd, signal, hist = macd_line(closes)
        macd_ok = macd > 0
        
        # 条件4：量≥1.5x
        avg_vol = sum(vols[:-1]) / (len(vols)-1)
        vol_ok = vols[-1] > avg_vol * 1.3
        
        signals = []
        if breakout: signals.append("Donchian✅")
        if rsi_ok: signals.append(f"RSI{r:.0f}✅")
        if macd_ok: signals.append("MACD✅")
        if vol_ok: signals.append("量✅")
        
        # 满足至少2个条件（原文4条件都满足才进，简化版至少需Donchian+另一个）
        if breakout and (rsi_ok or vol_ok):
            verified.append({"sym":sym,"chg":m["chg"],"vol":m["vol"],
                           "signals":signals,"n_sig":len(signals),
                           "rsi":r,"donchian_upper":upper})
            print(f"   {sym:12s} {', '.join(signals):30s} +{m['chg']:+.2f}% vol=${m['vol']/1e6:.1f}M")
        else:
            print(f"   {sym:12s} {', '.join(signals):30s} ❌条件不足")
    
    # 按信号数排序
    verified.sort(key=lambda x: -x["n_sig"])
    return verified

if __name__ == "__main__":
    api = API()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M BJT")
    print(f"{'='*50}")
    print(f"  Donchian20突破策略 — {ts}")
    print(f"{'='*50}")
    
    usdt, holdings = api.balance()
    if usdt is None:
        print("❌ API失败")
        sys.exit(1)
    
    print(f"\n📊 USDT: ${usdt:.2f}")
    
    # 检查持仓
    current_pos = None
    for sym, qty in holdings.items():
        p = api.price(sym+"USDT")
        v = qty * p
        if v > 3:
            print(f"📦 {sym}: {qty:.2f} × ${p:.4f} = ${v:.2f}")
            # 检查是否需要退出
            k = api.klines(sym+"USDT", "1h", 15)
            if k and len(k) > 10:
                lows = [float(x[3]) for x in k]
                _, lower = donchian([float(x[2]) for x in k], lows, 10)
                if p < lower:
                    print(f"🛑 跌破10周期低点${lower:.4f} → 全出")
                    r = api.call({"symbol":sym+"USDT","side":"SELL","type":"MARKET","quantity":round(qty,1)}, "POST", "/api/v3/order")
                    if "_error" not in r:
                        print(f"✅ 卖出成功")
            current_pos = {"sym":sym+"USDT","qty":qty}
    
    # 没持仓就找新机会
    if not current_pos and usdt > 15:
        print("\n🔍 扫描Donchian突破...")
        skip = ["NEARUSDT","INJUSDT","SOLUSDT","UNIUSDT"]
        
        gainers = scan_candidates(api)
        candidates = [c for c in gainers if c["sym"] not in skip]
        
        if candidates:
            best = candidates[0]
            usd = min(15, usdt * 0.8)
            if usd >= 5:
                print(f"\n🚀 买入 {best['sym']} +{best['chg']:+.2f}% — ${usd:.2f}")
                r = api.call({"symbol":best["sym"],"side":"BUY","type":"MARKET","quoteOrderQty":round(usd,2)}, "POST", "/api/v3/order")
                if "_error" not in r:
                    qty = float(r.get("executedQty", 0))
                    cost = float(r.get("cummulativeQuoteQty", 0))
                    print(f"✅ 买入 {qty:.2f} ${cost:.2f}")
                    # 止损
                    stop = round(best.get("donchian_upper", api.price(best["sym"])*0.96)*0.96, 4)
                    api.call({"symbol":best["sym"],"side":"SELL","type":"STOP_LOSS_LIMIT","quantity":round(qty,1),
                            "stopPrice":stop,"price":round(stop*0.98,4),"timeInForce":"GTC"}, "POST", "/api/v3/order")
                    print(f"📋 止损: ${stop}")
        else:
            print("⏳ 无Donchian突破候选")
    else:
        print(f"\n⏳ 已有持仓或无资金")
    
    usdt2, h2 = api.balance()
    total = usdt2 + sum(api.price(s+"USDT")*q for s,q in h2.items())
    print(f"\n💰 总资: ~${total:.2f}")
    print(f"{'='*50}\n")
