#!/usr/bin/env python3
"""Search DuckDuckGo and extract titles/snippets"""
import sys, re, html, urllib.parse, urllib.request

query = sys.argv[1] if len(sys.argv) > 1 else "crypto"
url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"

try:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode('utf-8', errors='replace')

    titles = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', content, re.DOTALL)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', content, re.DOTALL)

    for i, (url, title) in enumerate(titles[:8], 1):
        t = html.unescape(re.sub(r'<[^>]+>', '', title)).strip()
        print(f'{i}. {t}')
        print(f'   {url}')
        print()
    if not titles:
        print("NO_RESULTS_FOUND")
    print("---END---")
except Exception as e:
    print(f"ERROR: {e}")
