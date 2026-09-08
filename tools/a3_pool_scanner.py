#!/usr/bin/env python3
"""
A3 选币库扫描器 v1.2 — 先批量24h数据快速过滤，再深度验证
从选币库(173个)中扫两路：动量检测+动量预判，输出5-10个给A4

2026-05-18 老李纠正: A3从选币库取币，不是从涨幅榜
"""
import json, sys, subprocess, os, re
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COIN_POOL = os.path.join(BASE, "data", "coin_pool.json")
OUTPUT_DIR = os.path.join(BASE, "profiles", "a3-bull", "output")
AWS_SSH = "ssh web4"

def now_bjt():
    return datetime.now().strftime("%Y-%m-%d %H:%M BJT")

def run_cmd(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except: return ""

def calc_rsi(closes, p=14):
    if len(closes) < p + 1: return None
    g = l = 0
    for i in range(len(closes)-p, len(closes)):
        d = closes[i] - closes[i-1]
        if d > 0: g += d
        else: l -= d
    if l == 0: return 100
    return round(100 - 100/(1+(g/p)/(l/p)), 1)

def batch_fetch_all_tickers():
    """批量拉取全市场24h数据（一次SSH调用）"""
    data = run_cmd(f'{AWS_SSH} curl -s "https://api.binance.com/api/v3/ticker/24hr"', 30)
    try:
        return {t["symbol"]: t for t in json.loads(data)}
    except:
        return {}

def fetch_klines(sym, interval, limit):
    """拉取指定币种的K线"""
    cmd = f'{AWS_SSH} curl -s -G "https://api.binance.com/api/v3/klines" --data-urlencode "symbol={sym}USDT" --data-urlencode "interval={interval}" --data-urlencode "limit={limit}"'
    s = run_cmd(cmd, 10)
    m = re.search(r'\[.*\]', s, re.DOTALL)
    try: return json.loads(m.group()) if m else None
    except: return None

def scan_pool(count=10):
    """全流程: 批量取24h→快速过滤→深度验证→输出"""
    if not os.path.exists(COIN_POOL):
        print(f"❌ 选币库不存在: {COIN_POOL}")
        return []

    with open(COIN_POOL) as f:
        pool = json.load(f)

    master = pool.get("pools", {}).get("master", [])
    watch = pool.get("pools", {}).get("watch", [])
    all_coins = [c for c in master + watch if c.get("status") == "active"
                 and c["symbol"] not in ("BTC", "ETH", "SOL")]

    print(f"\n{'='*60}")
    print(f"📊 A3 选币库扫描 | {now_bjt()}")
    print(f"选币库: {len(master)}master + {len(watch)}watch = {len(master)+len(watch)}个")
    print(f"{'='*60}")

    # ─── 第一步: 批量全市场24h数据 ───
    print(f"[1/4] 批量拉取全市场24h数据...", end=" ", flush=True)
    tickers = batch_fetch_all_tickers()
    if not tickers:
        print("❌ 失败!")
        return []
    print(f"✅ {len(tickers)}个交易对")

    # ─── 第二步: 快速过滤（仅24h数据） ───
    print(f"[2/4] 从选币库快速过滤...")
    fast_pass = []
    for c in all_coins:
        sym = c["symbol"]
        t = tickers.get(f"{sym}USDT")
        if not t: continue
        chg = float(t["priceChangePercent"])
        vol = float(t["quoteVolume"])
        price = float(t["lastPrice"])

        # 路1: 动量检测（正在涨的币）
        if 5 <= chg <= 40 and vol >= 5e6:
            fast_pass.append({"symbol": sym, "type": "momentum", "price": price,
                              "chg": chg, "vol": vol, "ticker": t})
        # 路2: 动量预判（快要涨的币）— 放量不涨/吸筹信号
        elif 2 <= chg <= 6 and vol >= 3e6:
            fast_pass.append({"symbol": sym, "type": "prediction", "price": price,
                              "chg": chg, "vol": vol, "ticker": t})

    print(f"  通过: {len(fast_pass)}个")
    for f in fast_pass:
        print(f"  {f['symbol']:<10s} {f['type']:<6s} {f['chg']:>+5.1f}% ${f['vol']/1e6:.0f}M")

    # ─── 第三步: 深度验证（拉K线） ───
    print(f"[3/4] 深度验证...(最多{count*2}个)")
    results = []
    for i, item in enumerate(fast_pass):
        if len(results) >= count * 2: break
        sym = item["symbol"]
        print(f"  [{i+1}/{len(fast_pass)}] {sym}...", end=" ", flush=True)

        # 拉4h K线
        k4 = fetch_klines(sym, "4h", 100)
        if not k4 or len(k4) < 20:
            print("❌ 无4h数据")
            continue
        c4 = [float(k[4]) for k in k4]
        rsi = calc_rsi(c4, 14)
        ma20 = sum(c4[-20:]) / 20
        pos_7 = sum(1 for k in k4[-7:] if float(k[4]) > float(k[1]))
        detail = {"price": item["price"], "chg": item["chg"], "vol": item["vol"],
                  "rsi_4h": rsi, "ma20_4h": ma20, "4h_direction": f"{pos_7}/7向上"}

        # 7天日线
        k1 = fetch_klines(sym, "1d", 10)
        d7 = ""
        if k1 and len(k1) >= 5:
            dp = sum(1 for k in k1 if float(k[4]) > float(k[1]))
            dn = len(k1) - dp
            d7 = f"{dp}涨{dn}跌"
            detail["7d"] = d7

        # 判定逻辑
        reasons_buy = []
        reasons_skip = []
        chg = item["chg"]
        vol = item["vol"]

        if item["type"] == "momentum":
            # 路1判定
            if 5 <= chg <= 20: reasons_buy.append(f"涨幅+{chg:.1f}%✅")
            elif 20 < chg <= 30: reasons_buy.append(f"涨幅+{chg:.1f}%偏高")
            elif chg > 30: reasons_skip.append(f"涨幅+{chg:.1f}%偏高")
            # RSI
            if rsi and rsi > 80: reasons_skip.append(f"RSI{rsi}过热")
            elif rsi and rsi > 70: reasons_buy.append(f"RSI{rsi}偏高")
            elif rsi and rsi >= 45: reasons_buy.append(f"RSI{rsi}健康✅")
            elif rsi and rsi >= 30: reasons_skip.append(f"RSI{rsi}偏低")
            else: reasons_skip.append(f"RSI{rsi}超卖")
            # MA20
            if item["price"] > ma20: reasons_buy.append(f"高于MA20✅")
            else: reasons_skip.append(f"低于MA20")
            # 7天趋势
            if d7:
                if dp >= 4: reasons_buy.append(f"7天{d7}趋势确认✅")
                elif dp >= 3: reasons_buy.append(f"7天{d7}初步趋势✅")
                else: reasons_skip.append(f"7天{d7}趋势不足")
            # 成交量
            if vol >= 10e6: reasons_buy.append(f"量${vol/1e6:.0f}M充沛✅")
            elif vol >= 5e6: reasons_buy.append(f"量${vol/1e6:.0f}M充足✅")
        else:
            # 路2判定 — 预判型宽松
            reasons_buy.append(f"放量不涨+{chg:.1f}%关注")
            if rsi and 30 <= rsi <= 55: reasons_buy.append(f"RSI{rsi}可启动区间✅")
            if rsi and rsi > 70: reasons_skip.append(f"RSI{rsi}偏高")
            if item["price"] < ma20 * 0.95: reasons_skip.append(f"低于MA20较多")
            if vol >= 3e6: reasons_buy.append(f"量${vol/1e6:.0f}M✅")

        buy_w = len(reasons_buy)
        skip_w = len(reasons_skip)

        if item["type"] == "momentum":
            if buy_w >= 3 and skip_w <= 1: verdict = "🟢可买入"
            elif buy_w >= 2 and skip_w <= 2: verdict = "🟡关注"
            else: verdict = "⚪跳过"
        else:
            if buy_w >= 2 and skip_w <= 1: verdict = "🟢预判买入"
            elif buy_w >= 1 and skip_w <= 2: verdict = "🟡预判关注"
            else: verdict = "⚪跳过"

        print(f"{verdict} RSI{rsi} MA20${ma20:.2f}")

        if "跳过" not in verdict:
            results.append({
                "symbol": sym, "type": item["type"], "verdict": verdict,
                "buy_weight": buy_w, "skip_weight": skip_w,
                "reasons_buy": reasons_buy, "reasons_skip": reasons_skip,
                "detail": detail
            })

        if len(results) >= count: break

    # ─── 第四步: 输出 ───
    results.sort(key=lambda r: -r["buy_weight"])

    print(f"\n{'='*60}")
    print(f"🏆 A3 牛币库 — 今日推荐({len(results)}个) | {now_bjt()}")
    print(f"{'='*60}")
    print(f"  {'币种':<10s} {'类型':<8s} {'判定':<12s} {'涨幅':>7s} {'成交额':>8s} {'RSI':>5s}")
    print(f"  {'-'*55}")
    for r in results:
        d = r["detail"]
        t = "动量" if r["type"]=="momentum" else "预判"
        chg = d.get("chg", 0)
        vol = d.get("vol", 0)
        rsi = d.get("rsi_4h", "?")
        print(f"  {r['symbol']:<10s} {t:<8s} {r['verdict']:<12s} {chg:>+6.1f}% ${vol/1e6:>5.0f}M {str(rsi):>5s}")

    # 写报告
    _write_report(results)
    return results


def _write_report(candidates):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(OUTPUT_DIR, f"{date}.md")

    lines = [f"# A3 牛币官 — 每日精选报告"]
    lines.append(f"日期: {date} | 时间: {now_bjt()}")
    lines.append(f"数据源: 选币库(173个) → 两路筛选")
    lines.append("")
    lines.append(f"## 🏆 今日推荐({len(candidates)}个)")
    lines.append("| 币种 | 类型 | 判定 | 24h涨幅 | 成交额 | 4h RSI | MA20 | 7天 | 亮点 |")
    lines.append("|:----|:-----|:-----|:-------:|:------:|:------:|:----:|:---:|:-----|")
    for r in candidates:
        d = r["detail"]
        t = "动量" if r["type"]=="momentum" else "预判"
        chg = d.get("chg", 0)
        vol = d.get("vol", 0)
        rsi = d.get("rsi_4h", "?")
        ma = d.get("ma20_4h", "?")
        d7 = d.get("7d", "?")
        hl = r["reasons_buy"][0][:25] if r.get("reasons_buy") else "-"
        lines.append(f"| {r['symbol']} | {t} | {r['verdict']} | {chg:+.1f}% | ${vol/1e6:.1f}M | {rsi} | ${ma:.2f} | {d7} | {hl} |")
    lines.append("")
    lines.append("发送给A4的清单:")
    for r in candidates:
        lines.append(f"- {r['symbol']} ({r['type']}): {r['verdict']}")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n📝 报告: {path}")


if __name__ == "__main__":
    count = 10
    for a in sys.argv:
        if a.startswith("--count="):
            count = int(a.split("=")[1])
    scan_pool(count=count)
