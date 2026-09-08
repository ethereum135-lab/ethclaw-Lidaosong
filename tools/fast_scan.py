#!/usr/bin/env python3
"""快速扫描 v3.0 — 用K线替代24hr滚动ticker做判断
========================================
核心改动 (2026-06-24):
  1. 数据源: 用24根1h K线替代 ticker/24hr → 解决滚动窗口滞后问题
  2. 量比: 用K线成交量对比(近3根vs更早3根) → 替代count-based量比
  3. 价格位置: 用真实24h区间 → 替代ticker的rolling high/low
  4. 双通道: 追涨(近1h涨了) + 低吸(近1h跌了且刚拐头)

用法: python3 tools/fast_scan.py
输出: data/fast_scan_candidates.json
"""
import json, os, time, math, ssl, urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

BASE = os.path.expanduser("~/zq_web4_trading_system")
OUTPUT_PATH = os.path.join(BASE, "data/fast_scan_candidates.json")
SS_PATH = os.path.join(BASE, "data/smart_signal", "snapshot.json")

EXCLUDE_KEYWORDS = ['UP','DOWN','BULL','BEAR','BUSD','USDC','TUSD','DAI','FDUSD',
                    'USDP','AEUR','EUR','GBP','AUD','BRL','TRY','ZAR','IDRT',
                    'USTC','USDD','SUSD']
MIN_VOLUME = 500_000
_KLINES_CACHE = {}
_CACHE_LOCK = threading.Lock()

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def api_get(path, params=None, timeout=15):
    qs = "&".join(f"{k}={v}" for k,v in sorted((params or {}).items()))
    url = f"https://api.binance.com{path}?{qs}" if qs else f"https://api.binance.com{path}"
    # Primary: SOCKS5 proxy (direct urllib always times out in this network)
    import subprocess
    try:
        r = subprocess.run(
            ['curl', '-s', '--connect-timeout', '5', '--max-time', str(min(timeout, 10)),
             '--socks5-hostname', '127.0.0.1:1080', url],
            capture_output=True, text=True, timeout=timeout+5)
        if r.returncode == 0 and r.stdout:
            return json.loads(r.stdout)
    except: pass
    # Fallback: direct urllib
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        pass
    return None

def fetch_tickers():
    """获取全市场ticker（只用于粗筛成交量）"""
    data = api_get("/api/v3/ticker/24hr")
    if data is None:
        # fallback via subprocess + SOCKS5
        import subprocess
        try:
            r = subprocess.run(
                ['curl', '-s', '--connect-timeout', '8', '--max-time', '20',
                 '--socks5-hostname', '127.0.0.1:1080',
                 'https://api.binance.com/api/v3/ticker/24hr'],
                capture_output=True, text=True, timeout=25)
            if r.returncode == 0 and r.stdout:
                return json.loads(r.stdout)
        except: pass
    if data is None:
        # 2026-08-09 A5修复: 本地SOCKS5隧道(ssh -D 1080)对大响应(>100KB)不稳定,
        # ticker/24hr(1.88MB)稳定失败导致fast_scan停更12h(09:59~22:20)。
        # AWS直连Binance可靠 → AWS端预筛选脚本(/tmp/fs_prescreen.py), 只传回symbol列表(小数据)
        import subprocess
        try:
            r = subprocess.run(
                ['ssh', '-o', 'ConnectTimeout=10', '-o', 'BatchMode=yes', 'web4',
                 'python3 /tmp/fs_prescreen.py'],
                capture_output=True, text=True, timeout=45)
            if r.returncode == 0 and r.stdout and ',' in r.stdout and not r.stdout.startswith('ERR:'):
                syms = [s.strip() for s in r.stdout.strip().split(',') if s.strip()]
                # 伪ticker: vol置1e9过MIN_VOLUME上游检查, chg置0在±30内; 真实K线分析在本地进行
                return [{'symbol': s, 'quoteVolume': 1e9, 'priceChangePercent': 0.0} for s in syms]
        except: pass
    return data

def fetch_klines(symbol, interval="1h", limit=12):
    """拉取K线数据（带缓存，避免重复请求）"""
    cache_key = f"{symbol}_{interval}_{limit}"
    with _CACHE_LOCK:
        if cache_key in _KLINES_CACHE:
            now_ts = time.time()
            if now_ts - _KLINES_CACHE[cache_key]["ts"] < 120:  # 2分钟缓存
                return _KLINES_CACHE[cache_key]["data"]
    data = api_get("/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": limit}, timeout=10)
    if data:
        with _CACHE_LOCK:
            _KLINES_CACHE[cache_key] = {"data": data, "ts": time.time()}
    return data

def is_valid(symbol):
    if not symbol.endswith('USDT'):
        return False
    base = symbol.replace('USDT', '').replace('1000', '')
    for kw in EXCLUDE_KEYWORDS:
        if kw in base:
            return False
    return True

def load_smart_signal():
    if not os.path.exists(SS_PATH):
        return {}
    try:
        ss = json.load(open(SS_PATH))
    except:
        return {}
    mapping = {}
    for d in ss.get("data", []):
        sym = d.get("symbol", "")
        if not sym or "error" in d:
            continue
        clean = sym.replace("USDT", "").replace("1000", "")
        mapping[clean] = d
        mapping[sym] = d
    return mapping

def analyze_klines(symbol, smart_signal_map):
    """从1h K线分析币种状态
    返回: {
      valid: bool,
      price: float,
      vol_24h: float,
      range_pos: float,        # 在24h区间位置(0-100%)
      chg_1h: float,           # 最后一小时涨跌幅
      chg_4h: float,           # 最近4小时涨跌幅
      chg_24h: float,          # 最近24小时涨跌幅(来自K线)
      vol_surge: float,        # 成交量激增倍率(近3h/前12h)
      recent_high_pct: float,  # 距离24h前高的百分比
      n_candles_up: int,       # 最近3根K线中上涨的根数
      signals: list,           # 触发的NAV信号
      error: str or None
    }
    """
    klines = fetch_klines(symbol, "1h", 24)
    if not klines or len(klines) < 12:
        return None
    
    # 解析
    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    volumes = [float(k[7]) for k in klines]  # quote volume
    n = len(closes)
    
    price = closes[-1]
    
    # 24h区间
    high_24h = max(highs)
    low_24h = min(lows)
    range_pos = (price - low_24h) / (high_24h - low_24h) * 100 if high_24h > low_24h else 50
    recent_high_pct = (price - low_24h) / low_24h * 100 if low_24h > 0 else 0
    
    # 24h涨跌幅(从K线第一根到最后一根)
    price_24h_ago = closes[0]
    chg_24h = (price - price_24h_ago) / price_24h_ago * 100 if price_24h_ago > 0 else 0
    
    # 1h涨跌幅
    price_1h_ago = closes[-2] if n >= 2 else price
    chg_1h = (price - price_1h_ago) / price_1h_ago * 100 if price_1h_ago > 0 else 0
    
    # 4h涨跌幅
    price_4h_ago = closes[-5] if n >= 5 else price
    chg_4h = (price - price_4h_ago) / price_4h_ago * 100 if price_4h_ago > 0 else 0
    
    # 成交量激增(近3h成交量 vs 前12h平均每小时)
    vol_last_3h = sum(volumes[-3:])
    vol_earlier_12h = sum(volumes[-15:-3])  # 前12h
    vol_surge = vol_last_3h / (vol_earlier_12h / 4) if vol_earlier_12h > 0 else 1.0  # 后3h / (前12h平均3h)
    
    # 24h总成交量
    vol_24h = sum(volumes)
    
    # 最近3根K线中上涨的根数
    n_candles_up = sum(1 for i in range(-3, 0) if closes[i] > closes[i-1] if i >= 1)
    if n >= 3:
        n_candles_up = sum(1 for i in range(n-3, n-1) if closes[i] > closes[i-1])
        n_candles_up += 1 if closes[-1] > closes[-2] else 0
    
    # 检查品种在成交量靠前的200个里面才做深度扫描
    base_sym = symbol.replace('USDT', '').replace('1000', '')
    ss_data = smart_signal_map.get(base_sym) or smart_signal_map.get(symbol)
    
    return {
        "price": round(price, 8),
        "vol_24h": round(vol_24h, 2),
        "range_pos": round(range_pos, 1),
        "chg_1h": round(chg_1h, 2),
        "chg_4h": round(chg_4h, 2),
        "chg_24h": round(chg_24h, 2),
        "vol_surge": round(vol_surge, 2),
        "recent_high_pct": round(recent_high_pct, 2),
        "n_candles_up": n_candles_up,
        "has_smart_signal": ss_data is not None,
        "smart_signal": ss_data.get("analysis", {}).get("whaleBias", "NONE") if ss_data else "NONE",
    }

def score_candidate(sym, analysis, smart_signal_map):
    """用K线分析结果做评分"""
    signals = []
    
    vol_ok = analysis["vol_24h"] >= MIN_VOLUME
    chg_1h = analysis["chg_1h"]
    chg_24h = analysis["chg_24h"]
    range_pos = analysis["range_pos"]
    vol_surge = analysis["vol_surge"]
    n_up = analysis["n_candles_up"]
    ss = analysis["smart_signal"]
    
    # 信号1: 放量上涨 (近1h涨了+量激增+位置健康)
    if chg_1h > 1.0 and vol_surge >= 1.5 and 25 <= range_pos <= 80 and vol_ok:
        signals.append({"id": 1, "name": "1h放量上涨", "weight": 3,
                        "detail": f"1h+{chg_1h:.1f}% vol{vol_surge:.1f}x"})
    
    # 信号2: 短线趋势向好 (最近3根K线至少2根涨)
    if n_up >= 2 and chg_1h > 0:
        signals.append({"id": 2, "name": "短线趋势向上", "weight": 2,
                        "detail": f"近3h{n_up}/3涨 +{chg_1h:.1f}%"})
    
    # 信号3: 刚从低位反弹 (range_pos<30+刚涨)
    if range_pos < 30 and chg_1h > 0.5 and vol_surge >= 1.2:
        signals.append({"id": 3, "name": "低位反弹", "weight": 2,
                        "detail": f"range{range_pos:.0f}% +{chg_1h:.1f}% vol{vol_surge:.1f}x"})
    
    # 信号6: 聪明钱确认
    ss_signal = "NONE"
    base_sym = sym.replace('USDT', '').replace('1000', '')
    ss_data = smart_signal_map.get(base_sym) or smart_signal_map.get(sym)
    if ss_data:
        analysis_s = ss_data.get("analysis", {})
        wlp = analysis_s.get("whaleLongProfitPct", 0)
        if ss == "BULLISH" and wlp >= 80:
            signals.append({"id": 6, "name": "聪明钱强烈看涨", "weight": 3,
                          "detail": f"多头鲸{wlp}%盈"})
            ss_signal = "BUY"
        elif ss == "BULLISH":
            signals.append({"id": 6, "name": "聪明钱看涨", "weight": 2,
                          "detail": f"多{wlp}%盈"})
            ss_signal = "BULLISH"
    
    has_sig1 = any(s["id"] == 1 for s in signals)
    has_sig2 = any(s["id"] == 2 for s in signals)
    has_sig3 = any(s["id"] == 3 for s in signals)
    has_sig6 = any(s["id"] == 6 for s in signals)
    
    at_high = range_pos >= 85
    
    # 综合置信度
    if has_sig1 and has_sig6 and not at_high:
        confidence, tier = "超高", "A"
        suggested_pct = "USDT×30%"
    elif has_sig1 and not at_high:
        confidence, tier = "超高", "A"
        suggested_pct = "USDT×30%"
    elif has_sig2 and has_sig6 and not at_high:
        confidence, tier = "超高", "A"
        suggested_pct = "USDT×30%"
    elif has_sig3 and has_sig6:
        confidence, tier = "高", "A"
        suggested_pct = "USDT×15%"
    elif has_sig3:
        confidence, tier = "高", "A"
        suggested_pct = "USDT×15%"
    elif has_sig2 and not at_high:
        confidence, tier = "高", "A"
        suggested_pct = "USDT×15%"
    elif has_sig2 and at_high:
        confidence, tier = "高位慎入", "B"
        suggested_pct = "USDT×7.5%"
    elif has_sig6:
        confidence, tier = "中", "B"
        suggested_pct = "USDT×7.5%"
    elif vol_surge >= 1.5:
        confidence, tier = "中低", "B"
        suggested_pct = "USDT×7.5%"
    else:
        confidence, tier = "低", "C"
        suggested_pct = "不推荐"
    
    return {
        "signals": signals, "signal_count": len(signals),
        "total_weight": sum(s["weight"] for s in signals),
        "confidence": confidence, "tier": tier,
        "suggested_pct": suggested_pct,
        "vol_surge": vol_surge, "smart_signal": ss_signal,
    }

def analyze_one(symbol, smart_signal_map):
    """线程内分析一个币"""
    try:
        analysis = analyze_klines(symbol, smart_signal_map)
        if analysis is None:
            return None
        sc = score_candidate(symbol, analysis, smart_signal_map)
        if sc["tier"] == "C":
            return None
        total_score = sc["signal_count"] * max(sc["total_weight"], 1) * 2
        if sc["confidence"] == "超高": total_score += 10
        elif sc["confidence"] == "高": total_score += 5
        return {
            "symbol": symbol,
            "price": analysis["price"],
            "volume_24h": analysis["vol_24h"],
            "chg_1h": analysis["chg_1h"],
            "chg_4h": analysis["chg_4h"],
            "chg_24h": analysis["chg_24h"],
            "range_pos": analysis["range_pos"],
            "vol_surge": analysis["vol_surge"],
            "n_candles_up": analysis["n_candles_up"],
            "recent_high_pct": analysis["recent_high_pct"],
            "total_score": total_score,
            **sc
        }
    except:
        return None

def main():
    start_time = time.time()
    now = datetime.now()
    print(f"[{now.strftime('%H:%M')}] fast_scan v3.0 (K-line based)")
    
    smart_signal_map = load_smart_signal()
    has_ss = len(smart_signal_map) > 0
    print(f"  聪明钱: {'✅' if has_ss else '❌'} {len(smart_signal_map)}条")
    
    # Step 1: ticker粗筛
    all_tickers = fetch_tickers()
    if not all_tickers:
        print("  ❌ API失败")
        return
    
    usdt_pairs = [t for t in all_tickers if is_valid(t['symbol'])]
    usdt_pairs.sort(key=lambda t: float(t.get('quoteVolume', 0)), reverse=True)
    
    pre_candidates = []
    for t in usdt_pairs:
        try:
            vol = float(t.get('quoteVolume', 0))
            chg = float(t.get('priceChangePercent', 0))
        except ValueError:
            continue
        if vol < MIN_VOLUME:
            continue
        if chg > 30 or chg < -30:
            continue
        pre_candidates.append(t['symbol'])
        if len(pre_candidates) >= 50:
            break
    
    print(f"  粗筛: → 预选{len(pre_candidates)}个")
    
    # Step 2: 并行拉K线分析（8线程 — 2026-08-09 A5: 16线程打爆SOCKS5隧道致50请求全超时）
    candidates = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(analyze_one, sym, smart_signal_map): sym for sym in pre_candidates}
        for future in as_completed(futures):
            result = future.result()
            if result:
                candidates.append(result)
    
    # 排序
    candidates.sort(key=lambda c: c["total_score"], reverse=True)
    
    elapsed = time.time() - start_time
    print(f"  已分析: {len(candidates)}候选 ({elapsed:.1f}s)")
    
    # 输出
    output = {
        "scan_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "scanned": len(pre_candidates),
        "total_candidates": len(candidates),
        "engine_version": "v3.0-kline",
        "candidates": candidates
    }
    
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n=== Top候选 ===")
    for i, c in enumerate(candidates[:10]):
        print(f"  #{i+1} {c['symbol']:12s} "
              f"score:{c['total_score']:3d} {c['confidence']:6s} "
              f"vol:{c['vol_surge']:.1f}x "
              f"1h:{c['chg_1h']:+.2f}% "
              f"24h:{c['chg_24h']:+.2f}% "
              f"range:{c['range_pos']:.0f}% "
              f"sig:{c['signal_count']}个 "
              f"${c['price']:.6f}")
    
    by_conf = {}
    for c in candidates:
        by_conf[c["confidence"]] = by_conf.get(c["confidence"], 0) + 1
    print(f"\n=== 分布 ===")
    for cf, cnt in sorted(by_conf.items()):
        print(f"  {cf}: {cnt}")

if __name__ == "__main__":
    main()
