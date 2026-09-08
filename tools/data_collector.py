#!/usr/bin/env python3
"""
ZQ Data Collector — 多维度数据采集器
用法: python3 tools/data_collector.py [--all|--coingecko|--fng|--news]

配置在 config/data_sources.json
输出在 data/ 目录下:
  - market_overview.json   (CoinGecko)
  - sentiment.json         (Fear & Greed)
  - news_feed.json         (RSS新闻)
"""

import json, os, sys, time, hashlib, hmac
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

BJT = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")

def fetch_json(url, timeout=15):
    """通用JSON抓取"""
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  ⚠️ {url[:60]}: {e}")
        return None

def fetch_rss(url, timeout=15):
    """RSS抓取"""
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode()
    except Exception as e:
        print(f"  ⚠️ RSS {url[:40]}: {e}")
        return None

# ────────────────────────────────────────────────
# CoinGecko 模块
# ────────────────────────────────────────────────
CG_BASE = "https://api.coingecko.com/api/v3"

def fetch_coingecko():
    """获取CoinGecko市场概览"""
    print("📊 CoinGecko...")
    
    # 全局数据
    global_data = fetch_json(f"{CG_BASE}/global")
    if not global_data:
        return None
    
    data = global_data.get('data', {})
    
    # BTC占比、总市值
    btc_d = data.get('market_cap_percentage', {})
    total_mcap = data.get('total_market_cap', {}).get('usd', 0)
    
    # 前7天趋势
    btc_dominance_change = 0
    mcap_change_24h = data.get('market_cap_change_percentage_24h_usd', 0)
    
    overview = {
        "source": "coingecko",
        "timestamp": datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S"),
        "total_market_cap_usd": round(total_mcap, 0),
        "btc_dominance": round(btc_d.get('btc', 0), 1),
        "eth_dominance": round(btc_d.get('eth', 0), 1),
        "mcap_change_24h": round(mcap_change_24h, 2),
        "active_cryptos": data.get('active_cryptocurrencies', 0),
        "markets": data.get('markets', 0),
    }
    
    # Top10 币种
    print("  Top10列表...")
    coins = fetch_json(f"{CG_BASE}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1&sparkline=false")
    if coins:
        overview['top_coins'] = [{
            'symbol': c['symbol'].upper(),
            'name': c['name'],
            'price': c['current_price'],
            'mcap': c['market_cap'],
            'change_24h': c['price_change_percentage_24h'],
            'volume': c['total_volume']
        } for c in coins]
    
    # Trending（前15个）
    print("  Trending币种...")
    trending = fetch_json(f"{CG_BASE}/search/trending")
    if trending and 'coins' in trending:
        overview['trending'] = [{
            'symbol': c['item']['symbol'].upper(),
            'name': c['item']['name'],
            'score': c['item'].get('score', 0),
            'market_cap_rank': c['item'].get('market_cap_rank', 0)
        } for c in trending['coins'][:15]]
    
    # 保存
    path = os.path.join(DATA_DIR, "market_overview.json")
    with open(path, 'w') as f:
        json.dump(overview, f, indent=2, default=str)
    print(f"  ✅ 已保存 {path}")
    
    # 打印摘要
    print(f"  总市值: ${overview['total_market_cap_usd']:,.0f}")
    print(f"  BTC占比: {overview['btc_dominance']}%")
    print(f"  24h变化: {overview['mcap_change_24h']}%")
    if overview.get('trending'):
        print(f"  Trending: {', '.join(t['symbol'] for t in overview['trending'][:5])}")
    
    return overview

# ────────────────────────────────────────────────
# Fear & Greed 模块
# ────────────────────────────────────────────────
FNG_URL = "https://api.alternative.me/fng"

def fetch_fear_greed():
    """获取恐惧贪婪指数"""
    print("\n" + "😨 Fear & Greed...")
    
    data = fetch_json(f"{FNG_URL}/?limit=10")
    if not data or 'data' not in data:
        return None
    
    items = data['data']
    sentiment = {
        "source": "alternative.me",
        "timestamp": datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S"),
        "current": {
            "value": int(items[0]['value']),
            "label": items[0]['value_classification']
        },
        "history": [{
            "date": item['timestamp'],
            "value": int(item['value']),
            "label": item['value_classification']
        } for item in items[:10]]
    }
    
    # 趋势
    values = [int(item['value']) for item in items[:7]]
    if len(values) >= 2:
        sentiment['trend_7d'] = values[0] - values[-1]
    
    path = os.path.join(DATA_DIR, "sentiment.json")
    with open(path, 'w') as f:
        json.dump(sentiment, f, indent=2)
    print(f"  ✅ 已保存 {path}")
    print(f"  当前: {sentiment['current']['value']}/100 — {sentiment['current']['label']}")
    if 'trend_7d' in sentiment:
        trend_str = "上升" if sentiment['trend_7d'] > 0 else "下降"
        print(f"  7天趋势: {trend_str} {abs(sentiment['trend_7d'])}点")
    
    return sentiment

# ────────────────────────────────────────────────
# 新闻模块（4个RSS源）
# ────────────────────────────────────────────────
RSS_SOURCES = [
    ("CoinDesk", "https://feeds.feedburner.com/CoinDesk"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("CryptoSlate", "https://cryptoslate.com/feed"),
]

# 常见币种关键词
COIN_KEYWORDS = {
    'BTC': ['bitcoin', 'btc'], 'ETH': ['ethereum', 'eth'], 'SOL': ['solana', 'sol'],
    'XRP': ['xrp', 'ripple'], 'ADA': ['cardano', 'ada'], 'DOGE': ['dogecoin', 'doge'],
    'DOT': ['polkadot', 'dot'], 'AVAX': ['avalanche', 'avax'], 'LINK': ['chainlink', 'link'],
    'MATIC': ['polygon', 'matic'], 'ARB': ['arbitrum', 'arb'], 'OP': ['optimism', 'op'],
    'ATOM': ['cosmos', 'atom'], 'FIL': ['filecoin', 'fil'], 'NEAR': ['near protocol', 'near'],
    'APT': ['aptos', 'apt'], 'SUI': ['sui'], 'SEI': ['sei'], 'TIA': ['celestia', 'tia'],
    'PEPE': ['pepe'], 'SHIB': ['shiba inu', 'shib'], 'BONK': ['bonk'],
    'AAVE': ['aave'], 'UNI': ['uniswap', 'uni'], 'CRV': ['curve', 'crv'],
    'PENDLE': ['pendle'], 'MKR': ['maker', 'mkr'], 'LDO': ['lido', 'ldo'],
    'RUNE': ['thorchain', 'rune'], 'INJ': ['injective', 'inj'],
    'FET': ['fetch.ai', 'fetch', 'fet'], 'AGIX': ['singularity', 'agix'],
    'OCEAN': ['ocean protocol', 'ocean'], 'RNDR': ['render', 'rndr'],
    'TAO': ['bittensor', 'tao'], 'WLD': ['worldcoin', 'wld'],
    'AI': ['ai16z', 'zerebro', 'truth terminal', 'virtuals'],
    'MEGA': ['megadrive', 'mega'], 'ZEN': ['horizen', 'zen'],
    'EIGEN': ['eigenlayer', 'eigen'],
}

TOPIC_KEYWORDS = {
    'etf': ['etf', 'exchange-traded', 'spot etf'],
    'sec': ['sec', 'securities exchange commission'],
    'regulation': ['regulation', 'regulatory', 'crypto bill'],
    'hack': ['hack', 'exploit', 'theft', 'breach', 'security incident'],
    'institutional': ['institutional', 'blackrock', 'fidelity', 'grayscale'],
    'defi': ['defi', 'decentralized finance', 'lending', 'staking'],
    'nft': ['nft', 'non-fungible', 'digital collectibles'],
    'layer2': ['layer 2', 'l2', 'scaling', 'rollup', 'zk'],
    'rwa': ['real world asset', 'rwa', 'tokenization', 'tokenized'],
    'ai': ['artificial intelligence', 'ai agent', 'ai crypto', 'machine learning'],
}

def parse_rss_item(item):
    """解析RSS条目"""
    title = item.findtext('title', '')
    link = item.findtext('link', '')
    desc = item.findtext('description', '') or item.findtext('summary', '') or ''
    pubdate = item.findtext('pubDate', '') or item.findtext('published', '') or ''
    
    # 去HTML标签
    import re
    desc_clean = re.sub(r'<[^>]+>', ' ', desc)
    
    text = f"{title} {desc_clean}".lower()
    
    # 检测提到的币种
    mentioned_coins = []
    for coin, keywords in COIN_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                mentioned_coins.append(coin)
                break
    
    # 检测主题
    matched_topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                matched_topics.append(topic)
                break
    
    return {
        'title': title.strip(),
        'link': link.strip(),
        'pubdate': pubdate.strip(),
        'summary': desc_clean[:300].strip(),
        'mentioned_coins': list(set(mentioned_coins)),
        'topics': list(set(matched_topics))
    }

def fetch_news():
    """获取行业新闻"""
    print("\n" + "📰 行业新闻...")
    
    all_articles = []
    
    for source_name, url in RSS_SOURCES:
        print(f"  {source_name}...")
        raw = fetch_rss(url)
        if not raw:
            continue
        
        try:
            root = ET.fromstring(raw)
            # RSS 2.0 格式
            items = root.findall('.//item')
            if not items:
                # Atom 格式
                items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            
            for item in items[:10]:
                parsed = parse_rss_item(item)
                parsed['source'] = source_name
                all_articles.append(parsed)
        
        except Exception as e:
            print(f"    解析失败: {e}")
    
    # 按时间排序（最近的在前）
    # 简单去重
    seen_titles = set()
    unique_articles = []
    for art in all_articles:
        key = art['title'][:50].lower()
        if key not in seen_titles:
            seen_titles.add(key)
            unique_articles.append(art)
    
    # 统计币种提及
    coin_mentions = {}
    for art in unique_articles:
        for coin in art.get('mentioned_coins', []):
            coin_mentions[coin] = coin_mentions.get(coin, 0) + 1
    
    # 统计主题
    topic_counts = {}
    for art in unique_articles:
        for topic in art.get('topics', []):
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    news_data = {
        "source": "RSS",
        "timestamp": datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S"),
        "total_articles": len(unique_articles),
        "articles": unique_articles[:30],  # 保留最近30条
        "coin_mentions": dict(sorted(coin_mentions.items(), key=lambda x: -x[1])),
        "hot_topics": dict(sorted(topic_counts.items(), key=lambda x: -x[1])),
    }
    
    path = os.path.join(DATA_DIR, "news_feed.json")
    with open(path, 'w') as f:
        json.dump(news_data, f, indent=2, default=str)
    print(f"  ✅ 已保存 {path}")
    print(f"  共 {len(unique_articles)} 条新闻")
    if coin_mentions:
        hot = sorted(coin_mentions.items(), key=lambda x: -x[1])[:5]
        print(f"  最热币种: {', '.join(f'{c}({n}次)' for c, n in hot)}")
    if topic_counts:
        top_topics = sorted(topic_counts.items(), key=lambda x: -x[1])[:3]
        print(f"  热点话题: {', '.join(f'{t}({n}次)' for t, n in top_topics)}")
    
    return news_data

# ────────────────────────────────────────────────
# 主入口
# ────────────────────────────────────────────────
def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def main():
    import sys
    ensure_dirs()
    
    args = sys.argv[1:]
    
    run_all = not args or '--all' in args
    run_cg = '--coingecko' in args or run_all
    run_fng = '--fng' in args or run_all
    run_news = '--news' in args or run_all
    
    results = {}
    
    print("=" * 50)
    print(f"ZQ Data Collector — {datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    if run_cg:
        results['market_overview'] = fetch_coingecko()
    if run_fng:
        results['sentiment'] = fetch_fear_greed()
    if run_news:
        results['news_feed'] = fetch_news()
    
    print("
" + "=" * 50)
    print("采集完成 ✅")
    print("=" * 50)
    
    return results

if __name__ == '__main__':
    main()
