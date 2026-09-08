#!/usr/bin/env python3
"""Fetch Binance 24h ticker top gainers"""
import json, urllib.request

try:
    req = urllib.request.Request("https://api.binance.com/api/v3/ticker/24hr", 
                                  headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    
    exclude_suffixes = ('UPUSDT','DOWNUSDT','BULLUSDT','BEARUSDT','USDCUSDT','DAIUSDT',
                        'FDUSDUSDT','TUSDUSDT','USDPUSDT','BUSDUSDT','EURUSDT','GBPUSDT',
                        'JPYUSDT','AUDUSDT')
    
    usdt_pairs = [t for t in data if t['symbol'].endswith('USDT') 
                  and not any(t['symbol'].endswith(x) for x in exclude_suffixes)]
    
    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['priceChangePercent']), reverse=True)
    
    for p in sorted_pairs[:15]:
        vol = float(p['quoteVolume'])
        print(f"{p['symbol']}: {p['priceChangePercent']}% | Vol={vol:.0f}USDT | Price={p['lastPrice']}")
except Exception as e:
    print(f"BINANCE_FAILED: {e}")
