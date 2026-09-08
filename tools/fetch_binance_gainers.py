#!/usr/bin/env python3
"""Fetch Binance 24hr ticker and show top gainers"""
import json, urllib.request, sys

stablecoins = ['USDCUSDT','BUSDUSDT','DAIUSDT','FDUSDUSDT','TUSDUSDT','USDPUSDT','GUSDUSDT','PAXGUSDT']
exclude_keywords = ['UP','DOWN','BULL','BEAR','LUNA','LUNA2']

try:
    req = urllib.request.Request("https://api.binance.com/api/v3/ticker/24hr",
                                 headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read().decode())
except Exception:
    # SOCKS5 fallback
    import subprocess
    try:
        r = subprocess.run(
            ['curl', '-s', '--connect-timeout', '10', '--max-time', '25',
             '--socks5-hostname', '127.0.0.1:1080',
             'https://api.binance.com/api/v3/ticker/24hr'],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout:
            data = json.loads(r.stdout)
        else:
            print("Binance unreachable")
            sys.exit(1)
    except:
        print("Binance unreachable")
        sys.exit(1)
    
    pairs = []
    for d in data:
        sym = d['symbol']
        if not sym.endswith('USDT'): continue
        if sym in stablecoins: continue
        if any(kw in sym for kw in exclude_keywords): continue
        pct = float(d['priceChangePercent'])
        vol = float(d['quoteVolume'])
        price = float(d['lastPrice'])
        pairs.append((sym, pct, vol, price))
    
    pairs.sort(key=lambda x: x[1], reverse=True)
    
    print("=== 币安24h涨幅TOP20 ===")
    for i, (sym, pct, vol, price) in enumerate(pairs[:20]):
        vol_str = f'{vol/1e6:.1f}M' if vol > 1e6 else f'{vol/1e3:.1f}K'
        print(f'{i+1}. {sym:15s} +{pct:6.2f}%  Vol: {vol_str}  Price: {price:.8f}')
    
    # Check if TOP3 has unusual (>50%) gainers
    top3 = pairs[:3]
    unusual = [(sym, pct) for sym, pct, _, _ in top3 if pct > 50]
    if unusual:
        print(f"\n⚠ UNUSUAL: {[f'{s}+{p:.1f}%' for s,p in unusual]}")
    else:
        print("\nNo unusual gainers (>50%) in TOP3.")
    
except Exception as e:
    print(f"ERROR:{e}")
    sys.exit(1)
