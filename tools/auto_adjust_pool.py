#!/usr/bin/env python3
"""
A2+ 选币池自动调整引擎 — 每天根据涨幅榜"为什么会涨"的结论调整赛道容量

数据流:
  1. 读涨幅榜TOP15 → 分析赛道分布
  2. 哪个赛道涨的币多 → 该赛道容量自动+2
  3. 哪个赛道跌的币多/没动静 → 该赛道容量自动-1
  4. 写入 coin_pool_binance.json（下次--prime时生效）
  
用法:
  python3 tools/auto_adjust_pool.py
"""

import json, os, subprocess, tempfile
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PRIME_PATH = os.path.join(DATA_DIR, "coin_pool_binance.json")  # 原coin_pool_prime.json→改名, 2026-06-14
POOL_PATH = os.path.join(DATA_DIR, "coin_pool.json")

# 赛道映射（币名→赛道）
CATEGORY_MAP = {
    'BTC': 'layer1', 'ETH': 'layer1', 'SOL': 'layer1', 'XRP': 'layer1',
    'ADA': 'layer1', 'AVAX': 'layer1', 'DOT': 'layer1', 'NEAR': 'layer1',
    'APT': 'layer1', 'SUI': 'layer1', 'SEI': 'layer1', 'TIA': 'layer1',
    'TON': 'layer1', 'TRX': 'layer1', 'HBAR': 'layer1', 'ALGO': 'layer1',
    'FIL': 'storage', 'AR': 'storage', 'BLZ': 'storage',
    'PHA': 'privacy', 'ROSE': 'privacy', 'SCRT': 'privacy', 'ZEC': 'privacy',
    'XMR': 'privacy', 'DASH': 'privacy', 'RIF': 'privacy',
    'WLD': 'ai', 'FET': 'ai', 'RENDER': 'ai', 'TAO': 'ai', 'AGIX': 'ai',
    'OCEAN': 'ai', 'CGPT': 'ai', 'NMR': 'ai',
    'POND': 'meme', 'DOGE': 'meme', 'SHIB': 'meme', 'PEPE': 'meme',
    'BONK': 'meme', 'WIF': 'meme', 'FLOKI': 'meme', 'MYRO': 'meme',
    'CREAM': 'defi', 'AAVE': 'defi', 'UNI': 'defi', 'LINK': 'oracle',
    'MKR': 'defi', 'COMP': 'defi', 'CRV': 'defi',
    'EIGEN': 'layer2', 'OP': 'layer2', 'ARB': 'layer2', 'MATIC': 'layer2',
    'SAGA': 'gamefi', 'GALA': 'gamefi', 'SAND': 'gamefi', 'MANA': 'gamefi',
    'ONDO': 'rwa', 'POLYX': 'rwa',
    'PENDLE': 'lsd', 'LDO': 'lsd', 'RPL': 'lsd',
    'ATOM': 'cosmos', 'OSMO': 'cosmos', 'KAVA': 'cosmos',
    'KAS': 'pow', 'ETC': 'pow', 'ZEN': 'pow',
    'BNB': 'cex', 'CRO': 'cex', 'OKB': 'cex',
    'DEXE': 'other', 'MDX': 'other',
}

STABLECOINS = {'USDT','USDC','BUSD','DAI','FDUSD','TUSD','USDP','GUSD','PAX','USTC','USD1'}

# 当前默认赛道容量
DEFAULT_CAPACITY = {
    'layer1': 25, 'meme': 25, 'ai': 20, 'defi': 20,
    'gamefi': 15, 'layer2': 12, 'rwa': 10, 'oracle': 8,
    'depin': 8, 'privacy': 6, 'cex': 5, 'cosmos': 6,
    'btc_ecosystem': 6, 'storage': 5, 'nft': 5,
    'crosschain': 4, 'lsd': 4, 'pow': 6, 'other': 30,
}

def get_sector(symbol):
    """推测币的赛道"""
    return CATEGORY_MAP.get(symbol.upper(), 'other')

def fetch_gainers():
    """获取24h涨幅榜TOP30（通过SOCKS5代理绕过451阻断）"""
    url = "https://data-api.binance.vision/api/v3/ticker/24hr"
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
        tmpfile = f.name
    try:
        # 通过 data-api.binance.vision 绕过地域限制（api.binance.com 在部分区域被限制）
        curl_cmd = ["curl", "--compressed", "-s", "--max-time", "30", url]
        result = subprocess.run(
            curl_cmd, stdout=open(tmpfile, 'w'), stderr=subprocess.DEVNULL, timeout=35
        )
        if result.returncode != 0:
            # 备选：走Shadowrocket TUN的默认路由
            curl_cmd = ["curl", "--compressed", "-s", "--max-time", "60",
                        "https://api.binance.com/api/v3/ticker/24hr"]
            subprocess.run(
                curl_cmd, stdout=open(tmpfile, 'w'), stderr=subprocess.DEVNULL, timeout=65, check=True
            )
        with open(tmpfile) as f:
            data = json.load(f)
    finally:
        os.unlink(tmpfile)
    
    usdt = [t for t in data 
            if t['symbol'].endswith('USDT') 
            and t['symbol'].replace('USDT','') not in STABLECOINS]
    
    # 按涨幅排序TOP30
    usdt.sort(key=lambda x: -float(x['priceChangePercent']))
    top30 = usdt[:30]
    
    result = []
    for t in top30:
        sym = t['symbol'].replace('USDT','')
        result.append({
            'symbol': sym,
            'change': float(t['priceChangePercent']),
            'volume': float(t['quoteVolume']),
            'sector': get_sector(sym)
        })
    return result

def fetch_losers():
    """获取24h跌幅TOP30"""
    url = "https://data-api.binance.vision/api/v3/ticker/24hr"
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
        tmpfile = f.name
    try:
        curl_cmd = ["curl", "--compressed", "-s", "--max-time", "30", url]
        result = subprocess.run(
            curl_cmd, stdout=open(tmpfile, 'w'), stderr=subprocess.DEVNULL, timeout=35
        )
        if result.returncode != 0:
            curl_cmd = ["curl", "--compressed", "-s", "--max-time", "60",
                        "https://api.binance.com/api/v3/ticker/24hr"]
            subprocess.run(
                curl_cmd, stdout=open(tmpfile, 'w'), stderr=subprocess.DEVNULL, timeout=65, check=True
            )
        with open(tmpfile) as f:
            data = json.load(f)
    finally:
        os.unlink(tmpfile)
    
    usdt = [t for t in data 
            if t['symbol'].endswith('USDT') 
            and t['symbol'].replace('USDT','') not in STABLECOINS]
    
    usdt.sort(key=lambda x: float(x['priceChangePercent']))
    top30 = usdt[:30]
    
    result = []
    for t in top30:
        sym = t['symbol'].replace('USDT','')
        result.append({
            'symbol': sym,
            'change': float(t['priceChangePercent']),
            'volume': float(t['quoteVolume']),
            'sector': get_sector(sym)
        })
    return result

def adjust_capacity(current_capacity, gainers, losers):
    """根据涨幅榜自动调整赛道容量"""
    new_cap = dict(current_capacity)
    
    # 涨幅榜赛道统计
    sector_up = defaultdict(int)
    for g in gainers:
        if g['change'] > 5:
            sector_up[g['sector']] += 1
    
    # 跌幅榜赛道统计
    sector_down = defaultdict(int)
    for l in losers:
        if l['change'] < -5:
            sector_down[l['sector']] += 1
    
    print("📈 涨幅榜赛道分布:")
    for s, c in sorted(sector_up.items(), key=lambda x: -x[1]):
        print(f"  {s:15s}: {c}个币在涨")
    
    print("\n📉 跌幅榜赛道分布:")
    for s, c in sorted(sector_down.items(), key=lambda x: -x[1]):
        print(f"  {s:15s}: {c}个币在跌")
    
    # 调整算法
    adjustments = {}
    for sector in new_cap:
        up = sector_up.get(sector, 0)
        down = sector_down.get(sector, 0)
        
        net = up - down
        adj = 0
        if net >= 3:
            adj = 3  # 赛道强热，+3
        elif net >= 2:
            adj = 2  # 赛道较热，+2
        elif net >= 1:
            adj = 1  # 略热，+1
        elif net <= -3:
            adj = -2  # 赛道弱势，-2
        elif net <= -2:
            adj = -1  # 略弱，-1
        
        if adj != 0:
            new_val = max(2, min(40, new_cap[sector] + adj))
            adjustments[sector] = (new_cap[sector], new_val, adj)
            new_cap[sector] = new_val
    
    return new_cap, adjustments

def main():
    print("=" * 60)
    print("A2+ 选币池自动调整引擎")
    print("=" * 60)
    
    # 1. 读取当前容量配置
    current_cap = dict(DEFAULT_CAPACITY)
    if os.path.exists(PRIME_PATH):
        try:
            with open(PRIME_PATH) as f:
                existing = json.load(f)
                stored_cap = existing.get('sector_capacity', {})
                if stored_cap:
                    current_cap.update(stored_cap)
                    print(f"✅ 读取现有配置: {len(stored_cap)}个赛道")
        except:
            pass
    
    print(f"\n当前赛道容量: {sum(current_cap.values())}个币")
    
    # 2. 获取涨幅榜
    print("\n📡 获取涨幅榜TOP30...")
    gainers = fetch_gainers()
    losers = fetch_losers()
    
    print(f"   涨幅>5%: {len([g for g in gainers if g['change'] > 5])}个")
    print(f"   跌幅>5%: {len([l for l in losers if l['change'] < -5])}个")
    
    # 3. 自动调整
    print("\n🔄 正在计算赛道调整...")
    new_cap, adjustments = adjust_capacity(current_cap, gainers, losers)
    
    if not adjustments:
        print("   无调整（各赛道热度均衡）")
    else:
        print(f"\n📋 调整方案:")
        print(f"  {'赛道':15s} {'旧':>4s} → {'新':>4s}  {'调整值':>6s}")
        print(f"  {'─'*35}")
        for sec, (old, new, adj) in sorted(adjustments.items(), key=lambda x: -abs(x[1][2])):
            arrow = "↑" if adj > 0 else "↓"
            print(f"  {sec:15s} {old:3d} → {new:3d}  {arrow}{adj:+d}")
    
    # 4. 写入
    total_new = sum(new_cap.values())
    print(f"\n📦 新赛道总容量: {total_new}个币")
    
    # 更新coin_pool_binance.json（只改sector_capacity字段）
    if os.path.exists(PRIME_PATH):
        with open(PRIME_PATH) as f:
            prime = json.load(f)
        prime['sector_capacity'] = new_cap
        prime['auto_adjust_history'] = prime.get('auto_adjust_history', [])
        prime['auto_adjust_history'].append({
            'date': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M'),
            'adjustments': {k: {'old': v[0], 'new': v[1], 'delta': v[2]} 
                           for k, v in adjustments.items()},
            'total_capacity': total_new
        })
        # 只保留最近30天
        prime['auto_adjust_history'] = prime['auto_adjust_history'][-30:]
        with open(PRIME_PATH, 'w') as f:
            json.dump(prime, f, indent=2, ensure_ascii=False)
        print(f"✅ 已写入 {PRIME_PATH}")
    
    print("=" * 60)
    
    # 5. 立刻重建精选池（不等明天 --prime）
    print("\n🔄 正在用新容量重建精选池...")
    # os and subprocess already imported at module level
    env = os.environ.copy()
    # 直连Binance（不强制走SOCKS5，本地有直连能力）
    result = subprocess.run(['python3', 'tools/coin_pool_manager.py', '--prime'],
                          capture_output=True, text=True, timeout=180, env=env)
    print(result.stdout)
    if result.returncode != 0:
        print(f"⚠️  重建失败: {result.stderr}")
    else:
        print("✅ 精选池已用新容量重建，立即生效")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
