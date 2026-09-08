#!/usr/bin/env python3
"""
A3 信号扫描器 v1.0 — 选币策略引擎
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

功能：
  从精选池(70-100个币)中逐个扫描技术信号，输出带标记的候选列表。
  A3的LLM层只需对标记过的币做叙事判断。

参考：NostalgiaForInfinityX7 — 74个买入条件的核心逻辑简化版

输出：
  TARGET/signals.json — 结构化信号数据供A3 LLM读取
  TARGET/signals_report.md — 人类可读报告

用法：
  python3 tools/a3_signal_scanner.py                    # 读默认池(coin_pool.json)
  python3 tools/a3_signal_scanner.py --prime             # 读精选池(coin_pool_prime.json)
  python3 tools/a3_signal_scanner.py --threads 5         # 并行度
  python3 tools/a3_signal_scanner.py --min-volume 50000 # 最小成交量门槛
  python3 tools/a3_signal_scanner.py --output signals.md # 自定义输出

部署位置：AWS /home/ubuntu/zq_web4_trading_system/
数据流：
  AWS → 读coin_pool.json → 拉K线 → 算信号 → 输出signals.json → SCP回Mac
  Mac → A3 LLM读signals.json + 叙事/情绪 → 出最终报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json, os, sys, time, math, argparse, threading, queue
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from collections import defaultdict
import requests

# ─── 常量 ───
BJT = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
POOL_PATH = os.path.join(DATA_DIR, "coin_pool.json")
PRIME_PATH = os.path.join(DATA_DIR, "coin_pool_prime.json")
SIGNALS_PATH = os.path.join(DATA_DIR, "signals.json")
REPORT_PATH = os.path.join(DATA_DIR, "signals_report.md")

# SOCKS5隧道 (2026-08-31修复466/466 ERROR): Mac本机直连Binance被墙(SSL UNEXPECTED_EOF),
# 统一走 127.0.0.1:1080 隧道(与其他工具一致, 直连作为fallback)
SOCKS5_PROXY = {"http": "socks5h://127.0.0.1:1080", "https": "socks5h://127.0.0.1:1080"}

def _binance_get(url, timeout=10):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, proxies=SOCKS5_PROXY, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        # 隧道失败时尝试直连(极少数直连可用场景)
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode())

# 信号权重（总分100，越强越值得买）
SIGNAL_WEIGHTS = {
    "momentum_surge":  30,   # 🚀 动量爆发 — 24h已涨+还在放量（最可靠的小资金信号）
    "vol_breakout":    20,   # 放量突破
    "independent_up":  17,   # 独立于BTC上涨
    "rsi_recovery":    13,   # RSI从底部回升
    "volume_trend":    10,   # 成交量趋势（非脉冲）
    "trend_alignment": 10,   # 多时间框架趋势对齐
}

# 最小成交量门槛（低于此值直接标记不可交易）
MIN_VOLUME_TRADABLE = 100_000    # $100K
MIN_VOLUME_STRONG   = 500_000    # $500K

# 黑名单（与A2 coin_pool_manager.py 保持一致）
STABLECOINS = {'USDT', 'USDC', 'BUSD', 'DAI', 'FDUSD', 'TUSD', 'USDP', 'GUSD', 'PAX', 'USTC', 'USD1', 'SUSD', 'RLUSD', 'USDS', 'USDSB', 'AEUR', 'EURI', 'CUSD', 'CUSDT'}
FIAT_TOKENS = {'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'ARS', 'BRL', 'TRY', 'ZAR', 'NGN', 'PLN', 'RON', 'UAH', 'HKD', 'SGD', 'BIDR', 'IDRT', 'BRZ'}
LEVERAGE_KEYWORDS = ['UP', 'DOWN', 'BULL', 'BEAR', 'LONG', 'SHORT', 'BKRW', 'WBETH', 'STETH', 'PREMIUM', 'HALF', 'HEDGE', 'PERP', 'BVOL', 'IBVOL']

# 时间框架
TIMEFRAMES = {
    "15m": {"limit": 48, "weight": 0.2},
    "1h":  {"limit": 48, "weight": 0.3},
    "4h":  {"limit": 30, "weight": 0.3},
    "1d":  {"limit": 14, "weight": 0.2},
}

# BTC相关性参照
BTC_SYMBOL = "BTCUSDT"

# ─── 工具函数 ───

def now_bjt():
    return datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')

LOSS_BLACKLIST_PATH = f"{os.path.dirname(os.path.abspath(__file__))}/../data/loss_blacklist.json"

def load_loss_blacklist():
    """加载连损黑名单，返回 {symbol: entry_dict}"""
    try:
        if os.path.exists(LOSS_BLACKLIST_PATH):
            with open(LOSS_BLACKLIST_PATH) as f:
                data = json.load(f)
            entries = data.get('entries', {})
            now = datetime.now(BJT)
            # 清理已过期的
            expired = []
            for sym, entry in entries.items():
                expires = entry.get('expires_at', '')
                if expires:
                    try:
                        expires_dt = datetime.strptime(expires, '%Y-%m-%d %H:%M BJT')
                        expires_dt = expires_dt.replace(tzinfo=BJT)
                        if now > expires_dt:
                            expired.append(sym)
                    except:
                        pass
            if expired:
                for sym in expired:
                    del entries[sym]
                with open(LOSS_BLACKLIST_PATH, 'w') as f:
                    data['entries'] = entries
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"  🧹 连损黑名单清理过期: {expired}")
            return entries
    except Exception as e:
        print(f"  ⚠️ 连损黑名单读取失败: {e}")
    return {}

def is_loss_blacklisted(symbol, loss_blacklist):
    """检查币种是否在连损黑名单中"""
    return symbol.upper() in loss_blacklist

def is_blacklisted(symbol):
    """检查币种是否在黑名单中（同步A2的黑名单规则）"""
    # 稳定币
    if symbol in STABLECOINS:
        return True
    # 法币代币
    if symbol in FIAT_TOKENS:
        return True
    # 杠杆/结构化产品
    for kw in LEVERAGE_KEYWORDS:
        if kw in symbol.upper():
            return True
    return False

def fetch_klines(symbol, interval="1h", limit=50):
    """从币安公开API获取K线数据"""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    return _binance_get(url)

def fetch_current_price(symbol):
    """获取当前价格"""
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    return float(_binance_get(url)['price'])

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    return round(100 - 100 / (1 + avg_gain / avg_loss), 1)

def calc_ma(closes, period):
    if len(closes) < period:
        return closes[-1] if closes else 0
    return sum(closes[-period:]) / period

def calc_volume_baseline(klines):
    """计算成交量基线（用近14根的平均，排除异常值）"""
    vols = sorted([float(k[5]) for k in klines[-14:]])
    mid = len(vols) // 2
    return sum(vols[max(0,mid-2):min(len(vols),mid+3)]) / min(5, len(vols))

def count_consecutive_green(klines, n=8):
    """检查最近n根K线中有几根收涨"""
    count = 0
    for k in klines[-n:]:
        if float(k[4]) > float(k[1]):  # close > open
            count += 1
    return count

# ─── 信号检测函数 ───

def check_momentum_surge(klines_1h):
    """
    🚀 动量爆发信号 — 专为小资金设计
    - 24h已涨>3%（不是横盘等突破，是已在涨）
    - 近3根K线还在涨（动量持续）
    - 成交量真实（不是高位派发）
    """
    if not klines_1h or len(klines_1h) < 28:
        return 0, ""
    
    closes = [float(k[4]) for k in klines_1h]
    vols = [float(k[5]) for k in klines_1h]
    
    if len(closes) < 24:
        return 0, ""
    
    # 24h涨幅
    change_24h = (closes[-1] - closes[-24]) / closes[-24] * 100
    
    # 近3根K线涨幅（动量持续性）
    if len(closes) >= 27:
        change_3h = (closes[-1] - closes[-3]) / closes[-3] * 100
    else:
        change_3h = 0
    
    # 近3根平均成交量 vs 24h平均
    avg_vol_3h = sum(vols[-3:]) / 3
    avg_vol_24h = sum(vols[-24:]) / 24 if len(vols) >= 24 else 1
    vol_ratio = avg_vol_3h / avg_vol_24h if avg_vol_24h > 0 else 0
    
    score = 0
    details = []
    
    # 核心：24h已经在涨
    if change_24h >= 8:
        score += 15
        details.append(f"24h+{change_24h:.1f}%🔥")
    elif change_24h >= 5:
        score += 12
        details.append(f"24h+{change_24h:.1f}%")
    elif change_24h >= 3:
        score += 8
        details.append(f"24h+{change_24h:.1f}%")
    elif change_24h >= 1:
        score += 4
        details.append(f"24h+{change_24h:.1f}%")
    
    # 动量持续（近3h还在涨）
    if change_3h > 1.5:
        score += 8
        details.append(f"3h+{change_3h:.1f}%")
    elif change_3h > 0.5:
        score += 5
        details.append(f"3h+{change_3h:.1f}%")
    
    # 量价配合
    if vol_ratio >= 1.5 and change_3h > 0:
        score += 7
        details.append(f"量比{vol_ratio:.1f}x")
    elif vol_ratio >= 1.2 and change_3h > 0:
        score += 4
        details.append(f"量比{vol_ratio:.1f}x(温和)")
    
    if change_24h > 0 and change_3h > 0 and vol_ratio > 1:
        score += 3  # 三个维度一致的奖励分
        details.append("量价齐升✅")
    
    detail_str = ", ".join(details) if details else "无信号"
    return min(score, SIGNAL_WEIGHTS["momentum_surge"]), detail_str


def check_vol_breakout(klines_1h, klines_4h):
    """
    信号1: 放量突破
    - 最新成交量 > 基线 × 1.5x
    - 价格在MA20上方
    - 4h趋势向上
    """
    if not klines_1h or not klines_4h:
        return 0, ""
    
    closes_1h = [float(k[4]) for k in klines_1h]
    vols_1h = [float(k[5]) for k in klines_1h]
    
    latest_vol = vols_1h[-1] if vols_1h else 0
    baseline = calc_volume_baseline(klines_1h)
    ma20 = calc_ma(closes_1h, 20)
    latest_close = closes_1h[-1] if closes_1h else 0
    
    vol_ratio = latest_vol / baseline if baseline > 0 else 0
    
    # 4h趋势
    closes_4h = [float(k[4]) for k in klines_4h]
    ma7_4h = calc_ma(closes_4h, 7)
    latest_4h = closes_4h[-1] if closes_4h else 0
    
    score = 0
    details = []
    
    if vol_ratio >= 1.5:
        score += 15
        details.append(f"量比{vol_ratio:.1f}x")
    elif vol_ratio >= 1.0:
        score += 8
        details.append(f"量比{vol_ratio:.1f}x(温和)")
    
    if latest_close > ma20 and ma20 > 0:
        score += 10
        details.append("价格>MA20")
    
    if latest_4h > ma7_4h:
        score += 5
        details.append("4h趋势向上")
    
    detail_str = ", ".join(details) if details else "无信号"
    return min(score, SIGNAL_WEIGHTS["vol_breakout"]), detail_str


def check_rsi_recovery(klines_1h, klines_4h):
    """
    信号2: RSI从底部回升
    - 当前RSI在35-60之间（不过热）
    - 之前有低于35的记录（从底部爬起来）
    - 4h RSI也在回升
    """
    if not klines_1h:
        return 0, ""
    
    closes_1h = [float(k[4]) for k in klines_1h]
    rsi_now = calc_rsi(closes_1h, 14)
    rsi_4h = calc_rsi([float(k[4]) for k in klines_4h], 14) if klines_4h else 50
    
    # 检查过去24根中是否有RSI<35
    rsi_history = []
    for i in range(14, len(closes_1h)):
        rsi_history.append(calc_rsi(closes_1h[:i+1], 14))
    rsi_min = min(rsi_history) if rsi_history else 50
    
    score = 0
    details = []
    
    if rsi_min < 35 and 35 <= rsi_now <= 60:
        score += 12
        details.append(f"RSI从{rsi_min:.0f}回升至{rsi_now:.0f}")
    elif 30 <= rsi_now <= 55:
        score += 8
        details.append(f"RSI{rsi_now:.0f}(合理区间)")
    
    if 40 <= rsi_4h <= 60:
        score += 8
        details.append(f"4hRSI{rsi_4h:.0f}")
    elif rsi_4h < 40:
        # 4h还在低位，可能还有空间
        score += 5
        details.append(f"4hRSI{rsi_4h:.0f}(低位待起)")
    
    detail_str = ", ".join(details) if details else "无信号"
    return min(score, SIGNAL_WEIGHTS["rsi_recovery"]), detail_str


def check_independent_up(klines_coin, btc_change_24h):
    """
    信号3: 独立于BTC上涨
    - BTC跌/横盘（24h涨幅 < 2%）
    - 该币24h涨幅 > BTC涨幅
    - 成交量真实（不是脉冲）
    """
    if not klines_coin:
        return 0, ""
    
    closes = [float(k[4]) for k in klines_coin]
    if len(closes) < 2:
        return 0, ""
    
    coin_change = (closes[-1] - closes[0]) / closes[0] * 100
    
    score = 0
    details = []
    
    # BTC横盘或跌，币在涨 = 独立动力
    if btc_change_24h < 1 and coin_change > 3:
        score += 15
        details.append(f"独立于BTC(BTC{btc_change_24h:+.1f}% vs +{coin_change:+.1f}%)")
    elif btc_change_24h < 2 and coin_change > 2:
        score += 10
        details.append(f"相对强势(BTC{btc_change_24h:+.1f}% vs +{coin_change:+.1f}%)")
    
    if coin_change > 0:
        score += 5
        details.append(f"24h涨{coin_change:+.1f}%")
    
    detail_str = ", ".join(details) if details else "无信号"
    return min(score, SIGNAL_WEIGHTS["independent_up"]), detail_str


def check_sector_sync(symbol, sector_coins_by_status):
    """
    信号4: 赛道联动放量
    - 同赛道的币也在涨
    - 这是一个简化版，只看赛道热度
    """
    # 简化：这个信号主要靠LLM层判断
    # 脚本只标记"同赛道有哪些币"
    return 0, "（脚本仅标记，LLM判断）"


def check_trend_alignment(klines_15m, klines_1h, klines_4h):
    """
    信号5: 多时间框架趋势对齐
    - 15m: 短期趋势向上
    - 1h: 中期趋势向上
    - 4h: 长期趋势向上
    - 至少2个对齐才算有效
    """
    score = 0
    aligned = 0
    details = []
    
    for tf_name, klines in [("15m", klines_15m), ("1h", klines_1h), ("4h", klines_4h)]:
        if not klines or len(klines) < 7:
            continue
        closes = [float(k[4]) for k in klines]
        ma7 = calc_ma(closes, 7)
        latest = closes[-1]
        slope = (closes[-1] - closes[-4]) / closes[-4] * 100 if len(closes) >= 4 else 0
        
        if latest > ma7 and slope > 0.5:
            score += 5
            aligned += 1
            details.append(f"{tf_name}↑")
        elif latest > ma7:
            score += 3
            details.append(f"{tf_name}→")
        else:
            score -= 2
            details.append(f"{tf_name}↓")
    
    if aligned >= 2:
        score += 5  # 至少2个时间框架对齐的奖励分
    
    detail_str = ", ".join(details) if details else "无信号"
    return min(score, SIGNAL_WEIGHTS["trend_alignment"]), detail_str


def check_volume_trend(klines_1h):
    """
    信号6: 成交量趋势
    - 近7根成交量整体上升（不是单根脉冲）
    - 不是突然放量——是稳步增量
    """
    if not klines_1h or len(klines_1h) < 14:
        return 0, ""
    
    vols = [float(k[5]) for k in klines_1h[-14:]]
    recent_7 = sum(vols[-7:]) / 7
    prev_7 = sum(vols[:7]) / 7
    
    score = 0
    if recent_7 > prev_7 * 1.3 and prev_7 > 0:
        score += 10
        return score, f"成交量7日趋势+{(recent_7/prev_7-1)*100:.0f}%"
    elif recent_7 > prev_7 * 1.1:
        score += 5
        return score, f"成交量温和增长"
    
    return 0, ""


# ─── 扫描单个币 ───

def scan_coin(symbol, usdt_suffix, category, btc_change_24h):
    """对一个币进行全信号扫描"""
    sym = symbol if symbol.endswith('USDT') else symbol + 'USDT'
    
    try:
        # 获取多时间框架K线
        klines_data = {}
        for tf in TIMEFRAMES:
            limit = TIMEFRAMES[tf]["limit"]
            klines_data[tf] = fetch_klines(sym, tf, limit)
            time.sleep(0.05)  # 避免API限速
        
        # 计算各信号
        signals = {}
        total_score = 0
        
        s0_score, s0_detail = check_momentum_surge(klines_data.get("1h", []))
        signals["momentum_surge"] = {"score": s0_score, "detail": s0_detail}
        total_score += s0_score
        
        s1_score, s1_detail = check_vol_breakout(klines_data.get("1h", []), klines_data.get("4h", []))
        signals["vol_breakout"] = {"score": s1_score, "detail": s1_detail}
        total_score += s1_score
        
        s2_score, s2_detail = check_rsi_recovery(klines_data.get("1h", []), klines_data.get("4h", []))
        signals["rsi_recovery"] = {"score": s2_score, "detail": s2_detail}
        total_score += s2_score
        
        s3_score, s3_detail = check_independent_up(klines_data.get("1h", []), btc_change_24h)
        signals["independent_up"] = {"score": s3_score, "detail": s3_detail}
        total_score += s3_score
        
        s5_score, s5_detail = check_trend_alignment(
            klines_data.get("15m", []),
            klines_data.get("1h", []),
            klines_data.get("4h", [])
        )
        signals["trend_alignment"] = {"score": s5_score, "detail": s5_detail}
        total_score += s5_score
        
        s6_score, s6_detail = check_volume_trend(klines_data.get("1h", []))
        signals["volume_trend"] = {"score": s6_score, "detail": s6_detail}
        total_score += s6_score
        
        # 获取当前价格和成交量
        latest_1h = klines_data.get("1h", [])
        if latest_1h:
            current_price = float(latest_1h[-1][4])
            current_vol = float(latest_1h[-1][5])
        else:
            current_price = 0
            current_vol = 0
        
        # 计算24h涨幅（用于gain_24h字段和追高风险控制）
        gain_24h = 0
        if latest_1h and len(latest_1h) >= 24:
            try:
                closes_1h = [float(k[4]) for k in latest_1h]
                gain_24h = (closes_1h[-1] - closes_1h[-24]) / closes_1h[-24] * 100
            except:
                gain_24h = 0
        
        # 单一强信号门 — 必须有一个信号≥其满分60%才算STRONG
        max_weights = {k: v for k, v in SIGNAL_WEIGHTS.items()}
        has_strong_signal = any(
            signals.get(sig, {}).get("score", 0) >= max_weights[sig] * 0.6
            for sig in max_weights
        )
        
        # 判断等级
        if total_score >= 45 and has_strong_signal:
            level = "STRONG"     # 🟢🟢 强烈买入（有至少一个真实强信号）
        elif total_score >= 45 and not has_strong_signal:
            level = "SIGNAL"     # 🟢 总分够但没有强信号→降级SIGNAL
        elif total_score >= 25:
            level = "SIGNAL"     # 🟢 候选（1个明确信号）
        elif total_score >= 15:
            level = "WATCH"      # 🟡 观察（微弱信号）
        else:
            level = "PASS"       # ⚪ 跳过
        
        return {
            "symbol": symbol,
            "category": category,
            "price": round(current_price, 8),
            "volume_24h": current_vol,
            "total_score": total_score,
            "level": level,
            "gain_24h": round(gain_24h, 2),  # 24h涨幅%用于A4追高风险控制
            "signals": signals,
            "scanned_at": now_bjt()
        }
    
    except Exception as e:
        return {
            "symbol": symbol,
            "category": category,
            "price": 0,
            "volume_24h": 0,
            "total_score": 0,
            "level": "ERROR",
            "gain_24h": 0,  # 数据获取失败，默认0
            "signals": {},
            "error": str(e),
            "scanned_at": now_bjt()
        }


# ─── 批量扫描 ───

def batch_scan(pool_coins, max_threads=3):
    """批量扫描所有币"""
    # 先获取BTC 24h变化
    try:
        btc_ticker = fetch_klines("BTCUSDT", "1h", 24)
        btc_closes = [float(k[4]) for k in btc_ticker]
        btc_change_24h = (btc_closes[-1] - btc_closes[0]) / btc_closes[0] * 100 if btc_closes else 0
    except:
        btc_change_24h = 0
        print("  ⚠️  BTC数据获取失败，独立上涨信号可能不准")
    
    results = []
    total = len(pool_coins)
    print(f"  开始扫描 {total} 个币, BTC 24h变化: {btc_change_24h:+.2f}%")
    
    for i, coin in enumerate(pool_coins):
        symbol = coin.get('symbol', '')
        category = coin.get('category', 'other')
        usdt_suffix = coin.get('usdt', f'{symbol}USDT')
        
        result = scan_coin(symbol, usdt_suffix, category, btc_change_24h)
        results.append(result)
        
        if (i + 1) % 10 == 0 or i == total - 1:
            signal_count = len([r for r in results if r['level'] in ('STRONG', 'SIGNAL')])
            print(f"    进度: {i+1}/{total} | 已发现信号: {signal_count}")
    
    return results


# ─── 主逻辑 ───

def main():
    parser = argparse.ArgumentParser(description='A3 信号扫描器')
    parser.add_argument('--prime', action='store_true', help='使用精选池(coin_pool_prime.json)')
    parser.add_argument('--threads', type=int, default=3, help='并行线程数')
    parser.add_argument('--min-volume', type=float, default=50000, help='最小成交量门槛')
    parser.add_argument('--output', type=str, default='stdout', help='输出格式: stdout/md/json')
    parser.add_argument('--quick', action='store_true', help='快速模式(只扫成交量TOP30)')
    args = parser.parse_args()
    
    print(f"[{now_bjt()}] A3 信号扫描器 v1.0 启动")
    
    # 1. 读取选币库
    pool_path = PRIME_PATH if args.prime else POOL_PATH
    pool_data = None
    all_coins = []
    
    if os.path.exists(pool_path):
        with open(pool_path) as f:
            pool_data = json.load(f)
        all_coins = pool_data.get('pool', [])
    
    if not all_coins:
        print(f"  ⚠️  选币库 {pool_path} 不存在或为空，尝试直接从Binance获取...")
        try:
            ss = args.min_volume
            url = "https://api.binance.com/api/v3/ticker/24hr"
            tickers = _binance_get(url)
            usdt_pairs = []
            for t in tickers:
                s = t['symbol']
                if s.endswith('USDT') and not is_blacklisted(s.replace('USDT', '')):
                    usdt_pairs.append({
                        'symbol': s.replace('USDT', ''),
                        'volume_24h_usd': float(t['quoteVolume']),
                        'change_24h': float(t['priceChangePercent']),
                        'price': float(t['lastPrice']),
                        'category': 'other',
                        'status': 'active',
                    })
            all_coins = sorted(usdt_pairs, key=lambda x: -x['volume_24h_usd'])
            print(f"  直接从Binance获取: {len(all_coins)}个USDT对")
        except Exception as e:
            print(f"  ❌ 降级失败: {e}")
            return
    
    # 如果选了prime但没有prime文件，降级到普通池
    if args.prime and not os.path.exists(PRIME_PATH):
        print(f"  ⚠️  精选池不存在，使用全量池")
    
    print(f"  选币库: {len(all_coins)}个币")

    # 🔴 连损黑名单加载（2026-07-17 ZH Daily Research追加）
    loss_blacklist = load_loss_blacklist()
    loss_blacklisted_syms = set()
    
    # 黑名单过滤 + 连损黑名单 + 成交量门槛
    before_filter = len(all_coins)
    filtered = []
    for c in all_coins:
        sym = c.get('symbol', '')
        if is_blacklisted(sym):
            continue
        if c.get('volume_24h_usd', 0) < args.min_volume:
            continue
        if c.get('status', 'active') == 'removed':
            continue
        # 🔴 连损黑名单检查
        if is_loss_blacklisted(sym, loss_blacklist):
            loss_blacklisted_syms.add(sym)
            continue
        filtered.append(c)
    blacklisted_count = before_filter - len(filtered) - len([c for c in all_coins if c.get('volume_24h_usd', 0) < args.min_volume or c.get('status') == 'removed'])

    print(f"  黑名单排除+成交量过滤: {len(filtered)}个币（总量{before_filter}→{len(filtered)}, 黑名单{blacklisted_count}个）")
    if loss_blacklisted_syms:
        print(f"  🔴 连损黑名单跳过: {', '.join(sorted(loss_blacklisted_syms))}")
    
    # 快速模式：只扫成交量TOP30
    if args.quick:
        filtered = sorted(filtered, key=lambda x: -x.get('volume_24h_usd', 0))[:30]
        print(f"  快速模式: TOP30")
    
    if not filtered:
        print(f"  ❌ 无符合条件的币，退出")
        return
    
    # 2. 扫描
    results = batch_scan(filtered, args.threads)
    
    # 2b. 涨幅榜TOP20补充扫描 — 确保最新热点币不在池中也能被扫到
    scanned_syms = {r['symbol'] for r in results}
    try:
        gurl = "https://api.binance.com/api/v3/ticker/24hr"
        gdata = _binance_get(gurl)
        gusdt = [t for t in gdata if t['symbol'].endswith('USDT') 
                 and float(t['priceChangePercent']) > 5
                 and t['symbol'].replace('USDT','') not in scanned_syms
                 and not is_blacklisted(t['symbol'].replace('USDT',''))]
        for kw in ['UP','DOWN','BULL','BEAR','LONG','SHORT','BKRW','WBETH','STETH']:
            gusdt = [t for t in gusdt if kw not in t['symbol'].upper()]
        gainer_candidates = sorted(gusdt, key=lambda x: -float(x['priceChangePercent']))[:20]
        if gainer_candidates:
            print(f"\n  🚀 涨幅榜补充: {len(gainer_candidates)}个币（不在池中）")
            gainer_coins = []
            for g in gainer_candidates:
                sym = g['symbol'].replace('USDT', '')
                gainer_coins.append({
                    'symbol': sym,
                    'volume_24h_usd': float(g['quoteVolume']),
                    'change_24h': float(g['priceChangePercent']),
                    'price': float(g['lastPrice']),
                    'category': 'other',
                    'status': 'active',
                    '_gainer_supplement': True,
                })
            gainer_results = batch_scan(gainer_coins, args.threads)
            for gr in gainer_results:
                gr['_gainer_supplement'] = True
            results.extend(gainer_results)
            print(f"  ✅ 涨幅榜补充完成: +{len(gainer_results)}个（含信号分）")
    except Exception as e:
        print(f"  ⚠️  涨幅榜补充失败: {e}（不影响已有扫描结果）")
    
    # 3. 按分数排序
    results.sort(key=lambda x: -x['total_score'])
    
    # 4. 统计
    strong = [r for r in results if r['level'] == 'STRONG']
    signal = [r for r in results if r['level'] == 'SIGNAL']
    watch = [r for r in results if r['level'] == 'WATCH']
    passed = [r for r in results if r['level'] == 'PASS']
    errors = [r for r in results if r['level'] == 'ERROR']
    
    print(f"\n  📊 扫描完成:")
    print(f"     🟢🟢 STRONG: {len(strong)} (买入推荐)")
    print(f"     🟢 SIGNAL:   {len(signal)} (候选)")
    print(f"     🟡 WATCH:    {len(watch)} (观察)")
    print(f"     ⚪ PASS:     {len(passed)}")
    print(f"     ❌ ERROR:    {len(errors)}")
    
    # 5. 输出
    output_data = {
        "scanned_at": now_bjt(),
        "total_scanned": len(results),
        "summary": {
            "strong": len(strong),
            "signal": len(signal),
            "watch": len(watch),
            "pass": len(passed),
            "error": len(errors)
        },
        "results": results[:20],  # 只保留TOP20
    }
    
    if args.output == 'json':
        print(json.dumps(output_data, indent=2))
    elif args.output == 'md':
        generate_report(results)
    else:
        # 输出到stdout
        print(f"\n{'='*70}")
        print(f"A3 信号报告 — {now_bjt()}")
        print(f"{'='*70}")
        print(f"扫描: {len(results)}个币 | STRONG={len(strong)} SIGNAL={len(signal)} WATCH={len(watch)}")
        print()
        
        print("## 🟢🟢 STRONG（强烈买入推荐）")
        for r in strong[:5]:
            sigs = [f"{k}:{v['score']}" for k,v in r['signals'].items() if v['score'] > 0]
            print(f"  {r['symbol']:10s} | 总分:{r['total_score']:2d} | ${r['price']:<15.8f} | {', '.join(sigs[:3])}")
        
        print(f"\n## 🟢 SIGNAL（候选）")
        for r in signal[:5]:
            sigs = [f"{k}:{v['score']}" for k,v in r['signals'].items() if v['score'] > 0]
            print(f"  {r['symbol']:10s} | 总分:{r['total_score']:2d} | ${r['price']:<15.8f} | {', '.join(sigs[:3])}")
        
        # 写入文件
        output_data["results"] = results  # 保存完整结果
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SIGNALS_PATH, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\n  ✅ 信号数据已写入: {SIGNALS_PATH}")
    
    return output_data


def generate_report(results):
    """生成人类可读报告"""
    strong = [r for r in results if r['level'] == 'STRONG']
    signal = [r for r in results if r['level'] == 'SIGNAL']
    watch = [r for r in results if r['level'] == 'WATCH']
    
    lines = []
    lines.append(f"# A3 信号报告")
    lines.append(f"日期: {now_bjt()}")
    lines.append(f"扫描: {len(results)}个币")
    lines.append(f"")
    
    lines.append(f"## 🟢🟢 STRONG（强烈买入推荐）")
    lines.append(f"| 币种 | 赛道 | 总分 | 价格 | 信号 |")
    lines.append(f"|:----|:----|:----:|:----:|:-----|")
    for r in strong:
        sigs = [v['detail'] for k,v in r['signals'].items() if v['score'] > 0]
        lines.append(f"| {r['symbol']} | {r['category']} | {r['total_score']} | ${r['price']} | {'; '.join(sigs[:3])} |")
    
    lines.append(f"")
    lines.append(f"## 🟢 SIGNAL（候选）")
    for r in signal:
        sigs = [v['detail'] for k,v in r['signals'].items() if v['score'] > 0]
        lines.append(f"- {r['symbol']}: {r['total_score']}分 - {'; '.join(sigs[:3])}")
    
    lines.append(f"")
    lines.append(f"## 🟡 WATCH（观察）")
    for r in watch[:10]:
        sigs = [v['detail'] for k,v in r['signals'].items() if v['score'] > 0]
        lines.append(f"- {r['symbol']}: {r['total_score']}分 - {'; '.join(sigs[:3])}")
    
    report = '\n'.join(lines)
    
    with open(REPORT_PATH, 'w') as f:
        f.write(report)
    print(f"  ✅ 报告已写入: {REPORT_PATH}")
    
    return report


if __name__ == '__main__':
    main()
