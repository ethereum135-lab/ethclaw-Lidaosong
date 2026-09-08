#!/usr/bin/env python3
"""A7 Sentinel - Scrape monitoring data"""
import urllib.request, json, re

def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())

def fetch_text(url, timeout=15):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')

results = []

# 1. F&G Index
try:
    data = fetch_json('https://api.alternative.me/fng/?limit=1')
    val = int(data['data'][0]['value'])
    cls = data['data'][0]['value_classification']
    results.append(f'FNG:{val}|{cls}')
except Exception as e:
    results.append(f'FNG_ERR:{e}')

# 2. CoinGecko prices
try:
    data = fetch_json('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,dogecoin&vs_currencies=usd&include_24hr_change=true')
    for coin, info in data.items():
        chg = info.get('usd_24h_change', 'N/A')
        chg_str = f'{chg:.2f}%' if isinstance(chg, (int, float)) else str(chg)
        results.append(f'CG_{coin}:${info["usd"]}|24h:{chg_str}')
except Exception as e:
    results.append(f'CG_ERR:{e}')

# 3. CoinGecko trending
try:
    data = fetch_json('https://api.coingecko.com/api/v3/search/trending')
    coins = []
    for c in data.get('coins', [])[:5]:
        item = c['item']
        coins.append(f'{item["symbol"]}({item.get("market_cap_rank","N/A")})')
    results.append(f'TRENDING:{" ".join(coins)}')
except Exception as e:
    results.append(f'TREND_ERR:{e}')

# 4. Cointelegraph RSS
try:
    html = fetch_text('https://cointelegraph.com/rss')
    titles = re.findall(r'<title>(.*?)</title>', html)
    ct_titles = [t.strip() for t in titles[1:6]]
    for t in ct_titles:
        results.append(f'CT:{t}')
except Exception as e:
    results.append(f'CT_ERR:{e}')

# 5. Check if CryptoPanic free tier works (no API key)
try:
    data = fetch_json('https://cryptopanic.com/api/v1/posts/?auth_token=&kind=news&filter=rising')
    for p in data.get('results', [])[:3]:
        results.append(f'CP:{p["title"]}|{p.get("source","")}')
except Exception as e:
    results.append(f'CP_ERR:{e}')

print('\n'.join(results))
