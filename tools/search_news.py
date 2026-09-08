#!/usr/bin/env python3
"""Search Google for crypto hacks, regulation, major news"""
import urllib.request
import re

# Hack news
url1 = f"https://www.google.com/search?q=crypto+hack+attack+exploit+2026+May"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

try:
    req = urllib.request.Request(url1, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode('utf-8', errors='replace')
    
    with open('/tmp/hack_search.html', 'w') as f:
        f.write(html)
    
    results = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
    print("=== Crypto Hack/Attack News ===")
    for i, r in enumerate(results[:15]):
        clean = re.sub(r'<[^>]+>', '', r).strip()
        if clean:
            print(f"{i+1}. {clean}")
except Exception as e:
    print(f"ERROR hacks: {e}")

# Regulation news
try:
    url2 = f"https://www.google.com/search?q=crypto+regulation+ban+SEC+news+2026"
    req2 = urllib.request.Request(url2, headers=headers)
    with urllib.request.urlopen(req2, timeout=15) as resp2:
        html2 = resp2.read().decode('utf-8', errors='replace')
    
    with open('/tmp/reg_search.html', 'w') as f:
        f.write(html2)
    
    results2 = re.findall(r'<h3[^>]*>(.*?)</h3>', html2, re.DOTALL)
    print("\n=== Crypto Regulation/SEC News ===")
    for i, r in enumerate(results2[:15]):
        clean = re.sub(r'<[^>]+>', '', r).strip()
        if clean:
            print(f"{i+1}. {clean}")
except Exception as e:
    print(f"ERROR regulation: {e}")

# Upgrade/mainnet launch news
try:
    url3 = f"https://www.google.com/search?q=crypto+upgrade+mainnet+launch+2026+May"
    req3 = urllib.request.Request(url3, headers=headers)
    with urllib.request.urlopen(req3, timeout=15) as resp3:
        html3 = resp3.read().decode('utf-8', errors='replace')
    
    results3 = re.findall(r'<h3[^>]*>(.*?)</h3>', html3, re.DOTALL)
    print("\n=== Crypto Upgrade/Mainnet News ===")
    for i, r in enumerate(results3[:15]):
        clean = re.sub(r'<[^>]+>', '', r).strip()
        if clean:
            print(f"{i+1}. {clean}")
except Exception as e:
    print(f"ERROR upgrades: {e}")
