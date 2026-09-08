#!/usr/bin/env python3
"""
Smart Signal → signals.json 注入器 v2
把聪明钱数据注入到signals.json的每个对应币条目中。
signals.json里的symbol不带USDT后缀（如"PORTAL"），
Smart Signal里的symbol带USDT后缀（如"PORTALUSDT"），自动匹配。
"""
import json, os

WORK_DIR = "/Users/lidaosong/zq_web4_trading_system"
SIG_PATH = os.path.join(WORK_DIR, "data", "signals.json")
SS_PATH = os.path.join(WORK_DIR, "data", "smart_signal", "snapshot.json")

# 读取Smart Signal快照
if not os.path.exists(SS_PATH):
    print("[SS→A3] snapshot不存在，跳过")
    exit(0)
ss = json.load(open(SS_PATH))

# 建立 symbol→data 映射（去掉USDT后缀匹配）
ss_map = {}
for d in ss.get("data", []):
    sym_full = d.get("symbol", "")
    if not sym_full or "error" in d:
        continue
    sym_short = sym_full.replace("1000", "").replace("USDT", "")
    ss_map[sym_short] = d
    # 也保留完整带USDT的key
    ss_map[sym_full] = d

# 读取signals.json
sig = json.load(open(SIG_PATH))
injected = 0
for r in sig.get("results", []):
    sym = r.get("symbol", "")
    if not sym:
        continue
    
    # 尝试匹配（短名、长名、1000前缀）
    ss_data = ss_map.get(sym) or ss_map.get(sym + "USDT") or ss_map.get("1000" + sym + "USDT")
    if not ss_data:
        continue
    
    analysis = ss_data.get("analysis", {})
    
    # 生成简单信号
    lwp = analysis.get("whaleLongProfitPct", 0)
    swp = analysis.get("whaleShortProfitPct", 0)
    
    if lwp >= 70 and swp <= 30:
        direction = "BUY"  # 聪明钱看涨
    elif swp >= 70 and lwp <= 30:
        direction = "SELL"  # 聪明钱看跌
    elif lwp > swp:
        direction = "BIAS_LONG"
    elif swp > lwp:
        direction = "BIAS_SHORT"
    else:
        direction = "NEUTRAL"
    
    r["smart_signal"] = {
        "direction": direction,
        "whaleLongProfitPct": lwp,
        "whaleShortProfitPct": swp,
        "longShortRatio": ss_data.get("longShortRatio"),
        "longWhalesAvgEntry": ss_data.get("longWhalesAvgEntryPrice"),
        "shortWhalesAvgEntry": ss_data.get("shortWhalesAvgEntryPrice"),
        "timestamp": ss_data.get("timestamp"),
    }
    injected += 1

# 更新summary
sig.setdefault("summary", {})["smart_signal_summary"] = {
    "timestamp": list(ss_map.values())[0].get("timestamp") if ss_map else None,
    "symbols_checked": injected,
}

json.dump(sig, open(SIG_PATH, "w"), indent=2, ensure_ascii=False)
print(f"[SS→A3] ✅ 已注入 {injected} 个币的聪明钱信号到 signals.json")

# 输出信号汇总
buys = sum(1 for r in sig.get("results", []) if r.get("smart_signal",{}).get("direction") == "BUY")
sells = sum(1 for r in sig.get("results", []) if r.get("smart_signal",{}).get("direction") == "SELL")
for r in sig.get("results", []):
    ss = r.get("smart_signal", {})
    if ss.get("direction") in ("BUY", "SELL"):
        print(f"  {r['symbol']}: {ss['direction']} (多赚{ss['whaleLongProfitPct']}%空{ss['whaleShortProfitPct']}%)")
