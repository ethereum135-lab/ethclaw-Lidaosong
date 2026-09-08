#!/usr/bin/env python3
"""
ZQ Web 4.0 选币库管理器 v2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

功能：
  1. 从Binance拉取全量USDT交易对24h成交量
  2. 按成交量排序，构建三层池子：master(80)/watch(120)/excluded(其余)
  3. 计算每个币的"吸筹评分"（蓄力阶段指标，不是追涨指标）
  4. 写入 data/coin_pool.json

吸筹评分核心指标（替代纯成交量排序）：
  - 量比 0.8~1.5x（有量但还没爆）
  - 4h趋势向上 
  - RSI 30~60（没超买）
  - 24h涨幅 -5%~+5%（还没涨过，有空间）
  - 价格位置：不在近期高点

运行：
  python3 tools/coin_pool_manager.py --update    # 全量更新
  python3 tools/coin_pool_manager.py --status    # 查看当前状态

依赖：
  pip install python-binance
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json, os, sys, time
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
POOL_PATH = os.path.join(DATA_DIR, "coin_pool.json")
AUTH_PATH = os.path.join(BASE_DIR, "config", "auth.json")

# ─── 池子配置 ───
MASTER_SIZE = 80      # 主力池：Top80成交量（保留字段，旧过渡用）
WATCH_SIZE = 120      # 观察池：81-200名（保留字段，旧过渡用）
CACHE_TTL_HOURS = 6   # 缓存有效期（避免频繁拉取）

# ─── 精选池配置（2026-05-19 新增）───
PRIME_TARGET_TOTAL = 200          # 精选池目标总量（70-100之间浮动）
PRIME_MIN_VOLUME = 30000         # 精选池最小成交量门槛
PRIME_SECTOR_CAPACITY = {        # 赛道容量（LLM每日调整）— 扩至200币版
    'layer1': 25, 'meme': 25, 'ai': 20, 'defi': 20,
    'gamefi': 15, 'layer2': 12, 'rwa': 10, 'oracle': 8,
    'depin': 8, 'privacy': 6, 'cex': 5, 'cosmos': 6,
    'btc_ecosystem': 6, 'storage': 5, 'nft': 5,
    'crosschain': 4, 'lsd': 4, 'pow': 6, 'other': 30,
}
PRIME_CONFIG_PATH = os.path.join(DATA_DIR, "coin_pool_binance.json")  # 原coin_pool_prime.json→改名, 2026-06-14

# ─── 资产大类分类（覆盖120+币种，按Freqtrade+CoinGecko赛道标准）───
CATEGORY_MAP = {
    # === Layer1 (公链) ===
    'BTC': 'layer1', 'ETH': 'layer1', 'SOL': 'layer1', 'XRP': 'layer1',
    'ADA': 'layer1', 'AVAX': 'layer1', 'DOT': 'layer1', 'NEAR': 'layer1',
    'APT': 'layer1', 'SUI': 'layer1', 'SEI': 'layer1', 'TIA': 'layer1',
    'TON': 'layer1', 'TRX': 'layer1', 'HBAR': 'layer1', 'ALGO': 'layer1',
    'VET': 'layer1', 'THETA': 'layer1', 'EOS': 'layer1', 'XLM': 'layer1',
    'ICP': 'layer1', 'CRO': 'layer1', 'KAS': 'layer1', 'FLOW': 'layer1',
    'MINA': 'layer1', 'ZIL': 'layer1', 'EGLD': 'layer1',
    'KSM': 'layer1', 'XTZ': 'layer1', 'NEO': 'layer1',
    'WAVES': 'layer1', 'IOST': 'layer1', 'FTM': 'layer1',
    'CELO': 'layer1', 'LUNC': 'layer1', 'LUNA': 'layer1',
    'ASTR': 'layer1', 'ROSE': 'layer1',
    'KAIA': 'layer1', 'SAGA': 'layer1',
    'MONAD': 'layer1', 'BERA': 'layer1',

    # === Layer2 ===
    'MATIC': 'layer2', 'POL': 'layer2', 'ARB': 'layer2', 'OP': 'layer2',
    'IMX': 'layer2', 'METIS': 'layer2', 'MNT': 'layer2',
    'STRK': 'layer2', 'LRC': 'layer2', 'SKL': 'layer2',
    'BOBA': 'layer2', 'CTSI': 'layer2', 'CELR': 'layer2',

    # === DeFi ===
    'AAVE': 'defi', 'UNI': 'defi', 'CRV': 'defi', 'CAKE': 'defi',
    'PENDLE': 'defi', 'MKR': 'defi', 'COMP': 'defi',
    'LDO': 'defi', 'ENA': 'defi', 'RPL': 'defi',
    'SUSHI': 'defi', 'SNX': 'defi', 'BAL': 'defi',
    'DYDX': 'defi', 'GMX': 'defi', 'RDNT': 'defi',
    'JUP': 'defi', 'PERP': 'defi', 'YFI': 'defi',
    'CVX': 'defi', 'FXS': 'defi', 'GNS': 'defi',
    'INJ': 'defi', 'SPELL': 'defi', 'ALPHA': 'defi',
    'TRU': 'defi', 'ALCX': 'defi', 'BIFI': 'defi',
    'PHA': 'defi', 'UMA': 'defi', 'BAND': 'defi',
    'RUNE': 'defi', 'KP3R': 'defi', 'AKRO': 'defi',
    'SXP': 'defi', 'SNT': 'defi', 'CREAM': 'defi',
    'BOND': 'defi', 'AMP': 'defi', 'LIT': 'defi',
    'CHESS': 'defi', 'FLM': 'defi', 'LEVER': 'defi',
    'IRIS': 'defi', 'BETA': 'defi', 'ALPACA': 'defi',
    'DODO': 'defi', 'BADGER': 'defi', 'DEGO': 'defi',
    'FORTH': 'defi', 'ERN': 'defi', 'QUICK': 'defi',
    'PSP': 'defi', 'FIS': 'defi',

    # === Meme ===
    'DOGE': 'meme', 'SHIB': 'meme', 'PEPE': 'meme', 'FLOKI': 'meme',
    'BONK': 'meme', 'WIF': 'meme', 'PENGU': 'meme',
    'NEIRO': 'meme', 'DOGS': 'meme', 'MYRO': 'meme',
    'MEME': 'meme', 'TURBO': 'meme', 'POPCAT': 'meme',
    'MOG': 'meme', 'BRETT': 'meme',
    'TRUMP': 'meme', 'BODEN': 'meme', 'MAGA': 'meme',
    'BABYDOGE': 'meme',
    'CHIP': 'meme', 'FWOG': 'meme',
    'SPX': 'meme', 'GIGA': 'meme',
    'CHZ': 'meme',

    # === AI ===
    'FET': 'ai', 'AGIX': 'ai', 'TAO': 'ai', 'RNDR': 'ai', 'RENDER': 'ai',
    'WLD': 'ai', 'GRT': 'ai', 'AKT': 'ai',
    'AR': 'ai', 'LPT': 'ai', 'OCEAN': 'ai',
    'VIRTUAL': 'ai', 'AI16Z': 'ai', 'AIXBT': 'ai',
    'ARKM': 'ai', 'NMR': 'ai',
    'CGPT': 'ai', 'DEAI': 'ai', 'MODE': 'ai',
    'AIGENSYN': 'ai',

    # === RWA ===
    'ONDO': 'rwa', 'POLYX': 'rwa', 'RSR': 'rwa', 'GFI': 'rwa',
    'CPOOL': 'rwa', 'OM': 'rwa', 'TOKEN': 'rwa', 'IXS': 'rwa',
    'PAXG': 'rwa', 'XAUT': 'rwa',

    # === DePIN ===
    'HNT': 'depin', 'FIL': 'depin', 'MOBILE': 'depin',
    'IOTX': 'depin', 'DIONE': 'depin',
    'ANKR': 'depin', 'LTO': 'depin', 'DGB': 'depin',

    # === Oracle ===
    'LINK': 'oracle', 'PYTH': 'oracle', 'API3': 'oracle',
    'BAND': 'oracle', 'TRB': 'oracle', 'UMA': 'oracle',
    'DIA': 'oracle',

    # === Privacy ===
    'ZEC': 'privacy', 'XMR': 'privacy', 'DASH': 'privacy',
    'SCRT': 'privacy', 'ROSE': 'privacy',

    # === GameFi ===
    'GALA': 'gamefi', 'SAND': 'gamefi', 'MANA': 'gamefi',
    'AXS': 'gamefi', 'ENJ': 'gamefi', 'PIXEL': 'gamefi',
    'MAGIC': 'gamefi', 'ILV': 'gamefi',
    'GHST': 'gamefi', 'YGG': 'gamefi', 'SLP': 'gamefi',
    'BIGTIME': 'gamefi', 'DAR': 'gamefi',
    'MBOX': 'gamefi', 'ALICE': 'gamefi', 'HIGH': 'gamefi',
    'PYR': 'gamefi', 'VOXEL': 'gamefi', 'PRIME': 'gamefi',

    # === BTC生态系统 ===
    'STX': 'btc_ecosystem', 'RIF': 'btc_ecosystem', 'ORDI': 'btc_ecosystem',
    'SATS': 'btc_ecosystem', 'RATS': 'btc_ecosystem',

    # === Cosmos生态系统 ===
    'ATOM': 'cosmos', 'OSMO': 'cosmos', 'DYM': 'cosmos',
    'TIA': 'cosmos', 'KUJI': 'cosmos',

    # === CEX/平台币 ===
    'BNB': 'cex', 'LEO': 'cex', 'OKB': 'cex', 'GT': 'cex',
    'MX': 'cex', 'BGB': 'cex',

    # === LSD/LRT ===
    'RPL': 'lsd', 'SSV': 'lsd', 'EIGEN': 'lsd', 'SWISE': 'lsd',

    # === Storage ===
    'FIL': 'storage', 'AR': 'storage', 'STORJ': 'storage',
    'BLZ': 'storage',

    # === NFT ===
    'BLUR': 'nft', 'LOOKS': 'nft', 'SUPER': 'nft',

    # === Cross-chain ===
    'LAYER': 'crosschain', 'ZRO': 'crosschain', 'WORMHOLE': 'crosschain',

    # === PoW ===
    'ETC': 'pow', 'KAS': 'pow', 'LTC': 'pow', 'BCH': 'pow',
    'RVN': 'pow', 'ZEN': 'pow',
}

def now_bjt():
    return datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')

def load_pool():
    """读取当前选币库（兼容v2和v3格式）"""
    if os.path.exists(POOL_PATH):
        with open(POOL_PATH) as f:
            pool = json.load(f)
        # v3格式兼容：如果数据在pool键下
        if 'pool' in pool and isinstance(pool['pool'], list):
            pass  # v3格式，直接返回
        # v2格式兼容：从pools键合并数据
        elif 'pools' in pool:
            all_coins = pool['pools'].get('master', []) + pool['pools'].get('watch', []) + pool['pools'].get('excluded', [])
            pool['pool'] = all_coins
        return pool
    return {'version': 3, 'last_updated': None, 'total_coins': 0,
            'pool': [], 'behavior': {}, 'accumulation': {}}

def classify_symbol(symbol):
    """按名称归类"""
    base = symbol.replace('USDT', '').replace('USD', '')
    return CATEGORY_MAP.get(base, 'other')

def fetch_all_tickers(client, max_retries=3):
    """从Binance获取所有USDT交易对信息（通过 data-api.binance.vision 绕过地域限制）

    Args:
        client: Binance client实例（保留参数兼容，实际使用data-api）
        max_retries: 最大重试次数
    Returns:
        list: USDT交易对列表，失败返回空列表
    """
    import time
    from urllib.request import Request, urlopen

    for attempt in range(max_retries):
        try:
            # 通过 data-api.binance.vision 获取全量ticker（绕过地域封锁）
            gurl = "https://data-api.binance.vision/api/v3/ticker/24hr"
            greq = Request(gurl, headers={"User-Agent": "Mozilla/5.0"})
            gdata = json.loads(urlopen(greq, timeout=15).read().decode())
            # 直接过滤
            usdt_pairs = []
            for t in gdata:
                s = t['symbol']
                if s.endswith('USDT') and not any(x in s for x in ['UP', 'DOWN', 'BULL', 'BEAR', 'BKRW']):
                    usdt_pairs.append({
                        'symbol': s.replace('USDT', ''),
                        'volume_24h_usd': float(t['quoteVolume']),
                        'change_24h': float(t['priceChangePercent']),
                        'price': float(t['lastPrice']),
                        'high_24h': float(t['highPrice']),
                        'low_24h': float(t['lowPrice']),
                    })
            return usdt_pairs
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) * 5
                print(f"  ⚠️  data-api调用失败(第{attempt+1}次): {e}")
                print(f"     等待{wait}秒后重试...")
                time.sleep(wait)
            else:
                print(f"  ❌ data-api调用失败({max_retries}次): {e}")
                return []

def compute_accumulation_score(coin, klines_data):
    """
    计算吸筹评分（蓄力阶段指标）。
    分数越高 = 越有可能是"准备涨"而不是"已经涨完"
    
    评分维度：
      - 量比：0.8~1.5x最理想（+25分），>2.0x扣分（太热了）
      - 4h趋势：向上+20分，向下-20分
      - RSI：30~50最佳（+25分），50~60还行（+15分），>70扣分（-10分）
      - 24h涨幅：-3%~+3%最佳（+20分），>+10%扣分（-15分）
      - 价格位置：在近24h低点附近（+15分），在高点附近（-10分）
    """
    score = 0
    details = {}
    
    vol = coin.get('volume_surge', 1.0)
    trend = coin.get('trend_4h', 0)
    rsi = coin.get('rsi', 50)
    chg = coin.get('change_24h', 0)
    price = coin.get('price', 0)
    high = coin.get('high_24h', 0)
    low = coin.get('low_24h', 0)
    
    # 1. 量比评分
    if 0.8 <= vol <= 1.5:
        score += 25
        details['volume'] = f'量比{vol:.2f}x 理想(25分)'
    elif 1.5 < vol <= 2.0:
        score += 10
        details['volume'] = f'量比{vol:.2f}x 偏热(10分)'
    elif vol > 2.0:
        score -= 10
        details['volume'] = f'量比{vol:.2f}x 过热(-10分)'
    else:
        score -= 5
        details['volume'] = f'量比{vol:.2f}x 缩量(-5分)'
    
    # 2. 趋势评分
    if trend >= 1:
        score += 20
        details['trend'] = f'4h趋势{trend:+d}向上(20分)'
    elif trend == 0:
        score += 5
        details['trend'] = f'4h趋势横盘(5分)'
    else:
        score -= 20
        details['trend'] = f'4h趋势{trend}向下(-20分)'
    
    # 3. RSI评分
    if 30 <= rsi <= 50:
        score += 25
        details['rsi'] = f'RSI{rsi:.0f} 低位(25分)'
    elif 50 < rsi <= 60:
        score += 15
        details['rsi'] = f'RSI{rsi:.0f} 适中(15分)'
    elif 60 < rsi <= 70:
        score += 5
        details['rsi'] = f'RSI{rsi:.0f} 偏强(5分)'
    elif rsi > 70:
        score -= 10
        details['rsi'] = f'RSI{rsi:.0f} 超买(-10分)'
    else:
        score -= 5
        details['rsi'] = f'RSI{rsi:.0f} 超卖(-5分)'
    
    # 4. 涨幅评分
    if -3 <= chg <= 3:
        score += 20
        details['change'] = f'24h{chg:+.2f}% 未涨(20分)'
    elif 3 < chg <= 8:
        score += 10
        details['change'] = f'24h{chg:+.2f}% 小幅上涨(10分)'
    elif 8 < chg <= 15:
        score -= 5
        details['change'] = f'24h{chg:+.2f}% 已涨不少(-5分)'
    elif chg > 15:
        score -= 15
        details['change'] = f'24h{chg:+.2f}% 大涨过(-15分)'
    elif -8 <= chg < -3:
        score += 5
        details['change'] = f'24h{chg:+.2f}% 小幅下跌(5分)'
    else:
        score -= 5
        details['change'] = f'24h{chg:+.2f}% 大跌(-5分)'
    
    # 5. 价格位置评分（在近24h低点附近最优）
    if high > low and price > 0:
        pos = (price - low) / (high - low) if (high - low) > 0 else 0.5
        if pos < 0.3:
            score += 15
            details['position'] = f'价格在低位(pos={pos:.2f})(15分)'
        elif pos < 0.5:
            score += 10
            details['position'] = f'价格在中低位(pos={pos:.2f})(10分)'
        elif pos < 0.7:
            score += 0
            details['position'] = f'价格在中位(pos={pos:.2f})(0分)'
        else:
            score -= 10
            details['position'] = f'价格在高位(pos={pos:.2f})(-10分)'
    
    return score, details

def meets_entry_standards(coin):
    """选币库入池标准
    
    选币库是候选池，不是执行池。入池只排除绝对做不了的：
    1. 非稳定币
    2. 非杠杆/结构化产品
    
    成交量和价格精度由A4执行时检查（不同资金量不同容忍度）。
    价格不设硬门槛——低价币有潜力的很多。
    """
    symbol = coin['symbol']
    
    # 排除稳定币
    stablecoins = {'USDT', 'USDC', 'BUSD', 'DAI', 'FDUSD', 'TUSD', 'USDP', 'GUSD', 'PAX', 'USTC', 'USD1', 'RLUSD', 'EUR', 'EURI', 'SUSD', 'USDS', 'USDSB', 'AEUR', 'XUSD', 'USDM'}
    if symbol in stablecoins:
        return False, '稳定币'
    
    # 排除杠杆/结构化产品
    leveraged_keywords = ['UP', 'DOWN', 'BULL', 'BEAR', 'LONG', 'SHORT', 'BKRW', 'WBETH', 'STETH']
    for kw in leveraged_keywords:
        if kw in symbol.upper():
            return False, f'杠杆/结构化产品({kw})'

    return True, ''


def build_pool(client):
    """构建扁平化选币库（黑名单模式 + 动态健康监控 — 2026-05-18 v3.1）

    A2 = 安检门 + 动态健康监控
    所有通过黑名单的币按成交量排序后全部放入池子。
    每天用实时数据做健康检查，持续淘汰明显不行的币。

    健康检查（7天趋势）：
      - 成交量连续3天<$50K → 🔴 移出
      - 成交量连续5天下跌>30% → 🔴 移出
      - 下架/黑客/RUG → 🔴 立即移出
      - 成交量环比单日跌>50% → 🟡 标记
      - 成交量排名跌出TOP300 → 🟡 标记
      - 24h波动>30% → 🟡 标记
    """
    from collections import Counter

    print(f"[{now_bjt()}] 开始更新选币库（黑名单+动态健康）...")

    # 0. 读取旧池子（保留历史数据）
    old_pool = load_pool()
    old_coins = {c['symbol']: c for c in old_pool.get('pool', [])}
    print(f"  旧池子: {len(old_coins)}个币（含历史数据）")

    # 1. 获取全量USDT交易对
    print("  正在拉取Binance全量USDT交易对...")
    all_coins = fetch_all_tickers(client)

    # 1b. 如果获取失败，降级使用上次有效数据
    if not all_coins:
        print("  ⚠️  Binance获取失败，尝试使用上次有效数据降级...")
        if old_coins:
            print(f"  使用上次数据: {len(old_coins)}个币（标记为过时）")
            for c in old_coins.values():
                c['stale'] = True
            print(f"  ✅ 降级成功，使用上次有效数据")
            return old_pool
        else:
            print("  ❌ 无有效旧数据，无法降级")
            return None

    print(f"  获取到 {len(all_coins)} 个交易对")

    # 2. 入池标准过滤（仅黑名单排除）
    passed = []
    excluded_reasons = {}
    for c in all_coins:
        ok, reason = meets_entry_standards(c)
        if ok:
            passed.append(c)
        else:
            excluded_reasons[c['symbol']] = reason
    print(f"  黑名单通过: {len(passed)}个 | 排除: {len(all_coins)-len(passed)}个")
    for sym, reason in sorted(excluded_reasons.items()):
        print(f"    排除 {sym}: {reason}")

    # 3. 按24h成交量排序
    passed.sort(key=lambda x: -x['volume_24h_usd'])

    today_label = now_bjt()[:10]  # YYYY-MM-DD

    # 4. 构建带历史追踪的健康池
    all_entries = []
    health_counters = {'active': 0, 'warning': 0, 'removed': 0}

    for i, c in enumerate(passed):
        sym = c['symbol']
        new_rank = i + 1
        new_volume = c['volume_24h_usd']
        new_change = c['change_24h']
        new_price = round(c['price'], 8)

        # 获取旧记录（如果有）
        old_record = old_coins.get(sym, {})
        old_history = old_record.get('history', [])
        old_status = old_record.get('status', 'active')
        old_warnings = old_record.get('warnings', [])

        # 构建今日快照
        today_snap = {
            'date': today_label,
            'volume': round(new_volume, 2),
            'rank': new_rank,
            'price': new_price,
            'change_24h': new_change,
        }

        # 追加历史（保留最近7天）
        history = old_history + [today_snap]
        if len(history) > 7:
            history = history[-7:]

        # === 动态健康检查 ===
        warnings = []
        new_status = 'active'

        # 检查1: 下架/跑路检测（无数据或价格归零）
        if new_price <= 0:
            warnings.append('价格归零')
            new_status = 'removed'

        # 检查2: 成交量连续3天<$50K
        if len(history) >= 3:
            last3_vol = [h['volume'] for h in history[-3:]]
            if all(v < 50000 for v in last3_vol):
                warnings.append('成交量连续3天<$50K，流动性枯竭')
                new_status = 'removed'

        # 检查3: 成交量连续5天下跌>30%
        if len(history) >= 5:
            last5_vol = [h['volume'] for h in history[-5:]]
            vol_trend = all(last5_vol[i] > last5_vol[i+1] * 1.3 for i in range(4))
            if vol_trend:
                warnings.append('成交量连续5天下跌>30%，趋势性失活')
                new_status = 'removed'

        # 检查4: 成交量排名跌出TOP300（仅池子>=300时才检查）
        if new_rank > 300 and len(passed) >= 300:
            warnings.append(f'排名跌至{new_rank}名（TOP300以外）')
            if old_status == 'warning' and '排名' in str(old_warnings):
                # 连续2次排名在300外 → 淘汰
                warnings.append('排名持续在TOP300外')
                new_status = 'removed'
            else:
                new_status = 'warning'

        # 检查5: 成交量环比单日跌>50%
        if len(history) >= 2:
            prev_vol = history[-2]['volume']
            if prev_vol > 0 and new_volume < prev_vol * 0.5:
                warnings.append(f'成交量日环比跌{(1-new_volume/prev_vol)*100:.0f}%')
                new_status = 'warning'

        # 检查6: 24h波动>30%
        if abs(new_change) > 30:
            warnings.append(f'24h波动{new_change:+.1f}%')
            new_status = 'warning'

        # 如果之前就是removed但历史数据还保留着
        if old_status == 'removed' and new_status == 'active':
            # 如果已恢复活动迹象，需要多天确认才恢复
            new_status = 'warning'
            warnings.append('之前被淘汰，需连续观察')

        # 更新warnings（保留最近的，不要堆积）
        if warnings:
            # 保留旧warnings中的持久性问题+新的
            persistent_warnings = [w for w in old_warnings if '之前被淘汰' in w or '排名' in w]
            warnings = persistent_warnings + warnings[-5:]  # 最多5条
        else:
            warnings = []

        # 构建条目
        entry = {
            'symbol': sym,
            'volume_24h_usd': new_volume,
            'change_24h': new_change,
            'price': new_price,
            'rank': new_rank,
            'category': classify_symbol(sym),
            'last_scored': now_bjt(),
            'status': new_status,
            'warnings': warnings,
            'history': history,
        }
        all_entries.append(entry)
        health_counters[new_status] = health_counters.get(new_status, 0) + 1

    print(f"\n  总候选: {len(all_entries)}个币")
    print(f"    🟢 active:   {health_counters.get('active', 0)}个")
    print(f"    🟡 warning:  {health_counters.get('warning', 0)}个")
    print(f"    🔴 removed:  {health_counters.get('removed', 0)}个")

    # 统计赛道分布
    cat_counter = Counter(e['category'] for e in all_entries if e['status'] != 'removed')
    print(f"\n  活跃赛道分布（排除已淘汰）:")
    for cat, cnt in cat_counter.most_common(8):
        print(f"    {cat}: {cnt}个")
    other_count = cat_counter.get('other', 0)
    if other_count > 0:
        print(f"    (待分类/other: {other_count}个)")

    # 5. 构建coin_pool.json（保留旧behavior/accumulation数据）
    old_pool_data = load_pool()
    old_behavior = old_pool_data.get('behavior', {})
    old_accumulation = old_pool_data.get('accumulation', {})
    
    pool = {
        'version': 4,
        'last_updated': now_bjt(),
        'total_coins': len(all_entries),
        'total_active': health_counters.get('active', 0),
        'total_warning': health_counters.get('warning', 0),
        'total_removed': health_counters.get('removed', 0),
        'pool': all_entries,
        'behavior': old_behavior,
        'accumulation': old_accumulation,
        'metrics': {
            'active_count': health_counters.get('active', 0),
            'warning_count': health_counters.get('warning', 0),
            'removed_count': health_counters.get('removed', 0),
            'last_full_update': now_bjt(),
            'schema': 'v4_dynamic_health'
        }
    }

    # 6. 写入文件
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(POOL_PATH, 'w') as f:
        json.dump(pool, f, indent=2, ensure_ascii=False)

    print(f"\n  ✅ 选币库已写入: {POOL_PATH}")
    print(f"  总计 {pool['total_coins']} 个币种（active={pool['total_active']}/warning={pool['total_warning']}/removed={pool['total_removed']}）")
    print(f"  最后更新: {pool['last_updated']}")

    return pool

def record_trade(symbol, entry_price, exit_price, hold_minutes, exit_reason):
    """记录一次交易到选币库的behavior字段。

    Args:
        symbol: 币种名（如 XRP，无USDT后缀）
        entry_price: 买入价格
        exit_price: 卖出价格
        hold_minutes: 持仓时间（分钟）
        exit_reason: 退出原因（如 E1-E6, 末位淘汰等）
    """
    pool = load_pool()
    if 'behavior' not in pool:
        pool['behavior'] = {}
    
    pnl_pct = round((exit_price - entry_price) / entry_price * 100, 2) if entry_price > 0 else 0
    
    trade = {
        'entry': round(entry_price, 8),
        'exit': round(exit_price, 8),
        'hold_min': hold_minutes,
        'pnl_pct': pnl_pct,
        'exit_reason': exit_reason,
        'timestamp': now_bjt()
    }
    
    if symbol not in pool['behavior']:
        pool['behavior'][symbol] = {
            'trades': [],
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'avg_pnl': 0.0,
            'avg_hold_min': 0
        }
    
    pool['behavior'][symbol]['trades'].append(trade)
    pool['behavior'][symbol]['total_trades'] += 1
    if pnl_pct > 0:
        pool['behavior'][symbol]['wins'] += 1
    else:
        pool['behavior'][symbol]['losses'] += 1
    
    b = pool['behavior'][symbol]
    b['win_rate'] = round(b['wins'] / b['total_trades'] * 100, 1) if b['total_trades'] > 0 else 0.0
    b['avg_pnl'] = round(sum(t['pnl_pct'] for t in b['trades']) / len(b['trades']), 2)
    b['avg_hold_min'] = round(sum(t['hold_min'] for t in b['trades']) / len(b['trades']), 0)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(POOL_PATH, 'w') as f:
        json.dump(pool, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ behavior[{symbol}] 记录成功 | PnL: {pnl_pct:+.2f}% | 持仓: {hold_minutes}min | 理由: {exit_reason}")
    return True


def build_prime_pool(full_pool):
    """从全量池中精选200个优质币 — 涨幅榜为主通道 v6
    
    v6 哲学转变（2026-05-30 老李方向）：
    币安涨幅榜 = 主通道（几百万用户用真金白银投票，明牌告诉你谁在涨）
    综合评分 = 补充（填充剩余赛道名额）
    
    Args:
        full_pool: build_pool() 输出的完整池子
    
    Returns:
        dict: 精选池结构
    """
    from collections import defaultdict
    
    pool_coins = full_pool.get('pool', [])
    
    # 稳定币/法币/杠杆（与a3_signal_scanner.py保持一致）
    STABLE_LIST = {
        'USDT','USDC','BUSD','DAI','FDUSD','TUSD','USDP','GUSD','PAX','USTC',
        'USD1','SUSD','USDS','USDSB','AEUR','RLUSD',
        'EUR','EURI','GBP','JPY','AUD','CAD','CHF','ARS','BRL','TRY',
        'ZAR','NGN','PLN','RON','UAH','HKD','SGD','BIDR','IDRT','BRZ'
    }
    LEVERAGE_KEYWORDS = ['UP','DOWN','BULL','BEAR','LONG','SHORT','BKRW','WBETH','STETH']
    
    # ─── 0. 涨幅榜为主通道 ───
    # 先拿涨幅榜，再从全量池填充剩余名额
    gainer_coins = []  # 涨幅榜入选的币
    gainer_symbols = set()
    
    try:
        from urllib.request import urlopen, Request
        gurl = "https://data-api.binance.vision/api/v3/ticker/24hr"
        greq = Request(gurl, headers={"User-Agent": "Mozilla/5.0"})
        gdata = json.loads(urlopen(greq, timeout=10).read().decode())
        
        # 过滤：只取USDT交易对，排除稳定币/杠杆
        gusdt = [t for t in gdata if t['symbol'].endswith('USDT')]
        gusdt = [t for t in gusdt if t['symbol'].replace('USDT','') not in STABLE_LIST]
        for kw in LEVERAGE_KEYWORDS:
            gusdt = [t for t in gusdt if kw not in t['symbol'].upper()]
        # 按涨幅降序
        gusdt.sort(key=lambda x: -float(x['priceChangePercent']))
        
        top_gainers = gusdt[:40]  # 取TOP40，后面会按成交量过滤
        
        print(f"  🚀 涨幅榜主通道: 获取{len(top_gainers)}个币")
        for g in top_gainers:
            sym = g['symbol'].replace('USDT', '')
            vol = float(g['quoteVolume'])
            pct = float(g['priceChangePercent'])
            
            # 简单过滤：成交量≥门槛 + 非极小涨幅
            if vol < PRIME_MIN_VOLUME:
                print(f"    ⏭️  {sym}+{pct:.1f}% 成交量${vol:,.0f}<门槛，跳过")
                continue
            if pct < 3:
                continue  # <3%不叫涨幅榜
            
            sector = classify_symbol(sym)
            gainer_coins.append({
                'symbol': sym,
                'volume_24h_usd': vol,
                'change_24h': pct,
                'price': float(g['lastPrice']),
                'volume_change_24h': 0,
                'category': sector,
                'status': 'active',
                '_gainer_entry': True,   # 标记为涨幅榜来源
                '_composite_score': 85,  # 涨幅榜币默认高分
            })
            gainer_symbols.add(sym)
            print(f"    ✅ {sym}+{pct:.1f}% 入选（{sector}, 成交量${vol:,.0f}）")
    except Exception as e:
        print(f"  ⚠️  涨幅榜获取失败: {e}（降级使用综合评分）")
    
    gainer_count = len(gainer_coins)
    print(f"\n  📊 涨幅榜核心: {gainer_count}个币直接入选")
    
    # ─── 1. 过滤：排除removed + 零成交量 + 已从涨幅榜入选的 ───
    active = [c for c in pool_coins 
              if c.get('status', '') != 'removed'
              and c.get('volume_24h_usd', 0) >= PRIME_MIN_VOLUME
              and c['symbol'] not in gainer_symbols]
    
    if not active and not gainer_coins:
        print("  ⚠️  无符合条件的币，使用全量池")
        return full_pool
    
    # 读取赛道容量配置
    prime_config = {}
    if os.path.exists(PRIME_CONFIG_PATH):
        try:
            with open(PRIME_CONFIG_PATH) as f:
                existing = json.load(f)
                prime_config = existing.get('sector_capacity', {})
        except:
            pass
    sector_capacity = prime_config if prime_config else PRIME_SECTOR_CAPACITY.copy()
    
    # ─── 2. 计算每个赛道已被涨幅榜占用多少 ───
    gainer_sector_count = defaultdict(int)
    for g in gainer_coins:
        gainer_sector_count[g.get('category', 'other')] += 1
    
    sector_counts = dict(gainer_sector_count)
    
    if not active:
        # 没有剩余候选，涨幅榜本身就是整个池
        prime_coins = list(gainer_coins)
        print("  📌 涨幅榜已占满（无评分填充需要）")
    else:
        print(f"  评分候选: {len(active)}个币（涨幅榜已选{gainer_count}个，填充剩余赛道容量）")
        
        # ─── 3. 按赛道分组 ───
        by_sector = defaultdict(list)
        for c in active:
            by_sector[c.get('category', 'other')].append(c)
        for sec in by_sector:
            by_sector[sec].sort(key=lambda x: -x.get('volume_24h_usd', 0))
        
        # ─── 4. 综合评分（只对非涨幅榜的候选币） ───
        for c in active:
            vol = c.get('volume_24h_usd', 0)
            vol_change = c.get('volume_change_24h', 0)
            price_change = abs(c.get('change_24h', 0))
            
            vol_score = min(100, vol / 500000) * 100 if vol < 50000000 else 100
            vol_change_score = min(100, max(0, vol_change * 2)) if vol_change > 0 else 0
            
            if price_change > 0:
                price_score = min(100, price_change * 5)
                if price_change > 20:
                    price_score = max(0, 100 - (price_change - 20) * 3)
            else:
                price_score = max(0, 50 + price_change * 3)
            
            total_score = vol_score * 0.30 + vol_change_score * 0.25 + price_score * 0.25 + 20
            c['_composite_score'] = round(total_score, 1)
        
        # ─── 5. 按赛道填充剩余容量 ───
        prime_coins = list(gainer_coins)
        for sector in sorted(sector_capacity.keys()):
            capacity = sector_capacity[sector]
            used = gainer_sector_count.get(sector, 0)
            remaining = max(0, capacity - used)
            
            coins = by_sector.get(sector, [])
            coins.sort(key=lambda x: -x.get('_composite_score', 0))
            fill = coins[:remaining]
            prime_coins.extend(fill)
            sector_counts[sector] = used + len(fill)
            
            if used > 0 or fill:
                print(f"    {sector:12s}: 涨幅榜{used}个 + 评分{len(fill)}个（容量{capacity}）")
        
        # ─── 6. 如果超过目标总量，从综合分最低的裁剪 ───
        over_count = len(prime_coins) - PRIME_TARGET_TOTAL
        if over_count > 0:
            print(f"  ⚠️  精选池超{PRIME_TARGET_TOTAL}: {len(prime_coins)}个，裁减{over_count}个...")
            prime_coins.sort(key=lambda x: x.get('_composite_score', 0))
            prime_coins = prime_coins[over_count:]
            prime_coins.sort(key=lambda x: -x.get('volume_24h_usd', 0))
    
    # ─── 7. 淘汰僵尸币 ───
    stale = [c for c in prime_coins 
             if c.get('status') == 'warning' 
             and c.get('change_24h', 0) < -10
             and c.get('volume_24h_usd', 0) < 100000]
    if stale:
        print(f"  🗑️  淘汰{len(stale)}个僵尸币（warning+跌>10%+成交量<$100K）")
        for s in stale:
            prime_coins.remove(s)
            print(f"    ❌ {s['symbol']}")
    
    final_gainer_count = len([c for c in prime_coins if c.get('_gainer_entry')])
    print(f"\n  最终精选池: {len(prime_coins)}个币（涨幅榜{final_gainer_count}个）")
    
    # ─── 8. 构建精选池结构 ───
    prime_pool = {
        'version': 6,  # v6: 涨幅榜为主通道
        'last_updated': now_bjt(),
        'total_screened': len(pool_coins),
        'total_prime': len(prime_coins),
        'gainer_core': final_gainer_count,
        'sector_capacity': sector_capacity,
        'sector_counts': sector_counts,
        'pool': prime_coins,
        'metrics': {
            'schema': 'v6_gainer_primary',
            'filter_criteria': {
                'min_volume': PRIME_MIN_VOLUME,
                'target_total': PRIME_TARGET_TOTAL,
                'gainer_first': True,
            },
            'last_full_update': full_pool.get('last_updated', now_bjt()),
        }
    }
    
    # 9. 写入文件
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PRIME_CONFIG_PATH, 'w') as f:
        json.dump(prime_pool, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ 精选池v6已写入: {PRIME_CONFIG_PATH}")
    print(f"  总量 {len(prime_coins)} 个币（涨幅榜{final_gainer_count}个 + 评分{len(prime_coins)-final_gainer_count}个）")
    
    return prime_pool


def show_status():
    """显示当前选币库状态"""
    pool = load_pool()
    last_up = pool.get('last_updated', '从未更新')

    print(f"\n📊 选币库状态")
    print(f"{'='*50}")
    print(f"  版本: v{pool.get('version', 1)}")
    print(f"  最后更新: {last_up}")

    if last_up != '从未更新':
        try:
            last_dt = datetime.strptime(last_up.split('+')[0], '%Y-%m-%d %H:%M:%S')
            hours_ago = (datetime.now() - last_dt).total_seconds() / 3600
            print(f"  距今: {hours_ago:.0f}小时前")
            if hours_ago > 24:
                print(f"  ⚠️ 超过24小时未更新")
        except:
            pass

    print(f"  总币种数: {pool.get('total_coins', 0)}")

    coins = pool.get('pool', [])
    if coins:
        print(f"\n  候选池: {len(coins)}个币")
        top5 = [c['symbol'] if isinstance(c, dict) else str(c) for c in coins[:5]]
        print(f"    Top5成交量: {', '.join(top5)}")

        # 赛道分布
        from collections import Counter
        cats = Counter(c.get('category', 'other') for c in coins if isinstance(c, dict))
        if cats:
            print(f"\n  赛道分布:")
            for cat, cnt in cats.most_common(8):
                print(f"    {cat}: {cnt}个")

    acc = pool.get('accumulation', {})
    if acc:
        print(f"\n  吸筹评分数据: {len(acc)}个币有评分")

    beh = pool.get('behavior', {})
    if beh:
        total_trades = sum(d['total_trades'] for d in beh.values())
        wins = sum(d['wins'] for d in beh.values())
        print(f"\n  行为追踪数据: {len(beh)}个币种, {total_trades}笔交易")
        print(f"    胜: {wins} | 负: {total_trades - wins} | 胜率: {wins/max(total_trades,1)*100:.1f}%")
        top3 = sorted(beh.items(), key=lambda x: -x[1]['total_trades'])[:3]
        top3_strs = ', '.join(f'{s}({d["total_trades"]}笔)' for s,d in top3)
        print(f"    最活跃: {top3_strs}")
    else:
        print(f"\n  行为追踪: ❌ 无数据（A4每次SELL后自动记录）")

    return pool

def update_accumulation_scores(client):
    """
    为选币库中的币计算吸筹评分。
    从Binance获取每个币的K线数据 → 计算评分 → 写入pool
    """
    pool = load_pool()
    if not pool.get('pool'):
        print("❌ 选币库为空，请先运行 --update")
        return

    print(f"\n[{now_bjt()}] 开始计算吸筹评分...")

    all_coins = pool.get('pool', [])
    
    total = len(all_coins)
    scores = {}
    
    for i, coin in enumerate(all_coins):
        symbol = coin['symbol'] if isinstance(coin, dict) else coin
        print(f"  [{i+1}/{total}] {symbol}...", end=' ')
        
        try:
            # 获取K线数据计算
            klines = client.get_klines(symbol=symbol + 'USDT', interval='30m', limit=50)
            if klines and len(klines) >= 6:
                closes = [float(k[4]) for k in klines]
                vols = [float(k[5]) for k in klines]
                
                # 量比
                prev3 = sum(vols[-4:-1]) / 3 if len(vols) >= 4 else 1
                vol_ratio = vols[-1] / prev3 if prev3 > 0 else 1
                
                # RSI (简化计算)
                gains = sum(max(closes[i] - closes[i-1], 0) for i in range(1, min(15, len(closes))))
                losses = sum(max(closes[i-1] - closes[i], 0) for i in range(1, min(15, len(closes))))
                rsi = 50
                if losses == 0 and gains > 0:
                    rsi = 100
                elif losses > 0:
                    rs = gains / losses
                    rsi = 100 - 100 / (1 + rs)
                
                # 4h趋势(从30mK线近似)
                if len(closes) >= 12:
                    trend_4h = sum(1 for j in range(1, 13) if closes[-j] > closes[-j-1]) - sum(1 for j in range(1, 13) if closes[-j] < closes[-j-1])
                    trend_4h = max(-2, min(2, trend_4h // 4))
                else:
                    trend_4h = 0
                
                # 价格位置
                high_24 = max(closes[-24:]) if len(closes) >= 24 else max(closes)
                low_24 = min(closes[-24:]) if len(closes) >= 24 else min(closes)
                curr = closes[-1]
                
                coin_data = {
                    'volume_surge': round(vol_ratio, 2),
                    'trend_4h': trend_4h,
                    'trend': trend_4h,
                    'rsi': round(rsi, 1),
                    'change_24h': float(coin.get('change_24h', 0)) if isinstance(coin, dict) else 0,
                    'price': curr,
                    'high_24h': high_24,
                    'low_24h': low_24,
                }
                
                sc, details = compute_accumulation_score(coin_data, {})
                scores[symbol] = {
                    'score': sc,
                    'volume_surge': round(vol_ratio, 2),
                    'rsi': round(rsi, 1),
                    'trend_4h': trend_4h,
                    'details': details
                }
                print(f"吸筹分{sc}")
            else:
                print(f"数据不足")
                scores[symbol] = {'score': 0, 'error': '数据不足'}
        except Exception as e:
            print(f"失败: {e}")
            scores[symbol] = {'score': 0, 'error': str(e)}
        
        time.sleep(0.3)  # Binance限流
    
    # 按吸筹评分排序
    ranked = sorted(scores.items(), key=lambda x: -x[1]['score'])
    
    print(f"\n  吸筹评分Top10（蓄力阶段候选）：")
    for sym, data in ranked[:10]:
        sc = data['score']
        vol = data.get('volume_surge', '?')
        rsi = data.get('rsi', '?')
        trend = data.get('trend_4h', '?')
        print(f"    {sym:8s} 吸筹分{sc:+3d} | 量比{vol} | RSI{rsi} | trend{trend:+d}")
    
    # 写入pool
    pool['accumulation'] = scores
    pool['accumulation_updated'] = now_bjt()
    
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(POOL_PATH, 'w') as f:
        json.dump(pool, f, indent=2, ensure_ascii=False)
    
    print(f"\n  ✅ 吸筹评分已写入 {POOL_PATH}")
    print(f"  共评分 {len(scores)} 个币种")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ZQ选币库管理器')
    parser.add_argument('--update', action='store_true', help='全量更新选币库（从Binance拉取）')
    parser.add_argument('--prime', action='store_true', help='从全量池精选70-100个优质币（按赛道分配）')
    parser.add_argument('--scores', action='store_true', help='计算吸筹评分')
    parser.add_argument('--status', action='store_true', help='查看当前状态')
    parser.add_argument('--record-trade', nargs=5, metavar=('SYMBOL', 'ENTRY', 'EXIT', 'HOLD_MIN', 'REASON'),
                        help='记录一次交易到behavior: SYMBOL ENTRY_PRICE EXIT_PRICE HOLD_MINUTES EXIT_REASON')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
        sys.exit(0)
    
    # --record-trade 不需要Binance客户端
    if args.record_trade:
        sym, entry, exit_, hold, reason = args.record_trade
        try:
            entry_f = float(entry)
            exit_f = float(exit_)
            hold_i = int(float(hold))
            record_trade(sym.upper(), entry_f, exit_f, hold_i, reason)
            sys.exit(0)
        except ValueError as e:
            print(f"❌ 参数错误: {e}")
            print("   格式: SYMBOL ENTRY_PRICE EXIT_PRICE HOLD_MINUTES REASON")
            sys.exit(1)
    
    # 需要Binance客户端（仅scores模式必需，prime/update现已用data-api绕过）
    if args.scores:
        try:
            from binance.client import Client
            auth = json.load(open(AUTH_PATH))
            client = Client(auth['binance']['api_key'], auth['binance']['api_secret'])
        except Exception as e:
            print(f"❌ 无法连接Binance: {e}")
            sys.exit(1)
    else:
        client = None  # prime/update 使用 data-api，不需要Binance客户端
    
    if args.update:
        pool = build_pool(client)
    elif args.prime:
        pool = build_pool(client)
    
    if args.prime:
        if 'pool' not in locals() or not pool:
            pool = load_pool()
        build_prime_pool(pool)
    
    if args.scores:
        update_accumulation_scores(client)
    
    if not args.update and not args.scores and not args.prime:
        show_status()
        print("\n用法: python3 tools/coin_pool_manager.py --update   # 全量更新")
        print("      python3 tools/coin_pool_manager.py --scores   # 计算吸筹评分")
        print("      python3 tools/coin_pool_manager.py --status   # 查看状态")
