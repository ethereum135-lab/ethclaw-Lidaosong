#!/usr/bin/env python3
"""
ZQ Web 4.0 选币库增量更新 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

目的：填补全量池/精选池每天只有05:00一次快照的14小时空窗期
      使ARDR这种盘中突涨+37%的币能被系统及时捕获

依赖：requests (pip install requests)
运行: python3 tools/coin_pool_incremental_update.py
建议cron: 12:00 + 18:00 各一次

做三件事：
  1. 刷新全量池所有币的 change_24h / volume_24h_usd / price（拉实时ticker）
  2. 扫描涨幅榜TOP30 → 不在精选池的币自动补充
  3. 修复status: 排名恢复/涨幅转正 → warning→active
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import json, os, sys, time
from datetime import datetime, timezone, timedelta
from collections import defaultdict

BJT = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
POOL_PATH = os.path.join(DATA_DIR, "coin_pool.json")
PRIME_PATH = os.path.join(DATA_DIR, "coin_pool_binance.json")  # 原coin_pool_prime.json→改名, 2026-06-14

# 与 coin_pool_manager.py 保持一致
STABLE_LIST = {
    'USDT','USDC','BUSD','DAI','FDUSD','TUSD','USDP','GUSD','PAX','USTC',
    'USD1','SUSD','USDS','USDSB','AEUR','RLUSD',
    'EUR','EURI','GBP','JPY','AUD','CAD','CHF','ARS','BRL','TRY',
    'ZAR','NGN','PLN','RON','UAH','HKD','SGD','BIDR','IDRT','BRZ'
}
LEVERAGE_KEYWORDS = ['UP','DOWN','BULL','BEAR','LONG','SHORT','BKRW','WBETH','STETH']

PRIME_MIN_VOLUME = 30000      # 精选池最小成交量门槛
GAINER_TOP_N = 30             # 检查涨幅榜TOP N

def now_bjt():
    return datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')

def fetch_all_tickers():
    """从币安拉全量24hr ticker"""
    import requests
    gurl = "https://api.binance.com/api/v3/ticker/24hr"
    resp = requests.get(gurl, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # 过滤USDT交易对
    usdt = [t for t in data if t['symbol'].endswith('USDT')]
    usdt = [t for t in usdt if t['symbol'].replace('USDT','') not in STABLE_LIST]
    for kw in LEVERAGE_KEYWORDS:
        usdt = [t for t in usdt if kw not in t['symbol'].upper()]
    # 建立 symbol→ticker 映射
    ticker_map = {}
    for t in usdt:
        sym = t['symbol'].replace('USDT', '')
        ticker_map[sym] = t
    return ticker_map

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def incremental_update():
    print(f"[{now_bjt()}] ===== 选币库增量更新开始 =====")
    
    # ─── 加载现有数据 ───
    full_pool = load_json(POOL_PATH)
    prime_pool = load_json(PRIME_PATH)
    
    if not full_pool:
        print("❌ 全量池不存在，跳过")
        return False
    if not prime_pool:
        print("❌ 精选池不存在，跳过")
        return False
    
    pool_coins = full_pool.get('pool', [])
    prime_coins = prime_pool.get('pool', [])
    prime_symbols = {c['symbol'] for c in prime_coins}
    pool_symbols = {c['symbol'] for c in pool_coins}
    
    print(f"  全量池: {len(pool_coins)}个币 (上次: {full_pool.get('last_updated','?')})")
    print(f"  精选池: {len(prime_coins)}个币 (上次: {prime_pool.get('last_updated','?')})")
    
    # ─── 第1步：拉实时ticker ───
    print("\n📡 拉取实时ticker...")
    try:
        ticker_map = fetch_all_tickers()
        print(f"  ✅ 获取 {len(ticker_map)} 个USDT交易对实时数据")
    except Exception as e:
        print(f"  ❌ ticker获取失败: {e}")
        return False
    
    # ─── 第2步：刷新全量池数据 ───
    print("\n🔄 刷新全量池 change_24h / volume / price...")
    updated_count = 0
    for c in pool_coins:
        sym = c.get('symbol', '')
        t = ticker_map.get(sym)
        if not t:
            continue
        old_change = c.get('change_24h', 0)
        try:
            new_change = float(t['priceChangePercent'])
            new_vol = float(t['quoteVolume'])
            new_price = float(t['lastPrice'])
        except (ValueError, KeyError):
            continue
        
        c['change_24h'] = new_change
        c['volume_24h_usd'] = new_vol
        c['price'] = new_price
        # 标记这份数据是增量刷新的
        c['_incremental_updated_at'] = now_bjt()
        updated_count += 1
        
        # 记录明显的涨幅变化
        change_diff = new_change - old_change
        if abs(change_diff) > 5:
            print(f"    {sym}: {old_change:+.1f}% → {new_change:+.1f}% (Δ{change_diff:+.1f}%)")
    
    print(f"  ✅ 刷新 {updated_count}/{len(pool_coins)} 个币")
    
    # ─── 第3步：修复status ───
    def _sym(c):
        return c.get('symbol', '?')
    print("\n🔧 修复status（warning→active）...")
    fixed_count = 0
    for c in pool_coins:
        if c.get('status') == 'warning':
            chg = c.get('change_24h', 0)
            vol = c.get('volume_24h_usd', 0)
            # 涨幅为正 + 有成交量 → 说明涨回来了，升级active
            if chg > 5 and vol >= PRIME_MIN_VOLUME:
                c['status'] = 'active'
                c['warnings'] = [w for w in c.get('warnings', []) 
                                 if '排名' not in w]  # 清理旧排名警告
                print(f"    {_sym(c)}: {chg:+.1f}% vol=${vol:,.0f} → active")
                fixed_count += 1
    print(f"  ✅ 修复 {fixed_count} 个币的status")
    
    # ─── 第4步：检查涨幅榜新币 ───
    print(f"\n🚀 检查涨幅榜TOP{GAINER_TOP_N}中的新币...")
    
    # 从ticker计算涨幅榜
    all_tickers = list(ticker_map.values())
    all_tickers.sort(key=lambda x: -float(x['priceChangePercent']))
    top_gainers = all_tickers[:GAINER_TOP_N]
    
    new_entries = []
    for g in top_gainers:
        sym = g['symbol'].replace('USDT', '')
        vol = float(g['quoteVolume'])
        pct = float(g['priceChangePercent'])
        
        if vol < PRIME_MIN_VOLUME:
            continue
        if pct < 3:
            continue
        
        # 已经在精选池了 → 跳过
        if sym in prime_symbols:
            continue
        
        # 不在精选池 → 补充
        # 给新币分配赛道：先尝试从全量池的category复用
        category = 'other'
        for pc in pool_coins:
            if pc.get('symbol') == sym:
                category = pc.get('category', 'other')
                break
        
        new_entry = {
            'symbol': sym,
            'volume_24h_usd': vol,
            'change_24h': pct,
            'price': float(g['lastPrice']),
            'volume_change_24h': 0,
            'category': category,
            'status': 'active',
            '_gainer_entry': True,
            '_composite_score': 85,
            '_incremental_added': True,
        }
        new_entries.append(new_entry)
        
        # 如果不在全量池 → 也补进去
        if sym not in pool_symbols:
            pool_coins.append({
                'symbol': sym,
                'volume_24h_usd': vol,
                'change_24h': pct,
                'price': float(g['lastPrice']),
                'rank': 999,
                'category': category,
                'last_scored': now_bjt(),
                'status': 'active',
            })
            pool_symbols.add(sym)
            print(f"    🆕 {sym}: +{pct:.1f}% vol=${vol:,.0f} | 补入全量池+精选池")
        else:
            print(f"    🆕 {sym}: +{pct:.1f}% vol=${vol:,.0f} | 补入精选池（已在全量池）")
    
    print(f"  ✅ 新增 {len(new_entries)} 个涨幅榜币到精选池")
    
    # ─── 第4.5步：从signals.json捡漏盘中高涨幅但已回落的币 ───
    signals_path = os.path.join(DATA_DIR, "signals.json")
    signals_caught = 0
    if os.path.exists(signals_path):
        try:
            with open(signals_path) as f:
                sigs = json.load(f)
            sig_results = sigs.get('results', [])
            for r in sig_results:
                sym = r.get('symbol', '')
                gain = r.get('gain_24h', 0)
                vol = r.get('volume_24h', 0)
                price = r.get('price', 0)
                if sym in prime_symbols:
                    continue
                if gain < 10 or vol < PRIME_MIN_VOLUME:
                    continue
                # signals.json里此币今天曾涨>10%，但当前可能已回落 → 补充进精选池
                category = r.get('category', 'other')
                # 尝试从全量池拿更准确的category
                for pc in pool_coins:
                    if pc.get('symbol') == sym:
                        category = pc.get('category', category)
                        break
                prime_coins.append({
                    'symbol': sym,
                    'volume_24h_usd': vol,
                    'change_24h': float(r.get('gain_24h', 0)),
                    'price': price,
                    'volume_change_24h': 0,
                    'category': category,
                    'status': 'active',
                    '_gainer_entry': True,
                    '_composite_score': 85,
                    '_incremental_added': True,
                    '_from_signals_supplement': True,
                })
                prime_symbols.add(sym)
                # 同时补全量池（如果在全量池里已经是warning需修复）
                for pc in pool_coins:
                    if pc.get('symbol') == sym:
                        pc['status'] = 'active'
                        pc['change_24h'] = float(r.get('gain_24h', pc.get('change_24h', 0)))
                        break
                else:
                    # 不在全量池 → 补
                    pool_coins.append({
                        'symbol': sym, 'volume_24h_usd': vol,
                        'change_24h': float(r.get('gain_24h', 0)),
                        'price': price, 'rank': 999, 'category': category,
                        'last_scored': now_bjt(), 'status': 'active',
                    })
                    pool_symbols.add(sym)
                print(f"    🔍 {sym}: signals曾+{gain:.1f}% vol=${vol:,.0f} | 补入精选池(捡漏)")
                signals_caught += 1
        except Exception as e:
            print(f"  ⚠️ signals.json解析失败: {e}")
    if signals_caught > 0:
        print(f"  ✅ 从signals捡漏 {signals_caught} 个盘中高涨幅币")
    else:
        print(f"  📋 signals捡漏: 无新币")
    
    # 把新币加入精选池（不重新排序，直接追加）
    if new_entries:
        prime_coins.extend(new_entries)
    
    # ─── 第5步：重算精选池的统计数据 ───
    final_gainer_count = len([c for c in prime_coins if c.get('_gainer_entry')])
    
    # ─── 第6步：写入文件 ───
    print(f"\n💾 写入文件...")
    
    # 更新全量池
    full_pool['last_updated'] = now_bjt()
    full_pool['total_coins'] = len(pool_coins)
    full_pool['total_active'] = len([c for c in pool_coins if c.get('status') == 'active'])
    full_pool['total_warning'] = len([c for c in pool_coins if c.get('status') == 'warning'])
    full_pool['total_removed'] = len([c for c in pool_coins if c.get('status') == 'removed'])
    full_pool['pool'] = pool_coins  # 排好序的
    save_json(POOL_PATH, full_pool)
    
    # 更新精选池(coin_pool_binance.json)
    prime_pool['last_updated'] = now_bjt()
    prime_pool['total_coins'] = len(prime_coins)
    prime_pool['total_screened'] = len(prime_coins)  # 增量更新时保持一致
    prime_pool['gainer_core'] = final_gainer_count
    prime_pool['pool'] = prime_coins
    save_json(PRIME_PATH, prime_pool)
    
    print(f"\n✅ 增量更新完成!")
    print(f"  全量池: {len(pool_coins)}个币 (active={full_pool['total_active']})")
    print(f"  精选池: {len(prime_coins)}个币 (涨幅榜{final_gainer_count}个) -> data/coin_pool_binance.json")
    print(f"  时间戳: {now_bjt()}")
    print(f"  ===== 耗时: {time.time() - start_time:.1f}s =====")
    return True

if __name__ == '__main__':
    start_time = time.time()
    success = incremental_update()
    sys.exit(0 if success else 1)
