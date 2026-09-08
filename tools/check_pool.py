#!/usr/bin/env python3
"""检查选币库现状"""
import json

with open('/Users/lidaosong/zq_web4_trading_system/data/coin_pool_binance.json') as f:  # 原coin_pool_prime.json→改名
    data = json.load(f)

pool = data.get('pool', [])
print(f'精选池总量: {len(pool)}个币')

# 品类分布
cats = {}
for c in pool:
    cat = c.get('category', 'unknown')
    cats[cat] = cats.get(cat, 0) + 1
print(f'赛道分布:')
for k, v in sorted(cats.items(), key=lambda x: -x[1]):
    print(f'  {k:20s}: {v:4d}个')

# 成交量分布
vols = [c.get('volume_24h_usd', 0) for c in pool if c.get('volume_24h_usd', 0) > 0]
vols.sort()
if vols:
    print(f'\n成交量区间:')
    print(f'  最低: ${vols[0]:,.0f}')
    print(f'  25%:  ${vols[len(vols)//4]:,.0f}')
    print(f'  中位: ${vols[len(vols)//2]:,.0f}')
    print(f'  75%:  ${vols[3*len(vols)//4]:,.0f}')
    print(f'  最高: ${vols[-1]:,.0f}')

# 看看有多少币成交量<$1M
low_vol = [c for c in pool if c.get('volume_24h_usd', 0) < 1000000]
print(f'\n成交量<$1M: {len(low_vol)}个币')

# 看看币安总共有多少USDT交易对
import urllib.request
url = 'https://api.binance.com/api/v3/exchangeInfo'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=10)
exchange = json.loads(resp.read().decode())
usdt_pairs = [s for s in exchange['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
print(f'\n币安USDT交易对总数: {len(usdt_pairs)}个')

# 当前精选池占币安多大比例
pool_symbols = {c['symbol'] + 'USDT' for c in pool}
in_pool = sum(1 for s in usdt_pairs if s['baseAsset'] in pool_symbols)
print(f'精选池覆盖币安: {in_pool}/{len(usdt_pairs)} = {in_pool/len(usdt_pairs)*100:.1f}%')

# 再看全量池（如果有）
try:
    with open('/Users/lidaosong/zq_web4_trading_system/data/coin_pool.json') as f:
        full = json.load(f)
    full_pool = full.get('pool', [])
    print(f'\n全量池: {len(full_pool)}个币')
    full_symbols = {c['symbol'] + 'USDT' for c in full_pool}
    in_full = sum(1 for s in usdt_pairs if s['baseAsset'] in full_symbols)
    print(f'全量池覆盖币安: {in_full}/{len(usdt_pairs)} = {in_full/len(usdt_pairs)*100:.1f}%')
except:
    print('\n全量池文件不存在')
