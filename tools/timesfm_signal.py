#!/usr/bin/env python3
"""
TimesFM 2.5 预测信号 — 为ZQ系统提供AI时序预测参考

用法:
  # 单币预测
  python3 tools/timesfm_signal.py BTC
  
  # 批量预测多个币种
  python3 tools/timesfm_signal.py BTC ETH SOL DASH
  
  # 从A2精选池批量预测
  python3 tools/timesfm_signal.py --pool

定位: 补充信号(权重10-20%)，不替代RSI/MACD等核心指标
输出: JSON格式，可直接被其他Agent读取
"""

import json
import sys
import os
import numpy as np
import requests
from datetime import datetime

# 添加timesfm路径
sys.path.insert(0, os.path.expanduser("~/timesfm"))
os.chdir(os.path.expanduser("~/timesfm"))

def get_klines(symbol: str, interval: str = "4h", limit: int = 100) -> np.ndarray:
    """从币安获取K线收盘价"""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit={limit}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
    closes = np.array([float(x[4]) for x in data], dtype=np.float64)
    volumes = np.array([float(x[5]) for x in data], dtype=np.float64)
    highs = np.array([float(x[2]) for x in data], dtype=np.float64)
    lows = np.array([float(x[3]) for x in data], dtype=np.float64)
    return closes, volumes, highs, lows


def load_model():
    """加载TimesFM模型（带缓存）"""
    from timesfm import TimesFM_2p5_200M_torch, ForecastConfig
    import torch
    torch.set_float32_matmul_precision("high")
    
    model = TimesFM_2p5_200M_torch.from_pretrained(
        "google/timesfm-2.5-200m-pytorch"
    )
    model.compile(ForecastConfig(
        max_context=1024,
        max_horizon=256,
        normalize_inputs=True,
        use_continuous_quantile_head=True,
        force_flip_invariance=True,
    ))
    return model


def predict_single(model, closes: np.ndarray, horizon: int = 12) -> dict:
    """对单个币种做预测，返回结构化结果"""
    if len(closes) < 20:
        return {"error": "数据不足", "status": "skipped"}
    
    pts, quants = model.forecast(horizon=horizon, inputs=[closes])
    pred = pts[0]
    
    current_price = float(closes[-1])
    target_price = float(pred[-1])
    change_pct = round((target_price - current_price) / current_price * 100, 2)
    
    # 方向判断
    direction = "up" if change_pct > 0 else "down" if change_pct < 0 else "flat"
    
    # 连续上涨/下跌判断
    rising_streak = sum(1 for i in range(1, len(pred)) if pred[i] > pred[i-1])
    falling_streak = sum(1 for i in range(1, len(pred)) if pred[i] < pred[i-1])
    
    confidence = "high" if abs(change_pct) > 1.0 else "medium" if abs(change_pct) > 0.3 else "low"
    
    return {
        "current_price": round(current_price, 2),
        "target_price": round(target_price, 2),
        "change_pct": change_pct,
        "direction": direction,
        "confidence": confidence,
        "horizon": horizon,
        "timeline_hours": horizon * 4,  # 4h K线
        "rising_streak": rising_streak,
        "falling_streak": falling_streak,
        "prediction_path": [round(float(p), 2) for p in pred],
    }


def load_coin_pool() -> list:
    """从ZQ系统的A2精选池加载币种"""
    pool_path = os.path.expanduser("~/zq_web4_trading_system/data/coin_pool.json")
    if os.path.exists(pool_path):
        with open(pool_path) as f:
            data = json.load(f)
            if isinstance(data, dict) and "coins" in data:
                return data["coins"]
            elif isinstance(data, list):
                return data
    return []


def main():
    # 解析参数
    args = sys.argv[1:]
    use_pool = "--pool" in args
    coins = [a.upper() for a in args if not a.startswith("--")]
    
    if use_pool:
        pool_coins = load_coin_pool()
        if not pool_coins:
            print(json.dumps({"error": "精选池为空", "coins": []}))
            return
        coins = [c.get("symbol", c) if isinstance(c, dict) else c for c in pool_coins]
    
    if not coins:
        print("用法: python3 tools/timesfm_signal.py BTC ETH SOL [--pool]")
        return
    
    # 限制批量数量
    coins = coins[:20]  # 最多20个，避免太慢
    horizon = 12  # 预测12根4h K线=48小时
    
    # 加载模型
    model = load_model()
    
    results = []
    for coin in coins:
        try:
            closes, volumes, highs, lows = get_klines(coin)
            
            # 基础技术指标
            current_price = float(closes[-1])
            price_change_24h = ((closes[-1] - closes[-6]) / closes[-6] * 100) if len(closes) >= 6 else 0
            
            # TimesFM预测
            pred = predict_single(model, closes, horizon=horizon)
            
            # 最近价格波动率
            volatility = float(np.std(closes[-20:]) / np.mean(closes[-20:]) * 100) if len(closes) >= 20 else 0
            
            results.append({
                "symbol": coin,
                "current_price": round(current_price, 4),
                "price_change_24h": round(float(price_change_24h), 2),
                "volatility": round(volatility, 2),
                "timesfm": pred,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        except Exception as e:
            results.append({"symbol": coin, "error": str(e)})
    
    # 按预测涨幅排序
    valid = [r for r in results if "timesfm" in r and r["timesfm"].get("direction") in ("up", "down")]
    valid.sort(key=lambda r: abs(r["timesfm"]["change_pct"]), reverse=True)
    
    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(coins),
        "predicted": len(valid),
        "summary": {
            "up_count": sum(1 for r in valid if r["timesfm"]["direction"] == "up"),
            "down_count": sum(1 for r in valid if r["timesfm"]["direction"] == "down"),
            "avg_change": round(np.mean([r["timesfm"]["change_pct"] for r in valid]), 2) if valid else 0,
        },
        "ranked": valid,  # 按信号强度排序
    }
    
    print(json.dumps(output, ensure_ascii=False, indent=2))
    
    # 保存到ZQ系统数据目录
    out_path = os.path.expanduser("~/zq_web4_trading_system/data/timesfm_signals.json")
    with open(out_path, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n💾 已保存到 {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
