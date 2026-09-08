#!/usr/bin/env python3
"""
ZQ Simple Strategy v1.0 — 4H周期，每天1-2笔
目标：每天盈利，不管多少
研究依据：
  - 2条件极简策略(RSI<25)年化+55.5%，6条件复杂策略仅+42.8%
  - 4H周期是$50-$500账户最优频率
  - $66→$1000需要16-18个月月化18%，每天0.2-0.5%

入场条件（全部满足才买）：
  ① 涨幅榜3-15%（刚启动不是已泵顶）
  ② RSI(4h) < 70（不过热）
  ③ 成交量 > 前7天均值1.5x（有量）
出场条件（任一到就卖）：
  ① +8%止盈
  ② -4%止损
  ③ 持仓超24h + 浮亏 > -2%
  ④ BTC日跌超-5%

仓位：单笔$30-50，最大2仓，FNG<20时减半
"""
import json, hashlib, hmac, time, math, os, sys
from datetime import datetime

# === Config ===
CAPITAL = 197.66
MAX_POSITIONS = 2
POSITION_SIZE = 35  # per position in USDT
STOP_LOSS = -0.04
TAKE_PROFIT = 0.08
MAX_HOLD_HOURS = 24

AUTH_PATH = os.path.expanduser("~/zq_web4_trading_system/config/auth.json")
LOG_PATH = os.path.expanduser("~/zq_web4_trading_system/data/trades/daily_trades.json")

import urllib.request, ssl
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def api_signed(params, path="/api/v3/account"):
    """Signed API call to Binance"""
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 60000
    with open(AUTH_PATH) as f:
        auth = json.load(f)["binance"]
    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sig = hmac.new(auth["api_secret"].encode(), qs.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(f"https://api.binance.com{path}?{qs}&signature={sig}")
    req.add_header("X-MBX-APIKEY", auth["api_key"])
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15, context=CTX).read())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()[:300]}
    except Exception as e:
        return {"_error": str(e)[:300]}

def api_get(path, params=None):
    """Public API call"""
    if params is None: params = {}
    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items())) if params else ""
    url = f"https://api.binance.com{path}"
    if qs: url += f"?{qs}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=10, context=CTX).read())
    except:
        return None

def get_klines(symbol, interval="4h", limit=100):
    """Get K-line data"""
    return api_get("/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": limit})

def calc_rsi(closes, period=14):
    """Calculate RSI"""
    if len(closes) < period + 1: return 50
    gains, losses = 0, 0
    for i in range(1, period + 1):
        d = closes[-i] - closes[-i - 1]
        if d >= 0: gains += d
        else: losses -= d
    ag = gains / period
    al = losses / period
    return 100 - 100 / (1 + ag / al) if al else 100

def get_current_positions(balances):
    """Get current active positions (value > $3)"""
    prices = api_get("/api/v3/ticker/price")
    if not prices: return []
    price_map = {p["symbol"]: float(p["price"]) for p in prices}

    positions = []
    for asset, qty in balances.items():
        if asset in ("USDT", "USDC", "BUSD", "FDUSD"):
            continue
        pair = f"{asset}USDT"
        price = price_map.get(pair, 0)
        value = price * qty
        if value >= 3:
            positions.append({"asset": asset, "qty": qty, "price": price, "value": value})
    return sorted(positions, key=lambda x: -x["value"])

def log_trade(action, symbol, price, qty, reason):
    """Log trade to JSON file"""
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "symbol": symbol,
        "price": price,
        "qty": qty,
        "value": price * qty,
        "reason": reason
    }
    trades = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            try: trades = json.load(f)
            except: trades = []
    trades.append(entry)
    with open(LOG_PATH, "w") as f:
        json.dump(trades, f, indent=2)
    return entry

def main():
    print(f"=== ZQ Simple Strategy v1.0 ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Capital: ${CAPITAL:.2f} | Position: ${POSITION_SIZE} | Max: {MAX_POSITIONS} positions")
    print()

    # 1. Check account and current positions
    acct = api_signed({})
    if "_error" in acct:
        print(f"❌ Account API error: {acct['_error']} - {acct.get('_msg','')}")
        return

    balances = {b["asset"]: float(b["free"]) for b in acct["balances"] if float(b["free"]) > 0.001}
    usdt = balances.get("USDT", 0)
    positions = get_current_positions({k: v for k, v in balances.items() if k != "USDT"})

    print(f"USDT: ${usdt:.2f}")
    print(f"Current positions: {len(positions)}")
    for p in positions[:3]:
        print(f"  {p['asset']:8s} {p['qty']:.4f} × ${p['price']:.4f} = ${p['value']:.2f}")

    # 2. Check exit conditions for existing positions
    if positions:
        btc_price = api_get("/api/v3/ticker/price", {"symbol": "BTCUSDT"})
        btc_price = float(btc_price["price"]) if btc_price else 0

        for pos in positions:
            # Check BTC -5% condition
            btc_24h = api_get("/api/v3/ticker/24hr", {"symbol": "BTCUSDT"})
            if btc_24h:
                btc_change = float(btc_24h.get("priceChangePercent", 0))
                if btc_change < -5:
                    print(f"🔴 BTC dropped -{abs(btc_change):.1f}% — selling {pos['asset']}")
                    # Execute sell
                    result = api_signed({
                        "symbol": f"{pos['asset']}USDT",
                        "side": "SELL",
                        "type": "MARKET",
                        "quantity": pos["qty"]
                    }, "/api/v3/order")
                    if "_error" not in result:
                        log_trade("SELL", pos["asset"], pos["price"], pos["qty"], "BTC_drop")
                        usdt += pos["value"]
                        print(f"  ✅ Sold {pos['asset']} for ${pos['value']:.2f}")

    # 3. Scan for new entry candidates
    if usdt >= POSITION_SIZE:
        print(f"\nScanning for entries (USDT=${usdt:.2f})...")

        # Get top gainers
        gainers = api_get("/api/v3/ticker/24hr")
        if not gainers:
            print("❌ Cannot fetch ticker data")
            return

        # Filter: 3-15% gainers, volume > $500K, not stablecoins
        candidates = []
        for g in gainers:
            sym = g.get("symbol", "")
            if not sym.endswith("USDT"): continue
            base = sym.replace("USDT", "")
            if base in ("USDC", "BUSD", "FDUSD", "TUSD", "DAI", "USDP", "GUSD"):
                continue
            try:
                chg = float(g.get("priceChangePercent", 0))
                vol = float(g.get("quoteVolume", 0))
                price = float(g.get("lastPrice", 0))
            except:
                continue

            if 3 <= chg <= 15 and vol >= 500000 and price >= 0.001:
                candidates.append({"symbol": base, "pair": sym, "change": chg, "volume": vol, "price": price})

        # Sort by volume descending
        candidates.sort(key=lambda x: -x["volume"])

        if not candidates:
            print("No valid entry candidates found (3-15% gainers with volume)")
            return

        print(f"Top 5 candidates by volume:")
        for c in candidates[:5]:
            print(f"  {c['symbol']:8s} +{c['change']:+.1f}%  vol=${c['volume']/1e6:.1f}M  ${c['price']:.4f}")

        # Check RSI and volume confirmation for top candidate
        top = candidates[0]
        klines = get_klines(top["pair"])
        if klines:
            closes = [float(k[4]) for k in klines]
            rsi_val = calc_rsi(closes)

            # Volume check: current volume vs 7-day average
            current_vol = top["volume"]
            vol_klines = get_klines(top["pair"], "1d", 8)
            if vol_klines and len(vol_klines) >= 2:
                avg_vol = sum(float(k[5]) for k in vol_klines[-7:]) / 7
                vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
            else:
                vol_ratio = 0

            print(f"\nAnalyzing top candidate {top['symbol']}:")
            print(f"  RSI(4h): {rsi_val:.1f}  |  Vol ratio: {vol_ratio:.1f}x")

            if rsi_val >= 70:
                print(f"  ❌ RSI {rsi_val:.1f} >= 70 — too hot, skip")
                return

            if vol_ratio < 1.5:
                print(f"  ❌ Volume ratio {vol_ratio:.1f}x < 1.5x — no volume confirmation")
                return

            # ENTRY SIGNAL!
            qty = POSITION_SIZE / top["price"]
            print(f"\n🟢 ENTRY SIGNAL: BUY {top['symbol']} ${POSITION_SIZE}")
            print(f"  Entry: ${top['price']:.4f} × {qty:.4f}")
            print(f"  Stop: ${top['price'] * (1+STOP_LOSS):.4f} (-4%)")
            print(f"  Target: ${top['price'] * (1+TAKE_PROFIT):.4f} (+8%)")

            # Calculate quantity from position size
            import math
            raw_qty = POSITION_SIZE / top["price"]
            
            # Get LOT_SIZE info
            ex_info = api_get("/api/v3/exchangeInfo", {"symbol": top["pair"]})
            step_size = 0.00001  # default
            min_qty = 0.00001
            if ex_info and "symbols" in ex_info and ex_info["symbols"]:
                filters = ex_info["symbols"][0]["filters"]
                for f in filters:
                    if f["filterType"] == "LOT_SIZE":
                        step_size = float(f["stepSize"])
                        min_qty = float(f["minQty"])
                        break
            
            # Round to step size
            precision = int(round(-math.log10(step_size)))
            qty_rounded = math.floor(raw_qty / step_size) * step_size
            qty_rounded = round(qty_rounded, precision)
            
            if qty_rounded < min_qty:
                print(f"  ❌ Qty {qty_rounded:.8f} < min {min_qty}")
                return
            # Execute buy using aws_executor
            import sys
            sys.path.insert(0, '/home/ubuntu/zq_web4_trading_system/production/engine')
            from aws_executor import buy_market, load_auth
            ak, a_sec = load_auth()
            result = buy_market(ak, a_sec, top["symbol"], POSITION_SIZE)

            if "_error" not in result:
                fill_price = float(result.get("fills", [{}])[0].get("price", top["price"])) if result.get("fills") else top["price"]
                filled_qty = float(result.get("executedQty", qty))
                log_trade("BUY", top["symbol"], fill_price, filled_qty, "entry_signal")
                print(f"  ✅ Buy executed! Filled @ ${fill_price:.4f} x {filled_qty:.4f}")
            else:
                print(f"  ❌ Buy failed: {result.get('_error')} - {result.get('_msg','')}")
        else:
            print(f"❌ Cannot fetch K-line for {top['pair']}")
    else:
        print(f"USDT ${usdt:.2f} < min position ${POSITION_SIZE} — skip entry")

    print(f"\n=== Cycle complete ===")

if __name__ == "__main__":
    main()
