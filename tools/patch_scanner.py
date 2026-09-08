#!/usr/bin/env python3
"""Patch a3_signal_scanner.py to always include Binance 24h gainers TOP15"""

import re

with open('tools/a3_signal_scanner.py') as f:
    code = f.read()

# Find insertion point: right before "if not filtered:"
insert_before = "    if not filtered:"
insert_point = code.find(insert_before)

if insert_point == -1:
    print("ERROR: cannot find insertion point")
    exit(1)

# The code to inject - fetches top 15 gainers and adds them to filtered list
gainer_code = '''
    # 🆕 涨幅榜扫描：强制加上24h涨幅TOP15
    try:
        from urllib.request import urlopen, Request
        gainer_url = "https://api.binance.com/api/v3/ticker/24hr"
        gainer_req = Request(gainer_url, headers={"User-Agent": "Mozilla/5.0"})
        gainer_resp = urlopen(gainer_req, timeout=10)
        all_tickers = json.loads(gainer_resp.read().decode())
        
        # 过滤出USDT对，按涨幅排序
        gainer_usdt = [t for t in all_tickers 
                       if t['symbol'].endswith('USDT') 
                       and not is_blacklisted(t['symbol'].replace('USDT', ''))
                       and float(t['priceChangePercent']) > 5]  # 只>5%的涨幅
        
        gainer_usdt.sort(key=lambda x: -float(x['priceChangePercent']))
        top_gainers = gainer_usdt[:15]  # TOP15
        
        existing_symbols = {c['symbol'] for c in filtered}
        new_added = 0
        for g in top_gainers:
            sym = g['symbol'].replace('USDT', '')
            if sym not in existing_symbols:
                filtered.append({
                    'symbol': sym,
                    'volume_24h_usd': float(g['quoteVolume']),
                    'change_24h': float(g['priceChangePercent']),
                    'price': float(g['lastPrice']),
                    'category': 'other',
                    'status': 'active',
                    '_gainer': True,  # 标记为涨幅榜来源
                })
                new_added += 1
        
        if new_added > 0:
            print(f"  🚀 涨幅榜补充: +{new_added}个币（TOP15涨>5%的币）")
            # 打印涨幅榜TOP5
            print(f"  📈 涨幅前三: {', '.join([f'{g[\"symbol\"].replace(\"USDT\",\"\")}+{float(g[\"priceChangePercent\"]):.1f}%' for g in top_gainers[:5]])}")
    except Exception as e:
        print(f"  ⚠️  涨幅榜获取失败: {e}（不影响主扫描）")
    
'''

# Inject before "if not filtered:"
modified = code[:insert_point] + gainer_code + code[insert_point:]

with open('tools/a3_signal_scanner.py', 'w') as f:
    f.write(modified)

print("✅ Patch applied")
print(f"Total lines: {len(modified.splitlines())}")
