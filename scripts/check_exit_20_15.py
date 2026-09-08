import requests

syms = ['DOGEUSDT','XRPUSDT','LUNCUSDT','AVAXUSDT']

for sym in syms:
    r = requests.get('https://api.binance.com/api/v3/klines', params={'symbol': sym, 'interval': '30m', 'limit': 20}, timeout=10)
    k = r.json()
    
    # Engine excludes current forming candle: k30[:-1]
    completed = k[:-1]
    closes30 = [float(x[4]) for x in completed[-16:]]
    vols30 = [float(x[5]) for x in completed[-15:]]
    last = closes30[-1]
    
    # Trend (engine exact)
    ema7 = sum(closes30[-7:]) / 7
    ema25 = sum(closes30[-min(25, len(closes30)):]) / min(25, len(closes30))
    if last > ema7 > ema25: trend = 2
    elif last > ema7: trend = 1
    elif ema7 > last > ema25 or ema25 > last > ema7: trend = 0
    elif last < ema7 < ema25: trend = -2
    else: trend = -1
    
    # RSI(14)
    gains, losses = 0.0, 0.0
    for i in range(-15, -1):
        d = closes30[i+1] - closes30[i]
        if d > 0: gains += d
        else: losses -= d
    avg_gain = gains / 14
    avg_loss = losses / 14 if losses > 0 else 0.001
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Volume surge (engine exact)
    past = vols30[:-1]
    current_vol = vols30[-1]
    sorted_past = sorted(past)
    trim = max(1, len(past) // 7)
    baseline = sum(sorted_past[trim:-trim]) / max(len(sorted_past) - 2*trim, 1)
    vol_ratio = current_vol / baseline if baseline > 0 else 1.0
    
    print(f'{sym}:')
    print(f'  RSI={rsi:.1f} | vol_ratio={vol_ratio:.2f}x | trend={trend} | last_close={last}')
    exits = []
    if rsi < 45: exits.append('E1(RSI<45)')
    if vol_ratio < 0.6: exits.append('E2(vol<0.6)')
    if trend < 0: exits.append('E3(trend<0)')
    print(f'  Exit triggers: {exits if exits else "NONE - SAFE"}')
    
    # P&L
    costs = {'DOGEUSDT': 0.1068, 'XRPUSDT': 1.3723, 'LUNCUSDT': 0.0000714, 'AVAXUSDT': 9.17}
    if sym in costs:
        pnl = (last - costs[sym]) / costs[sym] * 100
        print(f'  P&L: {pnl:+.2f}%')
    print()
