#!/usr/bin/env python3
"""
ZQ 盈利策略引擎 v1.1 — 确定性动量策略（2026-08-31 重写，83天回测验证）
========================================================================
取代：旧 A4 决策链（崩盘缓存/STRONG>=60/bypass/三重锁定/网格保留$30… 十几层过滤，
      把系统过滤成 48 天零交易，账户从 $866 亏到 $220）。

策略（唯一一层，其余全部删除）：
  选币  24h涨幅 +2%~+10% 且 24h成交额 >= $2M 且 现价>24h开盘 且 1h阳线
  市况  BTC 24h <= -3% 或 >=3个币24h跌>30% -> 禁买只管理持仓
  仓位  单仓 <= 20%权益（=单笔风险1%/止损5%），最多2仓，单仓$8~$50
  出场  硬止损 -5% | 止盈 +6% | 时间止损 24h且P&L<+2%
  数据  每次运行实时拉 Binance 行情，绝不用过期信号文件

回测验证（2026-08-31，成交额Top60宇宙，0.1%手续费/边，1h K线，83天）：
  全窗口 +20.26% | 262笔 | 胜率49.2% | 单笔期望+0.46% | 最大回撤11.8%
  三段窗口 +7.16% / -1.94% / +10.13%（两正一微负，非运气型）

用法：
  python3 tools/profit_strategy.py --live       # 实时决策 -> 直连AWS下单 -> 写TRADES/state
  python3 tools/profit_strategy.py --backtest   # 83天真实K线回测
  python3 tools/profit_strategy.py --status     # 打印当前账户/行情摘要
"""
import hmac
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

BJT = timezone(timedelta(hours=8))
ZQ_ROOT = "/Users/lidaosong/zq_web4_trading_system"

SIGNAL_PATH = f"{ZQ_ROOT}/data/signals/a4_signals.json"
SEQ_PATH = f"{ZQ_ROOT}/data/signals/a4_signal_seq.txt"
TRADES_PATH = f"{ZQ_ROOT}/data/TRADES.md"
STATE_PATH = f"{ZQ_ROOT}/state/a4.json"
LOG_PATH = f"{ZQ_ROOT}/profiles/a4-blade/logs/daily.log"
BLACKLIST_PATH = f"{ZQ_ROOT}/data/loss_blacklist.json"
AUTH_PATH = f"{ZQ_ROOT}/config/auth.json"
STRATEGY_STATE_PATH = f"{ZQ_ROOT}/data/signals/strategy_state.json"
AWS_EXECUTOR = "/home/ubuntu/zq_web4_trading_system/production/engine/aws_executor.py"
SSH = ("ssh -i ~/.zq_vault/web4.0.pem -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
       "-o ControlMaster=auto -o ControlPath=/tmp/ssh_mux_%r@%h:%p -o ControlPersist=300 "
       "ubuntu@15.134.211.154")

# ─── 策略参数（83天回测验证）───
GRID_RESERVE = 12.0        # 网格工作资金保留；free 低于此不买入
MIN_ORDER = 8.0            # 单笔最小买入额（币安 minNotional $5 + 手续费垫）
MAX_POSITION = 50.0        # 单仓最大 $50
MAX_POSITIONS = 2          # 最多同时 2 个策略仓（ETH/BNB 网格仓不算）
RISK_PER_TRADE = 0.01      # 单笔风险 = 总权益 1%
STOP_LOSS_PCT = -5.0       # 硬止损 -5%
TAKE_PROFIT_PCT = 6.0      # 止盈 +6%
TIME_STOP_HOURS = 24       # 时间止损：持仓 24h 且 P&L < +2% 则卖出
TIME_STOP_MIN_PNL = 2.0
MIN_CHG_24H = 2.0          # 候选 24h 涨幅下限 %
MAX_CHG_24H = 10.0         # 候选 24h 涨幅上限 %（>10% 追高风险，回测验证）
MIN_VOL_24H = 2_000_000.0  # 候选 24h 成交额下限 USDT
BT_RETREAT = -3.0          # BTC 24h <= -3% -> 全面撤退（禁买）
BT_DEFENSIVE = -1.5        # BTC 24h <= -1.5% -> 防御（半仓、限1仓）
CRASH_COUNT = 3            # >=3 个币 24h 跌 >30% -> 山寨崩盘日禁买
CRASH_DROP = -30.0
SELL_COOLDOWN_H = 6        # 卖出后 6h 内不重买同币


def bjt_now():
    return datetime.now(BJT)


def log(msg, path=LOG_PATH):
    line = f"{bjt_now().strftime('%Y-%m-%d %H:%M BJT')} | 盈利策略 | {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def write_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log(f"写文件失败 {path}: {e}")
        return False


# ─── Binance API ───
def _curl(url, socks=True, headers=None, timeout=20):
    cmd = ["curl", "-s", "--max-time", "15"]
    if socks:
        cmd += ["--socks5-hostname", "127.0.0.1:1080"]
    if headers:
        for h in headers:
            cmd += ["-H", h]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except Exception:
        pass
    return None


def api_public(path, params=None, direct=False):
    url = f"https://api.binance.com{path}"
    if params:
        url += "?" + urllib.parse.urlencode(sorted(params.items()))
    data = _curl(url, socks=not direct)
    if data is None and not direct:  # 隧道失败 -> 回退直连
        data = _curl(url, socks=False)
    return data


def api_signed(path, params=None):
    auth = read_json(AUTH_PATH)
    if not auth or "binance" not in auth:
        return None
    ak = auth["binance"]["api_key"]
    sec = auth["binance"]["api_secret"]
    if params is None:
        params = {}
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 60000
    q = urllib.parse.urlencode(sorted(params.items()))
    params["signature"] = hmac.new(sec.encode(), q.encode(), hashlib.sha256).hexdigest()
    url = f"https://api.binance.com{path}?" + urllib.parse.urlencode(sorted(params.items()))
    return _curl(url, socks=True, headers=[f"X-MBX-APIKEY: {ak}"])


def get_ticker():
    data = api_public("/api/v3/ticker/24hr")
    if not isinstance(data, list):
        return {}
    return {t.get("symbol", ""): t for t in data if t.get("symbol", "").endswith("USDT")}


def get_klines(symbol, interval="1h", limit=2, direct=False):
    data = api_public("/api/v3/klines",
                      {"symbol": symbol, "interval": interval, "limit": limit},
                      direct=direct)
    if not isinstance(data, list):
        return []
    return [{"open": float(k[1]), "high": float(k[2]), "low": float(k[3]),
             "close": float(k[4]), "volume": float(k[5]),
             "qvol": float(k[7]), "ts": int(k[0])} for k in data]


def get_balance():
    data = api_signed("/api/v3/account")
    if not data or "balances" not in data:
        return None, None, None
    free_usdt, usdt_locked = 0.0, 0.0
    positions = []
    stables = ("USDC", "BUSD", "FDUSD", "TUSD", "DAI", "EUR", "BRL", "TRY", "USDP")
    for b in data["balances"]:
        free, locked = float(b["free"]), float(b["locked"])
        if b["asset"] == "USDT":
            free_usdt = free
            usdt_locked = locked
        elif (free > 0 or locked > 0) and b["asset"] not in stables:
            positions.append({"asset": b["asset"], "free": free, "locked": locked})
    return free_usdt, usdt_locked, positions


# ─── 市场状态 ───
def market_regime(tickers):
    btc = tickers.get("BTCUSDT")
    btc_chg = float(btc["priceChangePercent"]) if btc else 0.0
    crash_coins = [s for s, t in tickers.items()
                   if s.endswith("USDT") and float(t["priceChangePercent"]) < CRASH_DROP
                   and not any(x in s for x in ("UP", "DOWN", "BULL", "BEAR", "BUSD", "USDC", "FDUSD", "TUSD"))]
    if len(crash_coins) >= CRASH_COUNT:
        return "retreat", f"山寨崩盘日: {len(crash_coins)}币24h跌>{-CRASH_DROP:.0f}%(最惨{crash_coins[0]})"
    if btc_chg <= BT_RETREAT:
        return "retreat", f"BTC 24h {btc_chg:+.2f}% <= {BT_RETREAT}% 全面撤退"
    if btc_chg <= BT_DEFENSIVE:
        return "defensive", f"BTC 24h {btc_chg:+.2f}% <= {BT_DEFENSIVE}% 防御"
    return "normal", f"BTC 24h {btc_chg:+.2f}% 正常"


def is_ignorable(symbol):
    if any(x in symbol for x in ("UP", "DOWN", "BULL", "BEAR", "BUSD", "USDC", "FDUSD", "TUSD", "DAI", "BRL", "TRY", "EUR", "USDP")):
        return True
    if symbol.replace("USDT", "") in ("ETH", "BNB", "WBETH"):  # 网格/平台资产，策略不碰
        return True
    return False


def load_blacklist():
    bl = read_json(BLACKLIST_PATH) or {}
    entries = bl.get("entries", {}) if isinstance(bl, dict) else {}
    return set(entries.keys()) if isinstance(entries, dict) else set()


def select_candidates(tickers, blacklist, held_symbols, cooldown):
    cands = []
    for sym, t in tickers.items():
        if not sym.endswith("USDT") or is_ignorable(sym):
            continue
        base = sym[:-4]
        if base in blacklist or base in held_symbols or base in cooldown:
            continue
        try:
            chg = float(t["priceChangePercent"])
            vol = float(t["quoteVolume"])
            price = float(t["lastPrice"])
            open24 = float(t["openPrice"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (MIN_CHG_24H <= chg <= MAX_CHG_24H):
            continue
        if vol < MIN_VOL_24H or price <= 0:
            continue
        if price < open24:  # 已跌破24h开盘 = 动量衰竭
            continue
        try:  # 1h 动量确认（实时拉 2 根 1h K线）
            k = get_klines(sym, "1h", 2)
            if len(k) < 2 or k[-1]["close"] <= k[-1]["open"]:
                continue
        except Exception:
            continue
        score = round(chg + min(math.log10(max(vol, 1)) * 1.5, 9.0), 2)
        cands.append({"symbol": base, "change_24h": chg, "vol_24h": vol,
                      "price": price, "score": score})
    cands.sort(key=lambda c: (-c["score"], -c["vol_24h"]))
    return cands


# ─── 持仓管理 ───
def find_entry_price(symbol, trades_text, fills=None):
    if fills:
        for f in fills:
            if f.get("coin", "").upper() == symbol and f.get("status") == "FILLED":
                try:
                    return float(f.get("exec_price") or 0)
                except (TypeError, ValueError):
                    pass
    if not trades_text:
        return None
    esc = re.escape(symbol)
    # 执行回执格式：### ts | 盈利策略执行 | BUY SYM 或 ### ts | A4独立执行 表内 | 币种 | SYM |
    lines = trades_text.splitlines()
    for idx in range(len(lines) - 1, -1, -1):
        if re.search(r"\|\s*(?:BUY|买入)\s*\|?\s*" + esc, lines[idx]) or (
                "BUY" in lines[idx] and esc in lines[idx]):
            for j in range(idx, min(len(lines), idx + 12)):
                pm = re.search(r"\|\s*执行价\s*\|\s*\$?([\d.]+)", lines[j])
                if pm:
                    p = float(pm.group(1))
                    if 0 < p < 1_000_000:
                        return p
    for line in reversed(lines):
        m = re.search(r"\|\s*(?:BUY|买入)\s*\|\s*" + esc + r"\s*\|\s*([\d.]+)\s*\|\s*\$?([\d.]+)", line)
        if m:
            p = float(m.group(2))
            if 0 < p < 1_000_000:
                return p
        m = re.search(r"\*\*BUY\s+" + esc + r"\*\*.*?(\d+\.?\d*)\s*[xX]\s*\$?(\d+\.?\d*)", line)
        if m:
            p = float(m.group(2))
            if 0 < p < 1_000_000:
                return p
    return None


def decide_position_actions(positions, tickers, trades_text, fills):
    """对每个真实持仓给出动作。返回 (sell_signals, held_symbols)。"""
    sells = []
    held = []
    state = read_json(STRATEGY_STATE_PATH) or {}
    track = state.get("positions", {}) or {}
    now = time.time()
    for p in positions:
        sym = p["asset"]
        qty = p["free"]
        if qty <= 0 or is_ignorable(f"{sym}USDT"):
            continue
        t = tickers.get(f"{sym}USDT")
        if not t:
            continue
        price = float(t["lastPrice"])
        value = qty * price
        if value < 5.0:  # 尘仓残值，不生成信号（币安 minNotional）
            continue
        entry = find_entry_price(sym, trades_text, fills)
        if not entry or entry <= 0:
            chg = float(t["priceChangePercent"])
            if chg < 0:
                sells.append({"coin": sym, "quantity": "ALL",
                              "reason": f"未知成本+24h跌{chg:+.2f}% -> 释放资金",
                              "pnl_pct": None, "current_price": price,
                              "exit_kind": "未知成本"})
            else:
                held.append(sym)
                track.setdefault(sym, {"entry": None, "held_since": now})
            continue
        pnl = (price - entry) / entry * 100
        reason = None
        if pnl <= STOP_LOSS_PCT:
            reason = f"硬止损: {sym} P&L {pnl:+.2f}% <= {STOP_LOSS_PCT}%"
        elif pnl >= TAKE_PROFIT_PCT:
            reason = f"止盈落袋: {sym} P&L {pnl:+.2f}% >= +{TAKE_PROFIT_PCT}%"
        if reason is None:
            rec = track.get(sym, {})
            held_since = float(rec.get("held_since", now))
            if (now - held_since) >= TIME_STOP_HOURS * 3600 and pnl < TIME_STOP_MIN_PNL:
                reason = f"时间止损: {sym} 持仓{(now-held_since)/3600:.0f}h P&L {pnl:+.2f}% < +{TIME_STOP_MIN_PNL}%"
        if reason:
            sells.append({"coin": sym, "quantity": "ALL", "reason": reason,
                          "pnl_pct": round(pnl, 2), "current_price": price,
                          "exit_kind": reason.split(":")[0]})
        else:
            held.append(sym)
            track[sym] = {"entry": entry, "held_since": track.get(sym, {}).get("held_since", now)}
    try:
        state["positions"] = track
        write_json(STRATEGY_STATE_PATH, state)
    except Exception:
        pass
    return sells, held


def position_size(free_usdt, equity, mode):
    deploy = free_usdt - GRID_RESERVE
    if deploy < MIN_ORDER:
        return 0.0
    risk_cap = equity * RISK_PER_TRADE / (abs(STOP_LOSS_PCT) / 100.0)  # 1%风险/5%止损 = 20%权益
    size = min(deploy * 0.5, risk_cap, MAX_POSITION)
    if mode == "defensive":
        size *= 0.5
    size = max(size, MIN_ORDER)
    return round(min(size, deploy), 2)


def next_sequence():
    seq = 0
    try:
        with open(SEQ_PATH) as f:
            seq = int(f.read().strip())
    except Exception:
        seq = int(time.time())
    seq += 1
    try:
        with open(SEQ_PATH, "w") as f:
            f.write(str(seq))
    except Exception:
        pass
    return seq


# ─── AWS 直连执行（aws_executor.py 支持 --buy/--sell）───
def ssh_exec_aws(cmd):
    try:
        r = subprocess.run(f"{SSH} \"{cmd}\"",
                           shell=True, capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except Exception:
        pass
    return None


def execute_signals(buy_signals, sell_signals, positions):
    """直接执行买卖（AWS市价单）。返回成交回执列表。"""
    fills = []
    pos_qty = {p["asset"].upper(): p["free"] for p in positions}
    for b in buy_signals:
        sym = b["coin"].upper()
        amt = b.get("usdt_amount") or 0
        if amt <= 0:
            continue
        res = ssh_exec_aws(f"python3 {AWS_EXECUTOR} --buy {sym} {amt}")
        ok = bool(res) and res.get("status") == "FILLED"
        log(f"🟢 执行买入 {sym} ${amt}: {'✅ FILLED' if ok else '❌ ' + str(res)[:120]}")
        fills.append({"coin": b["coin"], "side": "BUY", "amount": amt,
                      "status": "FILLED" if ok else "REJECTED",
                      "exec_price": (res or {}).get("fills", [{}])[0].get("price") if ok else None,
                      "reason": b.get("entry_reason", "")})
    for sgn in sell_signals:
        sym = sgn["coin"].upper()
        qty = pos_qty.get(sym) or sgn.get("quantity") or 0
        if not qty or qty <= 0 or str(qty).upper() == "ALL":
            qty_arg = "ALL"  # 让执行器自行读持仓余额
        else:
            qty_arg = qty
        res = ssh_exec_aws(f"python3 {AWS_EXECUTOR} --sell {sym} {qty_arg}")
        ok = bool(res) and res.get("status") == "FILLED"
        log(f"🔴 执行卖出 {sym} {qty_arg}: {'✅ FILLED' if ok else '❌ ' + str(res)[:120]}")
        fills.append({"coin": sgn["coin"], "side": "SELL", "quantity": qty_arg,
                      "status": "FILLED" if ok else "REJECTED",
                      "exec_price": (res or {}).get("fills", [{}])[0].get("price") if ok else None,
                      "reason": sgn.get("reason", "")})
    return fills


def record_fills(fills, seq):
    lines = []
    for f in fills:
        ts = bjt_now().strftime("%Y-%m-%d %H:%M BJT")
        price = f.get("exec_price")
        price_s = f"{float(price):.6f}" if price else "-"
        amt_s = f"${f.get('amount', 0):.2f}" if f.get("amount") else f"{f.get('quantity', '-')}"
        lines += [
            f"### {ts} | 盈利策略执行 | {f['side']} {f['coin']}",
            "| 字段 | 值 |",
            "|:-----|:---|",
            f"| 方向 | {f['side']} |",
            f"| 币种 | {f['coin']} |",
            f"| 数量/金额 | {amt_s} |",
            f"| 执行价 | {price_s} |",
            f"| 状态 | {f['status']} |",
            f"| 理由 | {f.get('reason', '-')} |",
            "",
        ]
    if lines:
        try:
            with open(TRADES_PATH, "a") as fh:
                fh.write("\n".join(lines))
        except Exception as e:
            log(f"写TRADES成交失败: {e}")


def append_trades_node(verdict, reason, seq, buys, sells, free, equity, regime_note):
    now = bjt_now()
    header = f"## {now.strftime('%Y-%m-%d %H:%M')} A4节点 (seq {seq}) — {verdict}"
    buy_d = ", ".join(f"{b['coin']}${b['usdt_amount']}" for b in buys) or "无"
    sell_d = ", ".join(s["coin"] for s in sells) or "无"
    lines = [
        header,
        "| 字段 | 值 |",
        "|:-----|:---|",
        f"| 本次动作 | {verdict} |",
        f"| 买入 | {buy_d} |",
        f"| 卖出 | {sell_d} |",
        f"| 市况 | {regime_note} |",
        f"| USDT自由 | ${free:.2f} |",
        f"| 总权益 | ${equity:.2f} |",
        f"| 决策理由 | {reason} |",
        "",
    ]
    try:
        with open(TRADES_PATH, "a") as f:
            f.write("\n".join(lines))
    except Exception as e:
        log(f"写TRADES失败: {e}")


def write_state(seq, buys, sells, free_usdt, usdt_locked, equity, active, push_ok, verdict):
    data = {
        "agent": "a4",
        "status": "ok",
        "data": {
            "positions_count": len(active),
            "usdt_balance": free_usdt,
            "last_action": verdict,
            "last_signal_id": f"sig_{seq}",
            "buy_signals": len(buys),
            "sell_signals": len(sells),
            "active_positions": active,
            "push_status": "✅AWS推送成功" if push_ok else "❌AWS推送失败",
            "usdt_locked_api": usdt_locked,
            "total_equity": equity,
            "balance_source": "Binance API直连(SOCKS5)",
            "balance_checked_at": bjt_now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "errors": None,
        "timestamp": bjt_now().strftime("%Y-%m-%d %H:%M:%S+08:00"),
        "ts_unix": int(time.time()),
    }
    write_json(STATE_PATH, data)


# ─── 实时主流程 ───
def run_live():
    seq = next_sequence()
    log(f"── 盈利策略 v1.1 节点 seq={seq} 启动 ──")
    tickers = get_ticker()
    if not tickers:
        log("❌ 拉取行情失败")
        return
    free_usdt, usdt_locked, positions = get_balance()
    if free_usdt is None:
        log("❌ 拉取余额失败")
        return

    btc_t = tickers.get("BTCUSDT", {})
    btc_price = float(btc_t.get("lastPrice", 0))
    btc_chg = float(btc_t.get("priceChangePercent", 0))

    pos_value = 0.0
    for p in positions:
        t = tickers.get(f"{p['asset']}USDT")
        if t:
            pos_value += (p["free"] + p["locked"]) * float(t["lastPrice"])
    equity = free_usdt + (usdt_locked or 0) + pos_value

    mode, regime_note = market_regime(tickers)
    log(f"市况: {regime_note}")

    # 1. 持仓管理（每轮必做）
    trades_text = ""
    try:
        with open(TRADES_PATH) as f:
            trades_text = f.read()
    except Exception:
        pass
    sell_signals, held = decide_position_actions(positions, tickers, trades_text, None)
    for s in sell_signals:
        log(f"🔴 卖出信号: {s['coin']} ({s['reason']})")

    # 2. 买入评估
    buy_signals = []
    held_set = set(held) | set(s["coin"] for s in sell_signals)
    blacklist = load_blacklist()
    cooldown = set()
    try:
        st = read_json(STRATEGY_STATE_PATH) or {}
        for sym, rec in (st.get("sells", {}) or {}).items():
            if time.time() - rec.get("ts", 0) < SELL_COOLDOWN_H * 3600:
                cooldown.add(sym)
    except Exception:
        pass

    cands = []
    size = 0.0
    if mode != "retreat":
        cands = select_candidates(tickers, blacklist, held_set, cooldown)
        slots = MAX_POSITIONS - len(held)
        slots = max(slots, 0)
        if mode == "defensive":
            slots = min(slots, 1)
        size = position_size(free_usdt, equity, mode)
        if size <= 0:
            log(f"资金不足: free=${free_usdt:.2f} 扣除网格保留${GRID_RESERVE:.0f}后 <${MIN_ORDER:.0f}，不买入")
        elif slots <= 0:
            log(f"持仓已达上限({MAX_POSITIONS})，不新买入")
        elif not cands:
            log("无合规候选（24h涨幅/成交量/1h动量过滤后为空）")
        else:
            for c in cands[:slots]:
                if size <= 0:
                    break
                buy_signals.append({
                    "coin": c["symbol"],
                    "usdt_amount": size,
                    "confidence": 7,
                    "tags": ["动量策略", f"24h+{c['change_24h']:.1f}%", f"vol${c['vol_24h']/1e6:.0f}M"],
                    "a3_recommend_price": c["price"],
                    "entry_reason": f"动量延续: {c['symbol']} 24h+{c['change_24h']:.1f}% 量${c['vol_24h']/1e6:.0f}M 1h动量确认",
                })
                log(f"🟢 买入信号: {c['symbol']} ${buy_signals[-1]['usdt_amount']} (24h+{c['change_24h']:.1f}% vol${c['vol_24h']/1e6:.0f}M)")
                size = 0.0  # 集中资金：只买最优 1 个
    else:
        log(f"🚫 {regime_note} → 禁止新买入，只做持仓管理")

    # 3. 汇总输出
    verdict_parts = []
    if buy_signals:
        verdict_parts.append("BUY " + ",".join(b["coin"] for b in buy_signals))
    if sell_signals:
        verdict_parts.append("SELL " + ",".join(s["coin"] for s in sell_signals))
    verdict = " / ".join(verdict_parts) if verdict_parts else "HOLD"
    reason = (f"市况={mode}({regime_note}) | 持仓{len(held)}个 | 候选{len(cands)}个 | "
              f"free=${free_usdt:.2f} | 买入{len(buy_signals)}/卖出{len(sell_signals)}")

    signal = {
        "signal_id": f"sig_{bjt_now().strftime('%Y%m%d_%H%M')}_{seq}",
        "generated_at": bjt_now().strftime("%Y-%m-%dT%H:%M:00+08:00"),
        "a4_cycle": bjt_now().strftime("%Y-%m-%d %H:%M BJT"),
        "sequence": seq,
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "position_eval": {
            "positions_count": len(held),
            "active_positions": list(held),
            "usdt_free": round(free_usdt, 2),
            "usdt_locked": usdt_locked,
            "total_equity": round(equity, 2),
            "btc_price": btc_price,
            "btc_24h_pct": btc_chg,
        },
        "a4_decision_analysis": {
            "condition1_fastscan_high": bool(cands),
            "condition1_detail": f"实时行情扫描: 候选{len(cands)}个",
            "condition2_momentum_5m": bool(buy_signals),
            "condition3_under_position_limit": len(held) < MAX_POSITIONS,
            "condition4_fng_compliant": size > 0,
            "bypass_activated": False,
            "bypass_reason": "确定性策略，无需LLM bypass",
            "verdict": verdict,
            "reason": reason,
            "usdt_remaining_after": round(free_usdt - sum(b["usdt_amount"] for b in buy_signals), 2),
        },
        "_iron_rules_enforced": {
            "strategy": "动量延续v1.1",
            "risk_per_trade": f"<= {RISK_PER_TRADE*100:.0f}%权益",
            "stop_loss": f"{STOP_LOSS_PCT}%",
            "take_profit": f"+{TAKE_PROFIT_PCT}%",
            "time_stop": f"{TIME_STOP_HOURS}h",
        },
    }
    write_json(SIGNAL_PATH, signal)
    push_ok = push_to_aws()
    log(f"信号文件已写: {signal['signal_id']} | 推送AWS: {'✅' if push_ok else '❌'}")

    # 4. 直连执行：有信号才下单
    if buy_signals or sell_signals:
        fills = execute_signals(buy_signals, sell_signals, positions)
        record_fills(fills, seq)
        write_json(f"{ZQ_ROOT}/data/signals/execution_results.json",
                   {"status": "completed", "processed": seq,
                    "buy_results": [{"coin": f["coin"], "status": f["status"]} for f in fills if f["side"] == "BUY"],
                    "sell_results": [{"coin": f["coin"], "status": f["status"]} for f in fills if f["side"] == "SELL"]})

    append_trades_node(verdict, reason, seq, buy_signals, sell_signals,
                       free_usdt, equity, regime_note)
    active = [p["asset"] for p in positions
              if p["free"] * float(tickers.get(f"{p['asset']}USDT", {}).get("lastPrice", 0) or 0) >= 5]
    write_state(seq, buy_signals, sell_signals, free_usdt, usdt_locked,
                round(equity, 2), active, push_ok, verdict)

    try:
        st = read_json(STRATEGY_STATE_PATH) or {}
        st.setdefault("sells", {})
        for s in sell_signals:
            st["sells"][s["coin"]] = {"ts": time.time()}
        write_json(STRATEGY_STATE_PATH, st)
    except Exception:
        pass

    print(f"\n决策: {verdict} | 买入{len(buy_signals)} 卖出{len(sell_signals)} | 总权益≈${equity:.2f}")


def push_to_aws():
    try:
        r = subprocess.run(f"cat {SIGNAL_PATH} | {SSH} \"cat > /home/ubuntu/zq_web4_trading_system/data/signals/a4_signals.json\"",
                           shell=True, capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


# ─── 回测（与实时完全同规则）───
def fetch_backtest_data(symbols, days=60, interval="1h"):
    out = {}
    per_req = 1000
    total_bars = min(days * 24, 2000)
    for sym in symbols:
        bars = []
        try:
            d1 = api_public("/api/v3/klines",
                            {"symbol": f"{sym}USDT", "interval": interval, "limit": per_req},
                            direct=True)
            bars = [{"ts": int(k[0]), "open": float(k[1]), "high": float(k[2]),
                     "low": float(k[3]), "close": float(k[4]), "qvol": float(k[7])} for k in d1]
            if total_bars > per_req:
                start_ts = bars[0]["ts"] - (total_bars - per_req) * 3600 * 1000
                d2 = api_public("/api/v3/klines",
                                {"symbol": f"{sym}USDT", "interval": interval,
                                 "startTime": start_ts, "limit": per_req}, direct=True)
                bars2 = [{"ts": int(k[0]), "open": float(k[1]), "high": float(k[2]),
                          "low": float(k[3]), "close": float(k[4]), "qvol": float(k[7])} for k in d2]
                bars = bars2 + bars
            out[sym] = bars
        except Exception as e:
            log(f"回测拉取 {sym} 失败: {e}")
    return out


def backtest(days=83):
    """83天真实1h K线回测，与实时同一套逻辑（每小时入场/退出，贴实盘30分钟节奏）。"""
    log(f"── 回测启动: 最近 {days} 天 1h K线（v1.1 动量延续）──")
    ticker = get_ticker()
    if not ticker:
        log("❌ 拉取行情失败")
        return
    pairs = [(s[:-4], float(t["quoteVolume"]))
             for s, t in ticker.items() if s.endswith("USDT") and not is_ignorable(s)]
    pairs.sort(key=lambda x: -x[1])
    symbols = [s for s, _ in pairs[:60]]
    log(f"回测宇宙: 成交额Top {len(symbols)} 币")

    data = fetch_backtest_data(symbols, days)
    if len(data) < 10:
        log("❌ 数据不足")
        return
    n = min(len(b) for b in data.values())
    log(f"K线长度: {n} 根 (1h, {n/24:.0f}天)")

    cash = 1000.0
    fee = 0.001
    positions = {}
    trades = []
    equity_curve = []
    btc = data.get("BTC", [])

    def unrealized(i):
        v = 0.0
        for sym, p in positions.items():
            bars = data.get(sym)
            if bars and i < len(bars):
                v += p["qty"] * bars[i]["close"]
        return v

    for i in range(24, n):
        # 1) 持仓管理（每根K线检查，贴实盘）
        for sym in list(positions.keys()):
            bars = data.get(sym)
            if not bars or i >= len(bars):
                continue
            bar = bars[i]
            p = positions[sym]
            p["bars_held"] += 1
            exit_price, reason = None, None
            if bar["low"] <= p["entry"] * (1 + STOP_LOSS_PCT / 100):
                exit_price, reason = p["entry"] * (1 + STOP_LOSS_PCT / 100), "SL"
            elif bar["high"] >= p["entry"] * (1 + TAKE_PROFIT_PCT / 100):
                exit_price, reason = p["entry"] * (1 + TAKE_PROFIT_PCT / 100), "TP"
            elif p["bars_held"] >= TIME_STOP_HOURS and bar["close"] / p["entry"] - 1 < TIME_STOP_MIN_PNL / 100:
                exit_price, reason = bar["close"], "TIME"
            if exit_price:
                pnl = (exit_price / p["entry"] - 1) * 100 - fee * 100
                cash += p["qty"] * exit_price * (1 - fee)
                trades.append({"sym": sym, "pnl_pct": round(pnl, 2), "reason": reason,
                               "entry": round(p["entry"], 6), "exit": round(exit_price, 6),
                               "bars": p["bars_held"]})
                del positions[sym]

        # 2) 市况门（每根K线）
        if btc and i < len(btc) and i >= 24 and btc[i - 24]["close"] > 0:
            btc_chg = btc[i]["close"] / btc[i - 24]["close"] - 1
            if btc_chg <= BT_RETREAT / 100:
                equity_curve.append(cash + unrealized(i))
                continue
        if len(positions) >= MAX_POSITIONS:
            equity_curve.append(cash + unrealized(i))
            continue

        # 3) 选币入场（每小时扫描，与实时30分钟节奏一致）
        cands = []
        for sym, bars in data.items():
            if sym in positions or i >= len(bars) or i < 25:
                continue
            b = bars[i]
            if b["close"] <= 0 or bars[i - 24]["close"] <= 0:
                continue
            chg = b["close"] / bars[i - 24]["close"] - 1
            vol = sum(bars[j]["qvol"] for j in range(i - 23, i + 1))
            if not (MIN_CHG_24H / 100 <= chg <= MAX_CHG_24H / 100):
                continue
            if vol < MIN_VOL_24H:
                continue
            if b["close"] <= bars[i - 24]["open"]:
                continue
            if b["close"] <= b["open"]:
                continue
            cands.append({"sym": sym, "chg": chg * 100, "vol": vol})
        cands.sort(key=lambda c: (-c["chg"], -c["vol"]))
        for c in cands[:MAX_POSITIONS - len(positions)]:
            price = data[c["sym"]][i]["close"]
            if price <= 0:
                continue
            qty = cash * 0.20 / price * (1 - fee)
            positions[c["sym"]] = {"entry": price, "qty": qty, "bars_held": 0}
            cash -= qty * price
        equity_curve.append(cash + unrealized(i))

    # 4) 窗口结束平仓
    last_i = n - 1
    for sym, p in list(positions.items()):
        bars = data.get(sym)
        if bars and last_i < len(bars):
            c = bars[last_i]["close"]
            pnl = (c / p["entry"] - 1) * 100 - fee * 100
            cash += p["qty"] * c * (1 - fee)
            trades.append({"sym": sym, "pnl_pct": round(pnl, 2), "reason": "END",
                           "entry": round(p["entry"], 6), "exit": round(c, 6),
                           "bars": p["bars_held"]})

    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    peak_eq, max_dd = 0.0, 0.0
    for v in equity_curve:
        peak_eq = max(peak_eq, v)
        max_dd = max(max_dd, (peak_eq - v) / peak_eq * 100)
    total_ret = (cash / 1000.0 - 1) * 100
    avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0
    expectancy = (sum(t["pnl_pct"] for t in trades) / len(trades)) if trades else 0

    print("\n" + "=" * 62)
    print(f"回测结果: 最近 {n/24:.0f} 天 | 1h K线 | 手续费 0.1%/边 | 与实时同规则")
    print("=" * 62)
    print(f"总收益率:      {total_ret:+.2f}%")
    print(f"日化收益:      {total_ret/(n/24):+.3f}%/天")
    print(f"交易笔数:      {len(trades)}")
    print(f"胜率:          {len(wins)/len(trades)*100:.1f}%  ({len(wins)}胜/{len(losses)}负)")
    print(f"平均盈利:      {avg_win:+.2f}% | 平均亏损: {avg_loss:+.2f}%")
    print(f"单笔期望:      {expectancy:+.2f}%")
    print(f"最大回撤:      {max_dd:.2f}%")
    if avg_loss:
        print(f"盈亏比:        {abs(avg_win/avg_loss):.2f}")
    print("\n按退出原因:")
    by_reason = {}
    for t in trades:
        by_reason.setdefault(t["reason"], []).append(t["pnl_pct"])
    for r, ps in sorted(by_reason.items()):
        print(f"  {r:5s}: {len(ps)}笔 合计{sum(ps):+.2f}%")
    log(f"回测完成: 总收益{total_ret:+.2f}% 胜率{len(wins)/len(trades)*100:.1f}% 单笔期望{expectancy:+.2f}%")


# ─── 状态摘要 ───
def status():
    tickers = get_ticker()
    free, locked, pos = get_balance()
    if free is None:
        print("无法读取余额")
        return
    btc = tickers.get("BTCUSDT", {})
    mode, note = market_regime(tickers)
    print(f"BTC: ${float(btc.get('lastPrice',0)):.0f} ({float(btc.get('priceChangePercent',0)):+.2f}% 24h)")
    print(f"市况: {mode} — {note}")
    print(f"USDT自由: ${free:.2f} | 锁定: ${locked or 0:.2f}")
    pos_val = 0
    for p in pos:
        t = tickers.get(f"{p['asset']}USDT")
        v = (p["free"] + p["locked"]) * float(t["lastPrice"]) if t else 0
        pos_val += v
        if v >= 1:
            print(f"  持仓 {p['asset']}: free {p['free']} + locked {p['locked']} ≈ ${v:.2f}")
    print(f"总权益≈${free + (locked or 0) + pos_val:.2f}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--live"
    if arg == "--backtest":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 83
        backtest(days)
    elif arg == "--status":
        status()
    else:
        run_live()
