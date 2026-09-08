#!/usr/bin/env python3
"""Fetch latest crypto news via urllib"""
import json, urllib.request, re

urls = [
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
]

for name, url in urls:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode('utf-8', errors='ignore')
        titles = re.findall(r'<title[^>]*>(.*?)</title>', html, re.DOTALL)
        print(f'=== {name} ===')
        for i, t in enumerate(titles[:8], 1):
            clean = re.sub(r'<[^>]+>', '', t).strip()
            if clean and 'CoinTelegraph' not in clean and 'CoinDesk' not in clean:
                print(f'{i}. {clean}')
        print()
    except Exception as e:
        print(f'{name} error: {e}')
        print()
