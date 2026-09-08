#!/usr/bin/env python3
"""
选币库每日扫描 — 按选币库标准自动扫全市场
每天早上自动产出"今日可买清单"

标准：
  1. 涨幅5-20%（太低没动力，太高可能到顶）
  2. 成交量>$5M（真实资金）
  3. 4h RSI 45-78（趋势区域，不过热不超卖）
  4. 价格在MA20上方（趋势向上）
  5. 7天中至少3天收涨（有持续性）
  6. 排除涨幅>40%的（涨到头了）

用法: python3 tools/daily_scan.py
       python3 tools/daily_scan.py --detail  显示每个币的完整判定
"""

import json, sys, subprocess, os
from datetime import datetime

AWS_SSH = "ssh web4"

def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
        return r.stdout.strip()
    except:
        return ""

def get_binance_ticker(all_200=True):
    data_str = run_cmd(f"{AWS_SSH} curl -s 'https://api.binance.com/api/v3/ticker/24hr' ")
    try:
        return json.loads(data_str)
    except:
        return None

def get_klines(symbol, interval, limit):
    cmd = f'{AWS_SSH} curl -s -G "https://api.binance.com/api/v3/klines" --data-urlencode "symbol={symbol}USDT" --data-urlencode "interval={interval}" --data-urlencode "limit={limit}" '
    data_str = run_cmd(cmd)
    import re
    match = re.search(r'\[.*\]', data_str, re.DOTALL)
    if match: data_str = match.group()
    try: return json.loads(data_str)
    except: return None

def calc_rsi(closes, period=14):
    if len(closes) < period + 1: return None
    gains, losses = 0, 0
    for i in range(len(closes) - period, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff > 0: gains += diff
        else: losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)

def check_coin(symbol):
    """按选币库标准查一个币——返回 (verdict, reasons)"""
    results = {"symbol": symbol, "pass": True, "checks": [], "detail": {}}
    
    # 1. 24h数据
    data_str = run_cmd(f"{AWS_SSH} curl -s 'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT' ")
    try:
        t = json.loads(data_str)
    except:
        results["pass"] = False
        results["checks"].append(("数据拉取", False, "数据不可用"))
        return results
    if "symbol" not in t:
        results["pass"] = False
        results["checks"].append(("存在性", False, "找不到该币"))
        return results
    
    chg = float(t["priceChangePercent"])
    vol = float(t["quoteVolume"])
    price = float(t["lastPrice"])
    results["detail"] = {"price": price, "chg": chg, "vol": vol}
    
    # 标准1: 涨幅5-20%
    if chg > 40:
        results["checks"].append(("涨幅", False, f"+{chg:.1f}% — 可能涨到头"))
        results["pass"] = False
    elif chg > 20:
        results["checks"].append(("涨幅", False, f"+{chg:.1f}% — 偏高，等回调"))
        results["pass"] = False
    elif chg >= 5:
        results["checks"].append(("涨幅", True, f"+{chg:.1f}% ✅ 启动区间"))
    elif chg > 0:
        results["checks"].append(("涨幅", False, f"+{chg:.1f}% — 动力不足"))
        results["pass"] = False
    else:
        results["checks"].append(("涨幅", False, f"{chg:.1f}% — 跌的币不买"))
        results["pass"] = False
    
    # 标准2: 成交量>$5M
    if vol >= 10e6:
        results["checks"].append(("成交量", True, f"${vol/1e6:.0f}M ✅ 充沛"))
    elif vol >= 5e6:
        results["checks"].append(("成交量", True, f"${vol/1e6:.0f}M ✅ 充足"))
    else:
        results["checks"].append(("成交量", False, f"${vol/1e6:.1f}M ❌ 不够"))
        results["pass"] = False
    
    # 3. 4h K线趋势
    k4 = get_klines(symbol, "4h", 50)
    if k4 and len(k4) > 15:
        c4 = [float(k[4]) for k in k4]
        rsi4 = calc_rsi(c4, 14)
        ma20 = sum(c4[-20:]) / 20
        results["detail"]["rsi_4h"] = rsi4
        results["detail"]["ma20_4h"] = ma20
        
        if rsi4 and rsi4 > 80:
            results["checks"].append(("4h RSI", False, f"{rsi4} 🔴极度过热"))
            results["pass"] = False
        elif rsi4 and rsi4 > 75:
            results["checks"].append(("4h RSI", False, f"{rsi4} 🔴偏高，回调风险"))
            results["pass"] = False
        elif rsi4 and rsi4 >= 45:
            results["checks"].append(("4h RSI", True, f"{rsi4} ✅ 健康趋势"))
        elif rsi4 and rsi4 >= 30:
            results["checks"].append(("4h RSI", False, f"{rsi4} ⚠️ 偏低，等确认"))
            results["pass"] = False
        else:
            results["checks"].append(("4h RSI", False, f"{rsi4} 🔴 超卖不买"))
            results["pass"] = False
        
        # 标准4: 价格在MA20上方
        if price > ma20:
            results["checks"].append(("MA20位置", True, f"高于MA20(${ma20:.4f}) ✅"))
        else:
            results["checks"].append(("MA20位置", False, f"低于MA20(${ma20:.4f}) ❌"))
            results["pass"] = False
        
        # 4h最近3根方向
        last3 = [float(k[4]) > float(k[1]) for k in k4[-3:]]
        up3 = sum(last3)
        results["detail"]["4h_direction"] = f"{up3}/3向上"
        if up3 >= 2:
            results["checks"].append(("4h方向", True, f"{up3}/3K线向上 ✅"))
        else:
            results["checks"].append(("4h方向", False, f"{up3}/3K线向上，偏弱"))
    else:
        results["checks"].append(("4h数据", False, "无法获取"))
    
    # 5. 7天日线
    k1 = get_klines(symbol, "1d", 7)
    if k1 and len(k1) >= 5:
        pos = sum(1 for k in k1 if float(k[4]) > float(k[1]))
        neg = 7 - pos
        results["detail"]["7d"] = f"{pos}涨{neg}跌"
        if pos >= 4:
            results["checks"].append(("7天趋势", True, f"{pos}涨{neg}跌 ✅ 趋势确认"))
        elif pos >= 3:
            results["checks"].append(("7天趋势", True, f"{pos}涨{neg}跌 ✅ 初步趋势"))
        else:
            results["checks"].append(("7天趋势", False, f"{pos}涨{neg}跌 ❌ 趋势不足"))
            results["pass"] = False
    
    return results

def scan_market():
    """扫全部市场，按选币库标准产出候选清单"""
    print(f"\n{'='*60}")
    print(f"📊 选币库每日扫描 — 按标准自动筛选")
    print(f"时间: {datetime.now().strftime('%H:%M BJT')}")
    print(f"{'='*60}")
    print(f"标准: 涨幅5-20% | 成交量>$5M | 4h RSI 45-78 | 高于MA20 | 7天≥3涨")
    print(f"{'='*60}\n")
    
    all_data = get_binance_ticker()
    if not all_data:
        print("❌ 数据拉取失败")
        return
    
    # 过滤USDT交易对
    pairs = [d for d in all_data if d['symbol'].endswith('USDT') 
             and not any(x in d['symbol'] for x in ['DOWN','UP','BEAR','BULL','BUSD','USDC','DAI','FDUSD','USD1'])]
    pairs.sort(key=lambda x: float(x['priceChangePercent']), reverse=True)
    
    # 第一步：快速筛选（只看24h数据 — 严一点减少深度验证量）
    quick_pass = []
    for p in pairs:
        chg = float(p['priceChangePercent'])
        vol = float(p['quoteVolume'])
        sym = p['symbol'].replace('USDT','')
        # 快速条件：涨幅5-40% + 成交量>$5M（低于此直接跳过，不用查K线）
        if 5 <= chg <= 40 and vol >= 5e6:
            quick_pass.append((sym, chg, vol))
    
    print(f"快速筛选: {len(quick_pass)}个币通过（涨幅5-40%+量>$5M）")
    print(f"深度验证中...（每个币拉取K线数据）")
    
    # 第二步：深度验证（K线+趋势）— 最多跑6个，多了超时
    candidates = []
    skip_reasons = {}
    total = min(len(quick_pass), 6)  # 限制深度验证数量
    for i, (sym, chg, vol) in enumerate(quick_pass[:total]):
        result = check_coin(sym)
        if result["pass"] and all(c[1] for c in result["checks"]):
            candidates.append(result)
        elif not result["pass"]:
            fails = [c[0] for c in result["checks"] if not c[1]]
            skip_reasons[sym] = fails
    # 剩余作为"快速候选"
    remaining = [(sym, chg, vol) for (sym, chg, vol) in quick_pass[total:] if 5 <= chg <= 40]
    
    # 排序：按涨幅排
    candidates.sort(key=lambda r: r["detail"].get("chg", 0), reverse=True)
    
    # 输出
    print(f"\n{'='*60}")
    print(f"🏆 今日候选池 — 全部标准通过: {len(candidates)}个")
    print(f"{'='*60}")
    
    if not candidates:
        print("\n(无符合条件的币)")
    else:
        print(f"\n{'币种':<10s} {'涨幅':>7s} {'成交量':>10s} {'4h RSI':>7s} {'7天':>8s} {'判定':>10s}")
        print(f"{'-'*50}")
        for r in candidates:
            d = r["detail"]
            chg = d.get("chg", 0)
            vol = d.get("vol", 0)
            rsi = d.get("rsi_4h", 0)
            td = d.get("7d", "?")
            print(f"{r['symbol']:<10s} {chg:>+6.1f}% {vol/1e6:>8.1f}M {rsi:>6.1f} {td:>8s} 🟢")
    
    # 跳过列表（只看涨幅5-20%但被跳过的）
    print(f"\n{'='*60}")
    print(f"📋 接近通过但被跳过（涨幅5-20%）")
    print(f"{'='*60}")
    borderline = [(sym, chg, vol, reasons) for (sym, chg, vol) in quick_pass 
                  if 5 <= chg <= 40 and sym in skip_reasons
                  for reasons in [skip_reasons[sym]]]
    borderline.sort(key=lambda x: x[1], reverse=True)
    for sym, chg, vol, reasons in borderline[:15]:
        reason_str = ", ".join(reasons[:2])
        print(f" {sym:<10s} {chg:>+6.1f}% ${vol/1e6:.1f}M ❌ {reason_str}")
    
    # 快速候选（未深度验证）
    if remaining:
        print(f"\n{'='*60}")
        print(f"⚡ 快速候选（仅24h数据通过，待深度验证）")
        print(f"{'='*60}")
        for sym, chg, vol in remaining[:10]:
            print(f" {sym:<10s} {chg:>+6.1f}% ${vol/1e6:.1f}M ⏳")
        print(f"  深度验证: python3 tools/momentum_check.py <币名>")
    
    print(f"\n{'='*60}")
    print(f"✅ 完成! 候选: {len(candidates)}个 | 跳过(5-20%涨幅): {len(borderline)}个")
    print(f"详细查一个币: python3 tools/momentum_check.py <币名>")
    print(f"{'='*60}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--detail":
        # 深度模式：显示每个币的完整判定（暂未实现）
        scan_market()
    else:
        scan_market()
