#!/usr/bin/env python3
"""A2 Score candidates for today's prime pool"""
import json, math

with open('data/coin_pool_binance.json') as f:  # 原coin_pool_prime.json→改名, 2026-06-14
    data = json.load(f)
pool = data['pool']

# Sector weights from hot_sectors.md (2026-05-30)
sector_weight = {
    'layer1': 0.9, 'meme': 0.7, 'ai': 1.5, 'defi': 0.6, 'gamefi': 0.4,
    'layer2': 0.5, 'rwa': 0.3, 'oracle': 0.7, 'depin': 1.0, 'privacy': 0.4,
    'cex': 0.5, 'cosmos': 0.6, 'btc_ecosystem': 0.3, 'storage': 1.3,
    'nft': 0.3, 'crosschain': 0.5, 'lsd': 0.5, 'pow': 0.8, 'other': 0.7,
}

scored = []
for coin in pool:
    vol = coin['volume_24h_usd']
    chg = coin['change_24h']
    cat = coin['category']
    status = coin['status']

    # Volume score (0-100) - log scale
    vol_norm = min(100, math.log10(max(1, vol)) / math.log10(1e9) * 100)

    # Price change score (0-100)
    if chg > 20:
        price_score = max(0, 100 - (chg - 20) * 3)
    else:
        price_score = max(0, min(100, chg * 5))

    sw = sector_weight.get(cat, 0.7)
    status_penalty = -30 if status == 'warning' else 0
    score = vol_norm * 0.30 + price_score * 0.35 + sw * 20 + status_penalty + 10

    notes = []
    if chg > 20:
        notes.append(chr(22823)+chr(28072)+f'{chg:.1f}%')
    if chg > 50:
        notes.append(chr(26497)+chr(31471)+chr(27874)+chr(21160))
    if status == 'warning':
        notes.append(chr(9888)+chr(65039)+chr(35686)+chr(21578))
    if cat in ('rwa', 'btc_ecosystem') and chg < -2:
        notes.append(chr(20919)+chr(36187)+chr(36947)+chr(32487)+chr(36300))
    if cat == 'gamefi' and chg < -5:
        notes.append('GameFi暴跌不碰')
    if cat == 'privacy' and chg < -2:
        notes.append('ZEC假底')
    if cat == 'other':
        notes.append('other赛道')

    scored.append({
        'symbol': coin['symbol'],
        'category': cat,
        'vol': vol,
        'chg': chg,
        'price': coin['price'],
        'score': round(score, 1),
        'vol_score': round(vol_norm, 1),
        'price_score': round(price_score, 1),
        'notes': '; '.join(notes),
        'status': status
    })

scored.sort(key=lambda x: x['score'], reverse=True)

tier1 = [c for c in scored if c['score'] >= 55]
tier2 = [c for c in scored if 40 <= c['score'] < 55 and c['status'] != 'warning']
tier3 = [c for c in scored if 25 <= c['score'] < 40 and c['status'] != 'warning']
observe = [c for c in scored if c['score'] < 25 or c['status'] == 'warning']

print('=== TIER 1: Strong Candidates (score>=55) ===')
for c in tier1:
    cat_clean = c['category'].ljust(12)
    print(f"{c['symbol']:>8} | {cat_clean} | Score:{c['score']:>5.1f} | Vol:${c['vol']:>11,.0f} | Chg:{c['chg']:>+7.2f}% | {c['notes']}")

print(f'\nTotal T1: {len(tier1)}')
print(f'Total T2: {len(tier2)}')
print(f'Total T3: {len(tier3)}')
print(f'Total Observe: {len(observe)}')
