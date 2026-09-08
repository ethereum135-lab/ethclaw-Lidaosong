#!/usr/bin/env python3
"""A2 选币官 — 五因子评分数据计算（2026-08-23 06:0x BJT）
数据源: data-api.binance.vision 直连（Binance 24hr ticker + 1h klines）
"""
import json, urllib.request

BASE = "https://data-api.binance.vision"

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def rsi14(closes, period=14):
    if len(closes) < period+1: return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i]-closes[i-1]
        gains.append(max(d,0)); losses.append(max(-d,0))
    ag = sum(gains[:period])/period; al = sum(losses[:period])/period
    for i in range(period, len(gains)):
        ag = (ag*(period-1)+gains[i])/period
        al = (al*(period-1)+losses[i])/period
    if al == 0: return 100.0
    rs = ag/al
    return round(100 - 100/(1+rs), 1)

candidates = ["PEPEUSDT","ZECUSDT","DASHUSDT","ZENUSDT","AAVEUSDT","UNIUSDT","ENAUSDT",
              "POLUSDT","STXUSDT","XRPUSDT","SOLUSDT","ADAUSDT","PYTHUSDT","ZROUSDT",
              "TRUMPUSDT","PUMPUSDT","UTKUSDT","MUBARAKUSDT","PORTALUSDT","XLMUSDT",
              "LTCUSDT","TRXUSDT","ONDOUSDT","CVXUSDT","MOVEUSDT","ZAMAUSDT","SHELLUSDT",
              "KDAUSDT","SCUSDT","TUTUSDT"]

raw = json.load(open('/tmp/a2_ticker_raw.json'))
tick = {p['symbol']: p for p in raw if p['symbol'].endswith('USDT')}

print(f"{'币':8s} {'24h%':>7s} {'量$M':>8s} {'rp%':>5s} {'RSI14':>6s} {'volx':>5s}")
out = {}
for sym in candidates:
    t = tick.get(sym)
    if not t:
        print(f"{sym:8s} 无ticker"); continue
    chg = float(t['priceChangePercent'])
    vol = float(t['quoteVolume'])/1e6
    high = float(t['highPrice']); low = float(t['lowPrice']); last = float(t['lastPrice'])
    rp = round((last-low)/(high-low)*100,1) if high>low else 50.0
    rsi, volx = None, None
    try:
        kl = fetch(f"{BASE}/api/v3/klines?symbol={sym}&interval=1h&limit=24")
        closes = [float(k[4]) for k in kl]
        vols = [float(k[5]) for k in kl]
        rsi = rsi14(closes)
        recent3 = sum(vols[-3:])/3
        base9 = sum(vols[-15:-6])/9 if len(vols)>=15 else sum(vols)/len(vols)
        volx = round(recent3/base9, 2) if base9>0 else 0
    except Exception as e:
        rsi, volx = None, None
    out[sym] = {'chg': chg, 'vol': vol, 'rp': rp, 'rsi': rsi, 'volx': volx}
    print(f"{sym.replace('USDT',''):8s} {chg:+7.2f} {vol:8.2f} {rp:5.1f} {str(rsi):>6s} {str(volx):>5s}")

json.dump(out, open('/tmp/a2_score_data.json','w'), ensure_ascii=False, indent=1)
