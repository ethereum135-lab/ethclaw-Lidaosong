#!/usr/bin/env python3
"""Search Google and extract titles/snippets"""
import sys, re, html, urllib.parse, urllib.request

query = sys.argv[1] if len(sys.argv) > 1 else "crypto"
url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=5"

try:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode('utf-8', errors='replace')

    titles = re.findall(r'<h3[^>]*>(.*?)</h3>', content, re.DOTALL)
    snippets = re.findall(r'<div[^>]*class="[^"]*VwiC3b[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL)

    for i, (t, s) in enumerate(zip(titles, snippets), 1):
        title = html.unescape(re.sub(r'<[^>]+>', '', t)).strip()
        snippet = html.unescape(re.sub(r'<[^>]+>', '', s)).strip()
        print(f'{i}. {title}')
        print(f'   {snippet[:300]}')
        print()

    if not titles:
        print("NO_RESULTS_FOUND")
    print("---END---")
except Exception as e:
    print(f"ERROR: {e}")
