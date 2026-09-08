#!/usr/bin/env python3
"""A7舆情官 — 快速轻量抓取"""
import urllib.request
import re
import sys

def quick_fetch(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None

# Try multiple sources for crypto news
sources = [
    ("Coindesk", "https://www.coindesk.com/"),
    ("CoinTelegraph", "https://cointelegraph.com/"),
    ("Decrypt", "https://decrypt.co/"),
    ("TheBlock", "https://www.theblock.co/"),
]

for name, url in sources:
    try:
        html = quick_fetch(url)
        if html:
            # Extract headlines - look for h2/h3 tags or common patterns
            headlines = re.findall(r'<h[23][^>]*>(.*?)</h[23]>', html, re.DOTALL)
            clean = [re.sub(r'<[^>]+>', '', h).strip() for h in headlines]
            clean = [h for h in clean if len(h) > 10 and any(w in h.lower() for w in ['crypto','bitcoin','eth','hack','sec','regul','ban','dog','elon','cz ','binance'])]
            if clean:
                print(f"=== {name} ===")
                for h in clean[:5]:
                    print(f"  • {h}")
        else:
            print(f"{name}: no data")
    except:
        print(f"{name}: error")

print("\n=== DONE ===")
