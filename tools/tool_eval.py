#!/usr/bin/env python3
"""
tool_eval.py — 工具效果评估 (Before/After comparison)

评估新工具/策略引入前后的交易效果变化。
比较指标: 胜率、平均P&L、退出质量、E系列信号准确率。

Usage:
    # 分析指定工具
    python3 tools/tool_eval.py --tool freqtrade=2026-05-07 --days 14

    # 分析多个工具
    python3 tools/tool_eval.py --tool direction_judger=2026-05-07 --tool debate_manager=2026-05-07

    # 从TOOL_LOG.md自动检测所有工具
    python3 tools/tool_eval.py --auto-detect --days 7

    # 查看可用模式
    python3 tools/tool_eval.py
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

# === Paths ===
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES_DIR = os.path.join(PROJECT_ROOT, "data", "experience", "trades")
MASTER_EXP_PATH = os.path.join(PROJECT_ROOT, "data", "experience", "MASTER_EXPERIENCE.json")
TOOL_LOG_PATH = os.path.join(PROJECT_ROOT, "tools", "TOOL_LOG.md")
AUDIT_TRADES_PATH = os.path.join(PROJECT_ROOT, "audit", "TRADES.md")


def parse_args():
    parser = argparse.ArgumentParser(
        description="工具效果评估 — Before/After comparison",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--tool",
        action="append",
        dest="tools",
        help="指定工具名和引入日期: --tool name=YYYY-MM-DD (可多次使用)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="比较窗口天数 (默认: 14)",
    )
    parser.add_argument(
        "--auto-detect",
        action="store_true",
        help="从 TOOL_LOG.md 自动检测所有已安装工具及其发现日期",
    )
    return parser.parse_args()


# ============================================================
#  Data Loading
# ============================================================

def load_all_trades() -> list[dict]:
    """Load all trade JSON files from data/experience/trades/"""
    trades = []
    if not os.path.isdir(TRADES_DIR):
        print(f"⚠️  交易目录不存在: {TRADES_DIR}", file=sys.stderr)
        return trades

    for fname in sorted(os.listdir(TRADES_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(TRADES_DIR, fname)
        try:
            with open(fpath) as f:
                data = json.load(f)
            analysis = data.get("analysis", {})
            sell_time_str = analysis.get("sell_time", "")
            # Parse sell_time — format: "2026-04-30 14:26:07"
            sell_dt = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    sell_dt = datetime.strptime(sell_time_str, fmt)
                    break
                except ValueError:
                    continue
            if sell_dt is None:
                continue

            trades.append({
                "symbol": analysis.get("symbol", ""),
                "sell_time": sell_dt,
                "buy_time_str": analysis.get("buy_time", ""),
                "pnl_pct": analysis.get("pnl_pct", 0.0),
                "pnl_usd": analysis.get("pnl_usd", 0.0),
                "exit_reason": analysis.get("exit_reason", ""),
                "exit_quality": analysis.get("exit_quality", "unknown"),
                "trigger_signals": analysis.get("trigger_signals", []),
            })
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️  解析失败 {fname}: {e}", file=sys.stderr)
            continue

    return trades


def load_master_experience() -> dict:
    """Load MASTER_EXPERIENCE.json"""
    if not os.path.isfile(MASTER_EXP_PATH):
        return {"rules": []}
    with open(MASTER_EXP_PATH) as f:
        return json.load(f)


def detect_tools_from_log() -> list[tuple[str, str]]:
    """Parse TOOL_LOG.md to extract (tool_name, date) pairs."""
    if not os.path.isfile(TOOL_LOG_PATH):
        return []
    tools = []
    with open(TOOL_LOG_PATH) as f:
        for line in f:
            # Match table rows like: | freqtrade | 2026-05-07 | ...
            m = re.match(
                r"\|\s*(\S[\w/._-]+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|",
                line
            )
            if m:
                name = m.group(1).strip()
                date_str = m.group(2).strip()
                tools.append((name, date_str))
    return tools


# ============================================================
#  Analysis
# ============================================================

def compute_metrics(trades: list[dict]) -> dict[str, Any]:
    """Compute key metrics for a set of trades."""
    if not trades:
        return {
            "total_trades": 0,
            "avg_pnl_pct": 0.0,
            "avg_pnl_usd": 0.0,
            "win_rate": 0.0,  # % of trades with pnl > 0
            "correct_exit_pct": 0.0,
            "wrong_exit_pct": 0.0,
            "neutral_exit_pct": 0.0,
            "total_pnl_usd": 0.0,
        }

    n = len(trades)
    winning = [t for t in trades if t["pnl_pct"] > 0]
    losing = [t for t in trades if t["pnl_pct"] < 0]
    correct = [t for t in trades if t["exit_quality"] == "correct"]
    wrong = [t for t in trades if t["exit_quality"] == "wrong"]
    neutral = [t for t in trades if t["exit_quality"] == "neutral"]

    total_pnl = sum(t["pnl_usd"] for t in trades)
    avg_pnl_pct = sum(t["pnl_pct"] for t in trades) / n

    return {
        "total_trades": n,
        "avg_pnl_pct": round(avg_pnl_pct, 2),
        "avg_pnl_usd": round(total_pnl / n, 2),
        "win_rate": round(len(winning) / n * 100, 1),
        "lose_rate": round(len(losing) / n * 100, 1),
        "correct_exit_pct": round(len(correct) / n * 100, 1),
        "wrong_exit_pct": round(len(wrong) / n * 100, 1),
        "neutral_exit_pct": round(len(neutral) / n * 100, 1),
        "total_pnl_usd": round(total_pnl, 2),
    }


def compute_signal_quality(trades: list[dict]) -> dict[str, Any]:
    """Analyze E-series signal quality (correct vs wrong exit by signal type)."""
    if not trades:
        return {}

    signal_stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "correct": 0, "wrong": 0})

    for t in trades:
        signals = t.get("trigger_signals", [])
        if not signals:
            continue
        for sig in signals:
            if sig.startswith("E"):
                signal_stats[sig]["total"] += 1
                if t["exit_quality"] == "correct":
                    signal_stats[sig]["correct"] += 1
                elif t["exit_quality"] == "wrong":
                    signal_stats[sig]["wrong"] += 1

    results = {}
    for sig, stats in sorted(signal_stats.items()):
        results[sig] = {
            "total": stats["total"],
            "correct": stats["correct"],
            "wrong": stats["wrong"],
            "correct_rate": round(stats["correct"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0,
            "wrong_rate": round(stats["wrong"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0,
        }
    return results


# ============================================================
#  Output
# ============================================================

def print_tooleval_section(
    tool_name: str,
    tool_date: str,
    before_metrics: dict,
    after_metrics: dict,
):
    """Print TOOL_EVAL section for one tool."""
    b = before_metrics
    a = after_metrics

    delta_win = round(a["win_rate"] - b["win_rate"], 1)
    delta_avg_pnl = round(a["avg_pnl_pct"] - b["avg_pnl_pct"], 2)
    delta_correct = round(a["correct_exit_pct"] - b["correct_exit_pct"], 1)
    delta_wrong = round(a["wrong_exit_pct"] - b["wrong_exit_pct"], 1)
    delta_total_pnl = round(a["total_pnl_usd"] - b["total_pnl_usd"], 2)

    print(f"### 📊 {tool_name}")
    print(f"**引入日期:** {tool_date}")
    print(f"**Before:** {b['total_trades']} trades")
    print(f"**After:** {a['total_trades']} trades")
    print()
    print("| 指标 | Before | After | Δ (变化) | 方向 |")
    print("|------|--------|-------|----------|------|")
    print(f"| 总交易数 | {b['total_trades']} | {a['total_trades']} | {a['total_trades'] - b['total_trades']:+d} | — |")
    print(f"| 胜率 (P&L>0) | {b['win_rate']}% | {a['win_rate']}% | {delta_win:+0.1f}% | {'📈' if delta_win > 0 else '📉' if delta_win < 0 else '➖'} |")
    print(f"| 平均P&L% | {b['avg_pnl_pct']}% | {a['avg_pnl_pct']}% | {delta_avg_pnl:+0.2f}% | {'📈' if delta_avg_pnl > 0 else '📉' if delta_avg_pnl < 0 else '➖'} |")
    print(f"| 正确退出% | {b['correct_exit_pct']}% | {a['correct_exit_pct']}% | {delta_correct:+0.1f}% | {'📈' if delta_correct > 0 else '📉' if delta_correct < 0 else '➖'} |")
    print(f"| 错误退出% | {b['wrong_exit_pct']}% | {a['wrong_exit_pct']}% | {delta_wrong:+0.1f}% | {'📈' if delta_wrong < 0 else '📉' if delta_wrong > 0 else '➖'} |")
    print(f"| 中性退出% | {b['neutral_exit_pct']}% | {a['neutral_exit_pct']}% | {a['neutral_exit_pct'] - b['neutral_exit_pct']:+0.1f}% | — |")
    print(f"| 总P&L (USD) | ${b['total_pnl_usd']} | ${a['total_pnl_usd']} | ${delta_total_pnl:+0.2f} | {'📈' if delta_total_pnl > 0 else '📉' if delta_total_pnl < 0 else '➖'} |")
    print()


def print_keymetrics_section(all_before: dict, all_after: dict):
    """Print aggregated KEY_METRICS section."""
    b, a = all_before, all_after
    print("## 📋 KEY_METRICS — 综合前后对比")
    print()
    print("| 指标 | Before | After | Δ |")
    print("|------|--------|-------|-----|")
    print(f"| 总交易数 | {b['total_trades']} | {a['total_trades']} | {a['total_trades'] - b['total_trades']:+d} |")
    print(f"| 平均P&L% | {b['avg_pnl_pct']}% | {a['avg_pnl_pct']}% | {round(a['avg_pnl_pct'] - b['avg_pnl_pct'], 2):+0.2f}% |")
    print(f"| 胜率 | {b['win_rate']}% | {a['win_rate']}% | {round(a['win_rate'] - b['win_rate'], 1):+0.1f}% |")
    print(f"| 正确退出% | {b['correct_exit_pct']}% | {a['correct_exit_pct']}% | {round(a['correct_exit_pct'] - b['correct_exit_pct'], 1):+0.1f}% |")
    print(f"| 错误退出% | {b['wrong_exit_pct']}% | {a['wrong_exit_pct']}% | {round(a['wrong_exit_pct'] - b['wrong_exit_pct'], 1):+0.1f}% |")
    print(f"| 中性退出% | {b['neutral_exit_pct']}% | {a['neutral_exit_pct']}% | {round(a['neutral_exit_pct'] - b['neutral_exit_pct'], 1):+0.1f}% |")
    print(f"| 总P&L (USD) | ${b['total_pnl_usd']} | ${a['total_pnl_usd']} | ${round(a['total_pnl_usd'] - b['total_pnl_usd'], 2):+0.2f} |")
    print()


def print_conclusion(
    tool_name: str,
    before_metrics: dict,
    after_metrics: dict,
    before_signals: dict,
    after_signals: dict,
):
    """Print CONCLUSION for one tool."""
    b, a = before_metrics, after_metrics
    improvements = []
    regressions = []

    # Win rate
    if a["win_rate"] > b["win_rate"]:
        improvements.append(f"胜率 {b['win_rate']}% → {a['win_rate']}% ({round(a['win_rate'] - b['win_rate'], 1):+0.1f}%)")
    elif a["win_rate"] < b["win_rate"]:
        regressions.append(f"胜率 {b['win_rate']}% → {a['win_rate']}% ({round(a['win_rate'] - b['win_rate'], 1):+0.1f}%)")

    # Avg P&L
    if a["avg_pnl_pct"] > b["avg_pnl_pct"]:
        improvements.append(f"平均P&L {b['avg_pnl_pct']}% → {a['avg_pnl_pct']}% ({round(a['avg_pnl_pct'] - b['avg_pnl_pct'], 2):+0.2f}%)")
    elif a["avg_pnl_pct"] < b["avg_pnl_pct"]:
        regressions.append(f"平均P&L {b['avg_pnl_pct']}% → {a['avg_pnl_pct']}% ({round(a['avg_pnl_pct'] - b['avg_pnl_pct'], 2):+0.2f}%)")

    # Wrong exit rate (lower is better)
    if a["wrong_exit_pct"] < b["wrong_exit_pct"]:
        improvements.append(f"错误退出率 {b['wrong_exit_pct']}% → {a['wrong_exit_pct']}% ({round(a['wrong_exit_pct'] - b['wrong_exit_pct'], 1):+0.1f}%)")
    elif a["wrong_exit_pct"] > b["wrong_exit_pct"]:
        regressions.append(f"错误退出率 {b['wrong_exit_pct']}% → {a['wrong_exit_pct']}% ({round(a['wrong_exit_pct'] - b['wrong_exit_pct'], 1):+0.1f}%)")

    # Correct exit rate
    if a["correct_exit_pct"] > b["correct_exit_pct"]:
        improvements.append(f"正确退出率 {b['correct_exit_pct']}% → {a['correct_exit_pct']}% ({round(a['correct_exit_pct'] - b['correct_exit_pct'], 1):+0.1f}%)")
    elif a["correct_exit_pct"] < b["correct_exit_pct"]:
        regressions.append(f"正确退出率 {b['correct_exit_pct']}% → {a['correct_exit_pct']}% ({round(a['correct_exit_pct'] - b['correct_exit_pct'], 1):+0.1f}%)")

    # Signal quality
    for sig in sorted(set(list(before_signals.keys()) + list(after_signals.keys()))):
        bs = before_signals.get(sig, {})
        as_ = after_signals.get(sig, {})
        b_rate = bs.get("correct_rate", 0)
        a_rate = as_.get("correct_rate", 0)
        if b_rate > 0 or a_rate > 0:
            if a_rate > b_rate:
                improvements.append(f"{sig}信号正确率 {b_rate}% → {a_rate}% ({round(a_rate - b_rate, 1):+0.1f}%)")
            elif a_rate < b_rate:
                regressions.append(f"{sig}信号正确率 {b_rate}% → {a_rate}% ({round(a_rate - b_rate, 1):+0.1f}%)")

    print(f"### ✅ 结论: {tool_name}")
    if improvements:
        print()
        print("**📈 改善项:**")
        for item in improvements:
            print(f"  - ✅ {item}")
    if regressions:
        print()
        print("**📉 退步项:**")
        for item in regressions:
            print(f"  - ⚠️ {item}")

    # Overall verdict
    score = len(improvements) - len(regressions)
    print()
    if score > 0:
        print(f"**🏆 总体: 该工具产生了正向效果 ({score:+d} 改善 vs {len(regressions)} 退步)**")
        if a["correct_exit_pct"] > b["correct_exit_pct"] and a["avg_pnl_pct"] > b["avg_pnl_pct"]:
            print("  → **强烈建议保留** — 退出质量和盈利能力均有提升")
        else:
            print("  → **建议保留** — 总体正向但部分指标需继续观察")
    elif score == 0:
        print(f"**➖ 总体: 效果中性 ({score} 改善 vs {len(regressions)} 退步)**")
        print("  → **建议继续观察** — 效果不够明显，需更多数据")
    else:
        print(f"**⚠️ 总体: 效果负面 ({len(improvements)} 改善 vs {len(regressions)} 退步)**")
        if a["wrong_exit_pct"] > b["wrong_exit_pct"] * 1.2:
            print("  → **建议调整或替换** — 错误退出率显著上升")
        else:
            print("  → **建议调整** — 负面效果可能由其他因素导致，排查根因")
    print()


def print_usage_hint():
    """Print usage info when no tools specified."""
    print("# 🔍 工具效果评估 (Before/After Comparison)")
    print()
    print("## 使用方式")
    print()
    print("```bash")
    print("# 分析单个工具")
    print("python3 tools/tool_eval.py --tool 工具名=YYYY-MM-DD --days 14")
    print()
    print("# 分析多个工具")
    print('python3 tools/tool_eval.py --tool "direction_judger=2026-05-07" --tool "debate_manager=2026-05-07"')
    print()
    print("# 自动检测所有工具")
    print("python3 tools/tool_eval.py --auto-detect --days 7")
    print("```")
    print()
    print("## 参数说明")
    print()
    print("| 参数 | 说明 | 默认值 |")
    print("|------|------|--------|")
    print("| `--tool name=YYYY-MM-DD` | 指定工具名和引入日期 | 可多次使用 |")
    print("| `--days N` | 前后比较窗口天数 | 14 |")
    print("| `--auto-detect` | 从 TOOL_LOG.md 自动检测工具 | — |")
    print()

    # Auto-detect available tools if possible
    tools_found = detect_tools_from_log()
    if tools_found:
        print("## 已检测到的工具 (from TOOL_LOG.md)")
        print()
        print("| 工具名 | 发现日期 | 快速分析命令 |")
        print("|--------|---------|-------------|")
        for name, date_str in tools_found:
            print(f"| {name} | {date_str} | `--tool \"{name}={date_str}\"` |")
        print()
        print("💡 使用 `--auto-detect` 一次性评估以上所有工具。")
    else:
        print("⚠️  未在 TOOL_LOG.md 中发现工具记录。")
        print("   请确保 `tools/TOOL_LOG.md` 存在且包含工具表格。")
        print()


# ============================================================
#  Main
# ============================================================

def main():
    args = parse_args()
    trades = load_all_trades()
    if not trades:
        print("❌ 未找到任何交易数据。", file=sys.stderr)
        sys.exit(1)

    # Determine tool list
    tool_list: list[tuple[str, str]] = []

    if args.tools:
        # Parse --tool name=YYYY-MM-DD
        for t in args.tools:
            parts = t.split("=", 1)
            if len(parts) == 2 and re.match(r"^\d{4}-\d{2}-\d{2}$", parts[1]):
                tool_list.append((parts[0], parts[1]))
            else:
                print(f"⚠️  跳过无效工具参数: {t} (格式: name=YYYY-MM-DD)", file=sys.stderr)

    if args.auto_detect:
        detected = detect_tools_from_log()
        if detected:
            # Merge with any manually specified tools (manually specified take precedence)
            existing_names = {n for n, _ in tool_list}
            for name, date_str in detected:
                if name not in existing_names:
                    tool_list.append((name, date_str))
        else:
            print("⚠️  自动检测未发现任何工具。", file=sys.stderr)

    if not tool_list:
        print_usage_hint()
        sys.exit(0)

    # Sort trades by sell_time
    trades.sort(key=lambda t: t["sell_time"])

    print("# 📊 ZQ 工具效果评估报告")
    print()
    print(f"**报告时间:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"**比较窗口:** {args.days} 天 before/after")
    print(f"**交易样本总数:** {len(trades)}")
    print()

    all_before_trades = []
    all_after_trades = []

    for tool_name, tool_date_str in tool_list:
        tool_dt = datetime.strptime(tool_date_str, "%Y-%m-%d")
        before_start = tool_dt - timedelta(days=args.days)
        after_end = tool_dt + timedelta(days=args.days)

        before_trades = [
            t for t in trades
            if before_start <= t["sell_time"] < tool_dt
        ]
        after_trades = [
            t for t in trades
            if tool_dt <= t["sell_time"] <= after_end
        ]

        all_before_trades.extend(before_trades)
        all_after_trades.extend(after_trades)

        before_metrics = compute_metrics(before_trades)
        after_metrics = compute_metrics(after_trades)
        before_signals = compute_signal_quality(before_trades)
        after_signals = compute_signal_quality(after_trades)

        print("---")
        print()
        print(f"## 🛠️ TOOL_EVAL — {tool_name}")
        print()
        print_tooleval_section(tool_name, tool_date_str, before_metrics, after_metrics)

        # Signal quality comparison
        if before_signals or after_signals:
            all_signals = sorted(set(list(before_signals.keys()) + list(after_signals.keys())))
            print("#### 📡 E系列信号质量对比")
            print()
            print("| 信号 | Before 正确率 | Before 次数 | After 正确率 | After 次数 | Δ |")
            print("|------|--------------|------------|-------------|-----------|-----|")
            for sig in all_signals:
                bs = before_signals.get(sig, {"correct_rate": 0, "total": 0})
                as_ = after_signals.get(sig, {"correct_rate": 0, "total": 0})
                delta = round(as_["correct_rate"] - bs["correct_rate"], 1)
                arrow = "📈" if delta > 0 else "📉" if delta < 0 else "➖"
                print(f"| `{sig}` | {bs['correct_rate']}% (n={bs['total']}) | {as_['correct_rate']}% (n={as_['total']}) | {delta:+0.1f}% {arrow} |")
            print()

        # Conclusion for this tool
        print_conclusion(tool_name, before_metrics, after_metrics, before_signals, after_signals)

    # Aggregated summary across all tools
    if len(tool_list) > 1:
        print("---")
        print()
        print("## 🔄 综合汇总 — 全部工具")
        print()
        all_before_metrics = compute_metrics(all_before_trades)
        all_after_metrics = compute_metrics(all_after_trades)
        print_keymetrics_section(all_before_metrics, all_after_metrics)

        total_before = len(all_before_trades)
        total_after = len(all_after_trades)
        print(f"**合计样本:** Before={total_before} trades, After={total_after} trades")
        print()
        print("| 工具 | 日期 | 总变化评分 | 结论 |")
        print("|------|------|-----------|------|")
        for tool_name, tool_date_str in tool_list:
            tool_dt = datetime.strptime(tool_date_str, "%Y-%m-%d")
            before_t = [t for t in trades if (tool_dt - timedelta(days=args.days)) <= t["sell_time"] < tool_dt]
            after_t = [t for t in trades if tool_dt <= t["sell_time"] <= (tool_dt + timedelta(days=args.days))]
            bm = compute_metrics(before_t)
            am = compute_metrics(after_t)
            b_sig = compute_signal_quality(before_t)
            a_sig = compute_signal_quality(after_t)

            score = 0
            if am["win_rate"] > bm["win_rate"]:
                score += 1
            elif am["win_rate"] < bm["win_rate"]:
                score -= 1
            if am["avg_pnl_pct"] > bm["avg_pnl_pct"]:
                score += 1
            elif am["avg_pnl_pct"] < bm["avg_pnl_pct"]:
                score -= 1
            if am["wrong_exit_pct"] < bm["wrong_exit_pct"]:
                score += 1
            elif am["wrong_exit_pct"] > bm["wrong_exit_pct"]:
                score -= 1

            if score > 0:
                verdict = "✅ 保留"
            elif score == 0:
                verdict = "⏳ 观察"
            else:
                verdict = "⚠️ 调整/替换"

            print(f"| {tool_name} | {tool_date_str} | {score:+d} | {verdict} |")
        print()

    print("---")
    print()
    print("> *报告由 tool_eval.py 自动生成 | 数据源: data/experience/trades/*.json*")


if __name__ == "__main__":
    main()
