#!/usr/bin/env python3
"""Parse DDG HTML results from file."""
import sys, re

with open(sys.argv[1], 'r') as f:
    content = f.read()

# Try to find result links in DuckDuckGo HTML
results = re.findall(r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', content, re.DOTALL)
if results:
    for i, (url, title) in enumerate(results[:10]):
        clean_title = re.sub(r'<[^>]+>', '', title).strip()
        print(f'{i+1}. {clean_title}')
        print(f'   URL: {url}')
else:
    # Try another pattern
    results2 = re.findall(r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]*)"[^>]*>', content, re.DOTALL)
    if not results2:
        results2 = re.findall(r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*result__a[^"]*"[^>]*>', content, re.DOTALL)
    titles2 = re.findall(r'class="result__a"[^>]*>(.*?)</a>', content, re.DOTALL)
    
    # Fall back to extracting all links
    print(f"DDG content length: {len(content)}")
    # Show sample
    idx = content.find('result')
    if idx >= 0:
        print(f"Sample around 'result': {content[idx:idx+400]}")
    else:
        # Show title
        t = re.findall(r'<title>(.*?)</title>', content)
        if t:
            print(f"Title: {t[0]}")
        print(f"First 500 chars: {content[:500]}")
