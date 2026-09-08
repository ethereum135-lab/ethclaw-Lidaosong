#!/usr/bin/env python3
"""
Quick Buy Scanner — 每5分钟快速扫描
======================================
从 signals.json 读数据（A3每30分钟刷新），判断哪些币"要涨了"。
3个条件全满足就出信号，不做复杂分析。

条件：
1. 24h涨幅 3-15%（刚启动，不是已泵顶）
2. 成交量 > $100K（不是冷门币）
3. total_score >= 40（有信号支撑，不是瞎涨）

输出：data/quick_buy_signals.json（供A4读取）
      data/quick_buy_candidates.md（可读报告）

Mac本地读取，不需要网络请求。
"""

import json
import os
import sys
from datetime import datetime

# === CONFIG ===
BASE_DIR = os.path.expanduser("~/zq_web4_trading_system")
SIGNALS_PATH = os.path.join(BASE_DIR, "data/signals.json")
OUTPUT_JSON = os.path.join(BASE_DIR, "data/quick_buy_signals.json")
OUTPUT_MD = os.path.join(BASE_DIR, "data/quick_buy_candidates.md")
MIN_VOLUME = 100_000  # $100K最低成交量
GAIN_MIN = 3  # 最低涨幅%
GAIN_MAX = 15  # 最高涨幅%
MIN_SCORE = 40  # 最低信号分（替代RSI）
MAX_GAIN_PUMP = 40  # 已泵顶排除线


def main():
    print("=" * 60)
    print(f"🔍 Quick Buy Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Step 1: Read signals.json
    if not os.path.exists(SIGNALS_PATH):
        print(f"❌ 数据源不存在: {SIGNALS_PATH}")
        sys.exit(1)

    with open(SIGNALS_PATH) as f:
        signals = json.load(f)

    results = signals.get("results", [])
    scanned_at = signals.get("scanned_at", "unknown")
    print(f"\n📡 数据源: signals.json (扫描时间: {scanned_at})")
    print(f"   共 {len(results)} 个币")

    # Step 2: Filter
    candidates = []
    excluded_pump = 0
    excluded_no_volume = 0
    excluded_low_score = 0

    for coin in results:
        sym = coin.get("symbol", "")
        gain = coin.get("gain_24h", 0) or 0
        volume = coin.get("volume_24h", 0) or 0
        score = coin.get("total_score", 0) or 0
        level = coin.get("level", "")
        price = coin.get("price", 0) or 0

        # 排除已泵顶
        if gain >= MAX_GAIN_PUMP:
            excluded_pump += 1
            continue

        # 涨幅3-15%
        if gain < GAIN_MIN or gain > GAIN_MAX:
            continue

        # 有成交量
        if volume < MIN_VOLUME:
            excluded_no_volume += 1
            continue

        # 有信号支撑（替代RSI）
        if score < MIN_SCORE and level not in ("STRONG", "SIGNAL"):
            excluded_low_score += 1
            continue

        candidates.append({
            "symbol": sym + "USDT",
            "gain_24h": round(gain, 1),
            "volume_24h": round(volume, 0),
            "price": price,
            "score": score,
            "level": level,
        })

    candidates.sort(key=lambda x: x["gain_24h"], reverse=True)

    print(f"\n   筛选结果:")
    print(f"   已泵顶排除(>40%): {excluded_pump}")
    print(f"   量不足排除(<$100K): {excluded_no_volume}")
    print(f"   分低排除(<40): {excluded_low_score}")
    print(f"   ✅ 快速建仓候选: {len(candidates)} 个")

    # Step 3: Write output
    buy_signals = []
    for c in candidates:
        buy_signals.append({
            "symbol": c["symbol"],
            "gain_24h": c["gain_24h"],
            "volume_24h": c["volume_24h"],
            "price": c["price"],
            "score": c["score"],
            "level": c["level"],
            "action": "BUY",
            "reason": f"快涨{c['gain_24h']:+.1f}%+量${c['volume_24h']:.0f}+分{c['score']}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_age": scanned_at,
        })

    output = {
        "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": "signals.json",
        "data_age": scanned_at,
        "total_screened": len(results),
        "buy_signals": buy_signals[:10],
        "message": f"{len(buy_signals)} 个快速建仓候选" if buy_signals else "无候选"
    }

    json.dump(output, open(OUTPUT_JSON, "w"), indent=2)

    with open(OUTPUT_MD, "w") as f:
        f.write(f"# 🔍 Quick Buy Scan — {output['scanned_at']}\n\n")
        f.write(f"数据来源: signals.json ({scanned_at})\n\n")
        if buy_signals:
            f.write("## 🟢 快速建仓候选\n\n")
            f.write("| 币种 | 涨幅 | 成交量 | 价格 | 分 |\n")
            f.write("|:----|:----:|:-----:|:---:|:-:|\n")
            for s in buy_signals:
                f.write(f"| {s['symbol']} | {s['gain_24h']:+.1f}% | ${s['volume_24h']:.0f} | ${s['price']} | {s['score']} |\n")
        else:
            f.write("当前无符合条件的快速建仓候选\n")

    print(f"\n{'='*60}")
    print(f"✅ 快速建仓候选: {len(buy_signals)} 个")
    for s in buy_signals[:5]:
        print(f"   {s['symbol']:12s} | gain={s['gain_24h']:+.1f}% | vol=${s['volume_24h']:.0f} | score={s['score']}")
    print(f"\n📄 {OUTPUT_JSON}")
    print(f"📄 {OUTPUT_MD}")


if __name__ == "__main__":
    main()
