#!/usr/bin/env python3
"""
每日聪明钱信号（给老李看的）
一句话：聪明钱今天对每个币的看法是买还是卖
"""
import subprocess, json, sys
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
NOW = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")

# 我们交易的币中在Binance Futures上有数据的
COINS = [
    ("GUNUSDT", "GUN"), ("FIDAUSDT", "FIDA"), ("XLMUSDT", "XLM"),
    ("ZECUSDT", "ZEC"), ("TONUSDT", "TON"), ("SUIUSDT", "SUI"),
    ("ADAUSDT", "ADA"), ("PORTALUSDT", "PORTAL"), ("OPNUSDT", "OPN"),
    ("TAOUSDT", "TAO"), ("ASRUSDT", "ASR"), ("ALLOUSDT", "ALLO"),
    ("BANKUSDT", "BANK"), ("PARTIUSDT", "PARTI"), ("HMSTRUSDT", "HMSTR"),
    ("HEIUSDT", "HEI"), ("HOMEUSDT", "HOME"), ("CUSDT", "C"),
]

BASE = "https://www.binance.com/bapi/futures/v1/public/future/smart-money/signal/overview"
PROXY = "socks5-hostname://127.0.0.1:1080"

results = []

for api_sym, short_sym in COINS:
    url = f"{BASE}?symbol={api_sym}"
    cmd = ["curl", "-sS", "--socks5-hostname", "127.0.0.1:1080",
           "--connect-timeout", "6", "--max-time", "10", url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        data = json.loads(r.stdout)
        if data.get("code") != "000000":
            continue
        dd = data["data"]
        lwp = round(dd["longProfitWhales"] / max(dd["longWhales"],1) * 100, 0)
        swp = round(dd["shortProfitWhales"] / max(dd["shortWhales"],1) * 100, 0)
        lsr = round(dd["longShortRatio"], 2)
        
        # 信号判断（简单：看哪个方向的鲸鱼在赚钱）
        if lwp >= 70 and swp <= 30:
            signal = "📈 买"  # 多头大赚，聪明钱看涨
            detail = f"多头{lwp}%在赚"
        elif swp >= 70 and lwp <= 30:
            signal = "📉 卖"  # 空头大赚，聪明钱看跌
            detail = f"空头{swp}%在赚"
        elif lwp >= 55 and lwp > swp:
            signal = "↗️ 偏多"
            detail = f"多头{lwp}% > 空头{swp}%"
        elif swp >= 55 and swp > lwp:
            signal = "↘️ 偏空"
            detail = f"空头{swp}% > 多头{lwp}%"
        else:
            signal = "⏸️ 观望"
            detail = f"多头{lwp}% vs 空头{swp}%"
        
        results.append((short_sym, signal, detail, lsr, lwp, swp))
    except:
        pass

# 输出（一句话格式，老李能看懂）
print(f"📡 聪明钱今日信号 ({NOW})")
print()
for sym, sig, det, lsr, lwp, swp in results:
  print(f"{sym}: {sig} ({det})")

# 总结
buys_count = sum(1 for _,s,_,_,_,_ in results if s == "📈 买")
sells_count = sum(1 for _,s,_,_,_,_ in results if "卖" in s or "偏空" in s)
holds_count = sum(1 for _,s,_,_,_,_ in results if s == "↗️ 偏多")
waits_count = sum(1 for _,s,_,_,_,_ in results if s == "⏸️ 观望")

print()
print(f"今日信号统计：{buys_count}个可买 | {holds_count}个偏多 | {sells_count}个偏空/卖 | {waits_count}个观望")
