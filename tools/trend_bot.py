#!/usr/bin/env python3
"""
ZQ ETH 趋势通道 v3.1 (Donchian 5日突破 + 2%盈利锁定) — 每日盈利导向
====================================================================
核心理念：不做网格。只在趋势确认时持有 ETH，趋势破坏时全部回到 USDT。
网格的宿命（已在 2026-07-20 ~ 08-31 实盘 + 回测双重验证）：
  - 单边上涨：网格一路卖出，吃不到主升浪
  - 单边下跌：网格一路接飞刀（08-19 单日接刀买入 $517）
  - 震荡：资金单向流失→只剩卖单死锁（08-31 上午 USDT 仅 $15）
  - 硬止损 6 周内 0 次触发（下跌平移把止损线跟着下移）

本策略（v3.1 = 老李指令「每日盈利策略」定案，2026-08-31 本地回测验证）：
  - ENTRY：价格 > 近 5 日(120根已收盘1h K线)最高价 → 市价全仓买入 ETH
  - EXIT1：价格 < 近 5 日最低价 → 市价全仓卖出 ETH 锁 USDT（通道破位，v3.0保留）
  - EXIT2：1h收盘价 自入场以来峰值回落 ≥ 2% → 市价全仓卖出 ETH 锁利（盈利锁定层，v3.1新增）
  - 回测对比（06-09→08-31 真实行情含0.1%手续费，1h收盘口径独立复测）：
      原版v3.0    +35.3% | 2笔兑现 | 胜率— | 最大回撤 -6.9%
      v3.1(2%锁利) +27.2% | 7笔兑现 | 胜率57% | 最大回撤 -3.3%
    v3.1用 ~8pt 总收益换 3.5x 兑现频次 + 一半回撤：更贴合「每日盈利」目标。
  - 状态仅 mode(eth/cash)，崩溃重启安全：每周期重新拉K线算通道。

配置改动后改 CFG_VERSION → 强制撤单 + 状态重置，防旧订单残留。
"""
import json, hmac, hashlib, time, os, urllib.request, ssl, urllib.parse
from datetime import datetime

# ===== CONFIG =====
SYMBOL = 'ETHUSDT'
CHANNEL_BARS = 120          # 5日 = 120根1hK线 (2026-08-31 回测定稿)
KLINE_LIMIT = CHANNEL_BARS + 2   # 多拉2根，丢弃最后一根未收盘K线
MIN_NOTIONAL = 5.0
USDT_RESERVE = 2.0          # 买入时留$2缓冲（防滑点/精度）
TRAIL_PCT = 0.02            # v3.1 盈利锁定：1h收盘自入场峰值回落≥2% → 全仓卖出锁利
CFG_VERSION = "2026-08-31-donchian-v3.1-trail-r2"   # r2: 部署修正——强制撤掉遗留网格单+状态重置

AUTH_PATH = os.path.expanduser("~/zq_web4_trading_system/config/auth.json")
STATE_FILE = os.path.expanduser("~/zq_web4_trading_system/data/trades/trend_state.json")
TRADES_LOG = os.path.expanduser("~/zq_web4_trading_system/data/trades/trend_trades.jsonl")
LOG_FILE = os.path.expanduser("~/zq_web4_trading_system/logs/trend_bot.log")
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open(AUTH_PATH) as f:
    _auth = json.load(f)["binance"]

def log(msg):
    # cron把stdout重定向到logs/trend_bot.log, 这里只print避免重复写档
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)

def record_trade(side, price, qty, reason, entry_price=None, pnl=None, equity=None):
    """每笔成交写 ledger (data/trades/trend_trades.jsonl)，供日盈亏验证。"""
    rec = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "side": side, "symbol": SYMBOL,
        "price": round(price, 2), "qty": round(qty, 6),
        "usdt_value": round(qty * price, 2),
        "reason": reason,
        "entry_price": round(entry_price, 2) if entry_price else None,
        "pnl": round(pnl, 2) if pnl is not None else None,
        "equity": round(equity, 2) if equity is not None else None,
    }
    try:
        with open(TRADES_LOG, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        log(f"⚠️ record_trade failed: {str(e)[:80]}")

def _api(method, path, params=None, signed=False):
    if params is None: params = {}
    base = "https://api.binance.com"
    if signed:
        params["timestamp"] = int(time.time() * 1000)
        qs0 = urllib.parse.urlencode(sorted(params.items()))
        sig = hmac.new(_auth["api_secret"].encode(), qs0.encode(), hashlib.sha256).hexdigest()
    if method == "GET":
        qs = urllib.parse.urlencode(sorted(params.items()))
        url = f"{base}{path}?{qs}"
        if signed: url += f"&signature={sig}"
        req = urllib.request.Request(url)
    else:
        qs = urllib.parse.urlencode(sorted(params.items()))
        data = qs.encode()
        if signed: data = qs.encode() + f"&signature={sig}".encode()
        url = f"{base}{path}"
        req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("X-MBX-APIKEY", _auth["api_key"])
    req.add_header("User-Agent", "ZQ-TrendBot/3.0")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()[:200]}
    except Exception as e:
        return {"_error": str(e)[:200]}

def get_price():
    t = _api("GET", "/api/v3/ticker/price", {"symbol": SYMBOL})
    return float(t["price"]) if "_error" not in t else None

def get_channel():
    """返回 (channel_high, channel_low, n_bars, last_closed_close)。只用已收盘K线。"""
    k = _api("GET", "/api/v3/klines", {"symbol": SYMBOL, "interval": "1h", "limit": KLINE_LIMIT})
    if "_error" in k or not isinstance(k, list) or len(k) < CHANNEL_BARS:
        return None, None, 0, None
    closed = k[:-1]  # 丢弃最后一根（未收盘）
    win = closed[-CHANNEL_BARS:]
    hi = max(float(x[2]) for x in win)
    lo = min(float(x[3]) for x in win)
    last_close = float(closed[-1][4])
    return hi, lo, len(win), last_close

def get_balances():
    a = _api("GET", "/api/v3/account", signed=True)
    if "_error" in a:
        return None, None
    bal = {}
    for b in a["balances"]:
        if b["asset"] in ("ETH", "USDT"):
            bal[b["asset"]] = {"free": float(b["free"]), "locked": float(b["locked"])}
    usdt = bal.get("USDT", {"free": 0})["free"]
    eth = bal.get("ETH", {"free": 0})["free"]
    return usdt, eth

def cancel_open_orders():
    ts = int(time.time() * 1000)
    params = {"symbol": SYMBOL, "timestamp": ts}
    qs = urllib.parse.urlencode(sorted(params.items()))
    sig = hmac.new(_auth["api_secret"].encode(), qs.encode(), hashlib.sha256).hexdigest()
    data = qs.encode() + f"&signature={sig}".encode()
    req = urllib.request.Request("https://api.binance.com/api/v3/openOrders", data=data, method="DELETE")
    req.add_header("X-MBX-APIKEY", _auth["api_key"])
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        r = json.loads(resp.read())
        return len(r) if isinstance(r, list) else 0
    except Exception as e:
        log(f"⚠️ cancel_open_orders failed: {str(e)[:80]}")
        return 0

def market_order(side, qty):
    if os.environ.get("TREND_DRY_RUN") == "1":
        log(f"  🧪 DRY_RUN: would {side} {qty} {SYMBOL} at market")
        return True, {"dry_run": True}
    r = _api("POST", "/api/v3/order", {
        "symbol": SYMBOL, "side": side, "type": "MARKET", "quantity": qty
    }, signed=True)
    if "_error" in r:
        return False, r
    return True, r

def run():
    log("=" * 60)
    log("ZQ TrendBot v3.1 Donchian 5d + 2% profit lock — cycle start")

    price = get_price()
    if not price:
        log("❌ No price (API error), skip")
        return

    hi, lo, n, last_close = get_channel()
    if hi is None:
        log("❌ No channel data (API error), skip")
        return

    # ---- state ----
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except Exception:
            state = {}

    if state.get("cfg_version") != CFG_VERSION:
        n_cancelled = 0 if os.environ.get("TREND_DRY_RUN") == "1" else cancel_open_orders()
        log(f"🔄 CFG change ({state.get('cfg_version', 'none')} → {CFG_VERSION}): cancelled {n_cancelled} old grid orders, state reset")
        state = {"cfg_version": CFG_VERSION}

    usdt, eth = get_balances()
    if usdt is None:
        log("❌ Account API error, skip")
        return
    equity = usdt + eth * price

    # 首次启动(无状态)时按实际持仓初始化模式:
    # 账户持有ETH → eth模式(现有持仓立即纳入退出保护); 否则 cash模式
    if "mode" not in state:
        if eth * price > MIN_NOTIONAL:
            mode = "eth"
            log("  🔄 Fresh start: account holds ETH — init mode ETH (exit rule active)")
        else:
            mode = "cash"
            log("  🔄 Fresh start: no ETH held — init mode CASH (entry rule active)")
        state = {"mode": mode, "cfg_version": CFG_VERSION}
    else:
        mode = state.get("mode", "cash")

    log(f"  price ${price:.2f} | channel {n}h: high ${hi:.2f} low ${lo:.2f} | last1hClose ${last_close:.2f} | mode {mode.upper()} | USDT ${usdt:.2f} ETH {eth:.4f} (${eth*price:.2f})")
    log(f"  equity(ETH+USDT) ${equity:.2f}")

    acted = False
    if mode == "cash":
        if price > hi:
            buy_usdt = max(usdt - USDT_RESERVE, 0.0)
            qty = int(buy_usdt / price / 0.0001) * 0.0001
            if qty * price < MIN_NOTIONAL:
                log(f"  ⚠️ Entry notional too small (${qty*price:.2f}), skip")
            else:
                ok, r = market_order("BUY", round(qty, 4))
                if ok:
                    log(f"  ✅ ENTRY: bought {qty:.4f} ETH @ ~${price:.2f} (${qty*price:.2f}) — breakout above ${hi:.2f}")
                    record_trade("BUY", price, qty, f"breakout above channel high ${hi:.2f}", equity=usdt + eth * price)
                    state = {"mode": "eth", "cfg_version": CFG_VERSION, "entry_price": price,
                             "entry_qty": round(qty, 4), "channel_high": hi, "peak_close": price}
                    acted = True
                else:
                    log(f"  ❌ ENTRY failed: {str(r)[:120]}")
        else:
            log(f"  💤 CASH: price ${price:.2f} ≤ channel high ${hi:.2f}, wait for breakout")

    elif mode == "eth":
        if eth * price < MIN_NOTIONAL:
            log(f"  🔄 mode=ETH but no ETH in account (${eth*price:.2f}) — auto switch to CASH")
            state = {"mode": "cash", "cfg_version": CFG_VERSION}
        else:
            # v3.1 盈利锁定层：跟踪自入场以来的 1h 收盘峰值
            peak = max(float(state.get("peak_close", price)), last_close)
            state["peak_close"] = peak
            trail_level = peak * (1 - TRAIL_PCT)

            exit_reason = None
            if price < lo:
                exit_reason = f"breakdown below channel low ${lo:.2f}"
            elif last_close < trail_level:
                exit_reason = (f"profit lock: 1h close ${last_close:.2f} fell {TRAIL_PCT:.0%} "
                               f"from peak ${peak:.2f} (level ${trail_level:.2f})")

            if exit_reason:
                qty = int(eth / 0.0001) * 0.0001
                if qty * price < MIN_NOTIONAL:
                    log(f"  ⚠️ Exit notional too small (${qty*price:.2f}), skip")
                else:
                    ok, r = market_order("SELL", round(qty, 4))
                    if ok:
                        log(f"  ✅ EXIT ({exit_reason}): sold {qty:.4f} ETH @ ~${price:.2f} (${qty*price:.2f})")
                        entry_price = state.get("entry_price")
                        pnl = (price - entry_price) * qty if entry_price else None
                        record_trade("SELL", price, qty, exit_reason, entry_price=entry_price, pnl=pnl, equity=usdt + eth * price)
                        state = {"mode": "cash", "cfg_version": CFG_VERSION, "exit_price": price,
                                 "exit_qty": round(qty, 4), "exit_reason": exit_reason, "channel_low": lo}
                        acted = True
                    else:
                        log(f"  ❌ EXIT failed: {str(r)[:120]}")
            else:
                log(f"  💤 HOLD ETH: price ${price:.2f} ≥ low ${lo:.2f} | peak(1h) ${peak:.2f}, trail level ${trail_level:.2f} — ride the trend")
    else:
        log(f"  ⚠️ Unknown mode '{mode}', reset to cash")
        state = {"mode": "cash", "cfg_version": CFG_VERSION}

    state["ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["price"] = price
    state["channel_high"] = hi
    state["channel_low"] = lo
    if state.get("mode") == "eth":
        state["peak_close"] = max(float(state.get("peak_close", price)), last_close)
        state["trail_pct"] = TRAIL_PCT
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    log(f"  📝 state saved: mode={state.get('mode')} ts={state['ts']}")

    log(f"  done | mode now {state.get('mode', 'cash').upper()}")

if __name__ == "__main__":
    run()
