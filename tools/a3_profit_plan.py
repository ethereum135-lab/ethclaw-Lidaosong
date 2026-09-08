#!/usr/bin/env python3
"""
A3 牛币官 — 从候选到盈利方案

读daily_scan.py的候选池（自己标准筛选的），
对每个候选做深度验证，输出完整的盈利方案：
  - 这个币能买吗（验证可持续性）
  - 什么价格买、怎么分批建仓
  - 仓位占多少
  - 止盈多少、止损多少
  - 预期盈利、持有时间

用法: python3 tools/a3_profit_plan.py
       python3 tools/a3_profit_plan.py OPEN  查单个币
"""

import json, sys, subprocess, re
from datetime import datetime

AWS_SSH = "ssh web4"

def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
        return r.stdout.strip()
    except:
        return ""

def get_ticker(symbol):
    data_str = run_cmd(f"{AWS_SSH} curl -s 'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT' ")
    try: return json.loads(data_str)
    except: return None

def get_klines(symbol, interval, limit):
    cmd = f'{AWS_SSH} curl -s -G "https://api.binance.com/api/v3/klines" --data-urlencode "symbol={symbol}USDT" --data-urlencode "interval={interval}" --data-urlencode "limit={limit}" '
    data_str = run_cmd(cmd)
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

def find_support_resistance(prices_4h, prices_all):
    """找支撑位和阻力位"""
    if not prices_all: return None, None
    recent = prices_all[-30:] if len(prices_all) >= 30 else prices_all
    lows = sorted(recent)[:3]
    highs = sorted(recent, reverse=True)[:3]
    support = sum(lows) / len(lows)
    resistance = sum(highs) / len(highs)
    return round(support, 4), round(resistance, 4)

def get_profit_plan(symbol):
    """对一个候选币出完整盈利方案"""
    symbol = symbol.upper().replace("USDT", "")
    
    print(f"\n{'='*60}")
    print(f"💰 盈利方案: {symbol}")
    print(f"时间: {datetime.now().strftime('%H:%M BJT')}")
    print(f"{'='*60}")
    
    # 1. 24h数据
    t = get_ticker(symbol)
    if not t or "symbol" not in t:
        print(f"❌ 找不到{symbol}")
        return
    
    chg = float(t["priceChangePercent"])
    vol = float(t["quoteVolume"])
    price = float(t["lastPrice"])
    high = float(t["highPrice"])
    low = float(t["lowPrice"])
    
    print(f"\n📈 当前数据:")
    print(f"  价: ${price:.6f} | 涨幅: {chg:+.2f}% | 量: ${vol/1e6:.1f}M")
    
    # 2. K线深度分析
    k4 = get_klines(symbol, "4h", 50)
    k1 = get_klines(symbol, "1d", 7)
    
    if k4 and len(k4) > 15:
        c4 = [float(k[4]) for k in k4]
        h4 = [float(k[2]) for k in k4]
        l4 = [float(k[3]) for k in k4]
        rsi = calc_rsi(c4, 14)
        ma20 = sum(c4[-20:]) / 20
        ma50 = sum(c4[-50:]) / 50 if len(c4) >= 50 else None
        
        # 支撑阻力（最近30根4hK线的高低点）
        support, resistance = find_support_resistance(c4, c4 + h4 + l4)
        
        # 价格区间
        buy_low = round(support * 0.98, 6) if support else price * 0.95
        buy_high = round(price * 1.01, 6) if price > ma20 else round(ma20 * 1.01, 6)
        stop_loss = round(support * 0.97, 6) if support else price * 0.92
        take_profit_1 = round(price * 1.05, 6)  # 止盈1: +5%
        take_profit_2 = round(resistance * 0.99, 6) if resistance else round(price * 1.10, 6)  # 止盈2: 阻力位
        
        print(f"\n📉 技术分析:")
        print(f"  4h RSI: {rsi}")
        print(f"  MA20: ${ma20:.4f} | {'高于' if price > ma20 else '低于'}")
        if ma50: print(f"  MA50: ${ma50:.4f} | {'高于' if price > ma50 else '低于'}")
        print(f"  支撑位: ${support:.4f} | 阻力位: ${resistance:.4f}")
        
        # 7天趋势
        if k1 and len(k1) >= 3:
            pos = sum(1 for k in k1 if float(k[4]) > float(k[1]))
            print(f"  7天: {pos}涨{7-pos}跌")
        
        # 3. 盈利方案
        print(f"\n{'='*60}")
        print(f"💰 盈利方案")
        print(f"{'='*60}")
        
        print(f"\n🎯 买入区间:")
        print(f"   理想建仓: ${buy_low:.4f} - ${buy_high:.4f}")
        print(f"   当前价:   ${price:.6f}")
        
        # 根据技术面判断建仓方式
        if rsi and rsi > 65:
            print(f"   ⚠️ RSI偏高({rsi})，等回调至${buy_low:.4f}附近入场")
        elif price < ma20:
            print(f"   当前跌破MA20，等重新站上MA20(${ma20:.4f})再入场")
        else:
            print(f"   🟢 当前价在趋势上方，可现价或回调建仓")
        
        print(f"\n📊 仓位建议:")
        if chg >= 10:
            print(f"   首次: 30%总资金（涨幅偏大切仓位）")
        elif chg >= 5:
            print(f"   首次: 45%总资金（涨幅适中）")
        else:
            print(f"   首次: 35%总资金（涨幅温和）")
        print(f"   加仓: 30%+$0.003以上的回调加仓")
        print(f"   预留: 25-40%机动")
        
        print(f"\n🛑 止损: ${stop_loss:.4f} (亏损约{abs((stop_loss-price)/price*100):.1f}%)")
        if abs((stop_loss-price)/price*100) > 10:
            print(f"   ⚠️ 止损距离超过10%，检查合理性")
        
        print(f"\n📈 止盈:")
        print(f"   第一目标(${take_profit_1:.4f}): +{(take_profit_1/price-1)*100:.1f}% → 出50%")
        print(f"   第二目标(${take_profit_2:.4f}): +{(take_profit_2/price-1)*100:.1f}% → 出50%")
        
        rr = round((take_profit_1 - price) / abs(price - stop_loss), 2) if stop_loss != price else 0
        print(f"\n   R/R比: {rr}")
        if rr >= 2:
            print(f"   🟢 盈亏比合理")
        elif rr >= 1:
            print(f"   🟡 盈亏比一般，控制仓位")
        else:
            print(f"   🔴 盈亏比差，建议等更好价格")
        
        expected_return = (take_profit_1/price - 1) * (0.45 * 0.5) + (take_profit_2/price - 1) * (0.45 * 0.25) + ((0.1) * -0.05)
        print(f"\n   预期收益率: {expected_return*100:.1f}% (含止损概率)")
        
    else:
        print(f"❌ K线数据不足，无法出盈利方案")
        return
    
    print(f"\n{'='*60}")
    print(f"⏱ 预期持有: 1-3天 | 退出条件: 到止盈/止损/跌破趋势")
    print(f"{'='*60}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 读选币库今日候选
        print("从选币库读取候选池...需指定币名或待cron集成")
        print("用法: python3 tools/a3_profit_plan.py OPEN")
        sys.exit(1)
    get_profit_plan(sys.argv[1])
