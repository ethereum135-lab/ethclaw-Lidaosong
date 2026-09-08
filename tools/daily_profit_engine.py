#!/usr/bin/env python3
"""
ZQ每日盈利引擎 v1 — 全网研究结论的产物
代替整个A2/A3/A4/A5/A7/A8/A9系统

一句话策略：每30分钟扫涨幅榜，有动静就建仓，有动静就清仓
"""
import json, hashlib, hmac, time, math, os, sys
from datetime import datetime

# === 铁则 ===
CAPITAL_TOTAL = 198     # 总资金
PER_TRADE_USD = 20      # 每笔金额（固定，不分%）
STOP_LOSS_PCT = 0.04    # 止损-4%
TAKE_PROFIT_PCT = 0.08  # 止盈+8%
MAX_HOLD_HOURS = 48     # 最长持有48小时
LOG_PATH = os.path.expanduser("~/zq_web4_trading_system/data/trades/daily_profit_log.csv")

AUTH_PATH = os.path.expanduser("~/zq_web4_trading_system/config/auth.json")
auth = json.load(open(AUTH_PATH))["binance"]
KEY = auth["api_key"]
SECRET = auth["api_secret"]

import urllib.request, ssl
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

class BinanceAPI:
    def signed(self, params, method="GET", path="/api/v3/account"):
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
    
    def public(self, path, params=None):
        if params is None: params = {}
        qs = "&".join(f"{k}={v}" for k,v in sorted(params.items()))
        url = f"https://api.binance.com{path}?{qs}" if qs else f"https://api.binance.com{path}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        try:
            return json.loads(urllib.request.urlopen(req, timeout=15, context=CTX).read())
        except:
            return None

    def market_buy(self, symbol, usd_amount):
        return self.signed({"symbol":symbol,"side":"BUY","type":"MARKET","quoteOrderQty":round(usd_amount,2)}, "POST", "/api/v3/order")
    
    def market_sell(self, symbol, qty):
        return self.signed({"symbol":symbol,"side":"SELL","type":"MARKET","quantity":round(qty,1)}, "POST", "/api/v3/order")
    
    def stop_loss(self, symbol, qty, stop_price):
        return self.signed({
            "symbol":symbol,"side":"SELL","type":"STOP_LOSS_LIMIT",
            "quantity":round(qty,1),"stopPrice":round(stop_price,4),
            "price":round(stop_price*0.98,4),"timeInForce":"GTC"
        }, "POST", "/api/v3/order")
    
    def cancel_orders(self, symbol):
        return self.signed({"symbol":symbol}, "DELETE", "/api/v3/openOrders")

    def get_balance(self):
        acct = self.signed({})
        if "_error" in acct: return None, None, None
        balances = {b["asset"]: float(b["free"]) for b in acct["balances"] if float(b["free"]) > 0.001}
        usdt = balances.get("USDT", 0)
        non_usdt = {k:v for k,v in balances.items() if k != "USDT" and v*self.get_price(k+"USDT") > 0.5}
        return usdt, non_usdt, acct

    def get_price(self, symbol):
        d = self.public("/api/v3/ticker/price", {"symbol": symbol})
        return float(d["price"]) if d and "price" in d else 0

    def get_gainers(self, min_vol=1000000):
        tickers = self.public("/api/v3/ticker/24hr")
        if not tickers: return []
        candidates = []
        for t in tickers:
            if not t["symbol"].endswith("USDT"): continue
            sym = t["symbol"]
            if any(x in sym for x in ["UP","DOWN","BULL","BEAR","LUNA","UST"]): continue
            chg = float(t["priceChangePercent"])
            vol = float(t["quoteVolume"])
            price = float(t["lastPrice"])
            if 3 <= chg <= 20 and vol >= min_vol:
                candidates.append({"sym":sym,"chg":chg,"vol":vol,"price":price})
        candidates.sort(key=lambda x: -x["vol"])
        return candidates[:20]

def log_trade(action, symbol, price, qty, usd, pnl=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"{ts},{action},{symbol},{price:.6f},{qty:.2f},{usd:.2f},{pnl}\n"
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(line)
    print(f"📝 日志: {line.strip()}")

if __name__ == "__main__":
    api = BinanceAPI()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M BJT")
    print(f"\n{'='*50}")
    print(f"  ZQ每日盈利引擎 v1 — {ts}")
    print(f"{'='*50}")
    
    usdt, holdings, acct = api.get_balance()
    if usdt is None:
        print("❌ API失败，退出")
        sys.exit(1)
    
    print(f"\n📊 USDT: ${usdt:.2f}")
    
    # === 阶段1：检查现有持仓是否需要退出 ===
    active_position = None
    for sym, qty in holdings.items():
        price = api.get_price(sym+"USDT")
        if price == 0: continue
        value = qty * price
        if value > 1:
            print(f"📦 {sym}: {qty:.2f} × ${price:.4f} = ${value:.2f}")
            # 任何$5+的仓位都检查退出
            if value >= 5:
                active_position = {"sym":sym+"USDT","qty":qty,"price":price,"value":value}
    
    # 如果有持仓，检查退出条件
    if active_position:
        s = active_position
        entry_cost = PER_TRADE_USD
        current_value = s["qty"] * s["price"]
        pnl_pct = (current_value - entry_cost) / entry_cost * 100
        
        print(f"\n📊 {s['sym']}: PnL={pnl_pct:+.2f}% (成本${entry_cost:.2f})")
        
        # 检查止盈
        if pnl_pct >= TAKE_PROFIT_PCT * 100:
            print(f"🎯 止盈触发! +{pnl_pct:+.2f}%")
            api.cancel_orders(s["sym"])
            r = api.market_sell(s["sym"], s["qty"]*0.98)
            if "_error" not in r:
                proceeds = float(r.get("cummulativeQuoteQty", 0))
                profit = proceeds - entry_cost
                log_trade("SELL_TP", s["sym"], s["price"], s["qty"], proceeds, f"+${profit:.2f}")
                print(f"✅ 止盈卖出! 收入${proceeds:.2f} 利润${profit:.2f}")
            else:
                print(f"❌ 卖出失败: {r}")
        # 检查止损
        elif pnl_pct <= -STOP_LOSS_PCT * 100:
            print(f"🛑 止损触发! {pnl_pct:+.1f}%")
            api.cancel_orders(s["sym"])
            r = api.market_sell(s["sym"], s["qty"]*0.98)
            if "_error" not in r:
                proceeds = float(r.get("cummulativeQuoteQty", 0))
                log_trade("SELL_SL", s["sym"], s["price"], s["qty"], proceeds, f"-${entry_cost-proceeds:.2f}")
                print(f"✅ 止损卖出! 回收${proceeds:.2f}")
            else:
                print(f"❌ 卖出失败: {r}")
        else:
            print(f"⏳ 持有中，未到退出条件")
    
    # === 阶段2：没持仓就开新仓 ===
    else:
        print("\n🔍 无活跃持仓，扫描涨幅榜...")
        gainers = api.get_gainers(min_vol=1000000)
        
        if not gainers:
            print("❌ 无法获取涨幅榜")
            sys.exit(1)
        
        print(f"📋 涨幅榜TOP (成交量过滤>$1M):")
        for g in gainers[:10]:
            print(f"   {g['sym']:12s} +{g['chg']:+.2f}% vol=${g['vol']/1e6:.1f}M price=${g['price']:.4f}")
        
    # 选币：排除已有持仓 + 检查是否「刚启动」不是「已泵顶」
        skip = ["NEARUSDT","INJUSDT","UNIUSDT","SOLUSDT"]
        candidates = [g for g in gainers if g["sym"] not in skip]
        
        # 检查每个候选的1h K线，判断是否刚启动
        verified_candidates = []
        for g in candidates:
            sym = g["sym"]
            klines = api.public("/api/v3/klines", {"symbol": sym, "interval": "1h", "limit": 12})
            if not klines or len(klines) < 6: continue
            
            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            last_candle = klines[-1]
            last_open = float(last_candle[1])
            last_close = float(last_candle[4])
            last_vol = float(last_candle[5])
            
            # 计算指标
            avg_vol = sum(volumes[:-1]) / (len(volumes)-1) if len(volumes) > 1 else 1
            vol_ratio = last_vol / avg_vol if avg_vol > 0 else 0
            is_green = last_close > last_open
            prev_high = max(float(k[2]) for k in klines[:-1])
            broke_high = last_close > prev_high * 0.998  # 接近前高
            
            # 1h RSI
            gains, losses = 0, 0
            for i in range(1, min(15, len(closes))):
                diff = closes[-i] - closes[-i-1]
                if diff >= 0: gains += diff
                else: losses -= diff
            rsi_1h = 50  # default
            if losses > 0:
                rs = (gains/min(14,len(closes)-1)) / (losses/min(14,len(closes)-1))
                rsi_1h = 100 - 100/(1+rs)
            
            # 刚启动条件：该小时阳线 + 放量(>1.5x) + 突破前高 + RSI<75
            is_just_starting = (is_green and vol_ratio > 1.3 and 
                              broke_high and rsi_1h < 75)
            
            # 计算连续涨了多少小时
            green_hours = 0
            for k in reversed(klines):
                if float(k[4]) > float(k[1]): green_hours += 1
                else: break
            
            label = "🟢刚启动" if is_just_starting else ("⚠️已涨"+str(green_hours)+"h" if green_hours > 2 else "⚪观察")
            print(f"   {sym:12s} 1h:{'+' if is_green else '-'}{vol_ratio:.1f}x RSI{rsi_1h:.0f} {label}")
            
            if is_just_starting:
                g["rsi_1h"] = rsi_1h
                g["vol_ratio"] = vol_ratio
                g["green_hours"] = green_hours
                verified_candidates.append(g)
        
        if not verified_candidates:
            print("⏳ 无刚启动候选")
            sys.exit(0)
        
        # 从刚启动的候选里选成交量最大的
        verified_candidates.sort(key=lambda x: -x["vol"])
        best = verified_candidates[0]
        buy_amount = min(PER_TRADE_USD, usdt * 0.8)
        
        if buy_amount < 5:
            print(f"❌ 可买金额${buy_amount:.2f} < $5 MIN_NOTIONAL")
            sys.exit(0)
        
        print(f"\n🚀 选中: {best['sym']} +{best['chg']:+.2f}% vol=${best['vol']/1e6:.1f}M")
        print(f"   买入 ${buy_amount:.2f}...")
        
        r = api.market_buy(best["sym"], buy_amount)
        if "_error" in r:
            print(f"❌ 买入失败: {r['_error']}")
            sys.exit(1)
        
        fills = r.get("fills", [])
        avg_p = sum(float(f["price"])*float(f["qty"]) for f in fills) / max(sum(float(f["qty"]) for f in fills), 0.001)
        qty = float(r.get("executedQty", 0))
        cost = float(r.get("cummulativeQuoteQty", 0))
        
        print(f"✅ 买入成功!")
        print(f"   数量: {qty:.2f}")
        print(f"   均价: ${avg_p:.4f}")
        print(f"   金额: ${cost:.2f}")
        
        # 设止损
        stop_p = round(avg_p * (1 - STOP_LOSS_PCT), 4)
        sl = api.stop_loss(best["sym"], qty, stop_p)
        if "_error" in sl:
            print(f"⚠️ 止损单失败: {sl.get('_error','?')}")
        else:
            print(f"✅ 止损: ${stop_p} (-{STOP_LOSS_PCT*100:.0f}%)")
        
        log_trade("BUY", best["sym"], avg_p, qty, cost)
    
    # 最终资产
    usdt2, holdings2, _ = api.get_balance()
    total = usdt2 + sum(api.get_price(s+"USDT")*q for s,q in holdings2.items())
    print(f"\n💰 总资: ~${total:.2f}")
    print(f"{'='*50}\n")
