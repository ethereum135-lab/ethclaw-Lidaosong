#!/usr/bin/env python3
"""Search for crypto news and celebrity tweets"""
import urllib.request, urllib.parse, re, json, sys

results = []

searches = [
    ("Elon Musk crypto bitcoin 2026", "tweets"),
    ("CZ Binance announcement June 2026", "tweets"),
    ("Michael Saylor bitcoin strategy 2026", "tweets"),
    ("crypto hack stolen million 2026", "news"),
    ("crypto regulation SEC 2026", "news"),
    ("blockchain upgrade mainnet 2026", "news"),
]

for query, cat in searches:
    url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        # Extract results from lite version
        links = re.findall(r'class="result-link"[^>]*href="([^"]+)"[^>]*>([^<]+)', html)
        snippets = re.findall(r'class="result-snippet"[^>]*>([^<]+)', html)
        for i, (lnk, title) in enumerate(links[:3]):
            snippet = snippets[i] if i < len(snippets) else ""
            results.append({
                "query": query,
                "category": cat,
                "title": title.strip(),
                "url": lnk,
                "snippet": snippet.strip()
            })
    except Exception as e:
        results.append({
            "query": query,
            "category": cat,
            "error": str(e)
        })

print(json.dumps(results, indent=2))
