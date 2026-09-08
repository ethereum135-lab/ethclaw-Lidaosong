#!/usr/bin/env python3
"""
Binance Smart Signal 数据采集器
======================
通过SOCKS5代理，定时采集Binance Futures的聪明钱信号数据。
数据源: https://www.binance.com/bapi/futures/v1/public/future/smart-money/signal/overview

作用：
1. 采集每个交易对的多空比、鲸鱼平均入场价、盈利比例
2. 分析聪明钱的多空倾向和盈亏状态
3. 给A3评分时做参考，A4执行时做辅助判断（如：聪明钱在某个价位大量做多 → 支撑位参考）

输出: data/smart_signal/snapshot.json（每次运行覆盖）
      data/smart_signal/history/YYYY-MM-DD.jsonl（累积历史）

部署: cron每15分钟运行（no_agent=true模式，正常静默，故障才出声）
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

PROXY = "socks5-hostname://127.0.0.1:1080"
BASE_URL = "https://www.binance.com/bapi/futures/v1/public/future/smart-money/signal/overview"

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(WORK_DIR, "data", "smart_signal")
HISTORY_DIR = os.path.join(OUTPUT_DIR, "history")
SNAPSHOT_PATH = os.path.join(OUTPUT_DIR, "snapshot.json")

# 需要监控的币种列表（从系统信号和持仓自动更新）
def curl_smart_signal(symbol: str):
    """查询单个币种的Smart Signal数据 — 直连优先，SOCKS5回退"""
    url = f"{BASE_URL}?symbol={symbol}"
    headers = ["-H", "User-Agent: Mozilla/5.0"]
    
    # 尝试直连
    cmd = ["curl", "-sS", "--connect-timeout", "8", "--max-time", "15"] + headers + [url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode != 0:
            # 回退：SOCKS5代理
            cmd_socks = ["curl", "-sS", "--socks5-hostname", "127.0.0.1:1080",
                         "--connect-timeout", "8", "--max-time", "15"] + headers + [url]
            result = subprocess.run(cmd_socks, capture_output=True, text=True, timeout=20)
            if result.returncode != 0:
                return {"symbol": symbol, "error": f"curl_exit_{result.returncode}", "stderr": result.stderr[:200]}
        
        data = json.loads(result.stdout)
        if data.get("code") != "000000":
            return {"symbol": symbol, "error": f"api_code_{data.get('code')}", "message": data.get("message")}
        
        raw = data["data"]
        
        # 计算盈利分析
        long_profit_pct = round(raw["longProfitTraders"] / max(raw["longTraders"], 1) * 100, 1)
        short_profit_pct = round(raw["shortProfitTraders"] / max(raw["shortTraders"], 1) * 100, 1)
        whale_long_profit_pct = round(raw["longProfitWhales"] / max(raw["longWhales"], 1) * 100, 1)
        whale_short_profit_pct = round(raw["shortProfitWhales"] / max(raw["shortWhales"], 1) * 100, 1)
        
        # 判断聪明钱倾向
        whale_ratio = raw["longShortRatio"]
        if whale_long_profit_pct > 60 and whale_short_profit_pct < 40:
            whale_bias = "BULLISH"  # 多头鲸鱼大部分盈利
        elif whale_short_profit_pct > 60 and whale_long_profit_pct < 40:
            whale_bias = "BEARISH"  # 空头鲸鱼大部分盈利
        elif whale_long_profit_pct > 50 and whale_short_profit_pct > 50:
            whale_bias = "DIVERGENT"  # 双方都在盈利（罕见，可能在震荡中各自做波段）
        else:
            whale_bias = "MIXED"
        
        # 入场价分析
        if raw.get("longWhales", 0) > 0 and raw.get("shortWhales", 0) > 0:
            long_entry = raw["longWhalesAvgEntryPrice"]
            short_entry = raw["shortWhalesAvgEntryPrice"]
            # 看鲸鱼入场价格对比
            if short_entry > long_entry:
                # 空头入场价比多头高 → 空头在更高位置做空（逆势）
                entry_structure = "SHORT_AT_TOP"
            elif long_entry > short_entry:
                # 多头入场价比空头高 → 多头在更高位置做多（追涨）
                entry_structure = "LONG_AT_TOP"
            else:
                entry_structure = "EVEN"
        else:
            entry_structure = "INCOMPLETE"
        
        return {
            "symbol": raw["symbol"],
            "timestamp": datetime.now(BJT).isoformat(),
            "totalTraders": raw["totalTraders"],
            "longShortRatio": raw["longShortRatio"],
            "longTraders": raw["longTraders"],
            "shortTraders": raw["shortTraders"],
            "longWhales": raw["longWhales"],
            "longWhalesQty": raw["longWhalesQty"],
            "longWhalesAvgEntryPrice": raw["longWhalesAvgEntryPrice"],
            "shortWhales": raw["shortWhales"],
            "shortWhalesQty": raw["shortWhalesQty"],
            "shortWhalesAvgEntryPrice": raw["shortWhalesAvgEntryPrice"],
            "longProfitTraders": raw["longProfitTraders"],
            "shortProfitTraders": raw["shortProfitTraders"],
            "longProfitWhales": raw["longProfitWhales"],
            "shortProfitWhales": raw["shortProfitWhales"],
            # 分析字段
            "analysis": {
                "longProfitPct": long_profit_pct,
                "shortProfitPct": short_profit_pct,
                "whaleLongProfitPct": whale_long_profit_pct,
                "whaleShortProfitPct": whale_short_profit_pct,
                "whaleBias": whale_bias,
                "entryStructure": entry_structure,
                "whaleDominance": round(raw["longWhalesQty"] / max(raw["totalPositions"] / 100000, 1), 2),
            }
        }
    except subprocess.TimeoutExpired:
        return {"symbol": symbol, "error": "timeout"}
    except json.JSONDecodeError as e:
        return {"symbol": symbol, "error": f"json_decode: {e}"}
    except Exception as e:
        return {"symbol": symbol, "error": str(e)[:200]}


def get_tracked_symbols() -> list[str]:
    """从系统信号中动态获取需要监控的币种"""
    symbols = set()
    
    # 从 signals.json 读取所有币种（加上USDT后缀）
    sig_path = os.path.join(WORK_DIR, "data", "signals.json")
    if os.path.exists(sig_path):
        try:
            with open(sig_path) as f:
                sig = json.load(f)
            for r in sig.get("results", []):
                sym = r.get("symbol", "")
                if sym:
                    # signals.json的symbol不带USDT，Smart Signal需要带
                    symbols.add(sym + "USDT")
                    # 只有已知的高流通量代币才尝试1000前缀
                    KNOWN_1000_TOKENS = {"PEPE", "SHIB", "FLOKI", "BONK", "DOGS", "NEIRO", "TURBO"}
                    if sym in KNOWN_1000_TOKENS:
                        symbols.add("1000" + sym + "USDT")
        except Exception:
            pass
    
    # 再加默认的大市值币（始终监控市场风向）
    DEFAULT_LARGE_CAPS = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT",
        "1000PEPEUSDT", "BNBUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT",
        "SUIUSDT", "OPUSDT", "DOTUSDT", "ATOMUSDT", "WLDUSDT",
        "NEARUSDT", "APTUSDT", "ARBUSDT", "TIAUSDT", "FILUSDT",
    ]
    for s in DEFAULT_LARGE_CAPS:
        symbols.add(s)
    
    return sorted(symbols)


def main():
    os.makedirs(HISTORY_DIR, exist_ok=True)
    
    symbols = get_tracked_symbols()
    print(f"[SmartSignal] 开始采集 {len(symbols)} 个币种（并行8线程）...")
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    results = []
    errors = []
    completed = 0
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(curl_smart_signal, sym): sym for sym in symbols}
        for future in as_completed(future_map):
            sym = future_map[future]
            completed += 1
            try:
                result = future.result()
                if "error" in result:
                    errors.append(result)
                    print(f"  [{completed}/{len(symbols)}] {sym} ❌ {result['error']}")
                else:
                    results.append(result)
                    bias = result["analysis"]["whaleBias"]
                    long_pct = result["analysis"]["whaleLongProfitPct"]
                    short_pct = result["analysis"]["whaleShortProfitPct"]
                    print(f"  [{completed}/{len(symbols)}] {sym} ✅ 多空比={result['longShortRatio']} 多头盈利={long_pct}% 空头盈利={short_pct}% 倾向={bias}")
            except Exception as e:
                errors.append({"symbol": sym, "error": str(e)[:200]})
                print(f"  [{completed}/{len(symbols)}] {sym} ❌ {e}")
    
    snapshot = {
        "timestamp": datetime.now(BJT).isoformat(),
        "symbols_queried": len(symbols),
        "symbols_success": len(results),
        "symbols_error": len(errors),
        "data": results,
        "errors": errors[:5],  # 只保留前5个错误避免文件过大
    }
    
    # 写入快照
    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    
    # 追加到历史
    history_file = os.path.join(HISTORY_DIR, f"{datetime.now(BJT).strftime('%Y-%m-%d')}.jsonl")
    record = {
        "timestamp": datetime.now(BJT).isoformat(),
        "symbols_queried": len(symbols),
        "symbols_success": len(results),
        "symbols_error": len(errors),
        "summary": {
            sym: {
                "lsr": r.get("longShortRatio"),
                "wb": r.get("analysis", {}).get("whaleBias"),
                "lwp": r.get("analysis", {}).get("whaleLongProfitPct"),
                "swp": r.get("analysis", {}).get("whaleShortProfitPct"),
            }
            for r in results
            if (sym := r.get("symbol"))
        }
    }
    with open(history_file, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"\n[SmartSignal] ✅ 完成: {len(results)}/{len(symbols)} 成功, 快照→{SNAPSHOT_PATH}")
    
    # 如果有错误，输出到stderr用于cron告警
    if errors and len(errors) == len(symbols):
        print(f"[SmartSignal] ⚠️ 全部失败: {len(errors)}/{len(symbols)}", file=sys.stderr)
        sys.exit(1)
    elif errors:
        print(f"[SmartSignal] ⚠️ 部分失败: {len(errors)}/{len(symbols)}", file=sys.stderr)
        print(f"  错误币种: {[e['symbol'] for e in errors[:5]]}", file=sys.stderr)


if __name__ == "__main__":
    main()
