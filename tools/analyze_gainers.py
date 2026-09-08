#!/usr/bin/env python3
"""Analyze top gainers: what's driving them?"""
import json, urllib.request, sys

# Get top gainers
req = urllib.request.Request("https://api.binance.com/api/v3/ticker/24hr", 
                              headers={"User-Agent": "Mozilla/5.0"})
data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())

usdt = [t for t in data if t['symbol'].endswith('USDT') 
        and float(t['priceChangePercent']) > 5
        and t['symbol'].replace('USDT','') not in ['USDC','USDT','DAI','BUSD','FDUSD','TUSD']]
usdt.sort(key=lambda x: -float(x['priceChangePercent']))

print("=" * 60)
print(f"📊 币安24h涨幅TOP15 — 为什么会涨?")
print(f"扫描时间: {__import__('datetime').datetime.now().strftime('%H:%M')} BJT")
print("=" * 60)

for t in usdt[:15]:
    sym = t['symbol'].replace('USDT', '')
    chg = float(t['priceChangePercent'])
    vol = float(t['quoteVolume'])
    price = float(t['lastPrice'])
    high = float(t['highPrice'])
    low = float(t['lowPrice'])
    vol_q = float(t['volume'])
    
    # Get 1h klines for momentum analysis
    kurl = f"https://api.binance.com/api/v3/klines?symbol={t['symbol']}&interval=1h&limit=24"
    kreq = urllib.request.Request(kurl, headers={"User-Agent": "Mozilla/5.0"})
    kdata = json.loads(urllib.request.urlopen(kreq, timeout=5).read().decode())
    closes = [float(k[4]) for k in kdata]
    kvols = [float(k[5]) for k in kdata]
    avg_vol = sum(kvols) / len(kvols) if kvols else 1
    vol_ratio = kvols[-1] / avg_vol if avg_vol > 0 else 0
    
    # Categorize the rally type
    if chg > 50:
        rally_type = "🚀 爆拉（高风险，可能是垃圾币脉冲）"
    elif chg > 20:
        rally_type = "🔥 强势拉升（可能已有叙事驱动）"
    elif chg > 10:
        rally_type = "📈 健康上涨（值得研究叙事）"
    else:
        rally_type = "📊 温和上涨"
    
    # Momentum consistency
    recent_up = sum(1 for i in range(max(0,len(closes)-4), len(closes)) 
                    if closes[i] > closes[i-1]) if len(closes) >= 4 else 0
    momentum = "连续放量上涨" if recent_up >= 3 and vol_ratio > 1.5 else \
               "有量有价" if vol_ratio > 1.2 else \
               "量能一般" if vol_ratio > 0.8 else \
               "缩量上涨（谨慎）"
    
    print(f"\n{'─'*50}")
    print(f"{sym:12s} +{chg:>6.2f}%  |  ${price:<12.8f}  |  vol=${vol:>12,.0f}")
    print(f"  24h区间: ${low:.8f} ~ ${high:.8f}")
    print(f"  动能量: {momentum} | 时均量比: {vol_ratio:.1f}x")
    print(f"  类型: {rally_type}")
    print(f"  成交量排名: {'高' if vol > 10_000_000 else '中' if vol > 1_000_000 else '低'}")

print(f"\n{'='*60}")
print(f"结论: 哪些涨有逻辑支撑，哪些是脉冲")
print(f"{'='*60}")
