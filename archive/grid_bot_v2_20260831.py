#!/usr/bin/env python3
"""
ZQ ETH 自适应网格 v2.0 — 趋势跟踪版
=======================================
核心改进：
1. 趋势检测：价格持续超出网格范围时自动平移(re-center)
2. 集中资金：先清掉SOL/AAVE/DEXE等散仓，全部进ETH网格
3. 每档放大到$8-10，利润更高
"""

import json, hmac, hashlib, time, math, os, sys, urllib.request, ssl, urllib.parse
from datetime import datetime, timezone, timedelta

# ===== CONFIG =====
SYMBOL = 'ETHUSDT'
GRID_RANGE_PCT = 0.025        # ±2.5% (官方黄金法则: 参考7日波动, 太窄频繁中断)
GRID_LEVELS = 4               # 4买+4卖 (2026-08-31: 3→4, 档距更小→每日成交频率更高)
INVEST_USDT_PER_LEVEL = 20.0  # $20/档buy (4档=$80, 官方法则: 全部资金入网格)
MIN_NOTIONAL = 5.0

# 网格配置版本 — 改配置后强制撤单重挂, 防止旧参数挂单残留锁死资金
GRID_CFG_VERSION = "2026-08-31-symmetric-v4"

# 趋势跟踪参数
TREND_CHECK_COUNT = 3         # 连续N次检查超出范围→触发平移
TREND_COOLDOWN_MIN = 30       # 平移后至少30分钟才能再平移
PRICE_HISTORY_MAX = 12        # 保存最近12次价格(60分钟)

# ===== 市场模式 =====
# MODE_GRID: 网格模式（震荡市，默认）
# MODE_HOLD: 持有模式（上涨趋势，取消买单，只卖不买）
# MODE_CASH: 现金模式（下跌趋势，取消卖单，只持有U）
MODE_GRID = "grid"
MODE_HOLD = "hold"
MODE_CASH = "cash"
MODE_STOPPED = "stopped"  # 硬止损: 已清仓, 等待恢复

# 模式切换阈值
UP_TREND_PCT = 0.03           # 连续涨超3%→切HOLD
DOWN_TREND_PCT = -0.04        # 连续跌超4%→切CASH
STABLE_PCT = 0.015            # 回到震荡区间±1.5%→切回GRID

# ===== 硬止损 (2026-08-08 参谋审查通过) =====
# 网格数学宿命: 震荡/上涨赚, 单边暴跌亏(回测-30%段亏$42)
# 硬止损 = 跌破中心6%→清仓ETH锁USDT, 避免跌穿下沿满仓套死
HARD_STOP_PCT = 0.06          # 跌破网格中心6%触发
STOP_RESUME_PCT = 0.98        # 价格回到中心98%(即-2%内)才可恢复(参谋:0.95太松会接飞刀)
STOP_COOLDOWN_H = 48          # 清仓后48小时内不重复清仓(防死猫跳反复割肉)
STOP_CONFIRM_COUNT = 2        # 连续2次检查(10分钟)确认

AUTH_PATH = os.path.expanduser("~/zq_web4_trading_system/config/auth.json")
STATE_FILE = os.path.expanduser("~/zq_web4_trading_system/data/trades/grid_state.json")
TRADES_PATH = os.path.expanduser("~/zq_web4_trading_system/audit/TRADES.md")
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open(AUTH_PATH) as f:
    _auth = json.load(f)["binance"]

def _api(method, path, params=None, signed=False):
    if params is None: params = {}
    base = "https://api.binance.com"
    if signed:
        params["timestamp"] = int(time.time() * 1000)
        qs = urllib.parse.urlencode(sorted(params.items()))
        sig = hmac.new(_auth["api_secret"].encode(), qs.encode(), hashlib.sha256).hexdigest()
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
    req.add_header("User-Agent", "ZQ-Grid/2.0")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()[:200]}
    except Exception as e:
        return {"_error": str(e)[:200]}

def get_price():
    t = _api("GET", "/api/v3/ticker/price", {"symbol": SYMBOL})
    return float(t["price"]) if "_error" not in t else None

def cancel_all_orders():
    """Cancel all open ETHUSDT orders"""
    ts = int(time.time() * 1000)
    params = {"symbol": SYMBOL, "timestamp": ts}
    qs = urllib.parse.urlencode(sorted(params.items()))
    sig = hmac.new(_auth["api_secret"].encode(), qs.encode(), hashlib.sha256).hexdigest()
    data = qs.encode() + f"&signature={sig}".encode()
    req = urllib.request.Request(
        "https://api.binance.com/api/v3/openOrders", data=data, method="DELETE")
    req.add_header("X-MBX-APIKEY", _auth["api_key"])
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        result = json.loads(resp.read())
        cancelled = len(result) if isinstance(result, list) else 0
        print(f"  🗑️ Cancelled {cancelled} old orders")
        return cancelled
    except Exception as e:
        print(f"  ⚠️ Cancel failed: {str(e)[:60]}")
        return 0

def place(side, price, qty):
    qty = round(qty, 4)
    price = round(price, 2)
    r = _api("POST", "/api/v3/order", {
        "symbol": SYMBOL, "side": side,
        "type": "LIMIT", "timeInForce": "GTC",
        "price": str(price), "quantity": str(qty)
    }, signed=True)
    if "_error" not in r:
        print(f"  ✅ {side:4s} {qty:.4f} ETH @ ${price:.2f}  (id={r['orderId']})")
        return r["orderId"]
    else:
        msg = r.get('_msg', '')[:80]
        if "NOTIONAL" in msg:
            print(f"  ⚠️ {side:4s} @ ${price:.2f} — NOTIONAL too small")
        else:
            print(f"  ❌ {side:4s} @ ${price:.2f} — {msg}")
        return None

def calc_grid(center_price):
    """Calculate grid levels centered on a given price"""
    lo = center_price * (1 - GRID_RANGE_PCT)
    hi = center_price * (1 + GRID_RANGE_PCT)
    step = (hi - lo) / (GRID_LEVELS * 2 + 1)

    buys = []
    sells = []
    for i in range(GRID_LEVELS):
        bp = round(center_price * (1 - (i + 1) * GRID_RANGE_PCT / GRID_LEVELS) / 5) * 5
        sp = round(center_price * (1 + (i + 1) * GRID_RANGE_PCT / GRID_LEVELS) / 5) * 5
        if bp < center_price:
            buys.append(bp)
        if sp > center_price:
            sells.append(sp)

    buys = sorted(set(buys))[:GRID_LEVELS]
    sells = sorted(set(sells))[:GRID_LEVELS]
    return buys, sells, round(lo), round(hi)

def determine_mode(state, price):
    """Determine market mode based on recent price action"""
    history = state.get("price_history", [])
    mode = state.get("mode", MODE_GRID)

    # ===== 硬止损检测 (优先于一切模式) =====
    center = state.get("center_price", price)
    stop_ts = state.get("stop_ts", 0)
    stop_triggered = state.get("stop_triggered", False)
    now = time.time()

    # 已触发止损: 检查恢复条件
    if stop_triggered:
        # 冷却期内不恢复
        if now - stop_ts < STOP_COOLDOWN_H * 3600:
            return MODE_STOPPED
        # 冷却期满: 价格回到 center*0.95 以上才恢复GRID
        if price >= center * STOP_RESUME_PCT:
            state["stop_triggered"] = False
            state["stop_ts"] = 0
            print("  🔄 Hard stop cooldown passed & price recovered — resuming GRID")
            return MODE_GRID
        return MODE_STOPPED

    # 未触发: 检查是否跌破硬止损线
    if len(history) >= 3:
        if price < center * (1 - HARD_STOP_PCT):
            stop_count = state.get("stop_count", 0) + 1
            state["stop_count"] = stop_count
            if stop_count >= STOP_CONFIRM_COUNT:
                state["stop_triggered"] = True
                state["stop_ts"] = now
                state["stop_count"] = 0
                state["stop_price"] = price
                stop_line = center * (1 - HARD_STOP_PCT)
                print("  🛑 HARD STOP triggered! Price " + str(round(price,2)) + " < center*0.94 (" + str(round(stop_line,2)) + ")")
                print("  🛑 Clearing all ETH to USDT, trading paused for " + str(STOP_COOLDOWN_H) + "h cooldown")
                return MODE_STOPPED
            return mode
        else:
            state["stop_count"] = 0

    if len(history) < 3:
        return mode

    # Price change over last 3 checks (~15 min)
    pct_change = (price - history[0]) / history[0]

    # Uptrend detection: consecutive higher highs
    recent_3 = history[-3:] + [price]
    up_streak = all(recent_3[i] < recent_3[i+1] for i in range(len(recent_3)-1))

    # Downtrend detection: consecutive lower lows
    down_streak = all(recent_3[i] > recent_3[i+1] for i in range(len(recent_3)-1))

    # Price relative to center
    center = state.get("center_price", price)
    dist_from_center = (price - center) / center

    if mode == MODE_GRID:
        # Switch to HOLD: strong uptrend
        if pct_change > UP_TREND_PCT and up_streak:
            print(f"  🚀 Uptrend detected (+{pct_change*100:.1f}%) — switching to HOLD mode")
            return MODE_HOLD
        # Switch to CASH: strong downtrend
        if pct_change < DOWN_TREND_PCT and down_streak:
            print(f"  📉 Downtrend detected ({pct_change*100:.1f}%) — switching to CASH mode")
            return MODE_CASH
        return MODE_GRID

    elif mode == MODE_HOLD:
        # Switch back to GRID: price stabilizes near center
        if abs(dist_from_center) < STABLE_PCT and not up_streak:
            print(f"  🔄 Price stabilized near center — switching back to GRID mode")
            return MODE_GRID
        # Switch to CASH: trend reverses
        if pct_change < DOWN_TREND_PCT and down_streak:
            print(f"  📉 Trend reversed — switching to CASH mode")
            return MODE_CASH
        return MODE_HOLD

    elif mode == MODE_CASH:
        # Switch back to GRID: price stabilizes
        if abs(dist_from_center) < STABLE_PCT:
            print(f"  🔄 Price stabilized — switching back to GRID mode")
            return MODE_GRID
        return MODE_CASH

    return MODE_GRID

def should_recenter(state, price, buys, sells):
    """Check if grid should re-center due to price trend"""
    grid_min = min(buys) if buys else price * 0.9
    grid_max = max(sells) if sells else price * 1.1

    # Track price history
    history = state.get("price_history", [])
    history.append(price)
    if len(history) > PRICE_HISTORY_MAX:
        history = history[-PRICE_HISTORY_MAX:]
    state["price_history"] = history

    # Count consecutive out-of-range checks
    above_count = state.get("above_count", 0)
    below_count = state.get("below_count", 0)

    if price > grid_max:
        above_count += 1
        below_count = 0
    elif price < grid_min:
        below_count += 1
        above_count = 0
    else:
        above_count = 0
        below_count = 0

    state["above_count"] = above_count
    state["below_count"] = below_count

    # Check cooldown
    last_recenter = state.get("last_recenter_ts", 0)
    now = time.time()
    if now - last_recenter < TREND_COOLDOWN_MIN * 60:
        remaining = int(TREND_COOLDOWN_MIN * 60 - (now - last_recenter))
        if above_count >= TREND_CHECK_COUNT or below_count >= TREND_CHECK_COUNT:
            print(f"  ⏳ Trend detected but in cooldown ({remaining}s left)")
        return False

    # Trigger re-center
    if above_count >= TREND_CHECK_COUNT:
        print(f"  🚀 UPTREND: {above_count}x above grid max ${grid_max}")
        return True
    if below_count >= TREND_CHECK_COUNT:
        print(f"  📉 DOWNTREND: {below_count}x below grid min ${grid_min}")
        return True

    return False

def run():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"  ZQ Grid v2.0 自适应 — {ts}")
    print(f"{'='*60}")

    price = get_price()
    if not price:
        print("❌ No price")
        return

    # Load state
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except:
            state = {}

    # ===== 网格配置版本迁移 (2026-08-31) =====
    # 卖档从固定0.003ETH(≈$7)改为对称$20/档 → 旧参数挂单全部作废, 强制撤单重挂,
    # 防止"买$20/卖$7"的USDT单向流失→ETH重仓死锁复发
    if state.get("grid_cfg_version") != GRID_CFG_VERSION and not state.get("stop_triggered", False):
        print(f"  🔄 Grid config changed ({state.get('grid_cfg_version', 'old')} → {GRID_CFG_VERSION}): cancelling all orders")
        cancel_all_orders()
        state["grid_cfg_version"] = GRID_CFG_VERSION
        state["stopped_liquidated"] = False

    # ===== 硬止损状态恢复 (2026-08-08 参谋审查: 防重启后止损失效) =====
    # AWS重启后python内存丢失, 必须从state文件读回stop_triggered/stop_ts
    # 若冷却期内重启 → 强制保持STOPPED, 直到冷却期满且价格恢复
    try:
        st_ts = state.get("stop_ts", 0)
        st_trig = state.get("stop_triggered", False)
        if st_trig and st_ts and (time.time() - st_ts) < STOP_COOLDOWN_H * 3600:
            state["mode"] = MODE_STOPPED
            state["stopped_liquidated"] = True  # 已清过仓, 不重复清
            remaining_h = int((STOP_COOLDOWN_H * 3600 - (time.time() - st_ts)) / 3600)
            print(f"  🛑 Restored STOPPED state (cooldown {remaining_h}h remaining)")
    except Exception:
        pass

    # Calculate current grid
    center = state.get("center_price", price)
    # If center is stale (more than 6h old), reset to current price
    last_ts = state.get("ts", "")
    if last_ts:
        try:
            last_dt = datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S")
            if (datetime.now() - last_dt).total_seconds() > 21600:  # 6h
                center = price
        except:
            center = price

    buys, sells, grid_lo, grid_hi = calc_grid(center)

    print(f"\n  ETH: ${price:.2f}")
    print(f"  Grid center: ${center:.0f}")
    print(f"  Range: ${grid_lo} ~ ${grid_hi}")
    print(f"  Buys:  {', '.join(f'${p}' for p in buys)}")
    print(f"  Sells: {', '.join(f'${p}' for p in sells)}")

    # ---- TREND CHECK ----
    # STOPPED时跳过re-center(价格在止损位下方, 不重挂网格)
    if state.get("stop_triggered", False):
        pass
    elif should_recenter(state, price, buys, sells):
        print(f"\n  🔄 Re-centering grid to ${price:.0f}...")
        cancel_all_orders()
        center = price
        buys, sells, grid_lo, grid_hi = calc_grid(center)
        state["last_recenter_ts"] = time.time()
        state["above_count"] = 0
        state["below_count"] = 0
        print(f"  New center: ${center:.0f} | Range: ${grid_lo} ~ ${grid_hi}")

    # ---- MARKET MODE CHECK ----
    current_mode = determine_mode(state, price)
    prev_mode = state.get("mode", MODE_GRID)
    mode_changed = current_mode != prev_mode

    if mode_changed:
        print(f"\n  🔄 Mode: {prev_mode.upper()} → {current_mode.upper()}")
        cancel_all_orders()
        if current_mode == MODE_GRID:
            # Re-center and place fresh grid
            center = price
            state["center_price"] = price
            buys, sells, grid_lo, grid_hi = calc_grid(center)
            state["stopped_liquidated"] = False
            print(f"  New grid center: ${center:.0f}")
        elif current_mode == MODE_HOLD:
            # Hold mode: cancel buys, keep ETH, let sells ride
            print(f"  HOLD mode: buys cancelled, will re-place sells only")
        elif current_mode == MODE_CASH:
            # Cash mode: sell all ETH
            print(f"  CASH mode: will sell all ETH")
        elif current_mode == MODE_STOPPED:
            # Stop mode: handled above (liquidate + pause)
            print(f"  STOPPED mode: hard stop active")
    else:
        print(f"  Mode: {current_mode.upper()}")

    state["mode"] = current_mode

    # In HOLD mode: skip buy orders entirely
    skip_buys = (current_mode == MODE_HOLD) or (current_mode == MODE_STOPPED)
    # In CASH mode: skip both buys and sells
    skip_sells = (current_mode == MODE_CASH) or (current_mode == MODE_STOPPED)

    # ===== 硬止损清仓 (首次进入STOPPED时) =====
    if current_mode == MODE_STOPPED and not state.get("stopped_liquidated", False):
        print("  🛑 STOPPED mode: liquidating all ETH to USDT...")
        cancel_all_orders()
        try:
            acc_l = _api("GET", "/api/v3/account", signed=True)
            eth_total = 0.0
            for b in acc_l["balances"]:
                if b["asset"] == "ETH":
                    eth_total = float(b["free"]) + float(b["locked"])
            if eth_total > 0.001:
                qty = round(eth_total, 4)
                r = _api("POST", "/api/v3/order", {
                    "symbol": SYMBOL, "side": "SELL", "type": "MARKET",
                    "quantity": qty
                }, signed=True)
                if "_error" in r:
                    print("  ❌ Liquidate failed: " + str(r["_error"])[:80])
                else:
                    print("  ✅ Liquidated " + str(qty) + " ETH @ market")
            else:
                print("  ℹ️ ETH too small to liquidate")
        except Exception as e:
            print("  ❌ Liquidate error: " + str(e))
        state["stopped_liquidated"] = True
        state["mode"] = current_mode
        state["ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        return

    # ---- GET ACCOUNT ----
    a = _api("GET", "/api/v3/account", signed=True)
    if "_error" in a:
        print("❌ Account error")
        return
    bal = {}
    for b in a["balances"]:
        f, l = float(b["free"]), float(b["locked"])
        if f + l > 0: bal[b["asset"]] = {"free": f, "locked": l, "total": f + l}

    usdt = bal.get("USDT", {"total": 0})["total"]
    eth_total = bal.get("ETH", {"total": 0})["total"]
    eth_free = bal.get("ETH", {"free": 0})["free"]
    print(f"  USDT: ${usdt:.2f} | ETH: {eth_total:.4f} (${eth_total*price:.2f}) | Total: ${usdt+eth_total*price:.2f}")

    # ---- GET ORDERS ----
    orders = _api("GET", "/api/v3/openOrders", {"symbol": SYMBOL}, signed=True)
    if "_error" in orders: orders = []
    have_buy = set()
    have_sell = set()
    for o in orders:
        p = round(float(o["price"]), 2)
        if o["side"] == "BUY": have_buy.add(p)
        else: have_sell.add(p)
    print(f"  Active: {len(orders)} ({len(have_buy)} buy / {len(have_sell)} sell)")

    # ---- RECONCILE STALE ORDERS (2026-08-04 fix) ----
    # 任何不在当前目标网格价位的挂单都是历史残留（旧center/旧参数），会锁死资金：
    # 实案 08-03: center刷新到$1869后，08-01的$1720-1810买单未撤 → $105 USDT锁死
    # → 新买单$1830-1860每次-2010 insufficient balance → 3天0成交。
    # 每个cycle主动对账：目标价位 = buys ∪ sells，之外的订单一律撤掉。
    target_prices = set(buys) | set(sells)
    stale_orders = [o for o in orders if round(float(o["price"]), 2) not in target_prices]
    if stale_orders:
        stale_prices = sorted(set(round(float(o["price"]), 2) for o in stale_orders))
        print(f"  🧹 Reconciling {len(stale_orders)} stale orders (outside grid {stale_prices}) → cancel")
        cancel_all_orders()
        have_buy = set()
        have_sell = set()
        orders = []

    # ---- PLACE ORDER CHUNKS ----
    step_size = 0.0001
    # Sell orders (use locked + free ETH, but locked might be in old orders)
    # After cancel, everything should be free
    locked_eth = bal.get("ETH", {"locked": 0})["locked"]
    actual_free = eth_total - locked_eth  # what we can actually use
    print(f"  ETH free: {actual_free:.4f} (locked: {locked_eth:.4f})")

    # Sell orders — 对称网格(2026-08-31): 卖单金额≈买单金额($20/档),
    # 解决旧版"买$20/卖$7"的USDT单向流失→ETH重仓死锁 (08-31上午实况)
    sell_eth_available = actual_free - 0.003  # buffer
    new_sells = 0
    for sp in sells:
        if skip_sells:
            print(f"  💤 CASH mode: skipping sell @ ${sp}")
            break
        if sp in have_sell:
            continue
        raw_qty = INVEST_USDT_PER_LEVEL / sp
        sqty = math.floor(raw_qty / step_size) * step_size
        if sqty * sp < MIN_NOTIONAL:
            sqty = math.ceil(MIN_NOTIONAL / sp / step_size) * step_size
        sqty = round(sqty, 4)
        if sell_eth_available < sqty:
            # 动态缩档(卖侧): ETH不足时按可用缩量, 网格保持双向运转
            scaled = math.floor(sell_eth_available / step_size) * step_size
            scaled = round(scaled, 4)
            if scaled * sp >= MIN_NOTIONAL:
                sqty = scaled
                print(f"  🔽 Scaled sell @ ${sp} to {sqty:.4f} ETH (${sqty*sp:.2f}, have {sell_eth_available:.4f})")
            else:
                print(f"  ⚠️ ETH too low for sell @ ${sp} (need {sqty:.4f}, have {sell_eth_available:.4f})")
                continue
        if place("SELL", sp, sqty):
            new_sells += 1
            sell_eth_available -= sqty

    # Buy orders (use USDT) — 动态缩档(2026-08-31): 资金不足时缩小单档金额而不是跳过,
    # 解决"ETH重仓+USDT不足"导致的只能卖不能买死锁 (08-31实况: 需$19.8/档但只有$13.12)
    usdt_free = bal.get("USDT", {"free": 0})["free"]
    usdt_available = usdt_free - 2  # buffer (use FREE not total: existing buys lock USDT)
    new_buys = 0
    for bp in buys:
        if skip_buys:
            if mode_changed or prev_mode == MODE_GRID:
                print(f"  💤 HOLD mode: skipping buy @ ${bp}")
            break
        if bp in have_buy:
            continue
        if usdt_available < MIN_NOTIONAL:
            print(f"  ⚠️ USDT too low for buy @ ${bp}")
            continue
        raw_qty = INVEST_USDT_PER_LEVEL / bp
        qty = math.floor(raw_qty / step_size) * step_size
        if qty * bp < MIN_NOTIONAL:
            qty = math.ceil(MIN_NOTIONAL / bp / step_size) * step_size
        if qty * bp < MIN_NOTIONAL:
            qty = math.ceil(MIN_NOTIONAL / bp * 1.05 / step_size) * step_size
        qty = round(qty, 4)
        cost = qty * bp
        if usdt_available < cost:
            # 动态缩档: 按可用资金缩小买单, 网格保持双向运转
            scaled_qty = math.floor(usdt_available / bp / step_size) * step_size
            scaled_qty = round(scaled_qty, 4)
            if scaled_qty * bp >= MIN_NOTIONAL:
                qty = scaled_qty
                cost = qty * bp
                print(f"  🔽 Scaled buy @ ${bp} to {qty:.4f} ETH (${cost:.2f}, have ${usdt_available:.2f})")
            else:
                print(f"  ⚠️ Need ${cost:.2f} USDT for buy @ ${bp}, have ${usdt_available:.2f}")
                continue
        if place("BUY", bp, qty):
            new_buys += 1
            usdt_available -= cost

    # ---- 台账: 网格成交写入TRADES.md (#24修复) ----
    log_fills(state)

    # ---- SAVE STATE ----
    state.update({
        "ts": ts,
        "center_price": center,
        "price": price,
        "usdt": usdt,
        "eth": eth_total,
        "total": usdt + eth_total * price,
        "active_orders": len(orders),
        "new_buys": new_buys,
        "new_sells": new_sells,
        "buy_levels": buys,
        "sell_levels": sells,
        "grid_low": grid_lo,
        "grid_high": grid_hi,
    })
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    final_orders = _api("GET", "/api/v3/openOrders", {"symbol": SYMBOL}, signed=True)
    final_count = len(final_orders) if "_error" not in final_orders else "?"
    print(f"\n  📊 +{new_buys} buy / +{new_sells} sell | {final_count} active orders")


# ===== 台账记录: 网格成交写入TRADES.md (2026-08-31 修复#24) =====
BJT = timezone(timedelta(hours=8))

def log_fills(state):
    """查询Binance myTrades, 将ETHUSDT网格成交追加到 audit/TRADES.md。
    用 state['last_trade_id'] 增量记录, 避免重复/漏记。"""
    last_id = state.get("last_trade_id", 0)
    try:
        if last_id == 0:
            # 首次运行: 只记录当前最新成交ID, 不回填历史
            latest = _api("GET", "/api/v3/myTrades", {"symbol": SYMBOL, "limit": 1}, signed=True)
            if "_error" not in latest and latest:
                state["last_trade_id"] = int(latest[-1]["id"])
            return 0
        trades = _api("GET", "/api/v3/myTrades", {"symbol": SYMBOL, "fromId": last_id, "limit": 100}, signed=True)
        if "_error" in trades:
            print(f"  ⚠️ myTrades查询失败: {str(trades['_error'])[:60]}")
            return 0
        new_trades = [t for t in trades if int(t["id"]) > last_id]
        if not new_trades:
            return 0
        logged = 0
        for t in new_trades:
            ts_bjt = datetime.fromtimestamp(int(t["time"]) / 1000, tz=BJT).strftime("%Y-%m-%d %H:%M")
            side = "BUY" if t.get("isBuyer") else "SELL"
            price = float(t["price"])
            qty = float(t["qty"])
            notional = float(t.get("quoteQty", price * qty))
            trade_line = f"""### {ts_bjt} BJT | 网格Grid
| 字段 | 值 |
|:-----|:---|
| 指令来源 | ETH网格 {GRID_CFG_VERSION} |
| 币种 | ETH |
| 方向 | {side} |
| 执行价 | ${price:.2f} |
| 执行量 | {qty:.4f} ETH (${notional:.2f}) |
| 原因 | 网格成交 |
| PnL | ?% |
| 状态 | ✅ FILLED |
"""
            os.makedirs(os.path.dirname(TRADES_PATH), exist_ok=True)
            with open(TRADES_PATH, "a") as f:
                f.write(trade_line + "\n")
            logged += 1
            print(f"  📒 网格{side}入账: {qty:.4f} ETH @ ${price:.2f} (${notional:.2f})")
        state["last_trade_id"] = int(new_trades[-1]["id"])
        return logged
    except Exception as e:
        print(f"  ⚠️ 台账记录异常: {str(e)[:80]}")
        return 0

if __name__ == "__main__":
    run()

