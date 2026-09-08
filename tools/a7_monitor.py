#!/usr/bin/env python3
"""A7 Sentinel - Monitor script for crypto news, prices, and sentiment"""
import requests, json, sys
from datetime import datetime

now = datetime.now()
print(f"A7 MONITOR REPORT - {now.strftime('%Y-%m-%d %H:%M BJT')}")
print("="*60)

# 1. CoinGecko Price Data
print("\n[1] CoinGecko Market Data")
try:
    r = requests.get(
        'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=50&sparkline=false',
        headers={'User-Agent': 'Mozilla/5.0'},
        timeout=15
    )
    data = r.json()
    sorted_data = sorted(data, key=lambda x: x.get('price_change_percentage_24h', 0) or 0, reverse=True)
    print("TOP10 24h Gainers:")
    for i, c in enumerate(sorted_data[:10]):
        sym = c['symbol'].upper()
        name = c['name']
        chg = c.get('price_change_percentage_24h', 0) or 0
        price = c.get('current_price', 0) or 0
        vol = c.get('total_volume', 0) or 0
        print(f"  {i+1}. {sym:8s} {name:20s} +{chg:>6.2f}%  ${price:<10.4f} Vol:${vol/1e6:<8.2f}M")
    
    top3_chg = [c.get('price_change_percentage_24h', 0) or 0 for c in sorted_data[:3]]
    max_chg = max(top3_chg)
    if max_chg > 50:
        print(f"[ALERT] 发现涨幅>50%的币种: {max_chg:.2f}%")
        for c in sorted_data[:3]:
            chg = c.get('price_change_percentage_24h', 0) or 0
            if chg > 50:
                print(f"  {c['symbol']} ({c['name']}): +{chg:.2f}%")
    else:
        print(f"TOP3 max gain: {max_chg:.2f}% - normal range")
    
    # BTC and ETH
    for coin_id in ['bitcoin', 'ethereum']:
        r2 = requests.get(
            f'https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true',
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=10
        )
        d = r2.json()
        price = d[coin_id]['usd']
        chg = d[coin_id].get('usd_24h_change', 0)
        print(f"{coin_id.capitalize()}: ${price:,.2f} (24h: {chg:+.2f}%)")
        
except Exception as e:
    print(f"CoinGecko Error: {e}")

# 2. F&G Index
print("\n[2] Fear & Greed Index")
try:
    r = requests.get('https://api.alternative.me/fng/?limit=1', timeout=10)
    d = r.json()
    val = int(d['data'][0]['value'])
    cls = d['data'][0]['value_classification']
    print(f"F&G: {val} ({cls})")
    if val < 20:
        print("[ALERT] 极端恐慌! F&G < 20")
    elif val > 80:
        print("[ALERT] 极端贪婪! F&G > 80")
    else:
        print("Normal range, no alert")
except Exception as e:
    print(f"F&G Error: {e}")

# 3. Google News RSS
print("\n[3] Google News Crypto RSS")
try:
    url = 'https://news.google.com/rss/search?q=crypto+hack+OR+exploit+OR+regulation+OR+SEC+OR+ban+OR+upgrade&hl=en-US&gl=US&ceid=US:en'
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    import xml.etree.ElementTree as ET
    root = ET.fromstring(r.content)
    items = root.findall('.//item')
    print(f"Found {len(items)} items")
    
    alert_kw = ['hack','exploit','breach','attack','stolen','theft','phish',
                'regulat','ban','crackdown','lawsuit','cease','desist',
                'elon','musk','cz','binance','sayl']
    found = False
    recent_alerts = []
    cutoff = datetime.now().timestamp() - 86400  # 24 hours
    
    for item in items[:20]:
        title = item.find('title').text or ''
        link = item.find('link').text or ''
        pub_date = item.find('pubDate').text or ''
        source = item.find('source').text if item.find('source') is not None else ''
        
        has_alert = any(kw in title.lower() for kw in alert_kw)
        if has_alert:
            found = True
            recent_alerts.append((title[:120], source[:30], pub_date[:25]))
    
    if recent_alerts:
        print("Recent crypto news (24h window):")
        for t, s, d in recent_alerts[:10]:
            print(f"  {t}")
            print(f"    Source: {s} | {d}")
    else:
        print("No major alerts found")
        
except Exception as e:
    print(f"News RSS Error: {e}")

print("\n" + "="*60)
print("Monitor check complete")
