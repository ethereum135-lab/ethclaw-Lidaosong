#!/usr/bin/env python3
"""A7监控辅助脚本 — 无管道，直接文件IO"""
import json, urllib.request, sys

def fetch(url, timeout=8):
    try:
        resp = urllib.request.urlopen(url, timeout=timeout)
        return resp.read().decode('utf-8')
    except Exception as e:
        return f"ERROR:{e}"

if len(sys.argv) < 2:
    print("Usage: script <action>")
    sys.exit(1)

action = sys.argv[1]

if action == "fng":
    raw = fetch("https://api.alternative.me/fng/?limit=1")
    if raw.startswith("ERROR"):
        print(raw)
    else:
        data = json.loads(raw)
        v = int(data['data'][0]['value'])
        cls = data['data'][0]['value_classification']
        print(f"FNG:{v}:{cls}")

elif action == "coingecko_global":
    raw = fetch("https://api.coingecko.com/api/v3/global")
    if raw.startswith("ERROR"):
        print(raw)
    else:
        data = json.loads(raw)
        d = data.get('data', {})
        mc = d.get('total_market_cap', {}).get('usd', 0)
        btc_dom = d.get('market_cap_percentage', {}).get('btc', 0)
        vol = d.get('total_volume', {}).get('usd', 0)
        print(f"MC:{mc:.0f}:BTC_DOM:{btc_dom:.1f}:VOL:{vol:.0f}")

elif action == "trending":
    raw = fetch("https://api.coingecko.com/api/v3/trending/search")
    if raw.startswith("ERROR"):
        print(raw)
    else:
        data = json.loads(raw)
        coins = data.get('coins', [])
        for c in coins[:10]:
            item = c.get('item', {})
            print(f"TREND:{item.get('name','?')}:{item.get('symbol','?')}:score={item.get('score','?')}")

elif action == "news_rss":
    raw = fetch("https://news.google.com/rss/search?q=crypto+hack+OR+exploit+OR+regulation&hl=en-US&gl=US&ceid=US:en")
    if raw.startswith("ERROR"):
        print(raw)
    else:
        import re
        titles = re.findall(r'<title>(.*?)</title>', raw)
        for t in titles[1:16]:  # skip first (feed title)
            print(f"NEWS:{t}")

elif action == "elon_rss":
    raw = fetch("https://news.google.com/rss/search?q=Elon+Musk+crypto+tweet&hl=en-US&gl=US&ceid=US:en")
    if raw.startswith("ERROR"):
        print(raw)
    else:
        import re
        titles = re.findall(r'<title>(.*?)</title>', raw)
        for t in titles[1:11]:
            print(f"ELON:{t}")

elif action == "cz_rss":
    raw = fetch("https://news.google.com/rss/search?q=Binance+CZ+announcement+crypto&hl=en-US&gl=US&ceid=US:en")
    if raw.startswith("ERROR"):
        print(raw)
    else:
        import re
        titles = re.findall(r'<title>(.*?)</title>', raw)
        for t in titles[1:11]:
            print(f"CZ:{t}")

else:
    print(f"Unknown action: {action}")
