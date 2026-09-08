#!/usr/bin/env python3
"""Fetch crypto news from RSS feeds"""
import urllib.request, xml.etree.ElementTree as ET, re

feeds = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
]

for name, url in feeds:
    print(f"=== {name} RSS ===")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read()
        root = ET.fromstring(content)
        # Handle RSS 2.0 and Atom
        ns = {}
        items = root.findall('.//item') or root.findall('.//entry')
        for i, item in enumerate(items[:5], 1):
            title_el = item.find('title')
            link_el = item.find('link')
            desc_el = item.find('description')
            title = title_el.text.strip() if title_el is not None and title_el.text else ''
            if link_el is not None:
                link = link_el.text if link_el.text else (link_el.get('href', '') if hasattr(link_el, 'get') else '')
            else:
                link = ''
            desc = ''
            if desc_el is not None and desc_el.text:
                desc = re.sub(r'<[^>]+>', '', desc_el.text).strip()[:200]
            print(f'{i}. {title[:120]}')
            if desc:
                print(f'   {desc}')
            print()
    except Exception as e:
        # Try alternate URL format
        try:
            alt_url = url.replace('https://', 'https://')
            req = urllib.request.Request(alt_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as r:
                content = r.read()
            root = ET.fromstring(content)
            items = root.findall('.//item') or root.findall('.//entry')
            for i, item in enumerate(items[:5], 1):
                title_el = item.find('title')
                link_el = item.find('link')
                title = title_el.text.strip() if title_el is not None and title_el.text else ''
                if link_el is not None:
                    link = link_el.text if link_el.text else ''
                else:
                    link = ''
                print(f'{i}. {title[:120]}')
                print()
        except Exception as e2:
            print(f'Error: {e}')
