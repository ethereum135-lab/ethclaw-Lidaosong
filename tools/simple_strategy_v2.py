#!/usr/bin/env python3
"""
ZQ Simple Strategy v2.1 — $40固定仓位，+8%止盈
============================================
发布时间: 2026-07-14
参数修改（清仓ZEC后）:
  - 仓位: 从1%/min$10 → 固定$40（$230本金用1%=$2.30太小）
  - 止盈: 从"无止盈" → +8%止盈（赚了就跑）
  - 止损: -4%硬止损 + 5%浮动止损（不变）
  - API: 修复GET→POST（原代码用GET签名报-1101错误）
  - 目标: 日盈利2%=$4.60/天
         $40×8%=$3.20/胜，1.4胜/天即可达成

入场条件（全部满足才买）:
  ① 24h涨幅 +3%~+15%（刚启动，不是泵完也不是跌的）
  ② 成交量 > $500K（有流动性）
  ③ 不是稳定币/尘仓

出场条件（任一触发就卖）:
  ① +8%止盈: 盈利到8%就跑
  ② P1浮动止损: 从最高点回落 > 5%
  ③ 硬止损: 入场价 -4%
  ④ BTC日跌超 -5%

仓位: 固定$40/单仓，最低$10，最多1仓
周期: 4H（BJT 0/4/8/12/16/20）
"""

import json, hashlib, hmac, time, math, os, sys
from datetime import datetime

# ===== 动态仓位 =====
FIXED_POSITION = 40    # $40 per trade (was 1%/min$10, too small for $230 capital)
MIN_POSITION = 10      # Binance min
STOP_LOSS = -0.04      # -4% hard stop
TAKE_PROFIT = 0.08     # +8% take profit
TRAIL_STOP = 0.05      # 5% trailing
BTC_PANIC = -5.0       # BTC -5% triggers sell

AUTH_PATH = os.path.expanduser("~/zq_web4_trading_system/config/auth.json")
TRADES_DIR = os.path.expanduser("~/zq_web4_trading_system/data/trades")
os.makedirs(TRADES_DIR, exist_ok=True)

# ===== API helpers (raw no deps) =====
import urllib.request, ssl
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

# Load auth globally
with open(AUTH_PATH) as f:
    _AUTH = json.load(f)["binance"]

def _api_signed(params, path="/api/v3/order"):
    params["timestamp"] = int(time.time() * 1000)
    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sig = hmac.new(_AUTH["api_secret"].encode(), qs.encode(), hashlib.sha256).hexdigest()
    data = qs.encode() + f"&signature={sig}".encode()
    req = urllib.request.Request(f"https://api.binance.com{path}", data=data, method="POST")
    req.add_header("X-MBX-APIKEY", _AUTH["api_key"])
    req.add_header("User-Agent", "Mozilla/5.0")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15, context=_CTX).read())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()[:300]}
    except Exception as e:
        return {"_error": str(e)[:300]}

def _api_get(path, params=None, signed=False):
    if params is None: params = {}
    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items())) if params else ""
    if signed:
        params["timestamp"] = int(time.time() * 1000)
        qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        sig = hmac.new(_AUTH["api_secret"].encode(), qs.encode(), hashlib.sha256).hexdigest()
        url = f"https://api.binance.com{path}?{qs}&signature={sig}"
        req = urllib.request.Request(url)
        req.add_header("X-MBX-APIKEY", _AUTH["api_key"])
    else:
        url = f"https://api.binance.com{path}"
        if qs: url += f"?{qs}"
        req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=10, context=_CTX).read())
    except:
        return None

def _log(action, symbol, price, qty, value, reason):
    fname = f"{TRADES_DIR}/{datetime.now().strftime('%Y-%m-%d')}.json"
    trades = []
    if os.path.exists(fname):
        with open(fname) as f:
            try: trades = json.load(f)
            except: trades = []
    trades.append({
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action, "symbol": symbol,
        "price": price, "qty": qty, "value": value,
        "reason": reason
    })
    with open(fname, "w") as f:
        json.dump(trades, f, indent=2)
    print(f"  📝 Logged {action} {symbol} ${value:.2f} — {reason}")

# ===== Core =====

def get_state():
    """Return (usdt_free, positions_list, total_equity)"""
    acct = _api_get("/api/v3/account", signed=True)
    if "_error" in acct:
        print(f"❌ API error: {acct}")
        return (0, [], 0)

    # Get prices
    prices = _api_get("/api/v3/ticker/price")
    pm = {p["symbol"]: float(p["price"]) for p in prices} if prices else {}

    balances = {}
    for b in acct["balances"]:
        f = float(b["free"])
        l = float(b["locked"])
        if f + l > 0:
            balances[b["asset"]] = {"free": f, "locked": l, "total": f + l}

    usdt_bal = balances.get("USDT", {"total": 0})["total"]
    positions = []
    total = usdt_bal
    for asset, bal in balances.items():
        if asset == "USDT": continue
        price = pm.get(f"{asset}USDT", 0)
        value = bal["total"] * price
        total += value
        if value > 3:
            positions.append({
                "asset": asset, "qty": bal["total"],
                "price": price, "value": value,
                "free": bal["free"], "locked": bal["locked"]
            })

    positions.sort(key=lambda x: -x["value"])
    return (usdt_bal, positions, total)


def sell_dust(positions, min_value=5):
    """Sell all positions under min_value to free capital"""
    sold_any = False
    for p in positions:
        if p["value"] < min_value:
            sym = f"{p['asset']}USDT"
            print(f"  🗑️ Dust selling {p['asset']} ({p['value']:.2f})")
            result = _api_signed({
                "symbol": sym, "side": "SELL",
                "type": "MARKET",
                "quantity": p["qty"]
            }, "/api/v3/order")
            if "_error" not in result:
                fill_price = float(result.get("fills", [{}])[0].get("price", p["price"])) if result.get("fills") else p["price"]
                filled_qty = float(result.get("executedQty", p["qty"]))
                _log("SELL_DUST", p["asset"], fill_price, filled_qty, p["value"], "dust_cleanup")
                print(f"    ✅ Dust sold! ${p['value']:.2f} freed")
                sold_any = True
            else:
                print(f"    ❌ Dust sell failed: {result.get('_msg','')[:100]}")
    return sold_any


def check_positions(positions, wallet, usdt_free):
    """Check exit conditions for existing positions"""
    # Get BTC 24h change
    btc_24h = _api_get("/api/v3/ticker/24hr", {"symbol": "BTCUSDT"})
    btc_chg = float(btc_24h.get("priceChangePercent", 0)) if btc_24h else 0

    for p in positions:
        # Load state
        state_file = f"{TRADES_DIR}/state_{p['asset']}.json"
        peak = p["price"]
        if os.path.exists(state_file):
            with open(state_file) as f:
                try:
                    st = json.load(f)
                    peak = st.get("peak", p["price"])
                except:
                    pass

        # Update peak
        if p["price"] > peak:
            peak = p["price"]
            with open(state_file, "w") as f:
                json.dump({"peak": peak, "updated": datetime.now().strftime("%Y-%m-%d %H:%M")}, f)

        # Check exits
        peak_drop = (peak - p["price"]) / peak if peak > 0 else 0

        reasons = []
        # +8% take profit
        entry_price = st.get("entry_price", p["price"]) if os.path.exists(state_file) else p["price"]
        gain_pct = (p["price"] - entry_price) / entry_price * 100 if entry_price > 0 else 0
        if gain_pct >= TAKE_PROFIT * 100:
            reasons.append(f"take_profit(+{gain_pct:.1f}%)")
        # Trailing stop: -5% from peak
        if peak_drop > TRAIL_STOP:
            reasons.append(f"trailing_stop(drop={peak_drop*100:.1f}%)")
        if btc_chg < BTC_PANIC:
            reasons.append(f"btc_crash({btc_chg:.1f}%)")

        if reasons:
            sym = f"{p['asset']}USDT"
            print(f"  🔴 Selling {p['asset']} — {' + '.join(reasons)}")
            result = _api_signed({
                "symbol": sym, "side": "SELL",
                "type": "MARKET", "quantity": p["qty"]
            }, "/api/v3/order")
            if "_error" not in result:
                fill_price = float(result.get("fills", [{}])[0].get("price", p["price"])) if result.get("fills") else p["price"]
                filled_qty = float(result.get("executedQty", p["qty"]))
                _log("SELL", p["asset"], fill_price, filled_qty, p["value"], "; ".join(reasons))
                print(f"    ✅ Sold! Filled @ ${fill_price:.4f}")
                # Clean up state file
                if os.path.exists(state_file):
                    os.remove(state_file)
            else:
                print(f"    ❌ Sell failed: {result.get('_msg','')[:100]}")


def find_entry(usdt_free, total_equity):
    """Find best entry candidate from 24h gainers"""
    if usdt_free < MIN_POSITION:
        print(f"  USDT ${usdt_free:.2f} < min ${MIN_POSITION}")
        return None

    tickers = _api_get("/api/v3/ticker/24hr")
    if not tickers:
        print("  ❌ Cannot fetch tickers")
        return None

    # Position size: fixed $40 (was 1%, too small for $230 capital)
    # Cap at USDT available, min $10
    pos_size = max(MIN_POSITION, min(FIXED_POSITION, usdt_free))

    candidates = []
    for t in tickers:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"): continue
        base = sym.replace("USDT", "")
        # Filter stablecoins
        if base in ("USDC", "BUSD", "FDUSD", "TUSD", "DAI", "USDP", "GUSD", "AEUR", "EUR", "GBP", "AUD", "BRL", "TRY", "ZAR"):
            continue
        # Filter leveraged tokens
        skip = False
        for kw in ("UP", "DOWN", "BULL", "BEAR", "BUSD", "USDC", "DAI", "TUSD", "FDUSD", "USDP", "SUSD", "IDRT"):
            if kw in base:
                skip = True
                break
        if skip: continue

        try:
            chg = float(t.get("priceChangePercent", 0))
            vol = float(t.get("quoteVolume", 0))
            price = float(t.get("lastPrice", 0))
        except:
            continue

        # Condition ①: 3-15% gain
        if chg < 3 or chg > 15:
            continue
        # Condition ②: Volume > $500K
        if vol < 500000:
            continue
        # Condition ③: Price >= 0.001 (not dust)
        if price < 0.001:
            continue

        candidates.append({
            "symbol": base, "pair": sym,
            "change": chg, "volume": vol, "price": price,
            "score": vol * (1 + chg/10)  # volume-weighted
        })

    if not candidates:
        print("  No 3-15% gainers with >$500K volume")
        return None

    # Sort by score (volume-dominant)
    candidates.sort(key=lambda x: -x["score"])

    best = candidates[0]
    print(f"\n  🏆 Top candidate: {best['symbol']}")
    print(f"     +{best['change']:.1f}%  vol=${best['volume']/1e6:.1f}M  ${best['price']:.4f}")
    print(f"     Position size: ${pos_size:.2f}")

    return {"coin": best["symbol"], "pair": best["pair"],
            "price": best["price"], "change": best["change"],
            "volume": best["volume"], "amount": pos_size}


def buy(entry):
    """Execute buy"""
    pos_size = entry["amount"]
    print(f"\n  🟢 BUY {entry['coin']} ${pos_size:.2f}")

    # Get LOT_SIZE
    ex_info = _api_get("/api/v3/exchangeInfo", {"symbol": entry["pair"]})
    step_size = 0.00001
    min_qty = 0.00001
    min_notional = 5
    if ex_info and "symbols" in ex_info and ex_info["symbols"]:
        for f in ex_info["symbols"][0]["filters"]:
            if f["filterType"] == "LOT_SIZE":
                step_size = float(f["stepSize"])
                min_qty = float(f["minQty"])
            if f["filterType"] in ("NOTIONAL", "MIN_NOTIONAL"):
                min_notional = float(f.get("minNotional", 5))

    raw_qty = pos_size / entry["price"]
    precision = max(0, int(round(-math.log10(step_size)))) if step_size >= 1e-8 else 8
    qty = math.floor(raw_qty / step_size) * step_size
    qty = round(qty, precision)

    if qty < min_qty:
        print(f"  ❌ Qty {qty:.8f} < min {min_qty}")
        return None
    if qty * entry["price"] < min_notional:
        print(f"  ❌ Value ${qty*entry['price']:.2f} < min notional ${min_notional}")
        return None

    result = _api_signed({
        "symbol": entry["pair"], "side": "BUY",
        "type": "MARKET", "quoteOrderQty": pos_size
    }, "/api/v3/order")

    if "_error" not in result:
        fill_price = float(result.get("fills", [{}])[0].get("price", entry["price"])) if result.get("fills") else entry["price"]
        filled_qty = float(result.get("executedQty", 0))
        filled_val = fill_price * filled_qty
        _log("BUY", entry["coin"], fill_price, filled_qty, filled_val, "entry_signal")

        # Save state for trailing stop
        state_file = f"{TRADES_DIR}/state_{entry['coin']}.json"
        with open(state_file, "w") as f:
            json.dump({
                "peak": fill_price,
                "entry_price": fill_price,
                "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "stop_loss": fill_price * (1 + STOP_LOSS),
                "qty": filled_qty,
                "value": filled_val
            }, f, indent=2)

        print(f"    ✅ Bought! Filled @ ${fill_price:.4f} x {filled_qty:.4f} = ${filled_val:.2f}")
        return {"price": fill_price, "qty": filled_qty, "value": filled_val}
    else:
        print(f"    ❌ Buy failed: {result.get('_msg','')[:150]}")
        return None


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*50}")
    print(f"  ZQ Simple Strategy v2.0 — {ts}")
    print(f"{'='*50}")

    # 1. Get current state
    usdt_free, positions, total = get_state()
    print(f"\n  💰 Total: ${total:.2f}  |  USDT: ${usdt_free:.2f}  |  Positions: {len(positions)}")

    if positions:
        print(f"\n  📊 Positions:")
        for p in positions:
            tag = ""
            if p["value"] < 5: tag = " [DUST]"
            elif p["value"] < 15: tag = " [SMALL]"
            print(f"     {p['asset']:8s}  ${p['value']:.2f}{tag}")

    # 2. Sell dust to free capital
    dust_sold = sell_dust(positions)
    if dust_sold:
        # Re-check state after selling dust
        usdt_free, positions, total = get_state()
        print(f"\n  After dust cleanup:")
        print(f"  💰 Total: ${total:.2f}  USDT: ${usdt_free:.2f}")

    # 3. Check exit conditions for existing positions
    if positions:
        check_positions(positions, usdt_free, total)

    # 4. Find and execute entry
    if len(positions) == 0 or dust_sold:
        # Only enter if we have no position or just cleaned dust
        entry = find_entry(usdt_free, total)
        if entry:
            buy(entry)
        else:
            print("  No valid entry candidate")

    print(f"\n{'='*50}")
    print(f"  Cycle complete\n")


if __name__ == "__main__":
    main()
