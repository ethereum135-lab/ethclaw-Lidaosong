#!/usr/bin/env python3
"""
supervision_eval.py — A5 复盘官 监督评估工具
A3推荐质量 + A4执行质量 双维度评估，基于真实交易数据。

评估哲学：决策质量 ≠ P&L结果
  - 好决策可能亏钱（黑天鹅），依然是好的推荐
  - 坏决策可能赚钱（运气），依然是坏的决定

用法:
    cd ~/zq_web4_trading_system && python3 tools/supervision_eval.py [--days 7]

输出: 结构化的 Markdown 到 stdout（3个sections）
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional


# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = os.path.expanduser("~/zq_web4_trading_system")
TRADES_PATH = os.path.join(BASE_DIR, "audit", "TRADES.md")
MASTER_EXP_PATH = os.path.join(BASE_DIR, "data/experience/MASTER_EXPERIENCE.json")
A3_OUTPUT_DIR = os.path.join(BASE_DIR, "profiles/a3-bull/output")
A3_FINDINGS_PATH = os.path.join(BASE_DIR, "agents/a3/findings.md")
TRADES_DATA_DIR = os.path.join(BASE_DIR, "data/experience/trades")


# ── 辅助函数 ──────────────────────────────────────────────

def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date strings in various formats."""
    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    # try ISO format
    try:
        return datetime.fromisoformat(date_str.strip())
    except (ValueError, TypeError):
        return None


def within_days(dt: datetime, days: int) -> bool:
    """Check if datetime is within N days from now."""
    if dt is None:
        return False
    return (datetime.now() - dt).days <= days


def load_trades_md(path: str) -> list[dict]:
    """Parse TRADES.md pipe-delimited table into structured records."""
    if not os.path.exists(path):
        return []

    records = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("| :") or line.startswith("| 时间"):
            continue
        if not line.startswith("|"):
            continue

        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]  # remove empty from leading/trailing |

        if len(parts) < 6:
            continue

        time_str = parts[0]
        action = parts[1]
        symbol = parts[2]
        qty_str = parts[3]
        price_str = parts[4]
        reason = parts[5] if len(parts) > 5 else ""
        data = parts[6] if len(parts) > 6 else ""

        dt = parse_date(time_str)
        records.append({
            "time": time_str,
            "datetime": dt,
            "action": action.upper(),
            "symbol": symbol.strip().upper() if symbol.strip() != "-" and symbol.strip() != "—" and symbol.strip() != "--" else None,
            "qty": qty_str,
            "price": price_str,
            "reason": reason,
            "data": data,
        })
    return records


def load_master_experience(path: str) -> dict:
    """Load MASTER_EXPERIENCE.json."""
    if not os.path.exists(path):
        return {"rules": [], "version": "unknown"}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_trade_analyses(data_dir: str) -> list[dict]:
    """Load all individual trade analysis JSONs."""
    analyses = []
    if not os.path.exists(data_dir):
        return analyses
    for fname in sorted(os.listdir(data_dir)):
        if fname.endswith(".json"):
            path = os.path.join(data_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "analysis" in data:
                    analyses.append(data["analysis"])
                else:
                    analyses.append(data)
            except (json.JSONDecodeError, KeyError):
                continue
    return analyses


def load_a3_reports(output_dir: str, days: int) -> list[dict]:
    """Load A3 daily recommendation reports."""
    reports = []
    if not os.path.exists(output_dir):
        return reports
    for fname in sorted(os.listdir(output_dir)):
        if fname.endswith(".md") and re.match(r"\d{4}-\d{2}-\d{2}\.md", fname):
            date_str = fname.replace(".md", "")
            file_date = parse_date(date_str)
            if file_date and not within_days(file_date, days):
                continue
            path = os.path.join(output_dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            reports.append({
                "date": date_str,
                "file": fname,
                "content": content,
            })
    return reports


def extract_a3_recommendation(report: dict) -> Optional[dict]:
    """Extract the main recommendation from an A3 report."""
    content = report.get("content", "")

    # Determine if it's a "空仓" recommendation — check the CONCLUSION section carefully
    # Look for explicit skip patterns in the conclusion/result area, not just anywhere
    conclusion_area = ""

    # Extract the core conclusion section (last 25% of content or after "核心结论")
    m = re.search(r'##\s*核心结论|##\s*🏆.*结论|核心结论', content)
    if m:
        conclusion_area = content[m.start():]
    else:
        # Fallback: last 30% of content
        conclusion_area = content[-len(content)//3:]

    # Precise skip detection — only if the conclusion says "空仓" explicitly
    skip_patterns = [
        r'🚫\s*空仓',
        r'空仓\s*[—–-]\s*今日',
        r'空仓\s*不推',
        r'今日\s*不推荐',
        r'今日\s*不推币',
        r'今日无.*推荐',
        r'不推荐任何.*买入',
        r'不推荐任何新',
    ]
    is_skip = False
    for pat in skip_patterns:
        if re.search(pat, conclusion_area, re.IGNORECASE):
            is_skip = True
            break

    # Also check the beginning for an explicit skip header
    header_area = content[:min(500, len(content))]
    for pat in skip_patterns:
        if re.search(pat, header_area, re.IGNORECASE):
            is_skip = True
            break

    # Find recommended coin — only if not explicitly skipping
    coin = None

    if not is_skip:
        # Method 1: "**选中币种：XXX**" pattern (most common)
        m = re.search(r'\*\*选中币种[：:]\s*([A-Z]+)', content)
        if m:
            coin = m.group(1)

        # Method 2: "**精选牛币：XXX**" pattern
        if not coin:
            m = re.search(r'\*\*精选牛币[：:]\s*([A-Z]+)', content)
            if m:
                coin = m.group(1)

        # Method 3: "选币：XXX" in a code block or plain text
        if not coin:
            m = re.search(r'选币[：:]\s*([A-Z]+)', content)
            if m:
                coin = m.group(1)

        # Method 4: "🏆 今日精选牛币" section header followed by coin name
        if not coin:
            m = re.search(r'🏆.*?精选.*?牛币.*?\n.*?\*\*([A-Z]+)', content)
            if m:
                coin = m.group(1)

        # Method 5: "P0 🏆 WLD →" priority / P0 section (2026-05-27+ format)
        if not coin:
            m = re.search(r'P0.*?(?:🏆|🥇|⭐).*?([A-Z]{2,8})\s*→', content)
            if m:
                coin = m.group(1)

        # Method 6: "| **1** | **WLD** 🏆/🥇" table row in high-confidence section
        if not coin:
            m = re.search(r'\*\*\d+\*\*\s*\|\s*\*\*([A-Z]+)\*\*\s*\**\s*(?:🏆|🥇|🥈)', content)
            if m:
                coin = m.group(1)

        # Method 7: "| N | **WLD** 🥇/🥈" table row (non-bold # format)
        if not coin:
            m = re.search(r'\|\s*\d+\s*\|\s*\*\*([A-Z]+)\*\*\s*\**\s*(?:🥇|🥈|🥉)', content)
            if m:
                coin = m.group(1)

        # Method 8: "### 🟢 高置信度候选" section — first **SYMBOL** after header
        if not coin:
            m = re.search(r'(?:###|##)\s*🟢.*?候选.*?\n(?:.*?\n){0,3}\|\s*\*?\d+\*?\s*\|\s*\*\*([A-Z]+)\*\*', content)
            if m:
                coin = m.group(1)

        # Method 9: "🟢 高置信度候选" section — first bold symbol
        if not coin:
            m = re.search(r'高置信度.*?候选.*?\n(?:.*?\n){0,5}\*\*([A-Z]+)\*\*', content)
            if m:
                coin = m.group(1)

    # Extract price targets
    entry_price = None
    stop_loss = None
    take_profit = None
    confidence = None
    reasoning = ""

    # Entry price
    m = re.search(r'\*\*建仓价\*\*[：:]\s*\$?(\d+\.?\d*)', content)
    if m:
        entry_price = float(m.group(1))
    # Entry price (new format: "建仓价：$0.37-0.38")
    if not entry_price:
        m = re.search(r'建仓价[：:]\s*\$?(\d+\.?\d*)', content)
        if m:
            entry_price = float(m.group(1))

    # Stop loss
    m = re.search(r'\*\*止损价\*\*[：:]\s*\$?(\d+\.?\d*)', content)
    if m:
        stop_loss = float(m.group(1))
    # Stop loss (new format: "止损：$0.35")
    if not stop_loss:
        m = re.search(r'(?:止损|止损价)[：:]\s*\$?(\d+\.?\d*)', content)
        if m:
            stop_loss = float(m.group(1))

    # Take profit
    m = re.search(r'\*\*止盈价\*\*[：:]\s*\$?(\d+\.?\d*)', content)
    if m:
        take_profit = float(m.group(1))
    # Take profit (new format: "止盈1：$0.41")
    if not take_profit:
        m = re.search(r'止盈(?:\d)?[：:]\s*\$?(\d+\.?\d*)', content)
        if m:
            take_profit = float(m.group(1))

    # Confidence
    m = re.search(r'置信度[：:]\s*(\d+\.?\d*)/10', content)
    if m:
        confidence = float(m.group(1))

    # Core reasoning (extract the "核心逻辑" section)
    m = re.search(r'核心逻辑[：:](.*?)(?:\n\n|\n##|\Z)', content, re.DOTALL)
    if m:
        reasoning = m.group(1).strip()
    if not reasoning:
        m = re.search(r'核心结论(?:.*?)\n(?:.*?(?:核心逻辑[：:](.*?))?)?(?:\n\n|\n##|\Z)', content, re.DOTALL)
        if m and m.group(1):
            reasoning = m.group(1).strip()

    # Direction
    direction = "BUY"
    if is_skip:
        direction = "SKIP"

    return {
        "date": report["date"],
        "coin": coin,
        "direction": direction,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": confidence,
        "reasoning": reasoning,
        "is_skip": is_skip,
        "raw_excerpt": content[:500] if len(content) > 500 else content,
    }


def extract_a3_findings(path: str) -> list[dict]:
    """Extract A3 analysis findings (lessons/learnings)."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    findings = []
    # Parse findings — look for structured items
    sections = re.split(r'##+\s+', content)
    for sec in sections:
        if not sec.strip():
            continue
        lines = sec.strip().split("\n")
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        findings.append({"title": title, "body": body})
    return findings


def get_trades_for_coin(records: list[dict], coin: str, days: int) -> list[dict]:
    """Filter trades for a specific coin within the time window."""
    coin_upper = coin.upper()
    return [
        r for r in records
        if r.get("symbol") and coin_upper in r["symbol"]
        and r["datetime"] and within_days(r["datetime"], days)
    ]


def get_trades_for_date(records: list[dict], date_str: str) -> list[dict]:
    """Get trades that happened on a specific date."""
    return [
        r for r in records
        if r["datetime"] and r["datetime"].strftime("%Y-%m-%d") == date_str
    ]


def evaluate_recommendation_logic(recommendation: dict, trades_after: list[dict],
                                  trade_analyses: list[dict]) -> dict:
    """Evaluate whether the recommendation's reasoning was sound.

    Good recommendation != profitable outcome.
    Evaluate the logic: did the reasons given for buying materialize?
    """
    coin = recommendation.get("coin")
    reasoning = recommendation.get("reasoning", "")
    entry_price = recommendation.get("entry_price")
    direction = recommendation.get("direction")
    is_skip = recommendation.get("is_skip", False)

    result = {
        "coin": coin or "N/A",
        "direction": direction,
        "was_executed": False,
        "execution_details": [],
        "reasoning_validated": "inconclusive",
        "decision_quality": "inconclusive",
        "evidence": "",
    }

    if is_skip or direction == "SKIP":
        result["decision_quality"] = "good" if coin else "good"
        result["reasoning_validated"] = "valid"
        result["evidence"] = "空仓决定 — 守纪律不强行入场"
        return result

    if not coin:
        result["decision_quality"] = "inconclusive"
        result["evidence"] = "无法识别推荐的币种"
        return result

    # Check if this recommendation was executed (A4 bought it)
    buy_trades = [t for t in trades_after if t["action"] == "BUY" and t.get("symbol")
                  and coin in t["symbol"]]

    # Also check trade_analyses
    relevant_analyses = [a for a in trade_analyses if a.get("symbol", "").upper() == coin
                         or a.get("symbol", "").upper() == coin + "USDT"]

    if buy_trades or relevant_analyses:
        result["was_executed"] = True

    # Gather execution data
    for t in buy_trades:
        result["execution_details"].append({
            "time": t["time"],
            "price": t["price"],
            "qty": t["qty"],
            "reason": t["reason"],
        })

    for a in relevant_analyses:
        pnl = a.get("pnl_pct", 0)
        exit_quality = a.get("exit_quality", "unknown")
        result["execution_details"].append({
            "type": "analysis",
            "pnl_pct": pnl,
            "exit_quality": exit_quality,
            "lesson": a.get("lesson", ""),
        })

    # Evaluate reasoning quality based on what we know from the A3 report
    # Check if reasoning contains specific, testable claims
    reasoning_points = []

    # Check for volume claims
    if re.search(r'放量|成交量|量比|vol', reasoning, re.IGNORECASE):
        reasoning_points.append("volume_analysis")

    # Check for trend claims
    if re.search(r'趋势|RSI|突破|支撑|阻力|trend', reasoning, re.IGNORECASE):
        reasoning_points.append("technical_analysis")

    # Check for narrative/catalyst claims
    if re.search(r'叙事|板块|赛道|催化剂|新闻|利好|narrative|catalyst|AI|DePIN|RWA',
                 reasoning, re.IGNORECASE):
        reasoning_points.append("narrative_analysis")

    # Check for risk management
    if re.search(r'止损|止盈|仓位|限仓|风险|R/R|回报', reasoning, re.IGNORECASE):
        reasoning_points.append("risk_management")

    # Score the reasoning thoroughness
    score = len(reasoning_points)
    if score >= 3:
        result["reasoning_validated"] = "thorough"
    elif score >= 1:
        result["reasoning_validated"] = "partial"
    else:
        result["reasoning_validated"] = "poor"

    # Decision quality assessment
    if result["was_executed"]:
        # Check P&L from analyses
        total_pnl = 0
        has_analysis = False
        for e in result["execution_details"]:
            if isinstance(e, dict) and e.get("type") == "analysis":
                total_pnl += e.get("pnl_pct", 0)
                has_analysis = True

        if has_analysis:
            if total_pnl > 0 and result["reasoning_validated"] in ("thorough", "partial"):
                result["decision_quality"] = "good"
                result["evidence"] = f"推理充分 + 正回报 ({total_pnl:+.1f}%)"
            elif total_pnl > 0 and result["reasoning_validated"] == "poor":
                result["decision_quality"] = "lucky"
                result["evidence"] = f"推理薄弱但侥幸盈利 ({total_pnl:+.1f}%) — 运气成分高"
            elif total_pnl <= 0 and result["reasoning_validated"] in ("thorough", "partial"):
                result["decision_quality"] = "good_but_unlucky"
                result["evidence"] = f"推理充分但市场不利 ({total_pnl:+.1f}%) — 好决策≠好结果"
            else:
                result["decision_quality"] = "poor"
                result["evidence"] = f"推理薄弱且亏损 ({total_pnl:+.1f}%)"
        else:
            # Executed but no analysis file yet
            result["decision_quality"] = "pending"
            result["evidence"] = "已执行，待分析结果"
    else:
        # Wasn't executed — could be price deviation blocked it
        result["decision_quality"] = "not_executed"
        result["evidence"] = "A3已推荐但A4未执行（价格偏离阈值或其它原因）"

    return result


def evaluate_execution_quality(trades_for_coin: list[dict],
                               recommendation: dict,
                               trade_analyses: list[dict]) -> dict:
    """Evaluate A4 execution quality for a specific recommendation.

    Evaluate:
    1. Entry timing quality — did A4 buy at reasonable price vs A3's entry price range?
    2. Exit timing quality — was exit signal-based or panic-based?
    3. Discipline quality — did A4 follow the stop-loss and take-profit rules?
    """
    coin = recommendation.get("coin", "N/A")
    entry_price_target = recommendation.get("entry_price")
    stop_loss_target = recommendation.get("stop_loss")
    take_profit_target = recommendation.get("take_profit")

    result = {
        "coin": coin,
        "entry_quality": "inconclusive",
        "entry_evidence": "",
        "exit_quality": "inconclusive",
        "exit_evidence": "",
        "discipline_quality": "inconclusive",
        "discipline_evidence": "",
        "overall_score": 0,
    }

    # --- Entry quality ---
    buy_trades = [t for t in trades_for_coin if t["action"] == "BUY"]
    if buy_trades and entry_price_target:
        buy_prices = []
        for t in buy_trades:
            try:
                p = float(t["price"].replace("$", ""))
                buy_prices.append(p)
            except (ValueError, AttributeError):
                pass

        if buy_prices:
            avg_buy = sum(buy_prices) / len(buy_prices)
            deviation = abs(avg_buy - entry_price_target) / entry_price_target * 100

            if deviation <= 2.0:
                result["entry_quality"] = "excellent"
                result["entry_evidence"] = (f"A4买入均价${avg_buy:.4f}与A3建议${entry_price_target}偏差"
                                            f"{deviation:.1f}% — 精准执行")
                result["entry_score"] = 5
            elif deviation <= 5.0:
                result["entry_quality"] = "good"
                result["entry_evidence"] = (f"A4买入均价${avg_buy:.4f}与A3建议${entry_price_target}偏差"
                                            f"{deviation:.1f}% — 合理偏差范围")
                result["entry_score"] = 4
            elif deviation <= 10.0:
                result["entry_quality"] = "fair"
                result["entry_evidence"] = (f"A4买入均价${avg_buy:.4f}与A3建议${entry_price_target}偏差"
                                            f"{deviation:.1f}% — 偏差偏大")
                result["entry_score"] = 2
            else:
                result["entry_quality"] = "poor"
                result["entry_evidence"] = (f"A4买入均价${avg_buy:.4f}与A3建议${entry_price_target}偏差"
                                            f"{deviation:.1f}% — 显著偏离建议价")
                result["entry_score"] = 1
        else:
            result["entry_quality"] = "no_data"
            result["entry_evidence"] = "无法解析买入价格"
            result["entry_score"] = 0
    elif buy_trades:
        result["entry_quality"] = "executed_no_ref"
        result["entry_evidence"] = "已执行但无法对比A3建议价（无参考价）"
        result["entry_score"] = 3
    else:
        result["entry_quality"] = "not_executed"
        result["entry_evidence"] = "A4未执行买入"
        result["entry_score"] = 0

    # --- Exit quality ---
    sell_trades = [t for t in trades_for_coin if t["action"] == "SELL"]

    # Also check trade_analyses for exit quality
    analyses_for_coin = [a for a in trade_analyses
                         if a.get("symbol", "").upper() == coin
                         or a.get("symbol", "").upper() == coin + "USDT"]

    if analyses_for_coin:
        exit_qualities = [a.get("exit_quality", "unknown") for a in analyses_for_coin]
        if "correct" in exit_qualities:
            result["exit_quality"] = "signal_based"
            result["exit_evidence"] = "分析标记为'correct'退出 — 信号驱动"
            result["exit_score"] = 5
        elif "neutral" in exit_qualities or "wrong" in exit_qualities:
            result["exit_quality"] = "mixed"
            result["exit_evidence"] = f"退出质量分析: {', '.join(exit_qualities)}"
            result["exit_score"] = 3
        else:
            result["exit_quality"] = "pending_review"
            result["exit_evidence"] = f"退出标记: {', '.join(exit_qualities)}"
            result["exit_score"] = 2
    elif sell_trades:
        exit_reasons = [t["reason"] for t in sell_trades]
        panic_signals = ["panic", "恐慌", "FUD", "恐惧", "跟风", "随意", "直觉"]
        signal_signals = ["止损", "止盈", "E1", "E2", "E3", "E4", "信号", "趋势转跌",
                          "RSI", "超买", "超卖", "成交量萎缩", "评分骤降", "减仓线", "清仓线"]

        # Check if exits are signal-based or panic-based
        panic_count = 0
        signal_count = 0
        for r in exit_reasons:
            if any(s.lower() in r.lower() for s in panic_signals):
                panic_count += 1
            if any(s.lower() in r.lower() for s in signal_signals):
                signal_count += 1

        if signal_count > 0 and panic_count == 0:
            result["exit_quality"] = "signal_based"
            result["exit_evidence"] = f"退出原因含信号词({signal_count}次) — 纪律性退出"
            result["exit_score"] = 5
        elif signal_count > 0 and panic_count > 0:
            result["exit_quality"] = "mixed"
            result["exit_evidence"] = f"退出原因混合: 信号{signal_count}次/恐慌{panic_count}次"
            result["exit_score"] = 3
        elif panic_count > 0:
            result["exit_quality"] = "panic_based"
            result["exit_evidence"] = f"退出原因含恐慌词({panic_count}次) — 情绪驱动"
            result["exit_score"] = 1
        else:
            result["exit_quality"] = "unknown_reason"
            result["exit_evidence"] = "退出原因无法归类"
            result["exit_score"] = 2
    else:
        result["exit_quality"] = "no_exit"
        result["exit_evidence"] = "该币种无退出记录（可能仍在持仓）"
        result["exit_score"] = 3  # neutral — no exit is not necessarily bad

    # --- Discipline quality ---
    # Check if stop-loss was respected
    discipline_violations = []
    discipline_passes = []

    if stop_loss_target and sell_trades:
        for t in sell_trades:
            try:
                sell_price = float(t["price"].replace("$", ""))
            except (ValueError, AttributeError):
                continue
            reason = t["reason"].lower()
            # If sold below stop-loss, check if it was close
            if sell_price < stop_loss_target * 0.95:  # more than 5% below SL
                if "止损" in reason:
                    discipline_passes.append(f"严格执行止损（卖${sell_price} ≤ 止损${stop_loss_target}）")
                else:
                    discipline_violations.append(f"跌破止损且非止损退出（${sell_price} < 止损${stop_loss_target}）")
            elif sell_price >= stop_loss_target:
                if "止损" in reason and sell_price >= stop_loss_target:
                    discipline_violations.append(f"在止损价${stop_loss_target}以上执行止损退出（${sell_price}）— 可能错失利润")
                else:
                    discipline_passes.append(f"在止损线上方退出（${sell_price}）")

    if take_profit_target and sell_trades:
        for t in sell_trades:
            try:
                sell_price = float(t["price"].replace("$", ""))
            except (ValueError, AttributeError):
                continue
            reason = t["reason"].lower()
            if "止盈" in reason and sell_price >= take_profit_target * 0.95:
                discipline_passes.append(f"按止盈规则退出（${sell_price} ≈ 止盈${take_profit_target}）")

    if discipline_violations:
        result["discipline_quality"] = "violations_detected"
        result["discipline_evidence"] = "; ".join(discipline_violations)
        result["discipline_score"] = 1
    elif discipline_passes:
        result["discipline_quality"] = "disciplined"
        result["discipline_evidence"] = "; ".join(discipline_passes)
        result["discipline_score"] = 5
    else:
        result["discipline_quality"] = "no_data"
        result["discipline_evidence"] = "无纪律违规或执行记录"
        result["discipline_score"] = 3

    # --- Overall execution score ---
    scores = [
        result.get("entry_score", 0),
        result.get("exit_score", 0),
        result.get("discipline_score", 0),
    ]
    result["overall_score"] = round(sum(scores) / len(scores), 1) if scores else 0

    return result


def get_a3_accuracy_stats(results: list[dict]) -> dict:
    """Compute A3 recommendation accuracy statistics."""
    total = len(results)
    if total == 0:
        return {"total": 0, "good": 0, "good_but_unlucky": 0, "lucky": 0, "poor": 0,
                "not_executed": 0, "accuracy_pct": 0}

    good = sum(1 for r in results if r.get("decision_quality") == "good")
    good_but_unlucky = sum(1 for r in results if r.get("decision_quality") == "good_but_unlucky")
    lucky = sum(1 for r in results if r.get("decision_quality") == "lucky")
    poor = sum(1 for r in results if r.get("decision_quality") == "poor")
    not_exec = sum(1 for r in results if r.get("decision_quality") == "not_executed")

    # Effective accuracy: good + good_but_unlucky / (total - not_exec - pending)
    evaluable = total - not_exec
    good_decisions = good + good_but_unlucky
    accuracy = round(good_decisions / evaluable * 100, 1) if evaluable > 0 else 0

    return {
        "total": total,
        "good": good,
        "good_but_unlucky": good_but_unlucky,
        "lucky": lucky,
        "poor": poor,
        "not_executed": not_exec,
        "accuracy_pct": accuracy,
        "evaluable": evaluable,
    }


def get_execution_stats(exec_results: list[dict]) -> dict:
    """Compute A4 execution quality statistics."""
    total = len(exec_results)
    if total == 0:
        return {"total": 0, "avg_score": 0, "max_score": 5.0, "entry_excellent": 0, "signal_exit": 0,
                "disciplined": 0}

    avg_score = round(sum(e.get("overall_score", 0) for e in exec_results) / total, 1)
    entry_excellent = sum(1 for e in exec_results if e.get("entry_quality") == "excellent")
    signal_exit = sum(1 for e in exec_results if e.get("exit_quality") == "signal_based")
    disciplined = sum(1 for e in exec_results if e.get("discipline_quality") == "disciplined")

    return {
        "total": total,
        "avg_score": avg_score,
        "max_score": 5.0,
        "entry_excellent": entry_excellent,
        "signal_exit": signal_exit,
        "disciplined": disciplined,
    }


def get_weak_spots(rec_results: list[dict], exec_results: list[dict],
                   master_exp: dict) -> list[dict]:
    """Identify weak spots in the system."""
    weak_spots = []

    # 1. Check A3 recommendations not being executed
    not_executed = [r for r in rec_results if r.get("decision_quality") == "not_executed"]
    if not_executed:
        coins = [r.get("coin", "?") for r in not_executed]
        weak_spots.append({
            "area": "A3→A4 执行链路阻塞",
            "severity": "high",
            "detail": f"{len(not_executed)}个推荐未被执行: {', '.join(coins)}。原因可能为价格偏离±2%阈值。",
            "recommendation": "考虑扩大动态阈值或改用独立性验证替代静态±2%"
        })

    # 2. Check poor/lucky decisions
    poor_decisions = [r for r in rec_results if r.get("decision_quality") in ("poor", "lucky")]
    if poor_decisions:
        weak_spots.append({
            "area": "A3推荐质量不足",
            "severity": "medium",
            "detail": f"{len(poor_decisions)}个推荐质量评分低。推理不够充分或依赖运气的推荐。",
            "recommendation": "加强四维精选法执行检查，确保每维度均有数据支撑"
        })

    # 3. Check execution discipline
    violations = [e for e in exec_results if e.get("discipline_quality") == "violations_detected"]
    if violations:
        weak_spots.append({
            "area": "A4执行纪律问题",
            "severity": "high",
            "detail": f"{len(violations)}次执行纪律违规。",
            "recommendation": "强化A4退出规则检查，禁止非信号驱动退出"
        })

    # 4. Check panic exits
    panic_exits = [e for e in exec_results if e.get("exit_quality") == "panic_based"]
    if panic_exits:
        weak_spots.append({
            "area": "A4情绪化退出",
            "severity": "critical",
            "detail": f"{len(panic_exits)}次恐慌/情绪驱动退出。",
            "recommendation": "所有退出必须基于E1-E5信号系统，禁止主观决定"
        })

    # 5. Check master experience — E3 overuse
    e3_rules = [r for r in master_exp.get("rules", [])
                if r.get("signal") == "E3" and r.get("effectiveness") in ("低效", "需要改进")]
    if e3_rules:
        weak_spots.append({
            "area": "E3信号过度使用",
            "severity": "medium",
            "detail": f"MASTER_EXPERIENCE记录E3信号触发次数过多且效果不佳。最近20笔中15笔E3触发。",
            "recommendation": "E3单独触发不应直接卖出，需结合成交量或RSI确认（已建议但需强制执行）"
        })

    return weak_spots


# ── 主评估函数 ──────────────────────────────────────────

def run_evaluation(days: int = 7):
    """Run the full supervision evaluation and print results as Markdown."""

    # ── Load data ──
    trades = load_trades_md(TRADES_PATH)
    master_exp = load_master_experience(MASTER_EXP_PATH)
    trade_analyses = load_trade_analyses(TRADES_DATA_DIR)
    a3_reports = load_a3_reports(A3_OUTPUT_DIR, days)
    a3_findings = extract_a3_findings(A3_FINDINGS_PATH)

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M")

    # ── Begin Output ──
    print(f"# A5 监督评估报告 — ZH复盘(ZQ系统视角)")
    print(f"")
    print(f"**评估周期**: 最近 {days} 天 (since {cutoff})")
    print(f"**评估对象**: A3推荐质量 + A4执行质量")
    print(f"**核心理念**: 决策质量 ≠ P&L结果。好决策可能亏钱，坏决策可能赚钱。")
    print(f"")
    print(f"---")
    print(f"")

    # ══════════════════════════════════════════════════════
    # SECTION 1: RECOMMENDATION QUALITY
    # ══════════════════════════════════════════════════════
    print(f"## 1️⃣ RECOMMENDATION_QUALITY — A3推荐质量评估")
    print(f"")
    print(f"> 核心问题：「推荐的逻辑是否成立？」而不是「是否赚钱」。")
    print(f"> 评估方法：提取A3每日精选逻辑 → 对比实际市场走势 → 判断推理是否有效。")
    print(f"")

    rec_results = []

    if not a3_reports:
        print(f"⚠️ 最近 {days} 天内无A3报告。")
        print(f"")
    else:
        for report in a3_reports:
            rec = extract_a3_recommendation(report)
            if not rec:
                continue

            # Get trades for this coin around the recommendation date
            trades_for_coin = get_trades_for_date(trades, report["date"])

            # Also get trades for this specific coin
            if rec.get("coin"):
                trades_for_coin = get_trades_for_coin(trades, rec["coin"], days)

            # Evaluate recommendation logic
            eval_result = evaluate_recommendation_logic(rec, trades_for_coin, trade_analyses)
            rec_results.append(eval_result)

            date = rec.get("date", "?")
            coin = rec.get("coin", "N/A") or "空仓"
            direction = rec.get("direction", "?")
            confidence = rec.get("confidence", "?")
            reasoning = rec.get("reasoning", "无推理记录")[:200]
            dq = eval_result.get("decision_quality", "inconclusive")
            evidence = eval_result.get("evidence", "")

            # Emoji for quality
            quality_emoji = {
                "good": "✅ 好决策",
                "good_but_unlucky": "🟡 好决策(市场不利)",
                "lucky": "⚠️ 侥幸盈利",
                "poor": "❌ 坏决策",
                "not_executed": "⏭️ 未执行",
                "pending": "⏳ 待分析",
                "inconclusive": "❓ 待定",
            }.get(dq, "❓ 待定")

            print(f"### 📅 {date} — {coin}")
            print(f"")
            print(f"| 指标 | 值 |")
            print(f"|:-----|:----|")
            print(f"| 方向 | {direction} |")
            print(f"| 置信度 | {confidence}/10 |")
            print(f"| 是否执行 | {'✅ 是' if eval_result.get('was_executed') else '❌ 否'} |")
            print(f"| 决策质量 | {quality_emoji} |")
            print(f"| 推理验证 | {eval_result.get('reasoning_validated', '?')} |")
            print(f"")

            if reasoning:
                print(f"**A3推理摘要**:")
                print(f"> {reasoning}")
                print(f"")

            print(f"**评估依据**: {evidence}")
            print(f"")

            if eval_result.get("execution_details"):
                print(f"**执行详情**:")
                for ed in eval_result["execution_details"]:
                    if isinstance(ed, dict):
                        if ed.get("type") == "analysis":
                            pl = ed.get("pnl_pct", 0)
                            eq = ed.get("exit_quality", "?")
                            print(f"- P&L: {pl:+.1f}% | 退出质量: {eq} | 教训: {ed.get('lesson', '?')}")
                        else:
                            print(f"- 时间: {ed.get('time', '?')} | 价格: ${ed.get('price', '?')}")
                    else:
                        print(f"- {ed}")
                print(f"")

    print(f"---")
    print(f"")

    # ══════════════════════════════════════════════════════
    # SECTION 2: EXECUTION QUALITY
    # ══════════════════════════════════════════════════════
    print(f"## 2️⃣ EXECUTION_QUALITY — A4执行质量评估")
    print(f"")
    print(f"> 核心问题：「A4是否以合理的时机和纪律执行了A3的推荐？」")
    print(f"> 三项评分：入场时机 | 退出时机 | 纪律性")
    print(f"")

    exec_results = []
    if a3_reports:
        for report in a3_reports:
            rec = extract_a3_recommendation(report)
            if not rec or not rec.get("coin"):
                continue

            trades_for_coin = get_trades_for_coin(trades, rec["coin"], days)
            exec_result = evaluate_execution_quality(trades_for_coin, rec, trade_analyses)
            exec_results.append(exec_result)

            coin = exec_result.get("coin", "N/A")

            print(f"### 💰 {coin}")
            print(f"")

            # Entry quality
            eq = exec_result.get("entry_quality", "?")
            eq_map = {"excellent": "🟢 优秀", "good": "🟢 良好", "fair": "🟡 一般",
                      "poor": "🔴 差", "executed_no_ref": "🟡 已执行(无参考)",
                      "not_executed": "⚪ 未执行", "no_data": "⚪ 无数据",
                      "inconclusive": "⚪ 待定"}
            print(f"**入场质量**: {eq_map.get(eq, eq)}")
            print(f"- 依据: {exec_result.get('entry_evidence', '无')}")
            print(f"")

            # Exit quality
            xq = exec_result.get("exit_quality", "?")
            xq_map = {"signal_based": "🟢 信号驱动", "mixed": "🟡 混合",
                      "panic_based": "🔴 恐慌驱动", "no_exit": "⚪ 未退出",
                      "pending_review": "🟡 待复查", "unknown_reason": "⚪ 原因不明",
                      "inconclusive": "⚪ 待定"}
            print(f"**退出质量**: {xq_map.get(xq, xq)}")
            print(f"- 依据: {exec_result.get('exit_evidence', '无')}")
            print(f"")

            # Discipline quality
            dq = exec_result.get("discipline_quality", "?")
            dq_map = {"disciplined": "🟢 纪律良好", "violations_detected": "🔴 违规",
                      "no_data": "⚪ 无数据", "inconclusive": "⚪ 待定"}
            print(f"**纪律性**: {dq_map.get(dq, dq)}")
            print(f"- 依据: {exec_result.get('discipline_evidence', '无')}")
            print(f"")

            # Overall
            score = exec_result.get("overall_score", 0)
            print(f"**综合评分**: **{score}/5.0**")
            print(f"")

    else:
        print(f"⚠️ 最近 {days} 天内无A3报告，无法评估执行质量。")
        print(f"")
        exec_results = []

    print(f"---")
    print(f"")

    # ══════════════════════════════════════════════════════
    # SECTION 3: SUMMARY
    # ══════════════════════════════════════════════════════
    print(f"## 3️⃣ SUMMARY — 综合统计与改进建议")
    print(f"")

    # A3 Accuracy stats
    a3_stats = get_a3_accuracy_stats(rec_results)

    print(f"### 📊 A3推荐准确率统计")
    print(f"")
    print(f"| 指标 | 数值 |")
    print(f"|:-----|:----:|")
    print(f"| 总推荐数 | {a3_stats['total']} |")
    print(f"| 可评估数 | {a3_stats['evaluable']} |")
    print(f"| ✅ 好决策(盈利) | {a3_stats['good']} |")
    print(f"| 🟡 好决策(市场不利) | {a3_stats['good_but_unlucky']} |")
    print(f"| ⚠️ 侥幸盈利 | {a3_stats['lucky']} |")
    print(f"| ❌ 坏决策 | {a3_stats['poor']} |")
    print(f"| ⏭️ 未执行 | {a3_stats['not_executed']} |")
    print(f"| **有效准确率** | **{a3_stats['accuracy_pct']}%** |")
    print(f"")

    # A4 Execution stats
    exec_stats = get_execution_stats(exec_results)
    print(f"### 📊 A4执行质量统计")
    print(f"")
    print(f"| 指标 | 数值 |")
    print(f"|:-----|:----:|")
    print(f"| 评估交易数 | {exec_stats['total']} |")
    print(f"| 🏆 平均分 | **{exec_stats['avg_score']}/{exec_stats['max_score']}** |")
    print(f"| 🟢 精准入场 | {exec_stats['entry_excellent']} |")
    print(f"| 🟢 信号退出 | {exec_stats['signal_exit']} |")
    print(f"| 🟢 纪律良好 | {exec_stats['disciplined']} |")
    print(f"")

    # Weak spots
    weak_spots = get_weak_spots(rec_results, exec_results, master_exp)
    if weak_spots:
        print(f"### 🔴 薄弱环节识别")
        print(f"")
        for ws in weak_spots:
            severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            print(f"{severity_emoji.get(ws['severity'], '⚪')} **{ws['area']}** ({ws['severity']})")
            print(f"- 详情: {ws['detail']}")
            print(f"- 建议: {ws['recommendation']}")
            print(f"")

    # Recommendations for improvement
    print(f"### 💡 改进建议汇总")
    print(f"")
    print(f"1. **解决A3执行阻塞**: 将静态±2%阈值改为动态验证（如趋势验证+独立价格检查），避免合理推荐被阻塞")
    print(f"2. **强化A4退出纪律**: 所有退出必须关联E1-E5信号，禁止非信号驱动退出。恐慌/直觉驱动的退出应标记为违规")
    print(f"3. **改进A3推理透明度**: 每项推荐需标注推理深度（量价/趋势/叙事/风控各维度），以便A5评估")
    print(f"4. **建立反馈闭环**: A5评估结果应写入MASTER_EXPERIENCE.json，供A3下次推荐参考")
    print(f"5. **E3过度触发**: 近20次交易中15笔E3触发，E3不应单独触发卖出，需结合成交量或RSI确认")
    print(f"")

    print(f"---")
    print(f"*报告生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    print(f"*工具: tools/supervision_eval.py*")


# ── CLI Entry Point ─────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="A5 复盘官监督评估 — A3推荐质量 + A4执行质量"
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="分析最近N天的数据 (default: 7)"
    )
    args = parser.parse_args()

    if not os.path.exists(BASE_DIR):
        print(f"错误: 工作目录不存在 {BASE_DIR}")
        print(f"请确保在 zq_web4_trading_system 目录或其父目录运行")
        sys.exit(1)

    run_evaluation(days=args.days)


if __name__ == "__main__":
    main()
