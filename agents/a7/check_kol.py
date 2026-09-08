#!/usr/bin/env python3
"""A7 Sentinel - KOL check and additional news"""
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

# Check for recent stories about KOLs via news search
# Use duckduckgo lite API
try:
    html = fetch_text('https://lite.duckduckgo.com/lite/?q=Elon+Musk+crypto+site:twitter.com+OR+site:x.com&t=h_')
    # Extract links
    links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html)
    # Filter for result-like links
    for href, text in links[:10]:
        if 'twitter.com' in href or 'x.com' in href or 'twitter' in text.lower():
            print(f'TWITTER: {text.strip()[:100]}')
except Exception as e:
    print(f'DDG_ERR:{e}')

# Also search for CZ/BNB specific
try:
    html = fetch_text('https://lite.duckduckgo.com/lite/?q=CZ+Binance+announcement+2026&t=h_')
    links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html)
    for href, text in links[:15]:
        clean = re.sub(r'<[^>]+>', '', text).strip()
        if clean and len(clean) > 15:
            print(f'CZ: {clean[:120]}')
except Exception as e:
    print(f'DDG2_ERR:{e}')

# Check Tucker Carlson / Trump crypto mentions
try:
    html = fetch_text('https://lite.duckduckgo.com/lite/?q=Trump+crypto+bitcoin+2026&t=h_')
    links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html)
    for href, text in links[:15]:
        clean = re.sub(r'<[^>]+>', '', text).strip()
        if clean and len(clean) > 15:
            print(f'TRUMP: {clean[:120]}')
except Exception as e:
    print(f'DDG3_ERR:{e}')

# Check Saylor
try:
    html = fetch_text('https://lite.duckduckgo.com/lite/?q=Michael+Saylor+bitcoin+2026&t=h_')
    links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html)
    for href, text in links[:15]:
        clean = re.sub(r'<[^>]+>', '', text).strip()
        if clean and len(clean) > 15:
            print(f'SAYLOR: {clean[:120]}')
except Exception as e:
    print(f'DDG4_ERR:{e}')

# Additional check: crypto hack news
try:
    html = fetch_text('https://lite.duckduckgo.com/lite/?q=crypto+hack+exploit+2026+May+25&t=h_')
    links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html)
    for href, text in links[:15]:
        clean = re.sub(r'<[^>]+>', '', text).strip()
        if clean and len(clean) > 15:
            print(f'HACK: {clean[:120]}')
except Exception as e:
    print(f'DDG5_ERR:{e}')
