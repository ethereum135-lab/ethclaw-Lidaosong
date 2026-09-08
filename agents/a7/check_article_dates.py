#!/usr/bin/env python3
"""Check specific article dates"""
import urllib.request, re

def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')

# Check the Saylor "sell" article from Cointelegraph search
# Try a direct search on CT
try:
    html = fetch('https://cointelegraph.com/search?query=Michael+Saylor+sell', 10)
    titles = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
    times = re.findall(r'<time[^>]*datetime="([^"]+)"', html)
    print('=== Cointelegraph Saylor Search ===')
    for i in range(min(5, len(titles))):
        t = times[i] if i < len(times) else 'no time'
        clean = re.sub(r'<[^>]+>', '', titles[i]).strip()[:100]
        print(f'{t} | {clean}')
except Exception as e:
    print(f'CT Search: {e}')

# Try cryptoslate for Saylor sell news
try:
    html = fetch('https://cryptoslate.com/?s=Michael+Saylor+sell', 10)
    titles = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
    times = re.findall(r'<time[^>]*datetime="([^"]+)"', html)
    print()
    print('=== Cryptoslate Saylor Search ===')
    for i in range(min(5, len(titles))):
        t = times[i] if i < len(times) else 'no time'
        clean = re.sub(r'<[^>]+>', '', titles[i]).strip()[:100]
        print(f'{t} | {clean}')
except Exception as e:
    print(f'CSlate: {e}')

# Check The Block for Saylor news
try:
    html = fetch('https://www.theblock.co/search?q=Michael+Saylor', 10)
    titles = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
    times = re.findall(r'<time[^>]*datetime="([^"]+)"', html)
    print()
    print('=== TheBlock Saylor Search ===')
    for i in range(min(5, len(titles))):
        t = times[i] if i < len(times) else 'no time'
        clean = re.sub(r'<[^>]+>', '', titles[i]).strip()[:100]
        print(f'{t} | {clean}')
except Exception as e:
    print(f'TheBlock: {e}')

# Also check CoinDesk for ETF outflow news
try:
    html = fetch('https://www.coindesk.com/search/?q=Bitcoin+ETF+outflows+6+day', 10)
    titles = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
    times = re.findall(r'<time[^>]*datetime="([^"]+)"', html)
    print()
    print('=== CoinDesk ETF Search ===')
    for i in range(min(5, len(titles))):
        t = times[i] if i < len(times) else 'no time'
        clean = re.sub(r'<[^>]+>', '', titles[i]).strip()[:100]
        print(f'{t} | {clean}')
except Exception as e:
    print(f'CoinDesk: {e}')
