#!/usr/bin/env python3
"""
ZQ LH Scanner — 量化师扫描工具
用法:
  python3 tools/lh_scanner.py --top 20     # 输出Top20候选币
  python3 tools/lh_scanner.py --quick       # 快速扫描（Top10）
  python3 tools/lh_scanner.py --category ai,storage  # 特定赛道
  python3 tools/lh_scanner.py --output json # JSON格式输出

数据依赖（已采集到 data/）:
  - coin_pool.json    (400币+排名)
  - market_overview.json  (CoinGecko市场数据)
  - sentiment.json    (Fear & Greed)
  - news_feed.json    (行业新闻)
  - Binance API       (实时K线)
"""

import json, os, sys, time
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.parse import urlencode

BJT = timezone(timedelta(hours=8))
NOW = datetime.now(BJT)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ─── 工具函数 ───

def fetch_json(url, timeout=12):
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return None

def load_json(path):
    """从文件加载JSON"""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

# ─── 数据加载 ───

def load_coin_pool():
    """加载选币库"""
    path = os.path.join(DATA_DIR, "coin_pool.json")
    data = load_json(path)
    if not data:
        print("⚠️ coin_pool.json 不存在")
        return None, None
    coins = data.get('pools', {}).get('master', [])
    # 只取有换手率的（排除USDC/USDT等稳定币）
    active = [c for c in coins if c.get('volume_24h_usd', 0) > 100000 
              and c['symbol'] not in ('USDC', 'USDT', 'USD1', 'DAI', 'FDUSD', 'TUSD', 'BUSD')]
    return active, data

def load_market_overview():
    """加载市场概览"""
    return load_json(os.path.join(DATA_DIR, "market_overview.json"))

def load_sentiment():
    """加载情绪数据"""
    return load_json(os.path.join(DATA_DIR, "sentiment.json"))

def load_news():
    """加载新闻数据"""
    return load_json(os.path.join(DATA_DIR, "news_feed.json"))

# ─── Binance K线获取 ───

BINANCE_BASE = "https://api.binance.com"

def get_klines(symbol, interval='30m', limit=20):
    """获取K线数据"""
    params = urlencode({'symbol': symbol, 'interval': interval, 'limit': limit})
    url = f"{BINANCE_BASE}/api/v3/klines?{params}"
    data = fetch_json(url, timeout=8)
    if not data or not isinstance(data, list):
        return None
    return data

def get_ticker_24h(symbol):
    """获取24h行情"""
    params = urlencode({'symbol': symbol})
    url = f"{BINANCE_BASE}/api/v3/ticker/24hr?{params}"
    return fetch_json(url, timeout=8)

# ─── 技术指标计算 ───

def calc_rsi(closes, period=14):
    """计算RSI"""
    if len(closes) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(-period, 0):
        diff = closes[i] - closes[i-1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_trend(closes):
    """计算趋势方向（简化EMA比较）"""
    if len(closes) < 8:
        return 0
    short = sum(closes[-3:]) / 3
    long = sum(closes[-8:]) / 8
    diff = (short - long) / long * 100
    if diff > 0.5:
        return 1
    elif diff < -0.5:
        return -1
    return 0

def calc_volume_surge(volumes):
    """计算量比"""
    if len(volumes) < 5:
        return 1.0
    recent = volumes[-1]
    baseline = sum(volumes[-6:-1]) / 5
    if baseline == 0:
        return 1.0
    return recent / baseline

# ─── 评分引擎 ───

def score_single_coin(symbol, market_data=None, news_data=None, sentiment=None):
    """对单个币评分"""
    # 1. 获取实时K线
    klines = get_klines(symbol)
    if not klines or len(klines) < 10:
        return None
    
    # 解析K线
    completed = klines[:-1]  # 去掉当前形成K线
    closes30 = [float(k[4]) for k in completed[-16:]]
    vols30 = [float(k[5]) for k in completed[-15:]]
    
    if len(closes30) < 10:
        return None
    
    # 计算指标
    rsi = calc_rsi(closes30)
    surge = calc_volume_surge(vols30)
    trend = calc_trend(closes30)
    current_price = closes30[-1]
    price_pos = (current_price - min(closes30)) / (max(closes30) - min(closes30) + 0.001)
    
    # 2. 24h行情
    ticker = get_ticker_24h(symbol)
    chg24h = 0
    vol24h = 0
    if ticker:
        chg24h = float(ticker.get('priceChangePercent', 0))
        vol24h = float(ticker.get('quoteVolume', 0))
    
    # ── 评分 ──
    
    # 吸筹分（满分25）
    accu_score = 0
    # 量比：0.8~1.5 = 吸筹期
    if 0.8 <= surge <= 1.5:
        accu_score += 20
    elif 1.5 < surge <= 2.0:
        accu_score += 10  # 已热
    elif surge > 2.0:
        accu_score += 0   # 已爆量
    elif 0.5 <= surge < 0.8:
        accu_score += 5    # 偏低
    else:
        accu_score += 0
    # 价格微动（吸筹期价格不动）
    if -3 <= chg24h <= 3:
        accu_score += 5
    
    # 趋势分（满分20）
    trend_score = 0
    if trend == 1:
        trend_score += 15
        # 多框架共振：价格在中低位
        if price_pos < 0.7:
            trend_score += 5
    elif trend == 0:
        trend_score += 5
    
    # RSI分（满分15）
    rsi_score = 0
    if 30 <= rsi <= 50:
        rsi_score = 15      # 有上涨空间
    elif 50 < rsi <= 60:
        rsi_score = 8       # 已热但还行
    elif 20 <= rsi < 30:
        rsi_score = 8       # 超卖反弹
    elif 60 < rsi <= 70:
        rsi_score = 3       # 热区
    else:
        rsi_score = 0
    
    # 情绪分（满分15）— 基于新闻
    sentiment_score = 0
    name = symbol.replace('USDT', '')
    if news_data:
        mentions = news_data.get('coin_mentions', {})
        if name in mentions:
            sentiment_score = min(15, mentions[name] * 5)
    
    # 热度分（满分10）— 基于CoinGecko
    heat_score = 0
    if market_data:
        trending = market_data.get('trending', [])
        trending_symbols = [t['symbol'] for t in trending]
        if name in trending_symbols:
            heat_score = 10
        # 排名
        top_coins = market_data.get('top_coins', [])
        top_symbols = [t['symbol'] for t in top_coins]
        if name in top_symbols:
            heat_score = max(heat_score, 5)
    
    # 总评分
    total_score = accu_score + trend_score + rsi_score + sentiment_score + heat_score
    
    return {
        'symbol': name,
        'price': round(current_price, 6),
        'chg_24h': round(chg24h, 2),
        'rsi': round(rsi, 1),
        'volume_surge': round(surge, 2),
        'trend': trend,
        'score': total_score,
        'details': {
            '吸筹分': accu_score,
            '趋势分': trend_score,
            'RSI分': rsi_score,
            '情绪分': sentiment_score,
            '热度分': heat_score,
        },
        'recommendation': get_recommendation(total_score, trend, rsi, surge, chg24h)
    }

def get_recommendation(score, trend, rsi, surge, chg24h):
    """根据评分给出操作建议"""
    if score >= 70 and trend == 1 and 30 <= rsi <= 55:
        return "✅ 推荐买入 — 吸筹期+趋势向上+有空间"
    elif score >= 60 and trend >= 0:
        return "👀 关注 — 条件不错，等确认"
    elif score >= 50:
        return "📌 观察 — 部分条件达标"
    elif surge > 2.0 and chg24h > 10:
        return "🔴 观察不进 — 已爆量，等回调"
    else:
        return "⏸️ 观望 — 不满足条件"

# ─── 主流程 ───

def main():
    import argparse
    parser = argparse.ArgumentParser(description='ZQ LH Scanner')
    parser.add_argument('--top', type=int, default=20, help='输出TopN')
    parser.add_argument('--quick', action='store_true', help='快速扫描')
    parser.add_argument('--category', type=str, help='赛道过滤')
    parser.add_argument('--output', type=str, choices=['text', 'json'], default='text')
    args = parser.parse_args()
    
    print(f"\n{'='*55}")
    print(f"  ZQ LH Scanner — {NOW.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}")
    
    # 1. 加载数据
    print("\n📂 加载数据...")
    coins, pool_data = load_coin_pool()
    if not coins:
        print("❌ 无法加载选币库，尝试手动更新...")
        print("   运行: python3 tools/coin_pool_manager.py --update")
        return
    
    market_data = load_market_overview()
    sentiment = load_sentiment()
    news_data = load_news()
    
    # 显示市场状态
    if market_data:
        print(f"  总市值: ${market_data.get('total_market_cap_usd',0):,.0f}")
        print(f"  BTC占比: {market_data.get('btc_dominance',0)}%")
    if sentiment:
        s = sentiment.get('current', {})
        print(f"  情绪: {s.get('value','?')}/100 — {s.get('label','?')}")
    if news_data:
        hot_coins = list(news_data.get('coin_mentions', {}).keys())[:5]
        if hot_coins:
            print(f"  新闻提及: {', '.join(hot_coins)}")
    
    # 2. 赛道过滤
    if args.category:
        cats = args.category.split(',')
        coins = [c for c in coins if c.get('category', '') in cats]
        print(f"\n🎯 赛道过滤: {args.category} → {len(coins)}个币")
    
    # 3. 快速扫描（只扫Top10成交量）
    if args.quick:
        coins = coins[:10]
        print(f"\n⚡ 快速扫描: Top{len(coins)}成交额币种")
    
    # 4. 扫描
    top_n = args.top if not args.quick else 10
    print(f"\n🔍 扫描 {min(len(coins), top_n + 20)}个候选币...")
    
    results = []
    errors = 0
    
    for i, coin in enumerate(coins[:top_n + 20]):  # 多扫一些确保有足够候选
        symbol = coin['symbol'] + 'USDT'
        
        # 跳过稳定币
        if coin['symbol'] in ('USDC', 'USDT', 'USD1', 'DAI', 'FDUSD'):
            continue
        
        result = score_single_coin(symbol, market_data, news_data, sentiment)
        if result:
            results.append(result)
        else:
            errors += 1
        
        # 进度
        if (i + 1) % 10 == 0:
            print(f"  ...已扫 {i+1}个, {len(results)}个有效")
        
        time.sleep(0.3)  # Binance API限流
    
    # 5. 排序输出
    results.sort(key=lambda x: -x['score'])
    top_results = results[:top_n]
    
    # 输出
    if args.output == 'json':
        out = {
            'timestamp': NOW.strftime('%Y-%m-%d %H:%M:%S'),
            'scanned': len(coins[:top_n+20]),
            'valid': len(results),
            'errors': errors,
            'candidates': top_results
        }
        print(json.dumps(out, indent=2, default=str))
        return
    
    print(f"\n{'='*55}")
    print(f"  扫描结果 — {len(results)}个有效 / {errors}个失败")
    print(f"{'='*55}")
    
    for i, r in enumerate(top_results[:10]):
        print(f"\n  #{i+1} {r['symbol']}  —  总分 {r['score']}")
        print(f"    价格: ${r['price']}  |  24h: {r['chg_24h']}%")
        print(f"    RSI: {r['rsi']}  |  量比: {r['volume_surge']}x  |  趋势: {trend_icon(r['trend'])}")
        print(f"    评分: 吸筹{r['details']['吸筹分']} 趋势{r['details']['趋势分']} ", end='')
        print(f"RSI{r['details']['RSI分']} 情绪{r['details']['情绪分']} 热度{r['details']['热度分']}")
        print(f"    {r['recommendation']}")
    
    print(f"\n{'='*55}")
    print(f"  扫描完成 ✅  |  {NOW.strftime('%H:%M')}")
    print(f"{'='*55}")

def trend_icon(t):
    return '📈' if t == 1 else '📉' if t == -1 else '➡️'

if __name__ == '__main__':
    main()
