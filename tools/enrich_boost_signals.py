#!/usr/bin/env python3
"""
同步完成后台处理 — 从coin_enrichment读取标签，提升signals.json中匹配币种的评分。

A8 smart_money_signal → +15分
A7 正面舆情 → +10分
A8 + A7 双重确认 → +30分（阈值激励）

确保链上资金信号、舆情信号在A4交易时被纳入评分。
"""
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SIGNALS_PATH = BASE_DIR / "data" / "signals.json"
ENRICH_DIR = BASE_DIR / "data" / "coin_enrichment"


def load_enrich_tags(symbol: str) -> dict:
    """读取某个币的enrich标签（如果存在）"""
    # signals.json里的symbol没有USDT后缀
    enrich_path = ENRICH_DIR / f"{symbol.upper()}.json"
    if not enrich_path.exists():
        # 试试带USDT的
        enrich_path = ENRICH_DIR / f"{symbol.upper()}USDT.json"
    if not enrich_path.exists():
        return {}
    try:
        with open(enrich_path) as f:
            data = json.load(f)
        return data.get("tags", {})
    except (json.JSONDecodeError, IOError):
        return {}


def calculate_boost(symbol: str, current_score: int, gain_24h: float = 0) -> dict:
    """根据enrich标签计算加分

    🛡️ Pump Guard: 24h涨幅>40%的币不加分（已泵顶，追高风险大）
    """
    tags = load_enrich_tags(symbol)
    if not tags:
        return {"boost": 0, "sources": []}

    # 🛡️ Pump Guard: 24h>40%的已泵顶币种不加分
    if gain_24h > 40:
        return {"boost": 0, "sources": [], "note": f"pump-guard: gain_24h={gain_24h:.1f}%>40%"}

    boost = 0
    sources = []

    # A8: smart_money_signal → +15
    a8 = tags.get("A8", {})
    if a8.get("smart_money_signal"):
        boost += 15
        sources.append("A8")

    # A7: 正面舆情 → +10
    a7 = tags.get("A7", {})
    if a7.get("sentiment") in ("positive", "bullish"):
        boost += 10
        sources.append("A7")

    # 双重确认：A8 + A7 → 额外+5（共+15/+30）
    if "A8" in sources and "A7" in sources:
        boost += 5
        sources.append("A8+A7双重确认")

    return {"boost": boost, "sources": sources}


def apply_boosts(signals: dict) -> dict:
    """对所有信号应用enrich加分"""
    total_boosted = 0
    total_upgraded = 0

    for result in signals.get("results", []):
        symbol = result.get("symbol", "")
        current_score = result.get("total_score", 0)
        current_level = result.get("level", "")
        gain_24h = result.get("gain_24h", 0) or 0

        boost_info = calculate_boost(symbol, current_score, float(gain_24h))
        boost = boost_info["boost"]
        sources = boost_info["sources"]

        if boost == 0:
            # 有来源说明是被pump guard拦截的
            note = boost_info.get("note", "")
            if note:
                result["_enrich_note"] = note
            continue

        # 应用加分
        new_score = current_score + boost
        result["total_score"] = new_score
        result["_enrich_boost"] = boost
        result["_enrich_sources"] = sources
        total_boosted += 1

        # 等级提升
        old_level = current_level
        if new_score >= 60 and current_level in ("SIGNAL", "WATCH", "pass"):
            result["level"] = "STRONG"
            total_upgraded += 1
        elif new_score >= 40 and current_level in ("WATCH", "pass"):
            result["level"] = "SIGNAL"

        if result["level"] != old_level:
            result["_enrich_upgraded"] = f"{old_level}→{result['level']}"

    # 更新summary
    strong_count = sum(1 for r in signals.get("results", []) if r.get("level") == "STRONG")
    signal_count = sum(1 for r in signals.get("results", []) if r.get("level") == "SIGNAL")
    signals["summary"]["strong"] = strong_count
    signals["summary"]["signal"] = signal_count
    signals["summary"]["_enrich_boosted"] = total_boosted
    signals["summary"]["_enrich_upgraded"] = total_upgraded

    return signals


def main():
    if not SIGNALS_PATH.exists():
        print(f"❌ signals.json not found: {SIGNALS_PATH}")
        return 1

    with open(SIGNALS_PATH) as f:
        signals = json.load(f)

    original_strong = signals["summary"]["strong"]
    original_signal = signals["summary"]["signal"]

    signals = apply_boosts(signals)

    # 写回
    with open(SIGNALS_PATH, "w") as f:
        json.dump(signals, f, indent=2, ensure_ascii=False)

    boosted = signals["summary"]["_enrich_boosted"]
    upgraded = signals["summary"]["_enrich_upgraded"]

    print(f"✅ enrich_boost_signals — 完成")
    print(f"   共处理 {len(signals.get('results', []))} 个信号")
    print(f"   enrich加分: {boosted} 个币种")
    print(f"   等级提升: {upgraded} 个（STRONG: {original_strong}→{signals['summary']['strong']}, SIGNAL: {original_signal}→{signals['summary']['signal']}）")

    if boosted > 0:
        for r in signals.get("results", []):
            if r.get("_enrich_boost"):
                print(f"   {r['symbol']}: +{r['_enrich_boost']}pt ({'+'.join(r.get('_enrich_sources', []))}) → {r['level']} (总分{r['total_score']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
