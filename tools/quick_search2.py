#!/usr/bin/env python3
"""Quick search via DuckDuckGo's lite version"""
import urllib.request
import urllib.parse
import ssl
import re
import sys

query = sys.argv[1] if len(sys.argv) > 1 else "crypto"
label = sys.argv[2] if len(sys.argv) > 2 else query

# Try lite version
url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}
try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
        html = resp.read().decode('utf-8', errors='replace')
    
    # Lite version uses simple table structure
    links = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*class="result-link"[^>]*>(.*?)</a>', html, re.DOTALL)
    print(f"=== {label} ===")
    for i, (href, title) in enumerate(links[:5]):
        clean = re.sub(r'<[^>]+>', '', title).strip()
        print(f"{i+1}. {clean}")
        print(f"   {href[:120]}")
except Exception as e:
    print(f"ERROR ({type(e).__name__}): {e}")
