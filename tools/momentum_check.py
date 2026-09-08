#!/usr/bin/env python3
"""
动量验证工具 — 查一个币能不能买
输入币名(SYMBOL)，几秒出判定

用法: python3 tools/momentum_check.py FIDA
选项: python3 tools/momentum_check.py --all   扫涨幅榜TOP 20
      python3 tools/momentum_check.py FIDA --detail  详细原始数据
"""

import json, sys, subprocess, os
from datetime import datetime

AWS_SSH = "ssh web4"

def run_cmd(cmd):
    """跑命令返回输出"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return r.stdout.strip()
    except:
        return ""

def get_binance_ticker(symbol=None, all_200=False):
    """拉实时24hr数据"""
    if all_200:
        data_str = run_cmd(f"""{AWS_SSH} curl -s 'https://api.binance.com/api/v3/ticker/24hr' """)
    elif symbol:
        data_str = run_cmd(f"""{AWS_SSH} curl -s 'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT' """)
    else:
        return None
    try:
        return json.loads(data_str)
    except:
        return None

def get_klines(symbol, interval="4h", limit=100):
    """拉K线数据 — 用--data-urlencode避免&被shell吃掉"""
    cmd = f"""{AWS_SSH} curl -s -G "https://api.binance.com/api/v3/klines" --data-urlencode "symbol={symbol}USDT" --data-urlencode "interval={interval}" --data-urlencode "limit={limit}" """
    data_str = run_cmd(cmd)
    import re
    match = re.search(r'\[.*\]', data_str, re.DOTALL)
    if match:
        data_str = match.group()
    try:
        return json.loads(data_str)
    except:
        return None

def get_1d_klines(symbol, limit=7):
    """拉日线K线（7天）"""
    cmd = f"""{AWS_SSH} curl -s -G "https://api.binance.com/api/v3/klines" --data-urlencode "symbol={symbol}USDT" --data-urlencode "interval=1d" --data-urlencode "limit={limit}" """
    data_str = run_cmd(cmd)
    import re
    match = re.search(r'\[.*\]', data_str, re.DOTALL)
    if match:
        data_str = match.group()
    try:
        return json.loads(data_str)
    except:
        return None

def calc_rsi(closes, period=14):
    """计算RSI"""
    if len(closes) < period + 1:
        return None
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

def calc_ma(closes, period):
    if len(closes) < period: return None
    return sum(closes[-period:]) / period

def get_7day_trend(symbol):
    """查过去7天每天涨跌——判断是不是连续放量涨"""
    klines = get_1d_klines(symbol, 7)
    if not klines:
        return None, None
    
    results = []
    for k in klines:
        open_p = float(k[1])
        close_p = float(k[4])
        vol = float(k[5])
        chg = round((close_p - open_p) / open_p * 100, 2)
        results.append({"date": k[0], "open": open_p, "close": close_p, "chg": chg, "vol": vol})
    
    pos_days = sum(1 for r in results if r["chg"] > 0)
    neg_days = sum(1 for r in results if r["chg"] < 0)
    
    vol_up = all(results[i]["vol"] >= results[i-1]["vol"] for i in range(1, len(results)) if results[i]["chg"] > 0)
    
    return results, {"pos_days": pos_days, "neg_days": neg_days, "vol_up": vol_up}

def check_momentum(symbol):
    """核心验证函数——查一个币能不能买"""
    symbol = symbol.upper().replace("USDT", "")
    
    print(f"\n{'='*50}")
    print(f"📊 动量验证: {symbol}")
    print(f"时间: {datetime.now().strftime('%H:%M BJT')}")
    print(f"{'='*50}")
    
    # 1. 实时24h数据
    ticker = get_binance_ticker(symbol)
    if not ticker or "symbol" not in ticker:
        print(f"❌ 找不到{symbol}")
        return
    
    price = float(ticker["lastPrice"])
    chg_24h = float(ticker["priceChangePercent"])
    vol_24h = float(ticker["quoteVolume"])
    high_24h = float(ticker["highPrice"])
    low_24h = float(ticker["lowPrice"])
    
    print(f"\n📈 24h数据:")
    print(f"  最新价: ${price:.6f}")
    print(f"  涨幅:   {chg_24h:+.2f}%")
    print(f"  成交量: ${vol_24h/1e6:.1f}M")
    print(f"  最高:   ${high_24h:.6f}")
    print(f"  最低:   ${low_24h:.6f}")
    
    # 2. 7天日线趋势
    daily_klines, trend = get_7day_trend(symbol)
    if trend:
        print(f"\n📅 7天趋势:")
        for d in daily_klines:
            mark = "🟢" if d["chg"] > 0 else "🔴"
            print(f"  {mark} ${d['close']:.6f}  {d['chg']:+.2f}%  Vol: ${d['vol']/1e6:.1f}M")
        print(f"  涨的天数: {trend['pos_days']}/7 | 跌的天数: {trend['neg_days']}/7")
        print(f"  成交量递增: {'✅' if trend['vol_up'] else '❌'}")
    
    # 3. 4h K线趋势+RSI
    klines_4h = get_klines(symbol, "4h", 100)
    if klines_4h and len(klines_4h) > 20:
        closes_4h = [float(k[4]) for k in klines_4h]
        rsi_4h = calc_rsi(closes_4h, 14)
        
        # MA计算
        ma20_4h = calc_ma(closes_4h, 20)
        ma50_4h = calc_ma(closes_4h, 50) if len(closes_4h) >= 50 else None
        
        # 4h趋势判断（最近3根K线）
        last3_closes = [float(k[4]) for k in klines_4h[-3:]]
        last3_opens = [float(k[1]) for k in klines_4h[-3:]]
        up_count = sum(1 for i in range(3) if last3_closes[i] > last3_opens[i])
        
        print(f"\n📉 4小时K线趋势:")
        print(f"  当前RSI(14): {rsi_4h}")
        if ma20_4h: print(f"  MA20: ${ma20_4h:.4f} | 当前价{'高于' if price > ma20_4h else '低于'}MA20")
        if ma50_4h: print(f"  MA50: ${ma50_4h:.4f} | 当前价{'高于' if price > ma50_4h else '低于'}MA50")
        print(f"  最近3根K线方向: {'🟢🟢🟢' if up_count == 3 else '🟢🟢🔴' if up_count == 2 else '🔴🔴🔴' if up_count == 0 else '⚡震荡'}")
    
    # 4. 1h K线
    klines_1h = get_klines(symbol, "1h", 50)
    if klines_1h and len(klines_1h) > 14:
        closes_1h = [float(k[4]) for k in klines_1h]
        rsi_1h = calc_rsi(closes_1h, 14)
        ma20_1h = calc_ma(closes_1h, 20)
        
        print(f"\n⏰ 1小时K线:")
        print(f"  RSI(14): {rsi_1h}")
        if ma20_1h: print(f"  MA20: ${ma20_1h:.4f} | 当前价{'高于' if price > ma20_1h else '低于'}MA20")
    
    # 5. 综合判定
    print(f"\n{'='*50}")
    print(f"🔍 综合判定")
    print(f"{'='*50}")
    
    # 判定条件
    reasons_buy = []
    reasons_skip = []
    
    if chg_24h > 40: reasons_skip.append(f"涨幅{chg_24h:+.0f}%过高，大概率涨到头")
    elif chg_24h > 20: reasons_skip.append(f"涨幅{chg_24h:+.0f}%偏高，有回调风险")
    elif chg_24h > 5: reasons_buy.append(f"涨幅{chg_24h:+.0f}%健康，趋势启动区间")
    elif chg_24h > 0: reasons_buy.append(f"涨幅{chg_24h:+.0f}%温和，关注放量")
    else: reasons_skip.append(f"今日负涨幅{chg_24h:+.0f}%，不买跌的币")
    
    if vol_24h > 10e6: reasons_buy.append(f"成交量${vol_24h/1e6:.0f}M充沛，真实资金")
    elif vol_24h > 5e6: reasons_buy.append(f"成交量${vol_24h/1e6:.0f}M中等")
    else: reasons_skip.append(f"成交量${vol_24h/1e6:.1f}M偏低")
    
    if klines_4h and len(klines_4h) > 14:
        if rsi_4h and rsi_4h > 80: reasons_skip.append(f"4h RSI {rsi_4h}极度过热")
        elif rsi_4h and rsi_4h > 70: reasons_skip.append(f"4h RSI {rsi_4h}偏高，等回调")
        elif rsi_4h and rsi_4h > 50: reasons_buy.append(f"4h RSI {rsi_4h}健康趋势区域")
        elif rsi_4h and rsi_4h > 30: reasons_buy.append(f"4h RSI {rsi_4h}中性偏低，可能启动")
        else: reasons_skip.append(f"4h RSI {rsi_4h}超卖区，不买没动力的币")
    
    if trend:
        if trend["pos_days"] >= 5: reasons_buy.append(f"7天中{trend['pos_days']}天收涨，趋势确认")
        elif trend["pos_days"] >= 3: reasons_buy.append(f"7天中{trend['pos_days']}天收涨，初步趋势")
        else: reasons_skip.append(f"7天中仅{trend['pos_days']}天收涨，缺乏趋势支撑")
        
        if trend["vol_up"]: reasons_buy.append(f"放量上涨持续，资金在进场")
        else: reasons_skip.append(f"成交量未持续放大")
    
    print(f"\n✅ 可买入的理由:")
    if reasons_buy:
        for r in reasons_buy: print(f"  ✅ {r}")
    else: print(f"  (无)")
    
    print(f"\n❌ 应跳过的理由:")
    if reasons_skip:
        for r in reasons_skip: print(f"  ❌ {r}")
    else: print(f"  (无)")
    
    # 最终判定
    buy_weight = len(reasons_buy)
    skip_weight = len(reasons_skip)
    
    print(f"\n▶ 结论: ", end="")
    if buy_weight >= 3 and skip_weight <= 1:
        print(f"🟢 可买入（{buy_weight}买/{skip_weight}不买）")
    elif buy_weight >= 2 and skip_weight <= 2:
        print(f"🟡 谨慎关注（{buy_weight}买/{skip_weight}不买）— 等回调到支撑位")
    else:
        print(f"🔴 跳过（{buy_weight}买/{skip_weight}不买）— 风险大于机会")


def scan_top20():
    """扫描涨幅榜TOP 20，自动标记每个币能否买"""
    all_data = get_binance_ticker(all_200=True)
    if not all_data:
        print("❌ 拉取数据失败")
        return
    
    pairs = [d for d in all_data if d['symbol'].endswith('USDT') 
             and not any(x in d['symbol'] for x in ['DOWN','UP','BEAR','BULL','BUSD','USDC','DAI','FDUSD','USD1'])]
    pairs.sort(key=lambda x: float(x['priceChangePercent']), reverse=True)
    
    print(f"\n{'='*60}")
    print(f"📊 涨幅榜TOP 20 — 快速扫描")
    print(f"时间: {datetime.now().strftime('%H:%M BJT')}")
    print(f"{'='*60}")
    print(f"{'币种':<10s} {'涨幅':>7s} {'成交量':>10s} {'判定':>8s}")
    print(f"{'-'*40}")
    
    for p in pairs[:20]:
        symbol = p['symbol'].replace('USDT','')
        chg = float(p['priceChangePercent'])
        vol = float(p['quoteVolume'])
        
        # 快速判定
        if chg > 40: verdict = "🔴涨到头"
        elif chg > 20 and vol < 10e6: verdict = "🔴量不够"
        elif chg > 20: verdict = "🟡偏高"
        elif chg > 5 and vol > 5e6: verdict = "🟢可关注"
        elif chg > 5: verdict = "🟡量低"
        else: verdict = "⚪观望"
        
        print(f"{symbol:<10s} {chg:>+6.2f}% {vol/1e6:>8.1f}M {verdict:>8s}")
    
    print(f"\n🟢可关注: 涨幅5-20% + 成交量>$5M — 值得深度验证")
    print(f"跑深度验证: python3 tools/momentum_check.py <币名>")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 tools/momentum_check.py FIDA")
        print("      python3 tools/momentum_check.py --all   扫涨幅榜TOP 20")
        sys.exit(1)
    
    if sys.argv[1] == "--all":
        scan_top20()
    else:
        check_momentum(sys.argv[1])
