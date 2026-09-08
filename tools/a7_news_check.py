#!/usr/bin/env python3
"""A7舆情官 — 快速抓取新闻和社交媒体数据"""
import json
import urllib.request
import ssl
import sys

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        resp = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
        return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return f"FAILED: {e}"

results = {}

# 1. 搜索Elon Musk相关新闻
print("=== ELON MUSK CRYPTO NEWS ===")
data = fetch("https://news.google.com/rss/search?q=Elon+Musk+crypto+bitcoin+doge+tweet&hl=en-US&gl=US&ceid=US:en")
if data and not data.startswith("FAILED"):
    import re
    titles = re.findall(r'<title>(.*?)</title>', data)
    for t in titles:
        if 'Google News' not in t:
            print(f"  {t}")
else:
    print(f"  {data}")

# 2. 搜索CZ/币安相关新闻
print("\n=== CZ BINANCE NEWS ===")
data = fetch("https://news.google.com/rss/search?q=CZ+Binance+announcement+listing+crypto&hl=en-US&gl=US&ceid=US:en")
if data and not data.startswith("FAILED"):
    import re
    titles = re.findall(r'<title>(.*?)</title>', data)
    for t in titles:
        if 'Google News' not in t:
            print(f"  {t}")
else:
    print(f"  {data}")

# 3. 搜索黑客/监管新闻
print("\n=== HACK + REGULATION NEWS ===")
data = fetch("https://news.google.com/rss/search?q=crypto+hack+exploit+regulation+SEC+ban&hl=en-US&gl=US&ceid=US:en")
if data and not data.startswith("FAILED"):
    import re
    titles = re.findall(r'<title>(.*?)</title>', data)
    for t in titles:
        if 'Google News' not in t:
            print(f"  {t}")
else:
    print(f"  {data}")

print("\n=== DONE ===")
