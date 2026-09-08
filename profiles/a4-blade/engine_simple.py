#!/usr/bin/env python3
"""
A4 Blade — 极简交易引擎 v1
============================
3条规则进场 + 2条规则出场 + 硬止损。零Agent零架子零E系列。

进场（全满足就买）：
  1. 24h涨幅 3-15%（刚启动不是已泵顶）
  2. 成交量 ≥ 1.5x 均量（有真实资金进入）
  3. RSI(4h) < 70（不是超买区追高）

出场（满足任一就卖）：
  1. RSI(4h) > 85（P1信号，唯一验证62.7%正确）
  2. -5%硬止损（判断错了必须出）

持有：在涨就拿着，有更好的标的+仓位满就卖最弱的换
"""
import json, os, time, sys
from datetime import datetime, timezone, timedelta
from typing import Optional
import urllib.request
import urllib.error

BJT = timezone(timedelta(hours=8))
now = lambda: datetime.now(BJT).strftime('%Y-%m-%d %H:%M BJT')

# === Config ===
MAX_POSITIONS = 4
MIN_VOLUME_USD = 30_000
STOP_LOSS_PCT = -5.0
RSI_SELL_THRESHOLD = 85
RSI_BUY_MAX = 70
ENTRY_GAIN_MIN = 3.0
ENTRY_GAIN_MAX = 15.0
VOLUME_SURGE_MIN = 1.5
CYCLE_SECONDS = 30 * 60  # 30 minutes
# 🔴 2026-07-22 加仓策略：USDT极低(<$10)时，优先从盈利仓位释放资金
# 当USDT < $10时，如果某个仓位P&L>+10%，卖它来换弹药
# 而非死握盈利仓位+卖亏损仓位做轮换
CAPITAL_FREE_USDT_THRESHOLD = 10.0
PROFIT_SELL_TO_FREE_PCT = 10.0  # 盈利>10%的仓位优先卖
# 🔴 2026-07-22 幻影卖单抑制：同一symbol连续生成>3次sell信号且未执行→静默抑制
PHANTOM_SELL_HISTORY = {}  # {symbol: count}

ZQ_ROOT = os.path.expanduser("~/zq_web4_trading_system")
SIGNAL_DIR = os.path.join(ZQ_ROOT, "data", "signals")
TRADES_PATH = os.path.join(ZQ_ROOT, "audit", "TRADES.md")
STATE_PATH = os.path.join(ZQ_ROOT, "data", "node_state.json")
BALANCE_PATH = os.path.join(ZQ_ROOT, "data", "balance_cache.json")

os.makedirs(SIGNAL_DIR, exist_ok=True)

# === Helpers ===

def http_get(url, timeout=10):
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}

def rsi_from_klines(klines, period=14):
    """Calculate RSI from klines data."""
    closes = [float(k[4]) for k in klines]
    if len(closes) < period + 1:
        return 50.0
    gains, losses = 0, 0
    for i in range(-period, 0):
        diff = closes[i] - closes[i-1]
        if diff > 0: gains += diff
        else: losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0: return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

# === Binance API ===

def fetch_24hr_ticker():
    """Fetch Binance 24hr ticker data."""
    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = http_get(url, timeout=15)
    if isinstance(data, dict) and "error" in data:
        return data
    # Filter USDT pairs with tradeable volume
    candidates = []
    for t in data:
        symbol = t.get("symbol", "")
        if not symbol.endswith("USDT"): continue
        if any(x in symbol for x in ["DOWN", "UP", "BULL", "BEAR"]): continue
        try:
            vol = float(t.get("quoteVolume", 0))
            chg = float(t.get("priceChangePercent", 0))
            price = float(t.get("lastPrice", 0))
        except (ValueError, TypeError):
            continue
        if vol < MIN_VOLUME_USD: continue
        candidates.append({
            "symbol": symbol.replace("USDT", ""),
            "full_symbol": symbol,
            "price": price,
            "volume_24h": vol,
            "change_24h": chg
        })
    return candidates

def fetch_klines_4h(symbol, limit=30):
    """Fetch 4h klines for RSI calculation."""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=4h&limit={limit}"
    return http_get(url, timeout=10)

def fetch_balance():
    """Fetch Binance account balance via API."""
    # This needs API keys - for now use local cache
    # On AWS this uses the real API
    return None

# === Signal Generation ===

def scan_candidates(ticker_data):
    """Scan top gainers and filter by 3 rules."""
    if isinstance(ticker_data, dict) and "error" in ticker_data:
        return {"error": ticker_data["error"], "candidates": []}
    
    # Sort by change_24h descending
    sorted_coins = sorted(ticker_data, key=lambda x: x["change_24h"], reverse=True)
    
    candidates = []
    for coin in sorted_coins[:50]:  # Top 50 gainers
        chg = coin["change_24h"]
        vol = coin["volume_24h"]
        
        # Rule 1: 3-15% gain
        if chg < ENTRY_GAIN_MIN or chg > ENTRY_GAIN_MAX:
            continue
        
        # Need klines for RSI and volume baseline
        klines = fetch_klines_4h(coin["symbol"])
        if isinstance(klines, dict) and "error" in klines:
            continue
        
        # Rule 2: volume ≥ 1.5x baseline
        closes = [float(k[4]) for k in klines]
        volumes = [float(k[7]) for k in klines]
        avg_vol = sum(volumes) / len(volumes) if volumes else 0
        last_vol = volumes[-1] if volumes else 0
        
        volume_ratio = last_vol / avg_vol if avg_vol > 0 else 1
        if volume_ratio < VOLUME_SURGE_MIN:
            continue
        
        # Rule 3: RSI(4h) < 70
        rsi = rsi_from_klines(klines)
        if rsi >= RSI_BUY_MAX:
            continue
        
        candidates.append({
            "symbol": coin["symbol"],
            "price": coin["price"],
            "change_24h": chg,
            "volume_24h": vol,
            "volume_ratio": round(volume_ratio, 2),
            "rsi_4h": round(rsi, 1),
            "score": round(chg * 0.4 + min(volume_ratio, 5) * 0.3 + (70 - rsi) * 0.3, 1)
        })
    
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return {"candidates": candidates[:MAX_POSITIONS]}

def check_exit_signals(holdings):
    """Check P1 (RSI>85) and -5% stop loss for each holding.
    
    🔴 2026-07-22 幻影卖单抑制：如果同一symbol连续>3次生成SELL_ALL信号
    但持仓数不变（信号未被执行），认为是幻影单，静默跳过。
    """
    global PHANTOM_SELL_HISTORY
    signals = []
    for h in holdings:
        sym = h["symbol"]
        klines = fetch_klines_4h(sym)
        if isinstance(klines, dict) and "error" in klines:
            continue
        rsi = rsi_from_klines(klines)
        
        reason = None
        if rsi >= RSI_SELL_THRESHOLD:
            reason = f"P1(RSI={rsi:.1f}>85)"
        elif h.get("pnl_pct", 0) <= STOP_LOSS_PCT:
            reason = f"硬止损({h['pnl_pct']:.1f}%≤-5%)"
        
        if reason:
            # Phantom sell suppression: if this symbol has been >3 times
            # without the holding count actually decreasing, it's phantom
            PHANTOM_SELL_HISTORY[sym] = PHANTOM_SELL_HISTORY.get(sym, 0) + 1
            if PHANTOM_SELL_HISTORY[sym] >= 4:
                print(f"  👻 幻影卖单抑制: {sym} 已连续{PHANTOM_SELL_HISTORY[sym]}次生成SELL信号但未执行，跳过")
                continue
            signals.append({
                "symbol": sym,
                "action": "SELL_ALL",
                "reason": reason,
                "rsi": round(rsi, 1),
                "entry_price": h.get("entry_price", 0),
                "current_price": h.get("price", 0)
            })
    return signals

# === Main Cycle ===

def cycle(holdings=None, usdt=0):
    """One cycle of the engine."""
    ts = now()
    result = {"time": ts, "cycle_id": int(time.time())}
    
    # Step 1: Get market data
    print(f"\n{'='*50}")
    print(f"🔄 A4 Cycle — {ts}")
    print(f"   USDT: ${usdt:.2f} | 持仓: {len(holdings or [])}/{MAX_POSITIONS}")
    
    ticker = fetch_24hr_ticker()
    if isinstance(ticker, dict) and "error" in ticker:
        print(f"❌ Binance API不可达: {ticker['error']}")
        return {"status": "offline", "error": ticker["error"]}
    
    print(f"✅ Binance 24hr ticker: {len(ticker)} USDT对")
    
    # Step 2: Scan candidates (buy signals)
    scan = scan_candidates(ticker)
    if "error" in scan:
        print(f"⚠️ 扫描失败: {scan['error']}")
    
    candidates = scan.get("candidates", [])
    result["candidates"] = candidates
    print(f"\n📊 候选扫描:")
    if candidates:
        for c in candidates:
            print(f"   🟢 {c['symbol']}: +{c['change_24h']:.1f}% | 量比{c['volume_ratio']}x | RSI(4h)={c['rsi_4h']} | 评分{c['score']}")
    else:
        print(f"   无符合3条件的币")
    
    # Step 3: Check exit signals for holdings
    sell_signals = []
    if holdings:
        sell_signals = check_exit_signals(holdings)
        result["sell_signals"] = sell_signals
        print(f"\n📊 出场检查:")
        if sell_signals:
            for s in sell_signals:
                print(f"   🔴 {s['symbol']}: {s['reason']}")
        else:
            print(f"   无出场信号(P1/硬止损均未触发)")
    
    # Step 4: Decide actions
    actions = []
    for s in sell_signals:
        actions.append({"symbol": s["symbol"], "action": "SELL", "reason": s["reason"]})
    
    # Buy if we have USDT and candidates
    if candidates and usdt > 0:
        # Calculate position size (FNG placeholder - use 1/MAX)
        position_size = usdt / max(1, MAX_POSITIONS)
        # Only buy if not at max positions
        if len(holdings or []) < MAX_POSITIONS:
            buy = candidates[0]
            # But don't buy a coin we already hold
            holding_symbols = {h["symbol"] for h in (holdings or [])}
            for c in candidates:
                if c["symbol"] not in holding_symbols:
                    actions.append({"symbol": c["symbol"], "action": "BUY", "size": round(position_size, 2), "price": c["price"], "reason": f"+{c['change_24h']:.1f}%·量比{c['volume_ratio']}x·RSI={c['rsi_4h']}"})
                    break
    
    # Also handle rotation: if at max positions and better candidates exist
    if candidates and len(holdings or []) >= MAX_POSITIONS and not sell_signals:
        # 🔴 2026-07-22 弹药优先策略：USDT<$10时，优先卖盈利>10%的仓位释放资金
        # 而不是卖最弱的做轮换。没有弹药，有候选也买不了。
        if usdt < CAPITAL_FREE_USDT_THRESHOLD:
            profitable = [h for h in holdings if h.get("pnl_pct", 0) >= PROFIT_SELL_TO_FREE_PCT]
            if profitable:
                target = max(profitable, key=lambda h: h.get("pnl_pct", 0))
                sell_size = round(usdt + sum(h.get("qty", 0) * h.get("price", 0) * 0.3 for h in profitable if h["symbol"] == target["symbol"]), 2)
                actions.append({"symbol": target["symbol"], "action": "SELL", "reason": f"弹药释放·P&L+{target.get('pnl_pct',0):.1f}%·释放USDT约${sell_size:.1f}"})
                print(f"  🔴 {target['symbol']}: 弹药释放(P&L+{target.get('pnl_pct',0):.1f}%)·释放USDT约${sell_size:.1f}")
                # Don't add buy rotation — free capital first
            else:
                print(f"  ⚠️ USDT仅${usdt:.2f}，无盈利>10%的仓位可释放")
        else:
            # Standard rotation: check if best candidate is better than worst holding
            holding_symbols = {h["symbol"] for h in (holdings or [])}
            for c in candidates:
                if c["symbol"] not in holding_symbols:
                    # Found a better opportunity but no room - sell weakest holding
                    weakest = min(holdings, key=lambda h: h.get("pnl_pct", 0))
                    if weakest.get("pnl_pct", 0) < 0:
                        actions.append({"symbol": weakest["symbol"], "action": "SELL", "reason": f"轮换→{c['symbol']}(评分{c['score']})"})
                        actions.append({"symbol": c["symbol"], "action": "BUY", "size": round(position_size, 2), "price": c["price"], "reason": f"轮换·+{c['change_24h']:.1f}%·量比{c['volume_ratio']}x"})
                    break
    
    result["actions"] = actions
    
    print(f"\n📋 执行计划:")
    if actions:
        for a in actions:
            print(f"   {'🟢' if a['action']=='BUY' else '🔴'} {a['action']} {a['symbol']}: {a.get('reason','')}")
    else:
        print(f"   无操作")
    
    # Step 5: Write signal file
    signal = {
        "generated_at": ts,
        "cycle_id": result["cycle_id"],
        "usdt_balance": usdt,
        "positions_count": len(holdings or []),
        "buy_signals": [a for a in actions if a["action"] == "BUY"],
        "sell_signals": [a for a in actions if a["action"] == "SELL"],
        "candidates": [{"symbol": c["symbol"], "score": c["score"], "change_24h": c["change_24h"], "rsi_4h": c["rsi_4h"]} for c in candidates],
        "status": "offline" if isinstance(ticker, dict) and "error" in ticker else "ok"
    }
    
    sig_path = os.path.join(SIGNAL_DIR, "a4_signals.json")
    with open(sig_path, "w") as f:
        json.dump(signal, f, indent=2)
    
    result["status"] = "ok"
    return result

# === CLI ===

if __name__ == "__main__":
    print("🧊 A4 Blade — 极简交易引擎 v1")
    print(f"   规则: 涨幅{ENTRY_GAIN_MIN}-{ENTRY_GAIN_MAX}% + 量比≥{VOLUME_SURGE_MIN}x + RSI<{RSI_BUY_MAX}")
    print(f"   出场: P1(RSI>{RSI_SELL_THRESHOLD})或-{abs(STOP_LOSS_PCT)}%硬止损")
    print()
    
    # Try to load existing state
    holdings = []
    usdt = 0
    if os.path.exists(BALANCE_PATH):
        try:
            with open(BALANCE_PATH) as f:
                bal = json.load(f)
            usdt = bal.get("usdt", 0)
            holdings = bal.get("holdings", [])
        except: pass
    
    # Load phantom sell history
    phantom_path = os.path.join(ZQ_ROOT, "data", "phantom_sell_history.json")
    if os.path.exists(phantom_path):
        try:
            with open(phantom_path) as f:
                loaded_history = json.load(f)
                PHANTOM_SELL_HISTORY.clear()
                PHANTOM_SELL_HISTORY.update(loaded_history)
        except:
            pass
    
    result = cycle(holdings=holdings, usdt=usdt)
    
    print(f"\n{'='*50}")
    print(f"✅ Cycle完成 | 状态: {result.get('status', '?')}")
    
    # Save state
    with open(STATE_PATH, "w") as f:
        json.dump({"last_cycle": result.get("cycle_id"), "time": now(), "status": result.get("status")}, f, indent=2)
    
    # Save phantom sell history (persist across cycles)
    phantom_path = os.path.join(ZQ_ROOT, "data", "phantom_sell_history.json")
    try:
        with open(phantom_path, "w") as f:
            json.dump(PHANTOM_SELL_HISTORY, f, indent=2)
    except:
        pass
    
    # Auto-run loop if in background mode
    if "--daemon" in sys.argv:
        print(f"\n🔄 守护模式: 每{CYCLE_SECONDS//60}分钟循环一次")
        while True:
            time.sleep(CYCLE_SECONDS)
            # Reload state
            if os.path.exists(BALANCE_PATH):
                try:
                    with open(BALANCE_PATH) as f:
                        bal = json.load(f)
                    usdt = bal.get("usdt", 0)
                    holdings = bal.get("holdings", [])
                except: pass
            result = cycle(holdings=holdings, usdt=usdt)
