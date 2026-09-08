#!/usr/bin/env python3
"""
Risk-First Trading Engine v2
============================
核心设计（不是策略，是结构）：

1. 固定风险1%/仓  — 每笔最多亏总资的1%（$180→$1.80）
2. 仓位由风险倒推 — 止损窄多买、止损宽少买（固定风险、变仓位）
3. 让赢家跑      — 无止盈价，P1(RSI>85)或回撤跟综才出
4. 接受多数小亏   — 30%胜率+3:1盈亏比=赚钱，不需要每笔赢

规则：
  进场：涨幅榜3-15% + 量比≥1.5x + RSI(4h)<70
  出场：P1(RSI>85) 或 浮动止损(峰值-3%) 或 -5%硬止损
  仓位：risk $1.80 / 止损幅度
  最多1仓
"""
import json, os, sys, time, hmac, hashlib, urllib.request, ssl
from datetime import datetime, timezone, timedelta
from typing import Optional
import urllib.error

BJT = timezone(timedelta(hours=8))
N = lambda: datetime.now(BJT).strftime('%Y-%m-%d %H:%M BJT')

# === CONFIG ===
RISK_PER_TRADE = 0.01       # 单笔风险 = 总资 × 1%
MAX_DAILY_LOSS = 0.03       # 日最大亏损 = 总资 × 3%
RISK_FREE_RATE = 0.0

STOP_HARD = -0.05           # 硬止损 -5%
TRAIL_ACTIVATE = 0.05       # 浮盈5%后启动浮动止损
TRAIL_DISTANCE = 0.03       # 浮动距离3%
RSI_SELL = 85               # P1出场

ENTRY_GAIN_MIN = 3.0        # 最小涨幅
ENTRY_GAIN_MAX = 15.0       # 最大涨幅
VOLUME_SURGE = 1.5          # 量比
RSI_BUY_MAX = 70            # RSI上限
MAX_POSITIONS = 1           # 最多1仓
MIN_CAPITAL = 100           # 最低启动资金
CYCLE_SECONDS = 30 * 60     # 30分钟

ZQ_ROOT = os.path.expanduser("~/zq_web4_trading_system")
LOG_DIR = os.path.join(ZQ_ROOT, "data", "trades")
STATE_FILE = os.path.join(ZQ_ROOT, "data", "engine_v2_state.json")
os.makedirs(LOG_DIR, exist_ok=True)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# === HELPERS ===

def http_get(url, timeout=12):
    try:
        r = urllib.request.urlopen(url, timeout=timeout, context=CTX)
        return json.loads(r.read().decode())
    except Exception as e:
        return {"_error": str(e)}

def signed_call(params, method="GET", path="/api/v3/account"):
    """Signed Binance API call (for trades)."""
    auth_path = os.path.join(ZQ_ROOT, "config", "auth.json")
    if not os.path.exists(auth_path):
        return {"_error": "auth.json missing"}
    auth = json.load(open(auth_path))["binance"]
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 60000
    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sig = hmac.new(auth["api_secret"].encode(), qs.encode(), hashlib.sha256).hexdigest()
    url = f"https://api.binance.com{path}?{qs}&signature={sig}"
    req = urllib.request.Request(url, method=method)
    req.add_header("X-MBX-APIKEY", auth["api_key"])
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15, context=CTX).read())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()[:200]}
    except Exception as e:
        return {"_error": str(e)[:200]}

def get_balance():
    """Get USDT balance and holdings."""
    a = signed_call({})
    if "_error" in a:
        return None, None, a["_error"]
    usdt = 0
    holdings = {}
    for b in a.get("balances", []):
        free = float(b["free"])
        locked = float(b["locked"])
        total = free + locked
        if total <= 0.001:
            continue
        if b["asset"] == "USDT":
            usdt = total
        else:
            holdings[b["asset"]] = {"free": free, "locked": locked, "total": total}
    return usdt, holdings, None

def get_price(symbol):
    """Get current price for a symbol."""
    d = http_get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT")
    return float(d.get("price", 0)) if isinstance(d, dict) and "price" in d else 0

def get_klines_4h(symbol, limit=30):
    """Get 4h klines."""
    d = http_get(f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=4h&limit={limit}")
    return d if isinstance(d, list) else []

def calc_rsi(klines, period=14):
    closes = [float(k[4]) for k in klines]
    if len(closes) < period + 1:
        return 50.0
    gains, losses = 0, 0
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        if diff > 0: gains += diff
        else: losses -= diff
    ag = gains / period
    al = losses / period
    return 100.0 - (100.0 / (1.0 + ag / al)) if al else 100.0

# === RISK ENGINE ===

def calc_position(total_capital: float, stop_pct: float) -> float:
    """
    仓位由风险倒推：
      固定风险 = total_capital × RISK_PER_TRADE
      仓位价值 = 固定风险 / abs(止损幅度)
    
    例：$180 × 1% = $1.80风险
        止损-5% → $1.80/0.05 = $36
        止损-3% → $1.80/0.03 = $60
    """
    risk_amount = total_capital * RISK_PER_TRADE
    stop_abs = abs(stop_pct)
    if stop_abs < 0.01:  # 最小止损1%
        stop_abs = 0.01
    position = risk_amount / stop_abs
    # 最小$10（Binance门槛），最大50%总资
    position = max(10, min(position, total_capital * 0.5))
    return round(position, 2)

# === ENTRY SCANNER ===

def scan_top_gainers(ticker_data):
    """Scan top gainers and find entry candidates."""
    if not ticker_data or (isinstance(ticker_data, dict) and "_error" in ticker_data):
        return []
    
    # 过滤USDT对
    coins = []
    for t in ticker_data:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"): continue
        if any(x in sym for x in ["UP", "DOWN", "BULL", "BEAR", "LUNA"]): continue
        try:
            chg = float(t.get("priceChangePercent", 0))
            vol = float(t.get("quoteVolume", 0))
        except:
            continue
        coins.append({"symbol": sym.replace("USDT", ""), "change_24h": chg, "volume_24h": vol})
    
    # 涨幅排序，取TOP50
    coins.sort(key=lambda x: x["change_24h"], reverse=True)
    top50 = coins[:50]
    
    candidates = []
    for c in top50:
        # Rule 1: 涨幅3-15%
        if c["change_24h"] < ENTRY_GAIN_MIN or c["change_24h"] > ENTRY_GAIN_MAX:
            continue
        
        # 拉K线
        klines = get_klines_4h(c["symbol"])
        if not klines or len(klines) < 20:
            continue
        
        # Rule 2: 量比≥1.5x
        vols = [float(k[7]) for k in klines]
        avg_vol = sum(vols) / len(vols)
        last_vol = vols[-1]
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1.0
        if vol_ratio < VOLUME_SURGE:
            continue
        
        # Rule 3: RSI(4h) < 70
        rsi = calc_rsi(klines)
        if rsi >= RSI_BUY_MAX:
            continue
        
        # 计算止损距离（基于ATR或固定）
        closes = [float(k[4]) for k in klines]
        atr = sum(abs(closes[i] - closes[i-1]) for i in range(1, len(closes))) / (len(closes)-1)
        current_price = closes[-1]
        atr_pct = atr / current_price if current_price > 0 else 0.05
        
        # 止损 = 当前价 - 2倍ATR（动态），但不大于-5%
        stop_distance = min(max(atr_pct * 2, 0.02), 0.05)
        
        c["rsi_4h"] = round(rsi, 1)
        c["close"] = current_price
        c["vol_ratio"] = round(vol_ratio, 2)
        c["atr_pct"] = round(atr_pct * 100, 2)
        c["stop_pct"] = -round(stop_distance * 100, 1)
        
        candidates.append(c)
    
    # 按评分排序：涨幅贡献40% + 量比30% + (70-RSI)30%
    for c in candidates:
        c["score"] = round(
            c["change_24h"] / ENTRY_GAIN_MAX * 40 +
            min(c["vol_ratio"], 5) / 5 * 30 +
            (RSI_BUY_MAX - c["rsi_4h"]) / RSI_BUY_MAX * 30,
            1
        )
    
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates

# === EXIT ENGINE ===

def check_exit(position, current_price, peak_price, entry_price, total_capital):
    """
    出场检查（三个条件任一触发就卖）：
    1. P1: RSI(4h)>85
    2. 浮动止损：从峰值回落超过3%
    3. 硬止损：-5%
    """
    symbol = position["symbol"]
    klines = get_klines_4h(symbol)
    
    reasons = []
    pnl_pct = (current_price - entry_price) / entry_price
    
    # P1
    if klines and len(klines) > 14:
        rsi = calc_rsi(klines)
        if rsi >= RSI_SELL:
            reasons.append(f"P1(RSI={rsi:.1f}≥85)")
        
        # 跟踪止损
        if peak_price > entry_price * (1 + TRAIL_ACTIVATE):
            retrace = (peak_price - current_price) / peak_price
            if retrace >= TRAIL_DISTANCE:
                reasons.append(f"浮动止损(峰值${peak_price:.4f}→当前${current_price:.4f},回落{retrace*100:.1f}%≥3%)")
    
    # 硬止损
    if pnl_pct <= STOP_HARD:
        reasons.append(f"硬止损({pnl_pct*100:.1f}%≤-5%)")
    
    return reasons

# === EXECUTION ===

def execute_buy(candidate, position_size):
    """Execute a buy order."""
    sym = candidate["symbol"] + "USDT"
    r = signed_call({
        "symbol": sym,
        "side": "BUY",
        "type": "MARKET",
        "quoteOrderQty": str(position_size)
    }, "POST", "/api/v3/order")
    return r

def execute_sell(symbol, quantity):
    """Execute a sell order."""
    r = signed_call({
        "symbol": symbol,
        "side": "SELL",
        "type": "MARKET",
        "quantity": str(round(quantity, 4))
    }, "POST", "/api/v3/order")
    return r

# === MAIN CYCLE ===

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            return json.load(open(STATE_FILE))
        except:
            pass
    return {"position": None, "peak_price": {}, "daily_pnl": 0, "total_pnl": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def log_trade(action, data):
    logfile = os.path.join(LOG_DIR, f"{datetime.now(BJT).strftime('%Y%m%d')}.log")
    data["time"] = N()
    data["action"] = action
    with open(logfile, "a") as f:
        f.write(json.dumps(data) + "\n")

def cycle():
    state = load_state()
    ts = N()
    
    print(f"\n{'='*55}")
    print(f"  🔄 Risk-First Engine — {ts}")
    print(f"{'='*55}")
    
    # Step 1: Get balance and total capital
    usdt, holdings, err = get_balance()
    if err:
        print(f"❌ 获取余额失败: {err}")
        return
    
    # Calculate total capital
    total_cap = usdt
    position_info = None
    if state.get("position"):
        sym = state["position"]["symbol"]
        p = get_price(sym)
        pos_qty = state["position"].get("quantity", 0)
        pos_val = p * pos_qty
        total_cap += pos_val
        position_info = {"symbol": sym, "price": p, "qty": pos_qty, "value": round(pos_val, 2)}
    
    print(f"\n💰 总资: ~${total_cap:.2f}   |   USDT: ${usdt:.2f}")
    print(f"   风险预算: 1% = ${total_cap * RISK_PER_TRADE:.2f}/笔")
    if position_info:
        print(f"   📦 持仓: {position_info['symbol']} {position_info['qty']:.2f} × ${position_info['price']:.4f} = ${position_info['value']}")
    
    # Step 2: Check exit if holding
    if state.get("position"):
        sym = state["position"]["symbol"]
        entry = state["position"]["entry_price"]
        current = position_info["price"]
        peak = state.get("peak_price", {}).get(sym, current)
        
        if current > peak:
            state["peak_price"][sym] = current
            peak = current
        
        reasons = check_exit(state["position"], current, peak, entry, total_cap)
        if reasons:
            print(f"\n🔴 出场: {sym} — {' + '.join(reasons)}")
            # Execute sell
            qty = position_info["qty"]
            r = execute_sell(f"{sym}USDT", qty)
            if "_error" not in r:
                pnl = (current - entry) * qty
                state["position"] = None
                state["peak_price"] = {}
                state["daily_pnl"] = state.get("daily_pnl", 0) + pnl
                state["total_pnl"] = state.get("total_pnl", 0) + pnl
                print(f"   ✅ 已卖出 ${pnl:+.2f}")
                log_trade("SELL", {"symbol": sym, "price": current, "qty": qty, "pnl": round(pnl, 2), "reasons": reasons})
            else:
                print(f"   ❌ 卖出失败: {r.get('_error')}")
        else:
            pnl_pct = (current - entry) / entry * 100
            print(f"\n🟢 持有: {sym}  ${pnl_pct:+.2f}%  (峰值${peak:.4f})")
    
    # Step 3: Check if we can buy
    if not state.get("position") and usdt >= 10:
        # Check daily loss limit
        daily_pnl = state.get("daily_pnl", 0)
        if daily_pnl <= -total_cap * MAX_DAILY_LOSS:
            print(f"\n⛔ 日亏损已达{daily_pnl:.2f}({daily_pnl/total_cap*100:.1f}%)，停止交易")
            save_state(state)
            return
        
        print(f"\n🔍 扫描进场候选...")
        ticker = http_get("https://api.binance.com/api/v3/ticker/24hr")
        
        candidates = scan_top_gainers(ticker)
        if candidates:
            best = candidates[0]
            stop_pct = best["stop_pct"] / 100
            pos_size = calc_position(total_cap, stop_pct)
            pos_size = min(pos_size, usdt * 0.8)  # 最多用80% USDT
            
            print(f"\n   🥇 候选: {best['symbol']} +{best['change_24h']:.1f}%")
            print(f"      量比{best['vol_ratio']}x | RSI={best['rsi_4h']} | ATR={best['atr_pct']}%")
            print(f"      止损{best['stop_pct']}% → 仓位${pos_size}")
            
            # Check: don't buy if already scanned and rejected
            r = execute_buy(best, pos_size)
            if "_error" not in r:
                qty = float(r.get("executedQty", 0))
                cost = float(r.get("cummulativeQuoteQty", 0))
                entry_price = cost / qty if qty > 0 else best.get("close", 0)
                
                state["position"] = {
                    "symbol": best["symbol"],
                    "entry_price": entry_price,
                    "quantity": qty,
                    "cost": cost,
                    "stop_pct": best["stop_pct"],
                    "reason": f"+{best['change_24h']:.1f}%·量比{best['vol_ratio']}x·RSI{best['rsi_4h']}"
                }
                state["peak_price"][best["symbol"]] = entry_price
                
                print(f"   ✅ 买入 {qty:.2f} {best['symbol']} @ ${entry_price:.4f} = ${cost:.2f}")
                print(f"   止损: ${entry_price * (1 + stop_pct):.4f} ({best['stop_pct']}%)")
                log_trade("BUY", state["position"])
            else:
                print(f"   ❌ 买入失败: {r.get('_error')}")
        else:
            print(f"\n   无符合进场条件的币")
    
    # Save state
    save_state(state)
    
    # Summary
    total = total_cap
    print(f"\n{'='*55}")
    print(f"  ✅ 完成 | 总资${total:.2f} | 日盈亏${state.get('daily_pnl', 0):+.2f}")
    print(f"{'='*55}")

if __name__ == "__main__":
    print("🧊 Risk-First Engine v2")
    print(f"   单笔风险: 总资×{RISK_PER_TRADE*100:.0f}%")
    print(f"   日亏损上限: 总资×{MAX_DAILY_LOSS*100:.0f}%")
    print(f"   出场: P1(RSI>{RSI_SELL}) / 浮动止损({TRAIL_DISTANCE*100:.0f}%) / 硬止损({abs(STOP_HARD)*100:.0f}%)")
    print(f"   最多{MAX_POSITIONS}仓 | 每{CYCLE_SECONDS//60}分钟")
    print()
    
    cycle()
    
    # Daemon mode
    if "--daemon" in sys.argv:
        print(f"\n🔄 守护模式: 每{CYCLE_SECONDS//60}分钟循环...")
        while True:
            time.sleep(CYCLE_SECONDS)
            cycle()
