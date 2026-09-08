#!/usr/bin/env python3
with open('/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md', 'r') as f:
    content = f.read()
with open('/Users/lidaosong/zq_web4_trading_system/audit/TEMP_NODE_16_06.txt', 'r') as f:
    new_node = f.read()

old_marker = 'P&L |\n### 2026-05-24 15:00'
new_marker = 'P&L |\n' + new_node + '\n### 2026-05-24 15:00'

if old_marker in content:
    new_content = content.replace(old_marker, new_marker, 1)
    with open('/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md', 'w') as f:
        f.write(new_content)
    print('SUCCESS: Node 16:06 inserted')
    # Verify
    with open('/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md', 'r') as f:
        c2 = f.read()
    if '16:06 BJT' in c2:
        print('16:06 confirmed in TRADES.md')
    else:
        print('WARNING: 16:06 NOT found')
else:
    print('FAIL: marker not found')
    print('Searching for alternatives...')
    for p in range(0, len(content)):
        if '15:00 BJT' in content[p:p+80] and 'P&L' in content[max(0,p-20):p]:
            print(f'Found at pos {p} with context: {repr(content[max(0,p-30):p+30])}')
            break
