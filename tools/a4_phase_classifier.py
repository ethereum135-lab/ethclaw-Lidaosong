#!/usr/bin/env python3
"""
A4 Phase Classifier — 信号评分后的「快要涨/快要跌」判断层
======================================================
读取 signals.json，对每个币分类生命周期阶段（phase）和操作建议（action）。
不修改原信号评分逻辑，在信号之上加一层解读。

输出：data/phase_analysis.json（供A4读取决策）

阶段分类：
  - just_starting  （刚启动 → BUY_READY）快要涨
  - trending       （趋势中 → HOLD）
  - peaking        （见顶 → SELL_NOW）快要跌
  - declining      （下跌中 → AVOID）
  - consolidating  （横盘蓄力 → WATCH）
  - skipped        （跳过，无信号）

标签联动（扩展）：
  - 后续可从 coin_pool 读 A7/A8 标签，为 just_starting 增加置信度
"""

import json
import os
import sys
from datetime import datetime

# === CONFIG ===
SIGNALS_PATH = os.path.expanduser(
    "~/zq_web4_trading_system/data/signals.json"
)
OUTPUT_PATH = os.path.expanduser(
    "~/zq_web4_trading_system/data/phase_analysis.json"
)
COIN_POOL_PATH = os.path.expanduser(
    "~/zq_web4_trading_system/data/coin_pool.json"
)


def parse_trend_detail(detail: str) -> dict:
    """Parse '15m↑, 1h↑, 4h↑' → {15m: 'up', 1h: 'up', 4h: 'up'}"""
    result = {}
    parts = detail.replace(" ", "").split(",")
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # e.g. "15m↑", "1h↓", "4h→"
        if "↑" in p:
            tf = p.replace("↑", "")
            result[tf] = "up"
        elif "↓" in p:
            tf = p.replace("↓", "")
            result[tf] = "down"
        elif "→" in p:
            tf = p.replace("→", "")
            result[tf] = "flat"
    return result


def parse_momentum_3h(detail: str):
    """Extract 3h change from momentum_surge detail e.g. '3h+8.5%'"""
    import re
    m = re.search(r"3h([+-]\d+\.?\d*)%", detail)
    if m:
        return float(m.group(1))
    return None


def classify_coin(coin: dict, tags: dict = None) -> dict:
    """
    Classify a single coin's lifecycle phase.
    Returns {"phase": str, "action": str, "confidence": int, "reason": str}
    """
    gain = coin.get("gain_24h", 0) or 0
    level = coin.get("level", "")
    total_score = coin.get("total_score", 0) or 0
    signals = coin.get("signals", {})
    volume_24h = coin.get("volume_24h", 0) or 0

    # Signal scores
    ms = signals.get("momentum_surge", {})
    ms_score = ms.get("score", 0) or 0
    ms_detail = ms.get("detail", "") or ""

    vb = signals.get("vol_breakout", {})
    vb_score = vb.get("score", 0) or 0

    rsi = signals.get("rsi_recovery", {})
    rsi_score = rsi.get("score", 0) or 0
    rsi_detail = rsi.get("detail", "") or ""

    indep = signals.get("independent_up", {})
    indep_score = indep.get("score", 0) or 0

    ta = signals.get("trend_alignment", {})
    ta_score = ta.get("score", 0) or 0
    ta_detail = ta.get("detail", "") or ""

    vt = signals.get("volume_trend", {})
    vt_score = vt.get("score", 0) or 0

    # Parse trend directions
    trend_dirs = parse_trend_detail(ta_detail)
    up_count = sum(1 for d in trend_dirs.values() if d == "up")
    down_count = sum(1 for d in trend_dirs.values() if d == "down")
    flat_count = sum(1 for d in trend_dirs.values() if d == "flat")

    # Check 3h momentum direction
    _3h_change = parse_momentum_3h(ms_detail)
    _3h_rising = _3h_change is not None and _3h_change > 0

    # Volume check (minimum $100k for meaningful analysis)
    has_volume = volume_24h >= 100000
    volume_clause = "有量" if has_volume else "量低"

    # ============ DECISION TREE ============

    # Low score / no signal → skip (但保留已跌20-30%的币供oversold_bounce判定)
    if total_score < 15 or level in ("PASS", "ERROR"):
        # 检查是否在超卖区间 — 跌15-30%的币即使总分低也要保留判定
        if -30 <= gain <= -15:
            pass  # 不skip，进入oversold_bounce判定
        else:
            return {"phase": "skipped", "action": "SKIP",
                    "confidence": 1, "reason": f"无信号(score={total_score})"}

    # ——— OVERSOLD BOUNCE (超卖反弹→快要涨) ———
    # B策略：跌20-30% + RSI见底回升 + 缩量止跌 + 有叙事 → 抄底
    # 必须在PEAKING之前，确保超卖币不被Sell Guard误拦截
    # 2026-06-10 新增(B策略)

    if -30 <= gain <= -15:
        symbol = coin.get("symbol", "").upper()
        coin_tags = tags.get(symbol, {}) if tags else {}
        has_tags = bool(coin_tags)

        # 🔴 退市风险检查：跌得狠+成交量极低=可能是退市/归零币，不是抄底机会
        # 规则：跌>15% + 24h成交量<$200K → 疑似退市/流动性枯竭，不抄底
        volume_24h = coin.get("volume_24h", 0) or 0
        if volume_24h < 200000:
            return {"phase": "declining", "action": "AVOID",
                    "confidence": 5,
                    "reason": f"下跌{gain:.1f}%+成交量${volume_24h:.0f}<$200K疑似退市/流动性枯竭 🔴"}

        # RSI从超卖区回升（从<30回到30-50）是见底信号
        rsi_recovering = rsi_score > 0

        # 量比<0.7 = 卖盘衰竭（恐慌盘出清后缩量）
        volume_ratio = coin.get("volume_ratio_24h", 1.0) or 1.0
        volume_exhausted = volume_ratio < 0.7

        # 短周期止跌：15m/1h不是全部↓（至少flat或up）
        trend_stabilizing = down_count < 3 and up_count >= 1

        # 跌得多但成交量极低（没人卖了）
        extreme_volume_exhaustion = volume_ratio < 0.4

        # 最高置信：RSI回升+缩量+趋势止跌+有叙事
        if rsi_recovering and (volume_exhausted or trend_stabilizing):
            confidence = 7
            reasons = [f"超卖反弹{gain:.1f}%"]
            if rsi_recovering:
                reasons.append(f"RSI回升{rsi_detail}")
            if volume_exhausted:
                reasons.append(f"缩量(量比{volume_ratio:.1f}x)")
            if trend_stabilizing:
                reasons.append(f"短周期止跌{ta_detail}")
            if has_tags:
                confidence += 1
                reasons.append("有叙事")

            conf = min(9, confidence)
            return {"phase": "oversold_bounce", "action": "BUY_READY",
                    "confidence": conf,
                    "reason": "+".join(reasons) + " 📉→📈"}

        # 中等置信：跌够但只有部分信号
        if extreme_volume_exhaustion:
            return {"phase": "oversold_bounce", "action": "BUY_READY",
                    "confidence": 6,
                    "reason": f"超卖反弹{gain:.1f}%+极度缩量(量比{volume_ratio:.2f}x)卖盘枯竭 📉→📈"}

    # ——— PEAKING (已泵顶/见顶→快要跌) ———

    # Rule 1: 已泵顶 — gain ≥ 40%
    # 这个规则保留：>40%就是已泵顶，不管什么信号都要出
    if gain >= 40:
        return {"phase": "peaking", "action": "SELL_NOW",
                "confidence": 9, "reason": f"已泵顶+{gain:.1f}% 🔴"}

    # —— 警卫条款：SELL_NOW前交叉验证（2026-06-06新增） ——
    # 防止POND教训：短周期回调+涨幅5-15%但A3高信号、3h仍在涨→误判为见顶
    # 以下条件任一满足则SELL_NOW降级为WATCH：
    #  ① A3 level=STRONG或SIGNAL → 高信号说明仍有上涨动能
    #  ② total_score≥50 → 综合评分高，不应因短周期回调就清
    #  ③ 3h动量仍在上升（_3h_rising=True）→ 短回调不是见顶
    #  ④ 低成交量回调（量比<0.7x）→ 缩量回调=正常蓄力
    should_guard_sell = False
    guard_reasons = []
    if down_count >= 1:
        if level in ("STRONG", "SIGNAL"):
            should_guard_sell = True
            guard_reasons.append(f"A3_{level}")
        if total_score >= 50:
            should_guard_sell = True
            guard_reasons.append(f"总分{total_score}")
        if _3h_rising and _3h_change is not None:
            should_guard_sell = True
            guard_reasons.append(f"3h仍涨{_3h_change:+.1f}%")
        # 缩量回调：量比<0.7x → 不是出货
        volume_ratio = coin.get("volume_ratio_24h", 1.0) or 1.0
        if volume_ratio < 0.7:
            should_guard_sell = True
            guard_reasons.append(f"缩量(量比{volume_ratio:.1f}x)")

    # Rule 2: 见顶回调 — 短周期已转跌(15m↓或1h↓) + 之前涨过
    # 这是POND模式：24h还正但短线已跌
    if down_count >= 1:
        if gain > 15:
            # 警卫：高信号/3h仍涨/缩量回调 → 降级WATCH
            if should_guard_sell:
                return {"phase": "trending", "action": "WATCH",
                        "confidence": 6,
                        "reason": f"涨幅{gain:.1f}%+短转跌但{', '.join(guard_reasons)}，蓄力回调不追卖 🔵"}
            return {"phase": "peaking", "action": "SELL_NOW",
                    "confidence": 8, "reason": f"涨幅{gain:.1f}%+短周期{ta_detail}见顶回调 ⚠️"}
        elif gain > 5:
            # 警卫：高信号/3h仍涨/缩量回调 → 降级WATCH
            if should_guard_sell:
                return {"phase": "trending", "action": "WATCH",
                        "confidence": 6,
                        "reason": f"涨幅{gain:.1f}%+短转跌但{', '.join(guard_reasons)}，正常回调不追卖 🔵"}
            return {"phase": "peaking", "action": "SELL_NOW",
                    "confidence": 7, "reason": f"涨幅{gain:.1f}%+短周期转跌{ta_detail} ⚠️"}
        elif rsi_score == 0 and indep_score == 0:
            # 短线跌+无正面信号=真弱
            return {"phase": "declining", "action": "AVOID",
                    "confidence": 6, "reason": f"短周期跌{ta_detail}+无正面信号"}
        else:
            # 短线跌但有RSI恢复/独立上涨信号→可能是震荡
            return {"phase": "consolidating", "action": "WATCH",
                    "confidence": 4, "reason": f"短周期跌但有恢复信号{ta_detail}"}

    # ——— FUZZY ZONE (15-40% — NAVIGATION.md §3模糊区处理) ———
    # 策略：趋势中+量健康+有标签 → BUY_READY(7.5%试探)
    #       趋势中+量健康+无标签 → WATCH(等标签确认)
    #       趋势中+量偏弱 → WATCH(等回调)

    if 15 < gain < 40 and down_count == 0:
        coin_symbol = coin.get("symbol", "").upper()
        coin_tags = tags.get(coin_symbol, {}) if tags else {}
        volume_ratio = coin.get("volume_ratio_24h", 1.0) or 1.0
        has_good_volume = vb_score > 0 or volume_ratio >= 1.5
        has_tags = bool(coin_tags)

        if has_good_volume and has_tags:
            return {"phase": "trending", "action": "BUY_READY",
                    "confidence": 6,
                    "reason": f"趋势加速{gain:.1f}%+量健康+标签验证，USDT×7.5%试探 🟡"}
        elif has_good_volume:
            return {"phase": "trending", "action": "WATCH",
                    "confidence": 5,
                    "reason": f"趋势{gain:.1f}%+量健康，等标签确认 🔵"}
        else:
            return {"phase": "trending", "action": "WATCH",
                    "confidence": 4,
                    "reason": f"趋势{gain:.1f}%但量偏弱，等回调 🔵"}

    # ——— JUST STARTING (刚启动→快要涨) ———

    # Rule 3: 刚启动 — 涨幅3-15% + 放量 + 趋势向上(↓数=0)
    # 2026-06-06 fix: STRONG/SIGNAL高分币(≥50)免除成交量门槛
    # MDX(+13.5%,57分)和WAVES(+12%,50分)有动量+趋势但vb=0→被卡
    has_strong_signals = level in ("STRONG", "SIGNAL") and total_score >= 50
    has_volume_signal = vb_score > 0 or has_strong_signals
    if 3 <= gain <= 15:
        if down_count == 0 and has_volume_signal:
            # 3h动量检查：防止「上午涨了下午跌了」的假刚启动
            # 如果24h涨但最近3h在跌→可能是拉升末端，不是真刚启动
            _3h_direction_ok = _3h_rising if _3h_change is not None else True

            if not _3h_direction_ok:
                # 最近3h在跌→可能是拉升末端
                # 除非有A7/A8标签支撑，否则降级为WATCH
                return {"phase": "consolidating", "action": "WATCH",
                        "confidence": 5,
                        "reason": f"刚启动{gain:.1f}%+放量但3h近期方向转负({_3h_change:+.1f}%)，等方向恢复 🔵"}

            # 最佳：放量+趋势向上+RSI回升
            if rsi_score > 0:
                conf = 9 if ms_score >= 15 else 8
                return {"phase": "just_starting", "action": "BUY_READY",
                        "confidence": conf,
                        "reason": f"刚启动{gain:.1f}%+放量+趋势向上+RSI回升 🟢"}
            else:
                return {"phase": "just_starting", "action": "BUY_READY",
                        "confidence": 7,
                        "reason": f"刚启动{gain:.1f}%+放量+趋势向上 🟢"}
        elif down_count == 0:
            # 涨幅适中+趋势向上但无明显放量
            return {"phase": "just_starting", "action": "WATCH",
                    "confidence": 6,
                    "reason": f"涨幅{gain:.1f}%+趋势向上(量偏弱)，等放量确认 🔵"}

    # ——— CONSOLIDATING (蓄力)—RSI回升+放量，等待突破 ———

    # Rule 4: 蓄力待发 — gain 0-5% + RSI回升 + 放量
    if -5 <= gain <= 5 and down_count == 0:
        if rsi_score > 0 and vb_score > 0:
            return {"phase": "consolidating", "action": "BUY_READY",
                    "confidence": 7,
                    "reason": f"蓄力{gain:.1f}%+RSI回升{rsi_detail}+放量 🔵"}
        elif rsi_score > 0:
            return {"phase": "consolidating", "action": "WATCH",
                    "confidence": 5,
                    "reason": f"蓄力{gain:.1f}%+RSI回升{rsi_detail}，等放量"}
        elif vb_score > 0:
            return {"phase": "consolidating", "action": "WATCH",
                    "confidence": 5,
                    "reason": f"蓄力{gain:.1f}%+放量，等趋势确认"}

    # ——— TRENDING (趋势中→持有) ———

    # Rule 5: 趋势中 — 多周期向上+放量+涨幅>0
    if up_count >= 2 and vb_score > 0 and gain > 0:
        if 5 <= gain <= 20:
            return {"phase": "trending", "action": "HOLD",
                    "confidence": 7,
                    "reason": f"趋势中{gain:.1f}%+多周期向上+放量 ✅"}
        elif gain > 20:
            return {"phase": "trending", "action": "HOLD_TIGHT",
                    "confidence": 6,
                    "reason": f"趋势中但涨幅{gain:.1f}%已高，随时准备止盈 ⚡"}

    # Rule 6: 趋势偏弱 — 在涨但信号不强
    if gain > 0 and up_count >= 1:
        return {"phase": "trending", "action": "HOLD",
                "confidence": 4,
                "reason": f"微涨{gain:.1f}%但信号偏弱"}

    # ——— DECLINING (下跌中→远离) ———

    if gain < -3:
        return {"phase": "declining", "action": "AVOID",
                "confidence": 7, "reason": f"下跌{gain:.1f}% 🔴"}

    # Fallback
    return {"phase": "unknown", "action": "WATCH",
            "confidence": 2, "reason": f"无法分类(gain={gain:.1f}%, score={total_score})"}


def load_tags_from_coin_pool() -> dict:
    """
    Load A7/A8 tags from coin_pool.json for tag-based confidence boost.
    Tags are stored as: coin.tags._enrich.A7 / coin.tags._enrich.A8
    Returns: { "POND": {"A7_narrative": "DePIN/网络加速Marlin", "A7_sentiment": "positive", "A8_smart_money": True}, ... }
    """
    tags = {}
    if not os.path.exists(COIN_POOL_PATH):
        return tags
    try:
        with open(COIN_POOL_PATH) as f:
            pool_data = json.load(f)
        pool = pool_data.get("pool", []) if isinstance(pool_data, dict) else pool_data
        if not isinstance(pool, list):
            return tags

        for coin in pool:
            if not isinstance(coin, dict):
                continue
            sym = (coin.get("symbol") or "").upper()
            if not sym:
                continue

            enrich = coin.get("tags", {}).get("_enrich", {})
            if not enrich:
                continue

            coin_tags = {}

            # A7 tags
            a7 = enrich.get("A7", {})
            if a7:
                coin_tags["A7_sentiment"] = a7.get("sentiment", "")
                coin_tags["A7_narrative"] = a7.get("narrative", "")
                coin_tags["A7_alert"] = a7.get("alert_level", "")

            # A8 tags
            a8 = enrich.get("A8", {})
            if a8:
                coin_tags["A8_smart_money"] = a8.get("smart_money_signal", False)
                coin_tags["A8_source"] = a8.get("source", "")

            if coin_tags:
                tags[sym] = coin_tags

    except Exception as e:
        print(f"  ⚠️ 读coin_pool标签失败: {e}", file=sys.stderr)
    return tags


def apply_tags_boost(phase_data: dict, symbol: str, tags: dict) -> dict:
    """Boost confidence if coin has recent A7/A8 tags.

    A7: 舆情/叙事标签 → 有叙事支撑的刚启动币更可信
    A8: 聪明钱/大额买入 → 有资金验证的刚启动币更可信
    """
    upper = symbol.upper()
    if upper not in tags:
        return phase_data
    coin_tags = tags[upper]

    # Only boost BUY_READY phase
    if phase_data.get("action") not in ("BUY_READY", "HOLD"):
        return phase_data

    boost = 0
    tag_details = []

    # A7: positive sentiment → +1 confidence
    a7_sentiment = coin_tags.get("A7_sentiment", "")
    a7_narrative = coin_tags.get("A7_narrative", "")
    if a7_sentiment in ("positive", "bullish"):
        boost += 1
        tag_details.append(f"A7:{a7_sentiment}")
    if a7_narrative:
        tag_details.append(f"叙事:{a7_narrative[:30]}")

    # A8: smart money detected → +1 confidence
    a8_smart = coin_tags.get("A8_smart_money", False)
    if a8_smart:
        boost += 1
        tag_details.append("A8:聪明钱")

    if boost > 0:
        phase_data["confidence"] = min(10, phase_data["confidence"] + boost)
        phase_data["tags"] = tag_details
        phase_data["reason"] += f" +标签({'/'.join(tag_details)})"

    return phase_data


def main():
    print("=" * 60)
    print("A4 Phase Classifier — 阶段分类引擎")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Load signals
    if not os.path.exists(SIGNALS_PATH):
        print(f"❌ signals.json 不存在: {SIGNALS_PATH}")
        sys.exit(1)

    with open(SIGNALS_PATH) as f:
        signals = json.load(f)

    results = signals.get("results", [])
    if not results:
        print("❌ signals.json 无 results 数据")
        sys.exit(1)

    print(f"\n📊 输入: {len(results)} 个币的信号数据")
    print(f"   扫描时间: {signals.get('scanned_at', 'unknown')}")

    # Load tags
    tags = load_tags_from_coin_pool()
    print(f"🏷️  已加载 {len(tags)} 个币的标签数据")

    # Classify each coin
    phase_counts = {}
    action_counts = {}
    buy_ready_list = []
    sell_now_list = []

    for coin in results:
        sym = coin.get("symbol", "UNKNOWN")
        phase = classify_coin(coin, tags)

        # Apply tag boost
        phase = apply_tags_boost(phase, sym, tags)

        # Add phase data to coin
        coin["phase_analysis"] = {
            "phase": phase["phase"],
            "action": phase["action"],
            "confidence": phase["confidence"],
            "reason": phase["reason"],
        }
        if "tags" in phase:
            coin["phase_analysis"]["tags"] = phase["tags"]

        # Count
        p = phase["phase"]
        a = phase["action"]
        phase_counts[p] = phase_counts.get(p, 0) + 1
        action_counts[a] = action_counts.get(a, 0) + 1

        if a == "BUY_READY":
            buy_ready_list.append({
                "symbol": sym,
                "gain_24h": coin.get("gain_24h", 0),
                "total_score": coin.get("total_score", 0),
                "level": coin.get("level", ""),
                "phase": p,
                "confidence": phase["confidence"],
                "reason": phase["reason"],
            })

        if a == "SELL_NOW":
            sell_now_list.append({
                "symbol": sym,
                "gain_24h": coin.get("gain_24h", 0),
                "total_score": coin.get("total_score", 0),
                "level": coin.get("level", ""),
                "phase": p,
                "confidence": phase["confidence"],
                "reason": phase["reason"],
            })

    # Sort lists
    buy_ready_list.sort(key=lambda x: x["confidence"], reverse=True)
    sell_now_list.sort(key=lambda x: x["confidence"], reverse=True)

    # Build output
    output = {
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "signals_scanned_at": signals.get("scanned_at", "unknown"),
        "total_analyzed": len(results),
        "phase_summary": {
            "just_starting": phase_counts.get("just_starting", 0),
            "trending": phase_counts.get("trending", 0),
            "peaking": phase_counts.get("peaking", 0),
            "declining": phase_counts.get("declining", 0),
            "consolidating": phase_counts.get("consolidating", 0),
            "skipped": phase_counts.get("skipped", 0),
            "unknown": phase_counts.get("unknown", 0),
        },
        "action_summary": {
            "BUY_READY": action_counts.get("BUY_READY", 0),
            "HOLD": action_counts.get("HOLD", 0),
            "HOLD_TIGHT": action_counts.get("HOLD_TIGHT", 0),
            "SELL_NOW": action_counts.get("SELL_NOW", 0),
            "AVOID": action_counts.get("AVOID", 0),
            "WATCH": action_counts.get("WATCH", 0),
            "SKIP": action_counts.get("SKIP", 0),
        },
        "buy_candidates": buy_ready_list,
        "sell_candidates": sell_now_list,
        "results": results,
    }

    # Write output
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n{'='*60}")
    print("📈 阶段分类汇总")
    print(f"{'='*60}")
    for phase, count in sorted(phase_counts.items()):
        print(f"  {phase:20s}: {count:3d}个")
    print(f"\n🎯 操作建议汇总")
    print(f"{'='*60}")
    for action, count in sorted(action_counts.items()):
        print(f"  {action:15s}: {count:3d}个")

    print(f"\n🟢 快要涨 — BUY_READY（按置信度排序）")
    print(f"{'='*60}")
    for c in buy_ready_list[:15]:
        print(f"  {c['symbol']:10s} | conf={c['confidence']} | gain={c['gain_24h']:.1f}% | score={c['total_score']} | {c['reason']}")

    print(f"\n🔴 快要跌 — SELL_NOW（按置信度排序）")
    print(f"{'='*60}")
    for c in sell_now_list[:15]:
        print(f"  {c['symbol']:10s} | conf={c['confidence']} | gain={c['gain_24h']:.1f}% | score={c['total_score']} | {c['reason']}")

    print(f"\n✅ 输出已写入: {OUTPUT_PATH}")
    print(f"   共{len(results)}个币完成阶段分类")


if __name__ == "__main__":
    main()
