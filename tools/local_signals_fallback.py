#!/usr/bin/env python3
"""
Local Binance API fallback for signal scanning when SSH is down.
Uses direct Binance public API (no SOCKS5 needed) to update signals.json
with current prices, 24h changes, and volume data.
Output: data/signals.json with fresh scanned_at timestamp + "(SSH DOWN)" flag
"""
import json, os, sys, subprocess
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load existing signals to preserve categories and enrichments
try:
    with open(f'{BASE}/data/signals.json') as f:
        existing = json.load(f)
except:
    existing = {'results': [], 'summary': {}}

# 全量24hr行情走gzip压缩（隧道慢但压缩后~30s可下完；不压缩的1.2MB会超时）
def _fetch_tickers(proxy):
    # SSH断时SOCKS5不可用 → proxy=False直连 data-api.binance.vision（无地理451限制）
    # proxy=True走SOCKS5隧道→api.binance.com（隧道通时优先）
    url = 'https://api.binance.com/api/v3/ticker/24hr'
    if not proxy:
        url = 'https://data-api.binance.vision/api/v3/ticker/24hr'
    cmd = ['curl', '-s', '--compressed', '--connect-timeout', '8', '--max-time', '60', url]
    if proxy:
        cmd.insert(2, '--socks5-hostname')
        cmd.insert(3, '127.0.0.1:1080')
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return None
    if r.stdout:
        try:
            parsed = json.loads(r.stdout)
            # ticker/24hr 期望格式是数组；451受限/限流返回的是错误对象(dict)，
            # 必须验证是 非空list 才算有效响应，否则按失败走fallback
            if isinstance(parsed, list) and parsed:
                return r
        except (ValueError, TypeError):
            pass
        return None
    return None

result = _fetch_tickers(proxy=True) or _fetch_tickers(proxy=False)

if result is None:
    # Can't even reach Binance public API - just update timestamp
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    existing['scanned_at'] = f'{now} (SSH DOWN + API FAILED)'
    with open(f'{BASE}/data/signals.json', 'w') as f:
        json.dump(existing, f, indent=2)
    print('❌ Binance public API also unreachable')
    sys.exit(1)

all_tickers = json.loads(result.stdout)
ticker_map = {t['symbol']: t for t in all_tickers}

# Map existing results to fresh data
exclude_keywords = ['UP','DOWN','BULL','BEAR','BUSD','USDC','TUSD','DAI','FDUSD','USDP','AEUR','EUR','GBP','AUD','BRL','TRY','ZAR','SAND','IDRT','USTC','USDD']

fresh_results = []
updated_count = 0
stale_count = 0
preserved_categories = {}

for r in existing.get('results', []):
    sym = r['symbol']
    preserved_categories[sym] = r.get('category', 'other')
    usdt_pair = f'{sym}USDT'
    ticker = ticker_map.get(usdt_pair)
    
    if ticker:
        try:
            price = float(ticker['lastPrice'])
            vol = float(ticker['quoteVolume'])
            change = float(ticker['priceChangePercent'])
            r['price'] = price
            r['volume_24h'] = vol
            r['gain_24h'] = change
            
            # Recalculate basic score based on volume + gain
            base_score = min(int(abs(change) * 2), 30)
            vol_score = min(int(vol / 500000), 20)
            momentum = min(int(abs(change) * 1.5) if change > 0 else 0, 20)
            r['total_score'] = min(base_score + vol_score + momentum, 100)
            
            # Recalculate level
            if r['total_score'] >= 70:
                r['level'] = 'STRONG'
            elif r['total_score'] >= 45:
                r['level'] = 'SIGNAL'
            elif r['total_score'] >= 25:
                r['level'] = 'WATCH'
            else:
                r['level'] = 'PASS'
            
            # Update or set signals dict
            if 'signals' not in r:
                r['signals'] = {}
            r['signals']['momentum_surge'] = {
                'score': momentum,
                'detail': f'24h+{change:.1f}% (local fallback)'
            }
            r['signals']['vol_breakout'] = {
                'score': vol_score,
                'detail': f'vol=${vol:,.0f} (local fallback)'
            }
            
            r['scanned_at'] = 'local_fallback'
            updated_count += 1
        except (ValueError, KeyError):
            stale_count += 1
    else:
        # Coin not on Binance or not traded - don't touch
        stale_count += 1
    
    fresh_results.append(r)

now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

output = {
    'scanned_at': f'{now}',
    'total_scanned': len(fresh_results),
    'summary': {
        'strong': sum(1 for r in fresh_results if r.get('level') == 'STRONG'),
        'signal': sum(1 for r in fresh_results if r.get('level') == 'SIGNAL'),
        'watch': sum(1 for r in fresh_results if r.get('level') == 'WATCH'),
        'pass': sum(1 for r in fresh_results if r.get('level') == 'PASS'),
        'error': existing.get('summary', {}).get('error', 0),
        '_enrich_boosted': existing.get('summary', {}).get('_enrich_boosted', 0),
        '_enrich_upgraded': existing.get('summary', {}).get('_enrich_upgraded', 0)
    },
    'results': fresh_results,
    '_ssh_down_fallback': True,
    '_updated_via': 'local_binance_public_api'
}

with open(f'{BASE}/data/signals.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f'✅ signals.json refreshed via local Binance API ({updated_count}/{len(fresh_results)} coins updated) - SSH DOWN fallback')
