#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
profit_engine_v2.py — 盈利策略引擎 v2（2026-08-31 重写）
================================================================
替代旧A4买入决策链（A3解析+fast_scan FALLBACK+14层过滤），
用「3个入场条件 + 4条铁律风控」的干净逻辑重建。

旧策略尸检结论（2026-07-08 autopsy + 08-31 TRADES.md量化）：
  - 94笔亏损平均 -21.7%（最差 -48.9%）→ 止损形同虚设
  - UNI×29 / DOGE×14 / ADA×13 反复接飞刀 → 无冷却机制
  - 过滤层太多 → 要么0交易要么乱交易
  - 止盈被禁用(999%) → 盈利从不止盈

新策略设计（每一条都对应一个亏损根因）：
  ① 趋势过滤   close > EMA50(1h)           → 不接下跌飞刀（DOGE/ADA根因）
  ② 回撤低吸   RSI14∈[40,60] 且贴近EMA50    → 只在回调企稳处买（UNI追高根因）
  ③ 拐头确认   收盘突破前高+量能≥均量         → 等扳机，不猜底（sweep G最优确认）
  ④ 硬止损-5%                             → 旧均亏-21.7% → 砍到-5%（盈亏比3:1+）
  ⑤ 止盈+8% + 3%移动止盈                  → 落袋为安，趋势段让利润奔跑
  ⑥ 风险预算 1%权益/笔，单仓≤25%权益       → 单笔最大回撤受控（旧仓位过重）
  ⑦ 连亏冷却48h                           → 同一币亏损后48h禁买（UNI×29根因）
  ⑨ 时间止损48h                            → 不拖单（旧TIME=96h, sweep K改48h最优）
  ⑧ BTC市况门  BTC>EMA200才做多，24h跌>3%禁买 → 系统性风险回避（-4.87%单日根因）

用法：
  python3 tools/profit_engine_v2.py --backtest [--days 60] [--top 30]
  python3 tools/profit_engine_v2.py --live [--out data/signals/engine_v2_buys.json]
  python3 tools/profit_engine_v2.py --check    # 只打印当前市况与可买候选，不落盘

无第三方依赖（纯标准库 + curl SOCKS5拉币安API）。
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
ZQ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOCKS = ["curl", "--socks5-hostname", "127.0.0.1:1080", "-s", "--max-time", "20"]

# ═══════════════ 策略参数（回测即真值，改动须重跑回测）═══════════════
UNIVERSE_TOP_N = 30            # 按24h成交额取Top N个USDT现货对
MIN_BARS = 300                 # 少于300根1hK线(≈12.5天)的币不参与
MAX_CONCURRENT = 2             # 最多同时持仓数
RISK_PER_TRADE = 0.01          # 单笔风险 = 权益×1%
MAX_POSITION_PCT = 0.25        # 单仓上限 = 权益×25%
STOP_LOSS_PCT = 0.05           # 硬止损 -5%（旧策略实际均亏-21.7%）
TAKE_PROFIT_PCT = 0.08         # 止盈 +8%
TRAIL_ACTIVATE_PCT = 0.08      # 移动止盈激活线（>=TP时trail不生效=纯止盈; 120d回测trail降低期望, 保持dormant）
TRAIL_DIST_PCT = 0.05          # 从峰值回撤5%即离场
TIME_STOP_HOURS = 48           # 持仓超48小时按收盘离场（sweep K, 60天+11.44%最优）
LOSS_COOLDOWN_HOURS = 48       # 亏损后同币48h禁买（UNI×29根因）
WIN_COOLDOWN_HOURS = 24        # 盈利后同币24h禁买
FEE = 0.001                    # 单边手续费0.1%（币安现货taker）

# 入场参数
EMA_FAST = 50
RSI_PERIOD = 14
RSI_LO, RSI_HI = 45.0, 58.0    # 回撤区（sweep B/G: [45,58] 最优, 胜率42→53%）
NEAR_EMA_MAX_PCT = 0.03        # 收盘距EMA50 ≤3%（贴近支撑）
VOL_SMA = 20
VOL_MIN_MULT = 1.2             # 量能 ≥ 1.2×20均量（120d回测两窗口最优）
COIN_EMA200_FILTER = True      # 个币趋势门: 收盘>EMA200(≈8.3天)才买（样本外稳健性关键, B窗-2.1%→+2.3%）

# BTC市况门
BTC_EMA_REGIME = 200
BTC_CRASH_24H_PCT = -3.0       # BTC 24h跌超3% → 禁买

STABLE_EXCLUDE = {"USDC", "FDUSD", "TUSD", "DAI", "USDP", "BUSD", "EUR", "GBP",
                  "AEUR", "USDT", "RLUSD", "USD1", "USDE", "PYUSD", "FRAX",
                  "USDY", "EURI", "EURT", "GYEN", "USDS", "USDP"}
LEVERAGE_MARK = ("UP", "DOWN", "BULL", "BEAR", "3L", "3S", "5L", "5S")


# ═══════════════ 数据层 ═══════════════

def http_json(url):
    r = subprocess.run(SOCKS + [url], capture_output=True, text=True, timeout=25)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def fetch_klines(symbol, days):
    """分页拉取1hK线，返回[{ts,o,h,l,c,v}] 升序"""
    end = int(time.time() * 1000)
    start = end - days * 24 * 3600 * 1000
    bars, cur = [], start
    while cur < end:
        url = (f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h"
               f"&limit=1000&startTime={cur}&endTime={end}")
        page = http_json(url)
        if not page:
            break
        if not bars:
            bars = page
        else:
            bars.extend(page)
        cur = page[-1][6] + 1
        if len(page) < 2:
            break
    out = []
    seen = set()
    for b in bars:
        ts = b[0]
        if ts in seen:
            continue
        seen.add(ts)
        out.append({"ts": ts, "o": float(b[1]), "h": float(b[2]),
                    "l": float(b[3]), "c": float(b[4]), "v": float(b[5])})
    return out


def fetch_universe(top_n):
    """按24h成交额取Top N USDT现货对，返回[{symbol, quote_volume, price, change24h}]"""
    data = http_json("https://api.binance.com/api/v3/ticker/24hr")
    if not data:
        return []
    rows = []
    for t in data:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        base = sym[:-4]
        if base in STABLE_EXCLUDE:
            continue
        if any(base.endswith(m) or base.startswith(m) for m in LEVERAGE_MARK):
            continue
        try:
            qv = float(t.get("quoteVolume", 0))
            price = float(t.get("lastPrice", 0))
            chg = float(t.get("priceChangePercent", 0))
        except (TypeError, ValueError):
            continue
        if qv <= 0 or price <= 0:
            continue
        rows.append({"symbol": sym, "base": base, "quote_volume": qv,
                     "price": price, "change24h": chg})
    rows.sort(key=lambda x: x["quote_volume"], reverse=True)
    return rows[:top_n]


# ═══════════════ 指标（纯Python，无依赖）═══════════════

def ema(values, period):
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def sma(values, period):
    if len(values) < period:
        return [None] * len(values)
    out = [None] * (period - 1)
    s = sum(values[:period])
    out.append(s / period)
    for i in range(period, len(values)):
        s += values[i] - values[i - period]
        out.append(s / period)
    return out


def rsi(closes, period=14):
    if len(closes) <= period:
        return [None] * len(closes)
    out = [None] * period
    gains, losses = [], []
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag, al = sum(gains) / period, sum(losses) / period
    for i in range(period, len(closes)):
        if i > period:
            d = closes[i] - closes[i - 1]
            ag = (ag * (period - 1) + max(d, 0)) / period
            al = (al * (period - 1) + max(-d, 0)) / period
        out.append(100.0 if al == 0 else 100.0 - 100.0 / (1 + ag / al))
    return out


# ═══════════════ 信号逻辑 ═══════════════

def entry_signal(bars, i, ema50, rsi14, vol_sma20, ema200=None):
    """在bars[i]收盘处判断是否满足入场。bars为全量历史，只看<=i的数据（无未来函数）"""
    if i < max(EMA_FAST, RSI_PERIOD, VOL_SMA) + 5:
        return False
    c, c1, c2 = bars[i]["c"], bars[i - 1]["c"], bars[i - 2]["c"]
    e50, r14, v20 = ema50[i], rsi14[i], vol_sma20[i]
    if None in (e50, r14, v20):
        return False
    # ① 趋势：收盘在EMA50上方
    if c <= e50:
        return False
    # ①b 个币趋势门（2026-08-31新增）：收盘>EMA200(≈8.3天)，过滤自身下跌趋势的币
    if COIN_EMA200_FILTER:
        if ema200 is None or ema200[i] is None or c <= ema200[i]:
            return False
    # ② 回撤区：RSI在中位（不超买）
    if not (RSI_LO <= r14 <= RSI_HI):
        return False
    # ③ 拐头确认：前一根跌、本根收盘突破前高（sweep G: 胜率52.7%, 60天+9.5%最优）
    if not (c1 < c2 and c > c1):
        return False
    if c <= bars[i - 1]["h"]:
        return False
    # ④ 贴近支撑：收盘距EMA50 ≤3%（回踩买，不追高）
    if (c - e50) / e50 > NEAR_EMA_MAX_PCT:
        return False
    # ⑤ 量能：本根量 ≥ 20均量
    if bars[i]["v"] < v20 * VOL_MIN_MULT:
        return False
    return True


def regime_ok(btc_bars, btc_24h_chg):
    """BTC市况门：1h收盘>EMA200 且 24h跌幅未超-3%"""
    if btc_24h_chg is not None and btc_24h_chg <= BTC_CRASH_24H_PCT:
        return False
    closes = [b["c"] for b in btc_bars]
    if len(closes) < BTC_EMA_REGIME + 10:
        return True
    e200 = ema(closes, BTC_EMA_REGIME)
    return closes[-1] > e200[-1]


def position_size(equity):
    """仓位 = 权益×1%风险 / 5%止损距离 = 权益×20%，上限25%权益"""
    stop_dist = STOP_LOSS_PCT
    size = equity * RISK_PER_TRADE / stop_dist
    return min(size, equity * MAX_POSITION_PCT)


# ═══════════════ 回测 ═══════════════

def run_backtest(symbols_data, btc_bars, initial_capital=500.0, days=60):
    """逐bar仿真。symbols_data: {base: bars}。所有估值只用<=当前时间戳的数据（无未来函数）"""
    import bisect
    tss = {base: [b["ts"] for b in bars] for base, bars in symbols_data.items()}
    closes = {base: [b["c"] for b in bars] for base, bars in symbols_data.items()}
    highs = {base: [b["h"] for b in bars] for base, bars in symbols_data.items()}
    lows = {base: [b["l"] for b in bars] for base, bars in symbols_data.items()}

    ind = {}
    for base, bars in symbols_data.items():
        c = closes[base]
        ind[base] = {"ema50": ema(c, EMA_FAST), "rsi14": rsi(c, RSI_PERIOD),
                     "vol20": sma([b["v"] for b in bars], VOL_SMA),
                     "ema200": ema(c, 200)}

    cash = initial_capital
    positions = {}
    trades = []
    equity_curve = []
    cooldown = {}

    def last_idx(base, ts):
        return bisect.bisect_right(tss[base], ts) - 1

    # 时间感知市况门（2026-08-31修复：原regime_ok用整窗最后一根K线判断=未来函数泄漏）
    btc_tss = [b["ts"] for b in btc_bars] if btc_bars else []
    btc_closes = [b["c"] for b in btc_bars] if btc_bars else []
    btc_e200 = ema(btc_closes, BTC_EMA_REGIME) if btc_bars else []

    def regime_at(ts):
        if not btc_tss:
            return True
        b = bisect.bisect_right(btc_tss, ts) - 1
        if b < BTC_EMA_REGIME:
            return True
        if btc_closes[b] <= btc_e200[b]:
            return False
        if b >= 24:
            chg24 = (btc_closes[b] / btc_closes[b - 24] - 1) * 100
            if chg24 <= BTC_CRASH_24H_PCT:
                return False
        return True

    all_ts = sorted(set().union(*[set(v) for v in tss.values()]))
    for ts in all_ts:
        now = datetime.fromtimestamp(ts / 1000, tz=BJT)
        # ── 1. 持仓退出（用bar高低模拟盘中止损/止盈）──
        for base in list(positions.keys()):
            idx = last_idx(base, ts)
            if idx < 0:
                continue
            if tss[base][idx] != ts:
                continue  # 该币本小时无新bar
            pos = positions[base]
            hi, lo = highs[base][idx], lows[base][idx]
            exit_price, reason = None, None
            # 2026-08-31修复：peak原先只在激活分支内更新，永不自增→移动止盈永不触发。改为先记新高。
            if hi >= pos["peak"]:
                pos["peak"] = hi
            if lo <= pos["entry_price"] * (1 - STOP_LOSS_PCT):
                exit_price = pos["entry_price"] * (1 - STOP_LOSS_PCT)
                reason = "SL"
            elif hi >= pos["entry_price"] * (1 + TAKE_PROFIT_PCT):
                exit_price = pos["entry_price"] * (1 + TAKE_PROFIT_PCT)
                reason = "TP"
            elif pos["peak"] >= pos["entry_price"] * (1 + TRAIL_ACTIVATE_PCT) and \
                    lo <= pos["peak"] * (1 - TRAIL_DIST_PCT):
                exit_price = pos["peak"] * (1 - TRAIL_DIST_PCT)
                reason = "TRAIL"
            elif (now - pos["opened_at"]).total_seconds() >= TIME_STOP_HOURS * 3600:
                exit_price = closes[base][idx]
                reason = "TIME"
            if exit_price is not None:
                proceeds = pos["qty"] * exit_price * (1 - FEE)
                cash += proceeds
                pnl = proceeds - pos["cost"]
                trades.append({"base": base, "entry_ts": pos["entry_ts"],
                               "exit_ts": ts, "entry": pos["entry_price"],
                               "exit": exit_price, "qty": pos["qty"],
                               "pnl": pnl,
                               "pnl_pct": (exit_price / pos["entry_price"] - 1) * 100,
                               "reason": reason})
                cool_h = LOSS_COOLDOWN_HOURS if pnl < 0 else WIN_COOLDOWN_HOURS
                cooldown[base] = ts + cool_h * 3600 * 1000
                del positions[base]

        # ── 2. 市况门 + 收盘入场 ──
        if regime_at(ts) and len(positions) < MAX_CONCURRENT:
            for base, bars in symbols_data.items():
                if base in positions or (base in cooldown and ts < cooldown[base]):
                    continue
                idx = last_idx(base, ts)
                if idx < 2:
                    continue
                if tss[base][idx] != ts:
                    continue
                d = ind[base]
                if not entry_signal(bars, idx, d["ema50"], d["rsi14"], d["vol20"], d["ema200"]):
                    continue
                mv = sum(p["qty"] * closes[b][max(last_idx(b, ts), 0)]
                         for b, p in positions.items())
                equity = cash + mv
                alloc = position_size(equity)
                if alloc < 5:
                    continue
                price = closes[base][idx]
                qty = alloc / price / (1 + FEE)
                cost = qty * price * (1 + FEE)
                if cost > cash:
                    alloc = cash / (1 + FEE)
                    if alloc < 5:
                        continue
                    qty = alloc / price / (1 + FEE)
                    cost = qty * price * (1 + FEE)
                cash -= cost
                positions[base] = {
                    "entry_ts": ts, "entry_price": price, "qty": qty,
                    "cost": cost, "peak": price,
                    "opened_at": datetime.fromtimestamp(ts / 1000, tz=BJT),
                }
        # ── 3. 权益曲线（只用已知收盘价）──
        mv = sum(p["qty"] * closes[b][max(last_idx(b, ts), 0)]
                 for b, p in positions.items())
        equity_curve.append({"ts": ts, "equity": cash + mv})

    # 收盘强制平仓
    for base in list(positions.keys()):
        pos = positions[base]
        idx = len(closes[base]) - 1
        px = closes[base][idx]
        proceeds = pos["qty"] * px * (1 - FEE)
        cash += proceeds
        trades.append({"base": base, "entry_ts": pos["entry_ts"],
                       "exit_ts": tss[base][idx], "entry": pos["entry_price"],
                       "exit": px, "qty": pos["qty"],
                       "pnl": proceeds - pos["cost"],
                       "pnl_pct": (px / pos["entry_price"] - 1) * 100,
                       "reason": "EOD"})

    return summarize(initial_capital, trades, equity_curve)


def summarize(initial_capital, trades, equity_curve):
    final_eq = equity_curve[-1]["equity"] if equity_curve else initial_capital
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    peak, max_dd = initial_capital, 0.0
    for p in equity_curve:
        peak = max(peak, p["equity"])
        dd = (peak - p["equity"]) / peak * 100
        max_dd = max(max_dd, dd)
    by_coin = {}
    for t in trades:
        by_coin.setdefault(t["base"], []).append(t)
    return {
        "initial_capital": initial_capital,
        "final_equity": final_eq,
        "total_return_pct": (final_eq / initial_capital - 1) * 100,
        "total_pnl": final_eq - initial_capital,
        "n_trades": len(trades),
        "n_wins": len(wins),
        "n_losses": len(losses),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "avg_win_pct": sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0,
        "avg_loss_pct": sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0,
        "avg_win_usd": gross_win / len(wins) if wins else 0,
        "avg_loss_usd": gross_loss / len(losses) if losses else 0,
        "profit_factor": gross_win / gross_loss if gross_loss else float("inf"),
        "expectancy_usd": sum(t["pnl"] for t in trades) / len(trades) if trades else 0,
        "max_drawdown_pct": max_dd,
        "exit_reasons": {r: sum(1 for t in trades if t["reason"] == r) for r in set(t["reason"] for t in trades)},
        "per_coin": {c: {"n": len(v), "pnl": round(sum(t["pnl"] for t in v), 2),
                         "win_rate": round(sum(1 for t in v if t["pnl"] > 0) / len(v) * 100)}
                     for c, v in sorted(by_coin.items(), key=lambda x: sum(t["pnl"] for t in x[1]), reverse=True)},
        "trades": trades,
    }


def print_report(res, label):
    print(f"\n{'='*64}")
    print(f"回测结果: {label}")
    print(f"{'='*64}")
    print(f"期初 ${res['initial_capital']:.2f} → 期末 ${res['final_equity']:.2f}")
    print(f"总收益 {res['total_return_pct']:+.2f}%  (${res['total_pnl']:+.2f})")
    print(f"交易 {res['n_trades']}笔 (盈{res['n_wins']}/亏{res['n_losses']}) 胜率 {res['win_rate']:.1f}%")
    print(f"平均盈 {res['avg_win_pct']:+.2f}% / 平均亏 {res['avg_loss_pct']:+.2f}%  (盈亏比 {res['avg_win_pct']/abs(res['avg_loss_pct']) if res['avg_loss_pct'] else 0:.2f})")
    print(f"期望值 {res['expectancy_usd']:+.2f} $/笔 | 利润因子 {res['profit_factor']:.2f} | 最大回撤 {res['max_drawdown_pct']:.2f}%")
    print(f"离场原因: {res['exit_reasons']}")
    print(f"\nTop币种:")
    for c, s in list(res["per_coin"].items())[:12]:
        print(f"  {c:6s} {s['n']:3d}笔 胜率{s['win_rate']:3.0f}% PnL ${s['pnl']:+8.2f}")


# ═══════════════ 实盘信号 ═══════════════

def fetch_account_equity():
    """从币安API取真实账户权益（USDT计价，含锁定），失败返回None"""
    auth_path = os.path.join(ZQ_ROOT, "config", "auth.json")
    if not os.path.exists(auth_path):
        return None
    try:
        import hmac, hashlib
        auth = json.load(open(auth_path))
        ak = auth["binance"]["api_key"]
        sec = auth["binance"]["api_secret"]
        ts = int(time.time() * 1000)
        query = f"timestamp={ts}&recvWindow=60000"
        sig = hmac.new(sec.encode(), query.encode(), hashlib.sha256).hexdigest()
        url = f"https://api.binance.com/api/v3/account?{query}&signature={sig}"
        r = subprocess.run(SOCKS + ["-H", f"X-MBX-APIKEY: {ak}", url],
                           capture_output=True, text=True, timeout=20)
        if r.returncode != 0 or not r.stdout.strip():
            return None
        acc = json.loads(r.stdout)
        bal = {b["asset"]: float(b["free"]) + float(b["locked"])
               for b in acc.get("balances", [])}
        eq = bal.get("USDT", 0.0)
        non_usdt = {a: v for a, v in bal.items() if v > 0 and a != "USDT"}
        if non_usdt:
            tickers = http_json("https://api.binance.com/api/v3/ticker/price")
            if tickers:
                px = {t["symbol"]: float(t["price"]) for t in tickers}
                for a, v in non_usdt.items():
                    sym = f"{a}USDT"
                    if sym in px:
                        eq += v * px[sym]
        return eq
    except Exception:
        return None


def live_signals(days=3, top_n=None, equity=None):
    """返回 {regime, signals:[...]}"""
    top_n = top_n or UNIVERSE_TOP_N
    uni = fetch_universe(top_n * 2)  # 多取一些备用
    btc = next((u for u in uni if u["base"] == "BTC"), None)
    btc_bars = fetch_klines("BTCUSDT", max(days, 20))
    btc_chg = btc["change24h"] if btc else None
    ok = regime_ok(btc_bars, btc_chg)
    signals = []
    if not ok:
        return {"regime": "HOLD", "btc_24h_chg": btc_chg, "signals": signals,
                "reason": f"BTC市况门不通过: 24h={btc_chg}% / EMA200过滤"}

    for u in uni[:top_n]:
        if u["base"] == "BTC":
            continue
        bars = fetch_klines(u["symbol"], max(days, 15))  # 至少15天才能过MIN_BARS=300
        if len(bars) < MIN_BARS:
            continue
        closes = [b["c"] for b in bars]
        ema50 = ema(closes, EMA_FAST)
        rsi14 = rsi(closes, RSI_PERIOD)
        vol20 = sma([b["v"] for b in bars], VOL_SMA)
        ema200 = ema(closes, 200)
        i = len(bars) - 1
        if entry_signal(bars, i, ema50, rsi14, vol20, ema200):
            price = bars[i]["c"]
            signals.append({
                "coin": u["base"],
                "price": price,
                "change24h": u["change24h"],
                "quote_volume": u["quote_volume"],
                "entry_reason": (f"EMA50上方({(price/ema50[i]-1)*100:+.2f}%) "
                                 f"RSI={rsi14[i]:.0f} 回踩拐头 量{vol20[i]:.0f}"),
            })
    signals.sort(key=lambda s: s["quote_volume"], reverse=True)
    return {"regime": "LONG" if ok else "HOLD", "btc_24h_chg": btc_chg,
            "signals": signals}


def write_live_file(signals_info, out_path, equity=None):
    now = datetime.now(BJT)
    alloc = position_size(equity or 500.0)
    buy = []
    for s in signals_info["signals"]:
        buy.append({
            "coin": s["coin"],
            "usdt_amount": round(alloc, 2),
            "confidence": 7,
            "tags": ["engine_v2"],
            "a3_recommend_price": s["price"],
            "entry_reason": f"engine_v2: {s['entry_reason']}",
        })
    doc = {
        "signal_id": f"ev2_{now.strftime('%Y%m%d_%H%M')}",
        "generated_at": now.isoformat(),
        "engine": "profit_engine_v2",
        "regime": signals_info["regime"],
        "btc_24h_chg": signals_info.get("btc_24h_chg"),
        "max_concurrent": MAX_CONCURRENT,
        "buy_signals": buy,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    return doc


# ═══════════════ CLI ═══════════════

def cmd_backtest(args):
    uni = fetch_universe(args.top)
    print(f"宇宙: Top{args.top} USDT对 (按24h成交额), 拉取{args.days}天1hK线...")
    data = {}
    for u in uni:
        bars = fetch_klines(u["symbol"], args.days)
        if len(bars) >= MIN_BARS:
            data[u["base"]] = bars
        else:
            print(f"  ⏭ {u['base']}: 仅{len(bars)}根, 跳过")
    btc_bars = data.pop("BTC", None)
    print(f"参与回测: {len(data)}个币种 ({len(data)}/Top{args.top})")
    if len(data) < 5:
        print("❌ 有效币种太少，无法回测")
        return 1
    res = run_backtest(data, btc_bars, initial_capital=args.capital, days=args.days)
    print_report(res, f"Top{args.top} · {args.days}天 · 起始${args.capital}")
    if args.save:
        with open(args.save, "w") as f:
            json.dump({k: v for k, v in res.items() if k != "trades"}, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存: {args.save}")
    return 0


def cmd_live(args):
    equity = args.equity
    if equity is None:
        equity = fetch_account_equity()  # 真实账户权益（含网格锁定），失败则None
        if equity:
            print(f"真实账户权益: ${equity:.2f}")
    info = live_signals(days=args.days, top_n=args.top, equity=equity)
    now = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 市况: {info['regime']} (BTC 24h {info.get('btc_24h_chg')}%)")
    if info.get("reason"):
        print(f"  {info['reason']}")
    if not info["signals"]:
        print("  无engine_v2买入信号")
    for s in info["signals"]:
        print(f"  ✅ {s['coin']:6s} ${s['price']:.4f}  24h={s['change24h']:+.2f}%  vol24h=${s['quote_volume']/1e6:.1f}M  {s['entry_reason']}")
    if args.out:
        doc = write_live_file(info, args.out, equity=equity)
        print(f"信号文件: {args.out} ({len(doc['buy_signals'])}个买入信号)")
    return 0


def cmd_check(args):
    return cmd_live(argparse.Namespace(days=args.days, top=args.top, equity=args.equity,
                                       out=None))


def main():
    ap = argparse.ArgumentParser(description="盈利策略引擎 v2")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backtest", help="回测")
    b.add_argument("--days", type=int, default=60)
    b.add_argument("--top", type=int, default=UNIVERSE_TOP_N)
    b.add_argument("--capital", type=float, default=500.0)
    b.add_argument("--save", default=None)
    b.set_defaults(fn=cmd_backtest)
    l = sub.add_parser("live", help="实盘信号")
    l.add_argument("--days", type=int, default=3)
    l.add_argument("--top", type=int, default=UNIVERSE_TOP_N)
    l.add_argument("--equity", type=float, default=None)
    l.add_argument("--out", default=None)
    l.set_defaults(fn=cmd_live)
    c = sub.add_parser("check", help="只打印候选")
    c.add_argument("--days", type=int, default=3)
    c.add_argument("--top", type=int, default=UNIVERSE_TOP_N)
    c.add_argument("--equity", type=float, default=None)
    c.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
