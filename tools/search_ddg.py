#!/usr/bin/env python3
"""Search DuckDuckGo for crypto news (no JS needed)"""
import urllib.request
import urllib.parse
import re

def search_ddg(query, label):
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        
        # DuckDuckGo uses <a class="result__a"> for titles
        titles = re.findall(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
        snippets = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        
        print(f"\n=== {label} ===")
        for i in range(min(len(titles), 8)):
            title = re.sub(r'<[^>]+>', '', titles[i]).strip()
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ''
            print(f"{i+1}. {title}")
            print(f"   {snippet[:200]}")
            print()
        return titles, snippets
    except Exception as e:
        print(f"ERROR {label}: {e}")
        return [], []

# 1. Elon Musk crypto
search_ddg("Elon Musk crypto bitcoin doge 2026 May", "Elon Musk Crypto News")

# 2. CZ Binance
search_ddg("CZ Binance crypto announcement 2026 May", "CZ Binance News")

# 3. Michael Saylor / Trump crypto
search_ddg("Michael Saylor Bitcoin 2026 May", "Michael Saylor News")
search_ddg("Trump crypto 2026 May", "Trump Crypto News")

# 4. Crypto hacks
search_ddg("crypto hack exploit 2026 May", "Crypto Hack News")

# 5. Crypto regulation SEC
search_ddg("crypto regulation SEC 2026 May", "Crypto Regulation News")

# 6. Crypto upgrades mainnet
search_ddg("crypto mainnet launch upgrade 2026 May", "Crypto Upgrade News")
