#!/usr/bin/env python3
"""
实时动量检查 — 验证一个币最近15分钟(3根5m K线)是否还在涨。
用在A4买入决策之前：如果币的实时动量没了，不管24h评分多高都不买。
—— 这就是"快涨时建仓"的硬验证。
"""
import requests, json, sys, os
from datetime import datetime

BINANCE_API = "https://api.binance.com"

# SOCKS5 proxy for Binance API (direct connection blocked in some regions)
_SOCKS5_PROXY = "socks5h://127.0.0.1:1080"
_SESSION = requests.Session()
_SESSION.proxies.update({"https": _SOCKS5_PROXY, "http": _SOCKS5_PROXY})

def check_momentum(symbol: str) -> dict:
    """
    查一个币最近3根5分钟K线。
    返回: {"ok": True/False, "reason": "...", "details": {...}}
    """
    sym = symbol.upper().replace("USDT", "") + "USDT"
    
    try:
        r = _SESSION.get(
            f"{BINANCE_API}/api/v3/klines",
            params={"symbol": sym, "interval": "5m", "limit": 4},
            timeout=10
        )
        if r.status_code != 200:
            return {"ok": False, "reason": f"API返回{r.status_code}", "details": {}}
        
        klines = r.json()
        if len(klines) < 3:
            return {"ok": False, "reason": f"K线数据不足({len(klines)}根)", "details": {}}
        
        # 取最近3根完整K线(忽略最新那根可能未完成)
        candles = klines[-4:-1]  # 3根完整5m K线 = 15分钟
        
        results = []
        total_vol = 0
        price_start = float(candles[0][1])  # open of first candle
        price_end = float(candles[-1][4])   # close of last candle
        total_change_pct = (price_end - price_start) / price_start * 100
        
        for i, k in enumerate(candles):
            t = datetime.fromtimestamp(k[0] / 1000)
            o, h, l, c, v = float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
            chg = (c - o) / o * 100
            results.append({
                "time": t.strftime("%H:%M"),
                "open": round(o, 8),
                "close": round(c, 8),
                "high": round(h, 8),
                "low": round(l, 8),
                "change_pct": round(chg, 2),
                "volume": round(v, 2)
            })
            total_vol += v
        
        # 判断标准：
        # 1. 最近15分钟总体在涨 (total_change_pct > 0)
        # 2. 最后一根K线在涨 (results[-1]["change_pct"] >= 0 或跌幅很小)
        # 3. 有成交量 (total_vol > 0)
        
        still_rising = total_change_pct > 0
        last_candle_ok = results[-1]["change_pct"] >= -0.3  # 最后一根微跌可接受
        has_volume = total_vol > 0
        
        all_ok = still_rising and last_candle_ok and has_volume
        
        if all_ok:
            reason = f"✅ 最近15min涨{total_change_pct:+.2f}% 量{total_vol:.0f}"
        elif not still_rising:
            reason = f"❌ 最近15min跌{total_change_pct:+.2f}% — 不在涨"
        elif not last_candle_ok:
            reason = f"❌ 最后一根跌{results[-1]['change_pct']:+.2f}% — 动能衰竭"
        else:
            reason = "❌ 动量不足"
        
        return {
            "ok": all_ok,
            "reason": reason,
            "total_change_pct": round(total_change_pct, 2),
            "total_volume": round(total_vol, 2),
            "candles": results,
            "symbol": symbol
        }
        
    except Exception as e:
        return {"ok": False, "reason": f"异常: {str(e)}", "details": {"error": str(e)}}


def check_candidates(candidates):
    """批量检查多个候选币的实时动量"""
    results = []
    for sym in candidates:
        r = check_momentum(sym)
        results.append(r)
        status = "🟢" if r["ok"] else "🔴"
        print(f"{status} {sym:12s} | {r['reason']}")
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 单币检查
        result = check_momentum(sys.argv[1])
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["ok"] else 1)
    else:
        # 测试
        print("=== 实时动量检查测试 ===")
        print("用法: python3 tools/realtime_momentum_check.py <SYMBOL>")
        print()
        # 测试几个今天的涨幅榜币
        test_coins = ["XRP", "XLM", "ZEC", "NEAR", "AAVE", "WLD"]
        check_candidates(test_coins)
