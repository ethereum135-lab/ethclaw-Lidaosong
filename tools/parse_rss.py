#!/usr/bin/env python3
"""Extract recent news from Google News RSS without pipe issues."""
import sys, re

html = sys.stdin.read()

# Extract items
items = re.findall(r'<item>(.*?)</item>', html, re.DOTALL)
for item in items[:20]:
    title = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
    link = re.search(r'<link>(.*?)</link>', item, re.DOTALL)
    pdate = re.search(r'<pubDate>(.*?)</pubDate>', item, re.DOTALL)
    t = title.group(1).strip() if title else 'N/A'
    l = link.group(1).strip() if link else ''
    d = pdate.group(1).strip() if pdate else 'N/A'
    if 'Google News' not in t and len(t) > 10:
        print(f'{d}')
        print(f'  {t[:200]}')
        print()
