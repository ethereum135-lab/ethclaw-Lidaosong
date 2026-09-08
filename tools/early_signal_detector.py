#!/usr/bin/env python3
"""
ZQ Early Signal Detector — 早期信号检测器 v2
专职：在币"刚启动"时发现，不等它涨87%

核心差异于现有选币体系：
  现有: "谁涨了" → 分析它还能不能涨（事后分析）
  本工具: "谁突然活了" → 马上去验证（事前发现）

检测频率：推荐每10-15分钟一次（独立于30分钟引擎）
部署：AWS独立运行

信号优先级:
  P0: 成交量突变（15min量跳2.5x+）→ 最早期信号，大资金入场
  P1: 早期启动（24h涨5-30%，Vol/MC 20-200%）→ 刚启动的潜力币
  P2: 吸筹信号（没涨但健康）→ 埋伏型信号

数据源: Binance API + CoinGecko + Telegram + CoinTelegraph/Decrypt RSS
"""

import json
import time
import os
import sys
import re
import html as html_module
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ====== 配置 ======
BINANCE_API = "https://api.binance.com"
COINGECKO_API = "https://api.coingecko.com/api/v3"
TELEGRAM_BASE = "https://t.me/s"
FEAR_GREED_API = "https://api.alternative.me/fng/?limit=7"

RSS_SOURCES = [
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
]

# 信号阈值
VOLUME_SURGE_THRESHOLD = 2.5
BREAKOUT_MIN_CHANGE = 5.0
BREAKOUT_MAX_CHANGE = 30.0
MIN_VOLUME_USD = 5000000  # 最小成交额$5M

OUTPUT_DIR = os.path.expanduser("~/zq_web4_trading_system/agents/nbz")
FINDINGS_FILE = os.path.join(OUTPUT_DIR, "findings.md")


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}")


def fetch_json(url, timeout=10):
    import urllib.request
    ctx = __import__('ssl').create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=timeout)
        return json.loads(resp.read().decode())
    except Exception as e:
        log(f"⚠️ JSON获取失败: {url[:70]} — {e}")
        return None


def fetch_text(url, timeout=10):
    import urllib.request
    ctx = __import__('ssl').create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=timeout)
        return resp.read().decode()
    except Exception as e:
        return None


# ====== 信号检测 ======

def detect_volume_surge():
    """
    检测成交量突变（P0信号）
    只看Top100成交额币种，检查15min量跳
    """
    signals = []
    
    # 先获取所有24hr ticker
    data = fetch_json(f"{BINANCE_API}/api/v3/ticker/24hr")
    if not data:
        return signals
    
    usdt = [d for d in data if d["symbol"].endswith("USDT")]
    top100 = sorted(usdt, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)[:100]
    
    # 过滤非ASCII符号（Binance有少数非英文字符交易对）
    top100 = [d for d in top100 if all(ord(c) < 128 for c in d["symbol"])]
    
    for pair in top100:
        symbol = pair["symbol"]
        vol_24h = float(pair.get("quoteVolume", 0))
        
        if vol_24h < MIN_VOLUME_USD:
            continue
        
        # 获取15min K线（最近4根）
        klines = fetch_json(f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=15m&limit=4")
        if not klines or len(klines) < 4:
            continue
        
        # 最近15min成交额 vs 之前45min平均
        def kline_vol(k):
            return float(k[5]) * float(k[7])  # volume * quote asset volume
        
        current = kline_vol(klines[-1])
        prev = [kline_vol(k) for k in klines[-4:-1]]
        avg_prev = sum(prev) / len(prev) if prev else 1
        
        if avg_prev > 0 and current > avg_prev * VOLUME_SURGE_THRESHOLD:
            ratio = current / avg_prev
            signals.append({
                "type": "P0_volume_surge",
                "symbol": symbol,
                "coin": symbol.replace("USDT", ""),
                "price": float(pair.get("lastPrice", 0)),
                "volume_24h": vol_24h,
                "surge_ratio": round(ratio, 1),
                "detail": f"15min量跳{ratio:.1f}x",
            })
    
    return signals


def detect_early_breakout():
    """
    检测早期启动（P1信号）
    从CoinGecko Top50成交量找24h涨5-30%且Vol/MC健康的币
    """
    signals = []
    
    data = fetch_json(
        f"{COINGECKO_API}/coins/markets?vs_currency=usd&order=volume_desc&per_page=50&page=1"
    )
    if not data:
        return signals
    
    for coin in data:
        change_24h = coin.get("price_change_percentage_24h", 0)
        if not change_24h:
            continue
        
        vol = coin.get("total_volume", 0) or 0
        mcap = coin.get("market_cap", 0) or 0
        
        # 过滤条件：刚启动5-30%，成交量$5M+
        if BREAKOUT_MIN_CHANGE <= change_24h <= BREAKOUT_MAX_CHANGE:
            if vol >= MIN_VOLUME_USD and mcap > 0:
                vol_mcap = round((vol / mcap) * 100, 1)
                
                # Vol/MC 20-200% 是健康启动区域
                if 20 <= vol_mcap < 200:
                    signals.append({
                        "type": "P1_early_breakout",
                        "coin": coin.get("id", ""),
                        "symbol": (coin.get("symbol", "") or "").upper() + "USDT",
                        "price": coin.get("current_price", 0),
                        "change_24h": round(change_24h, 1),
                        "volume_24h": vol,
                        "vol_mcap_ratio": vol_mcap,
                        "rank": coin.get("market_cap_rank", 0),
                        "detail": f"24h涨{round(change_24h,1)}%, Vol/MC {vol_mcap}%",
                    })
    
    return signals


# ====== 交叉验证 ======

def check_telegram(coin_name):
    """查Telegram频道最新消息"""
    url = f"{TELEGRAM_BASE}/{coin_name.lower()}"
    html = fetch_text(url)
    if not html:
        return []
    
    msgs = re.findall(
        r'<div[^>]*class="[^"]*js-message_text[^"]*"[^>]*>(.*?)</div>\s*<div class="tgme_widget_message_reactions',
        html, re.DOTALL
    )
    
    results = []
    for m in msgs[:3]:
        clean = re.sub(r'<br\s*/?>', '\n', m)
        clean = re.sub(r'<[^>]+>', '', clean)
        clean = html_module.unescape(clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if clean:
            results.append(clean[:200])
    
    return results


def check_news_mention(coin_name, coin_symbol):
    """通过RSS检查新闻提及"""
    mentions = []
    keywords = [coin_name.lower(), coin_symbol.lower()]
    
    for src_name, rss_url in RSS_SOURCES:
        xml_text = fetch_text(rss_url)
        if not xml_text:
            continue
        
        try:
            root = ET.fromstring(xml_text)
            items = root.findall(".//item")[:10]
            for item in items:
                title = (item.findtext("title", "") or "")
                desc = (item.findtext("description", "") or "")
                content = (title + " " + desc).lower()
                
                for kw in keywords:
                    if kw in content:
                        mentions.append({
                            "source": src_name,
                            "title": title.strip()[:120],
                        })
                        break
        except ET.ParseError:
            continue
    
    return mentions


# CoinGecko市场数据缓存（1次API调用覆盖50个币）
COINGECKO_MARKET_DATA = []

def cache_coingecko_markets():
    """缓存CoinGecko Top50市场数据"""
    global COINGECKO_MARKET_DATA
    data = fetch_json(
        f"{COINGECKO_API}/coins/markets?vs_currency=usd&order=volume_desc&per_page=50&page=1"
    )
    if data:
        COINGECKO_MARKET_DATA = data

def get_coin_categories(coin_id):
    """从缓存获取类别"""
    for coin in COINGECKO_MARKET_DATA:
        if coin.get("id", "") == coin_id:
            return coin.get("categories", [])
    return []


# ====== 宏观数据 ======

def get_market_overview():
    d = fetch_json(f"{COINGECKO_API}/global")
    if d and "data" in d:
        dd = d["data"]
        return {
            "mcap": dd.get("total_market_cap", {}).get("usd", 0),
            "btc_dom": dd.get("market_cap_percentage", {}).get("btc", 0),
            "active": dd.get("active_cryptocurrencies", 0),
        }
    return {}


def get_fear_greed():
    d = fetch_json(FEAR_GREED_API)
    if d and "data" in d:
        items = d["data"]
        return f"{items[0]['value']} — {items[0]['value_classification']}"
    return "N/A"


# ====== 报告生成 ======

def generate_report(volume_sigs, breakout_sigs, validations, overview, fg):
    run_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# NBZ 早期信号报告 — {run_time}", ""]
    
    # 市场宏观
    lines.append("## 📊 市场状态")
    lines.append("")
    if overview:
        mcap = overview.get("mcap", 0)
        mcap_str = f"${mcap/1e12:.2f}T" if mcap > 1e12 else f"${mcap/1e9:.2f}B"
        lines.append(f"| 总市值 | {mcap_str} |")
        lines.append(f"| BTC占比 | {overview.get('btc_dom', 'N/A')}% |")
        lines.append(f"| 情绪 | {fg} |")
    lines.append("")
    
    # P0信号
    lines.append("## 🔴 P0 — 成交量突变（最早期信号）")
    lines.append("")
    if volume_sigs:
        for sig in volume_sigs:
            coin = sig["coin"]
            lines.append(f"### ⚡ {coin}")
            lines.append(f"- 价格: ${sig['price']} | {sig['detail']} | 24h量: ${sig['volume_24h']:,.0f}")
            v = validations.get(coin, {})
            if v.get("telegram"):
                lines.append(f"  📱 TG: {v['telegram'][0]}")
            if v.get("news"):
                lines.append(f"  📰 {v['news'][0]['source']}: {v['news'][0]['title']}")
            if v.get("categories"):
                lines.append(f"  🏷️ {', '.join(v['categories'][:3])}")
            lines.append("")
    else:
        lines.append("*当前无成交量突变信号*")
        lines.append("")
    
    # P1信号
    lines.append("## 🟡 P1 — 早期启动（刚涨5-30%，Vol/MC健康）")
    lines.append("")
    if breakout_sigs:
        for sig in breakout_sigs:
            coin = sig["coin"]
            lines.append(f"### 📈 {coin.upper()} (${sig['price']})")
            lines.append(f"- +{sig['change_24h']}% | Vol ${sig['volume_24h']:,.0f} | Vol/MC {sig['vol_mcap_ratio']}% | #{sig['rank']}")
            v = validations.get(coin, {})
            if v.get("telegram"):
                lines.append(f"  📱 TG: {v['telegram'][0]}")
            if v.get("news"):
                lines.append(f"  📰 {v['news'][0]['source']}: {v['news'][0]['title']}")
            if v.get("categories"):
                lines.append(f"  🏷️ {', '.join(v['categories'][:3])}")
            lines.append("")
    else:
        lines.append("*当前无早期启动信号*")
        lines.append("")
    
    lines.append("---")
    lines.append(f"最后更新: {run_time}")
    lines.append("数据源: Binance + CoinGecko + Telegram + CoinTelegraph/Decrypt RSS")
    lines.append("")
    
    return "\n".join(lines)


# ====== 主流程 ======

def main():
    start = time.time()
    log("🔄 NBZ早期信号检测 v2 启动")
    
    # 0. 先缓存CoinGecko市场数据（只用1次API调用）
    log("📦 缓存CoinGecko市场数据...")
    cache_coingecko_markets()
    
    # 1. 宏观
    fg = get_fear_greed()
    log(f"📊 F&G: {fg}")
    
    # 2. P0: 成交量突变
    log("🔍 成交量突变检测...")
    volume_sigs = detect_volume_surge()
    log(f"   发现 {len(volume_sigs)} 个")
    
    # 3. P1: 早期启动
    log("🔍 早期启动检测...")
    breakout_sigs = detect_early_breakout()
    log(f"   发现 {len(breakout_sigs)} 个")
    
    if not volume_sigs and not breakout_sigs:
        log("💤 无信号，生成空报告")
    
    # 4. 交叉验证（只验证有信号的币，用缓存避免429）
    validations = {}
    all_coins = set()
    for sig in volume_sigs:
        all_coins.add(sig["coin"])
    for sig in breakout_sigs:
        all_coins.add(sig["coin"])
    
    # 过滤稳定币
    STABLE_COINS = {"USDT", "USDC", "DAI", "FDUSD", "USDD", "XUSD", "TUSD", "BUSD", "GUSD", "PAX", "USTC"}
    for sig_list in [volume_sigs, breakout_sigs]:
        sig_list[:] = [s for s in sig_list if s.get("coin", "").upper() not in STABLE_COINS]
    
    for coin in all_coins:
        if coin.upper() in STABLE_COINS:
            continue
        log(f"🔎 验证 {coin}...")
        
        validations[coin] = {
            "telegram": check_telegram(coin),
            "news": check_news_mention(coin, coin),
            "categories": get_coin_categories(coin),
        }
    
    # 5. 生成报告
    overview = {}
    report = generate_report(volume_sigs, breakout_sigs, validations, overview, fg)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(FINDINGS_FILE, "w") as f:
        f.write(report)
    
    elapsed = time.time() - start
    log(f"✅ 完成! {elapsed:.1f}s")
    log(f"   报告: {FINDINGS_FILE}")
    log(f"   信号: P0={len(volume_sigs)} + P1={len(breakout_sigs)}")


if __name__ == "__main__":
    main()
