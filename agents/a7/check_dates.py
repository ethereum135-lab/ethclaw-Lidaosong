#!/usr/bin/env python3
"""A7 Sentinel - Check article dates"""
import urllib.request, json, re

def fetch_text(url, timeout=15):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')

# Check Saylor article dates
sources = [
    # Google News search for Saylor sell
    ('https://news.google.com/search?q=Michael+Saylor+sell+Bitcoin+2026&hl=en-US&gl=US&ceid=US:en', 'SAYLOR'),
    # Check Google News for Trump crypto policy
    ('https://news.google.com/search?q=Trump+crypto+bitcoin+2026+May&hl=en-US&gl=US&ceid=US:en', 'TRUMP'),
    # Check latest hack news
    ('https://news.google.com/search?q=crypto+bridge+hack+2026+May+25&hl=en-US&gl=US&ceid=US:en', 'HACK'),
    # Check ETF news
    ('https://news.google.com/search?q=Bitcoin+ETF+outflows+2026+May&hl=en-US&gl=US&ceid=US:en', 'ETF'),
]

for url, label in sources:
    try:
        html = fetch_text(url)
        # Extract article titles and timestamps
        # Google News uses specific markup
        articles = re.findall(r'<article[^>]*>.*?</article>', html, re.DOTALL)
        if articles:
            for art in articles[:5]:
                title_m = re.search(r'<h3[^>]*>(.*?)</h3>', art, re.DOTALL) or re.search(r'<a[^>]*aria-label="([^"]+)"', art)
                time_m = re.search(r'<time[^>]*datetime="([^"]+)"', art)
                source_m = re.search(r'<span[^>]*class="[^"]*source[^"]*"[^>]*>(.*?)</span>', art, re.DOTALL)
                title = title_m.group(1) if title_m else 'N/A'
                title = re.sub(r'<[^>]+>', '', title).strip()[:100]
                pub_time = time_m.group(1) if time_m else 'no timestamp'
                src = source_m.group(1) if source_m else 'unknown'
                src = re.sub(r'<[^>]+>', '', src).strip()
                print(f'[{label}] {pub_time} | {title}')
        else:
            print(f'[{label}] No articles found in HTML (length={len(html)})')
            # Fallback: try to find any time tags
            times = re.findall(r'<time[^>]*datetime="([^"]+)"', html)
            titles = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
            for i in range(min(3, len(titles))):
                clean = re.sub(r'<[^>]+>', '', titles[i]).strip()[:100]
                t = times[i] if i < len(times) else 'no time'
                print(f'  [{label}] {t} | {clean}')
    except Exception as e:
        print(f'[{label}] ERROR: {e}')
    print()
