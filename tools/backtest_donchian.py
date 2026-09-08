#!/usr/bin/env python3
"""
Donchian 5日通道突破 回测复现 (tools/trend_bot.py 的验证脚本)
=============================================================
用法: 在能访问 Binance API 的机器上运行 (AWS 可直接跑; 本地需走隧道)
  python3 tools/backtest_donchian.py [起始日期 YYYY-MM-DD]
输出: Donchian 5d/5d vs Buy&Hold vs 旧网格(近似) 的最终权益/回撤/交易明细
"""
import json, sys, urllib.request, time
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

def fmt(ms): return datetime.fromtimestamp(ms/1000, tz=BJT).strftime('%Y-%m-%d %H:%M')

def fetch_5m(symbol="ETHUSDT", start_ms=None, max_rows=30000):
    out, end = [], int(time.time()*1000)
    while len(out) < max_rows:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&endTime={end}&limit=1000"
        data = json.loads(urllib.request.urlopen(url, timeout=20).read())
        if not data: break
        out = data + out
        end = data[0][0] - 1
        if start_ms and data[0][0] <= start_ms: break
    return [[k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4])] for k in out]

def main():
    start_date = sys.argv[1] if len(sys.argv) > 1 else "2026-06-09"
    start_ms = int(datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=BJT).timestamp()*1000)
    print(f"fetching 5m klines from {start_date} ...")
    bars = fetch_5m(start_ms=start_ms)
    bars = [b for b in bars if b[0] >= start_ms]
    CAP = 218.0
    p0 = bars[0][4]
    n = 5*288  # 5日
    usdt, eth, pos = CAP, 0.0, 'cash'
    trades, eq = [], []
    for i in range(len(bars)):
        ts, o, h, l, c = bars[i]
        if i >= n:
            win = bars[i-n:i]
            hi = max(x[2] for x in win); lo = min(x[3] for x in win)
            if pos == 'cash' and c > hi:
                qty = int((usdt-2)/c/0.0001)*0.0001
                if qty*c >= 5:
                    eth += qty*0.999; usdt -= qty*c; pos = 'eth'
                    trades.append(('BUY', fmt(ts), c, hi, qty))
            elif pos == 'eth' and c < lo:
                qty = int(eth/0.0001)*0.0001
                if qty*c >= 5:
                    usdt += qty*c*0.999; eth -= qty; pos = 'cash'
                    trades.append(('SELL', fmt(ts), c, lo, qty))
        eq.append((ts, usdt + eth*c))
    final = usdt + eth*bars[-1][4]
    peak = max(x for _,x in eq); dd = (final/peak-1)*100
    print(f"\n== Donchian 5d/5d ({start_date} -> {fmt(bars[-1][0])}) ==")
    print(f"start ${CAP:.2f} @ ETH {p0:.2f} | final ${final:.2f} ({final/CAP*100-100:+.1f}%) | maxDD {dd:.1f}%")
    print(f"B&H: ${CAP*bars[-1][4]/p0:.2f} ({(bars[-1][4]/p0-1)*100:+.1f}%)")
    for t in trades: print(" ", t)
    print(f"trades: {len(trades)} | mode now: {pos}")

if __name__ == "__main__":
    main()
