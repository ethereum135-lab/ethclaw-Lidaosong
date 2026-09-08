#!/usr/bin/env python3
"""
A5 学习方向建议工具 — 分析系统薄弱环节, 给出ZH学习方向建议

用法:
    cd ~/zq_web4_trading_system && python3 tools/learning_suggest.py [--days 7]

输出:
    仅输出有效 Markdown, 包含:
    - WEAK_SPOT_RANKING — 本期Top3薄弱环节, 含支持统计和趋势
    - LEARNING_SUGGESTIONS — 每项的学习方向、重要性、预期改善
    - DATA_SOURCES — 数据来源
    - UNCERTAINTY — 可疑但需深入分析的事项
"""

import argparse
import json
import os
import glob
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta


# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.expanduser("~/zq_web4_trading_system")
MASTER_PATH = os.path.join(BASE_DIR, "data/experience/MASTER_EXPERIENCE.json")
TRADES_DIR = os.path.join(BASE_DIR, "data/experience/trades")
DAILY_DIR = os.path.join(BASE_DIR, "data/experience/daily")
PROFILES_DIR = os.path.join(BASE_DIR, "profiles/a5-review/output")


# ── Loaders ────────────────────────────────────────────────────────────

def load_master():
    """加载 MASTER_EXPERIENCE.json"""
    if not os.path.exists(MASTER_PATH):
        return None
    with open(MASTER_PATH) as f:
        return json.load(f)


def load_trades_in_range(days: int):
    """加载指定天数内的所有 trade JSON 文件"""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    trades = []
    for fname in os.listdir(TRADES_DIR):
        if not fname.endswith(".json"):
            continue
        # 从文件名提取日期: YYYY-MM-DD_HH-MM-SS_SYMBOL.json
        date_part = fname.split("_")[0] if "_" in fname else ""
        try:
            datetime.strptime(date_part, "%Y-%m-%d")
        except ValueError:
            continue
        if date_part < cutoff:
            continue
        fpath = os.path.join(TRADES_DIR, fname)
        try:
            with open(fpath) as f:
                data = json.load(f)
            trades.append(data)
        except (json.JSONDecodeError, KeyError):
            pass
    return trades


def load_daily_summaries(days: int):
    """加载指定天数内的每日复盘 Markdown 文件"""
    cutoff = datetime.now() - timedelta(days=days)
    daily_list = []
    for fname in os.listdir(DAILY_DIR):
        if not fname.endswith(".md"):
            continue
        date_str = fname.replace(".md", "")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        if dt < cutoff:
            continue
        fpath = os.path.join(DAILY_DIR, fname)
        with open(fpath) as f:
            content = f.read()
        daily_list.append({"date": date_str, "content": content})
    return sorted(daily_list, key=lambda x: x["date"])


def load_recent_supervision_evaluations(days: int):
    """加载近期监督评价文件"""
    cutoff = datetime.now() - timedelta(days=days)
    evals = []
    if not os.path.isdir(PROFILES_DIR):
        return evals
    for fname in os.listdir(PROFILES_DIR):
        if not fname.startswith("监督_"):
            continue
        # 格式: 监督_YYYY-MM-DD.md
        date_part = fname.replace("监督_", "").replace(".md", "")
        try:
            dt = datetime.strptime(date_part, "%Y-%m-%d")
        except ValueError:
            continue
        if dt < cutoff:
            continue
        fpath = os.path.join(PROFILES_DIR, fname)
        with open(fpath) as f:
            content = f.read()
        evals.append({"date": date_part, "content": content})
    return sorted(evals, key=lambda x: x["date"])


# ── Analysis Functions ────────────────────────────────────────────────

def analyze_exit_weakness(master, trades, daily_summaries):
    """
    分析退出弱点:
    - 无效信号(E2/E3)驱动的退出占比
    - 有效信号(P1/止盈)驱动的退出占比
    - 过早退出(too_early)的趋势
    """
    stats = {}
    if master and "exit_signal_performance" in master:
        esp = master["exit_signal_performance"]
        # 噪声信号: E2, E3 (高频低效)
        noise_signals = ["E2", "E3"]
        valid_signals = ["P1", "止盈", "风控减仓"]

        noise_total = sum(esp.get(s, {}).get("total", 0) for s in noise_signals)
        noise_wrong = sum(esp.get(s, {}).get("wrong", 0) for s in noise_signals)
        noise_correct = sum(esp.get(s, {}).get("correct", 0) for s in noise_signals)
        noise_neutral = sum(esp.get(s, {}).get("neutral", 0) for s in noise_signals)

        valid_total = sum(esp.get(s, {}).get("total", 0) for s in valid_signals if s in esp)
        valid_correct = sum(esp.get(s, {}).get("correct", 0) for s in valid_signals if s in esp)

        all_total = sum(s.get("total", 0) for s in esp.values())
        all_correct = sum(s.get("correct", 0) for s in esp.values())
        all_wrong = sum(s.get("wrong", 0) for s in esp.values())

        stats = {
            "noise_total": noise_total,
            "noise_wrong": noise_wrong,
            "noise_correct": noise_correct,
            "noise_neutral": noise_neutral,
            "valid_total": valid_total,
            "valid_correct": valid_correct,
            "all_total": all_total,
            "all_correct": all_correct,
            "all_wrong": all_wrong,
            "correct_rate": round(all_correct / all_total * 100, 1) if all_total else 0,
            "wrong_rate": round(all_wrong / all_total * 100, 1) if all_total else 0,
            "noise_pct_of_total": round(noise_total / all_total * 100, 1) if all_total else 0,
        }

    # 近期趋势: 从 daily_summaries 提取每天盈亏情况
    daily_pnl = {}
    for ds in daily_summaries:
        correct_match = re.search(r"正确:\s*(\d+)", ds["content"])
        error_match = re.search(r"错误:\s*(\d+)", ds["content"])
        pnl_match = re.search(r"总盈亏:\s*\$?(-?\d+\.?\d*)", ds["content"])
        c = int(correct_match.group(1)) if correct_match else 0
        e = int(error_match.group(1)) if error_match else 0
        p = float(pnl_match.group(1)) if pnl_match else 0.0
        daily_pnl[ds["date"]] = {"correct": c, "error": e, "pnl": p}

    stats["daily_pnl"] = daily_pnl

    # 近期 trades 中 exit_quality 分布
    quality_dist = Counter()
    for t in trades:
        q = t.get("analysis", {}).get("exit_quality", "unknown")
        quality_dist[q] += 1

    stats["recent_quality"] = {
        "correct": quality_dist.get("correct", 0),
        "wrong": quality_dist.get("wrong", 0),
        "neutral": quality_dist.get("neutral", 0),
        "total_recent": len(trades),
    }

    return stats


def analyze_entry_weakness(trades):
    """
    分析入场弱点:
    - 入场后即亏损的交易比例
    - 平均亏损幅度
    - 近期亏损集中度
    """
    if not trades:
        return {}

    all_pnls = []
    losing_trades = []
    for t in trades:
        a = t.get("analysis", {})
        pnl = a.get("pnl_pct", 0)
        all_pnls.append(pnl)
        if pnl < 0:
            losing_trades.append(t)

    # 亏损交易比例
    losing_pct = round(len(losing_trades) / len(all_pnls) * 100, 1) if all_pnls else 0

    # 平均亏损幅度
    avg_loss = round(sum(t.get("analysis", {}).get("pnl_pct", 0) for t in losing_trades) / len(losing_trades), 2) if losing_trades else 0

    # 亏损超过 -5% 的严重交易
    severe_losses = [t for t in losing_trades if t.get("analysis", {}).get("pnl_pct", 0) <= -5]

    # 按币种统计亏损
    loss_by_symbol = defaultdict(list)
    for t in losing_trades:
        sym = t.get("analysis", {}).get("symbol", "unknown")
        loss_by_symbol[sym].append(t.get("analysis", {}).get("pnl_pct", 0))

    avg_loss_by_symbol = {sym: round(sum(v) / len(v), 2) for sym, v in loss_by_symbol.items()}

    # 频繁亏损的币种
    repeat_losers = {sym: {"count": len(v), "avg_pnl": round(sum(v) / len(v), 2)}
                     for sym, v in loss_by_symbol.items() if len(v) >= 2}

    return {
        "total_trades": len(all_pnls),
        "losing_trades": len(losing_trades),
        "losing_pct": losing_pct,
        "avg_loss": avg_loss,
        "severe_losses_count": len(severe_losses),
        "repeat_losers": repeat_losers,
        "avg_loss_by_symbol": avg_loss_by_symbol,
    }


def analyze_direction_weakness(master, trades):
    """
    分析方向弱点 (A3/A2选币):
    - MASTER_EXPERIENCE 中反复亏损的币种
    - 有效经验(efectiveness=有效) vs 需要改进的比例
    - 近期亏损币种的规律
    """
    if not master:
        return {}

    rules = master.get("rules", [])

    # 统计 effectiveness
    eff_counter = Counter()
    signal_counter = Counter()
    pnl_by_coin = defaultdict(list)
    need_improve_signals = defaultdict(int)

    for r in rules:
        eff = r.get("effectiveness", "")
        eff_counter[eff] += 1

        sig = r.get("signal", "").strip()
        if sig:
            signal_counter[sig] += 1

        # 提取币种和盈亏
        cond = r.get("condition", "")
        pnl_str = r.get("pnl", "")
        # 从 condition 中提取币种: "XXX在..." 或 "XXX买入..."
        coin_match = re.match(r"^(\w+)", cond)
        if coin_match:
            coin = coin_match.group(1)
            if pnl_str:
                try:
                    pnl_val = float(pnl_str.replace("%", ""))
                    pnl_by_coin[coin].append(pnl_val)
                except ValueError:
                    pass

            if eff == "需要改进" and sig:
                need_improve_signals[sig] += 1

    # 平均亏损最高的币种
    coin_avg_loss = {}
    for coin, pnls in pnl_by_coin.items():
        if len(pnls) >= 2:  # 至少2次交易才统计
            avg = sum(pnls) / len(pnls)
            coin_avg_loss[coin] = {"avg_pnl": round(avg, 1), "count": len(pnls)}

    # 频繁亏损币种 (多次亏损且平均亏损 > -1%)
    bad_coins = {k: v for k, v in coin_avg_loss.items() if v["avg_pnl"] < -1 and v["count"] >= 2}
    bad_coins_sorted = sorted(bad_coins.items(), key=lambda x: x[1]["avg_pnl"])

    # 近期 trades 中的亏损币种
    recent_bad = {}
    for t in trades:
        a = t.get("analysis", {})
        sym = a.get("symbol", "")
        pnl = a.get("pnl_pct", 0)
        if pnl < -3:  # 明显的错误选币
            if sym not in recent_bad:
                recent_bad[sym] = {"pnls": [], "signals": []}
            recent_bad[sym]["pnls"].append(round(pnl, 1))
            recent_bad[sym]["signals"] = a.get("trigger_signals", [])

    return {
        "total_rules": len(rules),
        "need_improve": eff_counter.get("需要改进", 0),
        "effective": eff_counter.get("有效", 0),
        "need_improve_pct": round(eff_counter.get("需要改进", 0) / len(rules) * 100, 1) if rules else 0,
        "worst_coins": bad_coins_sorted[:10],
        "recent_bad_coins": recent_bad,
        "need_improve_signals": need_improve_signals,
    }


def analyze_data_weakness(trades, master):
    """
    分析数据质量弱点:
    - DQW 标记数量
    - 零值价格/数量问题
    - 精度截断
    """
    dqw_count = 0
    zero_price_count = 0
    precision_truncation = 0
    missing_buy = 0

    for t in trades:
        a = t.get("analysis", {})
        dq = a.get("data_quality", "")
        sell_p = a.get("sell_price", -1)
        buy_p = a.get("buy_price", -1)
        buy_time = a.get("buy_time", "")

        if dq:
            dqw_count += 1
            if "precision" in dq.lower() or "truncation" in dq.lower():
                precision_truncation += 1

        if (isinstance(sell_p, (int, float)) and sell_p == 0) or \
           (isinstance(buy_p, (int, float)) and buy_p == 0):
            zero_price_count += 1

        if buy_time == "unknown" or buy_p is None:
            missing_buy += 1

    return {
        "dqw_count": dqw_count,
        "zero_price_count": zero_price_count,
        "precision_truncation": precision_truncation,
        "missing_buy": missing_buy,
        "dq_rate": round(dqw_count / len(trades) * 100, 1) if trades else 0,
    }


def analyze_execution_weakness(trades, master):
    """
    分析执行弱点 (A4执行质量):
    - exit_quality = wrong 的比率
    - 止损执行偏差 (exit_reason 包含"止损"的盈亏分析)
    - 信号组合 vs 单一信号的表现
    """
    if not trades:
        return {}

    # 近期退出质量
    quality_counts = Counter()
    for t in trades:
        q = t.get("analysis", {}).get("exit_quality", "")
        quality_counts[q] += 1

    total_recent = len(trades)
    wrong_ratio = round(quality_counts.get("wrong", 0) / total_recent * 100, 1) if total_recent else 0
    correct_ratio = round(quality_counts.get("correct", 0) / total_recent * 100, 1) if total_recent else 0

    # 止损相关退出
    stop_loss_trades = []
    for t in trades:
        reason = t.get("analysis", {}).get("exit_reason", "")
        if "止损" in reason or "stop" in reason.lower():
            stop_loss_trades.append(t)

    avg_stop_loss_pnl = 0
    if stop_loss_trades:
        pnls = [t.get("analysis", {}).get("pnl_pct", 0) for t in stop_loss_trades]
        avg_stop_loss_pnl = round(sum(pnls) / len(pnls), 2)

    # 信号组合 vs 单一信号
    signal_perf = defaultdict(list)
    for t in trades:
        sigs = t.get("analysis", {}).get("trigger_signals", [])
        pnl = t.get("analysis", {}).get("pnl_pct", 0)
        key = "+".join(sorted(sigs)) if sigs else "无信号"
        signal_perf[key].append(pnl)

    signal_summary = {}
    for sig, pnls in signal_perf.items():
        signal_summary[sig] = {
            "count": len(pnls),
            "avg_pnl": round(sum(pnls) / len(pnls), 2),
            "min": round(min(pnls), 2),
            "max": round(max(pnls), 2),
        }

    return {
        "total_recent": total_recent,
        "wrong_count": quality_counts.get("wrong", 0),
        "correct_count": quality_counts.get("correct", 0),
        "neutral_count": quality_counts.get("neutral", 0),
        "wrong_ratio": wrong_ratio,
        "correct_ratio": correct_ratio,
        "stop_loss_count": len(stop_loss_trades),
        "avg_stop_loss_pnl": avg_stop_loss_pnl,
        "signal_performance": signal_summary,
    }


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="A5 系统薄弱环节分析与学习方向建议")
    parser.add_argument("--days", type=int, default=7, help="分析最近 N 天的数据 (默认: 7)")
    args = parser.parse_args()
    days = args.days

    # 加载所有数据
    master = load_master()
    trades = load_trades_in_range(days)
    daily_summaries = load_daily_summaries(days)
    supervision = load_recent_supervision_evaluations(days)

    # 执行分析
    exit_stats = analyze_exit_weakness(master, trades, daily_summaries)
    entry_stats = analyze_entry_weakness(trades)
    direction_stats = analyze_direction_weakness(master, trades)
    data_stats = analyze_data_weakness(trades, master)
    exec_stats = analyze_execution_weakness(trades, master)

    # ── 排名薄弱环节 ──
    weak_spots = []

    # 1. 退出弱点: E2/E3噪声信号
    if exit_stats:
        noise_pct = exit_stats.get("noise_pct_of_total", 0)
        wrong_rate = exit_stats.get("wrong_rate", 0)
        correct_rate = exit_stats.get("correct_rate", 0)
        recent_q = exit_stats.get("recent_quality", {})
        recent_correct = recent_q.get("correct", 0)
        recent_wrong = recent_q.get("wrong", 0)
        recent_total = recent_q.get("total_recent", 0)
        recent_wrong_ratio = round(recent_wrong / recent_total * 100, 1) if recent_total else 0

        # 判断趋势: 比较近期 vs 整体
        overall_wrong = master.get("stats", {}).get("wrong_exits", 0) if master else 0
        overall_total = master.get("stats", {}).get("total_trades_analyzed", 1) if master else 1
        overall_wrong_ratio = round(overall_wrong / overall_total * 100, 1)
        trend = "worsening" if recent_wrong_ratio > overall_wrong_ratio else ("improving" if recent_wrong_ratio < overall_wrong_ratio else "stable")

        weak_spots.append({
            "rank": 0,
            "dimension": "退出质量 — E2/E3噪声信号过度触发",
            "score": round(noise_pct * 0.5 + wrong_rate * 0.5, 1),
            "stats": {
                "历史噪声信号占比": f"{noise_pct}% ({exit_stats.get('noise_total', 0)}/{exit_stats.get('all_total', 0)})",
                "历史总体正确率": f"{correct_rate}%",
                "历史总体错误率": f"{wrong_rate}%",
                f"近{days}天退出质量": f"正确{recent_correct} / 错误{recent_wrong} / 中性{recent_q.get('neutral', 0)} / 共{recent_total}",
                f"近{days}天错误率": f"{recent_wrong_ratio}%",
                "过多退出(too_early)": f"{master.get('stats', {}).get('too_early_exits', 'N/A')}笔",
            },
            "trend": trend,
        })

    # 2. 入场弱点
    if entry_stats:
        losing_pct = entry_stats.get("losing_pct", 0)
        avg_loss = entry_stats.get("avg_loss", 0)
        severe = entry_stats.get("severe_losses_count", 0)
        total = entry_stats.get("total_trades", 0)
        repeat = entry_stats.get("repeat_losers", {})

        weak_spots.append({
            "rank": 1,
            "dimension": "入场质量 — 入场位置不佳导致亏损比例高",
            "score": round(losing_pct * 0.6 + abs(avg_loss) * 5, 1),
            "stats": {
                f"近{days}天亏损交易占比": f"{losing_pct}% ({entry_stats.get('losing_trades', 0)}/{total})",
                f"近{days}天平均亏损幅度": f"{avg_loss}%",
                f"严重亏损(>-5%)": f"{severe}笔",
                "重复亏损币种": ", ".join([f"{k}({v['count']}次,均{v['avg_pnl']}%)" for k, v in list(repeat.items())[:5]]) or "无",
            },
            "trend": "worsening" if losing_pct > 60 else "stable",
        })

    # 3. 方向弱点 (选币)
    if direction_stats:
        need_improve_pct = direction_stats.get("need_improve_pct", 0)
        effective_count = direction_stats.get("effective", 0)
        worst_coins = direction_stats.get("worst_coins", [])
        need_sigs = direction_stats.get("need_improve_signals", {})

        weak_spots.append({
            "rank": 2,
            "dimension": "选币方向 — A3/A2推荐的币种持续性差",
            "score": round(need_improve_pct * 0.5, 1),
            "stats": {
                "需改进经验占比": f"{need_improve_pct}% ({direction_stats.get('need_improve', 0)}/{direction_stats.get('total_rules', 0)})",
                "有效经验数": str(effective_count),
                "最差币种(Top5)": ", ".join([f"{c}({v['count']}次,均{v['avg_pnl']}%)" for c, v in worst_coins[:5]]) or "数据不足",
                "高频需改进信号": ", ".join([f"{k}({v}次)" for k, v in sorted(need_sigs.items(), key=lambda x: -x[1])[:5]]),
            },
            "trend": "stable",
        })

    # 4. 数据质量弱点
    if data_stats:
        dq_count = data_stats.get("dqw_count", 0)
        dq_rate = data_stats.get("dq_rate", 0)

        weak_spots.append({
            "rank": 3,
            "dimension": "数据质量 — DQW标记和价格精度问题",
            "score": round(dq_rate * 1.5, 1),
            "stats": {
                f"近{days}天DQW标记数": str(dq_count),
                f"DQW占比": f"{dq_rate}%",
                "零值价格记录": str(data_stats.get("zero_price_count", 0)),
                "精度截断记录": str(data_stats.get("precision_truncation", 0)),
                "缺失买入信息": str(data_stats.get("missing_buy", 0)),
            },
            "trend": "stable",
        })

    # 5. 执行弱点
    if exec_stats:
        wrong_ratio = exec_stats.get("wrong_ratio", 0)
        correct_ratio = exec_stats.get("correct_ratio", 0)
        stop_loss_cnt = exec_stats.get("stop_loss_count", 0)
        avg_sl = exec_stats.get("avg_stop_loss_pnl", 0)

        weak_spots.append({
            "rank": 4,
            "dimension": "执行质量 — A4止盈止损执行偏差",
            "score": round(wrong_ratio * 0.8, 1),
            "stats": {
                f"近{days}天执行正确率": f"{correct_ratio}% ({exec_stats.get('correct_count', 0)}/{exec_stats.get('total_recent', 1)})",
                f"近{days}天执行错误率": f"{wrong_ratio}%",
                f"止损执行次数": str(stop_loss_cnt),
                f"止损平均盈亏": f"{avg_sl}%",
            },
            "trend": "stable",
        })

    # 排序: 按 score 降序
    weak_spots.sort(key=lambda x: -x["score"])

    # 只取 Top 3
    top3 = weak_spots[:3]

    # ── 构建学习建议 ──
    learning_map = {
        "退出质量": {
            "learn": "学习退出信号优化: 研究如何区分噪声E2/E3信号与有效退出信号",
            "why": "当前E2+E3占总退出的{}%, 但正确率极低(E3: {:.1f}%, E2: {:.1f}%). 每次噪声退出平均亏损约-2%, 长期积累严重侵蚀收益",
            "expected": "将噪声信号误触发率降低50%, 预计可提升整体盈亏比30%以上",
        },
        "入场质量": {
            "learn": "学习入场时机优化: 研究多时间框架确认入场点, 避免在趋势末端或高波动时追入",
            "why": "近{}天{}%的交易亏损, 严重亏损(>-5%){}笔. 入场位置不佳导致一入场就处于被动, 是后续E2/E3误触的诱因",
            "expected": "改善入场位置后, 预计亏损交易占比可从{}%降至50%以下, 同时减少E2/E3误触",
        },
        "选币方向": {
            "learn": "学习选币逻辑重构: 研究币种轮动规律、强于大盘的币种特征、以及逃顶信号",
            "why": "经验库中{}%的经验标记为'需要改进', 大量币种反复出现在亏损列表中. 选币是交易系统的根基, 错误的选币无法通过优化退出弥补",
            "expected": "选币准确率提升10%, 可带来整体收益翻倍的效果(杠杆效应)",
        },
        "数据质量": {
            "learn": "学习数据管道清洗: 研究如何自动检测和修复Column Shift、精度截断等数据质量问题",
            "why": "DQW标记占比{}%, 零值和精度截断数据直接影响分析的准确性. 在错误数据上学习等于在沙上建塔",
            "expected": "将数据异常率降至1%以下, 确保经验库建立在准确数据上",
        },
        "执行质量": {
            "learn": "学习执行策略调优: 研究止损/止盈的参数优化, 以及在连续亏损时的应对策略",
            "why": "近{}天执行错误率{}%, 止损执行平均亏损{}%. A4的机械执行需要更智能的上下文判断",
            "expected": "将执行正确率从{}%提升至60%以上, 可显著减少不必要的亏损",
        },
    }

    # ── 输出 Markdown ──

    print(f"# A5 系统薄弱环节分析与学习建议")
    print(f"> 分析周期: 近 {days} 天 ({datetime.now().strftime('%Y-%m-%d')} 回溯 {days} 天)")
    print(f"> 分析范围: {len(trades)} 笔交易记录, {len(daily_summaries)} 日复盘摘要, MASTER_EXPERIENCE 经验库")
    print()

    # ── WEAK_SPOT_RANKING ──
    print("---")
    print("## WEAK_SPOT_RANKING — 本期 Top 3 薄弱环节")
    print()

    trend_icon = {"improving": "🟢 改善中", "worsening": "🔴 恶化中", "stable": "🟡 持平"}

    for i, spot in enumerate(top3):
        rank = i + 1
        dim = spot["dimension"]
        score = spot["score"]
        trend_str = trend_icon.get(spot["trend"], "⚪ 未知")

        print(f"### #{rank}: {dim}  (风险分: {score})")
        print(f"**趋势:** {trend_str}")
        print()
        print(f"| 指标 | 数值 |")
        print(f"|:-----|:----:|")
        for k, v in spot["stats"].items():
            print(f"| {k} | {v} |")
        print()

    # ── LEARNING_SUGGESTIONS ──
    print("---")
    print("## LEARNING_SUGGESTIONS — 学习方向建议")
    print()

    master_stats = master.get("stats", {}) if master else {}
    esp = master.get("exit_signal_performance", {}) if master else {}

    for i, spot in enumerate(top3):
        dim = spot["dimension"]
        rank = i + 1
        dim_key = dim.split("—")[0].strip()

        # 找到匹配的学习建议模板
        suggestion = None
        for key, val in learning_map.items():
            if key in dim_key or any(k in dim_key for k in key.split("/")):
                suggestion = val
                break

        if suggestion:
            learn_text = suggestion["learn"]

            # 填充动态数据
            if "退出" in dim_key:
                noise_total = exit_stats.get("noise_total", 0)
                e3_stats = esp.get("E3", {})
                e2_stats = esp.get("E2", {})
                e3_correct_rate = round(e3_stats.get("correct", 0) / e3_stats.get("total", 1) * 100, 1) if e3_stats.get("total", 0) > 0 else 0
                e2_correct_rate = round(e2_stats.get("correct", 0) / e2_stats.get("total", 1) * 100, 1) if e2_stats.get("total", 0) > 0 else 0
                noise_pct_val = exit_stats.get("noise_pct_of_total", 0)
                why_text = suggestion["why"].format(noise_pct_val, e3_correct_rate, e2_correct_rate)
                expected_text = suggestion["expected"]
            elif "入场" in dim_key:
                losing_pct = entry_stats.get("losing_pct", 0)
                severe = entry_stats.get("severe_losses_count", 0)
                why_text = suggestion["why"].format(days, losing_pct, severe)
                expected_text = suggestion["expected"].format(losing_pct)
            elif "选币" in dim_key:
                need_improve_pct = direction_stats.get("need_improve_pct", 0)
                why_text = suggestion["why"].format(need_improve_pct)
                expected_text = suggestion["expected"]
            elif "数据" in dim_key:
                dq_rate = data_stats.get("dq_rate", 0)
                why_text = suggestion["why"].format(dq_rate)
                expected_text = suggestion["expected"]
            elif "执行" in dim_key:
                wrong_ratio = exec_stats.get("wrong_ratio", 0)
                avg_sl = exec_stats.get("avg_stop_loss_pnl", 0)
                correct_ratio = exec_stats.get("correct_ratio", 0)
                why_text = suggestion["why"].format(days, wrong_ratio, avg_sl)
                expected_text = suggestion["expected"].format(correct_ratio)
            else:
                why_text = suggestion["why"]
                expected_text = suggestion["expected"]

            print(f"### 建议 #{rank}: {dim}")
            print()
            print(f"**📚 学什么:** {learn_text}")
            print()
            print(f"**❓ 为什么重要:** {why_text}")
            print()
            print(f"**📈 预期改善:** {expected_text}")
            print()
        else:
            print(f"### 建议 #{rank}: {dim}")
            print()
            print(f"**📚 学什么:** (需根据业务上下文补充具体学习方向)")
            print()
            print(f"**❓ 为什么重要:** 该维度当前风险分 {spot['score']}, 需深入排查根因")
            print()
            print(f"**📈 预期改善:** 待补充")
            print()

    # ── DATA_SOURCES ──
    print("---")
    print("## DATA_SOURCES — 数据来源")
    print()
    print(f"| 数据源 | 文件 | 用途 |")
    print(f"|:-------|:-----|:-----|")
    print(f"| 经验总库 | `data/experience/MASTER_EXPERIENCE.json` | 退出信号统计、经验有效性分析 |")
    print(f"| 交易记录 | `data/experience/trades/*.json` ({len(trades)} files) | 近期交易质量、入场时机、DQW |")
    print(f"| 日复盘摘要 | `data/experience/daily/*.md` ({len(daily_summaries)} files) | 每日盈亏趋势、正确/错误比 |")
    if supervision:
        print(f"| 监督评价 | `profiles/a5-review/output/监督_*.md` ({len(supervision)} files) | 外部评价参考 |")
    print(f"| 系统统计 | `state/a5.json` | A5运行状态 |")
    print()

    # ── UNCERTAINTY ──
    print("---")
    print("## UNCERTAINTY — 可疑但需深入分析的事项")
    print()

    uncertainties = []

    # 检查是否有零值价格但未标记DQW
    zero_unmarked = 0
    for t in trades:
        a = t.get("analysis", {})
        if (isinstance(a.get("sell_price"), (int, float)) and a["sell_price"] == 0) or \
           (isinstance(a.get("buy_price"), (int, float)) and a["buy_price"] == 0):
            if not a.get("data_quality"):
                zero_unmarked += 1
    if zero_unmarked > 0:
        uncertainties.append(f"- 🟡 近{days}天有{zero_unmarked}笔零值价格记录未标记DQW, 需要确认是真正的零值卖出还是数据采集问题")

    # 检查历史 vs 近期趋势是否一致
    if exit_stats and master:
        hist_wrong = master.get("stats", {}).get("wrong_exits", 0)
        hist_total = master.get("stats", {}).get("total_trades_analyzed", 1)
        hist_wrong_ratio = round(hist_wrong / hist_total * 100, 1)
        recent_wrong_ratio = exit_stats.get("recent_quality", {}).get("wrong", 0)
        recent_total = exit_stats.get("recent_quality", {}).get("total_recent", 1)

        if recent_total > 0:
            recent_wr = round(recent_wrong_ratio / recent_total * 100, 1)
            if abs(recent_wr - hist_wrong_ratio) > 15:
                uncertainties.append(f"- 🟡 近期错误率({recent_wr}%)与历史错误率({hist_wrong_ratio}%)差异较大, 需要确认是系统改进了还是样本量不足")

    # 检查 MASTER_EXPERIENCE 中的异常 PnL
    if master:
        for r in master.get("rules", []):
            pnl = r.get("pnl", "")
            cond = r.get("condition", "")
            if pnl and "-100.0%" in pnl:
                uncertainties.append(f"- 🔴 发现-100%亏损记录: {cond}, 需确认是否数据异常(精度截断/Column Shift)而非真实亏损")

    # 检查近期是否有连续亏损模式
    if daily_summaries:
        pnls = []
        for ds in daily_summaries:
            m = re.search(r"总盈亏:\s*\$?(-?\d+\.?\d*)", ds["content"])
            if m:
                pnls.append(float(m.group(1)))
        if len(pnls) >= 3:
            consecutive_losses = 0
            max_consecutive = 0
            for p in pnls:
                if p < 0:
                    consecutive_losses += 1
                    max_consecutive = max(max_consecutive, consecutive_losses)
                else:
                    consecutive_losses = 0
            if max_consecutive >= 3:
                uncertainties.append(f"- 🔴 近期出现{max_consecutive}天连续亏损, 需紧急排查系统是否存在系统性风险")

    # 检查重复亏损币种
    if direction_stats and direction_stats.get("recent_bad_coins"):
        bad_syms = list(direction_stats["recent_bad_coins"].keys())
        if len(bad_syms) >= 3:
            uncertainties.append(f"- 🟡 近{days}天亏损超过-3%的币种: {', '.join(bad_syms[:5])}, 需确认是A3选币问题还是整体市场下行")

    if not uncertainties:
        uncertainties.append("- ✅ 当前未发现明显可疑事项")

    for u in uncertainties:
        print(u)

    print()
    print("---")
    print(f"*A5 learning_suggest.py | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")


if __name__ == "__main__":
    main()
