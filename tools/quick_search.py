#!/usr/bin/env python3
"""Quick targeted search for A7 - single queries"""
import urllib.request
import urllib.parse
import re
import sys

query = sys.argv[1] if len(sys.argv) > 1 else "crypto"
label = sys.argv[2] if len(sys.argv) > 2 else query

url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}
try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as resp:
        html = resp.read().decode('utf-8', errors='replace')
    
    titles = re.findall(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
    snippets = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
    
    print(f"=== {label} ===")
    for i in range(min(len(titles), 5)):
        title = re.sub(r'<[^>]+>', '', titles[i]).strip()
        snip = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ''
        print(f"{i+1}. {title}")
        print(f"   {snip[:200]}")
except Exception as e:
    print(f"ERROR: {e}")
