#!/usr/bin/env python3
"""
a3_momentum_scanner.py — A3牛币官专用动量扫描工具
从A2候选池中，用真实K线数据做动量筛选
使用方式：ssh web4 'python3 ~/klines_tool.py <symbol>' 获取精确数据
"""
import json, subprocess, sys, os

def ssh_klines(symbol):
    """Call klines tool on AWS"""
    try:
        cmd = f"ssh web4 'python3 /home/ubuntu/klines_tool.py {symbol}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return None
    except:
        return None

def assess_entry_quality(data):
    """From real K线 data, assess if this is a good entry"""
    if not data:
        return {"decision": "NO_DATA", "score": 0}
    
    multi = data.get("multi_timeframe", {})
    rsi_30m = data.get("rsi_14", 50)
    trend_30m = data.get("trend", 0)
    vol_ratio = data.get("vol_ratio", 0)
    price_pos = data.get("pos_in_range_pct", 50)
    
    # Check multi-timeframe alignment
    tf_scores = []
    for tf_name in ["15m", "1h", "4h"]:
        tf = multi.get(tf_name, {})
        tf_rsi = tf.get("rsi_14", 50)
        tf_trend = tf.get("trend", 0)
        tf_vol = tf.get("vol_ratio", 0)
        
        # Trend alignment score
        trend_score = min(100, max(0, (tf_trend + 2) * 25))
        # RSI zone score (avoid extremes)
        if 30 <= tf_rsi <= 65:
            rsi_score = 100
        elif 20 <= tf_rsi < 30 or 65 < tf_rsi <= 70:
            rsi_score = 60
        else:
            rsi_score = 20
        # Volume score
        vol_score = min(100, max(0, tf_vol * 50))
        
        tf_scores.append({
            "timeframe": tf_name,
            "rsi": tf_rsi,
            "trend": tf_trend,
            "trend_score": trend_score,
            "rsi_score": rsi_score,
            "vol_score": vol_score,
            "composite": round((trend_score * 0.4 + rsi_score * 0.4 + vol_score * 0.2), 1)
        })
    
    # Overall assessment
    avg_trend = sum(tf["trend"] for tf in multi.values()) / max(len(multi), 1)
    avg_rsi = sum(tf["rsi_14"] for tf in multi.values()) / max(len(multi), 1)
    
    # Decision logic
    reasons = []
    signals = []
    
    # 1. Trend alignment: most TFs should be up or at least not down
    up_tfs = sum(1 for tf in multi.values() if tf.get("trend", 0) > 0)
    down_tfs = sum(1 for tf in multi.values() if tf.get("trend", 0) < 0)
    
    if up_tfs >= 2:
        signals.append("BULLISH")
        reasons.append(f"{up_tfs}/{len(multi)} timeframes trending UP")
    elif down_tfs >= 2:
        signals.append("BEARISH")
        reasons.append(f"{down_tfs}/{len(multi)} timeframes trending DOWN")
    else:
        signals.append("NEUTRAL")
        reasons.append("Mixed timeframes")
    
    # 2. RSI zone
    if avg_rsi < 30:
        signals.append("OVERSOLD")
        reasons.append(f"Avg RSI {avg_rsi:.0f} - oversold bounce potential")
    elif avg_rsi > 70:
        signals.append("OVERBOUGHT")
        reasons.append(f"Avg RSI {avg_rsi:.0f} - overbought, wait for pullback")
    else:
        signals.append("NEUTRAL_RSI")
        reasons.append(f"Avg RSI {avg_rsi:.0f} - neutral zone")
    
    # 3. Volume
    avg_vol = sum(tf.get("vol_ratio", 0) for tf in multi.values()) / max(len(multi), 1)
    if avg_vol > 1.5:
        signals.append("HIGH_VOLUME")
        reasons.append(f"Avg vol ratio {avg_vol:.1f}x - active")
    elif avg_vol < 0.5:
        signals.append("LOW_VOLUME")
        reasons.append(f"Avg vol ratio {avg_vol:.1f}x - quiet")
    
    # 4. Price position (buy at pullback, not at peak)
    if 20 <= price_pos <= 70:
        signals.append("GOOD_PRICE_POS")
        reasons.append(f"Price at {price_pos:.0f}% of range - reasonable entry zone")
    elif price_pos > 80:
        signals.append("HIGH_PRICE_POS")
        reasons.append(f"Price at {price_pos:.0f}% - near top of range")
    
    # Final decision
    buy_signals = sum(1 for s in signals if s in ["BULLISH", "OVERSOLD", "GOOD_PRICE_POS", "NEUTRAL_RSI", "HIGH_VOLUME"])
    sell_signals = sum(1 for s in signals if s in ["BEARISH", "OVERBOUGHT", "LOW_VOLUME"])
    
    if buy_signals >= 3 and "BEARISH" not in signals:
        decision = "BUY"
        confidence = min(10, 5 + buy_signals - sell_signals)
    elif "BEARISH" in signals and sell_signals >= 2:
        decision = "WAIT"
        confidence = max(1, 5 - sell_signals)
    else:
        decision = "OBSERVE"
        confidence = 5
    
    return {
        "decision": decision,
        "confidence": confidence,
        "signals": signals,
        "reasons": reasons,
        "avg_rsi": round(avg_rsi, 1),
        "avg_trend": round(avg_trend, 1),
        "timeframe_scores": tf_scores
    }

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AIGENSYNUSDT"
    data = ssh_klines(symbol)
    if data:
        assessment = assess_entry_quality(data)
        print(json.dumps(assessment, indent=2))
    else:
        print(json.dumps({"error": f"Could not fetch data for {symbol}"}))
