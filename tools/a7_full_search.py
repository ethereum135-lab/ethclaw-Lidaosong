#!/usr/bin/env python3
"""Comprehensive A7 search - save results to files, no pipes"""
import sys, re, html, urllib.parse, urllib.request, os, json

BASE = "/Users/lidaosong/zq_web4_trading_system"
OUT = os.path.join(BASE, "tmp")

def fetch_google(query, outfile):
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=5"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode('utf-8', errors='replace')
        titles = re.findall(r'<h3[^>]*>(.*?)</h3>', content, re.DOTALL)
        lines = []
        for i, t in enumerate(titles[:8], 1):
            t = html.unescape(re.sub(r'<[^>]+>', '', t)).strip()
            lines.append(f"{i}. {t}")
        if not lines:
            lines.append("NO_RESULTS")
        with open(outfile, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        return lines
    except Exception as e:
        with open(outfile, 'w') as f:
            f.write(f"ERROR: {e}\n")
        return [f"ERROR: {e}"]

def fetch_bing(query, outfile):
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&count=5"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode('utf-8', errors='replace')
        # Bing uses h2 > a pattern
        titles = re.findall(r'<h2><a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', content, re.DOTALL)
        lines = []
        for i, (url_, t) in enumerate(titles[:8], 1):
            t = html.unescape(re.sub(r'<[^>]+>', '', t)).strip()
            lines.append(f"{i}. {t}")
            lines.append(f"   {url_}")
        if not lines:
            lines.append("NO_RESULTS_FROM_BING")
        with open(outfile, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        return lines
    except Exception as e:
        with open(outfile, 'w') as f:
            f.write(f"BING_ERROR: {e}\n")
        return [f"BING_ERROR: {e}"]

# Run searches
queries = {
    "elon": "Elon Musk crypto bitcoin doge X Money",
    "cz": "CZ Binance crypto announcement",
    "hack": "crypto hack exploit May 2026",
    "regulation": "crypto regulation SEC ban May 2026",
}

os.makedirs(OUT, exist_ok=True)
results = {}
for key, q in queries.items():
    print(f"\n=== {key}: {q} ===")
    # Try Bing first (Google often blocks)
    bing_res = fetch_bing(q, os.path.join(OUT, f"a7_{key}_bing.txt"))
    for l in bing_res:
        print(f"  {l}")
    results[key] = bing_res

# Write summary
summary = []
for key, res in results.items():
    summary.append(f"=== {key} ===")
    summary.extend(res)
    summary.append("")

with open(os.path.join(OUT, "a7_search_summary.txt"), 'w') as f:
    f.write('\n'.join(summary))

print("\n=== ALL DONE ===")
print(f"Results in {os.path.join(OUT, 'a7_search_summary.txt')}")
