#!/usr/bin/env python3
"""
止损单同步验证器 (Stop Order Sync Verifier)
功能：验证每个持仓在交易所端是否有对应的止损单
防止"裸奔"（持仓但无止损单的危险状态）

运行方式：
- Cron: 每小时执行1次
- 手动: python3 stop_order_verifier.py
- 修复: python3 stop_order_verifier.py --fix
"""
import json, os, sys, time, ccxt

SC = "/home/ubuntu/shared_context"
REPORT_FILE = os.path.join(SC, "risk/stop_order_audit.json")
ALERT_FILE = os.path.join(SC, "alerts/stop_order_mismatch.json")
EVENTS_FILE = os.path.join(SC, "events/events.ndjson")

EXCHANGES = {
    "binance": {"api_key": "BINANCE_API_KEY", "api_secret": "BINANCE_API_SECRET"},
    "htx": {"api_key": "HTX_API_KEY", "api_secret": "HTX_API_SECRET"},
    "okx": {"api_key": "OKX_API_KEY", "api_secret": "OKX_API_SECRET"},
}


def load_env():
    env_path = os.path.expanduser("~/.env")
    env = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


def get_exchange(name, env):
    cfg = EXCHANGES.get(name)
    if not cfg:
        return None
    key = env.get(cfg["api_key"], "")
    secret = env.get(cfg["api_secret"], "")
    if not key or not secret:
        return None
    if name == "binance":
        return ccxt.binance({"apiKey": key, "secret": secret, "enableRateLimit": True})
    elif name == "htx":
        return ccxt.htx({"apiKey": key, "secret": secret, "enableRateLimit": True})
    elif name == "okx":
        return ccxt.okx({"apiKey": key, "secret": secret, "password": env.get("OKX_PASSPHRASE", ""), "enableRateLimit": True})
    return None


def load_positions():
    path = os.path.join(SC, "trades/positions.json")
    try:
        with open(path) as f:
            return json.load(f).get("positions", [])
    except Exception:
        return []


def load_open_stop_orders(exchange, symbol):
    """查询交易所端的挂单（止损单/止盈单）"""
    try:
        orders = exchange.fetch_open_orders(symbol)
        stop_orders = []
        for o in orders:
            otype = o.get("type", "")
            if otype in ("STOP", "STOP_LOSS", "STOP_MARKET", "TAKE_PROFIT", "TAKE_PROFIT_MARKET", "trigger"):
                stop_orders.append({
                    "id": o.get("id"),
                    "type": otype,
                    "side": o.get("side"),
                    "amount": o.get("amount"),
                    "price": o.get("price") or o.get("stopPrice"),
                    "status": o.get("status"),
                })
        return stop_orders
    except Exception as e:
        return [{"error": str(e)}]


def log_event(event_type, message):
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,
        "source": "stop_order_verifier",
        "message": message,
    }
    os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
    with open(EVENTS_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def verify():
    env = load_env()
    positions = load_positions()
    results = []
    naked_count = 0
    mismatch_count = 0
    ok_count = 0

    for p in positions:
        coin = p.get("coin", "?")
        exchange_name = p.get("exchange", "binance")
        symbol = f"{coin}/USDT"
        entry_price = p.get("entry_price", 0)
        side = p.get("side", "long")

        ex = get_exchange(exchange_name, env)
        if not ex:
            results.append({
                "coin": coin,
                "exchange": exchange_name,
                "status": "SKIP",
                "reason": "交易所未配置或无API密钥",
            })
            continue

        stop_orders = load_open_stop_orders(ex, symbol)

        has_stop_loss = any(
            o.get("type", "").startswith("STOP") and o.get("side", "") == "sell"
            for o in stop_orders if "error" not in o
        )
        has_take_profit = any(
            "TAKE_PROFIT" in o.get("type", "")
            for o in stop_orders if "error" not in o
        )

        if any("error" in o for o in stop_orders):
            status = "ERROR"
            reason = f"查询失败: {stop_orders[0].get('error', 'unknown')}"
        elif not has_stop_loss:
            status = "NAKED"
            reason = "无止损单！持仓裸奔！"
            naked_count += 1
        elif not has_take_profit:
            status = "MISSING_TP"
            reason = "有止损单但无止盈单"
            mismatch_count += 1
        else:
            status = "OK"
            reason = f"止损+止盈单均存在({len(stop_orders)}个挂单)"
            ok_count += 1

        results.append({
            "coin": coin,
            "exchange": exchange_name,
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "stop_orders": len(stop_orders) if stop_orders and "error" not in stop_orders[0] else 0,
            "has_stop_loss": has_stop_loss,
            "has_take_profit": has_take_profit,
            "status": status,
            "reason": reason,
        })

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_positions": len(positions),
        "ok": ok_count,
        "naked": naked_count,
        "mismatch": mismatch_count,
        "summary": f"{ok_count}正常 / {naked_count}裸奔 / {mismatch_count}不完整",
        "positions": results,
    }

    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    if naked_count > 0 or mismatch_count > 0:
        alert = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "severity": "CRITICAL" if naked_count > 0 else "WARNING",
            "type": "stop_order_mismatch",
            "message": f"止损单验证异常: {naked_count}个裸奔, {mismatch_count}个不完整",
            "details": [r for r in results if r["status"] not in ("OK", "SKIP")],
        }
        os.makedirs(os.path.dirname(ALERT_FILE), exist_ok=True)
        with open(ALERT_FILE, "w") as f:
            json.dump(alert, f, indent=2, ensure_ascii=False)
        log_event("risk.alert", f"止损单验证异常: {alert['message']}")

    log_event("risk.audit", f"止损单验证完成: {report['summary']}")
    print(f"[止损验证] {report['summary']}")
    for r in results:
        icon = {"OK": "✓", "NAKED": "✗", "MISSING_TP": "⚠", "ERROR": "?", "SKIP": "-"}.get(r["status"], "?")
        print(f"  {icon} {r['coin']} ({r['exchange']}): {r['status']} — {r.get('reason', '')}")

    return report


def fix():
    """尝试为裸奔持仓补下止损单"""
    env = load_env()
    positions = load_positions()
    import dsl_stop_loss

    fixed = 0
    for p in positions:
        coin = p.get("coin", "?")
        exchange_name = p.get("exchange", "binance")
        symbol = f"{coin}/USDT"
        side = p.get("side", "long")
        entry_price = p.get("entry_price", 0)

        ex = get_exchange(exchange_name, env)
        if not ex:
            continue

        stop_orders = load_open_stop_orders(ex, symbol)
        has_stop_loss = any(
            o.get("type", "").startswith("STOP") and o.get("side", "") == "sell"
            for o in stop_orders if "error" not in o
        )

        if not has_stop_loss:
            dsl = dsl_stop_loss.compute_stop_loss(p)
            stop_price = dsl.get("stop_loss_price", entry_price * 0.92)

            try:
                if side == "long":
                    ex.create_order(symbol, "STOP_LOSS", "sell", p.get("qty", 0), stop_price)
                else:
                    ex.create_order(symbol, "STOP_LOSS", "buy", p.get("qty", 0), stop_price)

                print(f"  ✓ {coin} 止损单已补下 @ {stop_price}")
                log_event("risk.fix", f"{coin} 止损单补下成功 @ {stop_price}")
                fixed += 1
            except Exception as e:
                print(f"  ✗ {coin} 止损单补下失败: {e}")
                log_event("risk.alert", f"{coin} 止损单补下失败: {e}")

    print(f"[止损修复] 完成: {fixed}个止损单已补下")
    return fixed


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--fix":
        fix()
    else:
        verify()
