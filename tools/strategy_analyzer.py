#!/usr/bin/env python3
"""
策略分析统计器 — 从交易数据中提取规律
铁律六: 每日盈利自检 — 今天为什么盈利/没盈利

用法:
    python3 tools/strategy_analyzer.py          # 生成分析报告
    python3 tools/strategy_analyzer.py --verbose # 详细输出
"""
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

ZQ_BASE = "/home/ubuntu/zq_web4_trading_system"
SC = "/home/ubuntu/shared_context"
REPORT_DIR = os.path.join(SC, "strategies", "__trade_db__")
os.makedirs(REPORT_DIR, exist_ok=True)


def load_csv_trades():
    """从 daily_profit_log.csv 加载历史交易"""
    path = os.path.join(ZQ_BASE, "data/trades/daily_profit_log.csv")
    trades = []
    if not os.path.exists(path):
        return trades
    with open(path) as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 5:
                continue
            trades.append({
                "datetime": row[0],
                "type": row[1],
                "symbol": row[2],
                "price": float(row[3]) if row[3] else 0,
                "qty": float(row[4]) if row[4] else 0,
                "pnl": float(row[6].replace("+$", "").replace("-$", "")) if len(row) > 6 and row[6] else 0,
            })
    return trades


def load_daily_ledger():
    """从 daily_profit_ledger.md 加载每日盈亏"""
    path = os.path.join(ZQ_BASE, "data/daily_profit_ledger.md")
    records = []
    if not os.path.exists(path):
        return records
    with open(path) as f:
        current = {}
        for line in f:
            line = line.strip()
            if line.startswith("## ") and "每日盈利账本" in line:
                if current:
                    records.append(current)
                current = {"date": line.replace("## ", "").replace(" 币安每日盈利账本", "")}
            elif "总资产" in line and "$" in line:
                parts = line.split("$")
                if len(parts) > 1:
                    val = parts[1].split("(")[0].split("（")[0].strip()
                    current["total_asset"] = val
            elif "网格毛利润" in line:
                if "+$" in line:
                    current["grid_pnl"] = line.split("+$")[1].split("**")[0].strip()
                elif "-$" in line:
                    current["grid_pnl"] = "-" + line.split("-$")[1].split("**")[0].strip()
            elif "ETH 持仓" in line:
                if "+$" in line:
                    current["eth_pnl"] = "+" + line.split("+$")[1].split("**")[0].strip()
                elif "-$" in line:
                    current["eth_pnl"] = "-" + line.split("-$")[1].split("**")[0].strip()
        if current:
            records.append(current)
    return records


def load_pnl_report():
    """加载每日PnL报告"""
    path = os.path.join(ZQ_BASE, "data/daily_pnl_report.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def load_total_asset():
    """加载总资产"""
    path = os.path.join(SC, "trades/total_asset.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def load_trend_state():
    """加载当前趋势策略状态"""
    path = os.path.join(ZQ_BASE, "data/trades/trend_state.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def load_trend_trades():
    """加载趋势策略交易记录"""
    path = os.path.join(ZQ_BASE, "data/trades/trend_trades.jsonl")
    trades = []
    if not os.path.exists(path):
        return trades
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    trades.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return trades


def analyze():
    """主分析函数"""
    verbose = "--verbose" in sys.argv

    csv_trades = load_csv_trades()
    ledger = load_daily_ledger()
    pnl_report = load_pnl_report()
    total_asset = load_total_asset()
    trend_state = load_trend_state()
    trend_trades = load_trend_trades()

    # 统计
    analysis = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "current": {
            "total_asset": total_asset.get("total", "?"),
            "date": total_asset.get("date", "?"),
            "trend_mode": trend_state.get("mode", "?"),
            "peak_close": trend_state.get("peak_close", "?"),
            "channel_high": trend_state.get("channel_high", "?"),
            "channel_low": trend_state.get("channel_low", "?"),
            "holdings": [
                {"asset": h.get("asset", "?"), "value": h.get("value", 0)}
                for h in pnl_report.get("holdings", [])[:10]
            ],
            "today_24h": {
                "buys": pnl_report.get("today_24h", {}).get("buys", 0),
                "sells": pnl_report.get("today_24h", {}).get("sells", 0),
                "buy_usd": pnl_report.get("today_24h", {}).get("buy_usd", 0),
                "sell_usd": pnl_report.get("today_24h", {}).get("sell_usd", 0),
            },
        },
        "trend_strategy_v31": {
            "trades_count": len(trend_trades),
            "mode": trend_state.get("mode", "?"),
            "cfg_version": trend_state.get("cfg_version", "?"),
            "trail_pct": trend_state.get("trail_pct", "?"),
        },
        "historical_csv": {
            "total_records": len(csv_trades),
            "buy_count": sum(1 for t in csv_trades if "BUY" in t["type"]),
            "sell_tp": sum(1 for t in csv_trades if "TP" in t["type"]),
            "sell_sl": sum(1 for t in csv_trades if "SL" in t["type"]),
            "total_pnl": round(sum(t["pnl"] for t in csv_trades), 2),
            "win_count": sum(1 for t in csv_trades if t["pnl"] > 0),
            "loss_count": sum(1 for t in csv_trades if t["pnl"] < 0),
        },
        "daily_ledger": {
            "records": len(ledger),
            "latest": ledger[-1] if ledger else None,
        },
    }

    # 计算胜率
    if csv_trades:
        pnl_trades = [t for t in csv_trades if t["pnl"] != 0]
        if pnl_trades:
            wins = sum(1 for t in pnl_trades if t["pnl"] > 0)
            analysis["historical_csv"]["win_rate"] = round(wins / len(pnl_trades) * 100, 1)
        else:
            analysis["historical_csv"]["win_rate"] = 0
    else:
        analysis["historical_csv"]["win_rate"] = 0

    # 每日盈亏趋势
    if ledger:
        assets = []
        for r in ledger:
            if "total_asset" in r:
                try:
                    assets.append(float(r["total_asset"]))
                except (ValueError, TypeError):
                    pass
        if len(assets) >= 2:
            analysis["daily_ledger"]["asset_trend"] = "↑" if assets[-1] > assets[0] else "↓"
            analysis["daily_ledger"]["asset_change"] = round(assets[-1] - assets[0], 2)
            analysis["daily_ledger"]["asset_start"] = assets[0]
            analysis["daily_ledger"]["asset_end"] = assets[-1]

    # 根因分析
    analysis["root_cause"] = {
        "current_strategy": "ETH趋势通道v3.1 (Donchian 5日突破+2%盈利锁定)",
        "mode": trend_state.get("mode", "unknown"),
        "decision": "持有ETH" if trend_state.get("mode") == "eth" else "持有USDT",
        "today_profit_target": round(float(total_asset.get("total", 201)) * 0.002, 2),
        "today_24h_net": round(
            pnl_report.get("today_24h", {}).get("sell_usd", 0) -
            pnl_report.get("today_24h", {}).get("buy_usd", 0), 2
        ),
        "lesson": "新策略v3.1尚未完成首笔交易，处于HOLD/持有ETH状态",
        "action_item": "等待通道突破信号或2%盈利锁定触发",
    }

    # 保存
    report_path = os.path.join(REPORT_DIR, "strategy_analysis.json")
    with open(report_path, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    # 输出
    if verbose:
        print("=== 策略分析统计 ===")
        print(f"\n当前策略: {analysis['root_cause']['current_strategy']}")
        print(f"模式: {analysis['root_cause']['mode']} ({analysis['root_cause']['decision']})")
        print(f"\n总资产: ${analysis['current']['total_asset']}")
        print(f"今日目标: ${analysis['root_cause']['today_profit_target']}")
        print(f"今日24h: 买{analysis['current']['today_24h']['buys']}笔 ${analysis['current']['today_24h']['buy_usd']} / 卖{analysis['current']['today_24h']['sells']}笔 ${analysis['current']['today_24h']['sell_usd']}")
        print(f"\n趋势策略v3.1交易数: {analysis['trend_strategy_v31']['trades_count']}")
        print(f"\n历史CSV交易: {analysis['historical_csv']['total_records']}笔, 胜率{analysis['historical_csv']['win_rate']}%, 总PnL ${analysis['historical_csv']['total_pnl']}")
        print(f"\n每日账本记录: {analysis['daily_ledger']['records']}条")

    print(json.dumps(analysis, ensure_ascii=False))
    print(f"\n✅ 报告已保存: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(analyze())
