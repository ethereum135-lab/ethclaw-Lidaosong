#!/usr/bin/env python3
"""
规则库学习闭环 (Rule Library Learning Loop)
功能：自动评估规则命中率，优化规则参数，记录学习历史

学习闭环：
1. 读取规则匹配历史（rule_library.json的历史记录）
2. 对比规则建议 vs 实际市场走势
3. 计算每条规则的命中率/准确率
4. 调整规则优先级（高命中率↑，低命中率↓）
5. 记录学习历史

输出：
- macro/rule_performance.json — 规则表现评估
- macro/rule_learning_history.json — 学习历史

Cron: 每日10:00执行（在rule_library 4小时Cron之后）
"""
import json, os, time, sys

SC = "/home/ubuntu/shared_context"
RULE_LIBRARY_OUTPUT = os.path.join(SC, "macro/rule_library.json")
PERFORMANCE_FILE = os.path.join(SC, "macro/rule_performance.json")
HISTORY_FILE = os.path.join(SC, "macro/rule_learning_history.json")
EVENTS_FILE = os.path.join(SC, "events/events.ndjson")
REVIEW_DIR = os.path.join(SC, "reviews/")

MAX_HISTORY = 90  # 保留90天学习历史
PERFORMANCE_THRESHOLD = 0.5  # 命中率低于50%的规则降级
PROMOTION_THRESHOLD = 0.7  # 命中率高于70%的规则升级


def _read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _log_event(event_type, message):
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,
        "source": "rule_learning",
        "message": message,
    }
    os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
    with open(EVENTS_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_rule_history():
    """加载历史规则匹配记录"""
    history = _read_json(HISTORY_FILE, {"records": []})
    return history.get("records", [])


def load_recent_reviews(days=7):
    """加载最近N天的复盘数据"""
    reviews = []
    if not os.path.exists(REVIEW_DIR):
        return reviews

    for fname in sorted(os.listdir(REVIEW_DIR), reverse=True)[:days]:
        if fname.endswith(".json"):
            data = _read_json(os.path.join(REVIEW_DIR, fname))
            if data:
                reviews.append(data)
    return reviews


def evaluate_rule(rule_id, history, reviews):
    """评估单条规则的表现"""
    matches = [h for h in history if rule_id in str(h.get("matched_rules", []))]
    if not matches:
        return {
            "rule_id": rule_id,
            "total_signals": 0,
            "hit_rate": None,
            "status": "no_data",
            "recommendation": "无历史数据，保持现状",
        }

    total = len(matches)
    hits = 0
    misses = 0
    details = []

    for m in matches:
        date = m.get("date", "")
        action = m.get("final_action", {})

        # 从复盘中找对应日期的结果
        review = next((r for r in reviews if r.get("date") == date), None)

        if review:
            daily_pnl = review.get("daily_pnl_pct", 0)
            action_type = action.get("action_type", "")

            # 判断规则建议方向是否与实际结果一致
            action_reason = action.get("reason", "")
            if "加仓" in action_reason or "做多" in action_reason or "long" in action_reason.lower():
                if daily_pnl > 0:
                    hits += 1
                    details.append({"date": date, "result": "hit", "pnl": daily_pnl})
                else:
                    misses += 1
                    details.append({"date": date, "result": "miss", "pnl": daily_pnl})
            elif "减仓" in action_reason or "避险" in action_reason or "halt" in action_reason.lower():
                if daily_pnl < 0:
                    hits += 1
                    details.append({"date": date, "result": "hit", "pnl": daily_pnl})
                else:
                    misses += 1
                    details.append({"date": date, "result": "miss", "pnl": daily_pnl})
            else:
                # 中性规则，看整体是否盈利
                if daily_pnl > 0:
                    hits += 1
                    details.append({"date": date, "result": "hit", "pnl": daily_pnl})
                else:
                    misses += 1
                    details.append({"date": date, "result": "miss", "pnl": daily_pnl})
        else:
            details.append({"date": date, "result": "no_review"})

    hit_rate = hits / total if total > 0 else 0

    if hit_rate >= PROMOTION_THRESHOLD:
        status = "excellent"
        recommendation = f"命中率{hit_rate*100:.0f}%≥{PROMOTION_THRESHOLD*100}%，建议提升优先级"
    elif hit_rate >= PERFORMANCE_THRESHOLD:
        status = "acceptable"
        recommendation = f"命中率{hit_rate*100:.0f}%，保持现状"
    elif total >= 3:
        status = "underperforming"
        recommendation = f"命中率{hit_rate*100:.0f}%<{PERFORMANCE_THRESHOLD*100}%，建议降低优先级或修改条件"
    else:
        status = "insufficient_data"
        recommendation = f"仅{total}次匹配，数据不足"

    return {
        "rule_id": rule_id,
        "total_signals": total,
        "hits": hits,
        "misses": misses,
        "hit_rate": round(hit_rate, 3),
        "status": status,
        "recommendation": recommendation,
        "details": details[-5:],
    }


def run_learning_loop():
    """执行规则学习闭环"""
    print("[规则学习] 开始规则库学习闭环...")

    # 1. 加载当前规则匹配
    current = _read_json(RULE_LIBRARY_OUTPUT, {})
    matched_rules = [r.split(":")[0] for r in current.get("matched_rules", [])]

    # 2. 加载历史
    history = load_rule_history()
    reviews = load_recent_reviews(30)

    print(f"  历史记录: {len(history)}条")
    print(f"  复盘数据: {len(reviews)}天")

    # 3. 记录今天的匹配
    today_record = {
        "date": time.strftime("%Y-%m-%d"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "matched_rules": current.get("matched_rules", []),
        "matched_count": current.get("matched_count", 0),
        "final_action": current.get("final_action", {}),
    }

    if today_record not in history:
        history.append(today_record)
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    # 4. 评估所有规则
    all_rule_ids = set()
    for h in history:
        for r in h.get("matched_rules", []):
            all_rule_ids.add(r.split(":")[0].strip())

    evaluations = []
    for rule_id in sorted(all_rule_ids):
        ev = evaluate_rule(rule_id, history, reviews)
        evaluations.append(ev)
        icon = {"excellent": "★", "acceptable": "✓", "underperforming": "✗", "insufficient_data": "?", "no_data": "-"}.get(ev["status"], "?")
        print(f"  {icon} {rule_id}: {ev['total_signals']}次信号, 命中率={ev['hit_rate']}, {ev['status']}")

    # 5. 生成优化建议
    optimizations = []
    for ev in evaluations:
        if ev["status"] == "excellent":
            optimizations.append({"rule_id": ev["rule_id"], "action": "promote", "reason": ev["recommendation"]})
        elif ev["status"] == "underperforming":
            optimizations.append({"rule_id": ev["rule_id"], "action": "demote", "reason": ev["recommendation"]})

    # 6. 输出
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "date": time.strftime("%Y-%m-%d"),
        "total_rules_evaluated": len(evaluations),
        "total_history_records": len(history),
        "total_reviews": len(reviews),
        "today_matched": matched_rules,
        "evaluations": evaluations,
        "optimizations": optimizations,
        "summary": f"{len(evaluations)}规则评估, {len(optimizations)}条优化建议",
    }

    _write_json(PERFORMANCE_FILE, report)
    _write_json(HISTORY_FILE, {"records": history, "last_updated": report["timestamp"]})

    _log_event("macro.rule_learning", f"规则学习: {report['summary']}")

    print(f"\n[规则学习] 完成: {report['summary']}")
    if optimizations:
        print("  优化建议:")
        for opt in optimizations:
            print(f"    {opt['action'].upper()} {opt['rule_id']}: {opt['reason']}")

    return report


if __name__ == "__main__":
    run_learning_loop()
