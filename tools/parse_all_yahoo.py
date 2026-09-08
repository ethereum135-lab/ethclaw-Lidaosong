#!/usr/bin/env python3
"""Parse Yahoo search results for A7 monitoring"""
import re, sys

def parse_yahoo(filepath, label):
    with open(filepath) as f:
        html = f.read()
    
    # Extract h3 titles and surrounding context
    blocks = re.findall(r'<div[^>]*class="[^"]*algo[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
    
    results = []
    if blocks:
        for block in blocks[:8]:
            title_match = re.search(r'<h3[^>]*>(.*?)</h3>', block, re.DOTALL)
            if title_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            else:
                continue
            
            # Get link
            link_match = re.search(r'href="(https?://[^"]+)"', block)
            link = link_match.group(1) if link_match else ""
            
            # Get snippet text
            body_text = re.sub(r'<[^>]+>', ' ', block)
            body_text = re.sub(r'\s+', ' ', body_text).strip()
            
            results.append((title, link, body_text[:300]))
    else:
        # Fallback: direct h3 extraction with context
        h3s = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
        for h3 in h3s[:8]:
            title = re.sub(r'<[^>]+>', '', h3).strip()
            if len(title) > 10:
                results.append((title, "", ""))
    
    return results

# Parse all files
files = [
    ('/tmp/yahoo_elon_tweets.html', 'Elon Musk Tweets'),
    ('/tmp/yahoo_cz.html', 'CZ Binance'),
    ('/tmp/yahoo_hack.html', 'Crypto Hacks'),
    ('/tmp/yahoo_reg.html', 'Regulation/SEC'),
    ('/tmp/yahoo_saylor.html', 'Michael Saylor'),
    ('/tmp/yahoo_trump.html', 'Trump Crypto'),
]

for filepath, label in files:
    results = parse_yahoo(filepath, label)
    print(f"\n{'='*60}")
    print(f"=== {label} ===")
    print(f"{'='*60}")
    for i, (title, link, snippet) in enumerate(results):
        print(f"\n{i+1}. {title}")
        if link:
            print(f"   {link[:120]}")
        if snippet:
            print(f"   {snippet[:200]}")
