#!/usr/bin/env python3
"""
A4 独立执行节点 v1.0 — 在AWS上运行
===============
职责：独立从信号文件读取A4的决策，验证后执行交易。
不依赖Mac，不依赖Hermes cron，不依赖A4。

信号文件格式（由Mac上A4通过SCP推送）：
  /home/ubuntu/zq_web4_trading_system/data/signals/a4_signals.json

执行结果写入：
  /home/ubuntu/zq_web4_trading_system/data/signals/execution_results.json

运行方式：AWS cron 每5分钟执行一次
"""
import json, hmac, hashlib, time, requests, os, sys, math
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
# Paths (absolute, not relative to __file__)
ZQ_ROOT = "/home/ubuntu/zq_web4_trading_system"
AUTH_PATH = os.path.join(ZQ_ROOT, "config/auth.json")
SIGNAL_PATH = os.path.join(ZQ_ROOT, "data/signals/a4_signals.json")
RESULT_PATH = os.path.join(ZQ_ROOT, "data/signals/execution_results.json")
TRADES_PATH = os.path.join(ZQ_ROOT, "audit/TRADES.md")

MIN_BUY_USDT = 5
GRID_USDT_RESERVE = 30  # 🛡️ 网格资金保留(2026-08-31): ETH网格独占USDT(NAVIGATION.md §二), free<$30禁止A4新买入
STALE_TIMEOUT_SEC = 1200  # 信号超过20分钟视为过期（含SCP推送延迟）

# 金额字段多键兼容：A4信号历史用过 usdt_amount / amount_usd / notional_usdt / amount / notional
# 2026-08-09 A5修复：字段全缺失时返回 None（调用方必须显式SKIP+告警，禁止静默fallback到MIN_BUY）
def _buy_amount(buy):
    for k in ("usdt_amount", "amount_usd", "notional_usdt", "notional", "amount", "amount_usdt"):
        v = buy.get(k)
        if v:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None

# loss blacklist
LOSS_BLACKLIST_PATH = os.path.join(ZQ_ROOT, "data/signals/loss_blacklist.json")
LOSS_BLACKLIST_HOURS = 24

_lot_size_cache = {}

# ───────── 基础工具 ─────────

def bjt_now():
    return datetime.now(BJT)

def log(msg):
    ts = bjt_now().strftime("%Y-%m-%d %H:%M BJT")
    line = f"{ts} | A4独立 | {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except:
        pass

def load_auth():
    with open(AUTH_PATH) as f:
        auth = json.load(f)
    return auth["binance"]["api_key"], auth["binance"]["api_secret"]

def sign(params, secret):
    q = urlencode(params)
    params["signature"] = hmac.new(secret.encode(), q.encode(), hashlib.sha256).hexdigest()
    return params

def get_lot_size(symbol):
    sym = f"{_base(symbol)}USDT"
    if sym in _lot_size_cache:
        return _lot_size_cache[sym]
    try:
        r = requests.get(f"https://api.binance.com/api/v3/exchangeInfo?symbol={sym}", timeout=5)
        data = r.json()
        filters = data["symbols"][0]["filters"]
        step_sz, min_qty, min_not = 0.00000001, 0.00000001, 5
        for f in filters:
            if f["filterType"] == "LOT_SIZE":
                step_sz, min_qty = float(f["stepSize"]), float(f["minQty"])
            if f["filterType"] in ("NOTIONAL", "MIN_NOTIONAL"):
                min_not = float(f.get("minNotional", 5))
        result = {"stepSize": step_sz, "minQty": min_qty, "minNotional": min_not}
        _lot_size_cache[sym] = result
        return result
    except Exception as e:
        log(f"LOT_SIZE查询失败({sym}): {e}")
        return {"stepSize": 0.00000001, "minQty": 0.00000001, "minNotional": 5}

def round_quantity(qty, step_size):
    precision = max(0, int(round(-math.log10(step_size)))) if step_size >= 1e-8 else 8
    if step_size > 0:
        qty = math.floor(qty / step_size) * step_size
    return round(qty, precision)

# ───────── Binance API ─────────

def check_balance(api_key, secret):
    params = {"timestamp": int(time.time() * 1000)}
    params = sign(params, secret)
    r = requests.get("https://api.binance.com/api/v3/account",
                     headers={"X-MBX-APIKEY": api_key}, params=params, timeout=10)
    data = r.json()
    non_zero = []
    for bal in data["balances"]:
        f, l = float(bal["free"]), float(bal["locked"])
        if f > 0 or l > 0:
            non_zero.append(bal)
    usdt_free = 0.0
    for bal in data["balances"]:
        if bal["asset"] == "USDT":
            usdt_free = float(bal["free"])
    return non_zero, usdt_free

def _base(symbol):
    """strip trailing USDT suffix (signals may carry ZECUSDT or ZEC)"""
    s = symbol.upper().strip()
    return s[:-4] if s.endswith("USDT") else s

def get_price(symbol):
    sym = _base(symbol)
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}USDT", timeout=5)
        if r.status_code == 200 and "price" in r.json():
            return float(r.json()["price"])
    except:
        pass
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym}USDT", timeout=5)
        if r.status_code == 200 and "lastPrice" in r.json():
            return float(r.json()["lastPrice"])
    except:
        pass
    raise Exception(f"无法获取 {sym} 价格")

def buy_market(api_key, secret, symbol, usdt_amount):
    if usdt_amount < MIN_BUY_USDT:
        return {"error": f"单笔最少${MIN_BUY_USDT}，金额${usdt_amount:.2f}过低", "code": "MIN_POSITION"}
    params = {
        "symbol": f"{_base(symbol)}USDT", "side": "BUY",
        "type": "MARKET", "quoteOrderQty": str(usdt_amount),
        "timestamp": int(time.time() * 1000),
    }
    params = sign(params, secret)
    r = requests.post("https://api.binance.com/api/v3/order",
                      headers={"X-MBX-APIKEY": api_key}, params=params, timeout=10)
    return r.json()

def sell_market(api_key, secret, symbol, quantity):
    sym = _base(symbol)
    ls = get_lot_size(sym)
    qty = round_quantity(quantity, ls["stepSize"])
    if qty < ls["minQty"]:
        return {"error": f"数量{qty}低于最小{ls['minQty']}", "code": "MIN_QTY"}
    price = get_price(sym)
    notional = qty * price
    if notional < ls["minNotional"]:
        return {"error": f"订单价值${notional:.2f}低于最低${ls['minNotional']}", "code": "MIN_NOTIONAL", "price": price}
    params = {
        "symbol": f"{sym}USDT", "side": "SELL",
        "type": "MARKET", "quantity": str(qty),
        "timestamp": int(time.time() * 1000),
    }
    params = sign(params, secret)
    r = requests.post("https://api.binance.com/api/v3/order",
                      headers={"X-MBX-APIKEY": api_key}, params=params, timeout=10)
    return r.json()

# ───────── 信号处理 ─────────

def load_blacklist():
    """load loss blacklist"""
    if not os.path.exists(LOSS_BLACKLIST_PATH):
        return {}
    try:
        with open(LOSS_BLACKLIST_PATH) as f:
            return json.load(f)
    except:
        return {}

def save_blacklist(bl):
    """save loss blacklist"""
    os.makedirs(os.path.dirname(LOSS_BLACKLIST_PATH), exist_ok=True)
    with open(LOSS_BLACKLIST_PATH, "w") as f:
        json.dump(bl, f, indent=2)

def is_blacklisted(coin, bl):
    """check if coin is blacklisted"""
    entry = bl.get(coin.upper())
    if not entry:
        return False
    ba = entry.get("blacklisted_at", 0)
    if not ba:
        return False
    now = time.time()
    if now - ba > LOSS_BLACKLIST_HOURS * 3600:
        del bl[coin.upper()]
        return False
    return True

def blacklist_coin(coin, reason, pnl_pct, bl):
    """add coin to loss blacklist"""
    bl[coin.upper()] = {"blacklisted_at": time.time(), "reason": reason, "pnl_pct": pnl_pct, "coin": coin}
    save_blacklist(bl)
    log(f"BLACKLIST: {coin} added (PnL{pnl_pct:+.2f}%, {reason})")

def load_signals():
    """读信号文件，返回None表示无信号或过期"""
    if not os.path.exists(SIGNAL_PATH):
        return None
    try:
        with open(SIGNAL_PATH) as f:
            data = json.load(f)
    except:
        log(f"信号文件解析失败")
        return None

    signal_id = data.get("signal_id", "unknown")
    generated_at = data.get("generated_at", "")

    # 检查信号是否已经处理过
    results = load_previous_results()
    if results and results.get("processed_signal_id") == signal_id:
        log(f"信号 {signal_id} 已处理，跳过")
        return None

    # 检查信号是否过期（超过10分钟）
    if generated_at:
        try:
            gen_ts = datetime.fromisoformat(generated_at)
            now = datetime.now(gen_ts.tzinfo or BJT)
            elapsed = (now - gen_ts).total_seconds()
            if elapsed > STALE_TIMEOUT_SEC:
                log(f"信号 {signal_id} 已过期({elapsed:.0f}s > {STALE_TIMEOUT_SEC}s)，跳过")
                data["expired"] = True
                return data
        except:
            pass

    data["signal_id"] = signal_id
    return data

def load_previous_results():
    """读之前的执行结果"""
    if not os.path.exists(RESULT_PATH):
        return None
    try:
        with open(RESULT_PATH) as f:
            return json.load(f)
    except:
        return None

def save_results(results):
    """保存执行结果"""
    os.makedirs(os.path.dirname(RESULT_PATH), exist_ok=True)
    with open(RESULT_PATH, "w") as f:
        json.dump(results, f, indent=2, default=str)

def append_trades_line(line):
    """追加一条记录到TRADES.md"""
    os.makedirs(os.path.dirname(TRADES_PATH), exist_ok=True)
    with open(TRADES_PATH, "a") as f:
        f.write(line + "\n")

# ───────── 验证层 ─────────

def self_verify(signal, api_key, secret):
    """独立验证信号的有效性"""
    issues = []

    # 1. 查Binance API连通
    try:
        assets, usdt_free = check_balance(api_key, secret)
    except Exception as e:
        return False, [f"Binance API不可用: {e}"]

    # 2. 验证每条买入信号
    for buy in signal.get("buy_signals", []):
        coin = buy.get("coin") or buy.get("symbol", "")
        try:
            price = get_price(coin)
            buy["_current_price"] = price
            # 检查价格偏离
            a3_price = buy.get("a3_recommend_price")
            if a3_price:
                dev = (price - a3_price) / a3_price * 100
                buy["_price_deviation_pct"] = round(dev, 2)
                if abs(dev) > 10:
                    issues.append(f"{coin} 价格偏离{dev:+.2f}% (A3建仓价${a3_price})")
            # 检查余额
            amount = _buy_amount(buy)
            if amount is None:
                issues.append(f"{coin} 信号缺金额字段(usdt_amount/amount_usd/notional_usdt)，无法执行")
                continue
            if amount > usdt_free:
                issues.append(f"{coin} 买入${amount}但余额仅${usdt_free:.2f}")
        except Exception as e:
            issues.append(f"{coin} 验证失败: {e}")

    # 3. 验证每条卖出信号
    for sell in signal.get("sell_signals", []):
        coin = sell.get("coin") or sell.get("symbol", "")
        qty = sell.get("quantity") or sell.get("qty", 0)
        # 检查持仓是否还存在
        found = False
        for bal in assets:
            if bal["asset"] == coin.upper():
                free = float(bal["free"])
                if isinstance(qty, str) and qty.upper() == "ALL":
                    if free > 0:
                        found = True
                    else:
                        issues.append(f"{coin} 无持仓可卖")
                elif free >= float(qty) * 0.99:
                    found = True
                else:
                    issues.append(f"{coin} 要卖{qty}但仅持有{free}")
                break
        if not found:
            issues.append(f"{coin} 无持仓可卖")

    return len(issues) == 0, issues

# ───────── 执行层 ─────────

def execute_buy(buy_signal, api_key, secret, usdt_free):
    """执行单条买入信号"""
    coin = buy_signal.get("coin") or buy_signal.get("symbol", "")
    # blacklist check
    bl = load_blacklist()
    if is_blacklisted(coin, bl):
        log(f"SKIP {coin}: in loss blacklist")
        save_blacklist(bl)
        return {"coin": coin, "status": "SKIP", "reason": f"{coin} in loss blacklist"}

    amount = _buy_amount(buy_signal)
    if amount is None:
        return {"coin": coin, "status": "SKIP", "reason": "信号缺金额字段(usdt_amount/amount_usd/notional_usdt)，拒绝静默$5成交"}
    amount = min(amount, usdt_free)

    if amount < MIN_BUY_USDT:
        return {"coin": coin, "status": "SKIP", "reason": f"余额不足(${amount:.2f} < ${MIN_BUY_USDT})"}

    log(f"🟢 执行买入 {coin} ${amount:.2f}")
    result = buy_market(api_key, secret, coin, amount)
    ts = bjt_now().strftime("%Y-%m-%d %H:%M BJT")

    exec_status = "FAILED"
    exec_price = 0
    fills_info = {}

    if "status" in result and result["status"] == "FILLED":
        exec_status = "FILLED"
        fills = result.get("fills", [])
        if fills:
            exec_price = float(fills[0].get("price", 0))
            fills_info = {
                "price": exec_price,
                "qty": float(fills[0].get("qty", 0)),
                "commission": float(fills[0].get("commission", 0)),
            }
        log(f"✅ {coin} 成交! 价${exec_price:.4f} 金额${amount:.2f}")
    elif "code" in result:
        exec_status = f"REJECTED_{result['code']}"
        log(f"⚠️ {coin} 拒绝: {result.get('error', '未知')}")
    else:
        exec_status = "PARTIAL"
        log(f"⚠️ {coin} 部分成交: {json.dumps(result)[:200]}")

    # 记录TRADES.md
    tags_str = ", ".join(buy_signal.get("tags", []))
    trade_line = f"""### {ts} | A4独立执行
| 字段 | 值 |
|:-----|:---|
| 指令来源 | A4 信号文件 |
| 币种 | {coin} |
| 方向 | BUY |
| 执行价 | ${exec_price:.4f} |
| 执行量 | ${amount:.2f} USDT |
| 标签 | {tags_str} |
| 状态 | ✅ {exec_status} |
"""
    append_trades_line(trade_line)

    return {
        "coin": coin,
        "action": "BUY",
        "status": exec_status,
        "exec_price": exec_price,
        "amount": amount,
        "fills": fills_info,
        "raw": result.get("orderId", ""),
        "executed_at": ts,
    }

def convert_dust_to_usdt(api_key, secret, coin, qty):
    """2026-08-25 尘仓修复: 市价卖不掉(<minNotional$5)时走官方Convert闪兑, 无$5门槛"""
    params = {"fromAsset": coin.upper(), "toAsset": "USDT", "fromAmount": str(qty),
              "timestamp": int(time.time() * 1000), "recvWindow": 10000}
    params = sign(params, secret)
    try:
        rq = requests.post("https://api.binance.com/sapi/v1/convert/getQuote",
                           headers={"X-MBX-APIKEY": api_key}, params=params, timeout=15)
        if rq.status_code != 200:
            return {"error": f"Convert getQuote失败: {rq.text[:120]}", "code": "CONVERT_NO_QUOTE"}
        q = rq.json()
        ra = requests.post("https://api.binance.com/sapi/v1/convert/acceptQuote",
                           headers={"X-MBX-APIKEY": api_key},
                           params={"quoteId": q["quoteId"], "timestamp": int(time.time() * 1000),
                                   "recvWindow": 10000}, timeout=20)
        if ra.status_code == 200:
            return {"status": "FILLED", "convert": True, "toAmount": q.get("toAmount"),
                    "orderId": ra.json().get("orderId")}
        return {"error": f"Convert acceptQuote失败: {ra.text[:120]}", "code": "CONVERT_ACCEPT_FAIL"}
    except Exception as e:
        return {"error": f"Convert异常: {str(e)[:120]}", "code": "CONVERT_EXC"}

def execute_sell(sell_signal, api_key, secret):
    """执行单条卖出信号"""
    coin = sell_signal.get("coin") or sell_signal.get("symbol", "")
    qty = sell_signal.get("quantity") or sell_signal.get("qty", 0)

    # 2026-08-25 A4修复: qty="ALL"字符串与0.99相乘崩溃 → 解析为实际持仓余额
    if isinstance(qty, str) and qty.upper() == "ALL":
        assets, _ = check_balance(api_key, secret)
        qty = 0.0
        for bal in assets:
            if bal["asset"] == coin.upper():
                qty = float(bal["free"])
                break
        if qty <= 0:
            return {"coin": coin, "action": "SELL", "status": "SKIP",
                    "reason": f"{coin} 无持仓可卖", "executed_at": bjt_now().strftime("%Y-%m-%d %H:%M BJT")}
    else:
        try:
            qty = float(qty)
        except (TypeError, ValueError):
            return {"coin": coin, "action": "SELL", "status": "SKIP",
                    "reason": f"{coin} 无效数量{qty}", "executed_at": bjt_now().strftime("%Y-%m-%d %H:%M BJT")}

    log(f"🔴 执行卖出 {coin} {qty}")
    result = sell_market(api_key, secret, coin, qty)
    ts = bjt_now().strftime("%Y-%m-%d %H:%M BJT")

    # 2026-08-25 尘仓修复: MIN_NOTIONAL(<$5卖不掉) → Convert闪兑兜底
    if isinstance(result, dict) and result.get("code") == "MIN_NOTIONAL":
        log(f"💱 {coin} 低于minNotional, 转Convert闪兑兜底...")
        result = convert_dust_to_usdt(api_key, secret, coin, qty)
        if isinstance(result, dict) and result.get("status") == "FILLED":
            log(f"✅ {coin} Convert闪兑成功 → {result.get('toAmount')} USDT")

    exec_status = "FAILED"
    exec_price = 0
    fills_info = {}
    exit_reason = sell_signal.get("reason", "信号触发")

    if "status" in result and result["status"] == "FILLED":
        exec_status = "FILLED"
        fills = result.get("fills", [])
        if result.get("convert"):  # Convert闪兑成交: 价=到账/数量
            try:
                exec_price = float(result.get("toAmount", 0)) / qty
            except (TypeError, ZeroDivisionError):
                exec_price = 0
        elif fills:
            exec_price = float(fills[0].get("price", 0))
            fills_info = {
                "price": exec_price,
                "qty": float(fills[0].get("qty", 0)),
                "commission": float(fills[0].get("commission", 0)),
            }
        log(f"✅ {coin} 已卖出! 价${exec_price:.4f} 数量{qty}")
    elif "code" in result:
        exec_status = f"REJECTED_{result['code']}"
        log(f"⚠️ {coin} 卖出拒绝: {result.get('error', '未知')}")
    else:
        exec_status = result.get("status", "UNKNOWN")
        log(f"⚠️ {coin} 卖出异常: {json.dumps(result)[:200]}")

    trade_line = f"""### {ts} | A4独立执行
| 字段 | 值 |
|:-----|:---|
| 指令来源 | A4 信号文件 |
| 币种 | {coin} |
| 方向 | SELL |
| 执行价 | ${exec_price:.4f} |
| 执行量 | {qty} {coin} |
| 原因 | {exit_reason} |
| PnL | {sell_signal.get('pnl_pct', '?')}% |
| 状态 | ✅ {exec_status} |
"""
    append_trades_line(trade_line)

    return {
        "coin": coin,
        "action": "SELL",
        "status": exec_status,
        "exec_price": exec_price,
        "quantity": qty,
        "fills": fills_info,
        "reason": exit_reason,
        "raw": result.get("orderId", ""),
        "executed_at": ts,
    }

# ───────── 主流程 ─────────

def main():
    ts_start = bjt_now().strftime("%Y-%m-%d %H:%M BJT")
    log(f"══════ A4独立执行节点启动 [{ts_start}] ══════")

    # 1. 读信号
    signal = load_signals()
    if signal is None:
        log("无新信号")
        return {"status": "idle", "reason": "无新信号"}

    if signal.get("expired"):
        return {"status": "expired", "reason": f"信号已过期"}

    signal_id = signal.get("signal_id", "?")
    log(f"发现信号: {signal_id}")
    log(f"  买入信号: {len(signal.get('buy_signals', []))}个")
    log(f"  卖出信号: {len(signal.get('sell_signals', []))}个")

    # 如果没有买入也没有卖出，标记为已处理并退出
    if not signal.get("buy_signals") and not signal.get("sell_signals"):
        results = {
            "processed_signal_id": signal_id,
            "processed_at": ts_start,
            "executions": [],
            "status": "noop",
        }
        save_results(results)
        log("信号无操作，标记为已处理")
        return results

    # 2. 加载API密钥
    try:
        api_key, secret = load_auth()
    except Exception as e:
        log(f"❌ API密钥加载失败: {e}")
        return {"status": "error", "reason": str(e)}

    # 3. 自验证
    valid, issues = self_verify(signal, api_key, secret)
    if not valid:
        log(f"⚠️ 自验证未通过:")
        for issue in issues:
            log(f"  ❌ {issue}")
        # 记录验证失败但是继续执行通过的信号
        results = {
            "processed_signal_id": signal_id,
            "processed_at": ts_start,
            "status": "verify_issues",
            "issues": issues,
            "executions": [],
        }

        # 获取余额，决定哪些信号可以执行
    assets, usdt_free = check_balance(api_key, secret)
    log(f"USDT余额: ${usdt_free:.2f} | 持仓: {len(assets)}个")

    # 4. 执行
    executions = []

    # 4a. 先执行卖出（释放资金）
    bl = load_blacklist()
    for sell in signal.get("sell_signals", []):
        coin = sell.get("coin", "")
        try:
            result = execute_sell(sell, api_key, secret)
            executions.append(result)
            # check PnL: if loss > 10% blacklist
            pnl_str = sell.get("pnl_pct", "0")
            try:
                pnl = float(pnl_str.replace("%", ""))
            except:
                pnl = 0
            if result.get("status") == "FILLED" and pnl < -10:
                blacklist_coin(coin, f"sell loss {pnl:.1f}%", pnl, bl)
            elif result.get("status") == "FILLED" and pnl < -5:
                log(f"LOSS {coin}: {pnl:.1f}%")
        except Exception as e:
            log(f"❌ {coin} 卖出异常: {e}")
            executions.append({"coin": coin, "action": "SELL", "status": "ERROR", "error": str(e)})

    save_blacklist(bl)
    # 4b. 重新查余额（卖出后资金回笼）
    try:
        assets, usdt_free = check_balance(api_key, secret)
        log(f"卖出后USDT余额: ${usdt_free:.2f}")
    except:
        pass

    # 4c. 执行买入
    # 🛡️ 网格资金保留: ETH网格独占USDT，free<$30禁止A4新买入（NAVIGATION.md §二, 2026-08-31）
    if usdt_free < GRID_USDT_RESERVE:
        log(f"🛡️ 网格资金保留: free=${usdt_free:.2f}<${GRID_USDT_RESERVE} — 跳过全部买入, USDT留给ETH网格")
        signal["buy_signals"] = []
    for buy in signal.get("buy_signals", []):
        if usdt_free < MIN_BUY_USDT:
            log(f"余额不足(${usdt_free:.2f})，停止买入")
            break
        coin = buy.get("coin", "")
        try:
            result = execute_buy(buy, api_key, secret, usdt_free)
            executions.append(result)
            if result.get("status") == "FILLED":
                usdt_free -= result.get("amount", 0)
        except Exception as e:
            log(f"❌ {coin} 买入异常: {e}")
            executions.append({"coin": coin, "action": "BUY", "status": "ERROR", "error": str(e)})

    # 5. 保存结果
    ts_end = bjt_now().strftime("%Y-%m-%d %H:%M BJT")
    results = {
        "processed_signal_id": signal_id,
        "processed_at": ts_end,
        "status": "completed",
        "executions": executions,
        "summary": {
            "total": len(executions),
            "filled": sum(1 for e in executions if e.get("status") == "FILLED"),
            "failed": sum(1 for e in executions if e.get("status", "").startswith(("FAILED", "ERROR", "REJECTED"))),
            "skipped": sum(1 for e in executions if e.get("status") == "SKIP"),
        }
    }
    save_results(results)

    log(f"✅ 执行完成: {results['summary']}")
    return results


if __name__ == "__main__":
    try:
        r = main()
        print(json.dumps(r, indent=2, default=str))
    except Exception as e:
        log(f"❌ 未捕获异常: {e}")
        import traceback
        traceback.print_exc()
