#!/usr/bin/env python3
"""
交易数据库 — 每笔交易的记录/查询/分析

用途：
  1. 记录每笔交易的完整信息（入场/出场/原因/结果）
  2. 统计分析各信号的成功率
  3. 为下一笔交易提供数据支撑

数据文件：
  __trade_db__/trades.jsonl — 逐笔交易记录（追加写入）
  __trade_db__/trade_stats.json — 实时统计汇总
  __trade_db__/strategy_signals.json — 各信号胜率统计

使用方法：
  python3 trade_db.py record --coin BTC --entry 68000 --reason "放量突破" ...
  python3 trade_db.py stats  # 查看统计
  python3 trade_db.py signals  # 查看信号胜率
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "strategies", "__trade_db__")
TRADES_FILE = os.path.join(DB_DIR, "trades.jsonl")
STATS_FILE = os.path.join(DB_DIR, "trade_stats.json")
SIGNALS_FILE = os.path.join(DB_DIR, "strategy_signals.json")
NAV_FILE = os.path.join(os.path.dirname(__file__), "..", "NAVIGATION.md")

BJT = timezone(timedelta(hours=8))

def ensure_db():
    os.makedirs(DB_DIR, exist_ok=True)
    for f in [TRADES_FILE, STATS_FILE, SIGNALS_FILE]:
        if not os.path.exists(f):
            with open(f, "w") as fh:
                json.dump([], fh) if f.endswith(".json") else fh.write("")

def record_trade(trade_data):
    """记录一笔交易"""
    ensure_db()
    trade_data["recorded_at"] = datetime.now(BJT).isoformat()
    if "trade_id" not in trade_data:
        today = datetime.now(BJT).strftime("%Y%m%d")
        existing = [t for t in load_trades() if t.get("trade_id", "").startswith(f"T{today}")]
        n = len(existing) + 1
        trade_data["trade_id"] = f"T{today}_{n:03d}"
    with open(TRADES_FILE, "a") as f:
        f.write(json.dumps(trade_data, ensure_ascii=False) + "\n")
    _recalc_stats()
    return trade_data["trade_id"]

def load_trades():
    """加载所有交易"""
    ensure_db()
    trades = []
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    trades.append(json.loads(line))
    return trades

def _recalc_stats():
    """重新计算统计"""
    trades = load_trades()
    closed = [t for t in trades if t.get("exit_price")]
    total = len(closed)
    wins = len([t for t in closed if t.get("pnl_usdt", 0) > 0])
    losses = len([t for t in closed if t.get("pnl_usdt", 0) <= 0])
    total_pnl = sum(t.get("pnl_usdt", 0) for t in closed)
    
    # 日统计
    today = datetime.now(BJT).strftime("%Y-%m-%d")
    today_trades = [t for t in closed if t.get("entry_time","").startswith(today)]
    today_pnl = sum(t.get("pnl_usdt", 0) for t in today_trades)
    
    stats = {
        "last_updated": datetime.now(BJT).isoformat(),
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
        "total_pnl_usdt": round(total_pnl, 2),
        "today_trades": len(today_trades),
        "today_pnl_usdt": round(today_pnl, 2),
        "best_trade": max(closed, key=lambda t: t.get("pnl_usdt", 0)) if closed else None,
        "worst_trade": min(closed, key=lambda t: t.get("pnl_usdt", 0)) if closed else None,
    }
    
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    # 信号胜率统计
    signal_stats = {}
    for t in closed:
        signals = t.get("entry_signals", {})
        pnl = t.get("pnl_usdt", 0)
        for sig, triggered in signals.items():
            if triggered:
                if sig not in signal_stats:
                    signal_stats[sig] = {"count": 0, "wins": 0, "total_pnl": 0}
                signal_stats[sig]["count"] += 1
                signal_stats[sig]["total_pnl"] += pnl
                if pnl > 0:
                    signal_stats[sig]["wins"] += 1
    
    for sig in signal_stats:
        c = signal_stats[sig]
        c["win_rate"] = round(c["wins"] / c["count"] * 100, 1) if c["count"] > 0 else 0
    
    with open(SIGNALS_FILE, "w") as f:
        json.dump(signal_stats, f, ensure_ascii=False, indent=2)
    
    return stats

def cmd_stats():
    stats = _recalc_stats()
    print(f"📊 交易统计")
    print(f"  {'总交易数:':15s} {stats['total_trades']}")
    print(f"  {'胜:':15s} {stats['wins']}")
    print(f"  {'负:':15s} {stats['losses']}")
    print(f"  {'胜率:':15s} {stats['win_rate']}%")
    print(f"  {'总盈亏:':15s} {stats['total_pnl_usdt']} USDT")
    print(f"  {'今日交易:':15s} {stats['today_trades']}")
    print(f"  {'今日盈亏:':15s} {stats['today_pnl_usdt']} USDT")

def cmd_signals():
    _recalc_stats()
    with open(SIGNALS_FILE) as f:
        signals = json.load(f)
    if not signals:
        print("暂无信号统计数据")
        return
    print("📈 信号胜率排名")
    sorted_sigs = sorted(signals.items(), key=lambda x: x[1]["win_rate"], reverse=True)
    for sig, data in sorted_sigs:
        print(f"  {sig:30s} {data['win_rate']:>5.1f}% ({data['wins']}/{data['count']}) PnL:{data['total_pnl']:+.1f}")

def cmd_list(limit=10):
    trades = load_trades()
    if not trades:
        print("暂无交易记录")
        return
    print(f"📋 最近{limit}笔交易")
    for t in reversed(trades[-limit:]):
        pnl = t.get("pnl_usdt", 0)
        pnl_str = f"+{pnl}" if pnl > 0 else str(pnl)
        print(f"  [{t.get('trade_id','?')}] {t.get('coin','?'):10s} "
              f"入:{t.get('entry_price','?'):>8}  出:{t.get('exit_price','?'):>8}  "
              f"盈亏:{pnl_str:>8}  {t.get('entry_reason','')[:30]}")

def cmd_record():
    """从命令行参数记录交易"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--coin", required=True)
    parser.add_argument("--entry", required=True, type=float)
    parser.add_argument("--exit", type=float)
    parser.add_argument("--reason", default="")
    parser.add_argument("--result", default="")
    parser.add_argument("--signals", default="")
    args = parser.parse_args()
    
    trade = {
        "coin": args.coin.upper(),
        "entry_time": datetime.now(BJT).isoformat(),
        "entry_price": args.entry,
        "exit_price": args.exit,
        "entry_reason": args.reason,
        "exit_reason": args.result,
        "entry_signals": {s.strip(): True for s in args.signals.split(",") if s.strip()},
    }
    if args.exit:
        trade["pnl_usdt"] = round((args.exit - args.entry) * 1, 2)  # 数量待完善
    tid = record_trade(trade)
    print(f"✅ 已记录交易 {tid}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_stats()
    elif sys.argv[1] == "stats":
        cmd_stats()
    elif sys.argv[1] == "signals":
        cmd_signals()
    elif sys.argv[1] == "list":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        cmd_list(limit)
    elif sys.argv[1] == "record":
        cmd_record()
    else:
        print(f"用法: {sys.argv[0]} [stats|signals|list|record]")
