#!/usr/bin/env python3
"""Patch coin_pool_manager.py:
1. PRIME_TARGET_TOTAL: 80 → 200
2. PRIME_MIN_VOLUME: 50000 → 30000  
3. PRIME_SECTOR_CAPACITY: expand proportionally
4. Add multi-dimensional scoring to build_prime_pool
"""

import re

with open('/Users/lidaosong/zq_web4_trading_system/tools/coin_pool_manager.py') as f:
    code = f.read()

# 1. Change PRIME_TARGET_TOTAL
code = code.replace('PRIME_TARGET_TOTAL = 80', 'PRIME_TARGET_TOTAL = 200')

# 2. Change PRIME_MIN_VOLUME
code = code.replace('PRIME_MIN_VOLUME = 50000', 'PRIME_MIN_VOLUME = 30000')

# 3. Expand sector capacities (roughly 2.5x from 80 to 200)
old_capacity = """PRIME_SECTOR_CAPACITY = {        # 赛道容量（LLM每日调整）
    'layer1': 15, 'meme': 15, 'ai': 10, 'defi': 10,
    'gamefi': 8, 'layer2': 5, 'rwa': 5, 'oracle': 3,
    'depin': 3, 'privacy': 3, 'cex': 3, 'cosmos': 3,
    'btc_ecosystem': 3, 'storage': 2, 'nft': 2,
    'crosschain': 2, 'lsd': 2, 'pow': 3, 'other': 15,
}"""

new_capacity = """PRIME_SECTOR_CAPACITY = {        # 赛道容量（LLM每日调整）— 扩至200币版
    'layer1': 25, 'meme': 25, 'ai': 20, 'defi': 20,
    'gamefi': 15, 'layer2': 12, 'rwa': 10, 'oracle': 8,
    'depin': 8, 'privacy': 6, 'cex': 5, 'cosmos': 6,
    'btc_ecosystem': 6, 'storage': 5, 'nft': 5,
    'crosschain': 4, 'lsd': 4, 'pow': 6, 'other': 30,
}"""

code = code.replace(old_capacity, new_capacity)

# 4. Modify build_prime_pool to add multi-dimensional scoring
# Find the section where it selects coins by volume per sector
old_select = """    # 4. 按赛道取TOP N
    prime_coins = []
    sector_counts = {}
    for sector in sorted(sector_capacity.keys()):
        limit = sector_capacity[sector]
        coins = by_sector.get(sector, [])
        taken = coins[:limit]
        prime_coins.extend(taken)
        sector_counts[sector] = len(taken)
        if taken:
            print(f\"    {sector:12s}: 取{limit}个（池中有{len(coins)}个）\")"""

new_select = """    # 4. 多维度评分选币（不只是成交量）
    # 每个币计算综合分 = vol_score*0.3 + vol_change_score*0.25 + price_change_score*0.25 + sector_momentum*0.2
    for c in active:
        vol = c.get('volume_24h_usd', 0)
        vol_change = c.get('volume_change_24h', 0)  # 成交量变化率
        price_change = abs(c.get('change_24h', 0))   # 24h涨幅绝对值
        
        # 成交量分（0-100）
        vol_score = min(100, vol / 500000) * 100 if vol < 50000000 else 100
        
        # 成交量变化分（0-100）- 放量=好信号
        vol_change_score = min(100, max(0, vol_change * 2)) if vol_change > 0 else 0
        
        # 价格动量分（0-100）- 适度涨幅=健康，大涨=风险
        if price_change > 0:
            price_score = min(100, price_change * 5)
            if price_change > 20:
                price_score = max(0, 100 - (price_change - 20) * 3)  # >20%涨幅的扣分
        else:
            price_score = max(0, 50 + price_change * 3)  # 跌的给保底分但不高
        
        # 综合分
        total_score = vol_score * 0.30 + vol_change_score * 0.25 + price_score * 0.25 + 20  # sector_momentum占20分（简化）
        c['_composite_score'] = round(total_score, 1)
    
    # 按赛道取TOP N（按综合分排序）
    prime_coins = []
    sector_counts = {}
    for sector in sorted(sector_capacity.keys()):
        limit = sector_capacity[sector]
        coins = by_sector.get(sector, [])
        # 按综合分排序
        coins.sort(key=lambda x: -x.get('_composite_score', 0))
        taken = coins[:limit]
        prime_coins.extend(taken)
        sector_counts[sector] = len(taken)
        if taken:
            print(f\"    {sector:12s}: 取{limit}个（池中有{len(coins)}个）\")"""

code = code.replace(old_select, new_select)

with open('/Users/lidaosong/zq_web4_trading_system/tools/coin_pool_manager.py', 'w') as f:
    f.write(code)

print("✅ Patch applied")
print(f"Total lines: {len(code.splitlines())}")

# Verify key changes
for check in ['PRIME_TARGET_TOTAL = 200', 'PRIME_MIN_VOLUME = 30000', '_composite_score', 'vol_change_score']:
    if check in code:
        print(f"  ✅ {check}")
    else:
        print(f"  ❌ {check} NOT FOUND")
