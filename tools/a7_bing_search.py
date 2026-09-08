#!/usr/bin/env python3
"""Search Bing for crypto news"""
import urllib.request, urllib.parse, re, json

results = []

searches = [
    ("Elon Musk bitcoin dogecoin crypto", "tweets"),
    ("CZ Binance announcement crypto", "tweets"),
    ("Michael Saylor bitcoin strategy", "tweets"),
    ("crypto hack stolen", "news"),
    ("crypto regulation SEC", "news"),
    ("blockchain upgrade", "news"),
]

for query, cat in searches:
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&count=5"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        # Extract b_algo results
        items = re.findall(r'<li class="b_algo"[^>]*>.*?<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', html, re.DOTALL)
        for url, title in items[:3]:
            results.append({
                "query": query,
                "category": cat,
                "title": title.strip(),
                "url": url
            })
        if not items:
            results.append({"query": query, "category": cat, "note": "no results found"})
    except Exception as e:
        results.append({"query": query, "category": cat, "error": str(e)})

print(json.dumps(results, indent=2, ensure_ascii=False))
