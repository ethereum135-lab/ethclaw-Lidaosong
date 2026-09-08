#!/usr/bin/env python3
"""
实时将A3信号扫描器gainer supplement中SIGNAL+(≥25分)的币注入精选池。

问题：A2精选池每天05:30重建，但白天新冲出来的币（通过A3的gainer supplement通道
识别为SIGNAL/STRONG）要等第二天才进池，错过24小时交易窗口。

修复：每次信号扫描后运行此脚本，将高评分非池币注入coin_pool_binance.json，
A4下一周期就能看到并交易。

用法：
  python3 tools/inject_gainer_to_pool.py
  python3 tools/inject_gainer_to_pool.py --dry-run   # 模拟运行，不实际写入
  python3 tools/inject_gainer_to_pool.py --min-score 40  # 自定义注入阈值（默认25=SIGNAL底线）
"""

import json
import os
import sys
import copy
from datetime import datetime

# 路径
ZQ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) or "/Users/lidaosong/zq_web4_trading_system"
SIGNALS_PATH = os.path.join(ZQ_ROOT, "data", "signals.json")
POOL_PATH = os.path.join(ZQ_ROOT, "data", "coin_pool_binance.json")  # 原coin_pool_prime.json→改名, 2026-06-14
MAIN_POOL_PATH = os.path.join(ZQ_ROOT, "data", "coin_pool.json")

# 注入阈值：SIGNAL底线分
MIN_SCORE = 25

def load_json(path, label):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ 无法读取{label}: {e}")
        return None

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ 已写入 {path}")

def main():
    dry_run = "--dry-run" in sys.argv
    global MIN_SCORE
    for i, arg in enumerate(sys.argv):
        if arg.startswith("--min-score="):
            MIN_SCORE = int(arg.split("=")[1])
    
    print(f"=== Gainer Supplement → 精选池注入器 ===")
    print(f"阈值: ≥{MIN_SCORE}分 | 模式: {'DRY-RUN（不写文件）' if dry_run else '实际写入'}")
    
    # 读signals.json
    sig = load_json(SIGNALS_PATH, "signals.json")
    if sig is None:
        return 1
    results = sig.get("results", [])
    
    # 读精选池
    pool_data = load_json(POOL_PATH, "coin_pool_binance.json")
    if pool_data is None:
        return 1

    pool = pool_data.get("pool", [])
    pool_symbols = [c.get("symbol", "").upper() for c in pool]
    pool_updated = False
    
    # 找gainer supplement中SIGNAL+且不在池的币
    candidates = []
    for r in results:
        if not r.get("_gainer_supplement"):
            continue
        sym = r.get("symbol", "").upper()
        score = r.get("total_score", 0)
        level = r.get("level", "PASS")
        if score >= MIN_SCORE:
            if sym not in pool_symbols:
                candidates.append(r)
    
    if not candidates:
        print(f"\n✅ 无需要注入的币。当前gainer supplement中≥{MIN_SCORE}分的币全部已在池中。")
        if dry_run:
            print("（未做任何修改）")
        return 0
    
    print(f"\n🔍 发现 {len(candidates)} 个需注入的币：")
    
    for r in sorted(candidates, key=lambda x: -x.get("total_score", 0)):
        sym = r["symbol"].upper()
        score = r.get("total_score", 0)
        level = r.get("level", "PASS")
        price = r.get("price", r.get("current_price", 0))
        vol = r.get("volume_24h", r.get("volume_24h_usd", 0))
        change = r.get("gain_24h", r.get("change_24h", 0))
        
        # 推测赛道（从tag或全量池查）
        category = r.get("category", r.get("tag", "other"))
        
        # 构建pool条目
        entry = {
            "symbol": sym,
            "volume_24h_usd": vol,
            "change_24h": change,
            "price": price,
            "volume_change_24h": 0,
            "category": category,
            "status": "active",
            "_gainer_entry": True,
            "_gainer_supplement_injected": True,
            "_composite_score": score
        }
        pool.append(entry)
        pool_symbols.append(sym)
        
        print(f"  📥 {sym:8s} {score:3d}分 {level:>8s} +{change:+.1f}% | vol=${vol:,.0f} | 赛道={category}")
    
    # 更新元数据
    pool_data["pool"] = pool
    pool_data["total_prime"] = len(pool)
    pool_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "gainer_core" in pool_data and isinstance(pool_data["gainer_core"], list):
        pool_data["gainer_core"] = list(set(pool_data["gainer_core"] + [r["symbol"].upper() for r in candidates]))
    
    print(f"\n📊 精选池大小: {len(pool)} (注入后)")
    
    if dry_run:
        print("（--dry-run，未实际写入）")
    else:
        save_json(POOL_PATH, pool_data)
        
        # ── 同步注入的币到主池 coin_pool.json ──
        main_data = load_json(MAIN_POOL_PATH, "coin_pool.json")
        if main_data is not None:
            main_pool = main_data.get("pool", [])
            main_symbols = [c.get("symbol", "").upper() for c in main_pool]
            main_updated = False
            for r in candidates:
                sym = r["symbol"].upper()
                if sym not in main_symbols:
                    entry = {
                        "symbol": sym,
                        "volume_24h_usd": r.get("volume_24h", r.get("volume_24h_usd", 0)),
                        "change_24h": r.get("gain_24h", r.get("change_24h", 0)),
                        "price": r.get("price", r.get("current_price", 0)),
                        "rank": None,
                        "category": r.get("category", r.get("tag", "other")),
                        "last_scored": None,
                        "status": "active",
                        "warnings": [],
                        "history": [],
                        "_gainer_injected": True
                    }
                    main_pool.append(entry)
                    main_symbols.append(sym)
                    main_updated = True
                    print(f"  📥 同步到主池: {sym}")
            if main_updated:
                main_data["pool"] = main_pool
                main_data["total_coins"] = len(main_pool)
                main_data["total_active"] = len([c for c in main_pool if c.get("status") == "active"])
                main_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_json(MAIN_POOL_PATH, main_data)
        
        print("🚀 下次A4周期即可交易这些币")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
