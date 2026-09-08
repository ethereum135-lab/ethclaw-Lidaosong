#!/usr/bin/env python3
"""
TimesFM 预测准确性追踪器
每天回看：昨天的预测准不准？累计准确率多少？

用法:
  python3 tools/timesfm_accuracy.py          # 追踪前一次的预测
  python3 tools/timesfm_accuracy.py --report # 输出累计报告

工作原理:
  1. 每次运行timesfm_signal.py时，预测记录保存到 data/timesfm_tracker.json
  2. 下次运行时，对比实际价格与上次预测的差距
  3. 持续累积准确率数据
"""

import json
import os
import sys
import numpy as np
import requests
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = os.path.expanduser("~/zq_web4_trading_system/data")
TRACKER_FILE = os.path.join(DATA_DIR, "timesfm_tracker.json")
SIGNALS_FILE = os.path.join(DATA_DIR, "timesfm_signals.json")

def get_current_price(symbol: str) -> float:
    """从币安获取当前价格"""
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
    r = requests.get(url, timeout=10)
    return float(r.json()["price"])


def load_tracker() -> dict:
    """加载追踪记录"""
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE) as f:
            return json.load(f)
    return {"predictions": [], "stats": {"total": 0, "correct": 0, "wrong": 0, "accuracy_pct": 0}}


def save_tracker(tracker: dict):
    """保存追踪记录"""
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f, ensure_ascii=False, indent=2)


def check_previous_predictions():
    """检查上一次的预测"""
    tracker = load_tracker()
    predictions = tracker.get("predictions", [])
    stats = tracker.get("stats", {"total": 0, "correct": 0, "wrong": 0, "accuracy_pct": 0})

    # 只检查还没有验证过的预测
    unchecked = [p for p in predictions if not p.get("verified")]
    
    if not unchecked:
        print("📋 没有待验证的预测记录")
        if stats["total"] > 0:
            print(f"📊 累计: {stats['total']}次 | 正确{stats['correct']} | 错误{stats['wrong']} | 准确率{stats['accuracy_pct']:.1f}%")
        return tracker

    print(f"🔍 检查 {len(unchecked)} 条未验证的预测...")
    
    for pred in unchecked:
        symbol = pred["symbol"]
        predicted_dir = pred["direction"]  # "up" or "down"
        predicted_target = pred["target_price"]
        predicted_change = pred["change_pct"]
        
        try:
            current_price = get_current_price(symbol)
            actual_change = (current_price - pred["current_price"]) / pred["current_price"] * 100
            
            # 判断是否预测正确
            if (predicted_dir == "up" and actual_change > 0) or \
               (predicted_dir == "down" and actual_change < 0):
                correct = True
                stats["correct"] += 1
                tag = "✅ 正确"
            else:
                correct = False
                stats["wrong"] += 1
                tag = "❌ 错误"
            
            pred["verified"] = True
            pred["verified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            pred["actual_price"] = round(current_price, 4)
            pred["actual_change_pct"] = round(actual_change, 2)
            pred["correct"] = correct
            
            stats["total"] += 1
            
            print(f"  [{symbol}] 预测{pred['duration_hours']}h后{tag}")
            print(f"    预测: ${predicted_target:.2f} ({predicted_change:+.2f}%)")
            print(f"    实际: ${current_price:.2f} ({actual_change:+.2f}%)")
            
        except Exception as e:
            print(f"  [{symbol}] 检查失败: {e}")
    
    # 更新统计
    if stats["total"] > 0:
        stats["accuracy_pct"] = round(stats["correct"] / stats["total"] * 100, 1)
    
    tracker["stats"] = stats
    tracker["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_tracker(tracker)
    
    print(f"\n📊 累计准确率: {stats['accuracy_pct']:.1f}% ({stats['correct']}/{stats['total']})")
    return tracker


def record_new_predictions():
    """从最新的signals.json记录新的预测"""
    if not os.path.exists(SIGNALS_FILE):
        print("⚠️ signals.json不存在，跳过记录")
        return
    
    with open(SIGNALS_FILE) as f:
        data = json.load(f)
    
    tracker = load_tracker()
    existing = {(p["symbol"], p["generated_at"]) for p in tracker.get("predictions", []) if not p.get("verified")}
    
    new_count = 0
    for coin in data.get("ranked", []):
        if "timesfm" not in coin:
            continue
        tm = coin["timesfm"]
        key = (coin["symbol"], data.get("generated_at", ""))
        if key in existing:
            continue
        
        tracker.setdefault("predictions", []).append({
            "symbol": coin["symbol"],
            "current_price": tm["current_price"],
            "target_price": tm["target_price"],
            "change_pct": tm["change_pct"],
            "direction": tm["direction"],
            "confidence": tm["confidence"],
            "horizon": tm["horizon"],
            "duration_hours": tm["timeline_hours"],
            "generated_at": data.get("generated_at", ""),
            "verified": False,
        })
        new_count += 1
    
    save_tracker(tracker)
    if new_count > 0:
        print(f"📝 记录了 {new_count} 条新预测")
    return tracker


def show_report():
    """输出累计报告"""
    tracker = load_tracker()
    stats = tracker.get("stats", {})
    predictions = tracker.get("predictions", [])
    last_checked = tracker.get("last_checked", "从未")
    
    print("=" * 50)
    print("   🤖 TimesFM 预测准确性报告")
    print("=" * 50)
    print(f"最后验证: {last_checked}")
    print(f"总预测:   {stats.get('total', 0)} 次")
    print(f"正确:     {stats.get('correct', 0)} 次")
    print(f"错误:     {stats.get('wrong', 0)} 次")
    print(f"准确率:   {stats.get('accuracy_pct', 0):.1f}%")
    print()
    
    # 按置信度分层
    verified = [p for p in predictions if p.get("verified")]
    high = [p for p in verified if p.get("confidence") == "high"]
    med = [p for p in verified if p.get("confidence") == "medium"]
    low = [p for p in verified if p.get("confidence") == "low"]
    
    def acc(group):
        if not group:
            return 0
        c = sum(1 for p in group if p.get("correct"))
        return round(c / len(group) * 100, 1)
    
    print("按置信度分层:")
    print(f"  🔴 高置信度: {len(high)}次 - 准确率 {acc(high)}%")
    print(f"  🟡 中置信度: {len(med)}次 - 准确率 {acc(med)}%")
    print(f"  🟢 低置信度: {len(low)}次 - 准确率 {acc(low)}%")
    
    # 最近10条
    recent = [p for p in verified if p.get("correct") is not None][-10:]
    if recent:
        print("\n最近验证:")
        for p in reversed(recent):
            tag = "✅" if p.get("correct") else "❌"
            print(f"  {tag} {p['symbol']}: 预测{p['change_pct']:+.2f}% → 实际{p.get('actual_change_pct', 0):+.2f}% ({p.get('confidence','-')})")
    
    # 正确/错误的币分布
    if verified:
        from collections import Counter
        correct_symbols = Counter(p["symbol"] for p in verified if p.get("correct"))
        wrong_symbols = Counter(p["symbol"] for p in verified if not p.get("correct"))
        print("\n常预测正确的币:")
        for sym, cnt in correct_symbols.most_common(5):
            print(f"  ✅ {sym}: {cnt}次正确")
        print("\n常预测错误的币:")
        for sym, cnt in wrong_symbols.most_common(5):
            print(f"  ❌ {sym}: {cnt}次错误")


def main():
    args = sys.argv[1:]
    
    if "--report" in args:
        show_report()
        return
    
    # 1. 先检查上次预测（验证）
    check_previous_predictions()
    
    # 2. 记录新的预测
    record_new_predictions()


if __name__ == "__main__":
    main()
