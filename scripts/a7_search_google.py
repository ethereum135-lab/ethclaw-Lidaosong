#!/usr/bin/env python3
"""Search Google and print snippets"""
import sys, re, html, urllib.request, urllib.parse

query = sys.argv[1] if len(sys.argv) > 1 else "crypto"
url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&hl=en"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
    resp = urllib.request.urlopen(req, timeout=15)
    content = resp.read().decode('utf-8', errors='replace')
    results = re.findall(r'<div[^>]*class="[^"]*BNeawe[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL)
    found = 0
    for r in results:
        text = re.sub(r'<[^>]+>', '', r)
        text = html.unescape(text).strip()
        if len(text) > 20:
            print(text[:400])
            print("---")
            found += 1
            if found >= 5:
                break
    if found == 0:
        # Try alternate extraction
        results2 = re.findall(r'<span[^>]*class="[^"]*aCOpRe[^"]*"[^>]*>(.*?)</span>', content, re.DOTALL)
        for r in results2:
            text = re.sub(r'<[^>]+>', '', r)
            text = html.unescape(text).strip()
            if len(text) > 20:
                print(text[:400])
                print("---")
                found += 1
                if found >= 5:
                    break
    if found == 0:
        print(f"NO_RESULTS_FOUND for: {query}")
except Exception as e:
    print(f"SEARCH_FAILED for '{query}': {e}")
