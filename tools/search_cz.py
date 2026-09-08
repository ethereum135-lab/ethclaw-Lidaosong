#!/usr/bin/env python3
"""Search Google for CZ Binance crypto news"""
import urllib.request
import re

query = "CZ+Binance+crypto+announcement+2026+May"
url = f"https://www.google.com/search?q={query}"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode('utf-8', errors='replace')
    
    with open('/tmp/cz_search.html', 'w') as f:
        f.write(html)
    
    results = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
    print("=== CZ/Binance Search Results ===")
    for i, r in enumerate(results[:15]):
        clean = re.sub(r'<[^>]+>', '', r).strip()
        if clean:
            print(f"{i+1}. {clean}")
except Exception as e:
    print(f"ERROR: {e}")
